"""Tofler transport: plain curl_cffi with browser-impersonated TLS. No
browser, no cookies. Egress: one sticky datacenter proxy exit per
thread session (config.tofler_proxy(), knob TOFLER_EXIT) — the pod's own
Google Cloud IP is refused with nginx 403 on every surface (pod probe
2026-10-23; a home ISP in India is open, so a Mac run proves nothing). A
retryable failure drops the session, so the retry rides a fresh exit.

Four upstream surfaces, all open:

  * SEARCH  POST /cnamesearch  {cname, nonce} -> JSON list of up to 10
    companies. The nonce is computed by the site's own bundle
    (bundle.prod.3.4.2.js module 690): md5("a" + term). Without it the
    route answers 401 "Unauthorized access".

  * COMPANY GET /company/<CIN|LLPIN|FCRN> — server-rendered page (~350 KB
    for a large company). The slug prefix (/infosys-limited/company/..) is
    optional; the bare path serves the same page. Unknown ids answer a real
    HTTP 404 ("Tofler - Error" page).

  * DIRECTOR GET /director/<DIN> — server-rendered page, slug optional.
    An unknown DIN answers HTTP 200 with a "500 Error" page title, so
    fetch_director() maps that title to NotFound.

  * LIST    GET /companylist/<state>/<industry>/pg-<n> — the browse
    directory, 30 rows per page, slugs in either order, one or both.
    A page past the end answers HTTP 404.

Failure taxonomy (scraper_errors, mapped to HTTP by route_glue):
  ToflerUpstreamError  transport failure / 5xx            — retryable
  ToflerBlocked        403 / 429 / challenge page          — retryable
  ToflerBadRequest     upstream 400                        — never retried
  ToflerNotFound       404 / unknown CIN / unknown DIN     — never retried
"""
import hashlib
import os
import re
import sys
import threading
import time

# Allow direct execution (python tofler/fetch.py): flat imports resolve
# like under the server. Idempotent when imported normally.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import config
from scraper_errors import BadRequest, Blocked, NotFound, UpstreamError
from tofler.refs import SITE, companylist_path

IMPERSONATE = "chrome"
PAGE_TIMEOUT = 30     # company pages are up to ~350 KB
SEARCH_TIMEOUT = 15

PAGE_HEADERS = {
    "accept": ("text/html,application/xhtml+xml,application/xml;q=0.9,"
               "image/avif,image/webp,*/*;q=0.8"),
    "accept-language": "en-US,en;q=0.9",
    "upgrade-insecure-requests": "1",
}
SEARCH_HEADERS = {
    "accept": "application/json, text/javascript, */*; q=0.01",
    "accept-language": "en-US,en;q=0.9",
    "x-requested-with": "XMLHttpRequest",
    "origin": SITE,
    "referer": SITE + "/",
}

_TITLE_RE = re.compile(r"<title>([^<]*)</title>", re.I)


class ToflerUpstreamError(UpstreamError):
    """Transport failure or 5xx — retryable."""


class ToflerBlocked(ToflerUpstreamError, Blocked):
    """403 / 429 or a challenge page where HTML/JSON was expected — retryable."""


class ToflerBadRequest(BadRequest):
    """Upstream 400 — never retried."""


class ToflerNotFound(NotFound):
    """Company / director / list page does not exist — never retried."""


# One session per cheroot worker thread: a curl handle must not be shared
# across threads; these GETs are stateless so thread-lifetime sessions with
# keep-alive are enough.
_local = threading.local()


def _session():
    sess = getattr(_local, "session", None)
    if sess is None:
        from curl_cffi import requests as curl_requests
        sess = curl_requests.Session(impersonate=IMPERSONATE)
        proxy = config.tofler_proxy()
        if proxy:
            sess.proxies = {"http": proxy, "https": proxy}
        _local.session = sess
    return sess


def _drop_session():
    """Close the thread's session so a poisoned keep-alive connection dies."""
    sess = getattr(_local, "session", None)
    _local.session = None
    if sess is not None:
        try:
            sess.close()
        except Exception:
            pass


def _retrying(fn):
    """Run fn() under the shared retry policy (ToflerUpstreamError only;
    NotFound / BadRequest surface immediately)."""
    last = None
    for attempt in range(1, config.MAX_RETRIES + 1):
        try:
            return fn()
        except ToflerUpstreamError as e:
            last = e
            _drop_session()
            if attempt < config.MAX_RETRIES:
                time.sleep(config.RETRY_BACKOFF * attempt)
    raise last


def _page_title(text):
    match = _TITLE_RE.search(text or "")
    return (match.group(1).strip() if match else "")


def _classify(resp, label):
    """Map an HTTP response to the error taxonomy; return the body text."""
    if resp.status_code == 404:
        raise ToflerNotFound(f"{label} not found")
    if resp.status_code == 400:
        raise ToflerBadRequest(resp.text[:200])
    if resp.status_code in (401, 403, 429):
        raise ToflerBlocked(f"HTTP {resp.status_code} for {label}")
    if resp.status_code != 200:
        raise ToflerUpstreamError(f"HTTP {resp.status_code} for {label}")
    return resp.text


def _get_page(path, label):
    def once():
        try:
            resp = _session().get(SITE + path, headers=PAGE_HEADERS,
                                  timeout=PAGE_TIMEOUT)
        except Exception as e:
            raise ToflerUpstreamError(f"request failed: {type(e).__name__}: {e}")
        text = _classify(resp, label)
        title = _page_title(text)
        # Their custom error pages can also surface as HTTP 200.
        if title == "Tofler - Error":
            raise ToflerNotFound(f"{label} not found")
        if title == "500 Error":
            raise ToflerNotFound(f"{label} not found")
        return text
    return _retrying(once)


def search_nonce(term):
    """The site's own autocomplete token: md5("a" + term), computed by
    bundle.prod.3.4.2.js (module 690 -> module 172, an inlined md5)."""
    return hashlib.md5(("a" + term).encode("utf-8")).hexdigest()


def fetch_search(term):
    """POST /cnamesearch -> the raw JSON list (up to 10 companies).
    A term with no match returns [{"label": "No companies found", ...}]."""
    def once():
        try:
            resp = _session().post(SITE + "/cnamesearch",
                                   data={"cname": term, "nonce": search_nonce(term)},
                                   headers=SEARCH_HEADERS, timeout=SEARCH_TIMEOUT)
        except Exception as e:
            raise ToflerUpstreamError(f"request failed: {type(e).__name__}: {e}")
        text = _classify(resp, "search")
        try:
            payload = resp.json()
        except Exception:
            raise ToflerBlocked(f"non-JSON search response: {text[:120]}")
        if not isinstance(payload, list):
            raise ToflerUpstreamError(f"unexpected search payload shape: {text[:120]}")
        return payload
    return _retrying(once)


def fetch_company(company_id):
    """GET the company page HTML for a CIN / LLPIN / FCRN."""
    return _get_page(f"/company/{company_id}", f"company {company_id}")


def fetch_director(din):
    """GET the director page HTML for a DIN."""
    return _get_page(f"/director/{din}", f"director {din}")


def fetch_companylist(state=None, industry=None, page=1):
    """GET one browse-directory page (30 rows)."""
    path = companylist_path(state, industry, page)
    label = f"company list {path}"
    try:
        return _get_page(path, label)
    except ToflerNotFound:
        # Past-the-end pages 404; the API reports an empty page instead so
        # paging clients stop cleanly.
        if page > 1:
            return None
        raise
