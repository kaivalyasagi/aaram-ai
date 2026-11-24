# AARAM AI crowding engine

This module predicts **relative historical ticket demand**, not vehicle occupancy or seat availability. It leaves sparse or unsupported combinations as `unknown`.

## Run

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python -m backend.crowding.pipeline data/raw/October-Delhi.csv.zip --gtfs-dir data/gtfs --output-dir data/processed
uvicorn backend.crowding.api:app --reload --port 8000
```

The batch command writes `tickets_clean.parquet`, `tickets_mapped.parquet`, `segment_demand.parquet`, and `crowding_profiles.json`. The API needs `data/gtfs/{trips.txt,stop_times.txt}` and the cached profile artifact. Preprocessing cannot truthfully run until those source datasets are supplied.

For an existing cleaned dataset, avoid re-reading the ZIP:

```bash
python -m backend.crowding.pipeline --cleaned-tickets data/processed/tickets_clean.parquet --gtfs-dir data/gtfs
```

`match_resolution.parquet` retains route/stop combinations that were unmatched or ambiguous; those records are not silently assigned to a pattern.

```bash
curl 'http://localhost:8000/health'
curl -G 'http://localhost:8000/v1/crowding' --data-urlencode trip_id=TRIP_ID \
  --data-urlencode from_stop_id=STOP_A --data-urlencode to_stop_id=STOP_B \
  --data-urlencode departure='2026-11-24T18:00:00+05:30'
```
