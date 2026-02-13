from __future__ import annotations

import argparse

from src.optimizer import run_two_pass_sweep


def parse_int_list(s: str) -> list[int]:
    return [int(x.strip()) for x in s.split(",") if x.strip()]


def parse_float_list(s: str) -> list[float]:
    return [float(x.strip()) for x in s.split(",") if x.strip()]


def main() -> None:
    parser = argparse.ArgumentParser(description="Run two-pass walk-forward menu sweep for PSAR.")
    parser.add_argument("--ticker", default="JPM")
    parser.add_argument("--validation", default="BAC,C,MS,WFC")
    parser.add_argument("--benchmark", default="XLF")
    parser.add_argument("--oos-years", default="5,7")
    parser.add_argument("--train-days", default="504,756,1008")
    parser.add_argument("--test-days", default="42,63,126")
    parser.add_argument("--txn-cost-bps", default="2,5,10")
    parser.add_argument("--focused-grid-n", type=int, default=11)
    parser.add_argument("--top", type=int, default=10)
    args = parser.parse_args()

    results, best, detail = run_two_pass_sweep(
        ticker=args.ticker.upper(),
        validation=args.validation,
        benchmark=args.benchmark.upper(),
        oos_years_options=parse_int_list(args.oos_years),
        train_days_options=parse_int_list(args.train_days),
        test_days_options=parse_int_list(args.test_days),
        txn_cost_options=parse_float_list(args.txn_cost_bps),
        focused_grid_n=args.focused_grid_n,
    )

    print("\n=== Best configuration ===")
    for k in [
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
        "Sharpe",
        "CAGR",
        "Max Drawdown",
        "Alpha (ann)",
        "Beta",
        "Turnover",
        "score",
    ]:
        if k in best:
            print(f"{k}: {best[k]}")

    print("\n=== Copy/paste summary ===")
    print(detail["summary_text"])

    print(f"\n=== Top {args.top} rows by score ===")
    cols = [
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
    present = [c for c in cols if c in results.columns]
    print(results[present].head(args.top).to_string(index=False))


if __name__ == "__main__":
    main()
