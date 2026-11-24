import pandas as pd

from backend.crowding.predictor import CrowdingPredictor


def _segments(days=4):
    return pd.DataFrame([{"route_id": "R", "direction_id": "0", "pattern_id": "P", "segment_index": 0, "weekday_type": "weekday", "time_band": 16, "service_date": f"2026-10-{day:02d}", "sampled_demand": 10, "match_confidence": .95} for day in range(1, days + 1)])


def test_sparse_data_returns_unknown():
    prediction = CrowdingPredictor.fit(_segments(1)).predict("R", "0", "P", 0, "weekday", 16)
    assert prediction.level == "unknown" and prediction.score is None


def test_supported_data_has_relative_score():
    prediction = CrowdingPredictor.fit(_segments()).predict("R", "0", "P", 0, "weekday", 16)
    assert prediction.level in {"low", "medium", "high"}
    assert 0 <= prediction.score <= 1
