"""
Scrapes daily fund figures from multiple ETF provider websites and appends
them to a single CSV log — one row per (date, fund, field).

Currently tracks:
    EETH  (proshares.com) -> CME Ether Future contracts
    BITO  (proshares.com) -> CME Bitcoin Future contracts, Coinbase Bitcoin Future contracts
    BITB  (bitbetf.com)   -> Shares Outstanding, Net Assets (AUM), Bitcoin in Trust, Bitcoin per Share

Two site "shapes" are handled:
  - TABLE_ROW_TARGETS: data sits in an HTML <table> with a Description
    column we match on, and the value is a specific <td> in that row.
  - LABEL_VALUE_TARGETS: data is a label ("Shares Outstanding") immediately
    followed by its value ("67,620,000") when you read the page's text
    top-to-bottom -- common on marketing sites built with headings/CMS
    fields rather than tables.

Usage:
    python scrape_funds.py

Schedule daily with cron (runs at 6:30am):
    30 6 * * * /usr/bin/python3 /path/to/scrape_funds.py >> /path/to/scrape_funds.log 2>&1
"""

import csv
import re
from datetime import datetime
from pathlib import Path

import requests
from bs4 import BeautifulSoup

OUTFILE = Path(__file__).parent / "fund_data_log.csv"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    )
}

NUMERIC_RE = re.compile(r"^\$?-?[\d,]+(\.\d+)?%?$")

# Matches things like "as of 7/20/2026", "As of 07/20/2026", "Data as of 07/19/2026"
AS_OF_RE = re.compile(r"as of\s+(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})", re.IGNORECASE)


def find_as_of_date(soup: BeautifulSoup, near_text: str = None) -> str:
    """Best-effort extraction of the page's self-reported 'as of' date.
    If near_text is given, prefer the as-of date that appears closest
    before that text in the page; otherwise return the first one found."""
    full_text = soup.get_text("\n")
    matches = list(AS_OF_RE.finditer(full_text))
    if not matches:
        return ""

    if near_text:
        anchor_idx = full_text.find(near_text)
        if anchor_idx != -1:
            best = None
            for m in matches:
                if m.start() <= anchor_idx:
                    best = m
                else:
                    break
            if best:
                return best.group(1)

    return matches[0].group(1)

# ---------------------------------------------------------------------------
# Site 1: ProShares -- table-row based (Holdings table, "Shares/Contracts" col)
# ---------------------------------------------------------------------------
TABLE_ROW_TARGETS = [
    {
        "fund": "EETH",
        "url": "https://www.proshares.com/our-etfs/strategic/eeth",
        "holdings": [
            {"label": "CME Ether Future", "match": "CME ETHER FUTURE", "value_col": 5},
        ],
    },
    {
        "fund": "BITO",
        "url": "https://www.proshares.com/our-etfs/strategic/bito",
        "holdings": [
            {"label": "CME Bitcoin Future", "match": "CME BITCOIN FUT", "value_col": 5},
            {"label": "Coinbase Bitcoin Future", "match": "COINBASE BIT FUT", "value_col": 5},
        ],
    },
    {
        "fund": "BRRR",
        "url": "https://coinshares.com/us/etf/brrr/",
        "holdings": [
            {"label": "Bitcoin Shares", "match": "XBTUSD", "value_col": 2},
            {"label": "Cash & Other", "match": "Cash&Other", "value_col": 2},
        ],
    },
]

# ---------------------------------------------------------------------------
# Site 2: BITB (bitbetf.com) -- label immediately followed by value in the
# page's rendered text order.
# ---------------------------------------------------------------------------
LABEL_VALUE_TARGETS = [
    {
        "fund": "BITB",
        "url": "https://bitbetf.com/",
        "fields": [
            {"label": "Shares Outstanding", "field_label": "Shares Outstanding"},
            {"label": "Net Assets (AUM)", "field_label": "Net Assets (AUM)"},
            {"label": "Bitcoin in Trust", "field_label": "Bitcoin in Trust"},
            {"label": "Bitcoin per Share", "field_label": "Bitcoin per Share"},
        ],
    },
    {
        "fund": "BTC",  # Grayscale Bitcoin Mini Trust ETF
        "url": "https://etfs.grayscale.com/btc",
        "fields": [
            {"label": "Shares Outstanding", "field_label": "SHARES OUTSTANDING"},
            {"label": "Total Bitcoin in Trust", "field_label": "TOTAL BITCOIN IN TRUST"},
            {"label": "Bitcoin per Share", "field_label": "BITCOIN PER SHARE"},
        ],
    },
]

