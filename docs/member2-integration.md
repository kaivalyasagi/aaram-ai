# Member 2: CrowdLens API integration

## Start the backend

Run from the repository root after `data/gtfs/` and `data/processed/crowding_profiles.json` are present:

```bash
python -m uvicorn backend.crowding.api:app --host 127.0.0.1 --port 8000
```

Check readiness:

```bash
curl http://127.0.0.1:8000/health
```

`model_loaded: true` means the cached historical profile index loaded. GTFS is indexed on the first trip query and reused afterwards.

## Request and response schema

`GET /v1/crowding` requires `trip_id`, `from_stop_id`, `to_stop_id`, and a timezone-aware ISO-8601 `departure`.

```json
{
  "trip_id": "GTFS trip ID",
  "prediction_type": "relative_ticket_demand",
  "capacity_calibrated": false,
  "overall": {"level": "low|medium|high|unknown", "evidence": "high|medium|low|insufficient"},
  "segments": [{
    "from_stop_id": "GTFS stop ID", "to_stop_id": "GTFS stop ID",
    "level": "low|medium|high|unknown", "score": 0.0,
    "evidence": "high|medium|low|insufficient", "observed_days": 0
  }]
}
```

`score` is `null` for unsupported predictions. Preserve the segment order returned by the API when rendering CrowdLens.

## Verified real example

```bash
curl -G 'http://127.0.0.1:8000/v1/crowding' \
  --data-urlencode 'trip_id=1_FULL_06_05' \
  --data-urlencode 'from_stop_id=2' \
  --data-urlencode 'to_stop_id=4470' \
  --data-urlencode 'departure=2026-10-01T07:00:00+05:30'
```

Actual response from the processed October artifacts:

```json
{
  "trip_id": "1_FULL_06_05",
  "prediction_type": "relative_ticket_demand",
  "capacity_calibrated": false,
  "overall": {"level": "medium", "evidence": "low"},
  "segments": [{
    "from_stop_id": "2", "to_stop_id": "4470", "level": "medium",
    "score": 0.4, "evidence": "low", "observed_days": 3
  }]
}
```

## UI interpretation and limitations

- Render `low`, `medium`, and `high` as relative historical ticket-demand categories only.
- Render `unknown`/`insufficient` in grey and avoid giving a comfort recommendation based on it.
- Evidence is a heuristic reliability category; `observed_days` shows the number of historical service dates supporting the selected profile.
- Never call the score an occupancy percentage, capacity percentage, passenger count, or seat guarantee. `capacity_calibrated` is currently always `false`.
- Client errors for unknown/reversed stops or a timestamp without an offset return `422`; an unknown trip returns `404`.
