"""Reference resolvers + the browse-directory slug tables for /tofler/*.

ONE param per input (tripadvisor QueryOrIdField convention): `company`
accepts a bare CIN / LLPIN OR any tofler.in company link; `director`
accepts a bare DIN OR a tofler.in director link. Resolvers raise ValueError
with a user-facing message (RefField turns it into a 400).

Identifier shapes (MCA):
  * CIN    21 chars: L85110KA1981PLC013115 (listing letter, 5-digit industry,
           2-letter state, 4-digit year, 3-letter ownership, 6-digit serial)
  * FCRN   foreign company: F + 5 digits (also served at /company/<id>)
  * LLPIN  LLP: 3 letters + "-" + 4 digits (AAN-5420)
  * DIN    8 digits

The state / industry slugs are tofler.in's own /companylist directory
(66 links on https://www.tofler.in/companylist, captured 2026-10-23:
30 industries + 36 states). The directory accepts the two slugs in either
order, so list_companies can always send state first.
"""
import re
from urllib.parse import urlparse

SITE = "https://www.tofler.in"

CIN_RE = re.compile(r"^[LUF][0-9]{5}[A-Z]{2}[0-9]{4}[A-Z]{3}[0-9]{6}$", re.I)
LLPIN_RE = re.compile(r"^[A-Z]{3}-[0-9]{4}$", re.I)
FCRN_RE = re.compile(r"^F[0-9]{4,5}$", re.I)
DIN_RE = re.compile(r"^[0-9]{8}$")

# Loose shape for ids pulled out of a pasted link (the strict patterns
# above guard bare input; a link's own /company/<id> segment is trusted).
_LINK_ID_RE = re.compile(r"/company/([A-Za-z0-9-]{4,25})")
_LINK_DIN_RE = re.compile(r"/director/([0-9]{8})")


def _is_company_id(value):
    return bool(CIN_RE.match(value) or LLPIN_RE.match(value) or FCRN_RE.match(value))


def _host_is_tofler(value):
    host = (urlparse(value).hostname or "").lower()
    return host == "tofler.in" or host.endswith(".tofler.in")


def resolve_company(value):
    """Bare CIN / LLPIN / FCRN or a tofler.in company link -> the id."""
    value = (value or "").strip()
    candidate = value.upper()
    if _is_company_id(candidate):
        return candidate
    if value.startswith(("http://", "https://", "//")):
        url = value if not value.startswith("//") else "https:" + value
        if not _host_is_tofler(url):
            raise ValueError("Must be a tofler.in link.")
        match = _LINK_ID_RE.search(url)
        if match:
            return match.group(1).upper()
        raise ValueError("Must be a tofler.in company link "
                         "(https://www.tofler.in/<name>/company/<CIN>).")
    raise ValueError("Must be a CIN (L85110KA1981PLC013115), an LLPIN (AAN-5420) "
                     "or a tofler.in company link.")


def resolve_director(value):
    """Bare 8-digit DIN or a tofler.in director link -> the DIN."""
    value = (value or "").strip()
    if DIN_RE.match(value):
        return value
    if value.startswith(("http://", "https://", "//")):
        url = value if not value.startswith("//") else "https:" + value
        if not _host_is_tofler(url):
            raise ValueError("Must be a tofler.in link.")
        match = _LINK_DIN_RE.search(url)
        if match:
            return match.group(1)
        raise ValueError("Must be a tofler.in director link "
                         "(https://www.tofler.in/<name>/director/<DIN>).")
    raise ValueError("Must be an 8-digit DIN or a tofler.in director link.")


def company_link(company_id):
    return f"{SITE}/company/{company_id}"


def director_link(din):
    return f"{SITE}/director/{din}"


# ---- browse directory slugs ---------------------------------------------------

STATES = (
    "andaman-and-nicobar", "andhra-pradesh", "arunachal-pradesh", "assam",
    "bihar", "chandigarh", "chhattisgarh", "dadar-and-nager-haveli",
    "daman-and-diu", "delhi", "goa", "gujarat", "haryana", "himachal-pradesh",
    "jammu-and-kashmir", "jharkhand", "karnataka", "kerala", "lakshadweep",
    "madhya-pradesh", "maharashtra", "manipur", "meghalaya", "mizoram",
    "nagaland", "odisha", "pondicherry", "punjab", "rajasthan", "sikkim",
    "tamil-nadu", "telangana", "tripura", "uttar-pradesh", "uttarakhand",
    "west-bengal",
)

INDUSTRIES = (
    "agriculture", "business-services", "community-and-social-services",
    "computer-related-services", "construction", "education",
    "electricity-gas-and-water", "finance", "general-manufacturing",
    "health-and-social-work", "hotels-and-restaurants", "insurance",
    "manufacturing-chemical-products", "manufacturing-food-products",
    "manufacturing-leather-products", "manufacturing-machinery",
    "manufacturing-motor-vehicles", "manufacturing-paper-products",
    "manufacturing-textiles", "manufacturing-tobacco-products",
    "manufacturing-wearing-apparel", "manufacturing-wood-products",
    "mining-and-quarrying", "post-and-telecom", "real-estate-and-renting",
    "recreational-cultural-and-sporting-activities",
    "research-and-development", "trading", "transport-and-storage",
    "transport-services",
)

# Our own `state` value for "every state" — tofler.in has no unfiltered
# directory (/companylist alone is the index page), so it needs an industry.
ALL_INDIA = "all-india"


def companylist_path(state=None, industry=None, page=1):
    """The browse-directory path for a state and/or industry filter."""
    segments = [slug for slug in (state, industry) if slug and slug != ALL_INDIA]
    path = "/companylist/" + "/".join(segments)
    if page > 1:
        path += f"/pg-{page}"
    return path