# ---------------------------------------------------------------------------
# Site 3: iShares (ishares.com) -- label, then value, then its own inline
# "as of <date>" line right after -- e.g. "Shares Outstanding / 1,311,240,000
# / as of Jun 29, 2026". This gives a per-field as-of date directly, so we
# don't need to fall back to a page-wide guess.
# ---------------------------------------------------------------------------
ISHARES_TARGETS = [
    {
        "fund": "IBIT",
        "url": "https://www.ishares.com/us/products/333011/ishares-bitcoin-trust-etf",
        "fields": [
            {"label": "Shares Outstanding", "field_label": "Shares Outstanding"},
            {"label": "Net Assets of Fund", "field_label": "Net Assets of Fund"},
            {"label": "Basket Bitcoin Amount", "field_label": "Basket Bitcoin Amount"},
        ],
    },
]

# ---------------------------------------------------------------------------
# Site 4: VanEck (vaneck.com) -- simple 2-column key/value <table> rows,
# e.g. <tr><td>Shares Outstanding</td><td>57,850,000</td></tr>. A page-level
# "as of <date>" heading (e.g. "ETF Statistics as of 06/18/2026") covers all
# fields on the page.
# ---------------------------------------------------------------------------
KEY_VALUE_TABLE_TARGETS = [
    {
        "fund": "HODL",
        "url": "https://www.vaneck.com/us/en/investments/bitcoin-etf-hodl/overview/",
        "fields": [
            {"label": "Shares Outstanding", "field_label": "Shares Outstanding"},
            {"label": "Bitcoin in Trust", "field_label": "Bitcoin in Trust"},
            {"label": "Bitcoin per 1,000 Shares", "field_label": "Bitcoin per 1,000 Shares"},
        ],
    },
]


def clean_number(raw: str):
    """Strip $ , % and return an int if whole, else a float. None if unparseable."""
    digits = re.sub(r"[^\d.]", "", raw)
    if not digits or digits == ".":
        return None
    return float(digits) if "." in digits else int(digits)


# --- Parser: ProShares-style tables -----------------------------------------
def parse_proshares_row(soup: BeautifulSoup, match: str, value_col: int = 5):
    target_row = None
    for row in soup.find_all("tr"):
        if match in row.get_text():
            target_row = row
            break
    if target_row is None:
        raise RuntimeError(f"Could not find a holdings row matching {match!r}.")

    cells = [c.get_text(strip=True) for c in target_row.find_all("td")]
    if len(cells) <= value_col:
        raise RuntimeError(f"Unexpected row shape for {match!r}, got cells: {cells}")

    raw = cells[value_col]
    value = clean_number(raw)
    if value is None:
        raise RuntimeError(f"Could not parse a number from {raw!r} (match={match!r}).")
    as_of = find_as_of_date(soup, near_text="Holdings")
    return value, raw, as_of


# --- Parser: label-immediately-followed-by-value pages -----------------------
def parse_label_value(soup: BeautifulSoup, label: str):
    lines = [line.strip() for line in soup.get_text("\n").split("\n") if line.strip()]
    for i, line in enumerate(lines):
        if line == label and i + 1 < len(lines):
            candidate = lines[i + 1]
            if NUMERIC_RE.match(candidate):
                value = clean_number(candidate)
                if value is not None:
                    as_of = find_as_of_date(soup, near_text=label)
                    return value, candidate, as_of
    raise RuntimeError(f"Could not find a numeric value following label {label!r}.")


