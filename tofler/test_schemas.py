"""Offline tests for the /tofler/* request schemas.

    python -m pytest tofler/test_schemas.py -q
"""
import os
import sys

import pytest
from marshmallow import ValidationError

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tofler import refs, schemas  # noqa: E402


def test_company_schema_accepts_cin_and_link():
    assert schemas.CompanySchema().load({"company": "l85110ka1981plc013115"}) == \
        {"company": "L85110KA1981PLC013115"}
    loaded = schemas.CompanySchema().load(
        {"company": "https://www.tofler.in/infosys-limited/company/L85110KA1981PLC013115"})
    assert loaded == {"company": "L85110KA1981PLC013115"}
    assert schemas.CompanySchema().load({"company": "AAN-5420"}) == {"company": "AAN-5420"}


@pytest.mark.parametrize("value", ["", "infosys", "https://example.com/company/x"])
def test_company_schema_rejects(value):
    with pytest.raises(ValidationError):
        schemas.CompanySchema().load({"company": value})


def test_company_schema_rejects_sibling_params():
    with pytest.raises(ValidationError):
        schemas.CompanySchema().load({"company": "AAN-5420", "cin": "AAN-5420"})


def test_director_schema():
    assert schemas.DirectorSchema().load({"director": "01876159"}) == {"director": "01876159"}
    loaded = schemas.DirectorSchema().load(
        {"director": "https://www.tofler.in/x/director/01876159"})
    assert loaded == {"director": "01876159"}
    with pytest.raises(ValidationError):
        schemas.DirectorSchema().load({"director": "123"})


def test_search_schema():
    loaded = schemas.CompaniesSearchSchema().load({"query": " infosys "})
    assert loaded == {"query": "infosys", "limit": 10}
    with pytest.raises(ValidationError):
        schemas.CompaniesSearchSchema().load({"query": "x", "limit": "11"})
    with pytest.raises(ValidationError):
        schemas.CompaniesSearchSchema().load({})


def test_list_schema():
    loaded = schemas.CompaniesListSchema().load({"state": "Karnataka"})
    assert loaded == {"state": "karnataka", "industry": None, "page": 1}
    loaded = schemas.CompaniesListSchema().load(
        {"state": "karnataka", "industry": "Computer-Related-Services", "page": "3"})
    assert loaded["industry"] == "computer-related-services"
    assert loaded["page"] == 3
    loaded = schemas.CompaniesListSchema().load({"state": "All-India", "industry": "finance"})
    assert loaded["state"] == "all-india"


def test_list_schema_requires_state():
    with pytest.raises(ValidationError):
        schemas.CompaniesListSchema().load({})
    with pytest.raises(ValidationError):
        schemas.CompaniesListSchema().load({"page": "2"})
    with pytest.raises(ValidationError):
        schemas.CompaniesListSchema().load({"industry": "finance"})


def test_list_schema_all_india_needs_industry():
    with pytest.raises(ValidationError):
        schemas.CompaniesListSchema().load({"state": "all-india"})


def test_companylist_path_drops_all_india():
    assert refs.companylist_path("all-india", "finance", 2) == "/companylist/finance/pg-2"
    assert refs.companylist_path("karnataka", None) == "/companylist/karnataka"


def test_list_schema_rejects_unknown_slugs():
    with pytest.raises(ValidationError):
        schemas.CompaniesListSchema().load({"state": "bangalore"})
    with pytest.raises(ValidationError):
        schemas.CompaniesListSchema().load({"industry": "software"})
