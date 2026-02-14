import numpy as np
import pandas as pd

from src.walkforward import build_diagnostic_text, summarize_trade_stats


def test_summarize_trade_stats_counts_wins_and_losses():
    idx = pd.bdate_range("2024-01-01", periods=6)
    oos_bt = pd.DataFrame(
        {
            "position": [0, 1, 1, 0, 1, 0],
            "strategy_return": [0.0, 0.02, 0.03, -0.01, -0.03, -0.01],
        },
        index=idx,
    )

    stats = summarize_trade_stats(oos_bt)

    assert stats["Trades"] == 2
    assert stats["Winning Trades"] == 1
    assert stats["Losing Trades"] == 1
    assert stats["Win Rate"] == 0.5
    assert np.isclose(stats["Avg Win %"], 3.0094, atol=1e-4)
    assert np.isclose(stats["Avg Loss %"], -3.97, atol=1e-4)


def test_build_diagnostic_text_contains_sections():
    idx = pd.bdate_range("2024-01-01", periods=3)
    metrics = {"CAGR": 0.12, "Trades": 3, "Win Rate": 2 / 3}
    folds = pd.DataFrame(
        [
            {
                "fold": 1,
                "train_start": idx[0],
                "train_end": idx[1],
                "test_start": idx[1],
                "test_end": idx[2],
                "step": 0.02,
                "max_step": 0.2,
                "train_objective": 1.1,
            }
        ]
    )
    typical = {"median_step": 0.02, "median_max_step": 0.2}
    oos_bt = pd.DataFrame(
        {
            "buy_signal": [False, True, False],
            "sell_signal": [False, False, True],
        },
        index=idx,
    )

    text = build_diagnostic_text(metrics, folds, typical, oos_bt)

    assert "Diagnostic Text" in text
    assert "Strategy stats:" in text
    assert "Fold summary:" in text
    assert "Typical params:" in text
    assert "Out-of-sample diagnostics:" in text
