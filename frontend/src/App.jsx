
import { useRef, useState } from "react";
import "./App.css";
import CrowdLens from "./components/CrowdLens";

const API =
  import.meta.env.VITE_JOURNEY_API_URL ||
  import.meta.env.VITE_API_BASE_URL ||
  "http://127.0.0.1:8001";

const formatTime = (time) =>
  time ? String(time).slice(0, 5) : "--:--";

const readable = (value) =>
  String(value || "unknown").replaceAll("_", " ");

const demandLevel = (bus) =>
  bus?.crowding_level ||
  bus?.crowding?.overall?.level ||
  "unknown";

const evidenceLevel = (bus) =>
  bus?.evidence ||
  bus?.crowding?.overall?.evidence ||
  "insufficient";

const minutes = (value) =>
  value == null ? "—" : `${value} min`;

function Icon({ name, size = 20 }) {
  const paths = {
    bus: (
      <>
        <rect x="5" y="3" width="14" height="15" rx="3" />
        <path d="M5 10h14M8 21v-3m8 3v-3M8 14h.01M16 14h.01" />
      </>
    ),
    route: (
      <>
        <circle cx="5" cy="17" r="2" />
        <circle cx="19" cy="5" r="2" />
        <path d="M7 17h6a4 4 0 0 0 0-8h-2a3 3 0 0 1 0-6h6" />
      </>
    ),
    search: (
      <>
        <circle cx="10.5" cy="10.5" r="6.5" />
        <path d="m16 16 5 5" />
      </>
    ),
    clock: (
      <>
        <circle cx="12" cy="12" r="9" />
        <path d="M12 7v5l3 2" />
      </>
    ),
    calendar: (
      <>
        <rect x="3" y="5" width="18" height="16" rx="2" />
        <path d="M7 3v4m10-4v4M3 10h18" />
      </>
    ),
    pin: (
      <>
        <path d="M20 10c0 5-8 12-8 12S4 15 4 10a8 8 0 1 1 16 0Z" />
        <circle cx="12" cy="10" r="2.5" />
      </>
    ),
    arrow: <path d="M4 12h16m-6-6 6 6-6 6" />,
    chevron: <path d="m9 6 6 6-6 6" />,
    scales: (
      <path d="M12 3v18M4 7h16M7 7l-4 7h8L7 7Zm10 0-4 7h8l-4-7ZM9 21h6" />
    ),
    chart: (
      <>
        <rect x="3" y="13" width="4" height="8" rx="1" />
        <rect x="10" y="8" width="4" height="13" rx="1" />
        <rect x="17" y="3" width="4" height="18" rx="1" />
      </>
    ),
    info: (
      <>
        <circle cx="12" cy="12" r="9" />
        <path d="M12 11v6m0-10h.01" />
      </>
    ),
    home: (
      <>
        <path d="m3 10 9-7 9 7M5 9v12h14V9" />
        <path d="M9 21v-8h6v8" />
      </>
    ),
  };

  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.8"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
    >
      {paths[name] || paths.bus}
    </svg>
  );
}

function DemandDots({ level }) {
  const normalized = String(level || "unknown").toLowerCase();

  return (
    <span
      className={`demand-dots ${normalized}`}
      aria-hidden="true"
    >
      {[0, 1, 2, 3, 4].map((n) => (
        <i key={n} />
      ))}
    </span>
  );
}

function Demand({ level, evidence }) {
  const normalized = String(level || "unknown").toLowerCase();

  const labels = {
    low: "Lower demand",
    medium: "Moderate demand",
    high: "High demand",
    unknown: "Demand unavailable",
  };

  return (
    <span className="demand-indicator">
      <DemandDots level={normalized} />

      <span>
        <strong>
          {labels[normalized] || readable(normalized)}
        </strong>

        <small>
          {readable(evidence || "insufficient")} evidence
        </small>
      </span>
    </span>
  );
}

function Heading({ icon, title, description }) {
  return (
    <div className="section-heading">
      <span className="heading-icon">
        <Icon name={icon} size={25} />
      </span>

      <div>
        <h2>{title}</h2>
        <p>{description}</p>
      </div>
    </div>
  );
}

