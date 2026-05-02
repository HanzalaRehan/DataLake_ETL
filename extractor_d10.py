"""
PBS Pakistan D-10 Extractor - Imports & Exports, all years

Handles every D-10 PDF variant observed:

  VARIANT A  - 2022 Import
    bare HS code alone on its own line
    commodity alone on next line
    8 numbers (quantities-first layout)
    unit (NO/KG/…) AFTER the 8 numbers

  VARIANT B  - 2022 Export
    bare HS code alone on its own line
    commodity alone on next line
    unit BEFORE the 8 numbers
    8 numbers (quantities-first layout)

  VARIANT C  - 2023 Import/Export, 2024 Import/Export
    HS + commodity (+ optional unit) all on one token
       e.g.  "1012100PURE BRED BREEDING HORSES"
        or   "01022190 OTH PURE BRED BREEDING ANIMALSNO"
        or   "01059400 OTH FOWLS OF THE SPE (CHICKEN) NO"
    unit token on the very next line (if not already on HS line)
    8 numbers — quantities-first layout

Column layout for ALL variants (fitz block order):
  [ jun_qty_cur,  cum_qty_cur,  jun_qty_prev,  cum_qty_prev,
    jun_val_cur,  cum_val_cur,  jun_val_prev,  cum_val_prev ]

  _reorder() maps this to the standard interleaved CSV schema:
  [ jun_qty_cur,  jun_val_cur,  cum_qty_cur,  cum_val_cur,
    jun_qty_prev, jun_val_prev, cum_qty_prev, cum_val_prev ]

Usage:
  python extractor_d10.py --pdf input/D-10_Import-06-2022.pdf  --years "2021-2022,2020-2021" --out outputs/
  python extractor_d10.py --pdf input/D-10_Export-06-2022.pdf  --years "2021-2022,2020-2021" --out outputs/
  python extractor_d10.py --pdf input/D-10_Import-06-2023.pdf  --years "2022-2023,2021-2022" --out outputs/
  python extractor_d10.py --pdf input/D-10_Export-06-2023.pdf  --years "2022-2023,2021-2022" --out outputs/
  python extractor_d10.py --pdf input/D-10_Import0624.pdf      --years "2023-2024,2022-2023" --out outputs/
  python extractor_d10.py --pdf input/D-10_Export0624.pdf      --years "2023-2024,2022-2023" --out outputs/
"""

import re
import csv
import argparse
from pathlib import Path

try:
    import fitz  # PyMuPDF  (pip install pymupdf)
    HAS_PDF = True
except ImportError:
    HAS_PDF = False


# CONSTANTS

_UNITS = {
    'NO', 'NOS', 'KG', 'KGS', 'MT', 'MTS', 'LTR', 'LTRE', 'LTRS',
    'DOZ', 'TON', 'SET', 'PRS', 'GM', 'M3', 'SQM', 'SQY',
}

# Sorted longest-first so the regex prefers e.g. "KGS" over "KG"
_UNIT_PAT = '|'.join(sorted(_UNITS, key=len, reverse=True))

_SKIP_EXACT = {
    'IMPORTS BY COMMODITES AND COUNTRIES',
    'IMPORTS BY COMMODITIES AND COUNTRIES',
    'EXPORTS BY COMMODITES AND COUNTRIES',
    'EXPORTS BY COMMODITIES AND COUNTRIES',
    '(D-10) IMPORTS BY COMMODITES AND COUNTRIES',
    '(D-10) IMPORTS BY COMMODITIES AND COUNTRIES',
    '(D-10) EXPORTS BY COMMODITES AND COUNTRIES',
    '(D-10) EXPORTS BY COMMODITIES AND COUNTRIES',
    'PAK RUPEES IN THOUSANDS', 'PKR IN THOUSANDS', 'PKR',
    'HS CODE', 'HSCODE',
    'COMMODITY BY COUNTRY', 'COMMODITY / COUNTRY',
    'UNIT', 'QUANTITY', 'PAK RUPEES', 'QTY',
    'GRAND TOTAL', 'TOTAL', 'PAKISTAN',
    'D-10', '(D-10)',
}


