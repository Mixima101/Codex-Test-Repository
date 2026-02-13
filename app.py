from __future__ import annotations

import datetime as dt

import pandas as pd
import streamlit as st

from src.data import download_ohlcv, normalize_tickers
from src.walkforward import build_param_grid, run_walk_forward_for_ticker

st.set_page_config(page_title="PSAR Walk-Forward Lab", layout="wide")
st.title("Parabolic SAR Walk-Forward Optimization (Daily)")

with st.sidebar:
    st.header("Inputs")
    primary = st.text_input("Primary ticker", value="AAPL")
    validation = st.text_input("Validation tickers (comma-separated)", value="MSFT,GOOGL,AMZN")
    benchmark = st.text_input("Benchmark ticker", value="SPY")

    oos_years = st.slider("Out-of-sample years", min_value=2, max_value=10, value=5)
    train_days = st.number_input("Rolling train window (trading days)", min_value=126, max_value=2520, value=504, step=21)
    test_days = st.number_input("Forward test window (trading days)", min_value=21, max_value=504, value=63, step=21)

    st.subheader("PSAR parameter grid")
    step_min = st.number_input("AF step min", min_value=0.001, max_value=0.2, value=0.01, step=0.001, format="%.3f")
    step_max = st.number_input("AF step max", min_value=0.001, max_value=0.3, value=0.05, step=0.001, format="%.3f")
    step_n = st.slider("AF step grid size", min_value=2, max_value=20, value=7)

    max_min = st.number_input("AF max min", min_value=0.01, max_value=0.5, value=0.1, step=0.01, format="%.2f")
    max_max = st.number_input("AF max max", min_value=0.01, max_value=1.0, value=0.3, step=0.01, format="%.2f")
    max_n = st.slider("AF max grid size", min_value=2, max_value=20, value=7)

    txn_cost_bps = st.number_input("Transaction cost (bps per position change)", min_value=0.0, max_value=100.0, value=2.0, step=0.5)
    run_btn = st.button("Run walk-forward", type="primary")


@st.cache_data(show_spinner=False)
def cached_download(tickers: tuple[str, ...], start: str, end: str, threads: bool = False):
    return download_ohlcv(tickers, start=start, end=end, threads=threads)


@st.cache_data(show_spinner=False)
def cached_walk_forward(price_df: pd.DataFrame, benchmark_returns: pd.Series, train_days: int, test_days: int, oos_years: int, grid: tuple[tuple[float, float], ...], txn_cost_bps: float):
    return run_walk_forward_for_ticker(
        price_df=price_df,
        benchmark_returns=benchmark_returns,
        train_days=train_days,
        test_days=test_days,
        oos_years=oos_years,
        grid=list(grid),
        txn_cost_bps=txn_cost_bps,
    )


if run_btn:
    tickers = normalize_tickers(primary, validation, benchmark)
    start = (dt.date.today() - dt.timedelta(days=365 * 12)).isoformat()
    end = dt.date.today().isoformat()

    with st.spinner("Downloading OHLCV from Yahoo Finance..."):
        data_map = cached_download(tuple(tickers), start, end, False)

    missing = [t for t in tickers if t not in data_map]
    if missing:
        st.warning(f"No data returned for: {missing}")

    if benchmark not in data_map:
        st.error("Benchmark data not available. Please choose another benchmark ticker.")
        st.stop()

    bench_ret = data_map[benchmark]["Close"].pct_change().fillna(0.0)

    grid = build_param_grid(step_min, step_max, step_n, max_min, max_max, max_n)
    st.caption(f"Grid size: {len(grid)} parameter pairs.")

    tickers_to_run = [primary] + [t.strip().upper() for t in validation.split(",") if t.strip()]
    tickers_to_run = [t for i, t in enumerate(tickers_to_run) if t and t not in tickers_to_run[:i]]

    results = {}
    for t in tickers_to_run:
        if t not in data_map:
            continue
        try:
            results[t] = cached_walk_forward(
                data_map[t],
                bench_ret,
                int(train_days),
                int(test_days),
                int(oos_years),
                tuple(grid),
                float(txn_cost_bps),
            )
        except Exception as e:
            st.warning(f"{t}: {e}")

    if primary in results:
        res = results[primary]
        st.subheader(f"Primary ticker: {primary}")

        col1, col2 = st.columns([2, 1])
        with col1:
            st.line_chart(res["oos_equity"], y_label="Equity", x_label="Date")
        with col2:
            st.dataframe(pd.DataFrame([res["metrics"]]).T.rename(columns={0: "value"}))

        st.markdown("**Chosen params per fold**")
        st.dataframe(res["folds"], use_container_width=True)
        st.markdown("**Typical params (median across folds)**")
        st.json(res["typical"])
        st.markdown("**Recommended params (most stable across folds)**")
        st.json(res["recommended"])

    st.subheader("Validation summary")
    rows = []
    for t, r in results.items():
        row = {"Ticker": t, **r["metrics"]}
        rows.append(row)
    if rows:
        val_df = pd.DataFrame(rows).set_index("Ticker")
        st.dataframe(val_df, use_container_width=True)

        agg = {
            "Mean OOS CAGR": float(val_df["CAGR"].mean()),
            "Median OOS CAGR": float(val_df["CAGR"].median()),
            "Share positive alpha": float((val_df["Alpha (ann)"] > 0).mean()),
            "Share Sharpe > benchmark": float((val_df["Sharpe"] > val_df["Benchmark Sharpe"]).mean()),
        }
        st.markdown("**Aggregate validation summary**")
        st.json(agg)
    else:
        st.info("No ticker produced valid walk-forward output.")
else:
    st.info("Configure settings in sidebar, then click **Run walk-forward**.")
