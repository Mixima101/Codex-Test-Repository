#!/usr/bin/env python3
"""Find PSAR parameters that beat buy-and-hold by a target margin on GOOG 2y daily data."""

from __future__ import annotations

import argparse
import csv
import datetime as dt
import json
import random
import urllib.parse
import urllib.request
from urllib.error import URLError
from dataclasses import dataclass
from typing import Iterable, List, Sequence, Tuple


@dataclass
class OHLCV:
    date: dt.date
    open: float
    high: float
    low: float
    close: float
    adj_close: float
    volume: float


def fetch_yahoo_chart(symbol: str = "GOOG", range_: str = "2y", interval: str = "1d") -> List[OHLCV]:
    query = urllib.parse.urlencode({
        "range": range_,
        "interval": interval,
        "events": "div,splits",
        "includeAdjustedClose": "true",
    })
    url = f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}?{query}"
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        payload = json.load(resp)

    result = payload["chart"]["result"][0]
    timestamps = result.get("timestamp") or []
    quote = result["indicators"]["quote"][0]
    adjclose_list = result["indicators"].get("adjclose", [{"adjclose": quote["close"]}])[0]["adjclose"]

    rows: List[OHLCV] = []
    for i, ts in enumerate(timestamps):
        o = quote["open"][i]
        h = quote["high"][i]
        l = quote["low"][i]
        c = quote["close"][i]
        a = adjclose_list[i]
        v = quote["volume"][i]
        if None in (o, h, l, c, a, v):
            continue
        rows.append(
            OHLCV(
                date=dt.datetime.utcfromtimestamp(ts).date(),
                open=float(o),
                high=float(h),
                low=float(l),
                close=float(c),
                adj_close=float(a),
                volume=float(v),
            )
        )
    if not rows:
        raise RuntimeError("No data returned from Yahoo chart API.")
    return rows


def load_csv(path: str) -> List[OHLCV]:
    rows: List[OHLCV] = []
    with open(path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for r in reader:
            rows.append(
                OHLCV(
                    date=dt.date.fromisoformat(r["Date"]),
                    open=float(r["Open"]),
                    high=float(r["High"]),
                    low=float(r["Low"]),
                    close=float(r["Close"]),
                    adj_close=float(r.get("Adj Close", r["Close"])),
                    volume=float(r["Volume"]),
                )
            )
    if not rows:
        raise RuntimeError(f"CSV has no rows: {path}")
    return rows


def parabolic_sar(high: Sequence[float], low: Sequence[float], close: Sequence[float], af_start: float, af_step: float, af_max: float) -> List[float]:
    n = len(close)
    if n == 0:
        return []

    psar = [0.0] * n
    bullish = True
    af = af_start
    ep = high[0]
    psar[0] = low[0]

    if n > 1 and close[1] < close[0]:
        bullish = False
        ep = low[0]
        psar[0] = high[0]

    for i in range(1, n):
        prev = psar[i - 1]
        if bullish:
            current = prev + af * (ep - prev)
            if i >= 2:
                current = min(current, low[i - 1], low[i - 2])
            else:
                current = min(current, low[i - 1])

            if low[i] < current:
                bullish = False
                current = ep
                ep = low[i]
                af = af_start
            else:
                if high[i] > ep:
                    ep = high[i]
                    af = min(af + af_step, af_max)
        else:
            current = prev + af * (ep - prev)
            if i >= 2:
                current = max(current, high[i - 1], high[i - 2])
            else:
                current = max(current, high[i - 1])

            if high[i] > current:
                bullish = True
                current = ep
                ep = high[i]
                af = af_start
            else:
                if low[i] < ep:
                    ep = low[i]
                    af = min(af + af_step, af_max)

        psar[i] = current

    return psar


def returns(series: Sequence[float]) -> List[float]:
    out = [0.0]
    for i in range(1, len(series)):
        prev = series[i - 1]
        out.append((series[i] / prev - 1.0) if prev != 0 else 0.0)
    return out


def total_return(daily_returns: Iterable[float]) -> float:
    wealth = 1.0
    for r in daily_returns:
        wealth *= 1.0 + r
    return wealth - 1.0


def evaluate(rows: Sequence[OHLCV], af_start: float, af_step: float, af_max: float) -> float:
    highs = [r.high for r in rows]
    lows = [r.low for r in rows]
    closes = [r.adj_close for r in rows]
    psar = parabolic_sar(highs, lows, closes, af_start=af_start, af_step=af_step, af_max=af_max)
    rets = returns(closes)

    signal = [1 if c > s else 0 for c, s in zip(closes, psar)]
    shifted_signal = [0] + signal[:-1]
    strat_daily = [r * pos for r, pos in zip(rets, shifted_signal)]
    return total_return(strat_daily)


def optimize(rows: Sequence[OHLCV], target_outperformance: float, seed: int = 42) -> Tuple[Tuple[float, float, float], float, float]:
    closes = [r.adj_close for r in rows]
    bh = total_return(returns(closes))

    best_params = (0.02, 0.02, 0.2)
    best_strat = evaluate(rows, *best_params)
    best_diff = best_strat - bh

    random.seed(seed)

    # Coarse deterministic sweep first.
    coarse_vals = [0.002, 0.005, 0.01, 0.02, 0.03, 0.05, 0.08]
    coarse_max = [0.08, 0.12, 0.2, 0.3, 0.5, 0.8]
    for af_start in coarse_vals:
        for af_step in coarse_vals:
            for af_max in coarse_max:
                if af_max < max(af_start, af_step):
                    continue
                strat = evaluate(rows, af_start, af_step, af_max)
                diff = strat - bh
                if diff > best_diff:
                    best_params, best_strat, best_diff = (af_start, af_step, af_max), strat, diff
                if diff >= target_outperformance:
                    return (af_start, af_step, af_max), strat, bh

    # Random exploration with early stop.
    for _ in range(3000):
        af_start = round(random.uniform(0.001, 0.08), 4)
        af_step = round(random.uniform(0.001, 0.08), 4)
        af_max = round(random.uniform(max(af_start, af_step), 1.0), 4)
        strat = evaluate(rows, af_start, af_step, af_max)
        diff = strat - bh
        if diff > best_diff:
            best_params, best_strat, best_diff = (af_start, af_step, af_max), strat, diff
        if diff >= target_outperformance:
            return (af_start, af_step, af_max), strat, bh

    return best_params, best_strat, bh


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--symbol", default="GOOG")
    parser.add_argument("--target-outperformance", type=float, default=0.10, help="Required strategy_return - buy_and_hold_return.")
    parser.add_argument("--csv", help="Optional local CSV path with Yahoo-style columns.")
    args = parser.parse_args()

    try:
        rows = load_csv(args.csv) if args.csv else fetch_yahoo_chart(symbol=args.symbol)
    except URLError as e:
        print(f"Failed to download Yahoo data: {e}")
        print("Tip: run with --csv <path_to_yfinance_export.csv> in restricted environments.")
        return 1
    params, strat, bh = optimize(rows, args.target_outperformance)
    diff = strat - bh

    print(f"Data points: {len(rows)}")
    print(f"Buy & hold return: {bh:.2%}")
    print(f"Best strategy return: {strat:.2%}")
    print(f"Outperformance: {diff:.2%}")
    print("PSAR params:")
    print(f"  starting_step={params[0]}")
    print(f"  step={params[1]}")
    print(f"  max_step={params[2]}")

    if diff >= args.target_outperformance:
        print("Target achieved.")
        return 0

    print("Target not achieved with current search budget.")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
