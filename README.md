## Stock data downloader (2 years, daily)

This program downloads the last 2 years of **daily** stock price data from `yfinance` for the following tickers:

- NVDA, AVGO, META, NFLX, CRWD, ANET, VST, NEE, FSLR, TSLA, ETN, TT, JNJ, JPM, PG, KO, MCD

### What it creates

By default, it creates a folder called `stock_data_2y/`.
Inside that folder, each ticker gets its own subfolder containing a `.txt` file.

Example output structure:

```text
stock_data_2y/
  NVDA/
    NVDA_2y_daily.txt
  AVGO/
    AVGO_2y_daily.txt
  ...
```

The `.txt` files are tab-separated and include daily OHLCV data plus adjusted close.

### Run in PowerShell

From the program folder:

```powershell
python -m pip install -r requirements.txt
python .\download_yfinance_data.py
```

Optional custom output folder:

```powershell
python .\download_yfinance_data.py --output-dir .\my_stock_files
```