function todayIST() {
  const parts = new Intl.DateTimeFormat("en-GB", {
    timeZone: "Asia/Kolkata",
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
  }).formatToParts(new Date());

  const get = (type) =>
    parts.find((part) => part.type === type)?.value;

  return `${get("year")}-${get("month")}-${get("day")}`;
}

function App() {
  const [fromQuery, setFromQuery] = useState("");
  const [toQuery, setToQuery] = useState("");

  const [fromStop, setFromStop] = useState(null);
  const [toStop, setToStop] = useState(null);

  const [fromResults, setFromResults] = useState([]);
  const [toResults, setToResults] = useState([]);

  const [travelDate, setTravelDate] = useState(todayIST);
  const [departureTime, setDepartureTime] = useState("08:00");

  const [journeys, setJourneys] = useState([]);
  const [alternatives, setAlternatives] = useState([]);

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [searched, setSearched] = useState(false);

  const [selectedTrip, setSelectedTrip] = useState(null);
  const [showDetails, setShowDetails] = useState(false);

  const stopRequests = useRef({});
  const journeyRequest = useRef(null);

  function resetResults() {
    journeyRequest.current?.abort();

    setLoading(false);
    setSearched(false);
    setJourneys([]);
    setAlternatives([]);
    setSelectedTrip(null);
    setShowDetails(false);
    setError("");
  }

  // Bus stop autocomplete
  async function searchStops(query, type) {
    stopRequests.current[type]?.abort();

    if (type === "from") {
      setFromQuery(query);
      setFromStop(null);
      setFromResults([]);
    } else {
      setToQuery(query);
      setToStop(null);
      setToResults([]);
    }

    resetResults();

    if (query.trim().length < 2) return;

    const controller = new AbortController();
    stopRequests.current[type] = controller;

    try {
      const response = await fetch(
        `${API}/v1/stops?query=${encodeURIComponent(query)}`,
        { signal: controller.signal }
      );

      if (!response.ok) {
        throw new Error("Stop search failed");
      }

      const data = await response.json();

      if (controller.signal.aborted) return;

      if (type === "from") {
        setFromResults(data.stops || []);
      } else {
        setToResults(data.stops || []);
      }
    } catch (err) {
      if (err.name !== "AbortError") {
        setError("Could not connect to the backend.");
      }
    }
  }

  function selectStop(stop, type) {
    stopRequests.current[type]?.abort();

    if (type === "from") {
      setFromStop(stop);
      setFromQuery(stop.stop_name);
      setFromResults([]);
    } else {
      setToStop(stop);
      setToQuery(stop.stop_name);
      setToResults([]);
    }

    resetResults();
  }

  // Existing journey API
  async function findJourneys(event) {
    event.preventDefault();

    if (!fromStop || !toStop) {
      setError(
        "Please select both stops from the suggestions."
      );
      return;
    }

    if (
      String(fromStop.stop_id) ===
      String(toStop.stop_id)
    ) {
      setError(
        "Starting and destination stops must be different."
      );
      return;
    }

    resetResults();

    const controller = new AbortController();
    journeyRequest.current = controller;

    setLoading(true);

    const params = new URLSearchParams({
      from_stop_id: fromStop.stop_id,
      to_stop_id: toStop.stop_id,
      departure_time: departureTime,
      travel_date: travelDate,
    });

    try {
      const response = await fetch(
        `${API}/v1/journeys?${params.toString()}`,
        { signal: controller.signal }
      );

      if (!response.ok) {
        throw new Error("Journey search failed");
      }

      const data = await response.json();

      if (controller.signal.aborted) return;

      const allJourneys = data.journeys || [];
      const allAlternatives = data.alternatives || [];

      const first =
        allAlternatives.find((bus) => bus.fastest) ||
        allAlternatives[0] ||
        allJourneys[0];

      setJourneys(allJourneys);
      setAlternatives(allAlternatives);
      setSelectedTrip(first?.trip_id ?? null);
      setSearched(true);
    } catch (err) {
      if (err.name !== "AbortError") {
        setError(
          "Journey search failed. Check that FastAPI is running."
        );
      }
    } finally {
      if (!controller.signal.aborted) {
        setLoading(false);
      }
    }
  }

  const buses = journeys.length
    ? journeys.map((journey) => {
        const alternative = alternatives.find(
          (bus) => bus.trip_id === journey.trip_id
        );

        return {
          ...journey,
          ...alternative,
          crowding:
            journey.crowding ?? alternative?.crowding,
        };
      })
    : alternatives;

  const fastestBus =
    buses.find((bus) => bus.fastest) ||
    [...buses].sort((a, b) =>
      String(a.arrival || "").localeCompare(
        String(b.arrival || "")
      )
    )[0] ||
    null;

  const selectedBus =
    buses.find((bus) => bus.trip_id === selectedTrip) ||
    fastestBus;

  const lowerDemandBuses = buses.filter(
    (bus) => bus.less_crowded === true
  );

  const calmerBus = lowerDemandBuses[0] || null;

  const orderedBuses = [...buses].sort((a, b) => {
    if (a.trip_id === b.trip_id) return 0;
    if (a.trip_id === fastestBus?.trip_id) return -1;
    if (b.trip_id === fastestBus?.trip_id) return 1;
    return String(a.arrival || "").localeCompare(
      String(b.arrival || "")
    );
  });

  function navigateTo(id) {
    document.getElementById(id)?.scrollIntoView({
      behavior: "smooth",
      block: "start",
    });
  }

  function renderStopField(type, title, placeholder) {
    const from = type === "from";
    const query = from ? fromQuery : toQuery;
    const stops = from ? fromResults : toResults;

    return (
      <div className="field stop-field">
        <label htmlFor={`${type}-stop`}>
          <Icon name="pin" size={15} />
          {title}
        </label>

        <div className="input-wrap">
          <Icon name="pin" size={17} />

          <input
            id={`${type}-stop`}
            type="text"
            autoComplete="off"
            placeholder={placeholder}
            value={query}
            onChange={(event) =>
              searchStops(event.target.value, type)
            }
          />

          <span className="input-chevron">⌄</span>
        </div>

        {stops.length > 0 && (
          <div className="suggestions">
            {stops.map((stop) => (
              <button
                key={stop.stop_id}
                type="button"
                onClick={() => selectStop(stop, type)}
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
    );
  }

  return (
    <div className="app aaram-redesign">
      <a className="skip-link" href="#main-content">
        Skip to journey planner
      </a>

      {/* Navigation */}
      <header className="navbar">
        <button
          className="logo"
          type="button"
          onClick={() => navigateTo("main-content")}
          aria-label="AARAM AI home"
        >
          <span className="logo-mark">
            <Icon name="bus" size={24} />
          </span>

          <span>
            aaram<span className="logo-accent">.ai</span>
          </span>
        </button>

        <nav className="top-nav" aria-label="Navigation">
          <button
            type="button"
            className="active"
            onClick={() => navigateTo("journey-search")}
          >
            <Icon name="home" size={17} />
            Plan Journey
          </button>

          <button
            type="button"
            onClick={() => navigateTo("comfortshift")}
          >
            <Icon name="scales" size={17} />
            ComfortShift
          </button>

          <button
            type="button"
            onClick={() => navigateTo("crowdlens")}
          >
            <Icon name="chart" size={17} />
            CrowdLens
          </button>

          <button
            type="button"
            onClick={() => navigateTo("how-it-works")}
          >
            <Icon name="info" size={17} />
            How it Works
          </button>
        </nav>

        <span className="city-tag">
          <Icon name="pin" size={16} />
          Delhi
        </span>
      </header>

      <main className="container" id="main-content">
        {/* Existing hero image */}
        <section className="hero">
          <img
            src="/hero-banner.png"
            alt="Delhi Bus Planner. Your journey. Your comfort. Find buses, compare options and choose a calmer ride with AARAM AI."
            className="hero-banner-img"
          />
        </section>

        {/* Journey search */}
        <form
          className="search-card"
          id="journey-search"
          onSubmit={findJourneys}
        >
          <Heading
            icon="route"
            title="Plan your journey"
            description="Select your stops, time and travel date to find the best bus options."
          />

          <div className="input-grid">
            {renderStopField(
              "from",
              "From",
              "Search starting stop..."
            )}

            {renderStopField(
              "to",
              "To",
              "Search destination stop..."
            )}

            <div className="field">
              <label htmlFor="departure-time">
                <Icon name="clock" size={15} />
                Departure time
              </label>

              <input
                id="departure-time"
                type="time"
                value={departureTime}
                onChange={(event) => {
                  setDepartureTime(event.target.value);
                  resetResults();
                }}
                required
              />
            </div>

            <div className="field">
              <label htmlFor="travel-date">
                <Icon name="calendar" size={15} />
                Travel date
              </label>

              <input
                id="travel-date"
                type="date"
                value={travelDate}
                onChange={(event) => {
                  setTravelDate(event.target.value);
                  resetResults();
                }}
                required
              />
            </div>

            <button
              className="search-btn"
              type="submit"
              disabled={loading}
            >
              <Icon name="search" size={18} />

              {loading ? "Finding..." : "Find Journeys"}
            </button>
          </div>

          {error && (
            <p className="error" role="alert">
              {error}
            </p>
          )}
        </form>

        {/* Main results dashboard */}
        <section className="dashboard-grid">

          {/* LEFT: Available journeys */}
          <section className="results-panel">
            <Heading
              icon="bus"
              title="Available journeys"
              description={
                searched
                  ? `${buses.length} scheduled journeys between your selected stops.`
                  : "Find scheduled buses between your selected stops."
              }
            />

            <div className="panel-divider" />

            {loading ? (
              <div className="loading-state" role="status">
                <span className="spinner" />
                Finding available buses...
              </div>
            ) : !searched ? (
              <div className="empty-state">
                <span className="empty-icon">
                  <Icon name="bus" size={32} />
                </span>

                <h3>Where are you going?</h3>

                <p>
                  Select your starting and destination stops
                  to discover available buses.
                </p>
              </div>
            ) : buses.length === 0 ? (
              <div className="empty-state">
                <h3>No direct buses found</h3>

                <p>
                  Try a different stop or departure time.
                </p>
              </div>
            ) : (
              <div className="journey-list">
                {orderedBuses.map((bus) => (
                  <button
                    key={bus.trip_id}
                    type="button"
                    aria-pressed={
                      selectedBus?.trip_id === bus.trip_id
                    }
                    className={`journey-list-card ${
                      selectedBus?.trip_id === bus.trip_id
                        ? "selected"
                        : ""
                    }`}
                    onClick={() => {
                      setSelectedTrip(bus.trip_id);
                      setShowDetails(false);
                    }}
                  >
                    <span className="route-pill">
                      {bus.route}
                    </span>

                    <span className="journey-list-times">
                      <strong>
                        {formatTime(bus.departure)}
                        {" → "}
                        {formatTime(bus.arrival)}
                      </strong>

                      <small>
                        {minutes(bus.duration_minutes)} ride

                        {bus.waiting_minutes != null
                          ? ` · ${bus.waiting_minutes} min wait`
                          : ""}
                      </small>
                    </span>

                    <Demand
                      level={demandLevel(bus)}
                      evidence={evidenceLevel(bus)}
                    />

                    <span className="journey-list-arrow">
                      <Icon name="chevron" size={18} />
                    </span>
                  </button>
                ))}
              </div>
            )}

            {selectedBus && (
              <button
                type="button"
                className="view-journey-btn"
                onClick={() => {
                  setShowDetails(true);

                  requestAnimationFrame(() =>
                    navigateTo("journey-details")
                  );
                }}
              >
                View selected journey details
                <Icon name="arrow" size={16} />
              </button>
            )}
          </section>

          {/* RIGHT: ComfortShift and CrowdLens */}
          <div className="dashboard-secondary">

            <section
              className="insight-panel comfort-panel"
              id="comfortshift"
            >
              <Heading
                icon="scales"
                title="ComfortShift"
                description="Compare a departure with a lower-demand option."
              />

              {fastestBus ? (
                <>
                  <div className="comfort-comparison">
                    <div className="comparison-box current-bus">
                      <small>Earliest-arriving bus</small>

                      <div className="comparison-route">
                        <strong>{fastestBus.route}</strong>

                        <DemandDots
                          level={demandLevel(fastestBus)}
                        />
                      </div>

                      <span className="comparison-time">
                        {formatTime(fastestBus.departure)}
                        {" → "}
                        {formatTime(fastestBus.arrival)}
                      </span>
                    </div>

                    <span className="comparison-arrow">
                      <Icon name="arrow" size={21} />
                    </span>

                    <div
                      className={`comparison-box ${
                        calmerBus
                          ? "calmer-bus"
                          : "unavailable-bus"
                      }`}
                    >
                      <small>Lower-demand option</small>

                      {calmerBus ? (
                        <>
                          <div className="comparison-route">
                            <strong>{calmerBus.route}</strong>

                            <DemandDots
                              level={demandLevel(calmerBus)}
                            />
                          </div>

                          <span className="comparison-time">
                            {formatTime(calmerBus.departure)}
                            {" → "}
                            {formatTime(calmerBus.arrival)}
                          </span>
                        </>
                      ) : (
                        <strong>Not identified</strong>
                      )}
                    </div>
                  </div>

                  <p className="comparison-note">
                    {fastestBus.crowding_status ===
                    "service_unavailable"
                      ? "Crowd prediction service unavailable."
                      : calmerBus
                      ? calmerBus.comfort_recommendation ||
                        "An evidence-backed lower-demand alternative is available."
                      : "No reliably lower-demand alternative found for this search."}
                  </p>
                </>
              ) : (
                <div className="insight-placeholder">
                  Search for a journey to compare bus
                  departures and historical demand.
                </div>
              )}
            </section>

            <section
              className="insight-panel crowd-panel"
              id="crowdlens"
            >
              <Heading
                icon="chart"
                title="CrowdLens"
                description={
                  selectedBus
                    ? `Historical demand along route ${selectedBus.route}.`
                    : "Historical crowding patterns along the route."
                }
              />

              <CrowdLens
                prediction={selectedBus?.crowding}
                compact
              />
            </section>
          </div>
        </section>

        {/* Detailed journey summary */}
        {selectedBus && showDetails && (
          <section
            className="details-panel"
            id="journey-details"
          >
            <div className="details-header">
              <Heading
                icon="info"
                title="Journey details"
                description="Scheduled timings and historical demand evidence."
              />

              <button
                type="button"
                className="details-toggle"
                onClick={() => setShowDetails(false)}
              >
                Hide details
              </button>
            </div>

            <article className="journey-card">
              <div className="journey-top">
                <span className="route-pill">
                  {selectedBus.route}
                </span>

                <Demand
                  level={demandLevel(selectedBus)}
                  evidence={evidenceLevel(selectedBus)}
                />
              </div>

              <div className="journey-times">
                <div>
                  <strong>
                    {formatTime(selectedBus.departure)}
                  </strong>

                  <p>{selectedBus.from_stop}</p>
                </div>

                <span className="travel-line">→</span>

                <div>
                  <strong>
                    {formatTime(selectedBus.arrival)}
                  </strong>

                  <p>{selectedBus.to_stop}</p>
                </div>
              </div>

              <div className="summary-metrics">
                <div>
                  Waiting time
                  <b>{minutes(selectedBus.waiting_minutes)}</b>
                </div>

                <div>
                  Travel time
                  <b>{minutes(selectedBus.duration_minutes)}</b>
                </div>

                <div>
                  Total time
                  <b>{minutes(selectedBus.total_minutes)}</b>
                </div>
              </div>

              {selectedBus.fastest && (
                <p className="fastest-label">
                  Earliest-arriving scheduled journey
                </p>
              )}

              {selectedBus.less_crowded && (
                <p className="less-crowded-label">
                  Evidence-backed lower historical demand
                </p>
              )}

              {selectedBus.comfort_recommendation && (
                <p className="comfort-note">
                  {selectedBus.comfort_recommendation}
                </p>
              )}

              <CrowdLens
                prediction={selectedBus.crowding}
              />
            </article>
          </section>
        )}

        {/* Data explanation */}
        <section
          className="about-panel"
          id="how-it-works"
        >
          <Icon name="info" size={18} />

          <div>
            <strong>How AARAM AI works</strong>

            <p>
              AARAM AI combines Delhi GTFS bus schedules
              with historical ticket-demand predictions.
              Times are scheduled estimates, not live vehicle
              tracking. CrowdLens does not confirm actual
              occupancy or seat availability.
            </p>
          </div>
        </section>
      </main>

      <footer className="site-footer">
        <strong>
          aaram<span>.ai</span>
        </strong>

        <span>Smarter journeys. Calmer cities.</span>

        <small>
          Delhi GTFS · Historical demand insights
        </small>
      </footer>
    </div>
  );
}

export default App;
