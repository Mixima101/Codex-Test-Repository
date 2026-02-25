# PSAR Strategy Simulator (Streamlit)

This project provides a runnable Streamlit app that backtests a **Parabolic SAR (PSAR)** long/flat strategy using Yahoo Finance daily OHLCV data from `yfinance`.

## What the app does

- Left-side menu for all inputs:
  - Ticker symbol
  - Market portfolio ticker (for benchmark comparison)
  - PSAR parameters (`start step`, `step`, `max step`)
  - Cost per trade
  - Start date and end date
  - Starting account value
- **Simulate** button to run the backtest.
- **Data Storage** screen to download and persist ticker datasets locally for reuse.
- Quick **Open Data Storage** buttons from Dashboard and Simulation.
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

## Windows install + launcher (desktop icon)

1. Double-click `Install_QuantumLeap.bat` in the project folder.
   - This creates `.venv`, installs dependencies, creates the desktop shortcut, and launches the app.
2. After install, launch using either:
   - Desktop shortcut: **QuantumLeap Institutional Console**
   - `scripts\launch_quantumleap.bat`

The launcher does not reinstall dependencies each time; it just starts the app (and runs installer only if `.venv` is missing).

If a browser does not auto-open, use the **Local URL** printed in the PowerShell window (for example `http://localhost:8501` or another shown port).

## Tests

```bash
pytest -q
```
