from __future__ import annotations

import numpy as np
import pandas as pd

from .metrics import summarize_performance


def simulate_long_flat(
    close: pd.Series,
    signal: pd.Series,
    initial_cash: float,
    cost_per_trade: float,
) -> pd.DataFrame:
    """Simulate a long/flat strategy with all-in/all-out allocation and fixed trade costs.

    Trades are executed at today's close using yesterday's signal.
    """
    idx = close.index
    target_pos = signal.shift(1).fillna(0).astype(int)

    cash = float(initial_cash)
    shares = 0.0
    invested = 0

    equity = []
    strategy_returns = []
    trade_costs = []
    position = []
    buys = []
    sells = []

    prev_equity = float(initial_cash)
    for dt, price in close.items():
        buy_price = np.nan
        sell_price = np.nan
        desired = int(target_pos.loc[dt])

        if desired != invested:
            if desired == 1:
                if cash > cost_per_trade:
                    cash -= cost_per_trade
                    shares = cash / price
                    cash = 0.0
                    invested = 1
                    buy_price = float(price)
                    trade_cost = cost_per_trade
                else:
                    trade_cost = 0.0
            else:
                cash += shares * price
                shares = 0.0
                if cash > 0:
                    cash = max(0.0, cash - cost_per_trade)
                invested = 0
                sell_price = float(price)
                trade_cost = cost_per_trade
        else:
            trade_cost = 0.0

        eq = cash + shares * price
        ret = 0.0 if prev_equity == 0 else (eq / prev_equity - 1)

        equity.append(eq)
        strategy_returns.append(ret)
        trade_costs.append(trade_cost)
        position.append(invested)
        buys.append(buy_price)
        sells.append(sell_price)
        prev_equity = eq

    out = pd.DataFrame(
        {
            "Close": close,
            "signal": signal,
            "position": position,
            "trade_cost": trade_costs,
            "strategy_return": strategy_returns,
            "equity": equity,
            "buy_price": buys,
            "sell_price": sells,
        },
        index=idx,
    )
    return out


def buy_and_hold_equity(close: pd.Series, initial_cash: float) -> pd.Series:
    start = float(close.iloc[0])
    return (close / start) * float(initial_cash)


def summarize_run(strategy_df: pd.DataFrame, benchmark_returns: pd.Series) -> dict[str, float]:
    strategy_returns = strategy_df["strategy_return"].fillna(0.0)
    aligned_bench = benchmark_returns.reindex(strategy_df.index).fillna(0.0)
    position_change = strategy_df["position"].diff().abs().fillna(strategy_df["position"]).astype(float)
    turnover = float(position_change.sum())
    invested_pct = float(strategy_df["position"].mean())
    metrics = summarize_performance(strategy_returns, aligned_bench, turnover=turnover, invested_pct=invested_pct)
    metrics["Final Equity"] = float(strategy_df["equity"].iloc[-1])
    metrics["Total Return"] = float(strategy_df["equity"].iloc[-1] / strategy_df["equity"].iloc[0] - 1)
    metrics["Number of Trades"] = float(position_change.sum())
    return metrics
