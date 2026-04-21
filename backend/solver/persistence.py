"""Parquet persistence (spec §2.5)."""
from __future__ import annotations

from pathlib import Path

import pandas as pd

from backend.contracts import TimeStepRecord


def append_records(run_id: str, records: list[TimeStepRecord], root: Path) -> Path:
    out_dir = root / "eval" / run_id
    out_dir.mkdir(parents=True, exist_ok=True)
    df = pd.DataFrame([r.model_dump() for r in records])
    df["timestamp"] = pd.to_datetime(df["timestamp"])
    df["day"] = df["timestamp"].dt.date.astype(str)
    path = out_dir / "records.parquet"
    df.to_parquet(path, index=False)
    return path
