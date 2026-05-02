import pandas as pd

input_file = "GDP_table.xlsx"
output_file = "outputs/GDP_table.csv"

# Step 1: Read raw (no header)
df = pd.read_excel(input_file, header=None, dtype=str)

# Step 2: Set correct header row (row 4)
header_row = 4
df.columns = df.iloc[header_row]

# Step 3: Drop rows above header
df = df.iloc[header_row + 1:].reset_index(drop=True)

# Step 4: Drop completely empty columns
df = df.dropna(axis=1, how='all')

# Step 5: Remove unwanted footer/meta columns (like "Page No.")
df = df.loc[:, ~df.columns.astype(str).str.contains("Page", case=False)]

# Step 6: Strip whitespace from column names
df.columns = df.columns.astype(str).str.strip()

# Step 7: Keep everything as string (bronze-safe)
df = df.astype(str)

# Step 8: Export clean CSV
df.to_csv(output_file, index=False, encoding="utf-8")

print(f"Clean CSV saved as {output_file}")