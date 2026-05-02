-- =============================================================================
-- DATA LAKE SQL: BRONZE → SILVER → GOLD
-- Covers: GDP, PSX, Price Data, Trade (Table2), Mineral Production,
--         Crop Data, CSV1 Core  (7 files provided; slot 8 reserved)
-- Engine: PostgreSQL-compatible syntax
-- =============================================================================


-- =============================================================================
-- ██████  ██████   ██████  ███    ██ ███████ ███████
-- ██   ██ ██   ██ ██    ██ ████   ██    ███  ██
-- ██████  ██████  ██    ██ ██ ██  ██   ███   █████
-- ██   ██ ██   ██ ██    ██ ██  ██ ██  ███    ██
-- ██████  ██   ██  ██████  ██   ████ ███████ ███████
--
-- LAYER 1: BRONZE — Raw ingestion, no transformation
-- =============================================================================

CREATE SCHEMA IF NOT EXISTS bronze;

-- ---------------------------------------------------------------------------
-- 1. GDP TABLE
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS bronze.gdp_table (
    s_no            TEXT,
    sector_industry TEXT,
    "1999-2000"     TEXT,
    "2000-01"       TEXT,
    "2001-02"       TEXT,
    "2002-03"       TEXT,
    "2003-04"       TEXT,
    "2004-05"       TEXT,
    "2005-06"       TEXT,
    "2006-07"       TEXT,
    "2007-08"       TEXT,
    "2008-09"       TEXT,
    "2009-10"       TEXT,
    "2010-11"       TEXT,
    "2011-12"       TEXT,
    "2012-13"       TEXT,
    "2013-14"       TEXT,
    "2014-15"       TEXT,
    "2015-16"       TEXT,
    "2016-17"       TEXT,
    "2017-18"       TEXT,
    "2018-19"       TEXT,
    "2019-20"       TEXT,
    "2020-21"       TEXT,
    "2021-22"       TEXT,
    "2022-23"       TEXT,
    "2023-24"       TEXT,
    "2024-25"       TEXT,
    _ingested_at    TIMESTAMP DEFAULT NOW(),
    _source_file    TEXT DEFAULT 'GDP_table.csv'
);

-- ---------------------------------------------------------------------------
-- 2. PSX HISTORICAL DATA
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS bronze.psx_historical_data (
    date         TEXT,
    symbol       TEXT,
    ldcp         TEXT,
    open         TEXT,
    high         TEXT,
    low          TEXT,
    close        TEXT,
    volume       TEXT,
    _ingested_at TIMESTAMP DEFAULT NOW(),
    _source_file TEXT DEFAULT 'psx_historical_data.csv'
);

-- ---------------------------------------------------------------------------
-- 3. PRICE DATA
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS bronze.price_data (
    source_file      TEXT,
    date             TEXT,
    category         TEXT,
    item_no          TEXT,
    item_description TEXT,
    unit             TEXT,
    city             TEXT,
    metric           TEXT,
    value            TEXT,
    _ingested_at     TIMESTAMP DEFAULT NOW(),
    _source_file     TEXT DEFAULT 'price_data.csv'
);

-- ---------------------------------------------------------------------------
-- 4. TABLE2 ALL YEARS (Trade / Imports)
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS bronze.table2_all_years (
    source_pdf   TEXT,
    year         TEXT,
    s_no         TEXT,
    items        TEXT,
    unit         TEXT,
    weight       TEXT,
    jul          TEXT,
    aug          TEXT,
    sep          TEXT,
    oct          TEXT,
    nov          TEXT,
    dec          TEXT,
    jan          TEXT,
    feb          TEXT,
    mar          TEXT,
    apr          TEXT,
    may          TEXT,
    jun          TEXT,
    year_total   TEXT,
    page         TEXT,
    table_index  TEXT,
    _ingested_at TIMESTAMP DEFAULT NOW(),
    _source_file TEXT DEFAULT 'table2_all_years.csv'
);

-- ---------------------------------------------------------------------------
-- 5. MINERAL PRODUCTION ALL YEARS
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS bronze.mineral_production_all_years (
    source_file  TEXT,
    source_kind  TEXT,
    source_sheet TEXT,
    fiscal_year  TEXT,   -- maps to column "2002-03" in raw CSV
    mineral      TEXT,
    province     TEXT,
    period_type  TEXT,
    period_order TEXT,
    period       TEXT,
    value        TEXT,
    unit         TEXT,
    _ingested_at TIMESTAMP DEFAULT NOW(),
    _source_file TEXT DEFAULT 'mineral_production_all_years.csv'
);

