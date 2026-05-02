# QIM Table 2 (Manufacturing/Crop) Data Documentation

## Potential Issues to Target in the Silver Layer (Data Cleansing/Refinement)

1. **Item Name Normalization**: 
   The parsed string for the `items` column can contain subtle variations across different fiscal years, varying whitespace, or casing differences (e.g., "Wheat & Rice Milling" vs. "Wheat and Rice Milling"). The Silver layer must normalize these item identifiers to ensure longitudinal tracking doesn't break across years.

2. **Weight/Unit Conflation**: 
   Some PDF columns have a `weight` field and a `unit` field. Depending on the extraction layout, Camelot might occasionally shift empty columns. The Silver layer must validate that the `unit` column contains valid strings (like "NOS" or "MT") and that the `weight` column strictly contains numeric index weights, correcting any offset errors.

3. **Missing/Null vs. Zero Values**: 
   The extraction pipeline sets empty cells to `null`. However, some sectors might literally have zero production in an off-season month. The Silver layer must implement business logic to distinguish between true zeros (e.g., sugar crushing off-season) versus missing data (which may require interpolation).

4. **Excluding Summary Headers**: 
   While the Bronze pipeline attempts to filter out "QIM" or "Items" summary rows, the Silver layer needs robust filtering to guarantee no aggregated sub-totals or stray header rows (that slipped through the PDF parser) are accidentally summed into the metrics.

## Key Indicators and Descriptions

1. **Total Output Volume**
   - **Description**: The sum of production for a specific manufacturing item over the entire fiscal year. This is the primary key performance indicator for evaluating the gross output scale of an industry.

2. **YoY (Year-over-Year) Sector Growth**
   - **Description**: The percentage change in total output volume for a specific item compared to the previous year. This indicator is crucial for identifying which manufacturing sectors are expanding and which are contracting.

3. **Monthly Production Trend & Seasonality**
   - **Description**: A time-series metric tracking the month-by-month output volume for a specific item. This is critical for industries with heavy seasonality, such as agriculture-based manufacturing (e.g., sugar production peaks sharply in the winter/spring).

4. **Quantum Index Contribution Weight**
   - **Description**: Utilizing the `weight` column (if present for the item), this indicator assesses how significantly a specific item's production volume impacts the overall Quantum Index of Manufacturing (QIM). Highly weighted items (like textiles or food processing) drive the national index.

5. **Production Volatility (Consistency)**
   - **Description**: A measure of how much monthly production volumes fluctuate from the mean. High volatility suggests an unstable supply chain or heavy seasonality, while low volatility points to consistent, year-round continuous manufacturing operations.
