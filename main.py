"""Use the scraper straight from Python — no server needed.

    python main.py

Every function returns the same JSON the API does; results are written to
output/*.json.
"""
import json
import os

from tofler.api import companies_search, company_details, company_financials

os.makedirs("output", exist_ok=True)


def save(name, data):
    path = os.path.join("output", name)
    with open(path, "w") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"saved {path}")


if __name__ == "__main__":
    # a CIN / LLPIN or any tofler.in company link resolves to the same id
    save("company_apple_india.json", company_details("U30007KA1996PTC019630"))

    # 5 years of P&L, balance sheet and ratios, in INR crore
    save("financials_apple_india.json", company_financials("U30007KA1996PTC019630"))

    # up to 10 matches with CIN, status and link
    save("search_google.json", companies_search(query="google", limit=10))