-- ---------------------------------------------------------------------------
-- 6. COMBINED CROP DATA
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS bronze.combined_crop_data (
    crop                     TEXT,
    province                 TEXT,
    district                 TEXT,
    year                     TEXT,
    area_000_hectares        TEXT,
    area_percent_share       TEXT,
    production_000_tons      TEXT,
    production_percent_share TEXT,
    _ingested_at             TIMESTAMP DEFAULT NOW(),
    _source_file             TEXT DEFAULT 'combined_crop_data.csv'
);

-- ---------------------------------------------------------------------------
-- 7. CSV1 CORE (News / Sentiment)
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS bronze.csv1_core (
    id           TEXT,
    date         TEXT,
    category     TEXT,
    location     TEXT,
    sentiment    TEXT,
    _ingested_at TIMESTAMP DEFAULT NOW(),
    _source_file TEXT DEFAULT 'csv1_core.csv'
);

-- ---------------------------------------------------------------------------
-- 8. [RESERVED — Slot for 8th CSV]
-- ---------------------------------------------------------------------------
-- CREATE TABLE IF NOT EXISTS bronze.table_8 ( ... );


-- =============================================================================
-- ███████ ██ ██      ██    ██ ███████ ██████
-- ██      ██ ██      ██    ██ ██      ██   ██
-- ███████ ██ ██      ██    ██ █████   ██████
--      ██ ██ ██       ██  ██  ██      ██   ██
-- ███████ ██ ███████   ████   ███████ ██   ██
--
-- LAYER 2: SILVER — Cleaned, typed, joined, deduplicated
-- =============================================================================

CREATE SCHEMA IF NOT EXISTS silver;

-- =============================================================================
-- REJECT / QUARANTINE TABLE (shared across all silver loads)
-- =============================================================================
CREATE TABLE IF NOT EXISTS silver.rejected_records (
    reject_id       BIGSERIAL PRIMARY KEY,
    source_table    TEXT        NOT NULL,   -- e.g. 'bronze.psx_historical_data'
    rejected_at     TIMESTAMP   DEFAULT NOW(),
    reject_reason   TEXT        NOT NULL,   -- e.g. 'NULL close price', 'Duplicate PK'
    raw_record      JSONB       NOT NULL    -- original row stored as JSON for audit
);

-- ---------------------------------------------------------------------------
-- SILVER 1: GDP — Unpivoted (wide → long) + typed
-- ---------------------------------------------------------------------------
-- The raw GDP table is "wide" (one column per fiscal year).
-- Silver unpivots it so each row is (sector, fiscal_year, value).

CREATE TABLE IF NOT EXISTS silver.gdp (
    gdp_id          BIGSERIAL PRIMARY KEY,
    s_no            TEXT,
    sector_industry TEXT        NOT NULL,
    fiscal_year     CHAR(7)     NOT NULL,   -- e.g. '2000-01'
    value_pkr_mn    NUMERIC(20,4),          -- NULL when source cell is empty
    is_growth_row   BOOLEAN     DEFAULT FALSE,
    _loaded_at      TIMESTAMP   DEFAULT NOW()
);

INSERT INTO silver.gdp (s_no, sector_industry, fiscal_year, value_pkr_mn, is_growth_row)

-- Pattern: UNION ALL one SELECT per fiscal year column
-- (Abbreviated for 3 years; extend identically for all 25 years)

SELECT
    NULLIF(TRIM(s_no), '')                        AS s_no,
    TRIM(sector_industry)                         AS sector_industry,
    '2000-01'                                     AS fiscal_year,
    CASE WHEN TRIM("2000-01") = '' OR "2000-01" IS NULL
         THEN NULL
         ELSE ROUND("2000-01"::NUMERIC, 4) END    AS value_pkr_mn,
    (TRIM(sector_industry) ILIKE '%gdp growth rate%') AS is_growth_row
FROM bronze.gdp_table
WHERE TRIM(sector_industry) IS NOT NULL
  AND TRIM(sector_industry) <> ''

UNION ALL

SELECT
    NULLIF(TRIM(s_no), ''),
    TRIM(sector_industry),
    '2001-02',
    CASE WHEN TRIM("2001-02") = '' OR "2001-02" IS NULL THEN NULL
         ELSE ROUND("2001-02"::NUMERIC, 4) END,
    (TRIM(sector_industry) ILIKE '%gdp growth rate%')
FROM bronze.gdp_table
WHERE TRIM(sector_industry) IS NOT NULL AND TRIM(sector_industry) <> ''

UNION ALL

