#!/usr/bin/env python3
"""
PSX Historical Data Scraper — Playwright Edition (JS-rendered fallback)
========================================================================
Use this if psx_scraper.py returns 0 rows on trading days
(i.e. the site loads table data via JavaScript).

Prerequisites:
    pip install playwright pandas
    playwright install chromium

Usage:
    python psx_scraper_playwright.py
    python psx_scraper_playwright.py --start-date 2023-01-01 --headless false
"""

import asyncio
import pandas as pd
from playwright.async_api import async_playwright, Page
from datetime import date, timedelta
from pathlib import Path
import argparse
import logging
import time

logging.basicConfig(level=logging.INFO, format="%(asctime)s  %(levelname)-7s  %(message)s", datefmt="%H:%M:%S")
log = logging.getLogger(__name__)

BASE_URL      = "https://dps.psx.com.pk/historical"
OUTPUT_FILE   = "outputs/psx_historical_data.csv"
PROGRESS_FILE = "psx_scraper_progress.txt"


def date_range(start: date, end: date):
    d = start
    while d <= end:
        yield d
        d += timedelta(days=1)


def load_progress() -> date | None:
    if Path(PROGRESS_FILE).exists():
        try:
            return date.fromisoformat(Path(PROGRESS_FILE).read_text().strip())
        except Exception:
            pass
    return None


def save_progress(d: date):
    Path(PROGRESS_FILE).write_text(d.isoformat())


def clean(s: str) -> str:
    return s.replace(",", "").strip() or None


async def scrape_date_playwright(page: Page, target_date: date) -> list[dict]:
    date_str = target_date.strftime("%d %b %Y")   # "30 Apr 2021"
    url = f"{BASE_URL}?date={date_str.replace(' ', '+')}&page=1"

    all_rows = []
    current_page = 1

    while True:
        nav_url = f"{BASE_URL}?date={date_str.replace(' ', '+')}&page={current_page}"
        await page.goto(nav_url, wait_until="networkidle", timeout=30000)

        # Wait for table or "no data" message
        try:
            await page.wait_for_selector("table, .no-data, .empty", timeout=10000)
        except Exception:
            break

        # Parse rows via JS evaluation (fast, no HTML download needed)
        rows = await page.evaluate("""() => {
            const table = document.querySelector('table');
            if (!table) return [];
            const rows = [];
            table.querySelectorAll('tbody tr').forEach(tr => {
                const cells = [...tr.querySelectorAll('td')].map(td => td.innerText.trim());
                if (cells.length >= 7) {
                    // skip leading index cell if not alphabetic
                    let c = cells;
                    if (!/^[A-Za-z]/.test(c[0])) c = c.slice(1);
                    if (c.length >= 7) {
                        rows.push({
                            symbol: c[0],
                            ldcp:   c[1].replace(/,/g,''),
                            open:   c[2].replace(/,/g,''),
                            high:   c[3].replace(/,/g,''),
                            low:    c[4].replace(/,/g,''),
                            close:  c[5].replace(/,/g,''),
                            volume: c[6].replace(/,/g,''),
                        });
                    }
                }
            });
            return rows;
        }""")

        if not rows:
            break

        all_rows.extend(rows)

        # Check for next page
        has_next = await page.evaluate("""() => {
            const links = [...document.querySelectorAll('a[href*="page="]')];
            const currentPage = new URL(window.location.href).searchParams.get('page') || '1';
            return links.some(a => {
                const p = new URL(a.href).searchParams.get('page');
                return p && parseInt(p) > parseInt(currentPage);
            });
        }""")

        if not has_next:
            break

        current_page += 1
        await asyncio.sleep(0.4)

    for row in all_rows:
        row["date"] = target_date.strftime("%Y-%m-%d")

    return all_rows


async def main_async(args):
    start = date.fromisoformat(args.start_date)
    end   = date.fromisoformat(args.end_date)

    resume_from = None if args.no_resume else load_progress()
    effective_start = (resume_from + timedelta(days=1)) if (resume_from and resume_from >= start) else start

    write_header = not Path(args.output).exists() or args.no_resume or (resume_from is None)

    log.info(f"Date range : {effective_start}  →  {end}")

    total_dates = (end - effective_start).days + 1
    done = 0
    total_rows = 0

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=(args.headless.lower() != "false"))
        page    = await browser.new_page()
        await page.set_extra_http_headers({"Accept-Language": "en-US,en;q=0.9"})

        for d in date_range(effective_start, end):
            done += 1
            pct = done / total_dates * 100
            log.info(f"[{pct:5.1f}%] Scraping {d} …")

            try:
                rows = await scrape_date_playwright(page, d)
            except Exception as exc:
                log.warning(f"Error on {d}: {exc}. Skipping.")
                rows = []

            if rows:
                df = pd.DataFrame(rows, columns=["date", "symbol", "ldcp", "open", "high", "low", "close", "volume"])
                df.to_csv(args.output, mode="a", index=False, header=write_header)
                write_header = False
                total_rows += len(rows)
                log.info(f"          ✓ {len(rows):4d} records  (total: {total_rows:,})")
            else:
                log.info("          – No data")

            save_progress(d)
            await asyncio.sleep(args.delay)

        await browser.close()

    log.info(f"Done!  {total_rows:,} rows  →  {args.output}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--start-date", default="2021-04-30")
    parser.add_argument("--end-date",   default=date.today().isoformat())
    parser.add_argument("--output",     default=OUTPUT_FILE)
    parser.add_argument("--delay",      type=float, default=1.0)
    parser.add_argument("--no-resume",  action="store_true")
    parser.add_argument("--headless",   default="true", help="'false' to see browser")
    args = parser.parse_args()
    asyncio.run(main_async(args))


if __name__ == "__main__":
    main()