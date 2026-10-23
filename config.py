"""Configuration for the Tofler Scraper. Everything can be set with an
environment variable; the defaults work out of the box.

    PORT          port the API listens on (default 8000)
    TOFLER_PROXY  proxy URL for every request, e.g. http://user:pass@host:port
                  (default: none — direct). Tofler answers home and office
                  connections directly, but refuses most cloud / datacenter
                  server IPs (AWS, Google Cloud, ...) with HTTP 403. Running on
                  a cloud server? Set this to a proxy that Tofler accepts.

Everything else below is a plain constant with a working default — edit it
here if you need to.
"""
import os

PORT = int(os.environ.get("PORT", "8000"))

# Retry policy for transport errors and blocks (every request).
MAX_RETRIES = 3
RETRY_BACKOFF = 2          # seconds, multiplied by the attempt number

TOFLER_PROXY = os.environ.get("TOFLER_PROXY") or None


def tofler_proxy():
    """The proxy for one curl session (None = direct)."""
    return os.environ.get("TOFLER_PROXY") or None
