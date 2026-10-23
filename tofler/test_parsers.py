"""Offline tests for the Tofler parsers, reference resolvers and value
helpers.

    python -m pytest tofler/test_parsers.py -q

Fixtures are real www.tofler.in pages captured 2026-10-23 (tofler/fixtures/):
a listed company whose standalone view is partially paid-tier (Infosys), an
unlisted company with full public financials (Groww), an LLP (sparse page),
a director page, one /companylist directory page and two /cnamesearch
payloads. No network.
"""
import json
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tofler import parsers as P, refs  # noqa: E402

FX = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fixtures")


def fixture(name):
    with open(os.path.join(FX, name), encoding="utf-8") as f:
        return json.load(f) if name.endswith(".json") else f.read()


@pytest.fixture(scope="module")
def groww():
    return P.parse_company(fixture("company_groww.html"), "U65100KA2016PTC092879")


@pytest.fixture(scope="module")
def infosys():
    return P.parse_company(fixture("company_infosys.html"), "L85110KA1981PLC013115")


@pytest.fixture(scope="module")
def llp():
    return P.parse_company(fixture("company_llp.html"), "AAN-5420")


# ---- refs -------------------------------------------------------------------------------

@pytest.mark.parametrize("value,expected", [
    ("L85110KA1981PLC013115", "L85110KA1981PLC013115"),
    ("l85110ka1981plc013115", "L85110KA1981PLC013115"),
    ("AAN-5420", "AAN-5420"),
    ("aan-5420", "AAN-5420"),
    ("F01234", "F01234"),
    ("https://www.tofler.in/infosys-limited/company/L85110KA1981PLC013115", "L85110KA1981PLC013115"),
    ("https://www.tofler.in/company/AAN-5420", "AAN-5420"),
    ("https://tofler.in/x/company/U65100KA2016PTC092879?x=1", "U65100KA2016PTC092879"),
])
def test_resolve_company(value, expected):
    assert refs.resolve_company(value) == expected


@pytest.mark.parametrize("value", [
    "", "infosys", "12345", "L85110KA1981PLC01311",            # 20 chars
    "https://example.com/company/L85110KA1981PLC013115",       # wrong site
    "https://www.tofler.in/salil-satish-parekh/director/01876159",
])
def test_resolve_company_invalid(value):
    with pytest.raises(ValueError):
        refs.resolve_company(value)


@pytest.mark.parametrize("value,expected", [
    ("01876159", "01876159"),
    ("https://www.tofler.in/salil-satish-parekh/director/01876159", "01876159"),
    ("https://tofler.in/director/05321547", "05321547"),
])
def test_resolve_director(value, expected):
    assert refs.resolve_director(value) == expected


@pytest.mark.parametrize("value", [
    "", "1876159", "018761590", "name", "https://example.com/director/01876159",
    "https://www.tofler.in/company/L85110KA1981PLC013115",
])
def test_resolve_director_invalid(value):
    with pytest.raises(ValueError):
        refs.resolve_director(value)


def test_companylist_path():
    assert refs.companylist_path("karnataka", None, 1) == "/companylist/karnataka"
    assert refs.companylist_path("karnataka", "finance", 3) == "/companylist/karnataka/finance/pg-3"
    assert refs.companylist_path(None, "finance", 2) == "/companylist/finance/pg-2"


def test_slug_tables():
    assert len(refs.STATES) == 36
    assert len(refs.INDUSTRIES) == 30
    assert "karnataka" in refs.STATES
    assert "computer-related-services" in refs.INDUSTRIES


# ---- value helpers ----------------------------------------------------------------------

@pytest.mark.parametrize("value,expected", [
    ("₹ 2,029.1 Cr", 2029.1),
    ("800.0  cr", 800.0),
    ("8.5 L", 0.085),
    ("50,000.0", 0.005),         # plain rupees (LLP capital)
    ("₹ 1,311.8 Cr", 1311.8),
])
def test_parse_money(value, expected):
    assert P.parse_money(value)["inr_crore"] == pytest.approx(expected)


