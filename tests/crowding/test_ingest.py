import pandas as pd

from backend.crowding.ingest import _clean


def test_naive_ticket_timestamp_is_interpreted_as_ist():
    cleaned = _clean(pd.DataFrame({"when": ["2026-10-01 08:00:00"], "passengers": [1]}), {"created_at": "when", "passenger_count": "passengers"})
    assert str(cleaned.created_at_ist.iloc[0]) == "2026-10-01 08:00:00+05:30"
