# Product Line Table Scraper

This repository now includes a desktop Python app that:

1. Reads product-line URLs from a CSV file (`name,url` columns).
2. Scrapes table data from each URL.
3. Shows progress + logs in a GUI.
4. Exports results as CSV files (one per product line) into an output folder.

## Run on Windows PowerShell

From this repository folder:

```powershell
py .\product_line_scraper.py
```

If `py` is unavailable:

```powershell
python .\product_line_scraper.py
```

## How to use

1. Launch the app.
2. Confirm/select the URL CSV file.
3. Confirm/select the output folder.
4. Click **Find Products**.
5. After scraping finishes, click **Download Tables**.

## Output format

Each generated CSV includes:

- `source_name`
- `source_url`
- A blank separator row
- Table headers
- Table rows

When a page has multiple tables for the same product line, extra files are suffixed (`_2`, `_3`, etc.).
