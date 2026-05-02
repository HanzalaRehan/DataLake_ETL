import pandas as pd
import re
from datetime import datetime


# =====================================
# HARD DATE NORMALIZER (NO EXCEPTIONS)
# =====================================
def force_dd_mm_yyyy(date_str):
    if not isinstance(date_str, str):
        return None

    date_str = date_str.strip()

    parts = re.split(r"[/-]", date_str)

    #  ONLY numeric DD-MM-YYYY
    if (
        len(parts) == 3 and
        all(p.isdigit() for p in parts)
    ):
        try:
            day, month, year = map(int, parts)

            if year == 2025:
                return None

            dt = datetime(year, month, day)
            return dt.strftime("%d-%m-%Y")
        except:
            pass  # <-- IMPORTANT: do NOT return here

    #  Let pandas handle month names
    try:
        dt = pd.to_datetime(date_str, dayfirst=True, errors="coerce")
        if pd.isna(dt) or dt.year == 2025:
            return None
        return dt.strftime("%d-%m-%Y")
    except:
        return None


# =====================================
# PARSE DAWN "time" COLUMN (FIXED)
# =====================================
def parse_published_time(s):
    if not isinstance(s, str):
        return None

    s = s.strip()

    # Drop relative times
    if re.search(r"(hour|day|minute|second)s?\s+ago", s, re.IGNORECASE):
        return None

    patterns = [
        # PublishedDecember 11, 2025  / Published June 1, 2023
        r"Published\s*([A-Za-z]+)\s*([0-9]{1,2}),?\s*([0-9]{4})",

        # Updated 01 Jun, 2023
        r"Updated\s*([0-9]{1,2})\s*([A-Za-z]+),?\s*([0-9]{4})",

        # 15 Dec, 2025
        r"^([0-9]{1,2})\s*([A-Za-z]+),?\s*([0-9]{4})"
    ]

    for p in patterns:
        m = re.search(p, s)
        if m:
            a, b, c = m.groups()

            if a.isdigit():
                return force_dd_mm_yyyy(f"{a}-{b}-{c}")
            else:
                return force_dd_mm_yyyy(f"{b}-{a}-{c}")

    return None

# =====================================
# LOCATION EXTRACTOR
# =====================================
def extract_location(text):
    if not isinstance(text, str):
        return "unknown"

    m = re.match(r"^([A-Z][A-Z\s\-]+):", text)
    if m:
        return m.group(1)

    return "unknown"


# =====================================
# STOPWORD AND PUNCTUATION REMOVER
# =====================================


def clean_text(text, min_len=3, remove_numbers=False):
    """
    Lowercase, remove URLs and non-alphanumeric (keep spaces)
    """
    if not isinstance(text, str) or len(text.strip()) == 0:
        return []

    # Lowercase
    text = text.lower()

    # Remove URLs
    text = re.sub(r"http\S+|www\.\S+", " ", text)

    # Replace non-alphanumeric (but keep spaces)
    if remove_numbers:
        text = re.sub(r"[^a-z\s]", " ", text)
    else:
        text = re.sub(r"[^a-z0-9\s]", " ", text)

    # Collapse spaces
    text = re.sub(r"\s+", " ", text).strip()

    return text



def main():
    # =====================================
    # PROCESS dawn.csv
    # =====================================
    df_dawn = pd.read_csv("dawn.csv", encoding="MacRoman")
    df_dawn = df_dawn[["headline", "date", "link", "description"]].copy()

    df_dawn["date"] = df_dawn["date"].astype(str).apply(force_dd_mm_yyyy)
    df_dawn["date"] = df_dawn["date"].str.replace("/", "-", regex=False)
    df_dawn["date"] = pd.to_datetime(df_dawn["date"], format="%d-%m-%Y", errors="coerce")
    df_dawn = df_dawn.dropna(subset=["date"])

    df_dawn = df_dawn.dropna(subset=["date"])

    df_dawn["location"] = df_dawn["description"].apply(extract_location)

    df_dawn = df_dawn.rename(columns={
        "headline": "title",
        "description": "text",
        "link": "url"
    })
    
    df_dawn["title"] = df_dawn["title"].astype(str).apply(clean_text)
    df_dawn["text"] = df_dawn["text"].astype(str).apply(clean_text)
    
    df_dawn["id"] = range(1, len(df_dawn) + 1)

    df_dawn_1 = df_dawn[["id", "date", "location", "title", "text"]]
    df_dawn_2 = df_dawn[["id", "title", "url"]]

    # =====================================
    # PROCESS dawn_test_merged.csv
    # =====================================
    df_test = pd.read_csv("dawn_test_merged.csv", encoding="latin1")

    # Remove junk header row
    df_test = df_test[df_test["date"] != "date"]
    
    df_test["title"] = df_test["title"].astype(str).apply(clean_text)
    df_test["text"] = df_test["text"].astype(str).apply(clean_text)
    
    start_id = len(df_dawn) + 1
    df_test["id"] = range(start_id, start_id + len(df_test))

    df_test["date"] = df_test["time"].apply(parse_published_time)
    df_test["date"] = df_test["date"].astype(str).apply(force_dd_mm_yyyy)
    df_test["date"] = df_test["date"].str.replace("/", "-", regex=False)
    df_test["date"] = pd.to_datetime(df_test["date"], format="%d-%m-%Y", errors="coerce")
    df_test = df_test.dropna(subset=["date"])

    df_test = df_test.dropna(subset=["date"])

    df_test["location"] = df_test["text"].apply(extract_location)

    df_test_1 = df_test[["id", "date", "location", "title", "text"]]
    df_test_2 = df_test[["id", "title", "url"]]
    
    # =====================================
    # PROCESS dawn_test_janjua.csv
    # =====================================
    df_janj = pd.read_csv("dawn_test_janjua.csv", encoding="latin1")

    # Remove junk header row
    df_janj = df_janj[df_janj["date"] != "date"]
    
    df_janj["title"] = df_janj["title"].astype(str).apply(clean_text)
    df_janj["text"] = df_janj["text"].astype(str).apply(clean_text)
    
    start_id = len(df_dawn) + len(df_test) + 1
    df_janj["id"] = range(start_id, start_id + len(df_janj))

    df_janj["date"] = df_janj["time"].apply(parse_published_time)
    df_janj["date"] = df_janj["date"].astype(str).apply(force_dd_mm_yyyy)
    df_janj["date"] = df_janj["date"].str.replace("/", "-", regex=False)
    df_janj["date"] = pd.to_datetime(df_janj["date"], format="%d-%m-%Y", errors="coerce")
    df_janj = df_janj.dropna(subset=["date"])

    df_janj["location"] = df_janj["text"].apply(extract_location)

    df_janj_1 = df_janj[["id", "date", "location", "title", "text"]]
    df_janj_2 = df_janj[["id", "title", "url"]]
    
    df_1 = pd.concat(
        [df_dawn_1, df_test_1, df_janj_1],
        ignore_index=True
    )

    df_2 = pd.concat(
        [df_dawn_2, df_test_2, df_janj_2],
        ignore_index=True
    )
    
    df_1.to_csv("dawn_content.csv", index=False, encoding="utf-8")
    df_2.to_csv("dawn_links.csv", index=False, encoding="utf-8")
    

if __name__ == "__main__":
    main()