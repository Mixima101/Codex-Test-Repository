# yfinance 2-Year Daily Stock Downloader

This script downloads the **last 2 years of daily stock price data** from yfinance for:

- BKNG (Booking Holdings)
- LULU (Lululemon Athletica)
- ADP (Automatic Data Processing)
- SPGI (S&P Global)
- ICE (Intercontinental Exchange)
- MMC (Marsh McLennan)
- AJG (Arthur J. Gallagher)
- CL (Colgate-Palmolive)
- PEP (PepsiCo)
- MDT (Medtronic)
- CAT (Caterpillar)
- NOC (Northrop Grumman)
- ITW (Illinois Tool Works)
- PHM (PulteGroup)
- CME (CME Group)

Each ticker is saved as its own `.txt` file inside an output folder (default: `stock_data_last_2_years`).

## PowerShell usage (from this program folder)

1. Install dependencies:

```powershell
python -m pip install -r requirements.txt
```

2. Run the downloader:

```powershell
python .\download_yfinance_data.py
```

3. Optional: choose a different output folder:

```powershell
python .\download_yfinance_data.py --output-dir .\my_stock_data
```

After it runs, you'll have a folder containing one text file per ticker with 2 years of daily data.
