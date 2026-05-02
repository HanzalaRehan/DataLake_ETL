import pandas as pd
from pathlib import Path
import argparse


def read_csv_safely(path):
    """Read CSV with robust handling for messy data."""
    try:
        return pd.read_csv(path, dtype=str)
    except Exception as e:
        print(f"⚠️ Skipping {path.name}: {e}")
        return None


def combine_csvs(input_dir: Path, output_file: Path, trade_type: str = None):
    all_files = list(input_dir.glob("*.csv"))

    if not all_files:
        print("❌ No CSV files found.")
        return

    dfs = []

    for file in all_files:
        print(f"📄 Reading: {file.name}")
        df = read_csv_safely(file)

        if df is None or df.empty:
            continue

        # Normalize column names (strip spaces)
        df.columns = [c.strip() for c in df.columns]

        # Optional: add trade type column
        if trade_type:
            df["trade_type"] = trade_type

        dfs.append(df)

    if not dfs:
        print("❌ No valid dataframes to combine.")
        return

    print("\n🔗 Combining files...")

    # Outer concat → keeps ALL columns across different schemas
    combined = pd.concat(dfs, ignore_index=True, sort=False)

    # Optional: sort for cleanliness
    sort_cols = ["hs_code", "country"]
    sort_cols = [c for c in sort_cols if c in combined.columns]

    if sort_cols:
        combined = combined.sort_values(by=sort_cols)

    # Save output
    combined.to_csv(output_file, index=False)

    print(f"\n✅ Combined file saved: {output_file}")
    print(f"📊 Total rows: {len(combined):,}")
    print(f"📊 Total columns: {len(combined.columns)}")


def main():
    parser = argparse.ArgumentParser(description="Combine PBS trade CSVs")

    parser.add_argument(
        "--input_dir",
        required=True,
        help="Folder containing CSV files"
    )

    parser.add_argument(
        "--output",
        default="combined.csv",
        help="Output CSV file"
    )

    parser.add_argument(
        "--type",
        choices=["import", "export"],
        help="Optional: specify trade type"
    )

    args = parser.parse_args()

    combine_csvs(
        input_dir=Path(args.input_dir),
        output_file=Path(args.output),
        trade_type=args.type
    )


if __name__ == "__main__":
    main()