# 🏢 Tofler Scraper

Tofler Scraper is a **free and open-source** scraper that gets you **unlimited** detailed Indian company data from Tofler for free.

## ✨ What Can I Get?

- 🏢 **Full profiles on 10M+ Indian companies** — status, capital, industry, offices, email & risk score
- 📊 **5 years of financials** — P&L, balance sheet & 21 ratios, in ₹ crore
- 🕸️ **Directors & corporate network** — board members, subsidiaries & connected companies
- 🔍 **Search & browse** — find any company by name, list companies by state or industry

## 🎥 Example: A Full Indian Company Profile

```json
{
  "cin": "U30007KA1996PTC019630",
  "name": "APPLE INDIA PRIVATE LIMITED",
  "link": "https://www.tofler.in/company/U30007KA1996PTC019630",
  "status": "Active",
  "company_type": "Private Others",
  "website": "www.apple.com",
  "industry": "Manufacturing of Machinery",
  "state": "Karnataka",
  "incorporation": { "date": "1996-01-19", "year": 1996, "age_years": 30.8 },
  "email": "contact_appleindia@apple.com",
  "registered_office": { "address": "13th Floor, Prestige Minsk Square, Municipal No. 6, Cubbon Road, Bangalore North, Karnataka - 560001", "pincode": "560001", "latitude": 12.9374749, "longitude": 77.4472495 },
  "capital": { "authorised": { "text": "₹ 2.0 Cr", "inr_crore": 2.0 }, "paid_up": { "text": "₹ 3.5 L", "inr_crore": 0.035 } },
  "key_metrics": {
    "period": "2026-03",
    "total_revenue": { "inr_crore": 104607.4, "change_pct": 31.78 },
    "ebitda": { "inr_crore": 8817.0, "change_pct": 87.44 },
    "net_profit": { "inr_crore": 5311.2, "change_pct": 66.18 },
    "networth": { "inr_crore": 6286.6, "change_pct": 83.69 },
    "return_on_equity": { "value": 84.5, "change": -8.91 }
  },
  "score": { "rating": "Very Good", "risks": { "severe": [], "moderate": ["HIGH LEVERAGE", "RECEIVABLES DETERIORATING"], "low": ["LOW INVENTORY"] } },
  "directors": [
    { "name": "Jamie Wonji Wong", "designation": "Director", "din": "09288107", "link": "https://www.tofler.in/jamie-wonji-wong/director/09288107", "tenure_years": 5 }
  ],
  "directors_count": 3,
  "locations_count": 45,
  "last_updated": "2026-10-23"
}
```

*Trimmed for readability.*

## 🚀 Unlimited Free Tofler Data — Get It in 60 Seconds

1️⃣ Clone and install:
```bash
git clone https://github.com/omkarcloud/tofler-scraper
cd tofler-scraper
python -m pip install -r requirements.txt
```

2️⃣ Start the API:
```bash
python run.py
```

3️⃣ Get your first data:
```bash
curl "http://localhost:8000/companies/details?company=U30007KA1996PTC019630"
```

```json
{
  "cin": "U30007KA1996PTC019630",
  "name": "APPLE INDIA PRIVATE LIMITED",
  "link": "https://www.tofler.in/company/U30007KA1996PTC019630",
  "status": "Active",
  "company_type": "Private Others",
  "website": "www.apple.com",
  "industry": "Manufacturing of Machinery",
  "state": "Karnataka",
  "incorporation": { "date": "1996-01-19", "year": 1996, "age_years": 30.8 },
  "email": "contact_appleindia@apple.com",
  "key_metrics": {
    "period": "2026-03",
    "total_revenue": { "inr_crore": 104607.4, "change_pct": 31.78 },
    "net_profit": { "inr_crore": 5311.2, "change_pct": 66.18 },
    "networth": { "inr_crore": 6286.6, "change_pct": 83.69 }
  },
  "score": { "rating": "Very Good" },
  "directors_count": 3,
  "locations_count": 45
}
```

