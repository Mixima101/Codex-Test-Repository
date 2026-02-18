from pathlib import Path

from src.strategy_store import load_strategies, save_strategies


def test_load_returns_empty_when_missing(tmp_path: Path):
    target = tmp_path / "strategies.json"
    assert load_strategies(target) == []


def test_save_and_load_round_trip(tmp_path: Path):
    target = tmp_path / "nested" / "strategies.json"
    strategies = [
        {
            "name": "AAPL PSAR",
            "ticker": "AAPL",
            "start_step": 0.02,
            "step": 0.02,
            "max_step": 0.2,
            "hard_stop_pct": None,
            "rolling_stop_pct": 0.12,
        }
    ]

    save_strategies(strategies, target)

    assert load_strategies(target) == strategies


def test_load_returns_empty_for_invalid_json(tmp_path: Path):
    target = tmp_path / "strategies.json"
    target.write_text("{not-valid-json", encoding="utf-8")
    assert load_strategies(target) == []
