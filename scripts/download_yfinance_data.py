from __future__ import annotations

import argparse
from pathlib import Path

import yfinance as yf

DEFAULT_TICKERS = [
    "BKNG",
    "LULU",
    "ADP",
    "SPGI",
    "ICE",
    "MMC",
    "AJG",
    "CL",
    "PEP",
    "MDT",
    "CAT",
    "NOC",
    "ITW",
    "PHM",
    "CME",
]


def download_ticker_data(ticker: str, output_root: Path, period: str = "2y", interval: str = "1d") -> Path:
    data = yf.download(
        ticker,
        period=period,
        interval=interval,
        auto_adjust=False,
        progress=False,
        actions=False,
    )

    if data.empty:
        raise ValueError(f"No data returned for ticker '{ticker}'.")

    ticker_dir = output_root / ticker
    ticker_dir.mkdir(parents=True, exist_ok=True)

    output_path = ticker_dir / f"{ticker}_2y_daily.txt"
    data.to_csv(output_path, sep="\t", index=True)
    return output_path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Download the last 2 years of daily OHLCV data from yfinance for one or more tickers."
        )
    )
    parser.add_argument(
        "--output-dir",
        default="yfinance_2y_data",
        help="Directory where ticker folders and text files will be saved.",
    )
    parser.add_argument(
        "--tickers",
        nargs="+",
        default=DEFAULT_TICKERS,
        help="Ticker symbols to download. Defaults to the requested list.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    output_root = Path(args.output_dir)
    output_root.mkdir(parents=True, exist_ok=True)

    for raw_ticker in args.tickers:
        ticker = raw_ticker.upper()
        path = download_ticker_data(ticker=ticker, output_root=output_root)
        print(f"Saved {ticker}: {path}")


if __name__ == "__main__":
    main()
