# Crowding methodology

Each matched ticket is expanded over every GTFS segment between its boarding and alighting indices. Passenger counts are retained as observed sampled demand. The predictor groups these observations by route, direction, pattern, segment, weekday/weekend, and 30-minute band, using median daily demand and a route-pattern 95th-percentile normalization.

Fallbacks widen from the precise time band to ±60 minutes and then the segment's broader profile. A result is `unknown` when evidence is too sparse. Evidence is heuristic and considers distinct days, fallback level, and stop-match quality; it is not a calibrated probability.

The method does not infer total passengers, actual load, capacity, or seat availability. Missing channels, pass holders, uncertain transaction time, vehicle identifiers, and ambiguous stop matching are explicit limitations.
