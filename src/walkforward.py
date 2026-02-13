from __future__ import annotations

from dataclasses import dataclass
from itertools import product

import numpy as np
import pandas as pd

from .backtest import objective_sharpe, run_psar_strategy
from .metrics import summarize_performance


@dataclass
class FoldResult:
    fold: int
    train_start: pd.Timestamp
    train_end: pd.Timestamp
    test_start: pd.Timestamp
    test_end: pd.Timestamp
    step: float
    max_step: float
    train_objective: float


def build_param_grid(step_min: float, step_max: float, step_n: int, max_min: float, max_max: float, max_n: int) -> list[tuple[float, float]]:
    step_vals = np.linspace(step_min, step_max, step_n)
    max_vals = np.linspace(max_min, max_max, max_n)
    return [(float(s), float(m)) for s, m in product(step_vals, max_vals) if m >= s]


def run_walk_forward_for_ticker(
    price_df: pd.DataFrame,
    benchmark_returns: pd.Series,
    train_days: int,
    test_days: int,
    oos_years: int,
    grid: list[tuple[float, float]],
    txn_cost_bps: float,
) -> dict:
    df = price_df.sort_index().copy()
    oos_days = int(oos_years * 252)
    if len(df) < train_days + test_days + 50:
        raise ValueError("Not enough history for requested walk-forward settings.")

    oos_end_idx = len(df)
    oos_start_idx = max(0, oos_end_idx - oos_days)
    first_test_start = oos_start_idx

    fold_results: list[FoldResult] = []
    stitched_returns = []

    fold = 1
    test_start_idx = first_test_start
    while test_start_idx < oos_end_idx:
        test_end_idx = min(test_start_idx + test_days, oos_end_idx)
        train_end_idx = test_start_idx
        train_start_idx = max(0, train_end_idx - train_days)
        if (train_end_idx - train_start_idx) < max(100, train_days // 2):
            break

        train_df = df.iloc[train_start_idx:train_end_idx]
        best = None
        best_obj = -np.inf
        for step, mx in grid:
            bt_train = run_psar_strategy(train_df, step=step, max_step=mx, txn_cost_bps=txn_cost_bps)
            obj = objective_sharpe(bt_train)
            if obj > best_obj:
                best_obj = obj
                best = (step, mx)

        if best is None:
            break

        test_df = df.iloc[test_start_idx:test_end_idx]
        bt_test = run_psar_strategy(test_df, step=best[0], max_step=best[1], txn_cost_bps=txn_cost_bps)
        stitched_returns.append(bt_test["strategy_return"])

        fold_results.append(
            FoldResult(
                fold=fold,
                train_start=train_df.index[0],
                train_end=train_df.index[-1],
                test_start=test_df.index[0],
                test_end=test_df.index[-1],
                step=best[0],
                max_step=best[1],
                train_objective=float(best_obj),
            )
        )

        fold += 1
        test_start_idx = test_end_idx

    if not stitched_returns:
        raise ValueError("Walk-forward produced no test folds.")

    oos_returns = pd.concat(stitched_returns).sort_index()
    oos_returns = oos_returns[~oos_returns.index.duplicated(keep="first")]

    # turnover/time invested from full OOS run, reapplying fold params to each segment
    oos_detail = []
    idx = first_test_start
    for fr in fold_results:
        seg = df.loc[fr.test_start:fr.test_end]
        bt = run_psar_strategy(seg, fr.step, fr.max_step, txn_cost_bps)
        oos_detail.append(bt)
        idx += len(seg)
    oos_bt = pd.concat(oos_detail).sort_index()
    turnover = float(oos_bt["position_change"].mean() * 252)
    invested_pct = float(oos_bt["position"].mean())

    bench_oos = benchmark_returns.reindex(oos_returns.index).fillna(0.0)
    metrics = summarize_performance(oos_returns, bench_oos, turnover=turnover, invested_pct=invested_pct)

    fold_df = pd.DataFrame([vars(f) for f in fold_results])
    typical = {
        "median_step": float(fold_df["step"].median()),
        "median_max_step": float(fold_df["max_step"].median()),
    }

    grouped = (
        fold_df.groupby(["step", "max_step"], as_index=False)
        .agg(folds_selected=("fold", "count"), mean_train_objective=("train_objective", "mean"))
        .sort_values(["folds_selected", "mean_train_objective"], ascending=[False, False])
    )
    recommended_row = grouped.iloc[0]
    recommended = {
        "step": float(recommended_row["step"]),
        "max_step": float(recommended_row["max_step"]),
        "folds_selected": int(recommended_row["folds_selected"]),
        "mean_train_objective": float(recommended_row["mean_train_objective"]),
    }

    return {
        "oos_returns": oos_returns,
        "oos_equity": (1 + oos_returns).cumprod(),
        "folds": fold_df,
        "typical": typical,
        "recommended": recommended,
        "metrics": metrics,
    }
