"""Cache TTL per /tofler/* endpoint (cache.py, keyed on the validated
params). Tofler's data is statutory MCA filing data: a company page moves
when a new filing lands (its own "Updated:" stamp is typically weeks old),
so a day of caching never serves a materially stale record. The three
company endpoints share ONE cached page parse (api._company_record), so
details + financials + network on the same company cost one upstream fetch.
"""
from datetime import timedelta

# One row per company id: the parsed full page record.
COMPANY_CACHE = timedelta(hours=24)
# Director pages move with the same filing cadence.
DIRECTOR_CACHE = timedelta(hours=24)
# Name search: companies are created / renamed slowly.
SEARCH_CACHE = timedelta(hours=12)
# The browse directory reorders as companies are registered.
LIST_CACHE = timedelta(hours=24)