def test_parse_money_masks():
    assert P.parse_money("-") is None
    assert P.parse_money("GET PRO") is None
    assert P.parse_money("3,693.8", plain_unit="crore")["inr_crore"] == pytest.approx(3693.8)


@pytest.mark.parametrize("value,expected", [
    ("02 July, 1981", "1981-07-02"),
    ("19 Mar, 1999", "1999-03-19"),
    ("16 Oct 2026", "2026-10-16"),
    ("Jun 2026", "2026-06"),
    ("Mar 2022", "2022-03"),
    ("-", None),
    ("Not Available", None),
])
def test_parse_date(value, expected):
    assert P.parse_date(value) == expected


# ---- search -----------------------------------------------------------------------------

def test_parse_search():
    results = P.parse_search(fixture("search_infosys.json"))
    assert len(results) == 10
    first = results[0]
    assert first["name"] == "INFOSYS LIMITED"
    assert first["cin"] == "L85110KA1981PLC013115"
    assert first["status"] == "Active"
    assert first["link"].startswith("https://www.tofler.in/")
    # LLP ids come through as-is
    assert any(r["cin"] == "AAN-5420" for r in results)


def test_parse_search_nomatch():
    assert P.parse_search(fixture("search_nomatch.json")) == []


def test_parse_search_junk():
    assert P.parse_search(None) == []
    assert P.parse_search([{"weird": 1}, "x"]) == []


# ---- company page: identity -------------------------------------------------------------

def test_company_identity(groww):
    assert groww["cin"] == "U65100KA2016PTC092879"
    assert groww["name"] == "GROWW INVEST TECH PRIVATE LIMITED"
    assert groww["link"] == "https://www.tofler.in/company/U65100KA2016PTC092879"
    assert groww["status"] == "Active"
    assert groww["is_listed"] is False
    assert groww["company_class"] == "private limited company"
    assert groww["company_type"] == "Private Others"
    assert groww["industry"] == "Finance"
    assert groww["state"] == "Karnataka"
    assert groww["industry_tags"] == ["Fintech"]
    assert groww["products"] == ["Online investing platform"]
    assert groww["email"] == "corp.secretarial@groww.in"
    assert groww["incorporation"] == {"date": "2016-05-04", "year": 2016, "age_years": 10.5}
    assert groww["last_updated"] == "2026-10-16"
    assert groww["description"].startswith("GROWW INVEST TECH PRIVATE LIMITED is a financial technology")


def test_company_capital_and_revenue(groww):
    assert groww["capital"]["authorised"]["inr_crore"] == 20.0
    assert groww["capital"]["paid_up"]["inr_crore"] == 6.6
    assert groww["revenue"]["range"] == "Over INR 500 cr"
    assert groww["revenue"]["range_detail"] == "₹ 3500-3750 cr"
    assert groww["revenue"]["financial_year_end"] == "2025-03-31"
    assert groww["revenue"]["ebitda_change_pct"] == 45.6
    assert groww["revenue"]["networth_change_pct"] == 47.56


def test_company_registered_office(groww):
    office = groww["registered_office"]
    assert office["type"] == "Registered Office"
    assert office["state"] == "Karnataka"
    assert office["pincode"] == "560103"
    assert office["latitude"] == pytest.approx(12.9333767)


def test_company_listed_flags(infosys):
    assert infosys["is_listed"] is True
    assert infosys["website"] == "www.infosys.com"
    assert infosys["last_agm_date"] == "2026-06-23"
    assert infosys["description"] == ("The company is engaged in providing software "
                                      "solution and wide range of IT Services.")


# ---- company page: key metrics / score --------------------------------------------------

def test_key_metrics_public(groww):
    metrics = groww["key_metrics"]
    assert metrics["period"] == "2025-03"
    assert metrics["total_revenue"] == {"inr_crore": 3693.8, "change_pct": 44.2}
    assert metrics["ebitda"] == {"inr_crore": 580.3, "change_pct": 45.6}
    assert metrics["net_profit"]["inr_crore"] == 421.8
    assert metrics["return_on_equity"] == {"value": 32.2, "change": -1.34}
    assert metrics["debt_to_equity"] == {"value": 0.4, "change": 0.36}


