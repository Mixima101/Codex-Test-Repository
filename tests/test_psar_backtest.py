import numpy as np
import pandas as pd

from src.backtest import run_psar_strategy
from src.psar import parabolic_sar
from src.walkforward import run_walk_forward_for_ticker


def synthetic_ohlc(n: int = 120) -> pd.DataFrame:
    idx = pd.bdate_range("2022-01-03", periods=n)
    base = np.linspace(100, 130, n) + np.sin(np.linspace(0, 8, n))
    close = pd.Series(base, index=idx)
    high = close + 1.0
    low = close - 1.0
    open_ = close.shift(1).fillna(close.iloc[0])
    vol = pd.Series(1_000_000, index=idx)
    return pd.DataFrame({"Open": open_, "High": high, "Low": low, "Close": close, "Volume": vol}, index=idx)


def test_psar_shape_and_index():
    df = synthetic_ohlc()
    psar = parabolic_sar(df["High"], df["Low"], df["Close"], step=0.02, max_step=0.2)
    assert len(psar) == len(df)
    assert psar.index.equals(df.index)


def test_backtest_return_alignment():
    df = synthetic_ohlc()
    bt = run_psar_strategy(df, step=0.02, max_step=0.2, txn_cost_bps=1.0)
    assert bt["strategy_return"].index.equals(df.index)
    assert bt["position"].iloc[0] == 0
    # position comes from prior-day signal
    signal = (bt["Close"] > bt["psar"]).astype(int)
    expected = signal.shift(1).fillna(0).astype(int)
    assert bt["position"].equals(expected)


def test_walkforward_returns_recommended_params():
    df = synthetic_ohlc(900)
    bench = pd.Series(0.0, index=df.index)

    res = run_walk_forward_for_ticker(
        price_df=df,
        benchmark_returns=bench,
        train_days=252,
        test_days=63,
        oos_years=2,
        grid=[(0.01, 0.1), (0.02, 0.2), (0.03, 0.3)],
        txn_cost_bps=0.0,
    )

    rec = res["recommended"]
    assert {"step", "max_step", "folds_selected", "mean_train_objective"}.issubset(rec.keys())
    assert rec["folds_selected"] >= 1
    fold_pairs = set(tuple(x) for x in res["folds"][["step", "max_step"]].to_numpy())
    assert (rec["step"], rec["max_step"]) in fold_pairs
