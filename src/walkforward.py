from __future__ import annotations

from dataclasses import dataclass
from itertools import product
from typing import Callable

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


@dataclass(frozen=True)
class MenuSettings:
    oos_years: int
    train_days: int
    test_days: int
    txn_cost_bps: float


@dataclass
class OptimizationResult:
    settings: MenuSettings
    grid: list[tuple[float, float]]
    summary: dict[str, float | str | bool]


def build_param_grid(step_min: float, step_max: float, step_n: int, max_min: float, max_max: float, max_n: int) -> list[tuple[float, float]]:
    step_vals = np.linspace(step_min, step_max, step_n)
    max_vals = np.linspace(max_min, max_max, max_n)
    return [(float(s), float(m)) for s, m in product(step_vals, max_vals) if m >= s]


def summarize_trade_stats(oos_bt: pd.DataFrame) -> dict[str, float | int]:
    trades: list[float] = []
    in_trade = False
    trade_return = 1.0

    for _, row in oos_bt.iterrows():
        position = int(row["position"])
        strat_ret = float(row["strategy_return"])

        if position == 1 and not in_trade:
            in_trade = True
            trade_return = 1.0

        if in_trade:
            trade_return *= 1 + strat_ret

            if position == 0:
                trades.append(trade_return - 1.0)
                in_trade = False

    if in_trade:
        trades.append(trade_return - 1.0)

    if not trades:
        return {
            "Trades": 0,
            "Winning Trades": 0,
            "Losing Trades": 0,
            "Win Rate": np.nan,
            "Avg Win %": np.nan,
            "Avg Loss %": np.nan,
        }

    trade_returns = np.asarray(trades, dtype=float)
    winners = trade_returns[trade_returns > 0]
    losers = trade_returns[trade_returns < 0]

    return {
        "Trades": int(trade_returns.size),
        "Winning Trades": int(winners.size),
        "Losing Trades": int(losers.size),
        "Win Rate": float(winners.size / trade_returns.size),
        "Avg Win %": float(np.mean(winners) * 100) if winners.size else np.nan,
        "Avg Loss %": float(np.mean(losers) * 100) if losers.size else np.nan,
    }


def build_diagnostic_text(
    metrics: dict[str, float | int],
    fold_df: pd.DataFrame,
    typical: dict[str, float],
    oos_bt: pd.DataFrame,
) -> str:
    lines = ["Diagnostic Text", "===============", "", "Strategy stats:"]
    for key, value in metrics.items():
        if isinstance(value, (int, np.integer)):
            formatted = f"{int(value)}"
        elif pd.isna(value):
            formatted = "nan"
        else:
            formatted = f"{float(value):.6f}"
        lines.append(f"- {key}: {formatted}")

    lines.extend(["", "Fold summary:"])
    for row in fold_df.itertuples(index=False):
        lines.append(
            "- Fold {fold}: train {train_start}→{train_end}, test {test_start}→{test_end}, "
            "step={step:.4f}, max_step={max_step:.4f}, train_obj={train_objective:.4f}".format(
                fold=row.fold,
                train_start=pd.Timestamp(row.train_start).date(),
                train_end=pd.Timestamp(row.train_end).date(),
                test_start=pd.Timestamp(row.test_start).date(),
                test_end=pd.Timestamp(row.test_end).date(),
                step=float(row.step),
                max_step=float(row.max_step),
                train_objective=float(row.train_objective),
            )
        )

    lines.extend(
        [
            "",
            "Typical params:",
            f"- median_step: {typical['median_step']:.6f}",
            f"- median_max_step: {typical['median_max_step']:.6f}",
            "",
            "Out-of-sample diagnostics:",
            f"- OOS rows: {len(oos_bt)}",
            f"- Date range: {oos_bt.index.min().date()} to {oos_bt.index.max().date()}",
            f"- Buy signals: {int(oos_bt['buy_signal'].sum())}",
            f"- Sell signals: {int(oos_bt['sell_signal'].sum())}",
        ]
    )

    return "\n".join(lines)


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
    for fr in fold_results:
        seg = df.loc[fr.test_start:fr.test_end]
        bt = run_psar_strategy(seg, fr.step, fr.max_step, txn_cost_bps)
        oos_detail.append(bt)
    oos_bt = pd.concat(oos_detail).sort_index()
    turnover = float(oos_bt["position_change"].mean() * 252)
    invested_pct = float(oos_bt["position"].mean())
    bench_oos = benchmark_returns.reindex(oos_returns.index).fillna(0.0)
    metrics = summarize_performance(oos_returns, bench_oos, turnover=turnover, invested_pct=invested_pct)
    metrics.update(summarize_trade_stats(oos_bt))

    buy_hold_equity = (oos_bt["Close"] / float(oos_bt["Close"].iloc[0])) * float((1 + oos_returns.iloc[0]))
    oos_bt = oos_bt.assign(
        buy_signal=((oos_bt["position"] == 1) & (oos_bt["position"].shift(1).fillna(0) == 0)),
        sell_signal=((oos_bt["position"] == 0) & (oos_bt["position"].shift(1).fillna(0) == 1)),
    )

    fold_df = pd.DataFrame([vars(f) for f in fold_results])
    typical = {
        "median_step": float(fold_df["step"].median()),
        "median_max_step": float(fold_df["max_step"].median()),
    }
    diagnostic_text = build_diagnostic_text(metrics, fold_df, typical, oos_bt)

    return {
        "oos_returns": oos_returns,
        "oos_equity": (1 + oos_returns).cumprod(),
        "folds": fold_df,
        "typical": typical,
        "metrics": metrics,
        "diagnostic_text": diagnostic_text,
        "buy_hold_equity": buy_hold_equity,
        "oos_detail": oos_bt[["Close", "position", "buy_signal", "sell_signal"]],
    }


