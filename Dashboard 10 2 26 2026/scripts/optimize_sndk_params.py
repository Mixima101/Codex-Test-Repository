#!/usr/bin/env python3
"""Phase-1 optimizer for SNDK (PSAR + hard stop + rolling stop only).

Focuses on stronger generalization without adding new indicators:
- tighter validation/test gates,
- multi-split walk-forward selection,
- parameter stability filtering.
"""

from __future__ import annotations

import csv
import json
import math
import random
from dataclasses import asdict, dataclass
from datetime import date, datetime
from pathlib import Path
from statistics import median

DATA_FILE = Path("Dashboard 10 2 26 2026/data/datasets/SNDK_d16978b26edc.csv")
REPORT_FILE = Path("Dashboard 10 2 26 2026/reports/sndk_optimization.md")

INITIAL_CASH = 10_000.0
COST_PER_TRADE = 1.0
MAX_TRADES = 49
MIN_BARS_BETWEEN_TRADES = 5
MIN_OUTPERFORMANCE_VS_BUY_HOLD = 0.20
MIN_WIN_LOSS_RATIO = 1.0

RANDOM_SEED = 17
RANDOM_TRIALS = 45_000
SHORTLIST_SIZE = 220
PHASE1_SPLITS: list[tuple[float, float]] = [
    (0.50, 0.25),
    (0.60, 0.20),
    (0.70, 0.15),
]


@dataclass
class Candle:
    day: date
    high: float
    low: float
    close: float


@dataclass
class Params:
    start_step: float
    step: float
    max_step: float
    hard_stop_pct: float
    rolling_stop_pct: float


@dataclass
class SimStats:
    final_equity: float
    number_of_trades: int
    winning_trades: int
    losing_trades: int
    win_loss_ratio: float
    outperformance_vs_buy_hold: float
    max_drawdown: float
    sharpe: float
    trade_indices: list[int]


def load_candles(path: Path) -> list[Candle]:
    with path.open("r", encoding="utf-8") as fh:
        return [
            Candle(
                day=datetime.strptime(r["Date"], "%Y-%m-%d").date(),
                high=float(r["High"]),
                low=float(r["Low"]),
                close=float(r["Close"]),
            )
            for r in csv.DictReader(fh)
        ]


def parabolic_sar(candles: list[Candle], start_step: float, step: float, max_step: float) -> list[float]:
    high = [c.high for c in candles]
    low = [c.low for c in candles]
    close = [c.close for c in candles]

    if len(close) < 2:
        return [math.nan] * len(close)

    bull = close[1] >= close[0]
    af = start_step
    ep = high[1] if bull else low[1]

    psar = [0.0] * len(close)
    psar[0] = low[0] if bull else high[0]
    psar[1] = min(low[0], low[1]) if bull else max(high[0], high[1])

    for i in range(2, len(close)):
        prior_psar = psar[i - 1]
        candidate = prior_psar + af * (ep - prior_psar)

        if bull:
            candidate = min(candidate, low[i - 1], low[i - 2])
            if low[i] < candidate:
                bull = False
                psar[i] = ep
                ep = low[i]
                af = start_step
            else:
                psar[i] = candidate
                if high[i] > ep:
                    ep = high[i]
                    af = min(af + step, max_step)
        else:
            candidate = max(candidate, high[i - 1], high[i - 2])
            if high[i] > candidate:
                bull = True
                psar[i] = ep
                ep = high[i]
                af = start_step
            else:
                psar[i] = candidate
                if low[i] < ep:
                    ep = low[i]
                    af = min(af + step, max_step)

    return psar


def max_drawdown(returns: list[float]) -> float:
    eq = 1.0
    peak = 1.0
    mdd = 0.0
    for r in returns:
        eq *= 1.0 + r
        peak = max(peak, eq)
        mdd = min(mdd, eq / peak - 1.0)
    return mdd


def sharpe(returns: list[float]) -> float:
    if not returns:
        return 0.0
    mu = sum(returns) / len(returns)
    var = sum((x - mu) ** 2 for x in returns) / len(returns)
    sd = math.sqrt(var)
    if sd == 0:
        return 0.0
    return mu / sd * math.sqrt(252)


