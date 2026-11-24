"""Batch runner: clean tickets -> indexed GTFS matching -> demand profiles."""
from __future__ import annotations

import argparse
import logging
import time
from pathlib import Path

import pandas as pd

from .ingest import ingest
from .passenger_flow import reconstruct_segment_demand
from .predictor import CrowdingPredictor
from .stop_matcher import GTFSStopMatcher
from .storage import read_table, write_table

LOG = logging.getLogger(__name__)


def build(source: str | Path | None, gtfs_dir: str | Path, output_dir: str | Path, *, cleaned_tickets: str | Path | None = None, sample_rows: int | None = None) -> dict[str, str | int | float]:
    started, output = time.monotonic(), Path(output_dir)
    if cleaned_tickets:
        clean_path = Path(cleaned_tickets)
    elif (output / "tickets_clean.parquet").exists():
        clean_path = output / "tickets_clean.parquet"
    elif source:
        clean_path = Path(ingest(source, output)["table"])
    else:
        raise ValueError("Provide source or --cleaned-tickets")
    tickets = read_table(clean_path)
    if sample_rows is not None:
        tickets = tickets.head(sample_rows).copy()
    LOG.info("Loaded %d ticket rows from %s", len(tickets), clean_path)
    matcher = GTFSStopMatcher(gtfs_dir)
    keys = tickets[["route", "start_stop_name", "end_stop_name"]].fillna("").drop_duplicates().reset_index(drop=True)
    results: list[dict] = []
    for index, row in enumerate(keys.itertuples(index=False), 1):
        result = matcher.match(row.route, row.start_stop_name, row.end_stop_name)
        results.append({"route": row.route, "start_stop_name": row.start_stop_name, "end_stop_name": row.end_stop_name, **result})
        if index % 10_000 == 0:
            LOG.info("Matched %d/%d unique route-stop combinations (%.1fs)", index, len(keys), time.monotonic() - started)
    resolution = pd.DataFrame(results)
    resolution_path = write_table(resolution, output / "match_resolution.parquet")
    matched_lookup = resolution[resolution.matched].drop(columns=["matched"], errors="ignore")
    mapped = tickets.merge(matched_lookup, how="inner", on=["route", "start_stop_name", "end_stop_name"], validate="many_to_one")
    reason_counts = resolution.loc[~resolution.matched, "reason"].value_counts().to_dict()
    LOG.info("Resolved %d unique combinations: %d matched, %d unmatched; %d/%d ticket rows matched", len(keys), int(resolution.matched.sum()), int((~resolution.matched).sum()), len(mapped), len(tickets))
    mapped_path = write_table(mapped, output / "tickets_mapped.parquet")
    segments = reconstruct_segment_demand(mapped, matcher.pattern_segments())
    segments_path = write_table(segments, output / "segment_demand.parquet")
    profile_path = output / "crowding_profiles.json"
    CrowdingPredictor.fit(segments).save(profile_path)
    elapsed = round(time.monotonic() - started, 2)
    LOG.info("Built %d segment observations in %.1fs", len(segments), elapsed)
    return {"cleaned_tickets": str(clean_path), "match_resolution": str(resolution_path), "mapped_tickets": str(mapped_path), "segment_demand": str(segments_path), "profiles": str(profile_path), "ticket_rows": len(tickets), "matched_ticket_rows": len(mapped), "unmatched_ticket_rows": len(tickets) - len(mapped), "unique_match_attempts": len(keys), "unmatched_reasons": str(reason_counts), "elapsed_seconds": elapsed}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", nargs="?")
    parser.add_argument("--gtfs-dir", default="data/gtfs")
    parser.add_argument("--output-dir", default="data/processed")
    parser.add_argument("--cleaned-tickets", help="Reuse clean Parquet instead of reading the ZIP")
    parser.add_argument("--sample-rows", type=int, help="Bounded real-data smoke test; do not use its artifacts as final outputs")
    parser.add_argument("--log-level", default="INFO")
    args = parser.parse_args()
    logging.basicConfig(level=getattr(logging, args.log_level.upper()), format="%(asctime)s %(levelname)s %(message)s")
    print(build(args.source, args.gtfs_dir, args.output_dir, cleaned_tickets=args.cleaned_tickets, sample_rows=args.sample_rows))


if __name__ == "__main__":
    main()
