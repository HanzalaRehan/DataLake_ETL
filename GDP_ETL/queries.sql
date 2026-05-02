CREATE TABLE bronze_gdp_raw (
    row_label TEXT,
    col_1 TEXT, col_2 TEXT, col_3 TEXT, col_4 TEXT, col_5 TEXT,
    col_6 TEXT, col_7 TEXT, col_8 TEXT, col_9 TEXT, col_10 TEXT,
    col_11 TEXT, col_12 TEXT, col_13 TEXT, col_14 TEXT, col_15 TEXT,
    col_16 TEXT, col_17 TEXT, col_18 TEXT, col_19 TEXT, col_20 TEXT,
    col_21 TEXT, col_22 TEXT, col_23 TEXT, col_24 TEXT, col_25 TEXT,
    col_26 TEXT, col_27 TEXT
);

LOAD DATA INFILE '/var/lib/mysql-files/GDP_table_clean.csv'
INTO TABLE bronze_gdp_raw
FIELDS TERMINATED BY ','
ENCLOSED BY '"'
LINES TERMINATED BY '\n'
IGNORE 1 ROWS;

CREATE TABLE silver_gdp_growth (
    year INT,
    gdp_growth_rate DECIMAL(10,5)
);

CREATE TABLE silver_gdp_sector (
    year INT,
    sector VARCHAR(10),
    subsector VARCHAR(255),
    value DECIMAL(20,5)
);

CREATE TEMPORARY TABLE year_map AS
SELECT 1 col_index, CAST(SUBSTRING_INDEX(col_1, '-', -1) AS UNSIGNED) year FROM bronze_gdp_raw LIMIT 1
UNION ALL SELECT 2, CAST(SUBSTRING_INDEX(col_2, '-', -1) AS UNSIGNED) FROM bronze_gdp_raw LIMIT 1
UNION ALL SELECT 3, CAST(SUBSTRING_INDEX(col_3, '-', -1) AS UNSIGNED) FROM bronze_gdp_raw LIMIT 1
UNION ALL SELECT 4, CAST(SUBSTRING_INDEX(col_4, '-', -1) AS UNSIGNED) FROM bronze_gdp_raw LIMIT 1
UNION ALL SELECT 5, CAST(SUBSTRING_INDEX(col_5, '-', -1) AS UNSIGNED) FROM bronze_gdp_raw LIMIT 1
UNION ALL SELECT 6, CAST(SUBSTRING_INDEX(col_6, '-', -1) AS UNSIGNED) FROM bronze_gdp_raw LIMIT 1
UNION ALL SELECT 7, CAST(SUBSTRING_INDEX(col_7, '-', -1) AS UNSIGNED) FROM bronze_gdp_raw LIMIT 1
UNION ALL SELECT 8, CAST(SUBSTRING_INDEX(col_8, '-', -1) AS UNSIGNED) FROM bronze_gdp_raw LIMIT 1
UNION ALL SELECT 9, CAST(SUBSTRING_INDEX(col_9, '-', -1) AS UNSIGNED) FROM bronze_gdp_raw LIMIT 1
UNION ALL SELECT 10, CAST(SUBSTRING_INDEX(col_10, '-', -1) AS UNSIGNED) FROM bronze_gdp_raw LIMIT 1
UNION ALL SELECT 11, CAST(SUBSTRING_INDEX(col_11, '-', -1) AS UNSIGNED) FROM bronze_gdp_raw LIMIT 1
UNION ALL SELECT 12, CAST(SUBSTRING_INDEX(col_12, '-', -1) AS UNSIGNED) FROM bronze_gdp_raw LIMIT 1
UNION ALL SELECT 13, CAST(SUBSTRING_INDEX(col_13, '-', -1) AS UNSIGNED) FROM bronze_gdp_raw LIMIT 1
UNION ALL SELECT 14, CAST(SUBSTRING_INDEX(col_14, '-', -1) AS UNSIGNED) FROM bronze_gdp_raw LIMIT 1
UNION ALL SELECT 15, CAST(SUBSTRING_INDEX(col_15, '-', -1) AS UNSIGNED) FROM bronze_gdp_raw LIMIT 1
UNION ALL SELECT 16, CAST(SUBSTRING_INDEX(col_16, '-', -1) AS UNSIGNED) FROM bronze_gdp_raw LIMIT 1
UNION ALL SELECT 17, CAST(SUBSTRING_INDEX(col_17, '-', -1) AS UNSIGNED) FROM bronze_gdp_raw LIMIT 1
UNION ALL SELECT 18, CAST(SUBSTRING_INDEX(col_18, '-', -1) AS UNSIGNED) FROM bronze_gdp_raw LIMIT 1
UNION ALL SELECT 19, CAST(SUBSTRING_INDEX(col_19, '-', -1) AS UNSIGNED) FROM bronze_gdp_raw LIMIT 1
UNION ALL SELECT 20, CAST(SUBSTRING_INDEX(col_20, '-', -1) AS UNSIGNED) FROM bronze_gdp_raw LIMIT 1
UNION ALL SELECT 21, CAST(SUBSTRING_INDEX(col_21, '-', -1) AS UNSIGNED) FROM bronze_gdp_raw LIMIT 1
UNION ALL SELECT 22, CAST(SUBSTRING_INDEX(col_22, '-', -1) AS UNSIGNED) FROM bronze_gdp_raw LIMIT 1
UNION ALL SELECT 23, CAST(SUBSTRING_INDEX(col_23, '-', -1) AS UNSIGNED) FROM bronze_gdp_raw LIMIT 1
UNION ALL SELECT 24, CAST(SUBSTRING_INDEX(col_24, '-', -1) AS UNSIGNED) FROM bronze_gdp_raw LIMIT 1
UNION ALL SELECT 25, CAST(SUBSTRING_INDEX(col_25, '-', -1) AS UNSIGNED) FROM bronze_gdp_raw LIMIT 1
UNION ALL SELECT 26, CAST(SUBSTRING_INDEX(col_26, '-', -1) AS UNSIGNED) FROM bronze_gdp_raw LIMIT 1
UNION ALL SELECT 27, CAST(SUBSTRING_INDEX(col_27, '-', -1) AS UNSIGNED) FROM bronze_gdp_raw LIMIT 1;

