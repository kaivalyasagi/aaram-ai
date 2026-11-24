
function CrowdLens({ prediction }) {
  const segments = prediction?.segments || [];

  const colors = {
    low: "#22c55e",
    medium: "#f59e0b",
    high: "#ef4444",
    unknown: "#64748b",
  };

  if (!prediction || segments.length === 0) {
    return (
      <div className="crowdlens">
        <div className="crowdlens-title">
          <strong>📊 CrowdLens</strong>
          <span>Insufficient data</span>
        </div>

        <p className="crowdlens-description">
          Historical crowd predictions are unavailable
          for this journey.
        </p>
      </div>
    );
  }

  const level = prediction.overall?.level || "unknown";
  const evidence = prediction.overall?.evidence || "insufficient";

  return (
    <div className="crowdlens">
      <div className="crowdlens-title">
        <strong>📊 CrowdLens</strong>

        <span>
          Demand: {level.toUpperCase()}
          {" | "}
          Evidence: {evidence}
        </span>
      </div>

      <div className="crowdlens-bar">
        {segments.map((segment, index) => (
          <div
            key={`${segment.from_stop_id}-${segment.to_stop_id}-${index}`}
            className="crowdlens-segment"
            style={{
              backgroundColor:
                colors[segment.level] || colors.unknown,
            }}
            title={`${segment.from_stop_id} to ${segment.to_stop_id}`}
          />
        ))}
      </div>

      <div className="crowdlens-legend">
        <span>🟢 Low</span>
        <span>🟡 Medium</span>
        <span>🔴 High</span>
        <span>⚪ Unknown</span>
      </div>

      <div className="crowdlens-details">
        {segments.map((segment, index) => (
          <div
            className="crowdlens-detail"
            key={index}
          >
            <span>
              Stop {segment.from_stop_id} →
              Stop {segment.to_stop_id}
            </span>

            <span>
              {segment.level.toUpperCase()}
              {" • "}
              {segment.observed_days ?? 0} observed days
              {" • "}
              Evidence: {segment.evidence}
            </span>
          </div>
        ))}
      </div>

      <p className="crowdlens-description">
        Relative historical ticket demand only.
        Not live occupancy or guaranteed seat availability.
      </p>
    </div>
  );
}

export default CrowdLens;
