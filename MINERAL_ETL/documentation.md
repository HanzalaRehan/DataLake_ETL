# Mineral Production Data Documentation

## Potential Issues to Target in the Silver Layer (Data Cleansing/Refinement)

1. **Unit Normalization & Correction**: 
   The Bronze extraction script currently hardcodes the `unit` column to `"MT"` (Metric Tons) for all rows as a fallback. However, certain minerals are measured differently. For instance, Crude Oil is typically measured in US Barrels (BBLS). The Silver layer needs a mapping table or regex logic to correctly derive and standardize the `unit` based on the `mineral` name string.

2. **Entity Resolution (Mineral Names)**: 
   There are inconsistencies in how the same mineral is named across different fiscal years and sources. For example, "Crude Oil (US Barrel)" and "CRUDE OIL ( US BBLS)" appear as separate entities. The Silver layer must normalize these variations into a standardized dimension (e.g., mapping both to a unified "Crude Oil" entity).

3. **Province/Region Standardization**: 
   Province names may contain abbreviations, variations, or typos (e.g., "KPK" vs. "Khyber Pakhtunkhwa"). Standardizing these to a consistent set of region names is critical for accurate geographic aggregation.

4. **Data Type Casting and Null Handling**: 
   The `value` column contains string representations of numbers that were cleansed, but it's essential that the Silver layer enforces strict numeric typing (e.g., Float/Integer). Missing or `"null"` values must be correctly cast to database `NULL` types rather than zero, to prevent skewed averages.

## Key Indicators and Descriptions

1. **Total Production Volume**
   - **Description**: The aggregated total extraction volume. This is the primary metric, and it can be sliced by mineral, province, fiscal year, or month. It provides a baseline for tracking the overall mining sector's output.

2. **Regional Contribution Share**
   - **Description**: The percentage share of total production contributed by each individual province. This indicator highlights geographic concentrations for specific minerals (e.g., identifying which province dominates Coal vs. Lime Stone extraction).

3. **YoY (Year-over-Year) Production Growth**
   - **Description**: The percentage change in total annual production volume for a specific mineral compared to the previous fiscal year. This is a critical macro-economic indicator of mining sector expansion or contraction.

4. **Seasonal Extraction Variance (MoM)**
   - **Description**: Month-over-Month fluctuations in extraction volume. This indicator helps identify operational bottlenecks (e.g., drops in extraction during monsoon/summer seasons) and production cyclicality.

5. **Mineral Dominance Ratio**
   - **Description**: The percentage of total national output represented by the top 3-5 minerals. Since heavy construction materials like Lime Stone dominate the volume metrics, tracking this ratio helps analysts understand how diversified the mining sector is beyond just construction aggregates.
