from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

import camelot
import pandas as pd


MONTHS = ["Jul", "Aug", "Sep", "Oct", "Nov", "Dec", "Jan", "Feb", "Mar", "Apr", "May", "Jun"]


_UNIT_TOKENS = {
    "MT",
    "000 L",
    "000L",
    "L",
    "KG",
    "TON",
    "TONS",
}


@dataclass(frozen=True)
class Schema:
    has_weight: bool

    @property
    def month_start_idx(self) -> int:
        return 4 if self.has_weight else 3

    @property
    def year_total_idx(self) -> int:
        return self.month_start_idx + 12


def norm(text: Any) -> str:
    if text is None:
        return ""
    s = str(text)
    s = s.replace("\n", " ").replace("\r", " ")
    s = " ".join(s.split())
    return s


_num_cleanup_re = re.compile(r"[^0-9.\-]+")


def parse_number(text: str) -> float | int | None:
    """Parse values like '1, 885, 912. 0' or '94. 4' into numbers."""
    s = norm(text)
    if not s:
        return None

    # Normalize split decimals like '94. 4' -> '94.4'
    s = s.replace(". ", ".").replace(" .", ".")

    # Remove thousands separators/spaces and any stray text
    s = _num_cleanup_re.sub("", s)
    if s in {"", ".", "-", "-."}:
        return None

    # Prefer int if it looks like an int
    if "." not in s:
        try:
            return int(s)
        except ValueError:
            return None

    try:
        f = float(s)
    except ValueError:
        return None

    # If it's a whole number like '123.0', store as int
    if abs(f - int(f)) < 1e-12:
        return int(f)
    return f


_num_token_re = re.compile(r"-?\d[\d,]*\.?\d*")


def split_numbers(text: str) -> list[float | int]:
    """Extract one-or-more numbers from a cell.

    Camelot sometimes glues multiple month values into one cell (especially for
    large comma-separated values). This returns *all* numbers found in order.
    """
    s = norm(text)
    if not s:
        return []

    # Normalize common split patterns
    s = s.replace(". ", ".").replace(" .", ".")
    # Normalize comma spacing: '1, 234' -> '1,234'
    s = re.sub(r",\s+", ",", s)

    parts = _num_token_re.findall(s)
    out: list[float | int] = []
    for p in parts:
        n = parse_number(p)
        if n is not None:
            out.append(n)
    return out


def looks_like_unit(text: str) -> bool:
    s = norm(text).upper()
    if not s:
        return False
    if s in _UNIT_TOKENS:
        return True
    # Common Camelot artifact: '000 L' sometimes gets split oddly
    if re.fullmatch(r"0{3}\s*L", s):
        return True
    # Reject pure numeric values (weights masquerading as units)
    if re.match(r"^[\d.]+$", s):
        return False
    # Accept common unit-like patterns
    if any(k in s for k in ["NOS", "TONNES", "KGS", "MT", "LITRE", "METRE", "SQ", "DOZEN", "BOXES"]):
        return True
    return False


def looks_numericish(text: str) -> bool:
    s = norm(text)
    if not s:
        return False
    return parse_number(s) is not None


