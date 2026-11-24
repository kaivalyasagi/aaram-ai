"""Small, explicit table I/O helpers with a CSV fallback for constrained setups."""
from __future__ import annotations

from pathlib import Path
import pandas as pd


def write_table(frame: pd.DataFrame, path: str | Path) -> Path:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        frame.to_parquet(path, index=False)
        return path
    except (ImportError, ValueError):
        fallback = path.with_suffix(".csv")
        frame.to_csv(fallback, index=False)
        return fallback


def read_table(path: str | Path) -> pd.DataFrame:
    path = Path(path)
    if path.exists():
        return pd.read_parquet(path) if path.suffix == ".parquet" else pd.read_csv(path)
    fallback = path.with_suffix(".csv")
    if fallback.exists():
        return pd.read_csv(fallback)
    raise FileNotFoundError(f"No table found at {path} (or {fallback})")
