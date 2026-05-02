"""
PBS Pakistan Import Data — Unified Bronze Extractor
====================================================
Handles ALL three PBS import data formats in one script:

  FORMAT 1 — Wide multi-year columns (2002-03 to 2012-13)
  ─────────────────────────────────────────────────────────
  Files:
    4_imp_2002-03_to_2007-08.pdf      → 6 fiscal years side by side
    5_imp_2008-09_to_2012-13.pdf      → 5 fiscal years side by side
  Layout:  HS | Commodity | Unit | [Qty  Val] x N_years
  Years auto-detected from file header.

  FORMAT 2 — Dual-year comparison with JUN + CUMULATIVE (2013-14 to 2020-21)
  ────────────────────────────────────────────────────────────────────────────
  Files:
    Import-by-commodities-and-countries-2014-15-2013-14.P6M.pdf
    IMPORTS-BY-COMMODITIES-AND-COUNTRIES-2015-2016.txt
    IMPORTS-BY-COMMODITIES-AND-COUNTRIES-PAKISTAN-2016-2017.txt
    IMPORTS-BY-COMMODITIES-AND-COUNTRIES-2017-2018.txt
    imports_commodities_and_countries_2018july_december.txt
    IMPORT-BY-COMMODITIES-AND-COUNTRIES-2020-21.txt
  Layout:  HS | Commodity | Unit | CurYr [JunQty JunVal CumQty CumVal]
                                        | PrvYr [JunQty JunVal CumQty CumVal]
  Years must be supplied via --years argument.

  FORMAT 3 — D-10 structured table PDFs (2021-22 to 2023-24)
  ────────────────────────────────────────────────────────────
  Files:
    D-10_Import-06-2022.pdf
    D-10_Import-06-2023.pdf
    D-10_Import0624.pdf
  Layout:  Same 8-column structure as Format 2 but in structured PDF tables.
  Years must be supplied via --years argument.

Usage
─────
  # Format 1 (years auto-detected):
  python extractor.py --format 1 --pdf input/4_imp_2002-03_to_2007-08.pdf --out outputs/
  python extractor.py --format 1 --pdf input/5_imp_2008-09_to_2012-13.pdf --out outputs/

  # Format 2 (years required):
  python extractor.py --format 2 --pdf input/Import-...-2014-15-2013-14.pdf --years 2014-2015,2013-2014 --out outputs/
  python extractor.py --format 2 --txt input/IMPORTS-...-2015-2016.txt      --years 2015-2016,2014-2015 --out outputs/
  python extractor.py --format 2 --txt input/IMPORTS-...-2016-2017.txt      --years 2016-2017,2015-2016 --out outputs/
  python extractor.py --format 2 --txt input/IMPORTS-...-2017-2018.txt      --years 2017-2018,2016-2017 --out outputs/
  python extractor.py --format 2 --txt input/imports_..._2018july_december.txt --years 2018-2019         --out outputs/
  python extractor.py --format 2 --txt input/IMPORT-...-2020-21.txt         --years 2020-2021,2019-2020 --out outputs/

  # Format 3 (years required):
  python extractor.py --format 3 --pdf input/D-10_Import-06-2022.pdf --years 2021-2022,2020-2021 --out outputs/
  python extractor.py --format 3 --pdf input/D-10_Import-06-2023.pdf --years 2022-2023,2021-2022 --out outputs/
  python extractor.py --format 3 --pdf input/D-10_Import0624.pdf     --years 2023-2024,2022-2023 --out outputs/
"""

import re
import csv
import sys
import argparse
from pathlib import Path

try:
    import fitz          # PyMuPDF
    HAS_PDF = True
except ImportError:
    HAS_PDF = False


# Fiscal years valid for Format 1 (auto-detection)
FORMAT1_YEARS = {
    "2002-2003", "2003-2004", "2004-2005", "2005-2006",
    "2006-2007", "2007-2008", "2008-2009", "2009-2010",
    "2010-2011", "2011-2012", "2012-2013",
}

UNIT_PATTERN = re.compile(
    r'\b(NO|NOS|KG|KGS|MT|MTS|LTR|LTRE|LTRS|DOZ|M3|TON|SET|PRS|GM|SQM|SQY)\b',
    re.IGNORECASE
)

