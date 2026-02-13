from __future__ import annotations

import pandas as pd
import streamlit as st

from src.optimizer import SweepState, run_two_pass_sweep

st.set_page_config(page_title="PSAR Optimizer Dashboard", layout="wide")
st.title("PSAR Automated Optimizer (No-manual Rotation)")
st.caption("Sweeps walk-forward windows and transaction costs automatically, then runs a coarse→focused PSAR grid search.")

with st.sidebar:
    st.header("Fixed inputs")
    ticker = st.text_input("Primary ticker", value="JPM")
    validation = st.text_input("Validation tickers (comma-separated)", value="BAC,C,MS,WFC")
    benchmark = st.text_input("Benchmark ticker", value="XLF")

    st.header("Automated sweep sets")
    oos_years = st.multiselect("Out-of-sample years", options=[2, 3, 4, 5, 6, 7, 8, 9, 10], default=[5, 7])
    train_days = st.multiselect("Train days", options=[252, 378, 504, 630, 756, 882, 1008, 1260], default=[504, 756, 1008])
    test_days = st.multiselect("Test days", options=[21, 42, 63, 84, 126, 168, 252], default=[42, 63, 126])
    txn_costs = st.multiselect("Txn cost (bps)", options=[0.0, 1.0, 2.0, 5.0, 10.0, 15.0], default=[2.0, 5.0, 10.0])

    focused_grid_n = st.select_slider("Focused grid size", options=[11, 13], value=11)

    optimize_btn = st.button("Optimize tests", type="primary")

if optimize_btn:
    if not oos_years or not train_days or not test_days or not txn_costs:
        st.error("Please select at least one value for each sweep set.")
        st.stop()

    progress = st.progress(0.0, text="Preparing optimizer...")
    status = st.empty()
    live_best = st.empty()

    tracker = {"best_score": float("-inf"), "best_state": None}

    def on_progress(state: SweepState) -> None:
        pct = state.completed / state.total if state.total else 0
        progress.progress(pct, text=f"Running combinations: {state.completed}/{state.total}")
        status.info(
            f"Current combo → OOS {state.oos_years}, train {state.train_days}, test {state.test_days}, "
            f"cost {state.txn_cost_bps:.1f} bps | score {state.score:.4f}"
        )

        if state.score > tracker["best_score"]:
            tracker["best_score"] = state.score
            tracker["best_state"] = state
            live_best.json(
                {
                    "best_score_so_far": round(tracker["best_score"], 6),
                    "recommended_step": round(state.recommended_step, 6),
                    "recommended_max_step": round(state.recommended_max_step, 6),
                    "CAGR": state.metrics.get("CAGR"),
                    "Sharpe": state.metrics.get("Sharpe"),
                    "Max Drawdown": state.metrics.get("Max Drawdown"),
                    "Beta": state.metrics.get("Beta"),
                    "Turnover": state.metrics.get("Turnover"),
                }
            )

    try:
        results, best, detail = run_two_pass_sweep(
            ticker=ticker.upper(),
            validation=validation,
            benchmark=benchmark.upper(),
            oos_years_options=sorted(set(int(x) for x in oos_years)),
            train_days_options=sorted(set(int(x) for x in train_days)),
            test_days_options=sorted(set(int(x) for x in test_days)),
            txn_cost_options=sorted(set(float(x) for x in txn_costs)),
            focused_grid_n=int(focused_grid_n),
            progress_callback=on_progress,
        )
    except Exception as exc:
        st.error(f"Optimization failed: {exc}")
        st.stop()

    progress.progress(1.0, text="Optimization complete")
    st.success("Optimization complete")

    st.subheader("Best configuration")
    best_cols = [
        "oos_years",
        "train_days",
        "test_days",
        "txn_cost_bps",
        "focused_step_min",
        "focused_step_max",
        "focused_max_min",
        "focused_max_max",
        "recommended_step",
        "recommended_max_step",
        "score",
    ]
    st.dataframe(pd.DataFrame([{k: best[k] for k in best_cols if k in best}]), use_container_width=True)

    st.markdown("**Copy/paste summary**")
    st.code(detail["summary_text"], language="text")

    col1, col2 = st.columns([2, 1])
    with col1:
        st.line_chart(detail["oos_equity"], y_label="Equity", x_label="Date")
    with col2:
        st.dataframe(pd.DataFrame([detail["metrics"]]).T.rename(columns={0: "value"}))

    st.markdown("**Chosen params per fold (best configuration)**")
    st.dataframe(detail["folds"], use_container_width=True)
    st.markdown("**Typical params (median across folds)**")
    st.json(detail["typical"])
    st.markdown("**Recommended params (most stable across folds)**")
    st.json(detail["recommended"])

    st.subheader("Top tested combinations")
    leaderboard_cols = [
        "oos_years",
        "train_days",
        "test_days",
        "txn_cost_bps",
        "recommended_step",
        "recommended_max_step",
        "Sharpe",
        "CAGR",
        "Max Drawdown",
        "Alpha (ann)",
        "Beta",
        "Turnover",
        "score",
    ]
    present = [c for c in leaderboard_cols if c in results.columns]
    st.dataframe(results[present].head(20), use_container_width=True)
else:
    st.info("Configure inputs and click **Optimize tests**.")
