#!/usr/bin/env python3
"""Download 2 years of daily Google (Alphabet) price data and save to a .txt file."""

from __future__ import annotations

import argparse
from datetime import date, timedelta
from pathlib import Path

import yfinance as yf


DEFAULT_TICKER = "GOOG"
DEFAULT_OUTPUT = "google_2y_daily_prices.txt"


def fetch_prices(ticker: str, start: date, end: date):
    """Fetch daily price data from Yahoo Finance for [start, end)."""
    data = yf.download(
        ticker,
        start=start.isoformat(),
        end=end.isoformat(),
        interval="1d",
        auto_adjust=False,
        progress=False,
        threads=False,
    )

    if data.empty:
        raise RuntimeError(
            f"No data returned for ticker '{ticker}' between {start} and {end}."
        )

    return data


def save_as_txt(data, output_path: Path, ticker: str, start: date, end: date) -> None:
    header = [
        f"Ticker: {ticker}",
        f"Date range requested: {start} to {end - timedelta(days=1)}",
        "Frequency: Daily",
        "Source: yfinance / Yahoo Finance",
        "",
    ]

    output_path.write_text("\n".join(header) + data.to_string() + "\n", encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Create a .txt file with 2 years of daily Google (Alphabet) stock prices."
    )
    parser.add_argument(
        "--ticker",
        default=DEFAULT_TICKER,
        help=f"Stock ticker to download (default: {DEFAULT_TICKER}).",
    )
    parser.add_argument(
        "--output",
        default=DEFAULT_OUTPUT,
        help=f"Output .txt filename (default: {DEFAULT_OUTPUT}).",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    end = date.today() + timedelta(days=1)
    start = end - timedelta(days=365 * 2)

    data = fetch_prices(args.ticker, start, end)
    output_path = Path(args.output)
    save_as_txt(data, output_path, args.ticker, start, end)

    print(f"Saved {len(data)} rows to {output_path.resolve()}")


if __name__ == "__main__":
    main()
