"""Marshmallow request schemas for every /tofler/* route.

ONE param per input (tripadvisor QueryOrIdField convention, never a sibling
`url`/`id` pair):

    company    a CIN (L85110KA1981PLC013115), an LLPIN (AAN-5420), an FCRN
               (F01234) OR any tofler.in company link
    director   an 8-digit DIN OR any tofler.in director link
    state      a directory slug ("karnataka", "tamil-nadu", ...) or
               "all-india"
    industry   a directory slug ("finance", "computer-related-services", ...)

The state / industry slugs are tofler.in's own /companylist directory
(tofler/refs.py, captured 2026-10-23). /tofler/companies/list requires
`state`; state=all-india (every state) also requires an industry.
"""
from marshmallow import ValidationError, missing, validates_schema

from schema_fields import BaseSchema, ChoiceField, LimitField, PageField, QueryField, RefField
from tofler import refs

# Deep directory pages are heavy for the upstream and rarely useful past a
# few hundred; Tofler itself 404s past the real end, which companies/list
# turns into an empty page.
MAX_LIST_PAGE = 2000


class CompanyRefField(RefField):
    resolver = staticmethod(refs.resolve_company)


class DirectorRefField(RefField):
    resolver = staticmethod(refs.resolve_director)


class CompaniesSearchSchema(BaseSchema):
    query = QueryField(metadata={"description": "company name to search for"})
    limit = LimitField(default=10, max_size=10)   # upstream returns 10


class CompanySchema(BaseSchema):
    company = CompanyRefField(metadata={
        "description": "CIN / LLPIN / FCRN, or a tofler.in company link"})


class DirectorSchema(BaseSchema):
    director = DirectorRefField(metadata={
        "description": "8-digit DIN, or a tofler.in director link"})


class CompaniesListSchema(BaseSchema):
    state = ChoiceField([refs.ALL_INDIA, *refs.STATES], required=True, load_default=missing)
    industry = ChoiceField(list(refs.INDUSTRIES))
    page = PageField(max_page=MAX_LIST_PAGE)

    @validates_schema
    def _all_india_needs_industry(self, data, **kwargs):
        if data.get("state") == refs.ALL_INDIA and not data.get("industry"):
            raise ValidationError(
                f"state={refs.ALL_INDIA} lists every state, so it needs an "
                "industry (see tofler.in/companylist for the directory).", "industry")
