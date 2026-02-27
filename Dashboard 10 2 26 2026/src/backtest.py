from __future__ import annotations

import numpy as np
import pandas as pd

from .psar import parabolic_sar


def run_psar_strategy(df: pd.DataFrame, step: float, max_step: float, txn_cost_bps: float = 0.0) -> pd.DataFrame:
    """Long/flat PSAR strategy with next-day execution and costs on position change."""
    data = df.copy()
    data["psar"] = parabolic_sar(data["High"], data["Low"], data["Close"], step=step, max_step=max_step)

    signal_today = (data["Close"] > data["psar"]).astype(int)
    data["position"] = signal_today.shift(1).fillna(0).astype(int)

    data["asset_return"] = data["Close"].pct_change().fillna(0.0)
    data["position_change"] = data["position"].diff().abs().fillna(data["position"]).astype(float)
    cost_per_turn = txn_cost_bps / 10_000.0
    data["cost"] = data["position_change"] * cost_per_turn
    data["strategy_return"] = data["position"] * data["asset_return"] - data["cost"]
    data["equity"] = (1 + data["strategy_return"]).cumprod()
    return data


def objective_sharpe(df: pd.DataFrame) -> float:
    r = df["strategy_return"]
    vol = r.std(ddof=0)
    if vol == 0 or np.isnan(vol):
        return -np.inf
    return float(r.mean() / vol * np.sqrt(252))
