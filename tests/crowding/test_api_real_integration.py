"""Integration coverage for the locally supplied GTFS/profile artifacts."""
from datetime import datetime
from pathlib import Path

import pytest


ARTIFACTS = Path("data/processed/crowding_profiles.json").exists() and Path("data/gtfs/stop_times.txt").exists()


@pytest.mark.skipif(not ARTIFACTS, reason="requires local GTFS and processed crowding profile artifact")
def test_real_trip_resolves_to_supported_contract_response():
    from backend.crowding import api

    response = api.crowding(
        "1_FULL_06_05", "2", "4470", datetime.fromisoformat("2026-10-01T07:00:00+05:30")
    )
    assert response["trip_id"] == "1_FULL_06_05"
    assert response["prediction_type"] == "relative_ticket_demand"
    assert response["capacity_calibrated"] is False
    assert response["segments"][0]["from_stop_id"] == "2"
    assert response["segments"][0]["to_stop_id"] == "4470"
    assert response["segments"][0]["score"] is not None
    assert response["segments"][0]["level"] in {"low", "medium", "high"}
