"""Reproducible ingestion and factual quality profiling for ticket extracts."""
from __future__ import annotations

import argparse
import json
import re
import zipfile
from pathlib import Path
from typing import Any

import pandas as pd

from .storage import write_table

CANONICAL_COLUMNS = {
    "passenger_count": ("passenger_count", "passengers", "passenger", "qty", "quantity"),
    "route": ("route", "route_id", "route_name", "routeno", "route_no"),
    "start_stop_name": ("start_stop_name", "start_stop", "boarding_stop", "from_stop", "source_stop"),
    "end_stop_name": ("end_stop_name", "end_stop", "alighting_stop", "to_stop", "destination_stop"),
    "vehicle_number": ("vehicle_number", "vehicle_no", "vehicle", "bus_number", "bus_no"),
    "created_at": ("created_at", "timestamp", "ticket_time", "createdon", "date_time"),
    "amount": ("amount", "fare", "ticket_amount"),
    "ticket_type_id": ("ticket_type_id", "ticket_type", "tickettype"),
    "is_ac": ("is_ac", "ac", "isac"),
}


def _key(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", str(value).lower()).strip("_")


def _aliases(columns: list[str]) -> dict[str, str]:
    indexed = {_key(column): column for column in columns}
    return {target: indexed[alias] for target, aliases in CANONICAL_COLUMNS.items()
            for alias in aliases if alias in indexed}


def inspect_source(source: str | Path) -> dict[str, Any]:
    """Return archive/CSV headers without making claims about unseen data."""
    source = Path(source)
    if not source.exists():
        raise FileNotFoundError(source)
    if source.suffix == ".zip":
        with zipfile.ZipFile(source) as archive:
            members = [name for name in archive.namelist() if name.lower().endswith(".csv") and not name.startswith("__MACOSX/")]
            if len(members) != 1:
                raise ValueError(f"Expected one CSV member in {source}; found {members}")
            with archive.open(members[0]) as member:
                header = pd.read_csv(member, nrows=0)
    else:
        header = pd.read_csv(source, nrows=0)
    return {"source": str(source), "columns": header.columns.tolist(),
            "recognized_columns": _aliases(header.columns.tolist()), "rows_profiled": 0}


def _clean(raw: pd.DataFrame, source_map: dict[str, str]) -> pd.DataFrame:
    result = pd.DataFrame(index=raw.index)
    for canonical, source in source_map.items():
        result[canonical] = raw[source]
    for column in CANONICAL_COLUMNS:
        if column not in result:
            result[column] = pd.NA
    for column in ("route", "start_stop_name", "end_stop_name", "vehicle_number"):
        result[column] = result[column].astype("string").str.strip().replace("", pd.NA)
    result["passenger_count"] = pd.to_numeric(result["passenger_count"], errors="coerce")
    timestamp_text = result["created_at"].astype("string")
    has_offset = timestamp_text.str.contains(r"(?:Z|[+-]\d{2}:?\d{2})$", case=False, na=False, regex=True)
    parsed = pd.Series(pd.NaT, index=result.index, dtype="datetime64[ns, UTC]")
    # Challenge exports commonly use naïve local transaction timestamps.  Interpret
    # only those as IST; offset-bearing values retain their stated offset.
    if has_offset.any():
        parsed.loc[has_offset] = pd.to_datetime(timestamp_text.loc[has_offset], errors="coerce", utc=True, format="mixed")
    if (~has_offset).any():
        naive = pd.to_datetime(timestamp_text.loc[~has_offset], errors="coerce", format="mixed")
        parsed.loc[~has_offset] = naive.dt.tz_localize("Asia/Kolkata", ambiguous="NaT", nonexistent="NaT").dt.tz_convert("UTC")
    result["created_at"] = parsed
    result["created_at_ist"] = result["created_at"].dt.tz_convert("Asia/Kolkata")
    result["service_date"] = result["created_at_ist"].dt.date.astype("string")
    result["source_row_valid"] = (result["passenger_count"].gt(0) & result["created_at"].notna()).fillna(False)
    return result


def ingest(source: str | Path, output_dir: str | Path, chunksize: int = 200_000) -> dict[str, Any]:
    source, output_dir = Path(source), Path(output_dir)
    inspection = inspect_source(source)
    chunks, total = [], 0
    if source.suffix == ".zip":
        archive = zipfile.ZipFile(source)
        members = [name for name in archive.namelist() if name.lower().endswith(".csv") and not name.startswith("__MACOSX/")]
        handle = archive.open(members[0])
    else:
        archive, handle = None, source
    try:
        for raw in pd.read_csv(handle, chunksize=chunksize, on_bad_lines="warn", low_memory=False):
            total += len(raw)
            chunks.append(_clean(raw, inspection["recognized_columns"]))
    finally:
        if archive is not None:
            handle.close()
            archive.close()
    cleaned = pd.concat(chunks, ignore_index=True) if chunks else pd.DataFrame(columns=CANONICAL_COLUMNS)
    valid = cleaned[cleaned["source_row_valid"]].copy()
    time_band = cleaned["created_at_ist"].dt.hour.mul(2).add(cleaned["created_at_ist"].dt.minute.floordiv(30))
    quality: dict[str, Any] = {
        **inspection, "total_rows": int(total), "valid_rows": int(len(valid)),
        "missing_route_ids": int(cleaned["route"].isna().sum()),
        "missing_stop_names": int((cleaned["start_stop_name"].isna() | cleaned["end_stop_name"].isna()).sum()),
        "missing_vehicle_numbers": int(cleaned["vehicle_number"].isna().sum()),
        "invalid_passenger_counts": int((cleaned["passenger_count"].isna() | cleaned["passenger_count"].le(0)).sum()),
        "distinct_routes": int(cleaned["route"].nunique()), "distinct_dates": int(cleaned["service_date"].nunique()),
        "date_range": [str(cleaned["service_date"].min()), str(cleaned["service_date"].max())],
        "tickets_by_weekday": cleaned["created_at_ist"].dt.day_name().value_counts().to_dict(),
        "tickets_by_time_band": time_band.value_counts().sort_index().astype(int).to_dict(),
    }
    table_path = write_table(cleaned, output_dir / "tickets_clean.parquet")
    report_path = output_dir / "ticket_quality_report.json"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(quality, indent=2, default=str))
    return {"table": str(table_path), "report": str(report_path), "quality": quality}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source")
    parser.add_argument("--output-dir", default="data/processed")
    args = parser.parse_args()
    print(json.dumps(ingest(args.source, args.output_dir), indent=2, default=str))


if __name__ == "__main__":
    main()
