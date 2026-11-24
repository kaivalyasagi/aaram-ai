
import csv
import sqlite3
from datetime import date

from routing.gtfs_index import GTFS_DIR, load_gtfs_file


# ---------------------------------------
# GTFS Database Location
# ---------------------------------------
DB_PATH = GTFS_DIR / "aaram_gtfs.db"


# ---------------------------------------
# Convert Time into Seconds
# ---------------------------------------
def time_to_seconds(value):
    """
    Convert HH:MM or HH:MM:SS to seconds.

    Supports GTFS times beyond midnight
    when allow_extended is True.
    """

    if not isinstance(value, str):
        raise ValueError(
            "Departure time must be a string"
        )

    parts = value.strip().split(":")

    if len(parts) == 2:
        parts.append("00")

    if len(parts) != 3:
        raise ValueError(
            "Invalid time format. Use HH:MM"
        )

    try:
        hours, minutes, seconds = map(int, parts)

    except ValueError:
        raise ValueError(
            "Time must contain valid numbers"
        )

    if not (
        0 <= hours <= 23
        and 0 <= minutes <= 59
        and 0 <= seconds <= 59
    ):
        raise ValueError(
            "Invalid departure time. "
            "Use a time between 00:00 and 23:59"
        )

    return (
        hours * 3600
        + minutes * 60
        + seconds
    )


# ---------------------------------------
# Convert Seconds into GTFS Time
# ---------------------------------------
def seconds_to_time(seconds):
    """
    Convert seconds to HH:MM:SS.

    GTFS permits times like 25:30:00,
    so hours are not restricted to 23.
    """

    hours = seconds // 3600

    minutes = (
        seconds % 3600
    ) // 60

    secs = seconds % 60

    return (
        f"{hours:02d}:"
        f"{minutes:02d}:"
        f"{secs:02d}"
    )


