"""HTML / JSON -> clean dicts for every /tofler/* endpoint.

Everything on a Tofler company page is server-rendered: the sections are
plain tables plus three embedded JSON vars (locationsTableData,
subsidiariesData) and one hidden markdown block ("# Key metrics of ...")
that carries the key-metric values and year-on-year changes. Figures the
site keeps for its paid tier render as "GET PRO" / "Details available with
Tofler Pro subscription" and come back as null here. Placeholder dashes
("-", "NA") are null too, never strings.

Value conventions (shared with the other scraper packages):
  * money   {"text": "₹ 2,029.1 Cr", "inr_crore": 2029.1} — text as printed,
            numeric normalized to INR crore (L = lakh = 0.01 cr, plain
            numbers are rupees)
  * dates   ISO: "02 July, 1981" -> "1981-07-02", "Mar 2026" -> "2026-03"
  * keys    snake_case; `link` not `url`; booleans as questions

Fixtures captured 2026-10-23 (tofler/fixtures/): a listed company with a
partially paywalled standalone view (Infosys), an unlisted company with
full public financials (Groww), an LLP (sparse page), a director page and
a /companylist directory page.
"""
import json
import re

from bs4 import BeautifulSoup

from tofler.refs import SITE

_MONTHS = {m.lower()[:3]: i for i, m in enumerate(
    ["January", "February", "March", "April", "May", "June", "July",
     "August", "September", "October", "November", "December"], 1)}

# Paid-tier masks and placeholder dashes -> null.
_MASKS = {"", "-", "NA", "N/A", "GET PRO",
          "Details available with Tofler Pro subscription"}

_FULL_DATE_RE = re.compile(r"(\d{1,2})\s+([A-Za-z]+),?\s+(\d{4})")
_MONTH_YEAR_RE = re.compile(r"^([A-Za-z]{3,9})\s+(\d{4})$")
_NUMBER_RE = re.compile(r"-?\d[\d,]*\.?\d*")


def _soup(html):
    return BeautifulSoup(html, "lxml")


def _text(node, sep=" "):
    return node.get_text(sep, strip=True) if node is not None else ""


def _clean(value):
    """Collapse whitespace; placeholder masks -> None."""
    if value is None:
        return None
    value = " ".join(str(value).split())
    return None if value in _MASKS else value


def parse_number(value):
    """"2,029.1" / "-21.81" -> float; masked / non-numeric -> None."""
    value = _clean(value)
    if value is None:
        return None
    match = _NUMBER_RE.search(value.replace("\u2212", "-"))
    if not match:
        return None
    try:
        return float(match.group(0).replace(",", ""))
    except ValueError:
        return None


def parse_money(value, plain_unit="rupee"):
    """"₹ 2,029.1 Cr" / "8.5 L" / "13,333.0" -> {text, inr_crore}.
    Units: Cr = crore, L/lac/lakh = 0.01 crore, K = 0.0001 crore. A number
    with no unit is rupees (LLP capital rows) unless `plain_unit="crore"`
    (the key-metrics block states "All rupee values in INR crores").
    Masked -> None (the whole object)."""
    text = _clean(value)
    if text is None:
        return None
    number = parse_number(text)
    if number is None:
        return {"text": text, "inr_crore": None}
    lowered = text.lower()
    if re.search(r"\bcr\b|crore", lowered):
        crore = number
    elif re.search(r"\bl\b|lakh|lac", lowered):
        crore = number / 100.0
    elif re.search(r"\bk\b", lowered):
        crore = number / 10000.0
    elif plain_unit == "crore":
        crore = number
    else:
        crore = number / 1e7
    return {"text": text, "inr_crore": round(crore, 6)}