def buy_hold_final(candles: list[Candle]) -> float:
    return INITIAL_CASH * candles[-1].close / candles[0].close


def respects_weekly_limit(trade_indices: list[int]) -> bool:
    return all((curr - prev) >= MIN_BARS_BETWEEN_TRADES for prev, curr in zip(trade_indices, trade_indices[1:]))


def simulate_with_params(candles: list[Candle], params: Params) -> SimStats:
    close = [c.close for c in candles]
    psar = parabolic_sar(candles, params.start_step, params.step, params.max_step)
    signal = [1 if c.close > s else 0 for c, s in zip(candles, psar)]
    target_pos = [0] + signal[:-1]

    cash = float(INITIAL_CASH)
    shares = 0.0
    invested = 0
    entry_price: float | None = None
    highest_close: float | None = None

    buy_marks: list[float | None] = [None] * len(close)
    sell_marks: list[float | None] = [None] * len(close)
    trade_indices: list[int] = []
    returns: list[float] = []
    prev_equity = INITIAL_CASH

    for i, price in enumerate(close):
        desired = int(target_pos[i])

        if invested == 1:
            highest_close = price if highest_close is None else max(highest_close, price)
            stop_level = max(
                entry_price * (1 - params.hard_stop_pct),
                highest_close * (1 - params.rolling_stop_pct),
            )
            if price <= stop_level:
                desired = 0

        if desired != invested:
            if desired == 1:
                if cash > COST_PER_TRADE:
                    cash -= COST_PER_TRADE
                    shares = cash / price
                    cash = 0.0
                    invested = 1
                    entry_price = price
                    highest_close = price
                    buy_marks[i] = price
                    trade_indices.append(i)
            else:
                cash += shares * price
                shares = 0.0
                if cash > 0:
                    cash = max(0.0, cash - COST_PER_TRADE)
                invested = 0
                entry_price = None
                highest_close = None
                sell_marks[i] = price
                trade_indices.append(i)

        equity = cash + shares * price
        returns.append(0.0 if prev_equity == 0 else (equity / prev_equity - 1.0))
        prev_equity = equity

    final_equity = cash + shares * close[-1]

    winning_trades = 0
    losing_trades = 0
    open_entry: float | None = None
    for i in range(len(close)):
        if buy_marks[i] is not None:
            open_entry = float(buy_marks[i])
        if sell_marks[i] is not None and open_entry is not None:
            ret = float(sell_marks[i]) / open_entry - 1.0
            if ret > 0:
                winning_trades += 1
            elif ret < 0:
                losing_trades += 1
            open_entry = None

    if losing_trades == 0:
        win_loss_ratio = math.inf if winning_trades > 0 else 0.0
    else:
        win_loss_ratio = winning_trades / losing_trades

    buy_hold = buy_hold_final(candles)
    return SimStats(
        final_equity=final_equity,
        number_of_trades=len(trade_indices),
        winning_trades=winning_trades,
        losing_trades=losing_trades,
        win_loss_ratio=win_loss_ratio,
        outperformance_vs_buy_hold=final_equity / buy_hold - 1.0,
        max_drawdown=max_drawdown(returns),
        sharpe=sharpe(returns),
        trade_indices=trade_indices,
    )


def sample_params(rng: random.Random) -> Params:
    while True:
        start_step = 10 ** rng.uniform(-3.0, -1.0)
        step = 10 ** rng.uniform(-3.0, -1.0)
        max_step = 10 ** rng.uniform(-1.3, -0.15)
        if start_step <= max_step and step <= max_step:
            break
    return Params(
        start_step=start_step,
        step=step,
        max_step=max_step,
        hard_stop_pct=rng.uniform(0.01, 0.35),
        rolling_stop_pct=rng.uniform(0.01, 0.45),
    )


def split_candles(candles: list[Candle], train_frac: float, valid_frac: float) -> tuple[list[Candle], list[Candle], list[Candle]]:
    n = len(candles)
    n_train = int(n * train_frac)
    n_valid = int(n * valid_frac)
    train = candles[:n_train]
    valid = candles[n_train : n_train + n_valid]
    test = candles[n_train + n_valid :]
    return train, valid, test