# ---------------------------------------
# Journey Finder Class
# ---------------------------------------
class JourneyFinder:

    def __init__(self):

        # Check whether GTFS database exists.
        if not DB_PATH.exists():
            raise FileNotFoundError(
                "GTFS database missing. "
                "Run python routing/build_gtfs_db.py"
            )

        # Load stop information.
        self.stops = load_gtfs_file(
            "stops.txt"
        )

        # Create stop lookup dictionary.
        self.stop_lookup = {
            stop["stop_id"]: stop
            for stop in self.stops
        }

        # Load GTFS service calendar.
        self.calendar = {
            row["service_id"]: row
            for row in load_gtfs_file(
                "calendar.txt"
            )
        }

        # Store service-date exceptions.
        self.exceptions = {}

        exception_file = (
            GTFS_DIR / "calendar_dates.txt"
        )

        if exception_file.exists():

            with open(
                exception_file,
                encoding="utf-8-sig",
                newline=""
            ) as file:

                reader = csv.DictReader(file)

                for row in reader:

                    key = (
                        row["service_id"],
                        row["date"]
                    )

                    self.exceptions[key] = (
                        row["exception_type"]
                    )

    # ---------------------------------------
    # Search Bus Stops
    # ---------------------------------------
    def search_stops(self, query):

        query = query.lower().strip()

        if not query:
            return []

        results = []

        for stop in self.stops:

            name = stop.get(
                "stop_name", ""
            )

            if query in name.lower():

                results.append({
                    "stop_id": stop["stop_id"],
                    "stop_name": name
                })

            # Limit dropdown results.
            if len(results) >= 20:
                break

        return results

    # ---------------------------------------
    # Check Service Availability
    # ---------------------------------------
    def service_runs(
        self,
        service_id,
        travel_date
    ):

        day = date.fromisoformat(
            travel_date
        )

        date_key = day.strftime(
            "%Y%m%d"
        )

        # Check service exceptions first.
        exception = self.exceptions.get(
            (service_id, date_key)
        )

        if exception == "1":
            return True

        if exception == "2":
            return False

        # Check regular calendar.
        service = self.calendar.get(
            service_id
        )

        if not service:
            return False

        if not (
            service["start_date"]
            <= date_key
            <= service["end_date"]
        ):
            return False

        weekday = day.strftime(
            "%A"
        ).lower()

        return (
            service.get(weekday) == "1"
        )

    # ---------------------------------------
    # Find Scheduled Bus Journeys
    # ---------------------------------------
    def find_journeys(
        self,
        from_stop_id,
        to_stop_id,
        departure_time="08:00",
        travel_date=None
    ):

        # Normalize input.
        from_stop_id = from_stop_id.strip()
        to_stop_id = to_stop_id.strip()
        departure_time = departure_time.strip()

        # Default travel date.
        if travel_date is None:
            travel_date = (
                date.today().isoformat()
            )

        # -----------------------------------
        # Validate Travel Date
        # -----------------------------------
        try:
            date.fromisoformat(
                travel_date
            )

        except (ValueError, TypeError):
            raise ValueError(
                "Invalid travel date. "
                "Use YYYY-MM-DD"
            )

        # -----------------------------------
        # Validate Stops
        # -----------------------------------
        if not from_stop_id:
            raise ValueError(
                "Starting stop is required"
            )

        if not to_stop_id:
            raise ValueError(
                "Destination stop is required"
            )

        if from_stop_id == to_stop_id:
            raise ValueError(
                "Starting and destination stops "
                "must be different"
            )

        if from_stop_id not in self.stop_lookup:
            raise ValueError(
                "Starting stop ID not found"
            )

        if to_stop_id not in self.stop_lookup:
            raise ValueError(
                "Destination stop ID not found"
            )

        # -----------------------------------
        # Validate Departure Time
        # -----------------------------------
        requested_seconds = (
            time_to_seconds(
                departure_time
            )
        )

        # -----------------------------------
        # Connect to GTFS Database
        # -----------------------------------
        connection = sqlite3.connect(
            DB_PATH
        )

        connection.row_factory = (
            sqlite3.Row
        )

        try:
            cursor = connection.cursor()

            # Find direct scheduled journeys
            # in the next 4 hours.
            cursor.execute(
                """
                SELECT
                    t.trip_id,
                    t.service_id,
                    r.route_short_name AS route,
                    a.departure_seconds AS departure,
                    b.arrival_seconds AS arrival

                FROM stop_times AS a

                JOIN stop_times AS b
                    ON a.trip_id = b.trip_id
                    AND b.stop_sequence > a.stop_sequence

                JOIN trips AS t
                    ON t.trip_id = a.trip_id

                JOIN routes AS r
                    ON r.route_id = t.route_id

                WHERE a.stop_id = ?
                  AND b.stop_id = ?
                  AND a.departure_seconds >= ?
                  AND a.departure_seconds < ?

                ORDER BY a.departure_seconds

                LIMIT 100
                """,
                (
                    from_stop_id,
                    to_stop_id,
                    requested_seconds,
                    requested_seconds + 14400
                )
            )

            rows = cursor.fetchall()

        finally:
            connection.close()

        # -----------------------------------
        # Filter Valid Journeys
        # -----------------------------------
        journeys = []

        for row in rows:

            # Skip inactive bus services.
            if not self.service_runs(
                row["service_id"],
                travel_date
            ):
                continue

            if row["arrival"] is None:
                continue

            duration_seconds = (
                row["arrival"]
                - row["departure"]
            )

            if duration_seconds < 0:
                continue

            # Build journey response.
            journeys.append({
                "trip_id": row["trip_id"],

                "route": row["route"],

                "from_stop": (
                    self.stop_lookup[
                        from_stop_id
                    ]["stop_name"]
                ),

                "to_stop": (
                    self.stop_lookup[
                        to_stop_id
                    ]["stop_name"]
                ),

                "departure": (
                    seconds_to_time(
                        row["departure"]
                    )
                ),

                "arrival": (
                    seconds_to_time(
                        row["arrival"]
                    )
                ),

                "duration_minutes": round(
                    duration_seconds / 60,
                    1
                ),

                "service_id": (
                    row["service_id"]
                ),

                "travel_date": (
                    travel_date
                )
            })

            # Return up to 10 journeys.
            if len(journeys) >= 10:
                break

        return journeys
