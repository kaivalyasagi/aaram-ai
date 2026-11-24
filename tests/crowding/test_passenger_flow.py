import pandas as pd

from backend.crowding.passenger_flow import reconstruct_segment_demand


def test_expands_multi_passenger_ticket_across_segments():
    frame = pd.DataFrame([{"route_id": "R", "direction_id": "0", "pattern_id": "P", "board_index": 0, "alight_index": 2, "passenger_count": 3, "service_date": "2026-10-01", "created_at_ist": "2026-10-01T08:15:00+05:30", "stop_ids": ["A", "B", "C"], "match_confidence": .9}])
    output = reconstruct_segment_demand(frame)
    assert output[["from_stop_id", "to_stop_id"]].values.tolist() == [["A", "B"], ["B", "C"]]
    assert output.sampled_demand.tolist() == [3.0, 3.0]


def test_rejects_reversed_ticket():
    frame = pd.DataFrame([{"route_id": "R", "direction_id": "0", "pattern_id": "P", "board_index": 2, "alight_index": 1, "passenger_count": 1, "service_date": "2026-10-01", "created_at_ist": "2026-10-01T08:15:00+05:30", "stop_ids": ["A", "B", "C"]}])
    assert reconstruct_segment_demand(frame).empty
