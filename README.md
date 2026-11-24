# AARAM AI

**Smarter bus journeys, less crowded travel.** AARAM AI combines a Delhi GTFS journey planner with historical, segment-level ticket-demand predictions to help commuters weigh travel time against likely comfort.

## What it demonstrates

- **Passenger Flow Twin:** ticket-observed demand reconstructed across GTFS stop-to-stop segments.
- **CrowdLens:** low, medium, high, or unknown historical demand for each journey segment.
- **ComfortShift:** compares scheduled departures while retaining evidence quality.
- **Evidence Meter:** exposes the amount and quality of historical support rather than overstating certainty.

Scores are relative historical ticket demand. They are **not** bus occupancy, capacity utilization, seat availability, or a seat guarantee.

## Quick start

Python 3.11+ is recommended. GTFS files belong in `data/gtfs/`; large ticket archives and generated model artifacts are intentionally ignored by Git.

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Build the Member 2 timetable database once.
python routing/build_gtfs_db.py

# Terminal 1: Member 1 crowding API.
python -m uvicorn backend.crowding.api:app --host 127.0.0.1 --port 8000

# Terminal 2: Member 2 journey planner.
python -m uvicorn routing.app:app --host 127.0.0.1 --port 8001

# Terminal 3: frontend.
cd frontend && npm ci && npm run dev
```

The crowding API requires `data/processed/crowding_profiles.json`, created from the documented batch pipeline. See [backend/crowding/README.md](backend/crowding/README.md) and [docs/member2-integration.md](docs/member2-integration.md).

## Evidence and validation

The chronological validation uses October 1–21 for training and October 22–31 for evaluation. It evaluates sampled ticket demand only; it does not validate physical occupancy. See [docs/crowding-validation.md](docs/crowding-validation.md) and [docs/crowding-validation.json](docs/crowding-validation.json).

## Repository layout

```text
backend/crowding/   Member 1: ingestion, GTFS matching, profiles, API, validation
routing/            Member 2: GTFS database and journey planning
frontend/           Member 2: React CrowdLens and ComfortShift interface
contracts/          Frozen frontend/backend API contract
docs/               Methodology, validation, and integration guide
tests/crowding/     Backend unit and integration coverage
```