# SKIP / PARSE HELPERS

def _is_skip(tok: str) -> bool:
    t = tok.strip()
    if not t:
        return True
    if t in _SKIP_EXACT:
        return True
    # "CUMULATIVE  FROM" (any whitespace)
    if re.match(r'^CUMULATIVE\s+FROM$', t, re.I):
        return True
    # Standalone 4-digit year
    if re.match(r'^\d{4}$', t):
        return True
    # Month/connector: JUN, JUL, TO, JUN 2022, JUN-2022, etc.
    if re.match(r'^(JUN|JUL|TO)(\s.*)?$', t, re.I):
        return True
    # Fiscal year range "2021-2022"
    if re.match(r'^\d{4}[-–]\d{4}$', t):
        return True
    # Separator lines
    if re.match(r'^[\*\-=_]{2,}$', t):
        return True
    # Page numbers
    if re.match(r'^PAGE\s*\d+', t, re.I):
        return True
    # D-10 header variants
    if re.match(r'^\(?D[-\s]*10\)?', t, re.I):
        return True
    # Truncated header fragments: "LATIVE FROM", "MULATIVE FROM", "CUMULATIVE  FROM"
    if re.match(r'^(CUM|M)?ULATIVE\s+FROM', t, re.I):
        return True
    # Grand total numbers (10+ digits when commas removed)
    digits_only = t.replace(',', '')
    if digits_only.isdigit() and len(digits_only) >= 10:
        return True
    # Standalone column header words
    if re.match(r'^(QUANTITY|PAK\s+RUPEES?|PKR|QTY)$', t, re.I):
        return True
    return False


def _is_num(tok: str) -> bool:
    """True for numeric values, dashes, and asterisk placeholders."""
    t = tok.strip()
    return bool(re.match(r'^[-–]+$|^\*+$|^[\d,]+$', t))


def _parse_num(tok: str):
    """Return int, or None for dash/asterisk placeholders."""
    t = tok.strip()
    if re.match(r'^[-–\*]+$', t):
        return None
    try:
        return int(t.replace(',', ''))
    except ValueError:
        return None


def _valid_country(name: str) -> bool:
    t = name.strip()
    if not t or len(t) < 2:
        return False
    if not re.match(r'^[A-Za-z(]', t):  # allow "(Islamic..." style names
        return False
    if re.match(r'^[\d\s,\-\*\.]+$', t):
        return False
    if re.search(r'\b(QUANTITY|VALUE|HSCODE|HS CODE|PAGE|RUPEES|PKR|UNIT)\b', t, re.I):
        return False
    if t.upper() in _UNITS:
        return False
    if not re.search(r'[A-Za-z]{2,}', t):
        return False
    return True


def _validate_hs(hs: str) -> str:
    try:
        return str(int(hs.strip())).zfill(8)
    except (ValueError, TypeError):
        return hs.strip().zfill(8)


# PDF EXTRACTION

def extract_blocks(path: Path) -> str:
    """
    Extract text from D-10 PDF using fitz blocks mode.
    Each table cell becomes its own line, sorted top-to-bottom left-to-right.
    """
    if not HAS_PDF:
        raise ImportError("pip install pymupdf")
    all_lines = []
    with fitz.open(str(path)) as pdf:
        for page in pdf:
            blocks = [b for b in page.get_text("blocks") if b[6] == 0 and b[4].strip()]
            blocks.sort(key=lambda b: (round(b[1] / 3) * 3, b[0]))
            for b in blocks:
                for sub in b[4].split('\n'):
                    sub = sub.strip()
                    if sub:
                        all_lines.append(sub)
    return '\n'.join(all_lines)


# NUMBER REORDERING