# Lines to always skip
SKIP_RE = [re.compile(p, re.IGNORECASE) for p in [
    r'^\s*$',
    r'^\s*[\*\-=]{3,}\s*$',
    r'IMPORTS\s+BY\s+COMMODIT',
    r'HSCODE\s+COMMODITY',
    r'HS\s*CODE\s+COMMODITY',
    r'QUANTITY\s+(VALUE|PAK|PKR)',
    r'G\s*R\s*A\s*N\s*D\s+T\s*O\s*T\s*A\s*L',
    r'^\s*T\s*O\s*T\s*A\s*L\s*$',
    r'RUPEES\s+IN\s+THOUSANDS',
    r'PKR\s+IN\s+THOUSANDS',
    r'PAK\s+RUPEES\s+IN\s+THOUSANDS',
    r'VALUE\s+IN\s+.*000',
    r'PAGE\s+\d+',
    r'Import by commodities',
    r'Page\s+\d+\s+of',
    r'CUMULATIVE\s+FROM',
    r'^\s*JUN\s+CUMULATIVE',
    r'^\s*2\s*0\s*[12]\s*[0-9]\s*[- ]\s*2\s*0',   # spaced year headers e.g. 2 0 2 0 - 2 0 2 1
    r'JUL\s+\d{4}\s+TO\s+JUN',
    r'D-10\s+IMPORT',
]]


def should_skip(line: str) -> bool:
    for pat in SKIP_RE:
        if pat.search(line):
            return True
    return False


def extract_text_plain(path: Path) -> str:
    """Extract text from PDF (plain layout) or read TXT file."""
    if path.suffix.lower() == '.pdf':
        if not HAS_PDF:
            raise ImportError("Run:  pip install pymupdf")
        pages = []
        with fitz.open(str(path)) as pdf:
            for page in pdf:
                t = page.get_text("text")   
                if t:
                    pages.append(t)
        return '\n'.join(pages)
    return path.read_text(encoding='utf-8', errors='replace')


def extract_text_tabular(path: Path) -> str:
    if not HAS_PDF:
        raise ImportError("Run:  pip install pymupdf")
    all_lines = []
    with fitz.open(str(path)) as pdf:
        for page in pdf:
            blocks = [b for b in page.get_text("blocks") if b[6] == 0 and b[4].strip()]
            blocks.sort(key=lambda b: (round(b[1] / 4) * 4, b[0]))
            for b in blocks:
                for sub in b[4].split('\n'):
                    sub = sub.strip()
                    if sub:
                        all_lines.append(sub)
    return '\n'.join(all_lines)


def to_int_or_none(s: str):
    if s is None:
        return None
    s = str(s).replace(',', '').strip()
    if not s or re.match(r'^[\-\*]+$', s):
        return None
    try:
        return int(s)
    except ValueError:
        return None


def validate_hs(hs: str) -> str:
    try:
        return str(int(str(hs).strip())).zfill(8)
    except (ValueError, TypeError):
        return str(hs).strip().zfill(8)


def valid_country(name: str) -> bool:
    if not name or len(name.strip()) < 2:
        return False
    if re.search(r'QUANTITY|VALUE|HSCODE|HS CODE|PAGE|RUPEES|PKR|\|', name, re.I):
        return False
    if re.match(r'^[\d\s,\-\*\.]+$', name.strip()):
        return False
    return True


def save_debug_txt(raw: str, src_path: Path, out_dir: Path):
    debug = out_dir / (src_path.stem + '_raw.txt')
    debug.write_text(raw, encoding='utf-8')
    print(f"  Debug text → {debug.name}")


