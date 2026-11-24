"""Efficient segment-level reconstruction of observed sampled ticket demand."""
from __future__ import annotations

import numpy as np
import pandas as pd


def reconstruct_segment_demand(mapped: pd.DataFrame, pattern_segments: dict[str, tuple[str, ...]] | None = None) -> pd.DataFrame:
    """Aggregate OD events before expanding them over segments.

    `pattern_segments` stays separate from ticket rows, so each matched ticket
    does not carry a duplicate list of stop IDs.
    """
    required = {"route_id", "direction_id", "pattern_id", "board_index", "alight_index", "passenger_count", "service_date", "created_at_ist"}
    missing = required - set(mapped.columns)
    if missing:
        raise ValueError(f"mapped ticket table missing columns: {sorted(missing)}")
    columns = ["route_id", "direction_id", "pattern_id", "segment_index", "from_stop_id", "to_stop_id", "service_date", "weekday_type", "time_band", "sampled_demand", "match_confidence"]
    if mapped.empty:
        return pd.DataFrame(columns=columns)
    working = mapped.copy()
    working["board_index"] = pd.to_numeric(working.board_index, errors="coerce")
    working["alight_index"] = pd.to_numeric(working.alight_index, errors="coerce")
    working["passenger_count"] = pd.to_numeric(working.passenger_count, errors="coerce")
    working = working[(working.board_index < working.alight_index) & (working.passenger_count > 0)].copy()
    if working.empty:
        return pd.DataFrame(columns=columns)
    if "match_confidence" not in working:
        working["match_confidence"] = 0.0
    timestamps = pd.to_datetime(working.created_at_ist)
    working["weekday_type"] = np.where(timestamps.dt.weekday >= 5, "weekend", "weekday")
    working["time_band"] = timestamps.dt.hour * 2 + timestamps.dt.minute // 30
    if pattern_segments is None:
        if "stop_ids" not in working:
            raise ValueError("pattern_segments is required unless mapped rows contain stop_ids")
        pattern_segments = {str(row.pattern_id): tuple(row.stop_ids) for row in working.itertuples(index=False)}
    group_columns = ["route_id", "direction_id", "pattern_id", "service_date", "weekday_type", "time_band"]
    od = working.groupby(group_columns + ["board_index", "alight_index"], as_index=False, sort=False).agg(passenger_count=("passenger_count", "sum"), match_confidence=("match_confidence", "mean"))
    rows: list[dict] = []
    for key, group in od.groupby(group_columns, sort=False):
        route_id, direction_id, pattern_id, service_date, weekday_type, time_band = key
        stops = pattern_segments.get(str(pattern_id))
        if not stops:
            continue
        deltas = np.zeros(len(stops), dtype=float)
        np.add.at(deltas, group.board_index.to_numpy(dtype=int), group.passenger_count.to_numpy(dtype=float))
        np.add.at(deltas, group.alight_index.to_numpy(dtype=int), -group.passenger_count.to_numpy(dtype=float))
        loads = np.cumsum(deltas)[:-1]
        confidence = float(np.average(group.match_confidence, weights=group.passenger_count))
        for index in np.flatnonzero(loads > 0):
            rows.append({"route_id": str(route_id), "direction_id": str(direction_id), "pattern_id": str(pattern_id), "segment_index": int(index), "from_stop_id": stops[index], "to_stop_id": stops[index + 1], "service_date": str(service_date), "weekday_type": weekday_type, "time_band": int(time_band), "sampled_demand": float(loads[index]), "match_confidence": confidence})
    return pd.DataFrame(rows, columns=columns)
