#!/usr/bin/env python3
"""Download 2 years of daily Eli Lilly (LLY) price data and save it as a .txt file."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
import argparse

import yfinance as yf


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Download 2 years of daily Eli Lilly (LLY) price data from yfinance "
            "and save it to a .txt file."
        )
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("lly_daily_prices_last_2_years.txt"),
        help="Output .txt file path (default: lly_daily_prices_last_2_years.txt)",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    data = yf.download("LLY", period="2y", interval="1d", progress=False)

    if data.empty:
        raise RuntimeError("No data returned for LLY. Please try again later.")

    data.index.name = "Date"
    header = (
        "# Eli Lilly and Company (LLY) daily historical prices from Yahoo Finance\n"
        f"# Generated on: {datetime.now().isoformat(timespec='seconds')}\n"
        "# Period: Last 2 years from today\n"
    )

    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", encoding="utf-8") as file:
        file.write(header)
        data.to_csv(file, sep="\t", float_format="%.6f")

    print(f"Saved {len(data)} rows to {args.output.resolve()}")


if __name__ == "__main__":
    main()
