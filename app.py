from __future__ import annotations

import datetime as dt

import altair as alt
import pandas as pd
import streamlit as st

from src.data import download_ohlcv
from src.psar import parabolic_sar
from src.simulator import buy_and_hold_equity, simulate_long_flat, summarize_run

st.set_page_config(page_title="PSAR Strategy Simulator", layout="wide")
st.title("PSAR Strategy Simulator")


def parse_float_input(raw: str, label: str) -> float:
    text = raw.strip().replace(",", "")
    try:
        return float(text)
    except ValueError as exc:
        raise ValueError(f"{label} must be a valid number.") from exc



with st.sidebar:
    st.header("Simulation Inputs")
    ticker = st.text_input("Ticker", value="AAPL").strip().upper()
    market_ticker = st.text_input("Market portfolio ticker", value="SPY").strip().upper()

    start_step_text = st.text_input("PSAR start step", value="0.02", help="Initial PSAR acceleration factor (AF). Paste any decimal value.")
    step_text = st.text_input("PSAR step", value="0.02", help="PSAR AF increment. Paste any decimal value.")
    max_step_text = st.text_input("PSAR max step", value="0.2", help="PSAR AF ceiling. Paste any decimal value.")

    cost_per_trade_text = st.text_input("Cost per trade ($)", value="1.0")
    initial_cash_text = st.text_input("Starting account value ($)", value="10000.0")

    default_start = dt.date.today() - dt.timedelta(days=365 * 5)
    start_date = st.date_input("Begin date", value=default_start)
    end_date = st.date_input("End date", value=dt.date.today())

    simulate_btn = st.button("Simulate", type="primary")


@st.cache_data(show_spinner=False)
def cached_download(ticker_list: tuple[str, ...], start: str, end: str):
    return download_ohlcv(ticker_list, start=start, end=end, threads=False)


if simulate_btn:
    if start_date >= end_date:
        st.error("Begin date must be before end date.")
        st.stop()
    try:
        start_step = parse_float_input(start_step_text, "PSAR start step")
        step = parse_float_input(step_text, "PSAR step")
        max_step = parse_float_input(max_step_text, "PSAR max step")
        cost_per_trade = parse_float_input(cost_per_trade_text, "Cost per trade")
        initial_cash = parse_float_input(initial_cash_text, "Starting account value")
    except ValueError as exc:
        st.error(str(exc))
        st.stop()

    if start_step <= 0 or step <= 0 or max_step <= 0:
        st.error("PSAR start step, step, and max step must all be greater than 0.")
        st.stop()
    if start_step > max_step:
        st.error("PSAR start step must be less than or equal to max step.")
        st.stop()
    if step > max_step:
        st.error("PSAR step must be less than or equal to max step.")
        st.stop()
    if cost_per_trade < 0:
        st.error("Cost per trade cannot be negative.")
        st.stop()
    if initial_cash <= 0:
        st.error("Starting account value must be greater than 0.")
        st.stop()

    with st.spinner("Downloading Yahoo Finance data..."):
        data_map = cached_download((ticker, market_ticker), start_date.isoformat(), end_date.isoformat())

    if ticker not in data_map:
        st.error(f"No data found for ticker {ticker}.")
        st.stop()
    if market_ticker not in data_map:
        st.error(f"No data found for market ticker {market_ticker}.")
        st.stop()

    asset = data_map[ticker].copy().dropna()
    market = data_map[market_ticker].copy().dropna()

    common_idx = asset.index.intersection(market.index)
    asset = asset.loc[common_idx]
    market = market.loc[common_idx]
    if asset.empty:
        st.error("No overlapping dates between ticker and market data.")
        st.stop()

    asset["psar"] = parabolic_sar(asset["High"], asset["Low"], asset["Close"], start_step=start_step, step=step, max_step=max_step)
    asset["signal"] = (asset["Close"] > asset["psar"]).astype(int)

    sim_df = simulate_long_flat(
        close=asset["Close"],
        signal=asset["signal"],
        initial_cash=initial_cash,
        cost_per_trade=cost_per_trade,
    )

    buy_hold = buy_and_hold_equity(asset["Close"], initial_cash=initial_cash)
    market_equity = buy_and_hold_equity(market["Close"], initial_cash=initial_cash)
    benchmark_returns = market["Close"].pct_change().fillna(0.0)

    metrics = summarize_run(sim_df, benchmark_returns)
    metrics_df = pd.DataFrame.from_dict(metrics, orient="index", columns=["Value"])
    st.subheader("Backtest Results")
    st.dataframe(metrics_df.style.format("{:.4f}"), use_container_width=True)

    chart1 = sim_df[["equity"]].rename(columns={"equity": "Strategy"})
    st.subheader("Account value (strategy)")
    st.line_chart(chart1)

    chart2 = pd.DataFrame({"Strategy": sim_df["equity"], "Buy & Hold": buy_hold}, index=sim_df.index)
    st.subheader(f"Strategy vs Buy & Hold ({ticker})")
    st.line_chart(chart2)

    chart3 = pd.DataFrame({"Strategy": sim_df["equity"], f"Market ({market_ticker})": market_equity}, index=sim_df.index)
    st.subheader("Strategy vs Market Portfolio")
    st.line_chart(chart3)

    st.subheader("Price chart with buy/sell markers")
    base = pd.DataFrame({"Date": sim_df.index, "Close": sim_df["Close"]})
    buys = sim_df.dropna(subset=["buy_price"]).copy()
    buys["Date"] = buys.index
    sells = sim_df.dropna(subset=["sell_price"]).copy()
    sells["Date"] = sells.index

    line = alt.Chart(base).mark_line().encode(x="Date:T", y="Close:Q")
    buy_marks = (
        alt.Chart(buys)
        .mark_point(shape="triangle-up", color="green", size=90)
        .encode(x="Date:T", y="buy_price:Q", tooltip=["Date:T", "buy_price:Q"])
    )
    sell_marks = (
        alt.Chart(sells)
        .mark_point(shape="triangle-down", color="red", size=90)
        .encode(x="Date:T", y="sell_price:Q", tooltip=["Date:T", "sell_price:Q"])
    )
    st.altair_chart((line + buy_marks + sell_marks).interactive(), use_container_width=True)
else:
    st.info("Set inputs in the sidebar and click **Simulate**.")