def parse_date(value):
    """"02 July, 1981" / "16 Oct 2026" -> "1981-07-02"; "Jun 2026" ->
    "2026-06"; anything else (incl. masks) -> None."""
    value = _clean(value)
    if value is None:
        return None
    match = _FULL_DATE_RE.search(value)
    if match:
        day, month_name, year = match.groups()
        month = _MONTHS.get(month_name.lower()[:3])
        if month:
            return f"{year}-{month:02d}-{int(day):02d}"
    match = _MONTH_YEAR_RE.match(value)
    if match:
        month = _MONTHS.get(match.group(1).lower()[:3])
        if month:
            return f"{match.group(2)}-{month:02d}"
    return None


def _period(value):
    """Table period header "Mar 2022" -> "2022-03" (fallback: as printed)."""
    return parse_date(value) or _clean(value)


def _snake(label):
    """Row label -> snake_case key: "LT loans and advances" ->
    "lt_loans_and_advances"; the "+" expander marker is dropped."""
    label = re.sub(r"[^0-9a-zA-Z]+", "_", label.replace("+", " ")).strip("_")
    return label.lower()


def _link(href):
    if not href:
        return None
    return href if href.startswith("http") else SITE + href


_COMPANY_HREF_RE = re.compile(r"/company/([A-Za-z0-9-]{4,25})")
_DIRECTOR_HREF_RE = re.compile(r"/director/(\d{8})")


def _id_from_href(href, pattern=_COMPANY_HREF_RE):
    match = pattern.search(href or "")
    return match.group(1).upper() if match else None


# ---- search --------------------------------------------------------------------

def parse_search(payload):
    """/cnamesearch JSON -> clean result rows. The id is the company's CIN
    (LLPIN for LLPs, FCRN for foreign companies) — Tofler serves all three
    at /company/<id>."""
    results = []
    for row in payload or []:
        if not isinstance(row, dict) or row.get("subtype") != "companyinfo":
            continue   # "nomatch" placeholder rows
        cin = _clean(row.get("value"))
        results.append({
            "name": _clean(row.get("label")),
            "cin": cin.upper() if cin else None,
            "status": _clean(row.get("status")),
            "link": _link(row.get("url")),
        })
    return results


# ---- company page --------------------------------------------------------------

def _breadcrumb(soup):
    """["All Companies", state, industry, name] -> (state, industry)."""
    items = [_text(item).replace("›", "").strip() for item in soup.select(".breadcrumb_item")]
    items = [item for item in items if item]
    if len(items) >= 4:
        return items[1], items[2]
    return None, None


def _header(soup, html):
    title_block = soup.select_one(".company_title")
    name = _text(title_block.find("h1") if title_block else soup.find("h1"))
    website = None
    if title_block:
        anchor = title_block.find("a")
        website = _clean(_text(anchor)) if anchor else None
    status = None
    point = soup.select_one(".circular_point")
    if point is not None:
        status = _clean(_text(point.find_next_sibling("span")))
    updated_match = re.search(r"Updated:\s*([0-9]{1,2}\s+[A-Za-z]+\s+[0-9]{4})", html)
    last_updated = parse_date(updated_match.group(1)) if updated_match else None
    return name or None, website, status, last_updated


def _description_blocks(soup):
    """(business description, full prose) from p.company_description. The
    first <p> is "<description><br><br><boilerplate prose>"; pages without a
    written description start straight at the prose."""
    paragraphs = soup.select("p.company_description")
    if not paragraphs:
        return None, ""
    prose_parts = [_text(p) for p in paragraphs]
    chunks = [c.strip() for c in re.split(r"<br\s*/?>\s*<br\s*/?>", paragraphs[0].decode_contents()) if c.strip()]
    description = None
    if len(chunks) >= 2:
        first = BeautifulSoup(chunks[0], "lxml").get_text(" ", strip=True)
        # The prose chunk always opens with "<Name>, is a ..." / "<Name> is
        # a ..." — a leading chunk that doesn't is the business description.
        if not re.search(r"(?:is an?|was)\s+(?:listed|unlisted|private|public)", first[:200]):
            description = _clean(first)
        elif not first.rstrip().endswith(("cr.", "cr")):
            description = None
    return description, " ".join(prose_parts)


