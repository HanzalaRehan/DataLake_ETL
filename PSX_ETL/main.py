#!/usr/bin/env python3
"""
PSX Historical Data Scraper
============================
Scrapes all-symbol daily data from https://dps.psx.com.pk/historical
for every trading date from 2021-04-30 to today.

Output: psx_historical.csv
Columns: date, symbol, ldcp, open, high, low, close, volume

Usage:
    pip install requests beautifulsoup4 pandas tqdm
    python psx_scraper.py

Notes:
  - The PSX site returns one page of results per date (all symbols).
  - The page uses a POST form: POST /historical  with body: date=DD-MM-YYYY
  - Results span multiple HTML table pages — handled via ?page=N param.
  - Rate-limiting: 1 second delay between date requests (configurable).
  - Progress is saved to psx_historical_partial.csv after each date,
    so you can safely resume if interrupted.
  - Already-scraped dates are skipped on resume.
"""

import requests
import pandas as pd
import time
import os
import sys
from bs4 import BeautifulSoup
from datetime import date, timedelta
from tqdm import tqdm

# ── Configuration ────────────────────────────────────────────────────────────
START_DATE   = date(2021, 4, 30)
END_DATE     = date.today()
OUTPUT_FILE  = "outputs/psx_historical.csv"
PARTIAL_FILE = "outputs/psx_historical_partial.csv"
DELAY_SECS   = 1.0          # polite delay between date requests
MAX_RETRIES  = 3             # retries per request on failure
BASE_URL     = "https://dps.psx.com.pk/historical"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept":          "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5",
    "Referer":         "https://dps.psx.com.pk/",
}
# ─────────────────────────────────────────────────────────────────────────────


def make_session() -> requests.Session:
    s = requests.Session()
    s.headers.update(HEADERS)
    return s


def fetch_page(session: requests.Session, date_str: str, page: int = 1) -> str | None:
    """POST to PSX historical endpoint for a given date and page number."""
    payload = {"date": date_str}
    url = f"{BASE_URL}?page={page}" if page > 1 else BASE_URL

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            resp = session.post(url, data=payload, timeout=30)
            resp.raise_for_status()
            return resp.text
        except requests.RequestException as e:
            if attempt == MAX_RETRIES:
                print(f"\n  ⚠  Failed {date_str} page {page} after {MAX_RETRIES} attempts: {e}")
                return None
            time.sleep(2 ** attempt)  # exponential backoff


def parse_table(html: str) -> list[dict]:
    """Parse the equities table from one page of HTML."""
    soup = BeautifulSoup(html, "html.parser")
    rows = []

    table = soup.find("table")
    if not table:
        return rows

    headers = [th.get_text(strip=True).lower() for th in table.find_all("th")]
    if not headers:
        return rows

    for tr in table.find("tbody").find_all("tr") if table.find("tbody") else table.find_all("tr")[1:]:
        cols = [td.get_text(strip=True) for td in tr.find_all("td")]
        if len(cols) < len(headers):
            continue
        row = dict(zip(headers, cols))
        rows.append(row)

    return rows


def get_last_page(html: str) -> int:
    """Find the last pagination page number from the HTML."""
    soup = BeautifulSoup(html, "html.parser")

    # Look for pagination links — PSX uses Bootstrap pagination
    pagination = soup.find("ul", class_="pagination")
    if not pagination:
        return 1

    page_nums = []
    for a in pagination.find_all("a", href=True):
        href = a["href"]
        if "page=" in href:
            try:
                p = int(href.split("page=")[-1].split("&")[0])
                page_nums.append(p)
            except ValueError:
                pass
        # also try text content
        try:
            page_nums.append(int(a.get_text(strip=True)))
        except ValueError:
            pass

    return max(page_nums) if page_nums else 1