SELECT
    NULLIF(TRIM(s_no), ''),
    TRIM(sector_industry),
    '2002-03',
    CASE WHEN TRIM("2002-03") = '' OR "2002-03" IS NULL THEN NULL
         ELSE ROUND("2002-03"::NUMERIC, 4) END,
    (TRIM(sector_industry) ILIKE '%gdp growth rate%')
FROM bronze.gdp_table
WHERE TRIM(sector_industry) IS NOT NULL AND TRIM(sector_industry) <> ''
-- ... repeat UNION ALL blocks for 2003-04 through 2024-25 ...
;

-- Reject GDP rows where sector_industry is blank (header artifacts)
INSERT INTO silver.rejected_records (source_table, reject_reason, raw_record)
SELECT
    'bronze.gdp_table',
    'Empty sector_industry — likely header or blank row',
    ROW_TO_JSON(g)::JSONB
FROM bronze.gdp_table g
WHERE TRIM(sector_industry) IS NULL OR TRIM(sector_industry) = '';


-- ---------------------------------------------------------------------------
-- SILVER 2: PSX HISTORICAL DATA
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS silver.psx_historical_data (
    psx_id       BIGSERIAL   PRIMARY KEY,
    trade_date   DATE        NOT NULL,
    symbol       TEXT        NOT NULL,
    ldcp         NUMERIC(12,4),
    open_price   NUMERIC(12,4),
    high_price   NUMERIC(12,4),
    low_price    NUMERIC(12,4),
    close_price  NUMERIC(12,4),
    price_change NUMERIC(12,4),           -- renamed from 'volume' (raw header is misleading)
    _loaded_at   TIMESTAMP   DEFAULT NOW(),
    CONSTRAINT uq_psx_date_symbol UNIQUE (trade_date, symbol)
);

-- Reject rows: unparseable date OR null close price
INSERT INTO silver.rejected_records (source_table, reject_reason, raw_record)
SELECT
    'bronze.psx_historical_data',
    CASE
        WHEN date !~ '^\d{4}-\d{2}-\d{2}$'     THEN 'Invalid date format'
        WHEN close IS NULL OR TRIM(close) = ''  THEN 'NULL close price'
        WHEN symbol IS NULL OR TRIM(symbol) = '' THEN 'NULL symbol'
    END,
    ROW_TO_JSON(p)::JSONB
FROM bronze.psx_historical_data p
WHERE date !~ '^\d{4}-\d{2}-\d{2}$'
   OR close IS NULL OR TRIM(close) = ''
   OR symbol IS NULL OR TRIM(symbol) = '';

-- Load clean rows (deduplication via ON CONFLICT)
INSERT INTO silver.psx_historical_data
    (trade_date, symbol, ldcp, open_price, high_price, low_price, close_price, price_change)
SELECT
    date::DATE,
    UPPER(TRIM(symbol)),
    NULLIF(TRIM(ldcp),  '')::NUMERIC,
    NULLIF(TRIM(open),  '')::NUMERIC,
    NULLIF(TRIM(high),  '')::NUMERIC,
    NULLIF(TRIM(low),   '')::NUMERIC,
    NULLIF(TRIM(close), '')::NUMERIC,
    NULLIF(TRIM(volume),'')::NUMERIC
FROM bronze.psx_historical_data
WHERE date ~ '^\d{4}-\d{2}-\d{2}$'
  AND close IS NOT NULL AND TRIM(close) <> ''
  AND symbol IS NOT NULL AND TRIM(symbol) <> ''
ON CONFLICT (trade_date, symbol) DO NOTHING;   -- deduplication


-- ---------------------------------------------------------------------------
-- SILVER 3: PRICE DATA
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS silver.price_data (
    price_id         BIGSERIAL  PRIMARY KEY,
    source_file      TEXT,
    price_date       DATE       NOT NULL,
    category         TEXT,
    item_no          INTEGER,
    item_description TEXT       NOT NULL,
    unit             TEXT,
    city             TEXT       NOT NULL,
    metric           TEXT       NOT NULL,   -- MIN / AVG / MAX
    value_pkr        NUMERIC(14,4) NOT NULL,
    _loaded_at       TIMESTAMP  DEFAULT NOW(),
    CONSTRAINT uq_price UNIQUE (price_date, item_no, city, metric)
);

-- Rejects: bad date, non-numeric value, metric not in allowed set
INSERT INTO silver.rejected_records (source_table, reject_reason, raw_record)
SELECT
    'bronze.price_data',
    CASE
        WHEN date !~ '^\d{4}-\d{2}-\d{2}$'          THEN 'Invalid date'
        WHEN value ~ '[^0-9.\-]'                     THEN 'Non-numeric value'
        WHEN UPPER(TRIM(metric)) NOT IN ('MIN','AVG','MAX') THEN 'Unknown metric type'
        WHEN city IS NULL OR TRIM(city) = ''         THEN 'NULL city'
    END,
    ROW_TO_JSON(p)::JSONB
