#!/usr/bin/env python3
"""Download last 2 years of daily stock data for a fixed ticker list using yfinance."""

from __future__ import annotations

import argparse
from pathlib import Path

import yfinance as yf

TICKERS = [
    "NVDA",
    "AVGO",
    "META",
    "NFLX",
    "CRWD",
    "ANET",
    "VST",
    "NEE",
    "FSLR",
    "TSLA",
    "ETN",
    "TT",
    "JNJ",
    "JPM",
    "PG",
    "KO",
    "MCD",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Download 2 years of daily yfinance price data for predefined tickers "
            "and save each ticker's data as a .txt file in its own folder."
        )
    )
    parser.add_argument(
        "--output-dir",
        default="stock_data_2y",
        help="Root directory where ticker folders/files are created (default: %(default)s)",
    )
    return parser.parse_args()


def download_ticker_data(ticker: str, output_root: Path) -> None:
    ticker_dir = output_root / ticker
    ticker_dir.mkdir(parents=True, exist_ok=True)

    output_file = ticker_dir / f"{ticker}_2y_daily.txt"

    data = yf.download(
        ticker,
        period="2y",
        interval="1d",
        auto_adjust=False,
        progress=False,
        threads=False,
    )

    if data.empty:
        print(f"[WARN] No data returned for {ticker}; skipping file write.")
        return

    data.to_csv(output_file, sep="\t", index=True)
    print(f"[OK] Saved {ticker}: {output_file}")


def main() -> None:
    args = parse_args()
    output_root = Path(args.output_dir)
    output_root.mkdir(parents=True, exist_ok=True)

    print(f"Saving data under: {output_root.resolve()}")
    for ticker in TICKERS:
        download_ticker_data(ticker, output_root)

    print("Done.")


if __name__ == "__main__":
    main()