All 6 endpoints are now live at `http://localhost:8000`.

Running it on a cloud server? Tofler refuses most cloud IPs, so set `TOFLER_PROXY=http://user:pass@host:port` before `python run.py`. From a home or office connection, no proxy is needed.

## 📚 Endpoints

6 endpoints cover everything you need.

| Endpoint | Path | Returns |
|---|---|---|
| Company Details | `/companies/details` | Status, capital, key metrics, risk score, directors and offices |
| Company Financials | `/companies/financials` | 5 years of P&L, balance sheet and 21 ratios |
| Company Network | `/companies/network` | Directors, subsidiaries and companies sharing a director |
| Search Companies | `/companies/search` | Up to 10 matches by name, with CIN and status |
| List Companies | `/companies/list` | 30 companies per page, by state and/or industry |
| Director Details | `/directors/details` | Every company a director sits on, with appointment dates |

## 🔍 Exploring Parameters

The same API is published on RapidAPI, and its playground is the easiest place to try parameters and see raw responses. Once a request looks right, run it locally for **unlimited free** data.

1. [Subscribe to the free plan](https://rapidapi.com/OmkarCloud/api/best-tofler-scraper-free-1000-calls/pricing) — 1,000 calls/month, no credit card.
2. [Try the endpoints in the playground](https://rapidapi.com/OmkarCloud/api/best-tofler-scraper-free-1000-calls/playground) — every param is pre-filled, so you see real data in one click.
3. Copy the generated code and replace `https://best-tofler-scraper-free-1000-calls.p.rapidapi.com` with `http://localhost:8000`. It will now run against your local API.

```python
import requests

# generated by the playground, host swapped for the local API
response = requests.get(
    "http://localhost:8000/companies/details",
    params={"company": "U30007KA1996PTC019630"},
)
print(response.json())
```

## 💬 Have Questions? We Have Answers.

You're a developer — we know how hard completing a project can be. So we offer full support: just message us and we'll reply ✅ with a solution within 1 working day.

[![Message Us on WhatsApp about Tofler Scraper](https://raw.githubusercontent.com/omkarcloud/assets/master/images/whatsapp-us.png)](https://www.omkar.cloud/l/tofler-scraper-github-whatsapp)

[![Ask Us by Email about Tofler Scraper](https://raw.githubusercontent.com/omkarcloud/assets/master/images/ask-on-email.png)](mailto:happy.to.help@omkar.cloud?subject=Help%20with%20Tofler%20Scraper%20API&body=I%20need%20help%20using%20the%20Tofler%20Scraper%20API.)

## ⚡ Popular Scrapers by Omkar Cloud

- [**Google Maps Scraper (3,100+ GitHub Stars)**](https://github.com/omkarcloud/google-maps-scraper) — type "dentists in New York", get every business as a ready-to-call lead list: phones, emails, websites & reviews. Up to 100K free leads/month.
- [**G2 Scraper**](https://www.omkar.cloud/tools/g2-scraper) — G2 product details, ratings & AI-found contacts
- [**Website Email Contact Scraper**](https://www.omkar.cloud/tools/website-email-contact-scraper) — emails, phones & socials from any website
- [**AliExpress Scraper**](https://www.omkar.cloud/tools/aliexpress-scraper-api) — live product details, SKU variants, stock & shipping
- [**Booking Scraper**](https://www.omkar.cloud/tools/booking-scraper) — Booking.com hotels: prices, ratings, rooms & amenities
- [**Etsy Scraper**](https://www.omkar.cloud/tools/etsy-scraper) — Etsy products: prices, discounts, shops & variations

## ⭐ Love It? [Star It ⭐!](https://github.com/omkarcloud/tofler-scraper)

Star the repo ⭐ and become my star hero!

It's just 1 click, but it means the world to me.

[![Star us on GitHub](https://raw.githubusercontent.com/omkarcloud/google-maps-scraper/master/screenshots/star-us.png)](https://github.com/omkarcloud/tofler-scraper)
