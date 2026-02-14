# Google 2-Year Daily Price Export

This repository contains a small Python script that downloads **2 years of daily price data** for Alphabet (Google) from Yahoo Finance using `yfinance` and saves it to a `.txt` file.

## Setup

```bash
pip install yfinance
```

## Run

```bash
python3 generate_google_prices.py
```

This creates:

- `google_2y_daily_prices.txt`

Optional arguments:

```bash
python3 generate_google_prices.py --ticker GOOG --output my_prices.txt
```
