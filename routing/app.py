
import os
from datetime import date

from fastapi import FastAPI, Query, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from routing.journey_finder import JourneyFinder
from routing.comfort_shift import (
    compare_departures,
    time_to_seconds
)
from routing.crowd_client import get_crowding_batch


# ---------------------------------------
# Initialize FastAPI
# ---------------------------------------
app = FastAPI(
    title="AARAM AI Journey Planner",
    description="Delhi Bus Crowdedness-Aware Journey Planner",
    version="1.0.0"
)


# ---------------------------------------
# Allow the local Vite app and the configured deployed frontend to connect.
# Set ALLOWED_ORIGINS to a comma-separated list in the journey API host.
# ---------------------------------------
ALLOWED_ORIGINS = [
    origin.strip()
    for origin in os.getenv(
        "ALLOWED_ORIGINS",
        "http://localhost:5173,http://127.0.0.1:5173",
    ).split(",")
    if origin.strip()
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_methods=["GET"],
    allow_headers=["*"],
)


# ---------------------------------------
# Initialize Journey Finder
# ---------------------------------------
finder = JourneyFinder()


# ---------------------------------------
# Home API
# ---------------------------------------
@app.get("/")
def home():
    return {
        "project": "AARAM AI",
        "module": "Journey Planner",
        "status": "running"
    }


# ---------------------------------------
# Health Check API
# ---------------------------------------
@app.get("/health")
def health():
    return {
        "status": "ok"
    }


# ---------------------------------------
# Search Delhi Bus Stops
# ---------------------------------------
@app.get("/v1/stops")
def search_stops(
    query: str = Query(..., min_length=1)
):
    return {
        "query": query,
        "stops": finder.search_stops(query)
    }


# ---------------------------------------
# Journey Planner with Crowd Predictions
# ---------------------------------------
@app.get("/v1/journeys")
def get_journeys(
    from_stop_id: str,
    to_stop_id: str,
    departure_time: str = "08:00",
    travel_date: date | None = None
):
    selected_date = (
        travel_date or date.today()
    ).isoformat()

    try:
        # Step 1: Find scheduled bus journeys
        journeys = finder.find_journeys(
            from_stop_id.strip(),
            to_stop_id.strip(),
            departure_time.strip(),
            selected_date
        )

        # Step 2: Calculate requested departure time
        requested_seconds = time_to_seconds(
            departure_time.strip()
        )

        # Step 3: Get crowd predictions concurrently
        # Maximum 4 requests at a time, as configured
        # in routing/crowd_client.py.
        crowd_results = get_crowding_batch(
            journeys=journeys,
            from_stop_id=from_stop_id.strip(),
            to_stop_id=to_stop_id.strip(),
            travel_date=selected_date
        )

        # Step 4: Attach predictions to each bus
        # zip() preserves the journey/prediction order.
        for journey, result in zip(
            journeys,
            crowd_results
        ):
            journey["crowding"] = result["prediction"]
            journey["crowding_status"] = result["status"]

            # Calculate waiting time
            bus_seconds = time_to_seconds(
                journey["departure"]
            )

            journey["waiting_minutes"] = round(
                max(
                    0,
                    bus_seconds - requested_seconds
                ) / 60,
                1
            )

            # Calculate total elapsed journey time
            journey["total_minutes"] = round(
                journey["waiting_minutes"]
                + journey["duration_minutes"],
                1
            )

        # Step 5: Build ComfortShift alternatives
        # using predictions already fetched above.
        alternatives = compare_departures(
            journeys,
            departure_time.strip()
        )

    except ValueError as error:
        raise HTTPException(
            status_code=400,
            detail=str(error)
        )

    # Step 6: Return journeys and ComfortShift
    # in a single frontend API response.
    return {
        "from_stop_id": from_stop_id.strip(),
        "to_stop_id": to_stop_id.strip(),
        "departure_time": departure_time.strip(),
        "travel_date": selected_date,
        "journeys": journeys,
        "total_results": len(journeys),
        "alternatives": alternatives,
        "crowd_data_available": any(
            bus.get("crowding_status") == "available"
            for bus in alternatives
        ),
        "source": "Static Delhi GTFS timetable",
        "prediction_source": (
            "Historical relative ticket demand"
        ),
        "realtime_tracking": False
    }


# ---------------------------------------
# ComfortShift API
# ---------------------------------------
@app.get("/v1/comfort-shift")
def comfort_shift(
    from_stop_id: str,
    to_stop_id: str,
    departure_time: str = "08:00",
    travel_date: date | None = None
):
    # Reuse the optimized journey planner.
    # Predictions are fetched concurrently.
    journey_response = get_journeys(
        from_stop_id=from_stop_id,
        to_stop_id=to_stop_id,
        departure_time=departure_time,
        travel_date=travel_date
    )

    alternatives = journey_response["alternatives"]

    return {
        "feature": "ComfortShift",
        "travel_date": journey_response["travel_date"],
        "alternatives": alternatives,
        "total_results": len(alternatives),
        "crowd_data_available": (
            journey_response["crowd_data_available"]
        ),
        "note": (
            "Historical relative ticket-demand predictions. "
            "Comfort recommendations require sufficiently "
            "reliable and comparable evidence."
        )
    }
