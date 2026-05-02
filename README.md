# DataLake_ETL

**EconReservoir: A Unified Economic Data Lake for Pakistan**

This project builds a scalable **ETL (Extract, Transform, Load) pipeline** to consolidate diverse economic datasets of Pakistan into a structured data lake for analysis, modeling, and decision-making.

---

## Overview

`DataLake_ETL` is designed to ingest, clean, transform, and store multi-domain economic data, including:

- Macroeconomic indicators (GDP, sector contributions)
- Financial markets (PSX stock data)
- Agricultural production (crops)
- Industrial output
- Mineral production
- Trade data (imports & exports)
- Local market prices (city-wise)
- Explainable sources (news data)

The goal is to create a **centralized, queryable, and analytics-ready data lake**.

---

## Architecture

```
                +-------------------+
                |   Data Sources    |
                |-------------------|
                | GDP, PSX, Trade   |
                | Crops, Industry   |
                | Market Prices     |
                | News APIs         |
                +--------+----------+
                         |
                         v
                +-------------------+
                |    Extract Layer  |
                | (Scrapers/APIs)   |
                +--------+----------+
                         |
                         v
                +-------------------+
                |  Bronze Layer     |
                | Raw Data Storage  |
                +--------+----------+
                         |
                         v
                +-------------------+
                |  Silver Layer     |
                | Cleaning &        |
                | Transformation    |
                +--------+----------+
                         |
                         v
                +-------------------+
                |   Gold Layer      |
                | Analytics Ready   |
                | Aggregated Data   |
                +-------------------+
```

---

## Tech Stack

- **Python** – Core ETL logic  
- **Pandas** – Data transformation  
- **BeautifulSoup / Requests** – Web scraping  
- **SQL (MySQL / SQL Server)** – Data storage  
- **Docker** – Containerized database setup  
- **tqdm** – Progress tracking  

---

## Project Structure

```
DataLake_ETL/
│
├── extract/
│   ├── psx_scraper.py
│   ├── trade_data.py
│   └── macro_data.py
│
├── transform/
│   ├── cleaning.py
│   ├── normalization.py
│   └── feature_engineering.py
│
├── load/
│   ├── load_to_sql.py
│   └── schema.sql
│
├── data/
│   ├── bronze/
│   ├── silver/
│   └── gold/
│
├── docker/
│   └── docker-compose.yml
│
├── notebooks/
│   └── analysis.ipynb
│
└── README.md
```

---

## Setup Instructions

### 1. Clone the Repository
```bash
git clone https://github.com/HanzalaRehan/DataLake_ETL.git
cd DataLake_ETL
```

### 2. Create Virtual Environment
```bash
python -m venv .venv
source .venv/bin/activate   # Mac/Linux
.venv\Scripts\activate      # Windows
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Run Docker (Database)
```bash
docker run --platform linux/amd64 \
  -e "ACCEPT_EULA=Y" \
  -e "MSSQL_SA_PASSWORD=YourPassword123" \
  -p 1433:1433 \
  -d mcr.microsoft.com/mssql/server:2022-latest
```

---

## Usage

### Run ETL Pipeline
```bash
python main.py
```

### Example Output
```csv
date,symbol,open,high,low,close,volume
2024-01-01,OGDC,95.5,97.0,94.8,96.2,1200000
```

---

## ETL Workflow

### Extract
- Scrapes PSX historical data  
- Fetches macroeconomic indicators  
- Collects trade and production datasets  

### Transform
- Cleans missing values  
- Standardizes formats  
- Normalizes schemas across datasets  
- Feature engineering for analytics  

### Load
- Stores raw data in **Bronze layer**  
- Cleaned data in **Silver layer**  
- Aggregated insights in **Gold layer**  

---

## Use Cases

- Economic trend analysis  
- Machine learning models (forecasting GDP, stock trends)  
- Explainable AI with news + economic indicators  
- Market risk analysis  
- Regional price comparisons  

---

## Future Improvements

- Airflow orchestration  
- Real-time streaming (Kafka)  
- Data validation layer (Great Expectations)  
- Dashboard integration (Power BI / Tableau)  
- API layer for data access  

---

## Contributing

Contributions are welcome!

1. Fork the repo  
2. Create a feature branch  
3. Commit your changes  
4. Submit a pull request  

---

## License

This project is licensed under the MIT License.

---

## Author

**Hanzala Rehan**  
Data Science | AI | Data Engineering  

## Collabrators

**Abdullah Janjua**  
**Hamdan Ishfaq**  
**Khadija Faisla**