FROM bronze.price_data p
WHERE date !~ '^\d{4}-\d{2}-\d{2}$'
   OR value ~ '[^0-9.\-]'
   OR UPPER(TRIM(metric)) NOT IN ('MIN','AVG','MAX')
   OR city IS NULL OR TRIM(city) = '';

INSERT INTO silver.price_data
    (source_file, price_date, category, item_no, item_description, unit, city, metric, value_pkr)
SELECT
    TRIM(source_file),
    date::DATE,
    INITCAP(TRIM(category)),
    NULLIF(TRIM(item_no),'')::INTEGER,
    INITCAP(TRIM(item_description)),
    TRIM(unit),
    INITCAP(TRIM(city)),
    UPPER(TRIM(metric)),
    value::NUMERIC
FROM bronze.price_data
WHERE date ~ '^\d{4}-\d{2}-\d{2}$'
  AND value !~ '[^0-9.\-]'
  AND UPPER(TRIM(metric)) IN ('MIN','AVG','MAX')
  AND city IS NOT NULL AND TRIM(city) <> ''
ON CONFLICT (price_date, item_no, city, metric) DO NOTHING;


-- ---------------------------------------------------------------------------
-- SILVER 4: TABLE2 ALL YEARS (Trade Imports — monthly)
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS silver.trade_imports (
    import_id    BIGSERIAL  PRIMARY KEY,
    source_pdf   TEXT,
    fiscal_year  CHAR(7)    NOT NULL,
    s_no         TEXT,
    items        TEXT       NOT NULL,
    unit         TEXT,
    weight       NUMERIC(10,4),
    month_name   TEXT       NOT NULL,   -- 'Jul'..'Jun'
    month_value  NUMERIC(18,2),         -- NULL = not reported
    year_total   NUMERIC(18,2),
    page         INTEGER,
    table_index  INTEGER,
    _loaded_at   TIMESTAMP  DEFAULT NOW()
);

-- Unpivot 12 month columns → rows
INSERT INTO silver.trade_imports
    (source_pdf, fiscal_year, s_no, items, unit, weight,
     month_name, month_value, year_total, page, table_index)

SELECT source_pdf, year, s_no, TRIM(items), unit,
       NULLIF(TRIM(weight),'')::NUMERIC,
       m.month_name,
       NULLIF(TRIM(m.raw_val),'')::NUMERIC,
       NULLIF(TRIM(year_total),'')::NUMERIC,
       NULLIF(TRIM(page),'')::INTEGER,
       NULLIF(TRIM(table_index),'')::INTEGER
FROM bronze.table2_all_years t
CROSS JOIN LATERAL (VALUES
    ('Jul', t.jul), ('Aug', t.aug), ('Sep', t.sep), ('Oct', t.oct),
    ('Nov', t.nov), ('Dec', t.dec), ('Jan', t.jan), ('Feb', t.feb),
    ('Mar', t.mar), ('Apr', t.apr), ('May', t.may), ('Jun', t.jun)
) AS m(month_name, raw_val)
WHERE TRIM(items) IS NOT NULL AND TRIM(items) <> '';

-- Rejects: blank items name
INSERT INTO silver.rejected_records (source_table, reject_reason, raw_record)
SELECT 'bronze.table2_all_years', 'Blank items field', ROW_TO_JSON(t)::JSONB
FROM bronze.table2_all_years t
WHERE TRIM(items) IS NULL OR TRIM(items) = '';


-- ---------------------------------------------------------------------------
-- SILVER 5: MINERAL PRODUCTION
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS silver.mineral_production (
    mineral_id   BIGSERIAL  PRIMARY KEY,
    source_file  TEXT,
    fiscal_year  CHAR(7)    NOT NULL,
    mineral      TEXT       NOT NULL,
    province     TEXT       NOT NULL,
    period_type  TEXT,                    -- 'month' or 'annual'
    period_order INTEGER,
    period       TEXT,                    -- e.g. '2-Jul'
    value        NUMERIC(18,4),
    unit         TEXT,
    _loaded_at   TIMESTAMP  DEFAULT NOW()
);

