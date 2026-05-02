"""
PBS Pakistan Imports — Unified Silver Layer
============================================
Reads ALL *_bronze.csv files from the outputs/ directory (from ALL three
formats) and produces a single clean long-format CSV with a consistent schema.

Bronze schemas handled:
  Format 1 cols: {year}_quantity, {year}_value_000rs
  Format 2/3 cols: {year}_jun_quantity, {year}_jun_value_000rs,
                   {year}_cum_quantity,  {year}_cum_value_000rs

Silver output: one row per (hs_code, country, fiscal_year)

Usage:
  python silver.py --bronze outputs/ --out outputs/silver_all_years.csv
"""

import re
import csv
import sys
import argparse
from pathlib import Path

# ── Country name standardisation ─────────────────────────────────────────────
COUNTRY_ALIASES = {
    'U.S.America':                'United States',
    'U.S.A':                      'United States',
    'USA':                        'United States',
    'United States of America':   'United States',
    'Dubai':                      'United Arab Emirates',
    'UAE':                        'United Arab Emirates',
    'U.A.E':                      'United Arab Emirates',
    'United Arab Emirate':        'United Arab Emirates',
    'Iran ( Islamic R.)':         'Iran',
    'Iran(Islamic Republic)':     'Iran',
    'Iran (Islamic Republic Of)': 'Iran',
    'U.R.of Tanzania':            'Tanzania',
    'U.R.Of Tanzania':            'Tanzania',
    'Hong Kong S.A.Re.Chi':       'Hong Kong SAR',
    'Egypt(U.A.R.)':              'Egypt',
    'Egypt(U.A.R)':               'Egypt',
    'Korea, Republic of':         'South Korea',
    'Korea Republic Of':          'South Korea',
    'O.Asia(Tai.For.Pe.Ki':       'Other Asia',
    'O.Asia(Tai.For.Pe.Ki.':      'Other Asia',
    'Europien Union':             'European Union',
    'D.R.of Congo':               'DR Congo',
    'D.R.Of Congo':               'DR Congo',
    'Congo, Republic of':         'Congo',
    'Russian Federation':         'Russia',
    'Kyrgyzstan/Kyrgyz R.':       'Kyrgyzstan',
    'U.K.':                       'United Kingdom',
    'Netherlands Antilles':       'Netherlands Antilles',
}

UNIT_MAP = {
    'NOS': 'NO', 'KGS': 'KG', 'MTS': 'MT',
    'LTRE': 'LTR', 'LTRS': 'LTR',
}

SILVER_FIELDS = [
    'hs_code', 'commodity', 'unit', 'country',
    'fiscal_year', 'fiscal_year_start',
    # Format 1 annual totals (no month breakdown)
    'annual_quantity', 'annual_value_000rs', 'annual_value_rs',
    # Format 2/3 monthly (June)
    'jun_quantity', 'jun_value_000rs', 'jun_value_rs',
    # Format 2/3 cumulative (full year Jul–Jun)
    'cum_quantity', 'cum_value_000rs', 'cum_value_rs',
    # Metadata
    'data_format', 'notes', 'source_file',
]


# ── Helpers ───────────────────────────────────────────────────────────────────

def normalise_country(name: str) -> str:
    if not name:
        return 'Unknown'
    name = re.sub(r'\s+', ' ', name).strip()
    return COUNTRY_ALIASES.get(name, name)

def normalise_commodity(name: str) -> str:
    return re.sub(r'\s+', ' ', str(name)).strip().upper() if name else ''

def normalise_unit(unit: str) -> str:
    u = str(unit).strip().upper()
    return UNIT_MAP.get(u, u)

def validate_hs(hs: str) -> str:
    try:
        return str(int(str(hs).strip())).zfill(8)
    except (ValueError, TypeError):
        return str(hs).strip()

def to_int(val) -> int | None:
    if val is None or str(val).strip() == '':
        return None
    try:
        return int(str(val).replace(',', '').strip())
    except ValueError:
        return None

def fy_start(fy: str) -> int:
    m = re.match(r'(\d{4})', fy)
    return int(m.group(1)) if m else 0


# ── Bronze schema detection ───────────────────────────────────────────────────

def detect_schema(fieldnames: list[str]) -> tuple[str, list]:
    """
    Returns ('format1', [(yr, qty_col, val_col), ...])
         or ('format23', [(yr, jq, jv, cq, cv), ...])
    """
    f1_years, f23_years = {}, {}

    for col in fieldnames:
        # Format 1:  2002-2003_quantity / 2002-2003_value_000rs
        m1 = re.match(r'^(\d{4}-\d{4})_(quantity|value_000rs|value_000_rs)$', col)
        if m1:
            yr, kind = m1.group(1), m1.group(2)
            f1_years.setdefault(yr, {})[kind.replace('value_000_rs', 'value_000rs')] = col
            continue

        # Format 2/3:  2014-2015_jun_quantity etc.
        m23 = re.match(
            r'^(\d{4}-\d{4})_(jun_quantity|jun_value_000rs|cum_quantity|cum_value_000rs)$', col
        )
        if m23:
            yr, kind = m23.group(1), m23.group(2)
            f23_years.setdefault(yr, {})[kind] = col

    if f23_years:
        result = []
        for yr in sorted(f23_years):
            c = f23_years[yr]
            result.append((
                yr,
                c.get('jun_quantity'),
                c.get('jun_value_000rs'),
                c.get('cum_quantity'),
                c.get('cum_value_000rs'),
            ))
        return 'format23', result

    if f1_years:
        result = []
        for yr in sorted(f1_years):
            c = f1_years[yr]
            result.append((
                yr,
                c.get('quantity'),
                c.get('value_000rs'),
            ))
        return 'format1', result

    return 'unknown', []


