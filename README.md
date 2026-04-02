# SOPREMA Product URL Extractor

Simple desktop app (Python + Tkinter) to extract SOPREMA product line names and URLs from a saved SOPREMA product-list HTML page.

## What it does

- Loads the local HTML file in this repository by default:
  - `All Roofs Products - Roofs - Building components _ SOPREMA.html`
- Finds product cards (`a.result`) and pulls:
  - product line name (`h3.result-title`)
  - product URL (`href`)
- Shows a progress bar and live log output
- Exports to CSV with two columns:
  - `name`
  - `url`

## Run in PowerShell (Windows)

```powershell
cd <folder-containing-this-project>
python .\soprema_url_extractor.py
```

If `python` is not recognized, try:

```powershell
py .\soprema_url_extractor.py
```

## Using the app

1. (Optional) Click **Browse** to choose a different saved HTML file.
2. Click **Find URLs**.
3. Review the results in the log box.
4. Click **Download URLs** and choose where to save the CSV.
5. Click **Exit** when done.

## Notes

- URLs in the CSV are cleaned to remove tracking query parameters.
- Duplicate `(name, url)` entries are removed.
