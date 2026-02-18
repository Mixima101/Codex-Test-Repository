from __future__ import annotations

import datetime as dt
import altair as alt
import pandas as pd
import streamlit as st

from src.data import download_ohlcv
from src.psar import parabolic_sar
from src.simulator import buy_and_hold_equity, simulate_long_flat, summarize_run

APP_NAME = "QuantumLeap Institutional Console"

SIM_DEFAULTS = {
    "sim_ticker": "AAPL",
    "sim_market_ticker": "SPY",
    "sim_start_date": dt.date.today() - dt.timedelta(days=365 * 5),
    "sim_end_date": dt.date.today(),
    "sim_start_step": "0.02",
    "sim_step": "0.02",
    "sim_max_step": "0.2",
    "sim_cost_per_trade": "1.0",
    "sim_initial_cash": "10000.0",
    "sim_hard_enabled": False,
    "sim_hard_pct": "8",
    "sim_rolling_enabled": False,
    "sim_rolling_pct": "12",
}

STRATEGY_DEFAULTS = {
    "add_name": "",
    "add_ticker": "AAPL",
    "add_start_step": "0.02",
    "add_step": "0.02",
    "add_max_step": "0.2",
    "add_hard_enabled": False,
    "add_hard_pct": "8",
    "add_rolling_enabled": False,
    "add_rolling_pct": "12",
}

st.set_page_config(page_title=APP_NAME, layout="wide")
st.markdown(
    f"""
    <style>
      .quantum-brand {{
          position: fixed;
          top: 0.75rem;
          right: 1rem;
          z-index: 9999;
          font-weight: 700;
          letter-spacing: 0.06em;
          color: #0A2342;
          background: rgba(255,255,255,0.9);
          padding: 0.35rem 0.6rem;
          border-radius: 0.35rem;
          border: 1px solid #D0D7DE;
      }}
    </style>
    <div class="quantum-brand">{APP_NAME}</div>
    """,
    unsafe_allow_html=True,
)


def parse_float_input(raw: str, label: str) -> float:
    text = raw.strip().replace(",", "")
    try:
        return float(text)
    except ValueError as exc:
        raise ValueError(f"{label} must be a valid number.") from exc


def parse_optional_pct(raw: str, label: str, enabled: bool) -> float | None:
    if not enabled:
        return None
    value = parse_float_input(raw, label)
    if value <= 0 or value >= 100:
        raise ValueError(f"{label} must be between 0 and 100.")
    return value / 100.0


@st.cache_data(show_spinner=False)
def cached_download(ticker_list: tuple[str, ...], start: str, end: str):
    return download_ohlcv(ticker_list, start=start, end=end, threads=False)


def ensure_state() -> None:
    if "strategies" not in st.session_state:
        st.session_state.strategies = []
    for key, value in SIM_DEFAULTS.items():
        if key not in st.session_state:
            st.session_state[key] = value
    for key, value in STRATEGY_DEFAULTS.items():
        if key not in st.session_state:
            st.session_state[key] = value


def reset_fields(defaults: dict[str, object]) -> None:
    for key, value in defaults.items():
        st.session_state[key] = value


def build_signal_df(
    ticker: str,
    market_ticker: str,
    start_date: dt.date,
    end_date: dt.date,
    start_step: float,
    step: float,
    max_step: float,
    initial_cash: float,
    cost_per_trade: float,
    hard_stop_pct: float | None,
    trailing_stop_pct: float | None,
):
    data_map = cached_download((ticker, market_ticker), start_date.isoformat(), end_date.isoformat())
    if ticker not in data_map:
        raise ValueError(f"No data found for ticker {ticker}.")
    if market_ticker not in data_map:
        raise ValueError(f"No data found for market ticker {market_ticker}.")

    asset = data_map[ticker].copy().dropna()
    market = data_map[market_ticker].copy().dropna()

    common_idx = asset.index.intersection(market.index)
    asset = asset.loc[common_idx]
    market = market.loc[common_idx]
    if asset.empty:
        raise ValueError("No overlapping dates between ticker and market data.")

    asset["psar"] = parabolic_sar(
        asset["High"], asset["Low"], asset["Close"], start_step=start_step, step=step, max_step=max_step
    )
    asset["signal"] = (asset["Close"] > asset["psar"]).astype(int)

    sim_df = simulate_long_flat(
        close=asset["Close"],
        signal=asset["signal"],
        initial_cash=initial_cash,
        cost_per_trade=cost_per_trade,
        hard_stop_pct=hard_stop_pct,
        trailing_stop_pct=trailing_stop_pct,
    )
    return sim_df, market


def validate_common(start_step: float, step: float, max_step: float, cost_per_trade: float, initial_cash: float):
    if start_step <= 0 or step <= 0 or max_step <= 0:
        raise ValueError("PSAR start step, step, and max step must all be greater than 0.")
    if start_step > max_step:
        raise ValueError("PSAR start step must be less than or equal to max step.")
    if step > max_step:
        raise ValueError("PSAR step must be less than or equal to max step.")
    if cost_per_trade < 0:
        raise ValueError("Cost per trade cannot be negative.")
    if initial_cash <= 0:
        raise ValueError("Starting account value must be greater than 0.")