def scrape_date(session: requests.Session, d: date) -> list[dict]:
    """Scrape all pages for a single trading date. Returns list of row dicts."""
    date_str = d.strftime("%d-%m-%Y")
    all_rows = []

    # Fetch page 1 to discover total pages
    html = fetch_page(session, date_str, page=1)
    if not html:
        return all_rows

    first_rows = parse_table(html)
    if not first_rows:
        return all_rows  # non-trading day / no data

    all_rows.extend(first_rows)

    last_page = get_last_page(html)

    for page in range(2, last_page + 1):
        html = fetch_page(session, date_str, page=page)
        if html:
            all_rows.extend(parse_table(html))

    # Tag each row with the date
    for row in all_rows:
        row["date"] = d.isoformat()

    return all_rows


def normalise_columns(df: pd.DataFrame) -> pd.DataFrame:
    """
    Rename raw PSX column names to the canonical output schema.
    PSX table headers (as of 2024): SYMBOL, LDCP, OPEN, HIGH, LOW, CLOSE, VOLUME
    (sometimes also: CHANGE, CHANGE(%), TURNOVER)
    """
    rename_map = {}
    for col in df.columns:
        c = col.strip().lower()
        if c in ("symbol", "code"):          rename_map[col] = "symbol"
        elif c in ("ldcp", "prev. close"):   rename_map[col] = "ldcp"
        elif c == "open":                     rename_map[col] = "open"
        elif c == "high":                     rename_map[col] = "high"
        elif c == "low":                      rename_map[col] = "low"
        elif c in ("close", "current"):       rename_map[col] = "close"
        elif c in ("volume", "turnover"):     rename_map[col] = "volume"

    df = df.rename(columns=rename_map)

    target_cols = ["date", "symbol", "ldcp", "open", "high", "low", "close", "volume"]
    present = [c for c in target_cols if c in df.columns]
    return df[present]


def trading_dates(start: date, end: date) -> list[date]:
    """Generate weekdays between start and end (inclusive)."""
    dates = []
    current = start
    while current <= end:
        if current.weekday() < 5:  # Mon–Fri
            dates.append(current)
        current += timedelta(days=1)
    return dates


def load_done_dates() -> set[str]:
    """Load already-scraped dates from the partial CSV."""
    if not os.path.exists(PARTIAL_FILE):
        return set()
    try:
        df = pd.read_csv(PARTIAL_FILE, usecols=["date"])
        return set(df["date"].unique())
    except Exception:
        return set()


def append_to_csv(rows: list[dict], file: str, write_header: bool):
    """Append a list of row dicts to the CSV file."""
    if not rows:
        return
    df = pd.DataFrame(rows)
    df = normalise_columns(df)
    df.to_csv(file, mode="a", header=write_header, index=False)


def main():
    print(f"PSX Historical Scraper")
    print(f"Date range : {START_DATE} → {END_DATE}")
    print(f"Output     : {OUTPUT_FILE}")
    print()

    all_dates    = trading_dates(START_DATE, END_DATE)
    done_dates   = load_done_dates()
    todo_dates   = [d for d in all_dates if d.isoformat() not in done_dates]

    if not todo_dates:
        print("All dates already scraped. Finalising output…")
    else:
        print(f"Dates to scrape : {len(todo_dates)}  (skipping {len(done_dates)} already done)")
        print()

        session       = make_session()
        write_header  = not os.path.exists(PARTIAL_FILE)

        for d in tqdm(todo_dates, desc="Scraping dates", unit="day"):
            rows = scrape_date(session, d)
            if rows:
                append_to_csv(rows, PARTIAL_FILE, write_header)
                write_header = False
            time.sleep(DELAY_SECS)

        print(f"\nPartial data saved to {PARTIAL_FILE}")

    # Merge partial → final
    if os.path.exists(PARTIAL_FILE):
        df = pd.read_csv(PARTIAL_FILE)
        df = df.drop_duplicates()
        df = df.sort_values(["date", "symbol"])
        df.to_csv(OUTPUT_FILE, index=False)
        print(f"Final CSV saved to  : {OUTPUT_FILE}")
        print(f"Total rows          : {len(df):,}")
        print(f"Unique dates        : {df['date'].nunique():,}")
        print(f"Unique symbols      : {df['symbol'].nunique():,}")
    else:
        print("No data was collected.")


if __name__ == "__main__":
    main()