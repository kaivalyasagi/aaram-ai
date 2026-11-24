
function CrowdLens({ prediction, compact = false }) {
  const segments = Array.isArray(prediction?.segments)
    ? prediction.segments
    : [];

  const colors = {
    low: "#35c76b",
    medium: "#f5bd28",
    high: "#eb5143",
    unknown: "#b8c2d3",
  };

  const heights = {
    low: 18,
    medium: 28,
    high: 40,
    unknown: 13,
  };

  const labels = {
    low: "Lower",
    medium: "Moderate",
    high: "Higher",
    unknown: "Unknown",
  };

  function normalize(value) {
    const level = String(value || "unknown").toLowerCase();

    return Object.hasOwn(colors, level)
      ? level
      : "unknown";
  }

  const level = normalize(prediction?.overall?.level);

  const evidence =
    prediction?.overall?.evidence || "insufficient";

  return (
    <div
      className={`crowdlens ${compact ? "compact" : ""}`}
    >
      {!compact && (
        <div className="crowdlens-title">
          <strong>CrowdLens — Segment predictions</strong>
        </div>
      )}

      {segments.length === 0 ? (
        <div className="insight-placeholder">
          {prediction
            ? "Insufficient segment data for this journey."
            : compact
            ? "Select an available bus to view its historical crowd-demand pattern, where data is available."
            : "Historical crowd predictions are unavailable for this journey."}
        </div>
      ) : (
        <>
          <div className="crowdlens-title">
            <span className="crowdlens-status">
              Demand: {labels[level]}
            </span>

            <span className="crowdlens-status">
              Evidence: {evidence}
            </span>
          </div>

          {/* Colored segment visualization */}
          <div
            className="crowdlens-bar"
            role="img"
            aria-label={`Historical segment demand: ${segments
              .map((segment) => labels[normalize(segment.level)])
              .join(", ")}`}
          >
            {segments.map((segment, index) => {
              const segmentLevel = normalize(segment.level);

              return (
                <div
                  key={`${segment.from_stop_id}-${segment.to_stop_id}-${index}`}
                  className="crowdlens-segment"
                  style={{
                    backgroundColor: colors[segmentLevel],
                    height: `${heights[segmentLevel]}px`,
                  }}
                  title={
                    `Stop ${segment.from_stop_id} → ` +
                    `Stop ${segment.to_stop_id}\n` +
                    `Demand: ${labels[segmentLevel]}\n` +
                    `Observed days: ${segment.observed_days ?? 0}\n` +
                    `Evidence: ${segment.evidence || "insufficient"}`
                  }
                />
              );
            })}
          </div>

          {/* Chart legend */}
          <div className="crowdlens-legend">
            {Object.entries(labels).map(([key, label]) => (
              <span key={key}>
                <i
                  className="legend-dot"
                  style={{
                    backgroundColor: colors[key],
                  }}
                />
                {label}
              </span>
            ))}
          </div>

          {/* Detailed segment evidence */}
          {!compact && (
            <details className="crowdlens-details">
              <summary>
                View all {segments.length} stop segments
              </summary>

              <div className="segment-list">
                {segments.map((segment, index) => {
                  const segmentLevel = normalize(segment.level);

                  return (
                    <div
                      className="crowdlens-detail"
                      key={`${segment.from_stop_id}-${segment.to_stop_id}-${index}`}
                    >
                      <span>
                        Stop {segment.from_stop_id}
                        {" → "}
                        Stop {segment.to_stop_id}
                      </span>

                      <span>
                        <strong
                          style={{
                            color:
                              segmentLevel === "low"
                                ? "#166534"
                                : segmentLevel === "medium"
                                ? "#926600"
                                : segmentLevel === "high"
                                ? "#b42318"
                                : "#64748b",
                          }}
                        >
                          {labels[segmentLevel]} demand
                        </strong>

                        {" · "}

                        {segment.observed_days ?? 0} observed days

                        {" · Evidence: "}

                        {segment.evidence || "insufficient"}
                      </span>
                    </div>
                  );
                })}
              </div>
            </details>
          )}
        </>
      )}

      <p className="crowdlens-description">
        Historical ticket demand only. Not live occupancy
        or guaranteed seat availability.
      </p>
    </div>
  );
}

export default CrowdLens;
