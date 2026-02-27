from __future__ import annotations

from typing import Iterable

import pandas as pd
import yfinance as yf


def normalize_tickers(primary: str, validation: str, benchmark: str) -> list[str]:
    vals = [t.strip().upper() for t in validation.split(",") if t.strip()]
    tickers = [primary.strip().upper(), benchmark.strip().upper(), *vals]
    seen: set[str] = set()
    out: list[str] = []
    for t in tickers:
        if t and t not in seen:
            out.append(t)
            seen.add(t)
    return out


def download_ohlcv(tickers: Iterable[str], start: str, end: str | None = None, threads: bool = False) -> dict[str, pd.DataFrame]:
    data = yf.download(
        tickers=list(tickers),
        start=start,
        end=end,
        auto_adjust=True,
        group_by="ticker",
        progress=False,
        threads=threads,
    )

    out: dict[str, pd.DataFrame] = {}
    if isinstance(data.columns, pd.MultiIndex):
        for t in tickers:
            if t in data.columns.get_level_values(0):
                df = data[t].dropna().copy()
                if not df.empty:
                    out[t] = df
    else:
        # single ticker path from yfinance
        t = list(tickers)[0]
        df = data.dropna().copy()
        if not df.empty:
            out[t] = df
    return out