def _prose_facts(prose):
    """Regex the stable facts out of the generated company paragraph."""
    facts = {}
    match = re.search(r"incorporated on\s+(\d{1,2}\s+[A-Za-z]+,?\s+\d{4})", prose)
    facts["incorporation_date"] = parse_date(match.group(1)) if match else None
    match = re.search(r"is an? (listed|unlisted)", prose)
    facts["is_listed"] = {"listed": True, "unlisted": False}.get(match.group(1)) if match else None
    match = re.search(r"classified as an? ([^.]+?) and is located", prose)
    facts["company_class"] = _clean(match.group(1)) if match else None
    match = re.search(r"operating revenue range is\s+(.+?)\s+for the financial year ending on\s+"
                      r"(\d{1,2}\s+[A-Za-z]+,?\s+\d{4})", prose)
    facts["revenue_range"] = _clean(match.group(1)) if match else None
    facts["financial_year_end"] = parse_date(match.group(2)) if match else None
    match = re.search(r"EBITDA has (increased|decreased) by\s+([\d.]+)%", prose)
    facts["ebitda_change_pct"] = (parse_number(match.group(2)) * (1 if match.group(1) == "increased" else -1)
                                  if match else None)
    match = re.search(r"networth has (increased|decreased) by\s+([\d.]+)%", prose)
    facts["networth_change_pct"] = (parse_number(match.group(2)) * (1 if match.group(1) == "increased" else -1)
                                    if match else None)
    match = re.search(r"AGM.*?was held on\s+(\d{1,2}\s+[A-Za-z]+,?\s+\d{4})", prose)
    facts["last_agm_date"] = parse_date(match.group(1)) if match else None
    return facts


def _industry_block(soup):
    """("Fintech" tags, ["Online investing platform", ...] products)."""
    tags, products = [], []
    for title in soup.select(".stats_title"):
        if _text(title) != "Industry and products":
            continue
        section = title.parent
        tags = [_clean(_text(tag)) for tag in section.select(".company_tag_item")]
        tags = [tag for tag in tags if tag]
        for item in section.select("ul li"):
            product = _clean(_text(item))
            if product:
                products.extend(p.strip() for p in product.split(",") if p.strip())
        break
    return tags, products


def _company_size(soup):
    """The "Company size" cards: Auth Capital / Paidup Capital / Revenue."""
    cards = {}
    for title in soup.select(".stats_title"):
        if _text(title) != "Company size":
            continue
        for label_div in title.parent.select(".key_metrics_wrapper"):
            label = _snake(_text(label_div))
            value_span = label_div.find_parent("div").find_next_sibling("span")
            cards[label] = _clean(_text(value_span))
        break
    return cards


_KEY_METRIC_KEYS = {
    "auth_capital": "authorised_capital", "paidup_capital": "paid_up_capital",
    "revenue": "revenue_range", "total_revenue": "total_revenue",
    "ebitda": "ebitda", "net_profit": "net_profit", "networth": "networth",
    "borrowings": "borrowings", "assets": "assets",
    "gross_margin": "gross_margin", "operating_margin": "operating_margin",
    "net_profit_margin": "net_profit_margin", "return_on_equity": "return_on_equity",
    "roce": "roce", "debt_to_equity": "debt_to_equity",
}
_MONEY_METRICS = {"authorised_capital", "paid_up_capital", "total_revenue",
                  "ebitda", "net_profit", "networth", "borrowings", "assets"}


