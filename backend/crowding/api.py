"""FastAPI interface implementing the frozen CrowdLens integration contract."""
from __future__ import annotations

import os
from functools import lru_cache
from datetime import datetime
from pathlib import Path

from fastapi import FastAPI, HTTPException, Query

from .predictor import CrowdingPredictor
from .stop_matcher import GTFSStopMatcher

app = FastAPI(title="AARAM AI Crowding API", version="0.1.0")
MODEL_PATH = Path(os.getenv("AARAM_MODEL_PATH", "data/processed/crowding_profiles.json"))
GTFS_DIR = Path(os.getenv("AARAM_GTFS_DIR", "data/gtfs"))
predictor = CrowdingPredictor.load(MODEL_PATH)


@lru_cache(maxsize=1)
def _gtfs_matcher() -> GTFSStopMatcher:
    if not (GTFS_DIR / "trips.txt").exists() or not (GTFS_DIR / "stop_times.txt").exists():
        raise HTTPException(503, "GTFS is unavailable; cannot resolve trip_id")
    return GTFSStopMatcher(GTFS_DIR)


def _trip_segments(trip_id: str) -> tuple[str, str, str, list[str]]:
    pattern = _gtfs_matcher().pattern_for_trip(trip_id)
    if pattern is None:
        raise HTTPException(404, "trip_id was not found in GTFS")
    return pattern.route_id, pattern.direction_id, pattern.pattern_id, list(pattern.stop_ids)


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "model_loaded": predictor.is_loaded, "capacity_calibrated": False}


@app.get("/v1/crowding")
def crowding(trip_id: str, from_stop_id: str, to_stop_id: str, departure: datetime = Query(...)) -> dict:
    if departure.tzinfo is None:
        raise HTTPException(422, "departure must include a timezone offset")
    route_id, direction_id, pattern_id, stops = _trip_segments(trip_id)
    try:
        start, end = stops.index(from_stop_id), stops.index(to_stop_id)
    except ValueError:
        raise HTTPException(422, "from_stop_id and to_stop_id must occur on trip_id")
    if start >= end:
        raise HTTPException(422, "from_stop_id must occur before to_stop_id on trip_id")
    local = departure.astimezone().astimezone(__import__("zoneinfo").ZoneInfo("Asia/Kolkata"))
    weekday_type, band = ("weekend" if local.weekday() >= 5 else "weekday"), local.hour * 2 + local.minute // 30
    segments = []
    for index in range(start, end):
        prediction = predictor.predict(route_id, direction_id, pattern_id, index, weekday_type, band)
        segments.append({"from_stop_id": stops[index], "to_stop_id": stops[index + 1], "level": prediction.level,
                         "score": prediction.score, "evidence": prediction.evidence, "observed_days": prediction.observed_days})
    known = [item for item in segments if item["score"] is not None]
    level = max((item["level"] for item in known), key=lambda val: ("low", "medium", "high").index(val)) if known else "unknown"
    evidence = min((item["evidence"] for item in known), key=lambda val: ("high", "medium", "low", "insufficient").index(val)) if known else "insufficient"
    return {"trip_id": trip_id, "prediction_type": "relative_ticket_demand", "capacity_calibrated": False,
            "overall": {"level": level, "evidence": evidence}, "segments": segments}
