# Eli Lilly (LLY) 2-Year Daily Price Downloader

This project provides a small Python program that downloads **2 years of daily free price data** for **Eli Lilly (ticker: `LLY`)** from Yahoo Finance (via `yfinance`) and writes it to a `.txt` file.

## Files

- `download_lly_data.py` – script to fetch and save the data
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

This creates:

- `lly_daily_prices_last_2_years.txt`

You can also choose your own output path:

```bash
python3 download_lly_data.py --output my_lly_data.txt
```

## Output format

The output file is tab-separated text with columns from Yahoo Finance data (for example: `Open`, `High`, `Low`, `Close`, `Adj Close`, `Volume`) and one row per trading day for the last 2 years.