def test_key_metrics_paywalled(infosys):
    metrics = infosys["key_metrics"]
    # Values are paid-tier for large listed companies; changes stay public.
    assert metrics["total_revenue"] == {"inr_crore": None, "change_pct": 9.86}
    assert metrics["networth"] == {"inr_crore": None, "change_pct": -7.39}
    assert metrics["paid_up_capital"]["inr_crore"] == 2029.1


def test_score(groww, infosys, llp):
    assert groww["score"]["rating"] == "Very Good"
    assert groww["score"]["risks"] == {"severe": [], "moderate": ["HIGH LEVERAGE"], "low": []}
    # Infosys renders the risk section with no rating tag.
    assert infosys["score"]["risks"] == {"severe": [], "moderate": [], "low": []}
    assert llp["score"] is None


# ---- company page: people / locations ---------------------------------------------------

def test_directors(groww):
    assert len(groww["directors"]) == 9
    first = groww["directors"][0]
    assert first["name"] == "Harsh Jain"
    assert first["din"] == "05321547"
    assert first["pan"] is None
    assert first["designation"] == "Director"
    assert first["tenure_years"] == 10
    assert first["link"] == "https://www.tofler.in/harsh-jain/director/05321547"


def test_directors_shareholder_badge(infosys):
    by_name = {d["name"]: d for d in infosys["directors"]}
    assert by_name["Salil Satish Parekh"]["is_shareholder"] is True
    assert by_name["Chitra Nayak"]["is_shareholder"] is False


def test_locations(infosys):
    assert len(infosys["locations"]) == 46
    office = infosys["locations"][0]
    assert office["type"] == "Registered Office"
    assert office["pincode"] == "560100"
    assert all("latitude" in loc for loc in infosys["locations"])


# ---- company page: financial tables -----------------------------------------------------

def test_financial_highlights(groww):
    highlights = groww["financials"]["highlights"]
    assert highlights["periods"] == ["2021-03", "2022-03", "2023-03", "2024-03", "2025-03"]
    assert highlights["rows"]["sales"] == [40.5, 348.3, 1258.2, 2560.3, 3684.6]


def test_balance_sheet_public(groww):
    sheet = groww["financials"]["balance_sheet"]["standalone"]
    assert sheet["rows"]["equity_capital"] == [3.3, 6.6, 6.6, 6.6, 6.6]
    pct = groww["financials"]["balance_sheet"]["standalone_pct_of_assets"]
    assert pct["rows"]["equity_capital"][0] == 0.58


def test_balance_sheet_consolidated(infosys):
    # Infosys: the standalone view is paid-tier, the consolidated is public.
    sheet = infosys["financials"]["balance_sheet"]
    assert sheet["standalone"]["rows"]["equity_capital"] == [None] * 5
    assert sheet["consolidated"]["rows"]["equity_capital"] == [2096.5, 2068.2, 2070.0, 2071.8, 2023.5]


def test_profit_and_loss(groww):
    pnl = groww["financials"]["profit_and_loss"]
    assert pnl["standalone"]["rows"]["sales"] == [40.5, 348.3, 1258.2, 2560.3, 3684.6]
    assert "standalone_pct_of_income" in pnl


def test_ratios_inherit_periods(groww):
    ratios = groww["financials"]["ratios"]["standalone"]
    assert ratios["periods"] == ["2021-03", "2022-03", "2023-03", "2024-03", "2025-03"]
    assert ratios["rows"]["current_ratio"] == [1.8, 1.4, 1.3, 1.1, 1.2]
    # section rows ("Solvency +") are dropped
    assert "solvency" not in ratios["rows"]


def test_llp_has_no_financials(llp):
    assert llp["financials"]["highlights"] is None
    assert llp["financials"]["balance_sheet"] is None
    assert llp["key_metrics"] is None


