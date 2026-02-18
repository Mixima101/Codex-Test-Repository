"""Download the last 2 years of daily stock data from yfinance for predefined tickers."""

from __future__ import annotations

import argparse
from pathlib import Path

import yfinance as yf

TICKERS = {
    "BKNG": "Booking Holdings",
    "LULU": "Lululemon Athletica",
    "ADP": "Automatic Data Processing",
    "SPGI": "S&P Global",
    "ICE": "Intercontinental Exchange",
    "MMC": "Marsh McLennan",
    "AJG": "Arthur J. Gallagher",
    "CL": "Colgate-Palmolive",
    "PEP": "PepsiCo",
    "MDT": "Medtronic",
    "CAT": "Caterpillar",
    "NOC": "Northrop Grumman",
    "ITW": "Illinois Tool Works",
    "PHM": "PulteGroup",
    "CME": "CME Group",
}


def sanitize_company_name(name: str) -> str:
    """Return a filesystem-safe company name."""
    invalid_chars = '<>:"/\\|?*'
    cleaned = "".join("_" if c in invalid_chars else c for c in name)
    return "_".join(cleaned.split())


def download_ticker_data(ticker: str, company_name: str, output_root: Path) -> Path | None:
    """Download and save one ticker's daily data as a text file."""
    output_root.mkdir(parents=True, exist_ok=True)

    data = yf.download(
        ticker,
        period="2y",
        interval="1d",
        progress=False,
        auto_adjust=False,
        threads=False,
    )

    if data.empty:
        print(f"[WARN] No data returned for {ticker}.")
        return None

    safe_company = sanitize_company_name(company_name)
    output_path = output_root / f"{ticker}_{safe_company}.txt"
    data.to_csv(output_path, sep="\t")
    print(f"[OK] Saved {ticker} data to: {output_path}")
    return output_path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Download last 2 years of daily yfinance data for predefined tickers "
            "into text files."
        )
    )
    parser.add_argument(
        "--output-dir",
        default="stock_data_last_2_years",
        help="Folder where ticker text files will be saved (default: stock_data_last_2_years).",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    output_dir = Path(args.output_dir)

    print(f"Saving files to: {output_dir.resolve()}")
    successes = 0

    for ticker, company_name in TICKERS.items():
        saved_file = download_ticker_data(ticker, company_name, output_dir)
        if saved_file:
            successes += 1

    print(f"\nDone. Saved {successes}/{len(TICKERS)} ticker files.")


if __name__ == "__main__":
    main()
