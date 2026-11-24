# Crowding validation: chronological October holdout

## Split and unit

The model was fit only on **October 1–21, 2026** and evaluated on **October 22–31, 2026**. The target and prediction are both daily **sampled ticket demand per matched GTFS segment**. They are not a count of all onboard passengers, occupancy percentage, capacity utilization, or seat availability.

The evaluation uses 4,794,102 training segment observations and 2,486,742 held-out observations. Exact time-aware profiles are route, direction, ordered stop pattern, segment, weekday/weekend type, and 30-minute band medians from the training period. The comparison baseline ignores weekday type and time band, using only the historical route-pattern-segment median.

## Actual results

| Measure | Result |
|---|---:|
| Prediction coverage | 99.8982% (2,484,210 / 2,486,742) |
| Time-aware MAE | 0.828794 sampled passengers per daily segment |
| Time-aware median absolute error | 0.5 |
| Time-aware p90 / p95 absolute error | 2.0 / 3.0 |
| Broad segment-history baseline MAE | 0.927580 |
| Fair time-aware MAE | 0.903316 |
| Fair baseline MAE, same 2,189,094 rows | 1.015420 |

The fair comparison uses only rows where both predictions exist. Time-aware historical profiles reduce MAE by **0.112104** sampled passengers per daily segment versus the broad segment-history baseline on that common evaluation set.

## Coverage and error breakdown

| Source | Held-out rows | MAE |
|---|---:|---:|
| Exact route-pattern-segment-time profile | 2,189,094 | 0.903316 |
| Broader segment-history fallback | 295,116 | 0.276008 |
| Unsupported | 2,532 | N/A |

Weekday MAE was 0.829201 across 1,821,723 rows; weekend MAE was 0.827677 across 662,487 rows.

Machine-readable output is in [crowding-validation.json](crowding-validation.json). Regenerate it with:

```bash
python -m backend.crowding.validation data/processed/segment_demand.parquet \
  --cutoff-date 2026-10-22 --output docs/crowding-validation.json
```

## Limitations

- Tickets represent observed ticket-channel demand, not verified total bus ridership.
- Pass holders, missing ticket channels, stop matching error, ticket timestamp interpretation, and missing vehicle IDs affect both model and validation coverage.
- The holdout establishes predictive consistency for matched sampled demand only. It does not validate actual physical crowding or guarantee a seat.