-- Rejects: non-numeric value or blank mineral/province
INSERT INTO silver.rejected_records (source_table, reject_reason, raw_record)
SELECT 'bronze.mineral_production_all_years',
       CASE
           WHEN value ~ '[^0-9.\-]'               THEN 'Non-numeric value'
           WHEN TRIM(mineral) = '' OR mineral IS NULL THEN 'Blank mineral name'
           WHEN TRIM(province) = '' OR province IS NULL THEN 'Blank province'
       END,
       ROW_TO_JSON(m)::JSONB
FROM bronze.mineral_production_all_years m
WHERE value ~ '[^0-9.\-]'
   OR TRIM(mineral) = '' OR mineral IS NULL
   OR TRIM(province) = '' OR province IS NULL;

INSERT INTO silver.mineral_production
    (source_file, fiscal_year, mineral, province, period_type, period_order, period, value, unit)
SELECT
    TRIM(source_file),
    TRIM(fiscal_year),
    UPPER(TRIM(REGEXP_REPLACE(mineral, '[()]', '', 'g'))),  -- strip parens e.g. "(ONYX)" → "ONYX"
    INITCAP(TRIM(province)),
    LOWER(TRIM(period_type)),
    NULLIF(TRIM(period_order),'')::INTEGER,
    TRIM(period),
    value::NUMERIC,
    UPPER(TRIM(unit))
FROM bronze.mineral_production_all_years
WHERE (value !~ '[^0-9.\-]')
  AND TRIM(mineral) <> '' AND mineral IS NOT NULL
  AND TRIM(province) <> '' AND province IS NOT NULL;


-- ---------------------------------------------------------------------------
-- SILVER 6: COMBINED CROP DATA
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS silver.crop_data (
    crop_id                  BIGSERIAL  PRIMARY KEY,
    crop                     TEXT       NOT NULL,
    province                 TEXT       NOT NULL,
    district                 TEXT       NOT NULL,
    fiscal_year              CHAR(7)    NOT NULL,
    area_000_hectares        NUMERIC(12,4),
    area_percent_share       NUMERIC(6,2),
    production_000_tons      NUMERIC(12,4),
    production_percent_share NUMERIC(6,2),
    _loaded_at               TIMESTAMP  DEFAULT NOW(),
    CONSTRAINT uq_crop UNIQUE (crop, province, district, fiscal_year)
);

-- Rejects: negative area or production
INSERT INTO silver.rejected_records (source_table, reject_reason, raw_record)
SELECT 'bronze.combined_crop_data',
       'Negative area or production value',
       ROW_TO_JSON(c)::JSONB
FROM bronze.combined_crop_data c
WHERE NULLIF(TRIM(area_000_hectares),'')::NUMERIC < 0
   OR NULLIF(TRIM(production_000_tons),'')::NUMERIC < 0;

INSERT INTO silver.crop_data
    (crop, province, district, fiscal_year,
     area_000_hectares, area_percent_share,
     production_000_tons, production_percent_share)
SELECT
    INITCAP(TRIM(crop)),
    INITCAP(TRIM(province)),
    INITCAP(TRIM(district)),
    TRIM(year),
    NULLIF(TRIM(area_000_hectares),'')::NUMERIC,
    NULLIF(TRIM(area_percent_share),'')::NUMERIC,
    NULLIF(TRIM(production_000_tons),'')::NUMERIC,
    NULLIF(TRIM(production_percent_share),'')::NUMERIC
FROM bronze.combined_crop_data
WHERE NULLIF(TRIM(area_000_hectares),'')::NUMERIC >= 0
  AND NULLIF(TRIM(production_000_tons),'')::NUMERIC >= 0
ON CONFLICT (crop, province, district, fiscal_year) DO NOTHING;


-- ---------------------------------------------------------------------------
-- SILVER 7: CSV1 CORE (Sentiment)
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS silver.news_sentiment (
    sentiment_id  BIGSERIAL  PRIMARY KEY,
    original_id   INTEGER    NOT NULL,
    event_date    DATE       NOT NULL,
    category      TEXT       NOT NULL,
    location      TEXT,                  -- 'unknown' standardised to NULL
    sentiment     TEXT       NOT NULL,   -- Positive / Negative / Neutral
    _loaded_at    TIMESTAMP  DEFAULT NOW(),
    CONSTRAINT uq_sentiment_id UNIQUE (original_id)
);

-- Rejects: non-integer id, bad date, sentiment not in allowed set
INSERT INTO silver.rejected_records (source_table, reject_reason, raw_record)
SELECT 'bronze.csv1_core',
       CASE
           WHEN id !~ '^\d+$'         THEN 'Non-integer ID'
           WHEN date !~ '^\d{4}-\d{2}-\d{2}$' THEN 'Invalid date'
           WHEN INITCAP(TRIM(sentiment)) NOT IN ('Positive','Negative','Neutral')
                                      THEN 'Invalid sentiment value'
       END,
       ROW_TO_JSON(c)::JSONB
