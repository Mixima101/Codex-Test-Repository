from __future__ import annotations

import datetime as dt
from dataclasses import dataclass
from typing import Callable

import pandas as pd

from .data import download_ohlcv, normalize_tickers
from .walkforward import build_param_grid, run_walk_forward_for_ticker


@dataclass
class SweepConfig:
    oos_years: int
    train_days: int
    test_days: int
    txn_cost_bps: float
    step_min: float
    step_max: float
    step_n: int
    max_min: float
    max_max: float
    max_n: int


@dataclass
class SweepState:
    completed: int
    total: int
    pass_name: str
    oos_years: int
    train_days: int
    test_days: int
    txn_cost_bps: float
    score: float
    recommended_step: float
    recommended_max_step: float
    metrics: dict[str, float]


def _score_row(metrics: dict[str, float], folds_selected: int) -> float:
    sharpe = float(metrics.get("Sharpe", 0.0))
    cagr = float(metrics.get("CAGR", 0.0))
    mdd = abs(float(metrics.get("Max Drawdown", 0.0)))
    turnover = float(metrics.get("Turnover", 0.0))
    alpha = float(metrics.get("Alpha (ann)", 0.0))
    return (2.0 * sharpe) + cagr + (0.5 * alpha) - (1.5 * mdd) - (0.005 * turnover) + (0.01 * folds_selected)


def _focused_grid_bounds(folds_df: pd.DataFrame) -> tuple[float, float, float, float]:
    step_q20, step_q80 = folds_df["step"].quantile([0.2, 0.8]).tolist()
    max_q20, max_q80 = folds_df["max_step"].quantile([0.2, 0.8]).tolist()

    step_min = max(0.001, step_q20 * 0.85)
    step_max = min(0.2, step_q80 * 1.15)
    max_min = max(0.01, max_q20 * 0.85)
    max_max = min(1.0, max_q80 * 1.15)

    if max_min < step_min:
        max_min = step_min

    return float(step_min), float(step_max), float(max_min), float(max_max)


def _format_best_summary(best: dict) -> str:
    lines = [
        "Best configuration from automated sweep",
        f"- OOS years: {int(best['oos_years'])}",
        f"- Train days: {int(best['train_days'])}",
        f"- Test days: {int(best['test_days'])}",
        f"- Transaction cost (bps): {float(best['txn_cost_bps']):.2f}",
        f"- Focused grid: step [{best['focused_step_min']:.4f}, {best['focused_step_max']:.4f}] x {int(best['focused_step_n'])}; max [{best['focused_max_min']:.4f}, {best['focused_max_max']:.4f}] x {int(best['focused_max_n'])}",
        f"- Recommended PSAR params: step={best['recommended_step']:.4f}, max_step={best['recommended_max_step']:.4f}",
        f"- Score: {best['score']:.4f}",
        "",
        "OOS performance snapshot",
        f"- CAGR: {best['CAGR']:.4f}",
        f"- Sharpe: {best['Sharpe']:.4f}",
        f"- Max Drawdown: {best['Max Drawdown']:.4f}",
        f"- Volatility: {best['Volatility']:.4f}",
        f"- Alpha (ann): {best['Alpha (ann)']:.4f}",
        f"- Beta: {best['Beta']:.4f}",
        f"- R^2: {best['R^2']:.4f}",
        f"- Turnover: {best['Turnover']:.4f}",
        f"- % Time Invested: {best['% Time Invested']:.4f}",
        f"- Benchmark Sharpe: {best['Benchmark Sharpe']:.4f}",
    ]
    return "\n".join(lines)