INSERT INTO silver_gdp_growth (year, gdp_growth_rate)
SELECT ym.year, CAST(v.val AS DECIMAL(10,5))
FROM year_map ym
JOIN (
    SELECT 1 col_index, col_1 val FROM bronze_gdp_raw WHERE row_label LIKE '%GDP Growth Rate%'
    UNION ALL SELECT 2, col_2 FROM bronze_gdp_raw WHERE row_label LIKE '%GDP Growth Rate%'
    UNION ALL SELECT 3, col_3 FROM bronze_gdp_raw WHERE row_label LIKE '%GDP Growth Rate%'
    UNION ALL SELECT 4, col_4 FROM bronze_gdp_raw WHERE row_label LIKE '%GDP Growth Rate%'
    UNION ALL SELECT 5, col_5 FROM bronze_gdp_raw WHERE row_label LIKE '%GDP Growth Rate%'
    UNION ALL SELECT 6, col_6 FROM bronze_gdp_raw WHERE row_label LIKE '%GDP Growth Rate%'
    UNION ALL SELECT 7, col_7 FROM bronze_gdp_raw WHERE row_label LIKE '%GDP Growth Rate%'
    UNION ALL SELECT 8, col_8 FROM bronze_gdp_raw WHERE row_label LIKE '%GDP Growth Rate%'
    UNION ALL SELECT 9, col_9 FROM bronze_gdp_raw WHERE row_label LIKE '%GDP Growth Rate%'
    UNION ALL SELECT 10, col_10 FROM bronze_gdp_raw WHERE row_label LIKE '%GDP Growth Rate%'
    UNION ALL SELECT 11, col_11 FROM bronze_gdp_raw WHERE row_label LIKE '%GDP Growth Rate%'
    UNION ALL SELECT 12, col_12 FROM bronze_gdp_raw WHERE row_label LIKE '%GDP Growth Rate%'
    UNION ALL SELECT 13, col_13 FROM bronze_gdp_raw WHERE row_label LIKE '%GDP Growth Rate%'
    UNION ALL SELECT 14, col_14 FROM bronze_gdp_raw WHERE row_label LIKE '%GDP Growth Rate%'
    UNION ALL SELECT 15, col_15 FROM bronze_gdp_raw WHERE row_label LIKE '%GDP Growth Rate%'
    UNION ALL SELECT 16, col_16 FROM bronze_gdp_raw WHERE row_label LIKE '%GDP Growth Rate%'
    UNION ALL SELECT 17, col_17 FROM bronze_gdp_raw WHERE row_label LIKE '%GDP Growth Rate%'
    UNION ALL SELECT 18, col_18 FROM bronze_gdp_raw WHERE row_label LIKE '%GDP Growth Rate%'
    UNION ALL SELECT 19, col_19 FROM bronze_gdp_raw WHERE row_label LIKE '%GDP Growth Rate%'
    UNION ALL SELECT 20, col_20 FROM bronze_gdp_raw WHERE row_label LIKE '%GDP Growth Rate%'
    UNION ALL SELECT 21, col_21 FROM bronze_gdp_raw WHERE row_label LIKE '%GDP Growth Rate%'
    UNION ALL SELECT 22, col_22 FROM bronze_gdp_raw WHERE row_label LIKE '%GDP Growth Rate%'
    UNION ALL SELECT 23, col_23 FROM bronze_gdp_raw WHERE row_label LIKE '%GDP Growth Rate%'
    UNION ALL SELECT 24, col_24 FROM bronze_gdp_raw WHERE row_label LIKE '%GDP Growth Rate%'
    UNION ALL SELECT 25, col_25 FROM bronze_gdp_raw WHERE row_label LIKE '%GDP Growth Rate%'
    UNION ALL SELECT 26, col_26 FROM bronze_gdp_raw WHERE row_label LIKE '%GDP Growth Rate%'
    UNION ALL SELECT 27, col_27 FROM bronze_gdp_raw WHERE row_label LIKE '%GDP Growth Rate%'
) v
ON ym.col_index = v.col_index;

