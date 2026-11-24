
# AARAM AI - Smart ComfortShift
# Evidence-aware journey recommendations


def time_to_seconds(value):
    """Convert GTFS HH:MM or HH:MM:SS into seconds."""

    parts = list(map(int, value.strip().split(":")))

    if len(parts) == 2:
        parts.append(0)

    if len(parts) != 3:
        raise ValueError("Invalid time format")

    hours, minutes, seconds = parts

    if not (
        0 <= hours <= 23
        and 0 <= minutes <= 59
        and 0 <= seconds <= 59
    ):
        raise ValueError("Invalid time")

    return hours * 3600 + minutes * 60 + seconds


def get_demand_score(prediction):
    """
    Return a demand score only when the prediction
    has sufficiently strong evidence.
    """

    if not prediction:
        return None

    overall = prediction.get("overall", {})

    if overall.get("evidence") != "high":
        return None

    scores = [
        segment["score"]
        for segment in prediction.get("segments", [])
        if segment.get("score") is not None
        and segment.get("evidence") == "high"
    ]

    if not scores:
        return None

    return sum(scores) / len(scores)


def compare_departures(journeys, requested_time):
    """
    Compare bus departures without fabricating
    crowd predictions.
    """

    requested_seconds = time_to_seconds(requested_time)
    alternatives = []

    for journey in journeys:
        departure_seconds = time_to_seconds(
            journey["departure"]
        )

        waiting_minutes = round(
            max(0, departure_seconds - requested_seconds) / 60,
            1
        )

        duration_minutes = journey["duration_minutes"]

        total_minutes = round(
            waiting_minutes + duration_minutes,
            1
        )

        prediction = journey.get("crowding")
        overall = (
            prediction.get("overall", {})
            if prediction else {}
        )

        level = overall.get("level", "unknown")
        evidence = overall.get(
            "evidence", "insufficient"
        )

        score = get_demand_score(prediction)

        alternatives.append({
            **journey,
            "waiting_minutes": waiting_minutes,
            "total_minutes": total_minutes,
            "crowding_level": level,
            "evidence": evidence,
            "demand_score": score,
            "reliable_comparison": score is not None,
            "fastest": False,
            "less_crowded": False,
            "comfort_recommendation": (
                "Insufficient comparable historical evidence"
            )
        })

    if not alternatives:
        return []

    # Rank by earliest arrival.
    alternatives.sort(
        key=lambda bus: (
            bus["total_minutes"],
            bus["waiting_minutes"]
        )
    )

    fastest = alternatives[0]
    fastest["fastest"] = True

    # Compare only buses on the same route,
    # with the same boarding and alighting stops.
    # Differences in route IDs and route patterns
    # should be evaluated before recommending.
    comparable = [
        bus
        for bus in alternatives
        if (
            bus["route"] == fastest["route"]
            and bus["from_stop"] == fastest["from_stop"]
            and bus["to_stop"] == fastest["to_stop"]
            and bus["reliable_comparison"]
        )
    ]

    baseline_score = fastest.get("demand_score")

    if baseline_score is not None:
        for bus in comparable:
            if bus["trip_id"] == fastest["trip_id"]:
                continue

            improvement = baseline_score - bus["demand_score"]

            # Require meaningful score improvement.
            if improvement >= 0.15:
                bus["less_crowded"] = True
                bus["comfort_recommendation"] = (
                    "Lower historical ticket demand "
                    "than the fastest comparable departure"
                )

    return alternatives
