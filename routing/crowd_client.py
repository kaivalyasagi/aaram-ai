
import os
from concurrent.futures import ThreadPoolExecutor
from datetime import date, datetime, timedelta, timezone

import httpx


# Member 1's Crowd Intelligence API
CROWD_API_URL = os.getenv(
    "CROWD_API_BASE_URL",
    "http://127.0.0.1:8000"
).rstrip("/")

# Limit simultaneous API requests
MAX_CROWD_WORKERS = 4

# Indian Standard Time
IST = timezone(timedelta(hours=5, minutes=30))


def build_crowd_params(
    trip_id,
    from_stop_id,
    to_stop_id,
    departure_time,
    travel_date
):
    """
    Create request parameters for Member 1's API.

    Handles GTFS times greater than 23:59:59.
    """

    hours, minutes, seconds = map(
        int,
        departure_time.split(":")
    )

    if (
        hours < 0
        or not 0 <= minutes <= 59
        or not 0 <= seconds <= 59
    ):
        raise ValueError("Invalid GTFS departure time")

    service_date = date.fromisoformat(travel_date)

    departure_datetime = (
        datetime.combine(
            service_date,
            datetime.min.time(),
            tzinfo=IST
        )
        + timedelta(
            hours=hours,
            minutes=minutes,
            seconds=seconds
        )
    )

    return {
        "trip_id": trip_id,
        "from_stop_id": from_stop_id,
        "to_stop_id": to_stop_id,
        "departure": departure_datetime.isoformat()
    }


def get_crowding(
    trip_id,
    from_stop_id,
    to_stop_id,
    departure_time,
    travel_date
):
    """
    Fetch one historical ticket-demand prediction
    from Member 1's Crowd Intelligence API.
    """

    try:
        params = build_crowd_params(
            trip_id,
            from_stop_id,
            to_stop_id,
            departure_time,
            travel_date
        )

        response = httpx.get(
            f"{CROWD_API_URL}/v1/crowding",
            params=params,
            timeout=15.0
        )

        response.raise_for_status()

        prediction = response.json()

        level = prediction.get(
            "overall", {}
        ).get("level")

        return {
            "status": (
                "available"
                if level not in (None, "unknown")
                else "insufficient_evidence"
            ),
            "prediction": prediction
        }

    except httpx.HTTPStatusError as error:
        return {
            "status": "error",
            "prediction": None,
            "detail": (
                "Crowd API returned HTTP "
                f"{error.response.status_code}"
            )
        }

    except httpx.RequestError:
        return {
            "status": "service_unavailable",
            "prediction": None
        }

    except (ValueError, TypeError, KeyError):
        return {
            "status": "error",
            "prediction": None,
            "detail": "Invalid prediction request data"
        }


def get_crowding_batch(
    journeys,
    from_stop_id,
    to_stop_id,
    travel_date
):
    """
    Fetch predictions for multiple journeys concurrently.

    Maximum of 4 workers prevents too many
    simultaneous requests to Member 1's server.

    Returns predictions in the same order as journeys.
    """

    if not journeys:
        return []

    def fetch_one(journey):
        return get_crowding(
            trip_id=journey["trip_id"],
            from_stop_id=from_stop_id,
            to_stop_id=to_stop_id,
            departure_time=journey["departure"],
            travel_date=travel_date
        )

    with ThreadPoolExecutor(
        max_workers=MAX_CROWD_WORKERS
    ) as executor:
        results = list(
            executor.map(fetch_one, journeys)
        )

    return results
