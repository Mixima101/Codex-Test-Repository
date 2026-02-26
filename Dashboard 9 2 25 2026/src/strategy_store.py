from __future__ import annotations

import json
from pathlib import Path


DEFAULT_STRATEGY_PATH = Path(__file__).resolve().parents[1] / "data" / "strategies.json"


def load_strategies(path: Path | None = None) -> list[dict]:
    strategy_path = path or DEFAULT_STRATEGY_PATH
    if not strategy_path.exists():
        return []

    try:
        raw = json.loads(strategy_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return []

    if not isinstance(raw, list):
        return []
    return [item for item in raw if isinstance(item, dict)]


def save_strategies(strategies: list[dict], path: Path | None = None) -> None:
    strategy_path = path or DEFAULT_STRATEGY_PATH
    strategy_path.parent.mkdir(parents=True, exist_ok=True)
    strategy_path.write_text(json.dumps(strategies, indent=2), encoding="utf-8")