def _reorder(nums: list, n_years: int) -> list:
    """
    D-10 PDFs (all variants) emit numbers in quantities-first order:
      [ jun_qty_0, cum_qty_0, jun_qty_1, cum_qty_1, ...  <- qty block
        jun_val_0, cum_val_0, jun_val_1, cum_val_1, ... ]  <- val block

    CSV schema wants interleaved-by-year order:
      [ jun_qty_0, jun_val_0, cum_qty_0, cum_val_0,
        jun_qty_1, jun_val_1, cum_qty_1, cum_val_1, ... ]
    """
    reordered = []
    for i in range(n_years):
        jun_qty = nums[i * 2]
        cum_qty = nums[i * 2 + 1]
        jun_val = nums[n_years * 2 + i * 2]
        cum_val = nums[n_years * 2 + i * 2 + 1]
        reordered += [jun_qty, jun_val, cum_qty, cum_val]
    return reordered


# HS LINE DETECTION

# Matches tokens where HS+commodity (+ optional unit) are all together:
#   "1012100PURE BRED BREEDING HORSES"
#   "01022190 OTH PURE BRED BREEDING ANIMALSNO"
#   "01059400 OTH FOWLS OF THE SPE (CHICKEN) NO"
_HS_COMBO_RE = re.compile(
    r'^(\d{7,8})\s*([A-Za-z(].+?)(?:\s*(' + _UNIT_PAT + r'))?\s*$',
    re.IGNORECASE
)


def _parse_hs_combo(tok: str):
    """
    Returns (hs, commodity, unit_or_None) if tok is a combined HS+commodity token.
    Returns None if tok is just a bare HS number or doesn't match.
    """
    # Reject bare HS numbers — handled separately
    if re.match(r'^\d{7,8}$', tok.strip()):
        return None
    m = _HS_COMBO_RE.match(tok.strip())
    if m:
        hs   = _validate_hs(m.group(1))
        comm = re.sub(r'\s+', ' ', m.group(2)).strip().upper()
        unit = m.group(3).upper() if m.group(3) else None
        return hs, comm, unit
    return None


# ─────────────────────────────────────────────────────────────────────────────
# MAIN STATE-MACHINE PARSER
# ─────────────────────────────────────────────────────────────────────────────