def focused_grid_around_typical(typical: dict, step_n: int = 11, max_n: int = 11) -> list[tuple[float, float]]:
    center_step = float(typical["median_step"])
    center_max = float(typical["median_max_step"])
    step_min = max(0.001, center_step - 0.015)
    step_max = min(0.08, center_step + 0.015)
    max_min = max(0.08, center_max - 0.06)
    max_max = min(0.40, center_max + 0.06)
    return build_param_grid(step_min, step_max, step_n, max_min, max_max, max_n)


def optimize_menu_settings(
    price_map: dict[str, pd.DataFrame],
    benchmark_returns: pd.Series,
    tickers_to_run: list[str],
    objective_mode: str = "cagr",
    beta_penalty_enabled: bool = True,
    progress_cb: Callable[[int, int, str], None] | None = None,
) -> OptimizationResult:
    candidates = [
        MenuSettings(oos_years=oos, train_days=train, test_days=test, txn_cost_bps=cost)
        for oos, train, test, cost in product([5, 7], [504, 756, 1008], [42, 63, 126], [2.0, 5.0, 10.0])
    ]
    coarse_grid = build_param_grid(0.005, 0.08, 9, 0.08, 0.40, 9)

    best: OptimizationResult | None = None
    total = len(candidates)
    for i, candidate in enumerate(candidates, start=1):
        per_ticker = {}
        for ticker in tickers_to_run:
            if ticker not in price_map:
                continue
            coarse = run_walk_forward_for_ticker(
                price_df=price_map[ticker],
                benchmark_returns=benchmark_returns,
                train_days=candidate.train_days,
                test_days=candidate.test_days,
                oos_years=candidate.oos_years,
                grid=coarse_grid,
                txn_cost_bps=candidate.txn_cost_bps,
            )
            fine_grid = focused_grid_around_typical(coarse["typical"], step_n=11, max_n=11)
            per_ticker[ticker] = run_walk_forward_for_ticker(
                price_df=price_map[ticker],
                benchmark_returns=benchmark_returns,
                train_days=candidate.train_days,
                test_days=candidate.test_days,
                oos_years=candidate.oos_years,
                grid=fine_grid,
                txn_cost_bps=candidate.txn_cost_bps,
            )

        if per_ticker:
            cagr_values = [v["metrics"]["CAGR"] for v in per_ticker.values()]
            alpha_values = [v["metrics"]["Alpha (ann)"] for v in per_ticker.values()]
            sharpe_values = [v["metrics"]["Sharpe"] for v in per_ticker.values()]
            beta_values = [v["metrics"]["Beta"] for v in per_ticker.values()]

            mean_cagr = float(np.nanmean(cagr_values))
            mean_alpha = float(np.nanmean(alpha_values))
            mean_sharpe = float(np.nanmean(sharpe_values))
            mean_beta = float(np.nanmean(beta_values))

            if objective_mode == "alpha":
                objective_value = mean_alpha
            elif objective_mode == "sharpe":
                objective_value = mean_sharpe
            else:
                objective_value = mean_cagr

            beta_penalty = (0.15 * abs(mean_beta - 1.0)) if beta_penalty_enabled else 0.0
            score = objective_value - beta_penalty

            summary: dict[str, float | str | bool] = {
                "score": score,
                "objective_mode": objective_mode,
                "objective_value": objective_value,
                "beta_penalty_enabled": beta_penalty_enabled,
                "beta_penalty": beta_penalty,
                "mean_cagr": mean_cagr,
                "mean_alpha": mean_alpha,
                "mean_sharpe": mean_sharpe,
                "mean_beta": mean_beta,
            }
            if best is None or summary["score"] > best.summary["score"]:
                primary_typical = per_ticker[tickers_to_run[0]]["typical"]
                best = OptimizationResult(
                    settings=candidate,
                    grid=focused_grid_around_typical(primary_typical, step_n=11, max_n=11),
                    summary=summary,
                )

        if progress_cb:
            progress_cb(i, total, f"Evaluated {i}/{total} menu combinations")

    if best is None:
        raise ValueError("Unable to score any menu setting combinations.")
    return best