INSERT INTO silver_gdp_sector (year, sector, subsector, value)
SELECT
    ym.year,
    CASE
        WHEN b.row_label REGEXP '^[A-Z],' THEN SUBSTRING_INDEX(b.row_label, ',', 1)
        ELSE NULL
    END AS sector,
    TRIM(SUBSTRING_INDEX(b.row_label, ',', -1)) AS subsector,
    CAST(v.val AS DECIMAL(20,5))
FROM bronze_gdp_raw b

JOIN (
    SELECT 1 col_index, col_1 val, row_label FROM bronze_gdp_raw
    UNION ALL SELECT 2, col_2, row_label FROM bronze_gdp_raw
    UNION ALL SELECT 3, col_3, row_label FROM bronze_gdp_raw
    UNION ALL SELECT 4, col_4, row_label FROM bronze_gdp_raw
    UNION ALL SELECT 5, col_5, row_label FROM bronze_gdp_raw
    UNION ALL SELECT 6, col_6, row_label FROM bronze_gdp_raw
    UNION ALL SELECT 7, col_7, row_label FROM bronze_gdp_raw
    UNION ALL SELECT 8, col_8, row_label FROM bronze_gdp_raw
    UNION ALL SELECT 9, col_9, row_label FROM bronze_gdp_raw
    UNION ALL SELECT 10, col_10, row_label FROM bronze_gdp_raw
    UNION ALL SELECT 11, col_11, row_label FROM bronze_gdp_raw
    UNION ALL SELECT 12, col_12, row_label FROM bronze_gdp_raw
    UNION ALL SELECT 13, col_13, row_label FROM bronze_gdp_raw
    UNION ALL SELECT 14, col_14, row_label FROM bronze_gdp_raw
    UNION ALL SELECT 15, col_15, row_label FROM bronze_gdp_raw
    UNION ALL SELECT 16, col_16, row_label FROM bronze_gdp_raw
    UNION ALL SELECT 17, col_17, row_label FROM bronze_gdp_raw
    UNION ALL SELECT 18, col_18, row_label FROM bronze_gdp_raw
    UNION ALL SELECT 19, col_19, row_label FROM bronze_gdp_raw
    UNION ALL SELECT 20, col_20, row_label FROM bronze_gdp_raw
    UNION ALL SELECT 21, col_21, row_label FROM bronze_gdp_raw
    UNION ALL SELECT 22, col_22, row_label FROM bronze_gdp_raw
    UNION ALL SELECT 23, col_23, row_label FROM bronze_gdp_raw
    UNION ALL SELECT 24, col_24, row_label FROM bronze_gdp_raw
    UNION ALL SELECT 25, col_25, row_label FROM bronze_gdp_raw
    UNION ALL SELECT 26, col_26, row_label FROM bronze_gdp_raw
    UNION ALL SELECT 27, col_27, row_label FROM bronze_gdp_raw
) v
ON v.row_label = b.row_label

JOIN year_map ym
ON ym.col_index = v.col_index

WHERE b.row_label NOT LIKE '%GDP%'
AND b.row_label NOT LIKE '%Source%'
AND b.row_label NOT LIKE '%GVA%'
AND b.row_label IS NOT NULL;

