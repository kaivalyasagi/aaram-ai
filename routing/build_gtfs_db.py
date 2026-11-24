
import csv
import sqlite3
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
GTFS_DIR = BASE_DIR / "data" / "gtfs"
DB_PATH = GTFS_DIR / "aaram_gtfs.db"


def convert_time(value):
    """Convert GTFS HH:MM:SS into seconds."""
    if not value:
        return None

    h, m, s = map(int, value.split(":"))
    return h * 3600 + m * 60 + s


def build_database():
    print("AARAM AI - Building GTFS Database")

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.executescript("""
        DROP TABLE IF EXISTS stop_times;
        DROP TABLE IF EXISTS trips;
        DROP TABLE IF EXISTS routes;
        DROP TABLE IF EXISTS stops;

        CREATE TABLE stops (
            stop_id TEXT PRIMARY KEY,
            stop_name TEXT,
            stop_lat REAL,
            stop_lon REAL
        );

        CREATE TABLE routes (
            route_id TEXT PRIMARY KEY,
            route_short_name TEXT
        );

        CREATE TABLE trips (
            trip_id TEXT PRIMARY KEY,
            route_id TEXT,
            service_id TEXT
        );

        CREATE TABLE stop_times (
            trip_id TEXT,
            stop_id TEXT,
            stop_sequence INTEGER,
            arrival_seconds INTEGER,
            departure_seconds INTEGER
        );
    """)

    print("Importing stops...")

    with open(GTFS_DIR / "stops.txt",
              encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)

        cursor.executemany(
            "INSERT INTO stops VALUES (?, ?, ?, ?)",
            (
                (
                    r["stop_id"],
                    r["stop_name"],
                    float(r["stop_lat"]) if r["stop_lat"] else None,
                    float(r["stop_lon"]) if r["stop_lon"] else None
                )
                for r in reader
            )
        )

    print("Importing routes...")

    with open(GTFS_DIR / "routes.txt",
              encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)

        cursor.executemany(
            "INSERT INTO routes VALUES (?, ?)",
            (
                (r["route_id"], r["route_short_name"])
                for r in reader
            )
        )

    print("Importing trips...")

    with open(GTFS_DIR / "trips.txt",
              encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)

        cursor.executemany(
            "INSERT INTO trips VALUES (?, ?, ?)",
            (
                (r["trip_id"], r["route_id"], r["service_id"])
                for r in reader
            )
        )

    print("Importing stop times...")

    count = 0
    batch = []

    with open(GTFS_DIR / "stop_times.txt",
              encoding="utf-8-sig", newline="") as f:

        reader = csv.DictReader(f)

        for r in reader:
            batch.append((
                r["trip_id"],
                r["stop_id"],
                int(r["stop_sequence"]),
                convert_time(r["arrival_time"]),
                convert_time(r["departure_time"])
            ))

            if len(batch) == 10000:
                cursor.executemany(
                    "INSERT INTO stop_times VALUES (?, ?, ?, ?, ?)",
                    batch
                )

                count += len(batch)
                batch.clear()

                if count % 500000 == 0:
                    print(f"Imported {count:,} records")

        if batch:
            cursor.executemany(
                "INSERT INTO stop_times VALUES (?, ?, ?, ?, ?)",
                batch
            )
            count += len(batch)

    print("Creating search indexes...")

    cursor.executescript("""
        CREATE INDEX idx_stop_times_stop
        ON stop_times(stop_id);

        CREATE INDEX idx_stop_times_trip
        ON stop_times(trip_id, stop_sequence);
    """)

    conn.commit()
    conn.close()

    print("\nDATABASE CREATED SUCCESSFULLY!")
    print(f"Total stop-time records: {count:,}")
    print(f"Location: {DB_PATH}")


if __name__ == "__main__":
    build_database()