def test_llp_contributed_capital(llp, groww):
    # An LLP page carries "Contributed Capital" in place of authorised / paid-up.
    assert llp["capital"]["authorised"] is None
    assert llp["capital"]["paid_up"] is None
    assert llp["capital"]["contributed"] == {"text": "₹ 1.0 L", "inr_crore": pytest.approx(0.01)}
    assert groww["capital"]["contributed"] is None


# ---- company page: charges / network / subsidiaries -------------------------------------

def test_charges(groww, infosys, llp):
    assert len(groww["charges"]) == 2
    first = groww["charges"][0]
    assert first["holder"] == "ICICI Bank Limited"
    assert first["amount"]["inr_crore"] == 800.0
    assert first["date"] == "2026-02-02"
    assert infosys["charges"] == []        # "no registered charges"
    assert llp["charges"] is None          # section absent


def test_connected_companies(groww):
    connected = groww["connected_companies"]
    assert len(connected) == 20
    first = connected[0]
    assert first["name"] == "BILLIONBRAINS GARAGE VENTURES LIMITED"
    assert first["cin"] == "U72900KA2018FTC109343"
    assert first["common_directors_count"] == 5
    assert first["paid_up_capital"]["inr_crore"] == 488.8


def test_subsidiaries(infosys):
    subsidiaries = infosys["subsidiaries"]
    assert len(subsidiaries) == 122
    edgeverve = next(s for s in subsidiaries if s["name"] == "EDGEVERVE SYSTEMS LIMITED")
    assert edgeverve["cin"] == "U72200KA2014PLC073660"
    assert edgeverve["incorporation_year"] == 2014
    assert edgeverve["paid_up_capital"]["inr_crore"] == 1311.8
    foreign = next(s for s in subsidiaries if s["name"] == "Fluido Sweden AB")
    assert foreign["cin"] is None
    assert foreign["location"] == "Sweden"
    assert foreign["paid_up_capital"] is None


# ---- robustness -------------------------------------------------------------------------

def test_parse_company_on_junk():
    record = P.parse_company("<html><body><p>nothing</p></body></html>", "X")
    assert record["cin"] == "X"
    assert record["name"] is None
    assert record["directors"] == []
    assert record["charges"] is None
    assert record["financials"]["highlights"] is None


def test_parse_director_on_junk():
    record = P.parse_director("<html></html>", "01876159")
    assert record["din"] == "01876159"
    assert record["directorships"] == []


# ---- director page ----------------------------------------------------------------------

def test_parse_director():
    record = P.parse_director(fixture("director_parekh.html"), "01876159")
    assert record["name"] == "Salil Satish Parekh"
    assert record["din"] == "01876159"
    assert record["link"] == "https://www.tofler.in/director/01876159"
    assert record["active_directorships_count"] == 5
    assert record["people_associations_count"] == 23
    assert record["longest_association_years"] == 19
    assert record["directorships_count"] == 5
    seat = record["directorships"][-1]
    assert seat["company_name"] == "INFOSYS LIMITED"
    assert seat["cin"] == "L85110KA1981PLC013115"
    assert seat["status"] == "Active"
    assert seat["appointed_on"] == "2018-01-02"
    assert seat["designation"] == "Managing Director"


# ---- browse directory -------------------------------------------------------------------

def test_parse_companylist():
    rows, has_next = P.parse_companylist(fixture("companylist_karnataka_it_pg2.html"))
    assert has_next is True
    assert len(rows) == 30
    first = rows[0]
    assert first["name"] == "SAMYUKTA SYSTEMS AND SOFTWARE PRIVATE LIMITED"
    assert first["cin"] == "U72100KA1989PTC009794"
    assert first["incorporation_year"] == 1989
    assert first["industry"] == "Computer Related Services"
    assert first["status"] == "Active"


def test_parse_companylist_junk():
    rows, has_next = P.parse_companylist("<html></html>")
    assert rows == []
    assert has_next is False