def render_simulation():
    st.title("Simulation Lab")
    st.caption("Run PSAR backtests with optional hard-stop and rolling-stop controls.")

    with st.form("sim_form"):
        col1, col2, col3 = st.columns(3)
        with col1:
            ticker = st.text_input("Ticker", key="sim_ticker").strip().upper()
            market_ticker = st.text_input("Market portfolio ticker", key="sim_market_ticker").strip().upper()
            start_date = st.date_input("Begin date", key="sim_start_date")
            end_date = st.date_input("End date", key="sim_end_date")
        with col2:
            start_step_text = st.text_input("PSAR start step", key="sim_start_step")
            step_text = st.text_input("PSAR step", key="sim_step")
            max_step_text = st.text_input("PSAR max step", key="sim_max_step")
        with col3:
            cost_per_trade_text = st.text_input("Cost per trade ($)", key="sim_cost_per_trade")
            initial_cash_text = st.text_input("Starting account value ($)", key="sim_initial_cash")

        c1, c2 = st.columns(2)
        with c1:
            hard_enabled = st.checkbox("Hard Stop", key="sim_hard_enabled")
            hard_text = st.text_input("Hard stop %", key="sim_hard_pct", help="Enter value anytime; checkbox controls activation.")
        with c2:
            rolling_enabled = st.checkbox("Rolling Stop", key="sim_rolling_enabled")
            rolling_text = st.text_input("Rolling stop %", key="sim_rolling_pct", help="Enter value anytime; checkbox controls activation.")

        simulate_btn = st.form_submit_button("Run Simulation", type="primary")

    if st.button("Clear fields", key="sim_clear_fields"):
        reset_fields(SIM_DEFAULTS)
        st.rerun()

    if not simulate_btn:
        st.info("Configure settings and run a simulation.")
        return

    if start_date >= end_date:
        st.error("Begin date must be before end date.")
        return

    try:
        start_step = parse_float_input(start_step_text, "PSAR start step")
        step = parse_float_input(step_text, "PSAR step")
        max_step = parse_float_input(max_step_text, "PSAR max step")
        cost_per_trade = parse_float_input(cost_per_trade_text, "Cost per trade")
        initial_cash = parse_float_input(initial_cash_text, "Starting account value")
        hard_stop_pct = parse_optional_pct(hard_text, "Hard stop %", hard_enabled)
        rolling_stop_pct = parse_optional_pct(rolling_text, "Rolling stop %", rolling_enabled)
        validate_common(start_step, step, max_step, cost_per_trade, initial_cash)
    except ValueError as exc:
        st.error(str(exc))
        return

    with st.spinner("Downloading Yahoo Finance data..."):
        try:
            sim_df, market = build_signal_df(
                ticker,
                market_ticker,
                start_date,
                end_date,
                start_step,
                step,
                max_step,
                initial_cash,
                cost_per_trade,
                hard_stop_pct,
                rolling_stop_pct,
            )
        except ValueError as exc:
            st.error(str(exc))
            return

    buy_hold = buy_and_hold_equity(sim_df["Close"], initial_cash=initial_cash)
    market_equity = buy_and_hold_equity(market["Close"], initial_cash=initial_cash)
    metrics = summarize_run(sim_df, market["Close"].pct_change().fillna(0.0))
    st.subheader("Backtest Results")
    st.dataframe(pd.DataFrame.from_dict(metrics, orient="index", columns=["Value"]).style.format("{:.4f}"), use_container_width=True)

    st.subheader("Account value (strategy)")
    st.line_chart(sim_df[["equity"]].rename(columns={"equity": "Strategy"}))

    st.subheader(f"Strategy vs Buy & Hold ({ticker})")
    st.line_chart(pd.DataFrame({"Strategy": sim_df["equity"], "Buy & Hold": buy_hold}, index=sim_df.index))

    st.subheader("Strategy vs Market Portfolio")
    st.line_chart(pd.DataFrame({"Strategy": sim_df["equity"], f"Market ({market_ticker})": market_equity}, index=sim_df.index))

    st.subheader("Price chart with buy/sell markers")
    base = pd.DataFrame({"Date": sim_df.index, "Close": sim_df["Close"]})
    buys = sim_df.dropna(subset=["buy_price"]).copy()
    buys["Date"] = buys.index
    sells = sim_df.dropna(subset=["sell_price"]).copy()
    sells["Date"] = sells.index

    line = alt.Chart(base).mark_line().encode(x="Date:T", y="Close:Q")
    buy_marks = alt.Chart(buys).mark_point(shape="triangle-up", color="green", size=90).encode(x="Date:T", y="buy_price:Q")
    sell_marks = alt.Chart(sells).mark_point(shape="triangle-down", color="red", size=90).encode(x="Date:T", y="sell_price:Q")
    st.altair_chart((line + buy_marks + sell_marks).interactive(), use_container_width=True)


