from pathlib import Path

from backend.crowding.stop_matcher import GTFSStopMatcher


def _gtfs(tmp_path: Path, trips: str, stop_times: str) -> Path:
    (tmp_path / "stops.txt").write_text("stop_id,stop_name\nA,Alpha Terminal\nB,Beta Road\nC,Gamma Station\nD,Delta Stop\n")
    (tmp_path / "routes.txt").write_text("route_id,route_short_name,route_long_name\nR1,42,Route Forty Two\n")
    (tmp_path / "trips.txt").write_text("route_id,trip_id,direction_id\n" + trips)
    (tmp_path / "stop_times.txt").write_text("trip_id,stop_id,stop_sequence\n" + stop_times)
    return tmp_path


def test_numeric_stop_sequence_and_duplicate_scheduled_patterns(tmp_path):
    directory = _gtfs(tmp_path, "R1,t1,0\nR1,t2,0\n", "t1,A,10\nt1,B,2\nt1,C,30\nt2,A,10\nt2,B,2\nt2,C,30\n")
    matcher = GTFSStopMatcher(directory)
    # Numeric sorting makes Beta (2) precede Alpha (10), so B -> C is valid.
    result = matcher.match("42", "Beta Road", "Gamma Station")
    assert result["matched"] is True
    assert result["board_index"] == 0
    assert result["pattern_trip_count"] == 2
    assert len(matcher.patterns) == 1


def test_preserves_ambiguous_route_patterns(tmp_path):
    directory = _gtfs(tmp_path, "R1,t1,0\nR1,t2,0\n", "t1,A,1\nt1,B,2\nt1,C,3\nt2,A,1\nt2,D,2\nt2,C,3\n")
    result = GTFSStopMatcher(directory).match("42", "Alpha Terminal", "Gamma Station")
    assert result == {"matched": False, "reason": "ambiguous_exact_match", "candidate_count": 2}


def test_exact_match_precedes_fuzzy_fallback(tmp_path):
    directory = _gtfs(tmp_path, "R1,t1,0\n", "t1,A,1\nt1,B,2\nt1,C,3\n")
    result = GTFSStopMatcher(directory).match("42", "Alpha Terminal", "Beta Road")
    assert result["matched"] is True
    assert result["match_confidence"] == 1.0