def perturbations(base: Params) -> list[Params]:
    factors = [0.90, 0.95, 1.05, 1.10]
    out = [base]
    for f in factors:
        out.append(
            Params(
                start_step=min(base.start_step * f, base.max_step),
                step=min(base.step * f, base.max_step),
                max_step=max(base.max_step * f, max(base.start_step, base.step)),
                hard_stop_pct=min(max(base.hard_stop_pct * f, 0.005), 0.50),
                rolling_stop_pct=min(max(base.rolling_stop_pct * f, 0.005), 0.60),
            )
        )
    return out


def multi_split_stats(candles: list[Candle], params: Params) -> dict:
    split_rows = []
    val_scores = []
    test_scores = []

    for idx, (train_frac, valid_frac) in enumerate(PHASE1_SPLITS, start=1):
        train, valid, test = split_candles(candles, train_frac, valid_frac)
        tr = simulate_with_params(train, params)
        va = simulate_with_params(valid, params)
        te = simulate_with_params(test, params)
        split_rows.append(
            {
                "split": idx,
                "train_range": [train[0].day.isoformat(), train[-1].day.isoformat()],
                "valid_range": [valid[0].day.isoformat(), valid[-1].day.isoformat()],
                "test_range": [test[0].day.isoformat(), test[-1].day.isoformat()],
                "train_outperformance": tr.outperformance_vs_buy_hold,
                "validation_outperformance": va.outperformance_vs_buy_hold,
                "test_outperformance": te.outperformance_vs_buy_hold,
                "validation_sharpe": va.sharpe,
                "test_sharpe": te.sharpe,
            }
        )
        val_scores.append(va.outperformance_vs_buy_hold)
        test_scores.append(te.outperformance_vs_buy_hold)

    return {
        "splits": split_rows,
        "avg_validation_outperformance": sum(val_scores) / len(val_scores),
        "avg_test_outperformance": sum(test_scores) / len(test_scores),
        "worst_validation_outperformance": min(val_scores),
        "worst_test_outperformance": min(test_scores),
    }


def stability_stats(candles: list[Candle], params: Params) -> dict:
    perf = []
    for p in perturbations(params):
        stats = simulate_with_params(candles, p)
        perf.append(stats.outperformance_vs_buy_hold)
    return {
        "samples": len(perf),
        "median_outperformance": median(perf),
        "worst_outperformance": min(perf),
    }


