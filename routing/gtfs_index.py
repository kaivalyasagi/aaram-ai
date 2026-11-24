
import csv
from pathlib import Path

# Find the GTFS folder relative to this Python file.
BASE_DIR = Path(__file__).resolve().parent.parent
GTFS_DIR = BASE_DIR / "data" / "gtfs"


def load_gtfs_file(filename):
    """Read a GTFS CSV file and return its records."""

    file_path = GTFS_DIR / filename

    if not file_path.exists():
        raise FileNotFoundError(
            f"GTFS file not found: {file_path}"
        )

    with open(file_path, "r", encoding="utf-8-sig", newline="") as file:
        reader = csv.DictReader(file)
        return list(reader)


def main():
    print("===================================")
    print("     AARAM AI - GTFS DATA LOADER")
    print("===================================")

    files = [
        "stops.txt",
        "routes.txt",
        "trips.txt",
        "stop_times.txt",
        "calendar.txt",
    ]

    for filename in files:
        records = load_gtfs_file(filename)

        print(f"\nFile: {filename}")
        print(f"Total records: {len(records)}")

        if records:
            print(f"Columns: {list(records[0].keys())}")
            print(f"First record: {records[0]}")

    print("\nGTFS data loaded successfully!")


if __name__ == "__main__":
    main()


def find_sample_journey():
    """Find two consecutive stops on a real GTFS trip."""
    import csv

    with open(
        GTFS_DIR / "stop_times.txt",
        "r",
        encoding="utf-8-sig",
        newline=""
    ) as file:
        reader = csv.DictReader(file)

        first = None

        for row in reader:
            if first is None:
                first = row
                continue

            if (
                row["trip_id"] == first["trip_id"]
                and int(row["stop_sequence"])
                > int(first["stop_sequence"])
                and row["departure_time"] >= "08:00:00"
            ):
                print("\nSAMPLE JOURNEY")
                print("Trip ID:", row["trip_id"])
                print("From stop ID:", first["stop_id"])
                print("To stop ID:", row["stop_id"])
                print("Departure:", first["departure_time"])
                print("Arrival:", row["arrival_time"])
                return

            first = row

    print("No sample journey found.")


if __name__ == "__main__":
    find_sample_journey()
