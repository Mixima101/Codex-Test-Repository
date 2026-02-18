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

## Windows one-click launcher (desktop icon)

If you want to launch without retyping setup commands each time:

1. Open PowerShell in the repo root.
2. Create a desktop shortcut (one time):
   ```powershell
   powershell -ExecutionPolicy Bypass -File .\scripts\create_desktop_shortcut.ps1
   ```
3. Double-click **QuantumLeap Institutional Console** on your desktop.

What happens when you click the icon:
- creates `.venv` if missing
- activates it
- upgrades `pip`
- installs `requirements.txt`
- runs `python -m streamlit run app.py`

You can also run the launcher directly:
```powershell
.\scripts\launch_quantumleap.bat
```

## Tests

```bash
pytest -q
```

## Download 2 years of daily yfinance data for a ticker list

A helper script is included to download the requested ticker set and save output as text files.

- Script: `scripts/download_yfinance_data.py`
- Default output folder: `yfinance_2y_data`
- Folder layout after running:
  - `yfinance_2y_data/BKNG/BKNG_2y_daily.txt`
  - `yfinance_2y_data/LULU/LULU_2y_daily.txt`
  - ...one folder and `.txt` file per ticker

PowerShell (from the repo/program folder):

```powershell
python .\scripts\download_yfinance_data.py
```

Optional: choose a different output folder:

```powershell
python .\scripts\download_yfinance_data.py --output-dir .\my_stock_data
```
