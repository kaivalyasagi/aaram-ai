"""Vectorized chronological validation of sampled segment-demand predictions.

This validation deliberately compares daily sampled ticket demand with a
historical median of the *same sampled-demand unit*. It does not evaluate, or
make claims about, physical onboard passenger occupancy.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd

from .storage import read_table

BASE_KEYS = ["route_id", "direction_id", "pattern_id", "segment_index"]
TIME_KEYS = BASE_KEYS + ["weekday_type", "time_band"]
REQUIRED = set(TIME_KEYS + ["service_date", "sampled_demand", "match_confidence"])


def _metrics(frame: pd.DataFrame, prediction: str) -> dict[str, float | int | None]:
    valid = frame[prediction].notna()
    if not valid.any():
        return {"rows": 0, "mae": None, "median_absolute_error": None}
    error = (frame.loc[valid, "sampled_demand"] - frame.loc[valid, prediction]).abs()
    return {"rows": int(valid.sum()), "mae": round(float(error.mean()), 6), "median_absolute_error": round(float(error.median()), 6)}


def validate(segments: pd.DataFrame, cutoff_date: str = "2026-10-22") -> dict:
    """Evaluate Oct 1–21 training predictions on Oct 22–31 observations.

    The time-aware model is the same route/direction/pattern/segment,
    weekday-type, 30-minute-band median calculated exclusively from training
    dates. The baseline is a route/direction/pattern/segment historical median
    that deliberately ignores time and weekday type.
    """
    missing = REQUIRED - set(segments.columns)
    if missing:
        raise ValueError(f"segment table missing columns: {sorted(missing)}")
    columns = list(REQUIRED)
    data = segments.loc[:, columns].copy()
    data["service_date"] = data.service_date.astype(str)
    train = data[data.service_date < cutoff_date]
    test = data[data.service_date >= cutoff_date]
    if train.empty or test.empty:
        raise ValueError("chronological split requires observations on both sides of cutoff_date")
    # The source already contains one observed daily segment demand per key.
    time_profile = train.groupby(TIME_KEYS, observed=True, sort=False).agg(
        time_aware_prediction=("sampled_demand", "median"),
        observed_days=("service_date", "nunique"),
        mean_match_confidence=("match_confidence", "mean"),
    ).reset_index()
    baseline_profile = train.groupby(BASE_KEYS, observed=True, sort=False).agg(
        baseline_prediction=("sampled_demand", "median"),
        baseline_observed_days=("service_date", "nunique"),
    ).reset_index()
    # Hash joins, not row-by-row model calls or DataFrame filtering.
    evaluated = test.merge(time_profile, on=TIME_KEYS, how="left", validate="many_to_one")
    evaluated = evaluated.merge(baseline_profile, on=BASE_KEYS, how="left", validate="many_to_one")
    exact = evaluated.time_aware_prediction.notna()
    broad = ~exact & evaluated.baseline_prediction.notna()
    evaluated["prediction"] = evaluated.time_aware_prediction.where(exact, evaluated.baseline_prediction)
    evaluated["prediction_source"] = np.select([exact, broad], ["time_aware_exact", "segment_history_fallback"], default="unsupported")
    model_metrics = _metrics(evaluated, "prediction")
    baseline_metrics = _metrics(evaluated, "baseline_prediction")
    comparable = evaluated[exact & evaluated.baseline_prediction.notna()].copy()
    comparable["time_aware_abs_error"] = (comparable.sampled_demand - comparable.time_aware_prediction).abs()
    comparable["baseline_abs_error"] = (comparable.sampled_demand - comparable.baseline_prediction).abs()
    covered = evaluated.prediction.notna()
    source_breakdown = {}
    for source, group in evaluated.groupby("prediction_source", sort=False):
        source_breakdown[str(source)] = {"rows": int(len(group)), **_metrics(group, "prediction")}
    # Grouping can omit all-null categorical join-key rows; account for them
    # explicitly so source counts always reconcile to evaluation_segment_rows.
    source_breakdown["unsupported"] = {"rows": int((~covered).sum()), "mae": None, "median_absolute_error": None}
    weekday_breakdown = {}
    for weekday_type, group in evaluated.groupby("weekday_type", sort=False):
        weekday_breakdown[str(weekday_type)] = {"rows": int(len(group)), **_metrics(group, "prediction")}
    error_quantiles = {}
    if covered.any():
        errors = (evaluated.loc[covered, "sampled_demand"] - evaluated.loc[covered, "prediction"]).abs()
        error_quantiles = {"p50": round(float(errors.quantile(.5)), 6), "p90": round(float(errors.quantile(.9)), 6), "p95": round(float(errors.quantile(.95)), 6)}
    result = {
        "split": {"training_dates": [str(train.service_date.min()), str(train.service_date.max())], "evaluation_dates": [str(test.service_date.min()), str(test.service_date.max())], "cutoff_date": cutoff_date},
        "unit": "daily sampled segment demand (ticket-observed, not physical occupancy)",
        "train_segment_rows": int(len(train)), "evaluation_segment_rows": int(len(test)),
        "time_aware_profile_rows": int(len(time_profile)), "baseline_profile_rows": int(len(baseline_profile)),
        "model": {**model_metrics, "coverage": round(float(covered.mean()), 6), "error_quantiles": error_quantiles},
        "baseline_segment_history": {**baseline_metrics, "coverage": round(float(evaluated.baseline_prediction.notna().mean()), 6)},
        "fair_time_aware_vs_baseline": {"rows": int(len(comparable)), "time_aware_mae": round(float(comparable.time_aware_abs_error.mean()), 6) if len(comparable) else None, "baseline_mae": round(float(comparable.baseline_abs_error.mean()), 6) if len(comparable) else None},
        "prediction_source_breakdown": source_breakdown,
        "weekday_type_breakdown": weekday_breakdown,
        "limitations": ["Holdout targets are observed sampled ticket demand, not total passengers or bus occupancy.", "Matching and ticketing-channel coverage limitations propagate into this validation.", "Time-aware coverage is limited to route-pattern-segment-time combinations observed before the cutoff."],
    }
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("segments", nargs="?", default="data/processed/segment_demand.parquet")
    parser.add_argument("--cutoff-date", default="2026-10-22")
    parser.add_argument("--output", default="docs/crowding-validation.json")
    args = parser.parse_args()
    result = validate(read_table(args.segments), args.cutoff_date)
    Path(args.output).write_text(json.dumps(result, indent=2))
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
