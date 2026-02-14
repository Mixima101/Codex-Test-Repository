# PSAR Strategy Simulator (Streamlit)

This project provides a runnable Streamlit app that backtests a **Parabolic SAR (PSAR)** long/flat strategy using Yahoo Finance daily OHLCV data from `yfinance`.

## What the app does

- Left-side menu for all inputs:
  - Ticker symbol
  - Market portfolio ticker (for benchmark comparison)
  - PSAR parameters (`start step`, `max step`)
  - Cost per trade
  - Start date and end date
  - Starting account value
- **Simulate** button to run the backtest.
- Outputs strategy statistics.
- Shows charts for:
  - Strategy account value
  - Strategy account value vs buy & hold
  - Strategy account value vs market portfolio
  - Price chart with buy/sell markers.

## Run locally

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
streamlit run app.py
```

## Tests

```bash
pytest -q
```