def _key_metrics(html):
    """The hidden "# Key metrics of ..." markdown block -> one dict:
    {"period": "2025-03", "<metric>": {"value"|money..., "change": float}}.
    ₹ metrics carry the year-on-year change in percent; margins and ratios
    carry the absolute change. Paid-tier values are null."""
    match = re.search(r"#\s*Key metrics of .*?Based on\s+([A-Za-z]+\s+\d{4})\s+numbers\.(.*?)</div>",
                      html, re.S)
    if not match:
        return None
    metrics = {"period": _period(match.group(1))}
    for row in re.findall(r"\|\s*([^|\n]+?)\s*\|\s*([^|\n]*?)\s*\|\s*([^|\n]*?)\s*\|", match.group(2)):
        label, value, change = row
        key = _KEY_METRIC_KEYS.get(_snake(label))
        if not key or key == "revenue_range":   # range duplicated from the size cards
            continue
        change_number = parse_number(change)
        if key in _MONEY_METRICS:
            money = parse_money(value, plain_unit="crore")
            metrics[key] = {
                "inr_crore": money["inr_crore"] if money else None,
                "change_pct": change_number,
            }
        else:
            metrics[key] = {"value": parse_number(value), "change": change_number}
    return metrics


def _directors(soup):
    """The People table: designation, name, DIN or PAN, tenure."""
    directors = []
    for table in soup.find_all("table"):
        headers = [_text(th) for th in table.find_all("th")]
        if headers[:3] != ["Designation", "Name", "DIN/PAN"]:
            continue
        for row in table.find_all("tr")[1:]:
            cells = row.find_all("td")
            if len(cells) < 4:
                continue
            anchor = cells[1].find("a")
            name = _clean(_text(anchor)) if anchor else None
            if name is None:
                # badge text ("Shareholder") shares the cell with the name
                name = _clean(_text(cells[1]).replace("Shareholder", ""))
            identifier = _clean(_text(cells[2]))
            is_din = bool(identifier and re.fullmatch(r"\d{8}", identifier))
            directors.append({
                "name": name,
                "designation": _clean(_text(cells[0])),
                "din": identifier if is_din else None,
                "pan": identifier if not is_din else None,
                "link": _link(anchor.get("href")) if anchor else None,
                "tenure_years": (lambda n: int(n) if n is not None else None)(
                    parse_number(_text(cells[3]))),
                "is_shareholder": "Shareholder" in _text(cells[1]),
            })
        break
    return directors


def _embedded_json(html, name):
    match = re.search(r"(?:var|const|let)\s+" + name + r"\s*=\s*(\[.*?\]);", html, re.S)
    if not match:
        return None
    try:
        return json.loads(match.group(1))
    except ValueError:
        return None


def _locations(html):
    """The locationsTableData JSON var: every office/plant with type and
    coordinates."""
    rows = _embedded_json(html, "locationsTableData") or []
    locations = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        address = _clean((row.get("address") or "").replace("\n", ", "))
        locations.append({
            "type": _clean(row.get("type")),
            "address": address,
            "city": _clean(row.get("city")),
            "state": _clean(row.get("state")),
            "pincode": _clean(row.get("pincode")),
            "latitude": row.get("latitude"),
            "longitude": row.get("longitude"),
        })
    return locations


def _financial_table(table, fallback_periods=None):
    """One financialsTable -> {"periods": [...], "rows": {snake_key:
    [floats|None]}}. "GET PRO" cells are null; a table whose cells are all
    null (fully paid-tier) is still returned so the shape is predictable.
    The ratio table carries no header row of its own (visually it reuses the
    P&L periods), so `fallback_periods` fills in; its section rows
    ("Solvency +" over empty cells) are dropped."""
    header = table.find("tr")
    if header is None:
        return None
    periods = [_period(_text(th)) for th in header.find_all("th")[1:]]
    data_rows = table.find_all("tr")
    if not periods:
        periods = list(fallback_periods or [])
    else:
        data_rows = data_rows[1:]
    rows = {}
    for row in data_rows:
        cells = row.find_all("td")
        if len(cells) < 2:
            continue
        label = _text(cells[0]).replace("+", "").strip()
        if not label:
            continue
        raw = [_text(cell) for cell in cells[1:(len(periods) + 1) if periods else None]]
        if not any(raw):
            continue   # section header row (empty cells)
        rows[_snake(label)] = [parse_number(value) for value in raw]
    if not rows:
        return None
    return {"periods": periods, "rows": rows}


