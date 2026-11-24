# CrowdLens API contract (v1)

Base URL: `http://localhost:8000`.

`GET /health` returns service and artifact state. `GET /v1/crowding` takes required query parameters `trip_id`, `from_stop_id`, `to_stop_id`, and timezone-aware ISO-8601 `departure`.

```json
{
  "trip_id": "GTFS_TRIP_ID",
  "prediction_type": "relative_ticket_demand",
  "capacity_calibrated": false,
  "overall": {"level": "high", "evidence": "medium"},
  "segments": [{
    "from_stop_id": "STOP_A", "to_stop_id": "STOP_B", "level": "high",
    "score": 0.82, "evidence": "medium", "observed_days": 7
  }]
}
```

`level` is one of `low`, `medium`, `high`, `unknown`; `evidence` is one of `high`, `medium`, `low`, `insufficient`. `score` is in `[0,1]` or `null` and means a relative historical ticket-demand score, **never occupancy percent**. `capacity_calibrated` is always `false` unless a separately verified calibration is integrated.

The API returns `422` for malformed input, stops absent from the trip, reversed stop ordering, or a timestamp without an offset; `404` for an unknown trip; and `503` when GTFS is not yet installed. Unsupported demand predictions return a successful response with `unknown` / `insufficient` fields so clients can render grey CrowdLens segments.
