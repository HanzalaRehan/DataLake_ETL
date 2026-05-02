import pdfplumber
import pandas as pd
import re
import traceback

def clean_text(text):
    if text is None:
        return ""
    return str(text).replace('\n', ' ').strip()

def is_province(text):
    text = clean_text(text)
    if not text:
        return False
    # Provinces are typically ALL CAPS and might have trailing spaces
    return text.isupper() and len(text) > 2 and text.lower() not in ["total", "pakistan", "province/district", "province/ district", "province / district"]

def extract_crop_data(pdf_path):
    records = []
    
    with pdfplumber.open(pdf_path) as pdf:
        current_crop = "Unknown"
        
        for page_num, page in enumerate(pdf.pages):
            text = page.extract_text()
            if text:
                # Look for crop names in the text, e.g. "Table 1: WHEAT", or just bold headers.
                lines = text.split('\n')
                for line in lines[:15]: # Look at the top 15 lines
                    line_clean = line.strip().upper()
                    # A basic heuristic to catch table titles
                    if "WHEAT" in line_clean: current_crop = "Wheat"
                    elif "RICE" in line_clean: current_crop = "Rice"
                    elif "MAIZE" in line_clean: current_crop = "Maize"
                    elif "COTTON" in line_clean: current_crop = "Cotton"
                    elif "SUGARCANE" in line_clean: current_crop = "Sugarcane"
                    elif "GRAM" in line_clean: current_crop = "Gram"
                    elif "BAJRA" in line_clean: current_crop = "Bajra"
                    elif "JAWAR" in line_clean: current_crop = "Jawar"
                    elif "BARLEY" in line_clean: current_crop = "Barley"
                    elif "RAPESEED" in line_clean: current_crop = "Rapeseed & Mustard"
                    elif "SESAMUM" in line_clean: current_crop = "Sesamum"
                    elif "TOBACCO" in line_clean: current_crop = "Tobacco"
                    elif "POTATO" in line_clean: current_crop = "Potato"
                    elif "ONION" in line_clean: current_crop = "Onion"
                    elif "CHILIES" in line_clean: current_crop = "Chilies"
                    elif "MOONG" in line_clean: current_crop = "Moong"
                    elif "MASH" in line_clean: current_crop = "Mash"
                    elif "MASOOR" in line_clean: current_crop = "Masoor"

            tables = page.extract_tables()
            for table in tables:
                if not table or len(table) < 2:
                    continue
                
                # Check if it's the expected 9-column format or close to it
                if len(table[0]) != 9:
                    # sometimes tables might be parsed with 10 columns if there's an empty line
                    # Let's clean empty columns
                    continue
                    
                current_province = "Unknown"
                
                for row_idx, row in enumerate(table):
                    # Skip headers
                    first_col = clean_text(row[0])
                    if "Province" in first_col or first_col == "":
                        continue
                        
                    # Check for Pakistan Total
                    if "Pakistan" in first_col or "PAKISTAN" in first_col:
                        continue 
                        
                    # Check if it's a Province row
                    if is_province(first_col):
                        current_province = first_col.title()
                        district = "Total" # The row itself often contains the provincial total
                    else:
                        district = first_col
                        
                    if "Total" in first_col or "TOTAL" in first_col:
                        district = "Total"
                        
                    # Extract data
                    try:
                        area_21 = clean_text(row[1]).replace(',', '')
                        area_share_21 = clean_text(row[2]).replace(',', '')
                        area_22 = clean_text(row[3]).replace(',', '')
                        area_share_22 = clean_text(row[4]).replace(',', '')
                        
                        prod_21 = clean_text(row[5]).replace(',', '')
                        prod_share_21 = clean_text(row[6]).replace(',', '')
                        prod_22 = clean_text(row[7]).replace(',', '')
                        prod_share_22 = clean_text(row[8]).replace(',', '')
                        
                        # Skip if all data fields are empty or just dashes
                        has_data = any(x and x != '-' and x != 'N.A.' for x in [area_21, area_22, prod_21, prod_22])
                        if has_data:
                            # 2021-22 Record
                            records.append({
                                "Crop": current_crop,
                                "Province": current_province,
                                "District": district,
                                "Year": "2021-22",
                                "Area_000_Hectares": area_21,
                                "Area_Percent_Share": area_share_21,
                                "Production_000_Tons": prod_21,
                                "Production_Percent_Share": prod_share_21
                            })
                            
                            # 2022-23 Record
                            records.append({
                                "Crop": current_crop,
                                "Province": current_province,
                                "District": district,
                                "Year": "2022-23",
                                "Area_000_Hectares": area_22,
                                "Area_Percent_Share": area_share_22,
                                "Production_000_Tons": prod_22,
                                "Production_Percent_Share": prod_share_22
                            })
                    except IndexError:
                        pass # Row might be malformed

    # Convert to DataFrame
    df = pd.DataFrame(records)
    
    # Clean up hyphens and N/A
    df.replace({'-': pd.NA, '': pd.NA, 'N.A.': pd.NA, 'N. A': pd.NA, 'N A': pd.NA}, inplace=True)
    
    # Filter out rows that are actually headers
    df = df[~df['Area_000_Hectares'].astype(str).str.contains("'000'|Hectares|Tons", case=False, na=False)]
    df = df[~df['Production_000_Tons'].astype(str).str.contains("'000'|Hectares|Tons", case=False, na=False)]
    
    return df

if __name__ == "__main__":
    pdf_file = "Crops Area AND Production by 2022-23.pdf"
    print(f"Starting extraction from {pdf_file}...")
    try:
        df = extract_crop_data(pdf_file)
        output_file = "combined_crop_data.csv"
        df.to_csv(output_file, index=False)
        print(f"Successfully extracted {len(df)} records.")
        print(f"Data saved to {output_file}")
        
        # Display summary
        print("\n--- Data Summary ---")
        if not df.empty:
            print(f"Total Crops found: {df['Crop'].nunique()} ({', '.join(df['Crop'].unique()[:5])}...)")
            print(f"Total Provinces: {df['Province'].nunique()} ({', '.join(df['Province'].unique())})")
            print("\nSample records:")
            print(df.head())
        else:
            print("No data extracted!")
    except Exception as e:
        print(f"An error occurred: {e}")
        traceback.print_exc()