def parse_d10(raw: str, years: list) -> list:
    """
    Token-stream state machine covering all D-10 variants.

    States
    ──────
    IDLE          Waiting for an HS code.
    NEED_COMM     Saw a bare HS number; waiting for the commodity text line.
    NEED_UNIT     Have HS+commodity; waiting for unit token (Variant C when
                  unit not already on HS line, or Variant B before numbers).
    NUMS          Collecting 8 numbers for the current entity.
    AFTER_NUMS    Collected all 8 numbers for ALL COUNTRIES; waiting for unit
                  token (Variant A — import 2022 only).
    COUNTRY_NUMS  Collecting 8 numbers for a country sub-row.

    Variant detection
    ─────────────────
    A (import 2022): bare HS → commodity → numbers → unit
    B (export 2022): bare HS → commodity → unit → numbers
    C (2023/2024):   HS+commodity[+unit] token → [unit token] → numbers

    All use _reorder() because fitz emits quantities-first layout.
    """
    n_cols  = len(years) * 4
    n_years = len(years)
    records = []

    cur_hs        = None
    cur_commodity = None
    cur_unit      = ''
    pending_entity = None   # (hs, commodity, unit, country)
    num_buf       = []

    # Per-HS-section flag: True = bare-HS style (A or B), False = combo style (C)
    bare_hs_style = False
    # Per-HS-section flag: True = unit appeared after numbers (Variant A)
    unit_after_nums = False

    # ── States ───────────────────────────────────────────────────────────────
    IDLE         = 0
    NEED_COMM    = 1
    NEED_UNIT    = 2
    NUMS         = 3
    AFTER_NUMS   = 4
    COUNTRY_NUMS = 5

    state = IDLE

    def flush(entity, nums, reorder=True):
        if not entity:
            return None
        hs, commodity, unit, country = entity
        if all(n is None for n in nums):
            return None
        work = (list(nums) + [None] * n_cols)[:n_cols]
        if reorder:
            work = _reorder(work, n_years)
        row = {'hs_code': hs, 'commodity': commodity, 'unit': unit, 'country': country}
        for idx, yr in enumerate(years):
            base = idx * 4
            row[f'{yr}_jun_quantity']    = work[base]
            row[f'{yr}_jun_value_000rs'] = work[base + 1]
            row[f'{yr}_cum_quantity']    = work[base + 2]
            row[f'{yr}_cum_value_000rs'] = work[base + 3]
        return row

    def start_new_hs(hs, commodity, unit):
        """Reset per-entity state when a new HS section begins."""
        nonlocal cur_hs, cur_commodity, cur_unit, num_buf, pending_entity, state
        cur_hs        = hs
        cur_commodity = commodity
        cur_unit      = unit or ''
        num_buf       = []
        pending_entity = (cur_hs, cur_commodity, cur_unit, 'ALL COUNTRIES')

    tokens = [ln.strip() for ln in raw.splitlines() if ln.strip()]

    for tok in tokens:

        # ── 1. Always-skip noise ─────────────────────────────────────────────
        if _is_skip(tok):
            continue

        # ── 2. Bare HS number alone (Variants A & B) ─────────────────────────
        if re.match(r'^\d{7,8}$', tok):
            # Flush any pending entity first
            if pending_entity and num_buf:
                r = flush(pending_entity, num_buf)
                if r:
                    records.append(r)
            bare_hs_style   = True
            unit_after_nums = False
            hs = _validate_hs(tok)
            # Don't call start_new_hs yet — commodity comes on next line
            cur_hs        = hs
            cur_commodity = None
            cur_unit      = ''
            num_buf       = []
            pending_entity = None
            state = NEED_COMM
            continue

        # ── 3. Combined HS+commodity[+unit] token (Variant C) ────────────────
        combo = _parse_hs_combo(tok)
        if combo:
            if pending_entity and num_buf:
                r = flush(pending_entity, num_buf)
                if r:
                    records.append(r)
            bare_hs_style   = False
            unit_after_nums = False
            hs, comm, unit  = combo
            start_new_hs(hs, comm, unit)
            if unit:
                state = NUMS         # unit already known → straight to numbers
            else:
                state = NEED_UNIT    # wait for unit token
            continue

        # ── 4. Commodity text (follows bare HS, state == NEED_COMM) ──────────
        if state == NEED_COMM:
            if tok.upper() in _UNITS:
                # Unit appearing where commodity expected (shouldn't happen,
                # but handle gracefully by treating it as Variant B mid-flow)
                cur_unit = tok.upper()
                pending_entity = (cur_hs, cur_commodity or '', cur_unit, 'ALL COUNTRIES')
                state = NUMS
            elif re.search(r'[A-Za-z]{2,}', tok) and not _is_num(tok):
                cur_commodity  = re.sub(r'\s+', ' ', tok).strip().upper()
                pending_entity = (cur_hs, cur_commodity, cur_unit, 'ALL COUNTRIES')
                state = NEED_UNIT   # next: expect unit (Variant B) or numbers (Variant A)
            continue

        # ── 5. Unit token ─────────────────────────────────────────────────────
        if tok.upper() in _UNITS:
            cur_unit = tok.upper()

            if state == NEED_UNIT:
                # Unit arrived before numbers → Variant B (export 2022) or Variant C
                pending_entity = (cur_hs, cur_commodity, cur_unit, 'ALL COUNTRIES')
                state = NUMS

            elif state == NUMS:
                # Unit arrived while collecting numbers (shouldn't normally happen)
                pending_entity = (cur_hs, cur_commodity, cur_unit, 'ALL COUNTRIES')

            elif state == AFTER_NUMS:
                # Unit arrived after all 8 numbers → Variant A (import 2022)
                entity_with_unit = (cur_hs, cur_commodity, cur_unit, 'ALL COUNTRIES')
                r = flush(entity_with_unit, num_buf)
                if r:
                    records.append(r)
                num_buf = []
                state   = COUNTRY_NUMS

            elif state == COUNTRY_NUMS:
                cur_unit = tok.upper()   # refresh unit between country rows
            continue

        # ── 6. Numeric token ─────────────────────────────────────────────────
        if _is_num(tok):
            if state in (NEED_UNIT, NUMS, COUNTRY_NUMS):
                # If we're still in NEED_UNIT and see a number, it means the
                # unit was absent (rare) — treat as Variant A, numbers started
                if state == NEED_UNIT:
                    state = NUMS

                num_buf.append(_parse_num(tok))

                if len(num_buf) == n_cols:
                    if state == NUMS:
                        if bare_hs_style and not cur_unit:
                            # Variant A: no unit yet — wait for it
                            state = AFTER_NUMS
                        else:
                            # Variant B / C: flush immediately
                            r = flush(pending_entity, num_buf)
                            if r:
                                records.append(r)
                            num_buf = []
                            state   = COUNTRY_NUMS
                    elif state == COUNTRY_NUMS:
                        r = flush(pending_entity, num_buf)
                        if r:
                            records.append(r)
                        num_buf = []
                        # stay in COUNTRY_NUMS
            continue

        # ── 7. Text token → country name ─────────────────────────────────────
        if state in (COUNTRY_NUMS, AFTER_NUMS, NUMS, NEED_UNIT) and cur_hs:
            # Flush partial num_buf if any
            if num_buf:
                if state == AFTER_NUMS:
                    # Somehow hit a country name while waiting for unit after nums
                    # Flush as-is (unit unknown → empty string)
                    r = flush((cur_hs, cur_commodity, cur_unit, 'ALL COUNTRIES'), num_buf)
                    if r:
                        records.append(r)
                else:
                    r = flush(pending_entity, num_buf)
                    if r:
                        records.append(r)
                num_buf = []
                if state != COUNTRY_NUMS:
                    state = COUNTRY_NUMS

            country = re.sub(r'\s+', ' ', tok).strip()
            if _valid_country(country):
                pending_entity = (cur_hs, cur_commodity, cur_unit, country)
                num_buf = []
                state   = COUNTRY_NUMS

    # ── Flush the very last entity ────────────────────────────────────────────
    if pending_entity and num_buf:
        r = flush(pending_entity, num_buf)
        if r:
            records.append(r)

    return records


