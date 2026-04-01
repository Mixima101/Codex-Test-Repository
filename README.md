# Soprema simPRO Import Builder

This repository now includes a PowerShell UI tool that scrapes Soprema product pages and builds a simPRO-compatible import CSV.

## What it does

- Discovers product pages from Soprema's **Products & Systems** page.
- Visits each product page and reads rows from the product-line table.
- Exports rows using your `Catalog-Import-Template-US.csv` headers.
- Sets the following values exactly as requested:
  - `Part Number` = `Soprema`
  - `Trade Price` / `Cost Price` / `Split Price` / `Split Cost Price` = `0`
- Adds product names into the `Description` column.
- Fills additional matching fields when available (`Manufacturer`, `Supplier Part Number`, `Supplier Description`, `Unit of Measurement`).

## Run from PowerShell

From this folder:

```powershell
powershell -ExecutionPolicy Bypass -File .\soprema_import_tool.ps1
```

## UI flow

1. Click **Start**.
2. Wait for progress bar to finish.
3. Click **Download CSV**.
4. Save the output file.

## Notes

- The tool uses your local saved main-page HTML (`Products & Systems _ SOPREMA_Main_Product_Listing_Page.html`) when present.
- Product detail pages are downloaded live from `soprema.ca` so it can collect product-line entries.
- `Unit of Measurement` is inferred when possible; if unavailable it is left blank.