FROM bronze.csv1_core c
WHERE id !~ '^\d+$'
   OR date !~ '^\d{4}-\d{2}-\d{2}$'
   OR INITCAP(TRIM(sentiment)) NOT IN ('Positive','Negative','Neutral');

INSERT INTO silver.news_sentiment
    (original_id, event_date, category, location, sentiment)
SELECT
    id::INTEGER,
    date::DATE,
    INITCAP(TRIM(category)),
    CASE WHEN LOWER(TRIM(location)) = 'unknown' THEN NULL
         ELSE INITCAP(TRIM(location)) END,
    INITCAP(TRIM(sentiment))
FROM bronze.csv1_core
WHERE id ~ '^\d+$'
  AND date ~ '^\d{4}-\d{2}-\d{2}$'
  AND INITCAP(TRIM(sentiment)) IN ('Positive','Negative','Neutral')
ON CONFLICT (original_id) DO NOTHING;


-- =============================================================================
-- ██████   █████  ████████  █████      �  ██████  ██    ██  █████  ██      ███████
-- ██   ██ ██   ██    ██    ██   ██    ██ ██    ██ ██    ██ ██   ██ ██      ██
-- ██   ██ ███████    ██    ███████   ██  ██    ██ ██    ██ ███████ ██      ███████
-- ██   ██ ██   ██    ██    ██   ██  ██   ██ ▄▄ ██ ██    ██ ██   ██ ██           ██
-- ██████  ██   ██    ██    ██   ██ ██     ██████   ██████  ██   ██ ███████ ███████
--
-- LAYER 2.5: DATA QUALITY CHECKS & REJECT SUMMARY
-- =============================================================================

-- ---------------------------------------------------------------------------
-- DQ-1  NULL CHECKS
-- ---------------------------------------------------------------------------
-- PSX: any critical NULL after load?
SELECT 'psx — null close_price' AS check_name, COUNT(*) AS failures
FROM silver.psx_historical_data WHERE close_price IS NULL

UNION ALL

-- Price: any null city?
SELECT 'price_data — null city', COUNT(*)
FROM silver.price_data WHERE city IS NULL

UNION ALL

-- Crop: null area or production
SELECT 'crop_data — null area_000_hectares', COUNT(*)
FROM silver.crop_data WHERE area_000_hectares IS NULL

UNION ALL

SELECT 'crop_data — null production_000_tons', COUNT(*)
FROM silver.crop_data WHERE production_000_tons IS NULL

UNION ALL

-- Mineral: null value
SELECT 'mineral_production — null value', COUNT(*)
FROM silver.mineral_production WHERE value IS NULL;


-- ---------------------------------------------------------------------------
-- DQ-2  RANGE CHECKS
-- ---------------------------------------------------------------------------
SELECT 'psx — close_price <= 0' AS check_name, COUNT(*) AS failures
FROM silver.psx_historical_data WHERE close_price <= 0

UNION ALL

SELECT 'psx — high < low', COUNT(*)
FROM silver.psx_historical_data WHERE high_price < low_price

UNION ALL

SELECT 'gdp — growth rate out of [-30, 30]%', COUNT(*)
FROM silver.gdp
WHERE is_growth_row = TRUE
  AND value_pkr_mn NOT BETWEEN -30 AND 30

UNION ALL

SELECT 'price_data — value <= 0', COUNT(*)
FROM silver.price_data WHERE value_pkr <= 0

UNION ALL

SELECT 'crop — area_percent_share > 100', COUNT(*)
FROM silver.crop_data WHERE area_percent_share > 100

UNION ALL

SELECT 'mineral — value < 0', COUNT(*)
FROM silver.mineral_production WHERE value < 0;


-- ---------------------------------------------------------------------------
-- DQ-3  DUPLICATE DETECTION
-- ---------------------------------------------------------------------------
-- (These should return 0 rows if ON CONFLICT DO NOTHING worked correctly)
SELECT 'psx — duplicate (date, symbol)' AS check_name, COUNT(*) AS dup_count
FROM (
    SELECT trade_date, symbol, COUNT(*) cnt
    FROM silver.psx_historical_data
    GROUP BY trade_date, symbol
    HAVING COUNT(*) > 1
) x

UNION ALL

SELECT 'price_data — duplicate (date, item_no, city, metric)', COUNT(*)
FROM (
    SELECT price_date, item_no, city, metric, COUNT(*) cnt
    FROM silver.price_data
    GROUP BY price_date, item_no, city, metric
    HAVING COUNT(*) > 1
) x

