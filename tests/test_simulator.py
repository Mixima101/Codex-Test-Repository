import pandas as pd

from src.simulator import buy_and_hold_equity, simulate_long_flat


def test_buy_and_hold_equity_scales_from_initial_cash():
    close = pd.Series([100.0, 105.0, 110.0], index=pd.date_range("2024-01-01", periods=3, freq="D"))
    eq = buy_and_hold_equity(close, initial_cash=1000.0)
    assert eq.iloc[0] == 1000.0
    assert eq.iloc[-1] == 1100.0


def test_simulate_long_flat_executes_next_day():
    idx = pd.date_range("2024-01-01", periods=4, freq="D")
    close = pd.Series([10.0, 10.0, 20.0, 20.0], index=idx)
    # Buy signal arrives on day 2, executed on day 3 at close=20
    signal = pd.Series([0, 1, 1, 0], index=idx)

    out = simulate_long_flat(close, signal, initial_cash=1000.0, cost_per_trade=0.0)

    assert out.loc[idx[1], "position"] == 0
    assert out.loc[idx[2], "position"] == 1
    assert out.loc[idx[2], "buy_price"] == 20.0