# ─────────────────────────────────────────────────────────────────────────────
# CSV OUTPUT
# ─────────────────────────────────────────────────────────────────────────────

def fieldnames(years: list) -> list:
    cols = ['hs_code', 'commodity', 'unit', 'country']
    for yr in years:
        cols += [
            f'{yr}_jun_quantity',    f'{yr}_jun_value_000rs',
            f'{yr}_cum_quantity',    f'{yr}_cum_value_000rs',
        ]
    return cols


def write_csv(records: list, fnames: list, out_path: Path):
    with open(out_path, 'w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=fnames, extrasaction='ignore')
        w.writeheader()
        for r in records:
            w.writerow({k: ('' if v is None else v) for k, v in r.items()})
    print(f"  ✓  {len(records):,} rows → {out_path.name}")


# ─────────────────────────────────────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────────────────────────────────────

def process(src: Path, years_arg: str, out_dir: Path):
    print(f"\n{'─'*60}")
    print(f"  D-10  |  {src.name}")

    out_dir.mkdir(parents=True, exist_ok=True)

    raw = extract_blocks(src)
    debug = out_dir / (src.stem + '_raw.txt')
    debug.write_text(raw, encoding='utf-8')
    print(f"  Debug text → {debug.name}")

    years = [y.strip() for y in years_arg.split(',')]
    print(f"  Years: {years}")

    records = parse_d10(raw, years)

    if not records:
        print(f"  ✗ No records extracted — inspect {debug.name}")
        return

    out_csv = out_dir / f'{src.stem}_bronze.csv'
    write_csv(records, fieldnames(years), out_csv)


def main():
    ap = argparse.ArgumentParser(description='PBS D-10 Import/Export PDF → CSV')
    ap.add_argument('--pdf',   required=True, help='Input D-10 PDF')
    ap.add_argument('--years', required=True,
                    help='Fiscal years, current first. E.g. "2021-2022,2020-2021"')
    ap.add_argument('--out', default='outputs', help='Output directory')
    args = ap.parse_args()
    process(Path(args.pdf), args.years, Path(args.out))
    print('\nDone.')


if __name__ == '__main__':
    main()