UNION ALL

SELECT 'crop — duplicate (crop, province, district, year)', COUNT(*)
FROM (
    SELECT crop, province, district, fiscal_year, COUNT(*) cnt
    FROM silver.crop_data
    GROUP BY crop, province, district, fiscal_year
    HAVING COUNT(*) > 1
) x;


-- ---------------------------------------------------------------------------
-- DQ-4  REJECT SUMMARY DASHBOARD
-- ---------------------------------------------------------------------------
SELECT
    source_table,
    reject_reason,
    COUNT(*)           AS reject_count,
    MIN(rejected_at)   AS first_seen,
    MAX(rejected_at)   AS last_seen
FROM silver.rejected_records
GROUP BY source_table, reject_reason
ORDER BY source_table, reject_count DESC;


-- =============================================================================
--  ██████   ██████  ██      ██████
-- ██       ██    ██ ██      ██   ██
-- ██   ███ ██    ██ ██      ██   ██
-- ██    ██ ██    ██ ██      ██   ██
--  ██████   ██████  ███████ ██████
--
-- LAYER 3: GOLD — Business-ready curated views & tables
-- =============================================================================

CREATE SCHEMA IF NOT EXISTS gold;

-- ---------------------------------------------------------------------------
-- GOLD 1: GDP SECTOR GROWTH (YoY % change per sector)
-- ---------------------------------------------------------------------------
CREATE OR REPLACE VIEW gold.gdp_sector_growth AS
WITH ranked AS (
    SELECT
        sector_industry,
        fiscal_year,
        value_pkr_mn,
        is_growth_row,
        LAG(value_pkr_mn) OVER (
            PARTITION BY sector_industry
            ORDER BY fiscal_year
        ) AS prev_value
    FROM silver.gdp
    WHERE is_growth_row = FALSE AND value_pkr_mn IS NOT NULL
)
SELECT
    sector_industry,
    fiscal_year,
    value_pkr_mn,
    prev_value,
    ROUND(
        ((value_pkr_mn - prev_value) / NULLIF(prev_value, 0)) * 100,
        2
    ) AS yoy_growth_pct
FROM ranked
ORDER BY sector_industry, fiscal_year;


-- ---------------------------------------------------------------------------
-- GOLD 2: PSX DAILY SUMMARY (OHLC + price change %)
-- ---------------------------------------------------------------------------
CREATE OR REPLACE VIEW gold.psx_daily_summary AS
SELECT
    trade_date,
    symbol,
    ldcp,
    open_price,
    high_price,
    low_price,
    close_price,
    price_change                                         AS abs_change,
    ROUND((price_change / NULLIF(ldcp, 0)) * 100, 4)    AS pct_change,
    high_price - low_price                               AS daily_range,
    CASE
        WHEN price_change > 0  THEN 'Up'
        WHEN price_change < 0  THEN 'Down'
        ELSE 'Flat'
    END                                                  AS direction
FROM silver.psx_historical_data
ORDER BY trade_date DESC, symbol;


-- ---------------------------------------------------------------------------
-- GOLD 3: PRICE INDEX — City-level monthly average per item
-- ---------------------------------------------------------------------------
CREATE OR REPLACE VIEW gold.price_index_monthly AS
SELECT
    DATE_TRUNC('month', price_date)::DATE  AS month,
    city,
    item_description,
    unit,
    MAX(CASE WHEN metric = 'MIN' THEN value_pkr END)  AS min_price,
    MAX(CASE WHEN metric = 'AVG' THEN value_pkr END)  AS avg_price,
    MAX(CASE WHEN metric = 'MAX' THEN value_pkr END)  AS max_price,
    MAX(CASE WHEN metric = 'MAX' THEN value_pkr END)
      - MAX(CASE WHEN metric = 'MIN' THEN value_pkr END) AS price_spread
FROM silver.price_data
GROUP BY 1, 2, 3, 4
ORDER BY 1 DESC, 2, 3;


-- ---------------------------------------------------------------------------
-- GOLD 4: TRADE IMPORT ANNUAL SUMMARY
-- ---------------------------------------------------------------------------
CREATE OR REPLACE VIEW gold.trade_import_annual AS
SELECT
    fiscal_year,
    items,
    unit,
    SUM(month_value)               AS computed_annual_total,
    MAX(year_total)                AS reported_annual_total,
    ABS(
        SUM(month_value) - MAX(year_total)
    )                              AS reconciliation_diff   -- flag if > 0
FROM silver.trade_imports
GROUP BY fiscal_year, items, unit
ORDER BY fiscal_year DESC, computed_annual_total DESC NULLS LAST;