_FINANCIAL_TABLE_IDS = {
    "reg-pnl-table": ("profit_and_loss", "standalone"),
    "reg-cs-pnl-table": ("profit_and_loss", "standalone_pct_of_income"),
    "cons-pnl-table": ("profit_and_loss", "consolidated"),
    "cons-cs-pnl-table": ("profit_and_loss", "consolidated_pct_of_income"),
    "reg-bs-table": ("balance_sheet", "standalone"),
    "reg-cs-bs-table": ("balance_sheet", "standalone_pct_of_assets"),
    "cons-bs-table": ("balance_sheet", "consolidated"),
    "cons-cs-bs-table": ("balance_sheet", "consolidated_pct_of_assets"),
    "reg-ratio-table": ("ratios", "standalone"),
    "cons-ratio-table": ("ratios", "consolidated"),
}


def _financial_tables(soup):
    """All id'd financial tables plus the un-id'd "Financial Highlights"
    summary -> {"highlights": table, "profit_and_loss": {...}, ...}."""
    out = {"highlights": None, "profit_and_loss": {}, "balance_sheet": {}, "ratios": {}}
    fallback_periods = None
    for table in soup.select("table.financialsTable"):
        parsed = _financial_table(table, fallback_periods)
        if parsed is None:
            continue
        if parsed["periods"] and fallback_periods is None:
            fallback_periods = parsed["periods"]
        table_id = table.get("id")
        if table_id in _FINANCIAL_TABLE_IDS:
            group, key = _FINANCIAL_TABLE_IDS[table_id]
            out[group][key] = parsed
        elif table_id is None and out["highlights"] is None:
            out["highlights"] = parsed
    for group in ("profit_and_loss", "balance_sheet", "ratios"):
        if not out[group]:
            out[group] = None
    return out


def _charges(soup, html):
    """The "Charges on assets" table (secured borrowings). A page with no
    charges prints "the company has no registered charges" -> []."""
    for table in soup.find_all("table"):
        headers = [_text(th) for th in table.find_all("th")]
        if headers[:2] != ["Charge Holder", "Amount"]:
            continue
        charges = []
        for row in table.find_all("tr")[1:]:
            cells = row.find_all("td")
            if len(cells) < 3:
                continue
            charges.append({
                "holder": _clean(_text(cells[0])),
                "amount": parse_money(_text(cells[1])),
                "date": parse_date(_text(cells[2])),
            })
        return charges
    if "no registered charges" in html:
        return []
    return None


def _connected_companies(soup):
    """"Companies connected through Directors": every company sharing at
    least one board member."""
    for table in soup.find_all("table"):
        headers = [_text(th) for th in table.find_all("th")]
        if headers[:4] != ["Name", "Status", "Paid up Capital", "Common Directors"]:
            continue
        rows = []
        for row in table.find_all("tr")[1:]:
            cells = row.find_all("td")
            if len(cells) < 5:
                continue
            anchor = cells[0].find("a")
            href = anchor.get("href") if anchor else None
            common = parse_number(_text(cells[3]))
            rows.append({
                "name": _clean(_text(cells[0])),
                "cin": _id_from_href(href),
                "link": _link(href),
                "status": _clean(_text(cells[1])),
                "paid_up_capital": parse_money(_text(cells[2])),
                "common_directors_count": int(common) if common is not None else None,
                "state": _clean(_text(cells[4])),
            })
        return rows
    return None


def _subsidiaries(soup):
    """The "Subsidiary Companies" table; Indian subsidiaries carry a link."""
    for table in soup.find_all("table"):
        headers = [_text(th) for th in table.find_all("th")]
        if headers[:2] != ["Name", "State / Country"]:
            continue
        rows = []
        for row in table.find_all("tr")[1:]:
            cells = row.find_all("td")
            if len(cells) < 4:
                continue
            anchor = cells[0].find("a")
            href = anchor.get("href") if anchor else None
            year = parse_number(_text(cells[2]))
            rows.append({
                "name": _clean(_text(cells[0])),
                "cin": _id_from_href(href),
                "link": _link(href),
                "location": _clean(_text(cells[1])),
                "incorporation_year": int(year) if year is not None else None,
                "paid_up_capital": parse_money(_text(cells[3])),
            })
        return rows
    return None