# --- Parser: label -> value -> inline "as of <date>" (iShares-style) --------
def parse_label_value_inline_asof(soup: BeautifulSoup, label: str):
    lines = [line.strip() for line in soup.get_text("\n").split("\n") if line.strip()]
    for i, line in enumerate(lines):
        if line == label and i + 1 < len(lines):
            candidate = lines[i + 1]
            if NUMERIC_RE.match(candidate):
                value = clean_number(candidate)
                if value is None:
                    continue
                as_of = ""
                if i + 2 < len(lines):
                    m = AS_OF_RE.search(lines[i + 2])
                    if m:
                        as_of = m.group(1)
                return value, candidate, as_of
    raise RuntimeError(f"Could not find a numeric value following label {label!r}.")


# --- Parser: simple 2-column key/value <table> rows (VanEck-style) ----------
def parse_key_value_table(soup: BeautifulSoup, label: str):
    for row in soup.find_all("tr"):
        cells = row.find_all(["td", "th"])
        if len(cells) == 2:
            key = cells[0].get_text(strip=True)
            if key == label:
                raw = cells[1].get_text(strip=True)
                value = clean_number(raw)
                if value is not None:
                    as_of = find_as_of_date(soup, near_text=label)
                    return value, raw, as_of
    raise RuntimeError(f"Could not find a 2-column table row matching label {label!r}.")


def fetch_soup(url: str) -> BeautifulSoup:
    resp = requests.get(url, headers=HEADERS, timeout=20)
    resp.raise_for_status()
    return BeautifulSoup(resp.text, "html.parser")


def append_rows(rows: list[dict]) -> None:
    file_exists = OUTFILE.exists()
    with open(OUTFILE, "a", newline="") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=[
                "timestamp",
                "date",
                "fund",
                "field",
                "value",
                "raw_text",
                "as_of_date",
            ],
        )
        if not file_exists:
            writer.writeheader()
        writer.writerows(rows)


def main():
    now = datetime.now()
    rows = []

    # ProShares sites
    for target in TABLE_ROW_TARGETS:
        soup = fetch_soup(target["url"])
        for holding in target["holdings"]:
            value, raw, as_of = parse_proshares_row(soup, holding["match"], holding.get("value_col", 5))
            rows.append(
                {
                    "timestamp": now.isoformat(timespec="seconds"),
                    "date": now.date().isoformat(),
                    "fund": target["fund"],
                    "field": holding["label"],
                    "value": value,
                    "raw_text": raw,
                    "as_of_date": as_of,
                }
            )
            print(f"{target['fund']} / {holding['label']}: {value} (as of {as_of})")

    # Label/value sites (e.g. BITB, Grayscale)
    for target in LABEL_VALUE_TARGETS:
        soup = fetch_soup(target["url"])
        for field in target["fields"]:
            value, raw, as_of = parse_label_value(soup, field["field_label"])
            rows.append(
                {
                    "timestamp": now.isoformat(timespec="seconds"),
                    "date": now.date().isoformat(),
                    "fund": target["fund"],
                    "field": field["label"],
                    "value": value,
                    "raw_text": raw,
                    "as_of_date": as_of,
                }
            )
            print(f"{target['fund']} / {field['label']}: {value} (as of {as_of})")

    # iShares-style sites (inline as-of date per field)
    for target in ISHARES_TARGETS:
        soup = fetch_soup(target["url"])
        for field in target["fields"]:
            value, raw, as_of = parse_label_value_inline_asof(soup, field["field_label"])
            rows.append(
                {
                    "timestamp": now.isoformat(timespec="seconds"),
                    "date": now.date().isoformat(),
                    "fund": target["fund"],
                    "field": field["label"],
                    "value": value,
                    "raw_text": raw,
                    "as_of_date": as_of,
                }
            )
            print(f"{target['fund']} / {field['label']}: {value} (as of {as_of})")

    # VanEck-style sites (simple key/value tables)
    for target in KEY_VALUE_TABLE_TARGETS:
        soup = fetch_soup(target["url"])
        for field in target["fields"]:
            value, raw, as_of = parse_key_value_table(soup, field["field_label"])
            rows.append(
                {
                    "timestamp": now.isoformat(timespec="seconds"),
                    "date": now.date().isoformat(),
                    "fund": target["fund"],
                    "field": field["label"],
                    "value": value,
                    "raw_text": raw,
                    "as_of_date": as_of,
                }
            )
            print(f"{target['fund']} / {field['label']}: {value} (as of {as_of})")

    append_rows(rows)


if __name__ == "__main__":
    main()