-- ---------------------------------------------------------------------------
-- GOLD 5: MINERAL PRODUCTION — Province × Year summary
-- ---------------------------------------------------------------------------
CREATE OR REPLACE VIEW gold.mineral_production_summary AS
SELECT
    fiscal_year,
    province,
    mineral,
    unit,
    SUM(value)                        AS total_production,
    COUNT(DISTINCT period)            AS reporting_periods,
    ROUND(AVG(value), 2)              AS avg_per_period
FROM silver.mineral_production
WHERE period_type = 'month'
GROUP BY fiscal_year, province, mineral, unit
ORDER BY fiscal_year DESC, total_production DESC NULLS LAST;


-- ---------------------------------------------------------------------------
-- GOLD 6: CROP PERFORMANCE — Province × Crop × Year
-- ---------------------------------------------------------------------------
CREATE OR REPLACE VIEW gold.crop_performance AS
SELECT
    fiscal_year,
    crop,
    province,
    SUM(area_000_hectares)            AS total_area_000_ha,
    SUM(production_000_tons)          AS total_production_000_tons,
    ROUND(
        SUM(production_000_tons)
        / NULLIF(SUM(area_000_hectares), 0),
        4
    )                                 AS yield_tons_per_000_ha,
    COUNT(DISTINCT district)          AS districts_reporting
FROM silver.crop_data
GROUP BY fiscal_year, crop, province
ORDER BY fiscal_year DESC, total_production_000_tons DESC NULLS LAST;


-- ---------------------------------------------------------------------------
-- GOLD 7: SENTIMENT DASHBOARD — Daily category sentiment score
-- ---------------------------------------------------------------------------
CREATE OR REPLACE VIEW gold.sentiment_dashboard AS
SELECT
    event_date,
    category,
    COUNT(*)                                                  AS total_articles,
    SUM(CASE WHEN sentiment = 'Positive' THEN 1 ELSE 0 END)  AS positive_count,
    SUM(CASE WHEN sentiment = 'Negative' THEN 1 ELSE 0 END)  AS negative_count,
    SUM(CASE WHEN sentiment = 'Neutral'  THEN 1 ELSE 0 END)  AS neutral_count,
    ROUND(
        100.0 * SUM(CASE WHEN sentiment = 'Positive' THEN 1 ELSE 0 END)
        / NULLIF(COUNT(*), 0), 2
    )                                                         AS positive_pct,
    ROUND(
        100.0 * SUM(CASE WHEN sentiment = 'Negative' THEN 1 ELSE 0 END)
        / NULLIF(COUNT(*), 0), 2
    )                                                         AS negative_pct
FROM silver.news_sentiment
GROUP BY event_date, category
ORDER BY event_date DESC, category;


-- ---------------------------------------------------------------------------
-- GOLD 8: CROSS-DOMAIN — GDP growth vs Crop production (joined view)
-- ---------------------------------------------------------------------------
CREATE OR REPLACE VIEW gold.gdp_vs_crop_production AS
SELECT
    g.fiscal_year,
    g.value_pkr_mn                       AS agri_gdp_pkr_mn,
    g.yoy_growth_pct                     AS agri_gdp_growth_pct,
    cp.total_production_000_tons         AS wheat_production_000_tons,
    cp.yield_tons_per_000_ha             AS wheat_yield
FROM gold.gdp_sector_growth g
LEFT JOIN gold.crop_performance cp
    ON  cp.fiscal_year = g.fiscal_year
    AND cp.crop       = 'Wheat'
    AND cp.province   = 'Punjab'
WHERE g.sector_industry ILIKE '%Agriculture%'
ORDER BY g.fiscal_year;


-- ---------------------------------------------------------------------------
-- GOLD 9: PRICE vs SENTIMENT CORRELATION PREP
-- ---------------------------------------------------------------------------
CREATE OR REPLACE VIEW gold.price_sentiment_monthly AS
SELECT
    p.month,
    p.city,
    p.item_description,
    p.avg_price,
    s.positive_pct,
    s.negative_pct,
    s.total_articles
FROM gold.price_index_monthly p
LEFT JOIN gold.sentiment_dashboard s
    ON  DATE_TRUNC('month', s.event_date) = p.month
ORDER BY p.month DESC, p.city, p.item_description;


-- =============================================================================
-- END OF DATA LAKE DDL
-- Schema summary:
--   bronze.*  — 7 raw tables (1 reserved slot)
--   silver.*  — 7 cleaned tables + rejected_records quarantine
--   gold.*    — 9 curated views (incl. 2 cross-domain joins)
-- =============================================================================