def _score(soup):
    """Tofler Score rating + the three risk lists. "No risks identified"
    renders as a list item and maps to an empty list."""
    tag = soup.select_one(".score_tag")
    rating = _clean(_text(tag)) if tag else None
    risks = {}
    found_risk_section = False
    for level in ("Severe", "Moderate", "Low"):
        items = []
        marker = soup.find(string=re.compile(rf"^\s*{level} Risk\s*$"))
        if marker:
            found_risk_section = True
            block = marker.find_parent("div")
            ul = block.find_next("ul") if block else None
            if ul:
                for li in ul.find_all("li"):
                    text = _clean(_text(li))
                    if text and text != "No risks identified":
                        items.append(text)
        risks[level.lower()] = items
    if rating is None and not found_risk_section:
        return None
    return {"rating": rating, "risks": risks}


def _registered_details(soup):
    """The "Registered Details" cards: CIN, incorporation year + age, email,
    capital, AGM month, company type."""
    heading = None
    for h2 in soup.find_all("h2"):
        if _text(h2) == "Registered Details":
            heading = h2
            break
    if heading is None:
        return {}
    section = heading.find_parent("div") or heading.parent
    # Walk the section's h3 label -> next-text pairs.
    details = {}
    for h3 in section.find_all_next("h3"):
        label = _text(h3)
        if label.startswith(("What is", "FAQ")):   # the FAQ block follows
            break
        value_node = h3.find_next_sibling()
        value = _clean(_text(value_node)) if value_node is not None else None
        details[_snake(label)] = value
        if label == "Type":
            break
    return details


def parse_company(html, company_id):
    """The full public company record, one page fetch. api.py slices this
    into the details / financials / network endpoint responses."""
    soup = _soup(html)
    name, website, status, last_updated = _header(soup, html)
    state, industry = _breadcrumb(soup)
    description, prose = _description_blocks(soup)
    facts = _prose_facts(prose)
    tags, products = _industry_block(soup)
    size_cards = _company_size(soup)
    registered = _registered_details(soup)
    locations = _locations(html)
    directors = _directors(soup)
    financials = _financial_tables(soup)
    charges = _charges(soup, html)
    connected = _connected_companies(soup)
    subsidiaries = _subsidiaries(soup)

    cin = registered.get("cin") or company_id
    incorporation_text = registered.get("incorporation")   # "1981, 45.3 years"
    incorporation_year = age_years = None
    if incorporation_text:
        parts = incorporation_text.split(",")
        year = parse_number(parts[0])
        incorporation_year = int(year) if year else None
        if len(parts) > 1:
            age_years = parse_number(parts[1])
    incorporation_date = facts.get("incorporation_date")
    if incorporation_year is None and incorporation_date:
        incorporation_year = int(incorporation_date[:4])

    registered_office = next((loc for loc in locations
                              if (loc.get("type") or "").lower() == "registered office"), None)

    return {
        "cin": cin,
        "name": name,
        "link": f"{SITE}/company/{cin}",
        "status": status,
        "company_type": registered.get("type"),
        "company_class": facts.get("company_class"),
        "is_listed": facts.get("is_listed"),
        "website": website,
        "description": description,
        "industry": industry,
        "industry_tags": tags,
        "products": products,
        "state": state,
        "incorporation": {
            "date": incorporation_date,
            "year": incorporation_year,
            "age_years": age_years,
        },
        "email": registered.get("company_email"),
        "registered_office": registered_office,
        "capital": {
            "authorised": parse_money(registered.get("authorised_capital")
                                      or size_cards.get("auth_capital")),
            "paid_up": parse_money(registered.get("paid_up_capital")
                                   or size_cards.get("paidup_capital")),
            # LLPs carry "Contributed Capital" instead of the two above
            # (the only capital figure on an LLP page; None for companies).
            "contributed": parse_money(registered.get("contributed_capital")),
        },
        "revenue": {
            "range": facts.get("revenue_range"),
            "range_detail": _clean(size_cards.get("revenue")),
            "financial_year_end": facts.get("financial_year_end"),
            "ebitda_change_pct": facts.get("ebitda_change_pct"),
            "networth_change_pct": facts.get("networth_change_pct"),
        },
        "key_metrics": _key_metrics(html),
        "score": _score(soup),
        "last_agm_date": facts.get("last_agm_date") or parse_date(registered.get("agm")),
        "last_updated": last_updated,
        "directors": directors,
        "locations": locations,
        "financials": financials,
        "charges": charges,
        "connected_companies": connected,
        "subsidiaries": subsidiaries,
    }