def render_add_strategy():
    st.title("Add Strategy")
    st.caption("Create stock-specific PSAR strategies for live dashboard monitoring.")

    with st.form("strategy_form"):
        c1, c2, c3 = st.columns(3)
        with c1:
            name = st.text_input("Strategy name", placeholder="AAPL Trend Core", key="add_name")
            ticker = st.text_input("Ticker", key="add_ticker").strip().upper()
        with c2:
            start_step = st.text_input("PSAR start step", key="add_start_step")
            step = st.text_input("PSAR step", key="add_step")
            max_step = st.text_input("PSAR max step", key="add_max_step")
        with c3:
            hard_enabled = st.checkbox("Hard Stop", key="add_hard_enabled")
            hard_pct = st.text_input("Hard stop %", key="add_hard_pct", help="Enter value anytime; checkbox controls activation.")
            rolling_enabled = st.checkbox("Rolling Stop", key="add_rolling_enabled")
            rolling_pct = st.text_input("Rolling stop %", key="add_rolling_pct", help="Enter value anytime; checkbox controls activation.")

        submitted = st.form_submit_button("Save", type="primary")

    if st.button("Clear fields", key="add_clear_fields"):
        reset_fields(STRATEGY_DEFAULTS)
        st.rerun()

    if submitted:
        try:
            start_step_f = parse_float_input(start_step, "PSAR start step")
            step_f = parse_float_input(step, "PSAR step")
            max_step_f = parse_float_input(max_step, "PSAR max step")
            validate_common(start_step_f, step_f, max_step_f, 0.0, 1.0)
            hard_val = parse_optional_pct(hard_pct, "Hard stop %", hard_enabled)
            rolling_val = parse_optional_pct(rolling_pct, "Rolling stop %", rolling_enabled)
            strategy_name = name.strip() or f"{ticker} PSAR"
            st.session_state.strategies.append(
                {
                    "name": strategy_name,
                    "ticker": ticker,
                    "start_step": start_step_f,
                    "step": step_f,
                    "max_step": max_step_f,
                    "hard_stop_pct": hard_val,
                    "rolling_stop_pct": rolling_val,
                    "created_at": dt.datetime.now().strftime("%Y-%m-%d %H:%M"),
                }
            )
            st.success(f"Saved strategy: {strategy_name}")
        except ValueError as exc:
            st.error(str(exc))


def strategy_decision(strategy: dict) -> tuple[str, str, str]:
    end = dt.date.today()
    start = end - dt.timedelta(days=365)
    try:
        sim_df, _ = build_signal_df(
            strategy["ticker"],
            "SPY",
            start,
            end,
            strategy["start_step"],
            strategy["step"],
            strategy["max_step"],
            initial_cash=10_000,
            cost_per_trade=0.0,
            hard_stop_pct=strategy["hard_stop_pct"],
            trailing_stop_pct=strategy["rolling_stop_pct"],
        )
    except Exception:
        return "No Data", "gray", "Unable to load quote history"

    latest = int(sim_df["position"].iloc[-1])
    label = "BUY" if latest == 1 else "SELL"
    color = "#0A7D34" if latest == 1 else "#BA1A1A"
    detail = f"Last close: ${sim_df['Close'].iloc[-1]:.2f}"
    return label, color, detail


def render_dashboard():
    st.title("Strategy Dashboard")
    if not st.session_state.strategies:
        st.info("No saved strategies yet. Use 'Add Strategy' to create one.")
        return

    for strat in st.session_state.strategies:
        signal, color, detail = strategy_decision(strat)
        left, right = st.columns([4, 1])
        with left:
            stops = []
            if strat["hard_stop_pct"] is not None:
                stops.append(f"Hard {strat['hard_stop_pct'] * 100:.1f}%")
            if strat["rolling_stop_pct"] is not None:
                stops.append(f"Rolling {strat['rolling_stop_pct'] * 100:.1f}%")
            stop_text = " | ".join(stops) if stops else "No stops"
            st.markdown(f"**{strat['name']}** ({strat['ticker']})  ")
            st.caption(
                f"PSAR: start={strat['start_step']}, step={strat['step']}, max={strat['max_step']} • {stop_text} • {detail}"
            )
        with right:
            st.markdown(
                f"<div style='background:{color};padding:0.6rem;border-radius:0.4rem;color:white;text-align:center;font-weight:700'>{signal}</div>",
                unsafe_allow_html=True,
            )


ensure_state()
with st.sidebar:
    st.header("☰ Navigation")
    section = st.radio("Go to", ["Dashboard", "Add Strategy", "Simulation"], label_visibility="collapsed")

if section == "Simulation":
    render_simulation()
elif section == "Add Strategy":
    render_add_strategy()
else:
    render_dashboard()
