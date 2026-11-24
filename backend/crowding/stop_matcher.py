"""Indexed, route-constrained GTFS ticket-stop matching.

A pattern is a unique ordered stop-id sequence within a route/direction, not a
shape_id. GTFS schedules often contain many trips with the same pattern.
"""
from __future__ import annotations

import hashlib
import logging
import re
from collections import defaultdict
from dataclasses import dataclass
from difflib import SequenceMatcher
from pathlib import Path

import pandas as pd

LOG = logging.getLogger(__name__)


def normalize(value: object) -> str:
    text = str(value or "").lower().strip()
    text = re.sub(r"\b(rd|road)\b", "road", text)
    text = re.sub(r"\b(st|station)\b", "station", text)
    return re.sub(r"[^a-z0-9]+", " ", text).strip()


def route_key(value: object) -> str:
    return normalize(value).replace(" ", "")


@dataclass(frozen=True)
class StopPattern:
    pattern_id: str
    route_id: str
    direction_id: str
    stop_ids: tuple[str, ...]
    stop_names: tuple[str, ...]
    representative_trip_id: str
    trip_count: int
    exact_positions: dict[str, tuple[int, ...]]


class GTFSStopMatcher:
    """Load GTFS once; ticket matching performs no DataFrame scans."""

    def __init__(self, gtfs_dir: str | Path):
        base = Path(gtfs_dir)
        stops = pd.read_csv(base / "stops.txt", dtype={"stop_id": str, "stop_name": str}, usecols=["stop_id", "stop_name"])
        routes = pd.read_csv(base / "routes.txt", dtype=str)
        trips = pd.read_csv(base / "trips.txt", dtype=str, usecols=["route_id", "trip_id", "direction_id"])
        times = pd.read_csv(base / "stop_times.txt", dtype={"trip_id": str, "stop_id": str}, usecols=["trip_id", "stop_id", "stop_sequence"])
        times["stop_sequence"] = pd.to_numeric(times["stop_sequence"], errors="coerce")
        times = times.dropna(subset=["stop_sequence"]).astype({"stop_sequence": "int64"})
        trips["route_id"] = trips.route_id.astype(str)
        trips["trip_id"] = trips.trip_id.astype(str)
        trips["direction_id"] = trips.direction_id.fillna("0").astype(str)
        stop_names = dict(zip(stops.stop_id.astype(str), stops.stop_name.map(normalize)))
        route_labels: dict[str, set[str]] = defaultdict(set)
        for row in routes.fillna("").itertuples(index=False):
            route_id = str(row.route_id)
            for field in ("route_id", "route_short_name", "route_long_name"):
                if hasattr(row, field):
                    key = route_key(getattr(row, field))
                    if key:
                        route_labels[key].add(route_id)
        # One numeric sort. Nothing below filters stop_times per ticket/trip.
        merged = times.merge(trips, on="trip_id", how="inner", validate="many_to_one")
        merged = merged.sort_values(["route_id", "direction_id", "trip_id", "stop_sequence"], kind="stable")
        grouped: dict[tuple[str, str, tuple[str, ...]], list[str]] = defaultdict(list)
        for (route_id, direction_id, trip_id), frame in merged.groupby(["route_id", "direction_id", "trip_id"], sort=False):
            sequence = tuple(frame.stop_id.astype(str))
            if len(sequence) >= 2:
                grouped[(str(route_id), str(direction_id), sequence)].append(str(trip_id))
        self.patterns: dict[str, StopPattern] = {}
        self.pattern_id_by_trip: dict[str, str] = {}
        by_route: dict[str, list[StopPattern]] = defaultdict(list)
        for (route_id, direction_id, sequence), trip_ids in grouped.items():
            digest = hashlib.sha1((route_id + "|" + direction_id + "|" + "|".join(sequence)).encode()).hexdigest()[:16]
            pattern_id = f"p_{digest}"
            positions: dict[str, list[int]] = defaultdict(list)
            names = tuple(stop_names.get(stop_id, "") for stop_id in sequence)
            for index, name in enumerate(names):
                if name:
                    positions[name].append(index)
            pattern = StopPattern(pattern_id, route_id, direction_id, sequence, names, min(trip_ids), len(trip_ids),
                                  {key: tuple(value) for key, value in positions.items()})
            self.patterns[pattern_id] = pattern
            by_route[route_id].append(pattern)
            self.pattern_id_by_trip.update({trip_id: pattern_id for trip_id in trip_ids})
        self.patterns_by_route = {key: tuple(value) for key, value in by_route.items()}
        self.route_labels = {key: frozenset(value) for key, value in route_labels.items()}
        LOG.info("GTFS indexed: %d trips, %d unique route-direction patterns, %d stop-time rows", len(trips), len(self.patterns), len(merged))

    def _route_ids(self, label: object) -> frozenset[str]:
        return self.route_labels.get(route_key(label), frozenset())

    @staticmethod
    def _pairs(pattern: StopPattern, board: str, alight: str) -> list[tuple[int, int]]:
        return [(start, end) for start in pattern.exact_positions.get(board, ()) for end in pattern.exact_positions.get(alight, ()) if start < end]

    def _result(self, pattern: StopPattern, start: int, end: int, score: float) -> dict:
        return {"matched": True, "trip_id": pattern.representative_trip_id, "route_id": pattern.route_id,
                "direction_id": pattern.direction_id, "pattern_id": pattern.pattern_id, "board_index": start,
                "alight_index": end, "match_confidence": round(score, 4), "pattern_trip_count": pattern.trip_count}

    def match(self, route_label: object, board_name: object, alight_name: object, threshold: float = .82) -> dict:
        route_ids = self._route_ids(route_label)
        if not route_ids:
            return {"matched": False, "reason": "route_unmatched"}
        board, alight = normalize(board_name), normalize(alight_name)
        candidates: list[tuple[StopPattern, int, int]] = []
        for route_id in route_ids:
            for pattern in self.patterns_by_route.get(route_id, ()):
                candidates.extend((pattern, start, end) for start, end in self._pairs(pattern, board, alight))
        if len(candidates) == 1:
            pattern, start, end = candidates[0]
            return self._result(pattern, start, end, 1.0)
        if len(candidates) > 1:
            return {"matched": False, "reason": "ambiguous_exact_match", "candidate_count": len(candidates)}
        # Only route-limited patterns reach this expensive fallback.
        fuzzy: list[tuple[float, StopPattern, int, int]] = []
        for route_id in route_ids:
            for pattern in self.patterns_by_route.get(route_id, ()):
                boards = [(SequenceMatcher(None, board, name).ratio(), index) for index, name in enumerate(pattern.stop_names)]
                alights = [(SequenceMatcher(None, alight, name).ratio(), index) for index, name in enumerate(pattern.stop_names)]
                best_board, best_alight = max(boards, default=(0.0, -1)), max(alights, default=(0.0, -1))
                if best_board[1] < best_alight[1]:
                    fuzzy.append((min(best_board[0], best_alight[0]), pattern, best_board[1], best_alight[1]))
        if not fuzzy:
            return {"matched": False, "reason": "stops_unmatched_or_out_of_order"}
        fuzzy.sort(key=lambda item: item[0], reverse=True)
        best = fuzzy[0]
        ties = [item for item in fuzzy if abs(item[0] - best[0]) < 1e-9]
        if best[0] < threshold:
            return {"matched": False, "reason": "fuzzy_match_below_threshold", "best_score": round(best[0], 4)}
        if len(ties) > 1:
            return {"matched": False, "reason": "ambiguous_fuzzy_match", "candidate_count": len(ties), "best_score": round(best[0], 4)}
        return self._result(best[1], best[2], best[3], best[0])

    def pattern_segments(self) -> dict[str, tuple[str, ...]]:
        return {pattern_id: pattern.stop_ids for pattern_id, pattern in self.patterns.items()}

    def pattern_for_trip(self, trip_id: str) -> StopPattern | None:
        pattern_id = self.pattern_id_by_trip.get(str(trip_id))
        return self.patterns.get(pattern_id) if pattern_id else None