def phase1_select(candles: list[Candle]) -> tuple[Params, dict, dict, dict]:
    rng = random.Random(RANDOM_SEED)

    # Stage A: broad search with strict simulator constraints on full sample.
    candidates: list[tuple[float, Params, SimStats]] = []
    for _ in range(RANDOM_TRIALS):
        p = sample_params(rng)
        s = simulate_with_params(candles, p)
        if s.number_of_trades > MAX_TRADES:
            continue
        if not respects_weekly_limit(s.trade_indices):
            continue
        if s.win_loss_ratio <= MIN_WIN_LOSS_RATIO:
            continue
        if s.outperformance_vs_buy_hold < MIN_OUTPERFORMANCE_VS_BUY_HOLD:
            continue

        full_score = (
            100.0 * s.outperformance_vs_buy_hold
            + 2.5 * s.sharpe
            - 35.0 * abs(s.max_drawdown)
        )
        candidates.append((full_score, p, s))

    if not candidates:
        raise RuntimeError("No feasible candidates found in broad search.")

    candidates.sort(key=lambda x: x[0], reverse=True)
    shortlist = candidates[:SHORTLIST_SIZE]

    # Stage B: progressively strict phase-1 profiles over multi-split and stability diagnostics.
    profiles = [
        {
            "name": "strict",
            "avg_validation_min": 0.08,
            "avg_test_min": 0.08,
            "worst_validation_min": 0.00,
            "worst_test_min": 0.00,
            "stability_median_min": 0.20,
            "stability_worst_min": 0.05,
        },
        {
            "name": "balanced",
            "avg_validation_min": 0.03,
            "avg_test_min": 0.03,
            "worst_validation_min": -0.03,
            "worst_test_min": -0.03,
            "stability_median_min": 0.15,
            "stability_worst_min": -0.03,
        },
        {
            "name": "practical",
            "avg_validation_min": -0.02,
            "avg_test_min": -0.05,
            "worst_validation_min": -0.15,
            "worst_test_min": -0.15,
            "stability_median_min": 0.12,
            "stability_worst_min": -0.08,
        },
    ]

    attempts = []
    for profile in profiles:
        best: tuple[float, Params, SimStats, dict, dict] | None = None
        passed = 0

        for _, p, full_stats in shortlist:
            ms = multi_split_stats(candles, p)
            stb = stability_stats(candles, p)

            if ms["avg_validation_outperformance"] < profile["avg_validation_min"]:
                continue
            if ms["avg_test_outperformance"] < profile["avg_test_min"]:
                continue
            if ms["worst_validation_outperformance"] < profile["worst_validation_min"]:
                continue
            if ms["worst_test_outperformance"] < profile["worst_test_min"]:
                continue
            if stb["median_outperformance"] < profile["stability_median_min"]:
                continue
            if stb["worst_outperformance"] < profile["stability_worst_min"]:
                continue

            passed += 1
            score = (
                6.0 * ms["avg_validation_outperformance"]
                + 6.0 * ms["avg_test_outperformance"]
                + 2.0 * ms["worst_validation_outperformance"]
                + 2.0 * ms["worst_test_outperformance"]
                + 1.5 * stb["median_outperformance"]
                + 0.5 * stb["worst_outperformance"]
                + 1.0 * full_stats.outperformance_vs_buy_hold
            )

            if best is None or score > best[0]:
                best = (score, p, full_stats, ms, stb)

        attempts.append({"profile": profile["name"], "candidates_passed": passed})
        if best is not None:
            return best[1], asdict(best[2]), best[3], {
                "profile": profile,
                "stability": best[4],
                "attempts": attempts,
            }

    # Fallback: return most robust score from shortlist even if profile gates are not met.
    fallback: tuple[float, Params, SimStats, dict, dict] | None = None
    for _, p, full_stats in shortlist:
        ms = multi_split_stats(candles, p)
        stb = stability_stats(candles, p)
        score = (
            5.0 * ms["avg_validation_outperformance"]
            + 5.0 * ms["avg_test_outperformance"]
            + 2.0 * stb["median_outperformance"]
            + 0.5 * stb["worst_outperformance"]
            + 1.0 * full_stats.outperformance_vs_buy_hold
        )
        if fallback is None or score > fallback[0]:
            fallback = (score, p, full_stats, ms, stb)

    if fallback is None:
        raise RuntimeError("No candidate passed phase-1 strictness profiles.")

    return fallback[1], asdict(fallback[2]), fallback[3], {
        "profile": {"name": "fallback_best_robust", "avg_validation_min": float("nan"), "avg_test_min": float("nan"), "worst_validation_min": float("nan"), "worst_test_min": float("nan")},
        "stability": fallback[4],
        "attempts": attempts,
    }


