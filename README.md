# Multi-Ticker 2-Year Daily Price Downloader

This project provides a Python program that downloads **2 years of daily free price data** from Yahoo Finance (via `yfinance`) and writes **one `.txt` file per ticker** into an output folder.

The default tickers are:

- `LLY` – Eli Lilly and Company
- `COST` – Costco Wholesale Corporation
- `PGR` – The Progressive Corporation
- `NEE` – NextEra Energy, Inc. (a large utility with major renewable energy operations)

## Files

- `download_lly_data.py` – script to fetch and save the data files
- `requirements.txt` – Python dependency list

## Usage

1. Install dependencies:

```bash
python3 -m pip install -r requirements.txt
```

2. Run the script:

```bash
python3 download_lly_data.py
```

This creates a folder named `stock_data_last_2_years` containing:

- `lly_daily_prices_last_2_years.txt`
- `cost_daily_prices_last_2_years.txt`
- `pgr_daily_prices_last_2_years.txt`
- `nee_daily_prices_last_2_years.txt`

You can choose your own output folder:

```bash
python3 download_lly_data.py --output-dir my_stock_data_folder
```

## Output format

Each output file is tab-separated text with columns from Yahoo Finance data (for example: `Open`, `High`, `Low`, `Close`, `Adj Close`, `Volume`) and one row per trading day for the last 2 years.
