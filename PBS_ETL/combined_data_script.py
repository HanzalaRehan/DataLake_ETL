import pandas as pd
import glob
import os
import re

def extract_date_from_filename(filename):
    # e.g., Annex_02.04.2026.xlsx -> 2026-04-02
    match = re.search(r'(\d{2})\.(\d{2})\.(\d{4})', filename)
    if match:
        day, month, year = match.groups()
        return f"{year}-{month}-{day}"
    return "Unknown"

def process_appendix_a(df, date, filename):
    records = []
    # Row 2 contains cities starting from column 3, spanning 3 columns each
    cities = []
    for col in range(3, df.shape[1] - 1, 3):
        city_val = df.iloc[2, col]
        if pd.notna(city_val):
            city_name = str(city_val).split('(')[0].strip()
            cities.append((city_name, col))
            
    # Data starts from row 6
    for idx in range(6, df.shape[0]):
        row = df.iloc[idx, :]
        if pd.isna(row[0]) or str(row[0]).strip() == "":
            continue
            
        item_no = str(row[0]).strip()
        item_desc = str(row[1]).strip()
        unit = str(row[2]).strip()
        
        for city_name, start_col in cities:
            min_val = row[start_col]
            avg_val = row[start_col + 1]
            max_val = row[start_col + 2]
            
            if pd.notna(min_val) and min_val != "N.A." and min_val != "-":
                records.append([filename, date, "CONSUMER PRICES OF ESSENTIAL ITEMS", item_no, item_desc, unit, city_name, "MIN", min_val])
            if pd.notna(avg_val) and avg_val != "N.A." and avg_val != "-":
                records.append([filename, date, "CONSUMER PRICES OF ESSENTIAL ITEMS", item_no, item_desc, unit, city_name, "AVG", avg_val])
            if pd.notna(max_val) and max_val != "N.A." and max_val != "-":
                records.append([filename, date, "CONSUMER PRICES OF ESSENTIAL ITEMS", item_no, item_desc, unit, city_name, "MAX", max_val])
                
    return records

def process_appendix_b(df, date, filename):
    records = []
    table_indices = []
    
    # Identify tables
    for idx, row in df.iterrows():
        val = str(row[0]) if pd.notna(row[0]) else ""
        if ":" in val and ("Prices" in val or "Rates" in val):
            table_indices.append((idx, val.strip()))
            
    for i, (start_idx, table_name) in enumerate(table_indices):
        # Determine end of table
        end_idx = table_indices[i+1][0] if i + 1 < len(table_indices) else df.shape[0]
        
        # Find headers
        header_idx = -1
        for j in range(start_idx + 1, min(start_idx + 5, df.shape[0])):
            if pd.notna(df.iloc[j, 1]) and str(df.iloc[j, 1]).strip().lower() == "description":
                header_idx = j
                break
            elif pd.notna(df.iloc[j, 0]) and str(df.iloc[j, 0]).strip().lower() == "description":
                header_idx = j
                break
                
        if header_idx == -1:
            continue
            
        headers = [str(x).replace('\n', ' ').strip() if pd.notna(x) else "" for x in df.iloc[header_idx, :]]
        
        has_unit_col = False
        desc_col_idx = -1
        unit_col_idx = -1
        for col_idx, h in enumerate(headers):
            if h.lower() == "description":
                desc_col_idx = col_idx
            elif h.lower() == "unit":
                has_unit_col = True
                unit_col_idx = col_idx
                
        if desc_col_idx == -1:
            continue
            
        # Parse items
        for j in range(header_idx + 1, end_idx):
            row = df.iloc[j, :]
            item_no = str(row[0]).strip() if pd.notna(row[0]) else ""
            if not item_no or item_no.lower() == "nan" or "No." in item_no:
                continue
                
            item_desc = str(row[desc_col_idx]).strip() if pd.notna(row[desc_col_idx]) else ""
            if not item_desc or item_desc.lower() == "nan":
                continue
                
            unit = str(row[unit_col_idx]).strip() if has_unit_col and pd.notna(row[unit_col_idx]) else ""
            
            # If no unit column, try to parse from table name (e.g., "(50 kg/bag)")
            if not unit:
                unit_match = re.search(r'\((.*?)\)', table_name)
                if unit_match:
                    unit = unit_match.group(1)
                    
            # Parse metrics for each column
            for col_idx in range(max(desc_col_idx, unit_col_idx) + 1, len(headers)):
                h = headers[col_idx]
                val = row[col_idx]
                
                if not h or h.lower() == "nan":
                    continue
                if pd.isna(val) or val == "N.A." or val == "-" or str(val).strip() == "":
                    continue
                    
                city_name = "National"
                metric = "Price"
                
                if "Average Price" in h:
                    city_name = "National"
                    metric = "Average Price"
                elif "% Change" in h or "% change" in h:
                    city_name = "National"
                    metric = "% Change"
                else:
                    city_name = h.split('(')[0].strip()
                    if "per litre" in h.lower() or "per kg" in h.lower():
                        city_name = "National"
                        metric = h
                
                records.append([filename, date, table_name, item_no, item_desc, unit, city_name, metric, val])
                
    return records

def main():
    files = glob.glob("Annex_*.xlsx")
    all_records = []
    
    print(f"Found {len(files)} files to process.")
    for f in files:
        print(f"Processing {f}...")
        date = extract_date_from_filename(f)
        try:
            xl = pd.ExcelFile(f)
            
            if "Appendix-A" in xl.sheet_names:
                df_a = xl.parse("Appendix-A", header=None)
                all_records.extend(process_appendix_a(df_a, date, f))
                
            if "Appendix-B" in xl.sheet_names:
                df_b = xl.parse("Appendix-B", header=None)
                all_records.extend(process_appendix_b(df_b, date, f))
                
        except Exception as e:
            print(f"Error processing {f}: {e}")
            
    columns = ["Source_File", "Date", "Category", "Item_No", "Item_Description", "Unit", "City", "Metric", "Value"]
    final_df = pd.DataFrame(all_records, columns=columns)
    
    # Clean up any potential messy text in values
    final_df['Value'] = pd.to_numeric(final_df['Value'], errors='coerce')
    # Filter out perfectly empty values that were coerced to NaN
    final_df = final_df.dropna(subset=['Value'])
    
    output_file = "combined_data.csv"
    final_df.to_csv(output_file, index=False)
    print(f"Successfully generated {output_file} with {len(final_df)} records.")

if __name__ == "__main__":
    main()