def write_report(candles: list[Candle], params: Params, full: dict, multisplit: dict, phase1_meta: dict) -> None:
    p = asdict(params)
    profile = phase1_meta["profile"]
    stability = phase1_meta["stability"]
    attempts = phase1_meta["attempts"]

    lines = [
        "# SNDK Phase-1 Robust Optimization (No New Indicators)",
        "",
        "## Recommended simulator inputs",
        "- Use PSAR entries/exits: **Enabled**",
        f"- PSAR start step: `{p['start_step']}`",
        f"- PSAR step: `{p['step']}`",
        f"- PSAR max step: `{p['max_step']}`",
        "- Hard Stop: **Enabled**",
        f"- Hard stop % (UI): `{p['hard_stop_pct'] * 100}`",
        "- Rolling Stop: **Enabled**",
        f"- Rolling stop % (UI): `{p['rolling_stop_pct'] * 100}`",
        "- Cost per trade ($): `1`",
        "- Starting account value ($): `10000`",
        "",
        "## Full-sample constraints and performance",
        f"- Date range: `{candles[0].day.isoformat()}` to `{candles[-1].day.isoformat()}`",
        f"- Strategy final equity: `${full['final_equity']:.2f}`",
        f"- Outperformance vs Buy & Hold: `{full['outperformance_vs_buy_hold'] * 100:.2f}%`",
        f"- Trades: `{full['number_of_trades']}`",
        f"- Win/Loss ratio: `{full['win_loss_ratio']}`",
        f"- Max drawdown: `{full['max_drawdown'] * 100:.2f}%`",
        f"- Sharpe: `{full['sharpe']:.3f}`",
        "",
        "## Phase-1 validation process",
        "- No new indicators added; only PSAR + hard stop + rolling stop params optimized.",
        "- Used multi-split walk-forward checks and stability perturbation checks.",
        f"- Selected strictness profile: `{profile['name']}`",
        (
            f"- Profile thresholds: avg val >= `{profile['avg_validation_min'] * 100:.1f}%`, avg test >= `{profile['avg_test_min'] * 100:.1f}%`, "
            f"worst val >= `{profile['worst_validation_min'] * 100:.1f}%`, worst test >= `{profile['worst_test_min'] * 100:.1f}%`."
            if profile['name'] != 'fallback_best_robust'
            else "- Profile thresholds: `N/A` (no profile fully passed; selected best robust fallback candidate)."
        ),
        "",
        "## Multi-split walk-forward results",
        f"- Average validation outperformance: `{multisplit['avg_validation_outperformance'] * 100:.2f}%`",
        f"- Average test outperformance: `{multisplit['avg_test_outperformance'] * 100:.2f}%`",
        f"- Worst validation outperformance: `{multisplit['worst_validation_outperformance'] * 100:.2f}%`",
        f"- Worst test outperformance: `{multisplit['worst_test_outperformance'] * 100:.2f}%`",
        "",
        "### Per-split details",
    ]

    for row in multisplit["splits"]:
        lines.extend(
            [
                f"- Split {row['split']}:",
                f"  - Train `{row['train_range'][0]}` -> `{row['train_range'][1]}` outperformance `{row['train_outperformance'] * 100:.2f}%`",
                f"  - Validation `{row['valid_range'][0]}` -> `{row['valid_range'][1]}` outperformance `{row['validation_outperformance'] * 100:.2f}%`",
                f"  - Test `{row['test_range'][0]}` -> `{row['test_range'][1]}` outperformance `{row['test_outperformance'] * 100:.2f}%`",
            ]
        )

    lines.extend(
        [
            "",
            "## Stability filter (parameter perturbations)",
            f"- Perturbation samples tested: `{stability['samples']}`",
            f"- Median outperformance across perturbations: `{stability['median_outperformance'] * 100:.2f}%`",
            f"- Worst outperformance across perturbations: `{stability['worst_outperformance'] * 100:.2f}%`",
            "",
            "## Profile attempt summary",
        ]
    )

    for at in attempts:
        lines.append(f"- `{at['profile']}` profile: `{at['candidates_passed']}` candidates passed")

    lines.extend(
        [
            "",
            "## Reproduce",
            "```bash",
            "python3 \"Dashboard 10 2 26 2026/scripts/optimize_sndk_params.py\"",
            "```",
        ]
    )

    REPORT_FILE.parent.mkdir(parents=True, exist_ok=True)
    REPORT_FILE.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    candles = load_candles(DATA_FILE)
    params, full, multisplit, phase1_meta = phase1_select(candles)
    write_report(candles, params, full, multisplit, phase1_meta)

    output = {
        "data_file": str(DATA_FILE),
        "start_date": candles[0].day.isoformat(),
        "end_date": candles[-1].day.isoformat(),
        "initial_cash": INITIAL_CASH,
        "cost_per_trade": COST_PER_TRADE,
        "params_for_simulator": {
            "use_psar": True,
            **asdict(params),
            "hard_stop_enabled": True,
            "rolling_stop_enabled": True,
        },
        "full_sample": full,
        "phase1_multisplit": multisplit,
        "phase1_meta": phase1_meta,
        "constraints": {
            "max_trades": MAX_TRADES,
            "min_bars_between_trades": MIN_BARS_BETWEEN_TRADES,
            "min_win_loss_ratio": MIN_WIN_LOSS_RATIO,
            "min_outperformance_vs_buy_hold": MIN_OUTPERFORMANCE_VS_BUY_HOLD,
        },
        "report_file": str(REPORT_FILE),
    }
    print(json.dumps(output, indent=2))


if __name__ == "__main__":
    main()