# ---- director page --------------------------------------------------------------

def parse_director(html, din):
    """The director page: profile cards + every board seat."""
    soup = _soup(html)
    name = _clean(_text(soup.find("h1")))

    cards = {}
    marker = soup.find(string=re.compile(r"^\s*More Details\s*$"))
    if marker:
        section = marker.find_parent("div")
        if section is not None:
            section = section.parent or section
            text = _text(section, sep="\n")
            for label, key in (("Active business association", "active_directorships_count"),
                               ("People associations", "people_associations_count"),
                               ("Longest association", "longest_association_years")):
                match = re.search(re.escape(label) + r"\s*\n\s*([\d.]+)", text)
                cards[key] = parse_number(match.group(1)) if match else None

    directorships = []
    for table in soup.find_all("table"):
        headers = [_text(th) for th in table.find_all("th")]
        if headers[:2] != ["Business Name", "Incorporation Date"]:
            continue
        for row in table.find_all("tr")[1:]:
            cells = row.find_all("td")
            if len(cells) < 7:
                continue
            anchor = cells[0].find("a")
            href = anchor.get("href") if anchor else None
            directorships.append({
                "company_name": _clean(_text(cells[0])),
                "cin": _id_from_href(href),
                "link": _link(href),
                "incorporation_date": parse_date(_text(cells[1])),
                "industry": _clean(_text(cells[2])),
                "status": _clean(_text(cells[3])),
                "appointed_on": parse_date(_text(cells[4])),
                "as_on": parse_date(_text(cells[5])),
                "designation": _clean(_text(cells[6])),
            })
        break

    def _int(value):
        return int(value) if value is not None else None

    return {
        "din": din,
        "name": name,
        "link": f"{SITE}/director/{din}",
        "active_directorships_count": _int(cards.get("active_directorships_count")),
        "people_associations_count": _int(cards.get("people_associations_count")),
        "longest_association_years": _int(cards.get("longest_association_years")),
        "directorships": directorships,
        "directorships_count": len(directorships),
    }


# ---- browse directory ------------------------------------------------------------

def parse_companylist(html):
    """One /companylist page -> (rows, has_next_page). 30 rows per page."""
    soup = _soup(html)
    rows = []
    table = soup.find("table", id="data-table") or soup.find("table")
    if table is not None:
        for row in table.find_all("tr")[1:]:
            cells = row.find_all("td")
            if len(cells) < 4:
                continue
            anchor = cells[0].find("a")
            href = anchor.get("href") if anchor else None
            year = parse_number(_text(cells[1]))
            rows.append({
                "name": _clean(_text(cells[0])),
                "cin": _id_from_href(href),
                "link": _link(href),
                "incorporation_year": int(year) if year is not None else None,
                "industry": _clean(_text(cells[2])),
                "status": _clean(_text(cells[3])),
            })
    next_button = soup.find("a", id="next-btn")
    return rows, next_button is not None
