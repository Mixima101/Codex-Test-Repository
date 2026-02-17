#!/usr/bin/env python3
"""Download 2 years of daily stock data and save one .txt file per ticker."""

from __future__ import annotations

import argparse
from datetime import datetime
from pathlib import Path

import yfinance as yf

TICKERS: dict[str, str] = {
    "LLY": "Eli Lilly and Company",
    "COST": "Costco Wholesale Corporation",
    "PGR": "The Progressive Corporation",
    "NEE": "NextEra Energy, Inc.",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Download 2 years of daily price data for selected tickers from yfinance "
            "and save each ticker to its own .txt file in an output folder."
        )
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("stock_data_last_2_years"),
        help="Output folder path (default: stock_data_last_2_years)",
    )
    return parser.parse_args()


def save_ticker_data(output_dir: Path, ticker: str, company_name: str) -> Path:
    data = yf.download(ticker, period="2y", interval="1d", progress=False)

    if data.empty:
        raise RuntimeError(f"No data returned for {ticker}. Please try again later.")

    data.index.name = "Date"
    output_path = output_dir / f"{ticker.lower()}_daily_prices_last_2_years.txt"
    header = (
        f"# {company_name} ({ticker}) daily historical prices from Yahoo Finance\n"
        f"# Generated on: {datetime.now().isoformat(timespec='seconds')}\n"
        "# Period: Last 2 years from today\n"
    )

    with output_path.open("w", encoding="utf-8") as file:
        file.write(header)
        data.to_csv(file, sep="\t", float_format="%.6f")

    return output_path


def main() -> None:
    args = parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)

    for ticker, company_name in TICKERS.items():
        output_path = save_ticker_data(args.output_dir, ticker, company_name)
        print(f"Saved {ticker} data to {output_path.resolve()}")


if __name__ == "__main__":
    main()