def write_bronze_csv(records: list[dict], fieldnames: list[str], out_path: Path):
    with open(out_path, 'w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=fieldnames, extrasaction='ignore')
        w.writeheader()
        for r in records:
            w.writerow({k: ('' if v is None else v) for k, v in r.items()})
    print(f"  ✓  {len(records):,} rows → {out_path.name}")


# ═══════════════════════════════════════════════════════════════════════════════
# FORMAT 1 — Multi-year wide layout (2002-03 to 2012-13)
# ═══════════════════════════════════════════════════════════════════════════════

def detect_format1_years(text: str) -> list[str]:
    """Auto-detect fiscal years from the file header block."""
    found = re.findall(r'(\d{4}-\d{4})', text[:4000])
    seen, years = [], []
    for y in found:
        if y not in seen and y in FORMAT1_YEARS:
            seen.append(y)
            years.append(y)
    return years


def extract_format1_numbers(tail: str) -> list:
    """Pull numeric tokens from tail; no dashes in Format 1 (blanks = absent)."""
    tokens = tail.split()
    return [t for t in tokens if re.match(r'^\d[\d,]*$', t.replace(',', ''))]


def parse_format1(raw: str, years: list[str]) -> list[dict]:
    records = []
    cur_hs = cur_commodity = cur_unit = None

    for raw_line in raw.splitlines():
        line = raw_line.rstrip()
        if not line.strip():
            continue
        stripped = line.strip()
        if stripped.startswith('---') or stripped.startswith('|'):
            continue
        if should_skip(line):
            continue
        if re.search(r'Value in|HS Code', stripped, re.I):
            continue

        # HS commodity line
        hs_m = re.match(r'^(\d{8})\s{1,5}(.+?)\s{2,}([A-Z/]{1,6})\s*([\d\s]*)$', line)
        if hs_m:
            cur_hs        = validate_hs(hs_m.group(1))
            cur_commodity = re.sub(r'\s+', ' ', hs_m.group(2)).strip().upper()
            cur_unit      = hs_m.group(3).strip()
            nums          = extract_format1_numbers(hs_m.group(4))
            row = _build_format1_row(cur_hs, cur_commodity, cur_unit, 'ALL COUNTRIES', nums, years)
            if row:
                records.append(row)
            continue

        # Country sub-line
        if cur_hs and line and line[0] == ' ':
            c_m = re.match(r'^\s{5,20}(.+?)\s{2,}([\d\s]*)$', line)
            if c_m:
                country = re.sub(r'\s+', ' ', c_m.group(1)).strip()
                if not valid_country(country):
                    continue
                nums = extract_format1_numbers(c_m.group(2))
                row = _build_format1_row(cur_hs, cur_commodity, cur_unit, country, nums, years)
                if row:
                    records.append(row)

    return records


def _build_format1_row(hs, commodity, unit, country, nums, years) -> dict | None:
    if not nums:
        return None
    row = {'hs_code': hs, 'commodity': commodity, 'unit': unit, 'country': country}
    for i, yr in enumerate(years):
        base = i * 2
        row[f'{yr}_quantity']      = nums[base]     if base     < len(nums) else None
        row[f'{yr}_value_000rs']   = nums[base + 1] if base + 1 < len(nums) else None
    return row


def format1_fieldnames(years: list[str]) -> list[str]:
    cols = ['hs_code', 'commodity', 'unit', 'country']
    for yr in years:
        cols += [f'{yr}_quantity', f'{yr}_value_000rs']
    return cols


# ═══════════════════════════════════════════════════════════════════════════════
# FORMAT 2 — JUN + CUMULATIVE dual-year (2013-14 to 2020-21)
# ═══════════════════════════════════════════════════════════════════════════════

def extract_format2_numbers(tail: str, expected: int) -> list:
    """
    Extract numbers/dashes from the numeric tail of a line.

    The PBS TXT format uses '--' (with surrounding spaces) as a placeholder
    for missing data.  We must NOT use regex substitution on the whole string
    because that merges adjacent tokens.  Instead we split on whitespace first,
    then classify each token individually:
      '--' or '-' or '*...' → None  (missing / not applicable)
      digits (with optional commas) → int
      anything else → ignored (headers, units that leaked through)
    """
    tokens = tail.split()
    result = []
    for t in tokens:
        if re.match(r'^[\-\*]+$', t):          # dash or asterisk placeholder
            result.append(None)
        else:
            clean = t.replace(',', '')
            if clean.isdigit():
                result.append(int(clean))
            # anything else (stray letters etc.) is silently skipped
        if len(result) == expected:
            break
    # Pad to expected length with None for fully-blank trailing columns
    while len(result) < expected:
        result.append(None)
    return result


def parse_format2(raw: str, years: list[str]) -> list[dict]:
    records = []
    cur_hs = cur_commodity = cur_unit = None
    n_cols = len(years) * 4

    for raw_line in raw.splitlines():
        line = raw_line.rstrip()
        if should_skip(line):
            continue

        # HS commodity line
        hs_m = re.match(
            r'^(\d{7,8})\s+(.+?)\s{2,}(NO|KG|KGS|MT|MTS|LTR|LTRE|DOZ|NOS?|TON)\s+([\d\s,\-\*]*)$',
            line, re.IGNORECASE
        )
        if hs_m:
            cur_hs        = validate_hs(hs_m.group(1))
            cur_commodity = re.sub(r'\s+', ' ', hs_m.group(2)).strip().upper()
            cur_unit      = hs_m.group(3).upper()
            nums          = extract_format2_numbers(hs_m.group(4), n_cols)
            row = _build_format2_row(cur_hs, cur_commodity, cur_unit, 'ALL COUNTRIES', nums, years)
            if row:
                records.append(row)
            continue

        # Country sub-line
        if cur_hs and line and line[0] == ' ':
            c_m = re.match(r'^\s{5,30}([A-Za-z][^\d\|\t]{2,45}?)\s{2,}([\d\s,\-\*]*)$', line)
            if c_m:
                country = re.sub(r'\s+', ' ', c_m.group(1)).strip()
                if not valid_country(country):
                    continue
                nums = extract_format2_numbers(c_m.group(2), n_cols)
                row = _build_format2_row(cur_hs, cur_commodity, cur_unit, country, nums, years)
                if row:
                    records.append(row)

    return records


def _build_format2_row(hs, commodity, unit, country, nums, years) -> dict | None:
    if all(n is None for n in nums):
        return None
    row = {'hs_code': hs, 'commodity': commodity, 'unit': unit, 'country': country}
    for i, yr in enumerate(years):
        base = i * 4
        row[f'{yr}_jun_quantity']    = nums[base]
        row[f'{yr}_jun_value_000rs'] = nums[base + 1]
        row[f'{yr}_cum_quantity']    = nums[base + 2]
        row[f'{yr}_cum_value_000rs'] = nums[base + 3]
    return row


def format2_fieldnames(years: list[str]) -> list[str]:
    cols = ['hs_code', 'commodity', 'unit', 'country']
    for yr in years:
        cols += [
            f'{yr}_jun_quantity', f'{yr}_jun_value_000rs',
            f'{yr}_cum_quantity', f'{yr}_cum_value_000rs',
        ]
    return cols


# ═══════════════════════════════════════════════════════════════════════════════
# FORMAT 3 — D-10 structured table PDFs (2021-22 to 2023-24)
# ═══════════════════════════════════════════════════════════════════════════════

_F3_SKIP = {
    'IMPORTS BY COMMODITES AND COUNTRIES',
    'IMPORTS BY COMMODITIES AND COUNTRIES',
    'PAK RUPEES IN THOUSANDS', 'PKR IN THOUSANDS',
    'HS CODE', 'COMMODITY BY COUNTRY', 'COMMODITY / COUNTRY',
    'UNIT', 'QUANTITY', 'PAK RUPEES', 'PKR',
    'CUMULATIVE FROM', 'GRAND TOTAL', 'TOTAL',
    'PAKISTAN',
}

_F3_UNITS = {'NO','NOS','KG','KGS','MT','MTS','LTR','LTRE','LTRS','DOZ','TON','SET','PRS','GM'}


def _f3_is_skip(tok: str) -> bool:
    t = tok.strip()
    if t in _F3_SKIP:
        return True
    # Single year fragments like "2021", "2020"
    if re.match(r'^\d{4}$', t):
        return True
    # "JUN", "JUL", "TO" standing alone
    if re.match(r'^(JUN|JUL|TO)$', t, re.I):
        return True
    if re.match(r'^(JUN|JUL|TO)\s+\d{4}', t, re.I):
        return True
    if re.match(r'^\d{4}-\d{4}$', t):
        return True
    if re.match(r'^[\*\-=]{3,}$', t):
        return True
    if re.match(r'^PAGE\s+\d+', t, re.I):
        return True
    if re.match(r'^\(D-10\)', t, re.I):
        return True
    if re.match(r'^D-10\s+IMPORT', t, re.I):
        return True
    if re.match(r'^D\s*-\s*10\b', t, re.I):
        return True
    # "QUANTITY", "PAK RUPEES" column headers standing alone
    if re.match(r'^(QUANTITY|PAK\s+RUPEES|PKR)$', t, re.I):
        return True
    # Large grand-total numbers (comma-separated, 10+ digits)
    if re.match(r'^[\d,]{10,}$', t):
        return True
    return False


def _f3_is_num(tok: str) -> bool:
    return bool(re.match(r'^-+$|^\*+$|^[\d,]+$', tok.strip()))


def _f3_parse_num(tok: str):
    t = tok.strip()
    if re.match(r'^[-\*]+$', t):
        return None
    try:
        return int(t.replace(',', ''))
    except ValueError:
        return None
    
def parse_tabular_row(line: str) -> tuple[str | None, list]:
    """Parse a tab-separated row into (name, nums)."""
    parts = [p.strip() for p in line.split('\t') if p.strip()]
    name, nums = None, []
    for p in parts:
        clean = re.sub(r'[,\.]', '', p)
        if clean.isdigit():
            nums.append(int(clean))
        elif re.match(r'^[\-\*]+$', p):
            nums.append(None)
        elif name is None and re.search(r'[A-Za-z]', p):
            name = p
    return name, nums


def parse_format3(raw: str, years: list[str]) -> list[dict]:
    """
    Token-stream state machine for fitz block output from D-10 PDFs.
    
    Actual token order observed in the PDF:
      HS_CODE COMMODITY_NAME   <- one token, e.g. "01012100 PURE BRED BREEDING HORSES"
      num num num num           <- 8 numbers (n_cols), one per line
      num num num num
      UNIT                     <- unit arrives AFTER the numbers
      COUNTRY                  <- country sub-rows follow
      num num num num
      num num num num
      COUNTRY
      ...
    """
    n_cols = len(years) * 4
    records = []

    cur_hs = cur_commodity = cur_unit = None
    pending_entity = None
    num_buf = []

    # States
    STATE_IDLE        = 0   # waiting for HS line
    STATE_NUMS_MAIN   = 1   # collecting numbers for ALL COUNTRIES row
    STATE_GOT_UNIT    = 2   # unit received, now expecting country rows
    STATE_COUNTRY_NUM = 3   # collecting numbers for a country row

    state = STATE_IDLE

    def flush(entity, nums):
        if not entity:
            return None
        if all(n is None for n in nums):
            return None
        hs, commodity, unit, country = entity
        padded = (nums + [None] * n_cols)[:n_cols]
        row = {'hs_code': hs, 'commodity': commodity, 'unit': unit, 'country': country}
        for idx, yr in enumerate(years):
            base = idx * 4
            row[f'{yr}_jun_quantity']    = padded[base]
            row[f'{yr}_jun_value_000rs'] = padded[base + 1]
            row[f'{yr}_cum_quantity']    = padded[base + 2]
            row[f'{yr}_cum_value_000rs'] = padded[base + 3]
        return row

    tokens = [ln.strip() for ln in raw.splitlines() if ln.strip()]

    for tok in tokens:

        # Always-skip tokens
        if _f3_is_skip(tok):
            continue

        # ── New HS commodity line ────────────────────────────────────────
        hs_m = re.match(r'^(\d{7,8})\s+(.+)$', tok)
        if hs_m:
            # Flush whatever was pending before
            if pending_entity and num_buf:
                r = flush(pending_entity, num_buf)
                if r:
                    records.append(r)

            cur_hs        = str(int(hs_m.group(1))).zfill(8)
            cur_commodity = re.sub(r'\s+', ' ', hs_m.group(2)).strip().upper()
            cur_unit      = ''
            num_buf       = []
            # Set up ALL COUNTRIES entity immediately; unit will be filled in later
            pending_entity = (cur_hs, cur_commodity, '', 'ALL COUNTRIES')
            state = STATE_NUMS_MAIN
            continue

        # ── Unit token ───────────────────────────────────────────────────
        if tok.upper() in _F3_UNITS:
            cur_unit = tok.upper()

            if state == STATE_NUMS_MAIN:
                # Numbers for ALL COUNTRIES are complete; flush with unit now known
                if pending_entity and len(num_buf) >= n_cols:
                    entity_with_unit = (cur_hs, cur_commodity, cur_unit, 'ALL COUNTRIES')
                    r = flush(entity_with_unit, num_buf[:n_cols])
                    if r:
                        records.append(r)
                    num_buf = []
                else:
                    # Update pending entity with unit
                    pending_entity = (cur_hs, cur_commodity, cur_unit, 'ALL COUNTRIES')
                state = STATE_GOT_UNIT

            elif state == STATE_COUNTRY_NUM:
                # Unit appearing mid-country-block — just update unit
                cur_unit = tok.upper()
            continue

        # ── Numeric token ────────────────────────────────────────────────
        if _f3_is_num(tok):
            if state in (STATE_NUMS_MAIN, STATE_COUNTRY_NUM, STATE_GOT_UNIT):
                num_buf.append(_f3_parse_num(tok))

                # Once we have a full set of n_cols numbers for a country row
                if state in (STATE_COUNTRY_NUM, STATE_GOT_UNIT) and len(num_buf) == n_cols:
                    r = flush(pending_entity, num_buf)
                    if r:
                        records.append(r)
                    num_buf = []
                    state = STATE_GOT_UNIT  # back to waiting for next country
            continue

        # ── Country name token ───────────────────────────────────────────
        if state in (STATE_GOT_UNIT, STATE_COUNTRY_NUM):
            # Flush partial nums if any
            if num_buf:
                r = flush(pending_entity, num_buf)
                if r:
                    records.append(r)
                num_buf = []

            country = re.sub(r'\s+', ' ', tok).strip()
            if valid_country(country):
                pending_entity = (cur_hs, cur_commodity, cur_unit, country)
                state = STATE_COUNTRY_NUM

    # Flush final entity
    if pending_entity and num_buf:
        r = flush(pending_entity, num_buf)
        if r:
            records.append(r)

    return records

# ═══════════════════════════════════════════════════════════════════════════════
# MAIN DISPATCH
# ═══════════════════════════════════════════════════════════════════════════════

def process(fmt: int, src: Path, years_arg: str | None, out_dir: Path):
    print(f"\n{'─'*60}")
    print(f"  Format {fmt}  |  {src.name}")

    out_dir.mkdir(parents=True, exist_ok=True)

    # ── Extract raw text ────────────────────────────────────────────────
    if fmt in (1, 2):
        raw = extract_text_plain(src)
    else:  # format 3
        raw = extract_text_tabular(src)

    save_debug_txt(raw, src, out_dir)

    # ── Parse years ─────────────────────────────────────────────────────
    if fmt == 1:
        years = detect_format1_years(raw)
        if not years:
            print(f"  ✗ Could not auto-detect years in {src.name}")
            return
        print(f"  Auto-detected years: {years}")
    else:
        if not years_arg:
            print("  ✗ --years required for Format 2 and Format 3")
            return
        years = [y.strip() for y in years_arg.split(',')]
        print(f"  Years: {years}")

    # ── Parse records ────────────────────────────────────────────────────
    if fmt == 1:
        records    = parse_format1(raw, years)
        fieldnames = format1_fieldnames(years)
    elif fmt == 2:
        records    = parse_format2(raw, years)
        fieldnames = format2_fieldnames(years)
    else:
        records    = parse_format3(raw, years)
        fieldnames = format2_fieldnames(years)   # same schema as fmt 2

    if not records:
        print(f"  ✗ No records extracted — inspect {src.stem}_raw.txt")
        return

    out_csv = out_dir / f'{src.stem}_bronze.csv'
    write_bronze_csv(records, fieldnames, out_csv)


def main():
    ap = argparse.ArgumentParser(
        description='PBS Pakistan Imports — unified bronze extractor (all formats).',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )
    ap.add_argument('--format', type=int, choices=[1, 2, 3], required=True,
                    help='File format: 1=2002-13, 2=2013-21, 3=D-10 2021-24')
    ap.add_argument('--pdf',  help='Input PDF path')
    ap.add_argument('--txt',  help='Input TXT path')
    ap.add_argument('--years',
                    help='Comma-separated fiscal years, current first. '
                         'Required for --format 2 and 3. '
                         'E.g. --years 2014-2015,2013-2014')
    ap.add_argument('--out', default='outputs', help='Output directory (default: outputs/)')
    args = ap.parse_args()

    src = args.pdf or args.txt
    if not src:
        ap.error('Provide --pdf or --txt')

    process(args.format, Path(src), args.years, Path(args.out))
    print('\nDone.')


if __name__ == '__main__':
    main()
