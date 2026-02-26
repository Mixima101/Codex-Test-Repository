from __future__ import annotations

import numpy as np
import pandas as pd

from .metrics import summarize_performance


def simulate_long_flat(
    close: pd.Series,
    signal: pd.Series,
    initial_cash: float,
    cost_per_trade: float,
    hard_stop_pct: float | None = None,
    trailing_stop_pct: float | None = None,
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
    stop_levels = []
    stop_exits = []

    entry_price: float | None = None
    highest_close: float | None = None

    prev_equity = float(initial_cash)
    for dt, price in close.items():
        buy_price = np.nan
        sell_price = np.nan
        desired = int(target_pos.loc[dt])

        stop_level = np.nan
        stop_exit = 0
        if invested == 1:
            if highest_close is None:
                highest_close = float(price)
            else:
                highest_close = max(highest_close, float(price))

            candidate_levels: list[float] = []
            if hard_stop_pct is not None and entry_price is not None:
                candidate_levels.append(entry_price * (1 - hard_stop_pct))
            if trailing_stop_pct is not None:
                candidate_levels.append(highest_close * (1 - trailing_stop_pct))

            if candidate_levels:
                stop_level = max(candidate_levels)
                if price <= stop_level:
                    desired = 0
                    stop_exit = 1

        if desired != invested:
            if desired == 1:
                if cash > cost_per_trade:
                    cash -= cost_per_trade
                    shares = cash / price
                    cash = 0.0
                    invested = 1
                    entry_price = float(price)
                    highest_close = float(price)
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
                entry_price = None
                highest_close = None
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
        stop_levels.append(stop_level)
        stop_exits.append(stop_exit)
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
            "stop_level": stop_levels,
            "stop_exit": stop_exits,
        },
        index=idx,
    )
    return out


def calculate_trade_returns(strategy_df: pd.DataFrame) -> list[float]:
    trade_returns: list[float] = []
    entry_price: float | None = None

    for _, row in strategy_df.iterrows():
        buy_price = row.get("buy_price")
        sell_price = row.get("sell_price")

        if pd.notna(buy_price):
            entry_price = float(buy_price)

        if pd.notna(sell_price) and entry_price is not None and entry_price > 0:
            trade_returns.append(float(sell_price) / entry_price - 1.0)
            entry_price = None

    return trade_returns


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
    trade_returns = calculate_trade_returns(strategy_df)
    winning_trades = sum(1 for ret in trade_returns if ret > 0)
    losing_trades = sum(1 for ret in trade_returns if ret < 0)
    if losing_trades == 0:
        win_loss_ratio = float("inf") if winning_trades > 0 else 0.0
    else:
        win_loss_ratio = winning_trades / losing_trades

    avg_trade_return_pct = float(np.mean(trade_returns) * 100.0) if trade_returns else 0.0

    metrics["Final Equity"] = float(strategy_df["equity"].iloc[-1])
    metrics["Total Return"] = float(strategy_df["equity"].iloc[-1] / strategy_df["equity"].iloc[0] - 1)
    metrics["Number of Trades"] = float(position_change.sum())
    metrics["Winning Trades"] = float(winning_trades)
    metrics["Losing Trades"] = float(losing_trades)
    metrics["Win/Loss Ratio"] = float(win_loss_ratio)
    metrics["Average Return Per Trade (%)"] = avg_trade_return_pct
    return metrics