def run_two_pass_sweep(
    ticker: str,
    validation: str,
    benchmark: str,
    oos_years_options: list[int],
    train_days_options: list[int],
    test_days_options: list[int],
    txn_cost_options: list[float],
    focused_grid_n: int = 11,
    progress_callback: Callable[[SweepState], None] | None = None,
) -> tuple[pd.DataFrame, dict, dict]:
    tickers = normalize_tickers(ticker, validation, benchmark)
    start = (dt.date.today() - dt.timedelta(days=365 * 12)).isoformat()
    end = dt.date.today().isoformat()
    data_map = download_ohlcv(tuple(tickers), start=start, end=end, threads=False)

    if ticker not in data_map:
        raise ValueError(f"Primary ticker {ticker} not available from data source")
    if benchmark not in data_map:
        raise ValueError(f"Benchmark ticker {benchmark} not available from data source")

    bench_ret = data_map[benchmark]["Close"].pct_change().fillna(0.0)

    rows: list[dict] = []
    combinations = len(oos_years_options) * len(train_days_options) * len(test_days_options) * len(txn_cost_options)
    completed = 0

    for oos in oos_years_options:
        for train in train_days_options:
            for test in test_days_options:
                for cost in txn_cost_options:
                    try:
                        coarse = SweepConfig(oos, train, test, cost, 0.005, 0.08, 9, 0.08, 0.40, 9)
                        coarse_grid = build_param_grid(coarse.step_min, coarse.step_max, coarse.step_n, coarse.max_min, coarse.max_max, coarse.max_n)
                        coarse_res = run_walk_forward_for_ticker(
                            price_df=data_map[ticker],
                            benchmark_returns=bench_ret,
                            train_days=coarse.train_days,
                            test_days=coarse.test_days,
                            oos_years=coarse.oos_years,
                            grid=coarse_grid,
                            txn_cost_bps=coarse.txn_cost_bps,
                        )

                        step_min, step_max, max_min, max_max = _focused_grid_bounds(coarse_res["folds"])
                        focused = SweepConfig(oos, train, test, cost, step_min, step_max, focused_grid_n, max_min, max_max, focused_grid_n)
                        focused_grid = build_param_grid(
                            focused.step_min,
                            focused.step_max,
                            focused.step_n,
                            focused.max_min,
                            focused.max_max,
                            focused.max_n,
                        )
                        focused_res = run_walk_forward_for_ticker(
                            price_df=data_map[ticker],
                            benchmark_returns=bench_ret,
                            train_days=focused.train_days,
                            test_days=focused.test_days,
                            oos_years=focused.oos_years,
                            grid=focused_grid,
                            txn_cost_bps=focused.txn_cost_bps,
                        )

                        rec = focused_res["recommended"]
                        metrics = focused_res["metrics"]
                        score = _score_row(metrics, int(rec["folds_selected"]))

                        row = {
                            "oos_years": oos,
                            "train_days": train,
                            "test_days": test,
                            "txn_cost_bps": cost,
                            "coarse_step_min": coarse.step_min,
                            "coarse_step_max": coarse.step_max,
                            "coarse_step_n": coarse.step_n,
                            "coarse_max_min": coarse.max_min,
                            "coarse_max_max": coarse.max_max,
                            "coarse_max_n": coarse.max_n,
                            "focused_step_min": focused.step_min,
                            "focused_step_max": focused.step_max,
                            "focused_step_n": focused.step_n,
                            "focused_max_min": focused.max_min,
                            "focused_max_max": focused.max_max,
                            "focused_max_n": focused.max_n,
                            "recommended_step": rec["step"],
                            "recommended_max_step": rec["max_step"],
                            "folds_selected": rec["folds_selected"],
                            "mean_train_objective": rec["mean_train_objective"],
                            **metrics,
                            "score": score,
                        }
                        rows.append(row)

                        completed += 1
                        if progress_callback is not None:
                            progress_callback(
                                SweepState(
                                    completed=completed,
                                    total=combinations,
                                    pass_name="focused",
                                    oos_years=oos,
                                    train_days=train,
                                    test_days=test,
                                    txn_cost_bps=cost,
                                    score=score,
                                    recommended_step=float(rec["step"]),
                                    recommended_max_step=float(rec["max_step"]),
                                    metrics=metrics,
                                )
                            )
                    except Exception as exc:
                        completed += 1
                        rows.append(
                            {
                                "oos_years": oos,
                                "train_days": train,
                                "test_days": test,
                                "txn_cost_bps": cost,
                                "error": str(exc),
                            }
                        )

    summary = pd.DataFrame(rows)
    valid = summary[summary.get("error").isna()].copy() if "error" in summary.columns else summary.copy()
    if valid.empty:
        raise ValueError("No valid optimization result. Check ticker data or sweep ranges.")

    valid = valid.sort_values("score", ascending=False).reset_index(drop=True)
    best = valid.iloc[0].to_dict()

    best_grid = build_param_grid(
        float(best["focused_step_min"]),
        float(best["focused_step_max"]),
        int(best["focused_step_n"]),
        float(best["focused_max_min"]),
        float(best["focused_max_max"]),
        int(best["focused_max_n"]),
    )
    best_detail = run_walk_forward_for_ticker(
        price_df=data_map[ticker],
        benchmark_returns=bench_ret,
        train_days=int(best["train_days"]),
        test_days=int(best["test_days"]),
        oos_years=int(best["oos_years"]),
        grid=best_grid,
        txn_cost_bps=float(best["txn_cost_bps"]),
    )

    best_detail["summary_text"] = _format_best_summary(best)
    return valid, best, best_detail
