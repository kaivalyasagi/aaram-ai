from datetime import datetime, timezone

from backend.crowding import api
from backend.crowding.predictor import CrowdingPredictor


def test_requires_timezone(monkeypatch):
    try:
        api.crowding("T", "A", "B", datetime(2026, 1, 1, 8, 0))
    except Exception as exc:
        assert getattr(exc, "status_code", None) == 422
    else:
        raise AssertionError("naive timestamps must be rejected")


def test_unknown_profiles_are_contract_safe(monkeypatch):
    monkeypatch.setattr(api, "_trip_segments", lambda _trip: ("R", "0", "P", ["A", "B"]))
    monkeypatch.setattr(api, "predictor", CrowdingPredictor())
    response = api.crowding("T", "A", "B", datetime(2026, 1, 1, 8, 0, tzinfo=timezone.utc))
    assert response["capacity_calibrated"] is False
    assert response["segments"][0]["score"] is None
