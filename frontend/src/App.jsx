
import { useState } from "react";
import "./App.css";
import CrowdLens from "./components/CrowdLens";

const API = "http://127.0.0.1:8001";

function App() {
  const [fromQuery, setFromQuery] = useState("");
  const [toQuery, setToQuery] = useState("");

  const [fromStop, setFromStop] = useState(null);
  const [toStop, setToStop] = useState(null);

  const [fromResults, setFromResults] = useState([]);
  const [toResults, setToResults] = useState([]);

  const [travelDate, setTravelDate] = useState(
    new Intl.DateTimeFormat("en-CA", {
      timeZone: "Asia/Kolkata",
      year: "numeric",
      month: "2-digit",
      day: "2-digit",
    }).format(new Date())
  );

  const [departureTime, setDepartureTime] = useState("08:00");

  const [journeys, setJourneys] = useState([]);
  const [alternatives, setAlternatives] = useState([]);

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [searched, setSearched] = useState(false);

  // Step 35.4: Show detailed cards only when requested
  const [showDetails, setShowDetails] = useState(false);

  // ---------------------------------------
  // Search for bus stops
  // ---------------------------------------
  async function searchStops(query, type) {
    if (type === "from") {
      setFromQuery(query);
      setFromStop(null);
      setFromResults([]);
    } else {
      setToQuery(query);
      setToStop(null);
      setToResults([]);
    }

    setSearched(false);
    setJourneys([]);
    setAlternatives([]);
    setError("");

    if (query.trim().length < 2) {
      return;
    }

    try {
      const response = await fetch(
        `${API}/v1/stops?query=${encodeURIComponent(query)}`
      );

      if (!response.ok) {
        throw new Error("Stop search failed");
      }

      const data = await response.json();

      if (type === "from") {
        setFromResults(data.stops || []);
      } else {
        setToResults(data.stops || []);
      }
    } catch {
      setError("Could not connect to the backend.");
    }
  }

  // ---------------------------------------
  // Select a bus stop
  // ---------------------------------------
  function selectStop(stop, type) {
    if (type === "from") {
      setFromStop(stop);
      setFromQuery(stop.stop_name);
      setFromResults([]);
    } else {
      setToStop(stop);
      setToQuery(stop.stop_name);
      setToResults([]);
    }

    setError("");
  }

  // ---------------------------------------
  // Find Journeys + ComfortShift
  // ---------------------------------------
  async function findJourneys(event) {
    event.preventDefault();

    if (!fromStop || !toStop) {
      setError(
        "Please select both stops from the suggestions."
      );
      return;
    }

    if (fromStop.stop_id === toStop.stop_id) {
      setError(
        "Starting and destination stops must be different."
      );
      return;
    }

    setLoading(true);
    setError("");
    setJourneys([]);
    setAlternatives([]);
    setSearched(false);
    setShowDetails(false);

    const params = new URLSearchParams({
      from_stop_id: fromStop.stop_id,
      to_stop_id: toStop.stop_id,
      departure_time: departureTime,
      travel_date: travelDate,
    });

    try {
      // Only one API request.
      const response = await fetch(
        `${API}/v1/journeys?${params.toString()}`
      );

      if (!response.ok) {
        throw new Error("Journey search failed");
      }

      const data = await response.json();

      setJourneys(data.journeys || []);
      setAlternatives(data.alternatives || []);
      setSearched(true);
    } catch {
      setError(
        "Journey search failed. Check that FastAPI is running."
      );
    } finally {
      setLoading(false);
    }
  }

  // ---------------------------------------
  // Select earliest-arrival journey
  // ---------------------------------------
  const fastestBus =
    alternatives.find((bus) => bus.fastest) ||
    alternatives[0] ||
    null;

  const lowerDemandBuses = alternatives.filter(
    (bus) => bus.less_crowded === true
  );

  // ---------------------------------------
  // React UI
  // ---------------------------------------
  return (
    <div className="app">
      {/* Navigation Bar */}
      <header className="navbar">
        <div className="logo">
          🚌 AARAM<span>AI</span>
        </div>

        <div className="nav-label">
          Delhi Smart Bus Journey Planner
        </div>
      </header>

      <main className="container">
        {/* Hero Section */}
        <section className="hero">
          <div className="eyebrow">
            DELHI BUS HACKATHON
          </div>

          <h1>
            Travel smarter.
            <br />
            <span>Travel with Aaram.</span>
          </h1>

          <p>
            Find scheduled bus journeys across Delhi
            with historical ticket-demand insights.
          </p>
        </section>

        {/* ---------------------------------------
            Journey Search Form
        --------------------------------------- */}
        <form
          className="search-card"
          onSubmit={findJourneys}
        >
          <h2>Plan Your Journey</h2>

          <div className="input-grid">
            {/* Starting Stop */}
            <div className="field stop-field">
              <label>📍 Starting Stop</label>

              <input
                placeholder="Search starting bus stop"
                value={fromQuery}
                onChange={(e) =>
                  searchStops(e.target.value, "from")
                }
              />

              {fromResults.length > 0 && (
                <div className="suggestions">
                  {fromResults.map((stop) => (
                    <button
                      type="button"
                      key={stop.stop_id}
                      onClick={() =>
                        selectStop(stop, "from")
                      }
                    >
                      {stop.stop_name}

                      <small>
                        Stop ID: {stop.stop_id}
                      </small>
                    </button>
                  ))}
                </div>
              )}
            </div>

            {/* Destination Stop */}
            <div className="field stop-field">
              <label>🏁 Destination Stop</label>

              <input
                placeholder="Search destination bus stop"
                value={toQuery}
                onChange={(e) =>
                  searchStops(e.target.value, "to")
                }
              />

              {toResults.length > 0 && (
                <div className="suggestions">
                  {toResults.map((stop) => (
                    <button
                      type="button"
                      key={stop.stop_id}
                      onClick={() =>
                        selectStop(stop, "to")
                      }
                    >
                      {stop.stop_name}

                      <small>
                        Stop ID: {stop.stop_id}
                      </small>
                    </button>
                  ))}
                </div>
              )}
            </div>

            {/* Travel Date */}
            <div className="field">
              <label>📅 Travel Date</label>

              <input
                type="date"
                value={travelDate}
                onChange={(e) => {
                  setTravelDate(e.target.value);
                  setSearched(false);
                }}
                required
              />
            </div>

            {/* Departure Time */}
            <div className="field">
              <label>🕒 Departure Time</label>

              <input
                type="time"
                value={departureTime}
                onChange={(e) => {
                  setDepartureTime(e.target.value);
                  setSearched(false);
                }}
                required
              />
            </div>
          </div>

          {/* Error Message */}
          {error && (
            <p className="error">
              {error}
            </p>
          )}

          <button
            type="submit"
            className="search-btn"
            disabled={loading}
          >
            {loading
              ? "Searching buses..."
              : "Find Bus Journeys →"}
          </button>
        </form>

        {/* ---------------------------------------
            Search Results
        --------------------------------------- */}
        {searched && (
          <>
            {/* Result Count */}
            <section className="results">
              <h2>🚌 Your Journey Options</h2>

              <p className="result-count">
                {journeys.length} scheduled journey
                options found
              </p>

              {journeys.length === 0 && (
                <div className="empty">
                  No direct scheduled buses found.
                  Try another stop or departure time.
                </div>
              )}
            </section>

            {/* ---------------------------------------
                Quick Journey Summary
            --------------------------------------- */}
            {fastestBus && (
              <section className="comfort-section">
                <div className="comfort-heading">
                  <div>
                    <h2>⚡ Quick Journey Summary</h2>
                    <p className="comfort-description">
                      Your earliest-arriving scheduled bus.
                    </p>
                  </div>
                </div>

                <div className="comfort-card">
                  <div className="fastest-label">
                    ⚡ Earliest arrival
                  </div>

                  <div className="comfort-route">
                    🚌 {fastestBus.route}
                  </div>

                  <h3>
                    {fastestBus.departure.slice(0, 5)}
                    {" → "}
                    {fastestBus.arrival.slice(0, 5)}
                  </h3>

                  <p>
                    Boarding:{" "}
                    <strong>
                      {fastestBus.from_stop}
                    </strong>
                  </p>

                  <p>
                    Destination:{" "}
                    <strong>
                      {fastestBus.to_stop}
                    </strong>
                  </p>

                  <p>
                    Waiting time:{" "}
                    <strong>
                      {fastestBus.waiting_minutes} min
                    </strong>
                  </p>

                  <p>
                    Travel time:{" "}
                    <strong>
                      {fastestBus.duration_minutes} min
                    </strong>
                  </p>

                  <p>
                    Total elapsed time:{" "}
                    <strong>
                      {fastestBus.total_minutes} min
                    </strong>
                  </p>

                  <div
                    className={
                      `crowd-level crowd-${
                        fastestBus.crowding_level || "unknown"
                      }`
                    }
                  >
                    Historical demand:{" "}
                    {(fastestBus.crowding_level || "unknown")
                      .toUpperCase()}
                  </div>

                  <p className="comfort-evidence">
                    Evidence:{" "}
                    <strong>
                      {fastestBus.evidence || "insufficient"}
                    </strong>
                  </p>

                  <p className="comfort-note">
                    {fastestBus.crowding_status ===
                    "service_unavailable"
                      ? "Crowd prediction service is unavailable. Timetable results are still available."
                      : fastestBus.comfort_recommendation}
                  </p>
                </div>

                {/* Evidence-backed alternatives */}
                {lowerDemandBuses.length > 0 && (
                  <p className="comfort-description">
                    🌿 {lowerDemandBuses.length} lower-demand
                    alternative(s) identified.
                    Compare their departure times below.
                  </p>
                )}
              </section>
            )}

            {/* ---------------------------------------
                ComfortShift Alternatives
            --------------------------------------- */}
            {alternatives.length > 0 && (
              <section className="comfort-section">
                <div className="comfort-heading">
                  <div>
                    <h2>⏱ ComfortShift</h2>

                    <p className="comfort-description">
                      Compare scheduled departures,
                      waiting times and historical demand.
                    </p>
                  </div>
                </div>

                <div className="comfort-grid">
                  {alternatives.map((bus) => (
                    <div
                      className="comfort-card"
                      key={bus.trip_id}
                    >
                      <div className="comfort-route">
                        🚌 {bus.route}
                      </div>

                      <h3>
                        {bus.departure.slice(0, 5)}
                        {" → "}
                        {bus.arrival.slice(0, 5)}
                      </h3>

                      <p>
                        Waiting time:{" "}
                        <strong>
                          {bus.waiting_minutes} min
                        </strong>
                      </p>

                      <p>
                        Travel time:{" "}
                        <strong>
                          {bus.duration_minutes} min
                        </strong>
                      </p>

                      <p>
                        Total elapsed time:{" "}
                        <strong>
                          {bus.total_minutes} min
                        </strong>
                      </p>

                      <div
                        className={
                          `crowd-level crowd-${
                            bus.crowding_level || "unknown"
                          }`
                        }
                      >
                        Historical demand:{" "}
                        {(bus.crowding_level || "unknown")
                          .toUpperCase()}
                      </div>

                      <p className="comfort-evidence">
                        Evidence:{" "}
                        <strong>
                          {bus.evidence || "insufficient"}
                        </strong>
                      </p>

                      {bus.fastest && (
                        <div className="fastest-label">
                          ⚡ Earliest arrival
                        </div>
                      )}

                      {bus.less_crowded && (
                        <div className="less-crowded-label">
                          🌿 Lower historical demand
                        </div>
                      )}

                      <p className="comfort-note">
                        {bus.crowding_status ===
                        "service_unavailable"
                          ? "Crowd prediction service unavailable."
                          : bus.comfort_recommendation}
                      </p>
                    </div>
                  ))}
                </div>
              </section>
            )}

            {/* ---------------------------------------
                Expandable Detailed Journeys
            --------------------------------------- */}
            {journeys.length > 0 && (
              <section className="results">
                <h2>📊 Detailed Journey Predictions</h2>

                <p className="result-count">
                  View individual CrowdLens predictions
                  and stop-segment evidence.
                </p>

                <button
                  type="button"
                  className="search-btn"
                  onClick={() =>
                    setShowDetails(!showDetails)
                  }
                >
                  {showDetails
                    ? "Hide Detailed Journeys ▲"
                    : `View All ${journeys.length} Detailed Journeys ▼`}
                </button>

                {showDetails &&
                  journeys.map((journey) => (
                    <div
                      className="journey-card"
                      key={journey.trip_id}
                    >
                      <div className="journey-top">
                        <span className="bus-number">
                          🚌 {journey.route}
                        </span>

                        <span className="duration">
                          {journey.duration_minutes} min
                        </span>
                      </div>

                      <div className="journey-times">
                        <div>
                          <strong>
                            {journey.departure.slice(0, 5)}
                          </strong>

                          <p>{journey.from_stop}</p>
                        </div>

                        <div className="travel-line">
                          →
                        </div>

                        <div>
                          <strong>
                            {journey.arrival.slice(0, 5)}
                          </strong>

                          <p>{journey.to_stop}</p>
                        </div>
                      </div>

                      <div className="journey-bottom">
                        <span>
                          Scheduled GTFS journey
                        </span>

                        <span>
                          Historical demand:{" "}
                          {journey.crowding?.overall?.level ??
                            "Unknown"}
                          {" | "}
                          Evidence:{" "}
                          {journey.crowding?.overall?.evidence ??
                            "Insufficient"}
                        </span>
                      </div>

                      {journey.crowding_status ===
                        "service_unavailable" && (
                        <p className="comfort-note">
                          Crowd prediction service unavailable.
                        </p>
                      )}

                      <CrowdLens
                        prediction={journey.crowding}
                      />
                    </div>
                  ))}
              </section>
            )}
          </>
        )}
      </main>

      {/* Footer */}
      <footer>
        AARAM AI • Delhi Bus Hackathon •
        Static GTFS timetable • Historical demand only
      </footer>
    </div>
  );
}

export default App;
