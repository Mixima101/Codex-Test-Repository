from __future__ import annotations

import datetime as dt
import json
from pathlib import Path
from uuid import uuid4

import pandas as pd

from .data import download_ohlcv

DATA_DIR = Path(__file__).resolve().parents[1] / "data"
DATASET_INDEX_PATH = DATA_DIR / "datasets.json"
DATASET_FILES_DIR = DATA_DIR / "datasets"


def load_datasets(path: Path | None = None) -> list[dict]:
    dataset_path = path or DATASET_INDEX_PATH
    if not dataset_path.exists():
        return []
    try:
        raw = json.loads(dataset_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return []
    if not isinstance(raw, list):
        return []
    return [item for item in raw if isinstance(item, dict)]


def save_datasets(datasets: list[dict], path: Path | None = None) -> None:
    dataset_path = path or DATASET_INDEX_PATH
    dataset_path.parent.mkdir(parents=True, exist_ok=True)
    dataset_path.write_text(json.dumps(datasets, indent=2), encoding="utf-8")


def _dataset_file_path(dataset_id: str, ticker: str) -> Path:
    DATASET_FILES_DIR.mkdir(parents=True, exist_ok=True)
    safe_ticker = "".join(ch for ch in ticker.upper() if ch.isalnum()) or "DATA"
    return DATASET_FILES_DIR / f"{safe_ticker}_{dataset_id}.csv"


def download_and_store_dataset(ticker: str, start_date: dt.date, end_date: dt.date) -> dict:
    ticker_clean = ticker.strip().upper()
    if not ticker_clean:
        raise ValueError("Ticker is required.")

    data_map = download_ohlcv((ticker_clean,), start=start_date.isoformat(), end=end_date.isoformat(), threads=False)
    if ticker_clean not in data_map:
        raise ValueError(f"No data found for ticker {ticker_clean}.")

    df = data_map[ticker_clean].copy().dropna()
    if df.empty:
        raise ValueError(f"No data rows returned for ticker {ticker_clean}.")

    dataset_id = uuid4().hex[:12]
    file_path = _dataset_file_path(dataset_id, ticker_clean)
    df.to_csv(file_path, index_label="Date")

    return {
        "id": dataset_id,
        "ticker": ticker_clean,
        "start_date": start_date.isoformat(),
        "end_date": end_date.isoformat(),
        "row_count": int(len(df)),
        "file": str(file_path.relative_to(DATA_DIR.parent).as_posix()),
        "created_at": dt.datetime.now().strftime("%Y-%m-%d %H:%M"),
    }


def delete_dataset(dataset: dict) -> None:
    rel = dataset.get("file")
    if not isinstance(rel, str):
        return
    file_path = DATA_DIR.parent / rel
    if file_path.exists():
        file_path.unlink()


def find_dataset(datasets: list[dict], ticker: str, start_date: dt.date, end_date: dt.date) -> dict | None:
    t = ticker.strip().upper()
    s = start_date.isoformat()
    e = end_date.isoformat()
    for item in reversed(datasets):
        if item.get("ticker") == t and item.get("start_date") == s and item.get("end_date") == e:
            return item
    return None


def load_dataset_frame(dataset: dict) -> pd.DataFrame:
    rel = dataset.get("file")
    if not isinstance(rel, str):
        raise ValueError("Dataset file path is missing.")
    file_path = DATA_DIR.parent / rel
    if not file_path.exists():
        raise ValueError(f"Dataset file is missing: {file_path}")
    df = pd.read_csv(file_path, parse_dates=["Date"], index_col="Date")
    return df.dropna().copy()
