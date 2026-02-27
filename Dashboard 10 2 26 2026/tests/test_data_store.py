import datetime as dt
from pathlib import Path

import pandas as pd

import src.data_store as data_store


def test_load_and_save_datasets_roundtrip(tmp_path: Path):
    index_path = tmp_path / "datasets.json"
    datasets = [{"id": "abc", "ticker": "TSLA", "start_date": "2024-01-01", "end_date": "2024-01-31"}]

    data_store.save_datasets(datasets, path=index_path)
    loaded = data_store.load_datasets(path=index_path)

    assert loaded == datasets


def test_find_dataset_exact_match():
    datasets = [
        {"id": "1", "ticker": "AAPL", "start_date": "2024-01-01", "end_date": "2024-01-31"},
        {"id": "2", "ticker": "TSLA", "start_date": "2024-02-01", "end_date": "2024-02-28"},
    ]

    found = data_store.find_dataset(datasets, "tsla", dt.date(2024, 2, 1), dt.date(2024, 2, 28))
    assert found is not None
    assert found["id"] == "2"


def test_load_dataset_frame_and_delete_dataset(tmp_path: Path, monkeypatch):
    monkeypatch.setattr(data_store, "DATA_DIR", tmp_path / "data")

    data_store.DATA_DIR.mkdir(parents=True, exist_ok=True)
    csv_path = data_store.DATA_DIR.parent / "sample.csv"

    df = pd.DataFrame(
        {
            "Date": pd.to_datetime(["2024-01-02", "2024-01-03"]),
            "Open": [1.0, 2.0],
            "High": [1.5, 2.5],
            "Low": [0.5, 1.5],
            "Close": [1.2, 2.2],
        }
    )
    df.to_csv(csv_path, index=False)

    dataset = {"file": str(csv_path.relative_to(data_store.DATA_DIR.parent).as_posix())}

    loaded = data_store.load_dataset_frame(dataset)
    assert not loaded.empty
    assert "Close" in loaded.columns

    data_store.delete_dataset(dataset)
    assert not csv_path.exists()
