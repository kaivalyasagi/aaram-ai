"""Deterministic profiles and hierarchical fallback for relative ticket demand."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd

LEVELS = ((0.34, "low"), (0.67, "medium"), (1.0, "high"))


@dataclass
class SegmentPrediction:
    level: str
    score: float | None
    evidence: str
    observed_days: int


class CrowdingPredictor:
    def __init__(self, profiles: pd.DataFrame | None = None):
        self.profiles = profiles if profiles is not None else pd.DataFrame()
        self._exact: dict[int, int] = {}
        self._pattern_codes: dict[str, int] = {}
        self._pattern_meta: dict[int, tuple[str, str]] = {}
        self._scores = np.array([], dtype=np.float32)
        self._days = np.array([], dtype=np.uint16)
        self._confidence = np.array([], dtype=np.float32)
        if not self.profiles.empty:
            self._build_index()

    @staticmethod
    def _key(pattern_code: int, segment_index: int, weekday_code: int, time_band: int) -> int:
        """Compact, collision-free key for GTFS-sized pattern/segment/band domains."""
        return (pattern_code << 18) | (segment_index << 8) | (weekday_code << 6) | time_band

    def _build_index(self) -> None:
        required = {"route_id", "direction_id", "pattern_id", "segment_index", "weekday_type", "time_band", "score", "observed_days", "mean_match_confidence"}
        missing = required - set(self.profiles.columns)
        if missing:
            raise ValueError(f"profile artifact missing columns: {sorted(missing)}")
        pattern_ids = self.profiles.pattern_id.astype(str)
        codes, uniques = pd.factorize(pattern_ids, sort=True)
        self._pattern_codes = {pattern_id: index for index, pattern_id in enumerate(uniques.tolist())}
        meta = self.profiles.assign(_code=codes).groupby("_code", sort=False)[["route_id", "direction_id"]].first()
        self._pattern_meta = {int(code): (str(row.route_id), str(row.direction_id)) for code, row in meta.iterrows()}
        weekdays = (self.profiles.weekday_type.astype(str) == "weekend").to_numpy(dtype=np.int8)
        segments = pd.to_numeric(self.profiles.segment_index, errors="raise").to_numpy(dtype=np.int64)
        bands = pd.to_numeric(self.profiles.time_band, errors="raise").to_numpy(dtype=np.int64)
        if (segments < 0).any() or (segments >= 1024).any() or (bands < 0).any() or (bands >= 64).any():
            raise ValueError("profile segment_index/time_band exceeds compact index limits")
        keys = (codes.astype(np.int64) << 18) | (segments << 8) | (weekdays.astype(np.int64) << 6) | bands
        self._exact = {int(key): index for index, key in enumerate(keys)}
        self._scores = pd.to_numeric(self.profiles.score, errors="coerce").to_numpy(dtype=np.float32)
        self._days = pd.to_numeric(self.profiles.observed_days, errors="coerce").fillna(0).to_numpy(dtype=np.uint16)
        self._confidence = pd.to_numeric(self.profiles.mean_match_confidence, errors="coerce").fillna(0).to_numpy(dtype=np.float32)

    @property
    def is_loaded(self) -> bool:
        return bool(self._exact)

    @classmethod
    def fit(cls, segments: pd.DataFrame) -> "CrowdingPredictor":
        if segments.empty:
            return cls(pd.DataFrame())
        keys = ["route_id", "direction_id", "pattern_id", "segment_index", "weekday_type", "time_band"]
        daily = segments.groupby(keys + ["service_date"], as_index=False).agg(demand=("sampled_demand", "sum"), match_confidence=("match_confidence", "mean"))
        profile = daily.groupby(keys, as_index=False).agg(demand_median=("demand", "median"), observed_days=("service_date", "nunique"), observations=("service_date", "size"), mean_match_confidence=("match_confidence", "mean"), demand_variability=("demand", "std"))
        profile["demand_variability"] = profile["demand_variability"].fillna(0.0)
        normalizer = profile.groupby(["route_id", "direction_id", "pattern_id"])["demand_median"].transform(lambda col: max(float(col.quantile(.95)), 1.0))
        profile["score"] = (profile["demand_median"] / normalizer).clip(0, 1)
        return cls(profile)

    def save(self, path: str | Path) -> None:
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        self.profiles.to_json(path, orient="records", date_format="iso")

    @classmethod
    def load(cls, path: str | Path) -> "CrowdingPredictor":
        path = Path(path)
        model = cls(pd.read_json(path) if path.exists() else pd.DataFrame())
        # The compact index replaces a very large DataFrame at API runtime.
        if model.is_loaded:
            model.profiles = pd.DataFrame()
        return model

    @staticmethod
    def _evidence(observed_days: int, confidence: float, fallback: int) -> str:
        if fallback >= 3 or observed_days < 2:
            return "insufficient"
        if fallback >= 2 or observed_days < 4 or confidence < .70:
            return "low"
        if fallback == 1 or observed_days < 8:
            return "medium"
        return "high"

    def _prediction_at(self, profile_index: int, fallback: int) -> SegmentPrediction:
        observed_days = int(self._days[profile_index])
        evidence = self._evidence(observed_days, float(self._confidence[profile_index]), fallback)
        if evidence == "insufficient":
            return SegmentPrediction("unknown", None, evidence, observed_days)
        score = float(self._scores[profile_index])
        level = next(name for cutoff, name in LEVELS if score <= cutoff)
        return SegmentPrediction(level, round(score, 4), evidence, observed_days)

    def predict(self, route_id: str, direction_id: str, pattern_id: str, segment_index: int, weekday_type: str, time_band: int) -> SegmentPrediction:
        pattern_code = self._pattern_codes.get(str(pattern_id))
        if pattern_code is None or self._pattern_meta.get(pattern_code) != (str(route_id), str(direction_id)):
            return SegmentPrediction("unknown", None, "insufficient", 0)
        weekday_code = 1 if weekday_type == "weekend" else 0
        exact = self._exact.get(self._key(pattern_code, segment_index, weekday_code, time_band))
        if exact is not None:
            return self._prediction_at(exact, 0)
        # Bounded constant-time fallback probes: ±60 minutes, then all 48
        # weekly/weekend bands. No profile DataFrame scan occurs per request.
        for offset in (1, -1, 2, -2):
            band = time_band + offset
            if 0 <= band < 48:
                index = self._exact.get(self._key(pattern_code, segment_index, weekday_code, band))
                if index is not None:
                    return self._prediction_at(index, 1)
        closest: tuple[int, int] | None = None
        for candidate_weekday in (weekday_code, 1 - weekday_code):
            for band in range(48):
                index = self._exact.get(self._key(pattern_code, segment_index, candidate_weekday, band))
                if index is not None and (closest is None or abs(band - time_band) < closest[0]):
                    closest = (abs(band - time_band), index)
        if closest is not None:
            return self._prediction_at(closest[1], 2)
        return SegmentPrediction("unknown", None, "insufficient", 0)
