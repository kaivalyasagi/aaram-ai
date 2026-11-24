import pandas as pd

from backend.crowding.validation import validate


def test_chronological_validation_uses_training_medians_on_same_scale():
    rows = []
    for date, demand in [("2026-10-01", 2.0), ("2026-10-08", 4.0), ("2026-10-22", 5.0)]:
        rows.append({"route_id": "R", "direction_id": "0", "pattern_id": "P", "segment_index": 0,
                     "weekday_type": "weekday", "time_band": 16, "service_date": date,
                     "sampled_demand": demand, "match_confidence": 1.0})
    result = validate(pd.DataFrame(rows), "2026-10-22")
    assert result["model"]["coverage"] == 1.0
    assert result["model"]["mae"] == 2.0  # held out 5 minus training median 3
    assert result["fair_time_aware_vs_baseline"]["time_aware_mae"] == 2.0
    assert result["unit"].startswith("daily sampled")
