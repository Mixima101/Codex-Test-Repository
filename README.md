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

## Batch optimizer (no UI)

To sweep walk-forward menu options and automatically run a two-pass (coarse then focused) SAR grid search:

```bash
python run_optimizer.py \
  --ticker JPM \
  --validation BAC,C,MS,WFC \
  --benchmark XLF \
  --oos-years 5,7 \
  --train-days 504,756,1008 \
  --test-days 42,63,126 \
  --txn-cost-bps 2,5,10
```

The script prints the best configuration and top-ranked combinations by composite score.


## Optimizer UI dashboard

For an interactive optimizer workflow with progress updates and live best-so-far metrics:

```bash
streamlit run app_optimizer.py
```

This UI lets you set fixed inputs (ticker/benchmark/etc.), runs the automated sweep, shows a progress bar, and provides a copy/paste text summary for the best configuration.
