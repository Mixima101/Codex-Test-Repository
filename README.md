# PSAR Walk-Forward Streamlit Lab

Small local Python project for walk-forward optimization of a **Parabolic SAR** long/flat strategy using free Yahoo Finance daily OHLCV data via `yfinance` (`auto_adjust=True`).

## Features

- Streamlit UI for:
  - Primary ticker
  - Comma-separated validation tickers
  - Benchmark ticker (default `SPY`)
  - Out-of-sample horizon (default 5 years)
  - Rolling train/test walk-forward windows
  - PSAR `step` and `max` parameter ranges + grid sizes
  - Transaction costs in bps on position changes
- In-house PSAR implementation (no TA-Lib)
- Next-day execution to avoid look-ahead bias
- Walk-forward optimization per fold (optimize on train, lock and test on next segment)
- Stitched out-of-sample series and metrics:
  - CAGR, Sharpe, max drawdown, annualized volatility
  - Annualized alpha/beta vs benchmark (OLS-style moments)
  - Turnover and percent time invested
- Same process across validation tickers + aggregate summary
- Caching for price downloads and expensive computations

## Project structure

```text
app.py
src/
  data.py
  psar.py
  backtest.py
  metrics.py
  walkforward.py
tests/
  test_psar_backtest.py
requirements.txt
```

## Setup

```bash
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

## Run

```bash
streamlit run app.py
# or
python -m streamlit run app.py
```

Then open the local URL printed by Streamlit (usually `http://localhost:8501`).

## Tests

```bash
pytest -q
```