def infer_year_label(pdf_name: str) -> str:
    # Patterns in filenames:
    # - Table-2-for-year-2016-17.pdf
    # - Table-2-23-24-1.pdf
    m = re.search(r"(20\d{2})-(\d{2})", pdf_name)
    if m:
        start = int(m.group(1))
        end2 = int(m.group(2))
        end = (start // 100) * 100 + end2
        if end < start:
            end += 100
        return f"{start}-{str(end)[-2:]}"

    m = re.search(r"\b(\d{2})-(\d{2})\b", pdf_name)
    if m:
        start2 = int(m.group(1))
        end2 = int(m.group(2))
        start = 2000 + start2
        end = 2000 + end2
        if end < start:
            end += 100
        return f"{start}-{str(end)[-2:]}"

    return ""


def choose_schema(df: pd.DataFrame) -> Schema | None:
    # Drop fully empty trailing columns that Camelot sometimes creates
    while df.shape[1] and df.iloc[:, -1].astype(str).map(norm).eq("").all():
        df = df.iloc[:, :-1]

    ncol = df.shape[1]
    if ncol == 17:
        return Schema(has_weight=True)
    if ncol == 16:
        return Schema(has_weight=False)

    return None


def is_header_row(row: list[str]) -> bool:
    line = " ".join(row).lower()
    return ("s. no" in line or "s.no" in line) and "items" in line


def looks_like_data_row(s_no: str, items: str, month_values: list[str]) -> bool:
    if items and items.lower().startswith("table"):
        return False

    if is_header_row([s_no, items]):
        return False

    # If we have a serial-like entry OR any numeric month values, treat as data
    if re.match(r"^\d+(?:-\d+)?$", s_no.strip()):
        return True

    if items and any(v for v in month_values):
        return True

    return False


def extract_rows_from_table(df: pd.DataFrame, *, pdf_name: str, page: int, table_index: int) -> list[dict[str, Any]]:
    schema = choose_schema(df)
    if schema is None:
        return []

    # Normalize cells
    df = df.copy()
    for c in df.columns:
        df[c] = df[c].map(norm)

    rows = df.values.tolist()

    # Find the header row if present; start parsing after it.
    start_i = 0
    for i, r in enumerate(rows[:25]):
        r0 = r[0] if len(r) else ""
        r1 = r[1] if len(r) > 1 else ""
        if is_header_row([r0, r1]) or any("jul" in cell.lower() for cell in r):
            # Header block can be multiple rows; start right after the first 'S. No' row if found.
            if "s." in (r0 + " " + r1).lower():
                start_i = i + 1
            else:
                start_i = i
            break

    out: list[dict[str, Any]] = []
    last: dict[str, Any] | None = None

    for r in rows[start_i:]:
        # Pad row to expected columns
        r = list(r) + [""] * (schema.year_total_idx + 1 - len(r))

        s_no = r[0]

        # Camelot is not perfectly consistent for 16-col (no-weight) tables:
        # sometimes long item strings land in col2 and col1 is blank.
        raw_col1 = r[1] if len(r) > 1 else ""
        raw_col2 = r[2] if len(r) > 2 else ""

        # Detect the correct items/unit/weight layout
        if schema.has_weight:
            # 17-col: S_NO | ITEMS | UNIT | WEIGHT | ... months
            items = raw_col1
            unit = raw_col2
            weight_raw = r[3] if len(r) > 3 else ""
        else:
            # 16-col (no weight): S_NO | ITEMS | UNIT | ... months
            # But Camelot may shift long item names right, so:
            # - If col1 is empty and col2 looks like items, use col2
            # - If col2 is numeric (weight), move it to weight_raw and leave unit empty
            items = raw_col1
            unit = raw_col2
            weight_raw = ""

            # Handle shifted item names
            if not items.strip() and raw_col2.strip() and not looks_like_unit(raw_col2):
                items = raw_col2
                unit = ""

            # Handle numeric units (actually weights)
            if unit.strip() and parse_number(unit) is not None and not looks_like_unit(unit):
                weight_raw = unit
                unit = ""

        month_cells = r[schema.month_start_idx : schema.month_start_idx + 12]
        year_total_cell = r[schema.year_total_idx]

        # Drop totally empty rows
        if not any([s_no, items, unit, weight_raw, *month_cells, year_total_cell]):
            continue

        # Skip obvious title/header clutter
        joined = " ".join([s_no, items, unit, weight_raw, *month_cells, year_total_cell]).lower()
        if any(k in joined for k in ["quantum index", "qim", "manufacturing industries"]):
            # keep real data rows (they won't contain these phrases)
            if not looks_like_data_row(s_no, items, month_cells):
                continue

        if "production" in joined and not looks_like_data_row(s_no, items, month_cells):
            continue

        # Merge "value-only" rows into the previous row (seen in 2022-23 for the first line)
        value_only = (
            not s_no.strip()
            and not items.strip()
            and not unit.strip()
            and (not schema.has_weight or not weight_raw.strip())
            and any(cell.strip() for cell in month_cells)
        )
        if value_only and last is not None:
            # If last row lacks months, fill them
            if sum(v is not None for v in last.get("months", [])) <= 2:
                parsed = [parse_number(x) for x in month_cells]
                last["months"] = parsed
                last["year_total"] = parse_number(year_total_cell)
            continue

        if not looks_like_data_row(s_no, items, month_cells):
            continue

        # Parse months with multi-number spillover support.
        months: list[float | int | None] = [None] * 12
        i = 0
        while i < 12:
            cell = month_cells[i]
            if not cell.strip():
                i += 1
                continue

            nums = split_numbers(cell)
            if not nums:
                i += 1
                continue

            # If previous month cell is empty and current cell contains multiple numbers,
            # Camelot likely shifted the sequence right by 1 (seen in 2022-23).
            start_i = i
            if len(nums) > 1 and i > 0 and not month_cells[i - 1].strip() and months[i - 1] is None:
                start_i = i - 1

            j = start_i
            for n in nums:
                if j >= 12:
                    break
                if months[j] is None and (not month_cells[j].strip() or j == i or j == start_i):
                    months[j] = n
                    j += 1
                else:
                    # Don't overwrite existing/non-empty columns; move forward.
                    j += 1

            i += 1

        year_total = parse_number(year_total_cell)

        rec: dict[str, Any] = {
            "source_pdf": pdf_name,
            "page": page,
            "table_index": table_index,
            "year": infer_year_label(pdf_name),
            "s_no": s_no.strip(),
            "items": items.strip(),
            "unit": unit.strip(),
            "weight": parse_number(weight_raw) if schema.has_weight else None,
            "months": months,
            "year_total": year_total,
        }

        out.append(rec)
        last = rec

    return out


def explode_records(records: Iterable[dict[str, Any]]) -> pd.DataFrame:
    flat_rows: list[dict[str, Any]] = []
    for r in records:
        row: dict[str, Any] = {
            "source_pdf": r["source_pdf"],
            "page": r["page"],
            "table_index": r["table_index"],
            "year": r["year"],
            "s_no": r["s_no"],
            "items": r["items"],
            "unit": r["unit"],
            "weight": r["weight"],
            "year_total": r["year_total"],
        }
        months = r.get("months") or [None] * 12
        for i, m in enumerate(MONTHS):
            row[m] = months[i] if i < len(months) else None
        flat_rows.append(row)

    df = pd.DataFrame(flat_rows)

    # Keep deterministic column order
    cols = [
        "source_pdf",
        "year",
        "s_no",
        "items",
        "unit",
        "weight",
        *MONTHS,
        "year_total",
        "page",
        "table_index",
    ]
    for c in cols:
        if c not in df.columns:
            df[c] = None
    df = df[cols]
    return df


def main() -> None:
    root = Path(__file__).resolve().parent
    pdfs = sorted(root.glob("*.pdf"))
    if not pdfs:
        raise SystemExit("No PDFs found next to the script.")

    all_records: list[dict[str, Any]] = []

    for pdf_path in pdfs:
        # Read all pages; stream mode works well here and doesn't need Ghostscript.
        tables = camelot.read_pdf(str(pdf_path), pages="all", flavor="stream")
        for t in tables:
            recs = extract_rows_from_table(
                t.df,
                pdf_name=pdf_path.name,
                page=int(getattr(t, "page", 0) or 0),
                table_index=int(getattr(t, "order", 0) or 0),
            )
            all_records.extend(recs)

    out_df = explode_records(all_records)

    # Drop rows that are still obviously headers
    out_df = out_df[~out_df["items"].str.contains(r"\bItems\b", case=False, na=False)]

    # Filter out "QIM" summary rows (Quantum Index of Manufacturing index/summary, typically on page 2)
    out_df = out_df[~out_df["items"].str.match(r"^QIM$", na=False)]

    out_csv = root / "table2_all_years.csv"
    out_df.to_csv(out_csv, index=False)

    print(f"Wrote {len(out_df):,} rows to {out_csv.name}")


if __name__ == "__main__":
    main()