# ── Per-file processing ───────────────────────────────────────────────────────

def process_bronze(path: Path) -> list[dict]:
    records = []
    seen = set()

    # Half-year file note
    is_half_year = '2018july_december' in path.name.lower() or 'p6m' in path.name.lower()
    notes = 'Jul-Dec half year only' if is_half_year else ''

    with open(path, newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames or []
        schema_type, year_cols = detect_schema(fieldnames)

        if schema_type == 'unknown':
            print(f"    ⚠  Could not detect schema in {path.name}, skipping.")
            return []

        for row in reader:
            hs        = validate_hs(row.get('hs_code', ''))
            commodity = normalise_commodity(row.get('commodity', ''))
            unit      = normalise_unit(row.get('unit', ''))
            country   = normalise_country(row.get('country', ''))

            if schema_type == 'format1':
                for (yr, qty_col, val_col) in year_cols:
                    qty = to_int(row.get(qty_col))
                    val = to_int(row.get(val_col))
                    if qty is None and val is None:
                        continue
                    key = (hs, country, yr)
                    if key in seen:
                        continue
                    seen.add(key)
                    records.append({
                        'hs_code':            hs,
                        'commodity':          commodity,
                        'unit':               unit,
                        'country':            country,
                        'fiscal_year':        yr,
                        'fiscal_year_start':  fy_start(yr),
                        'annual_quantity':    '' if qty is None else qty,
                        'annual_value_000rs': '' if val is None else val,
                        'annual_value_rs':    '' if val is None else val * 1000,
                        'jun_quantity':       '',
                        'jun_value_000rs':    '',
                        'jun_value_rs':       '',
                        'cum_quantity':       '',
                        'cum_value_000rs':    '',
                        'cum_value_rs':       '',
                        'data_format':        'format1_annual',
                        'notes':              notes,
                        'source_file':        path.name,
                    })

            else:  # format23
                for (yr, jq_col, jv_col, cq_col, cv_col) in year_cols:
                    jq = to_int(row.get(jq_col))
                    jv = to_int(row.get(jv_col))
                    cq = to_int(row.get(cq_col))
                    cv = to_int(row.get(cv_col))
                    if all(x is None for x in [jq, jv, cq, cv]):
                        continue
                    key = (hs, country, yr)
                    if key in seen:
                        continue
                    seen.add(key)
                    records.append({
                        'hs_code':            hs,
                        'commodity':          commodity,
                        'unit':               unit,
                        'country':            country,
                        'fiscal_year':        yr,
                        'fiscal_year_start':  fy_start(yr),
                        'annual_quantity':    '',
                        'annual_value_000rs': '',
                        'annual_value_rs':    '',
                        'jun_quantity':       '' if jq is None else jq,
                        'jun_value_000rs':    '' if jv is None else jv,
                        'jun_value_rs':       '' if jv is None else jv * 1000,
                        'cum_quantity':       '' if cq is None else cq,
                        'cum_value_000rs':    '' if cv is None else cv,
                        'cum_value_rs':       '' if cv is None else cv * 1000,
                        'data_format':        'format23_jun_cum',
                        'notes':              notes,
                        'source_file':        path.name,
                    })

    return records


# ── Entry point ───────────────────────────────────────────────────────────────

def main():
    ap = argparse.ArgumentParser(description='Consolidate all bronze CSVs into unified silver CSV.')
    ap.add_argument('--bronze', required=True, help='Bronze CSV file or directory of *_bronze.csv files')
    ap.add_argument('--out', default='outputs/silver_all_years.csv', help='Output silver CSV path')
    args = ap.parse_args()

    p = Path(args.bronze)
    files = sorted(p.glob('*_bronze.csv')) if p.is_dir() else [p] if p.is_file() else []

    if not files:
        print('No *_bronze.csv files found.')
        sys.exit(1)

    all_records = []
    for f in files:
        print(f"  Reading {f.name} …")
        recs = process_bronze(f)
        print(f"    → {len(recs):,} records (schema detected from columns)")
        all_records.extend(recs)

    # Sort: fiscal year start → HS code → country
    all_records.sort(key=lambda r: (r['fiscal_year_start'], r['hs_code'], r['country']))

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    with open(out_path, 'w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=SILVER_FIELDS)
        w.writeheader()
        w.writerows(all_records)

    # Summary
    years = sorted(set(r['fiscal_year'] for r in all_records))
    hs_codes = set(r['hs_code'] for r in all_records)
    countries = set(r['country'] for r in all_records)
    fmt_counts = {}
    for r in all_records:
        fmt_counts[r['data_format']] = fmt_counts.get(r['data_format'], 0) + 1

    print(f"\n  ✓  Silver CSV: {len(all_records):,} rows → {out_path}")
    print(f"  Coverage   : {years[0] if years else '?'} → {years[-1] if years else '?'}")
    print(f"  Fiscal yrs : {len(years)}")
    print(f"  HS codes   : {len(hs_codes)}")
    print(f"  Countries  : {len(countries)}")
    print(f"  By format  : {fmt_counts}")
    print('\nDone.')


if __name__ == '__main__':
    main()
