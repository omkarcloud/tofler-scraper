"""The /tofler/* endpoint functions (route_glue's route_table calls them
with the schema's loaded kwargs).

The three company endpoints (details / financials / network) slice ONE
cached page parse: cache.cached_call stores the full parse_company record
under tofler.company keyed on the company id, so hitting all three on the
same company costs one upstream fetch. The slices never overlap (the
details response carries counts where the other two carry the lists), so
no caller pays twice for the same bytes.
"""
from cache import cached_call
from tofler import cache_config as ttl
from tofler import parsers
from tofler.fetch import fetch_company, fetch_companylist, fetch_director, fetch_search
from tofler.refs import company_link

LIST_PAGE_SIZE = 30   # tofler.in's own directory page size


# ---- companies/search --------------------------------------------------------

def _search(query, limit):
    results = parsers.parse_search(fetch_search(query))[:limit]
    return {"query": query, "count": len(results), "results": results}


def companies_search(**data):
    return cached_call("tofler.search", data, _search, ttl.SEARCH_CACHE)


# ---- the shared company record -----------------------------------------------

def _company_record(company):
    return parsers.parse_company(fetch_company(company), company)


def _record(company):
    return cached_call("tofler.company", {"company": company}, _company_record,
                       ttl.COMPANY_CACHE)


def _identity(record):
    return {"cin": record["cin"], "name": record["name"], "link": record["link"]}


def _count(value):
    return len(value) if isinstance(value, list) else None


# ---- companies/details -------------------------------------------------------

def company_details(company):
    """Everything on the public company page except the multi-year financial
    tables (companies/financials) and the relationship lists
    (companies/network) — those carry counts here."""
    record = _record(company)
    return {
        **_identity(record),
        "status": record["status"],
        "company_type": record["company_type"],
        "company_class": record["company_class"],
        "is_listed": record["is_listed"],
        "website": record["website"],
        "description": record["description"],
        "industry": record["industry"],
        "industry_tags": record["industry_tags"],
        "products": record["products"],
        "state": record["state"],
        "incorporation": record["incorporation"],
        "email": record["email"],
        "registered_office": record["registered_office"],
        "capital": record["capital"],
        "revenue": record["revenue"],
        "key_metrics": record["key_metrics"],
        "score": record["score"],
        "directors": record["directors"],
        "directors_count": _count(record["directors"]),
        "locations": record["locations"],
        "locations_count": _count(record["locations"]),
        "charges_count": _count(record["charges"]),
        "connected_companies_count": _count(record["connected_companies"]),
        "subsidiaries_count": _count(record["subsidiaries"]),
        "last_agm_date": record["last_agm_date"],
        "last_updated": record["last_updated"],
    }


# ---- companies/financials ----------------------------------------------------

def company_financials(company):
    """The money view: key metrics with year-on-year changes, the financial
    highlights summary, standalone + consolidated P&L / balance sheet (₹
    crore and common-size %), the ratio table, and registered charges.
    Values Tofler keeps for its paid tier are null (large listed companies);
    unlisted companies usually carry the full figures."""
    record = _record(company)
    financials = record["financials"] or {}
    return {
        **_identity(record),
        "currency": "INR",
        "unit": "crore",
        "financial_year_end": (record["revenue"] or {}).get("financial_year_end"),
        "key_metrics": record["key_metrics"],
        "highlights": financials.get("highlights"),
        "profit_and_loss": financials.get("profit_and_loss"),
        "balance_sheet": financials.get("balance_sheet"),
        "ratios": financials.get("ratios"),
        "charges": record["charges"],
        "charges_count": _count(record["charges"]),
    }


# ---- companies/network -------------------------------------------------------

def company_network(company):
    """The relationship view: companies sharing a director, subsidiaries,
    and the board itself (with per-director profile links for
    /tofler/directors/details)."""
    record = _record(company)
    return {
        **_identity(record),
        "directors": record["directors"],
        "directors_count": _count(record["directors"]),
        "connected_companies": record["connected_companies"],
        "connected_companies_count": _count(record["connected_companies"]),
        "subsidiaries": record["subsidiaries"],
        "subsidiaries_count": _count(record["subsidiaries"]),
    }


# ---- companies/list ----------------------------------------------------------

def _companies_list(state, industry, page):
    html = fetch_companylist(state, industry, page)
    if html is None:   # past the last page
        rows, has_next = [], False
    else:
        rows, has_next = parsers.parse_companylist(html)
    # Tofler publishes no total count: `has_next` drives the next link
    # (route_glue.paginate) and the totals stay null.
    return {
        "state": state,
        "industry": industry,
        "results": rows,
        "pagination": {
            "page": page,
            "items_per_page": LIST_PAGE_SIZE,
            "has_next": has_next,
            "total_pages": None,
            "total_count": None,
        },
    }


def companies_list(**data):
    return cached_call("tofler.companies_list", data, _companies_list, ttl.LIST_CACHE)


# ---- directors/details -------------------------------------------------------

def _director_details(director):
    return parsers.parse_director(fetch_director(director), director)


def director_details(**data):
    return cached_call("tofler.director", data, _director_details, ttl.DIRECTOR_CACHE)
