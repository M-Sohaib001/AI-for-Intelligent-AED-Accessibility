"use client";

import { useState, useCallback } from "react";
import dynamic from "next/dynamic";

import SafetyBanner from "@/components/SafetyBanner";
import Results from "@/components/Results";
import AbstainState from "@/components/AbstainState";

import { fixture_normal } from "@/fixtures";
import type { RankResponse, RankAedsRequest, RankedResult } from "@/types";

// RouteMap uses Leaflet (browser-only) – must be dynamically imported
const RouteMap = dynamic(() => import("@/components/RouteMap"), { ssr: false });

// ---------------------------------------------------------------------------
// Config – flip NEXT_PUBLIC_USE_FIXTURES=false + set NEXT_PUBLIC_API_BASE
// when the backend is running. Zero code change required.
// ---------------------------------------------------------------------------
const USE_FIXTURES = process.env.NEXT_PUBLIC_USE_FIXTURES === "true";
const API_BASE = process.env.NEXT_PUBLIC_API_BASE ?? "http://localhost:8000";

// ---------------------------------------------------------------------------
// API call – POST /rank_aeds with { start_lat, start_lon, datetime }
// Returns the real RankResponse from backend/main.py
// ---------------------------------------------------------------------------
async function fetchAeds(req: RankAedsRequest): Promise<RankResponse> {
  if (USE_FIXTURES) {
    await new Promise((r) => setTimeout(r, 700));
    return fixture_normal;
  }

  let res: Response;
  try {
    res = await fetch(`${API_BASE}/rank_aeds`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(req),
    });
  } catch (e) {
    // Network error – return a synthetic abstain response
    return {
      abstained: true,
      abstain_reason: "NO_FEASIBLE_AED",
      safety_banner:
        "Prototype for planning and simulation only — not for emergency use. In an emergency in Singapore, call 995 immediately and follow SCDF instructions.",
      ranked: [],
      baseline: [],
    };
  }

  if (!res.ok) {
    return {
      abstained: true,
      abstain_reason: "NO_FEASIBLE_AED",
      safety_banner:
        "Prototype for planning and simulation only — not for emergency use. In an emergency in Singapore, call 995 immediately and follow SCDF instructions.",
      ranked: [],
      baseline: [],
    };
  }

  return res.json() as Promise<RankResponse>;
}

// ---------------------------------------------------------------------------
// Main page
// ---------------------------------------------------------------------------
export default function Home() {
  // ── Form state ──────────────────────────────────────────────────────────
  const [lat, setLat] = useState("");
  const [lon, setLon] = useState("");
  const [datetime, setDatetime] = useState(() => {
    const now = new Date();
    now.setSeconds(0, 0);
    return now.toISOString().slice(0, 16); // "YYYY-MM-DDTHH:MM"
  });
  const [geoLoading, setGeoLoading] = useState(false);

  // ── Result state ─────────────────────────────────────────────────────────
  const [loading, setLoading] = useState(false);
  const [response, setResponse] = useState<RankResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [selectedId, setSelectedId] = useState<string | null>(null);

  // ── Geolocation ──────────────────────────────────────────────────────────
  const handleGeolocate = useCallback(() => {
    if (!navigator.geolocation) {
      setError("Geolocation is not supported by your browser.");
      return;
    }
    setGeoLoading(true);
    navigator.geolocation.getCurrentPosition(
      (pos) => {
        setLat(pos.coords.latitude.toFixed(6));
        setLon(pos.coords.longitude.toFixed(6));
        setGeoLoading(false);
      },
      () => {
        setError("Could not get your location. Enter coordinates manually.");
        setGeoLoading(false);
      }
    );
  }, []);

  // ── Submit ───────────────────────────────────────────────────────────────
  const handleSearch = useCallback(
    async (e: React.FormEvent) => {
      e.preventDefault();
      const parsedLat = parseFloat(lat);
      const parsedLon = parseFloat(lon);
      if (isNaN(parsedLat) || isNaN(parsedLon)) {
        setError("Please enter valid latitude and longitude.");
        return;
      }

      setLoading(true);
      setError(null);
      setResponse(null);
      setSelectedId(null);

      // Format datetime as ISO 8601 without ms (what Pydantic expects)
      const isoDatetime = new Date(datetime).toISOString().slice(0, 19);

      try {
        const data = await fetchAeds({ start_lat: parsedLat, start_lon: parsedLon, datetime: isoDatetime });
        setResponse(data);
        // Auto-select first ranked result
        if (!data.abstained && data.ranked.length > 0) {
          setSelectedId(data.ranked[0].aed_id);
        }
      } catch (err) {
        setError(err instanceof Error ? err.message : "Unexpected error.");
      } finally {
        setLoading(false);
      }
    },
    [lat, lon, datetime]
  );

  // ── Derived state ─────────────────────────────────────────────────────────
  const selectedResult: RankedResult | null =
    response && !response.abstained
      ? (response.ranked.find((r) => r.aed_id === selectedId) ?? null)
      : null;

  const formReady = lat.trim() && lon.trim() && datetime;

  return (
    <>
      {/* Safety banner – grading gate – always visible */}
      <SafetyBanner />

      <main className="main-container">
        {/* Header */}
        <header className="app-header">
          <div className="app-logo" aria-hidden="true">🫀</div>
          <h1 className="app-title">AED Finder</h1>
          <p className="app-subtitle">
            AI-ranked defibrillators · Toa Payoh, Singapore · Prototype
          </p>
          {USE_FIXTURES && (
            <span className="fixture-badge" title="Running against fixture data">
              🔧 Demo mode – fixture data
            </span>
          )}
        </header>

        {/* Search form – POST /rank_aeds */}
        <form
          onSubmit={handleSearch}
          className="search-form-grid"
          aria-label="Find nearest AEDs"
        >
          {/* Row 1: Lat / Lon + geolocate */}
          <div className="coord-row">
            <div className="coord-field">
              <label htmlFor="start-lat" className="field-label">Latitude</label>
              <input
                id="start-lat"
                type="number"
                step="any"
                value={lat}
                onChange={(e) => setLat(e.target.value)}
                placeholder="e.g. 1.3343"
                className="search-input"
                disabled={loading || geoLoading}
                required
              />
            </div>
            <div className="coord-field">
              <label htmlFor="start-lon" className="field-label">Longitude</label>
              <input
                id="start-lon"
                type="number"
                step="any"
                value={lon}
                onChange={(e) => setLon(e.target.value)}
                placeholder="e.g. 103.8496"
                className="search-input"
                disabled={loading || geoLoading}
                required
              />
            </div>
            <button
              id="geolocate-button"
              type="button"
              className="geo-button"
              onClick={handleGeolocate}
              disabled={loading || geoLoading}
              title="Use my current location"
              aria-label="Use my current location"
            >
              {geoLoading
                ? <span className="spinner" aria-label="Getting location…" />
                : <>📍 My location</>}
            </button>
          </div>

          {/* Row 2: Datetime + Search */}
          <div className="datetime-row">
            <div className="datetime-field">
              <label htmlFor="search-datetime" className="field-label">Date &amp; time</label>
              <input
                id="search-datetime"
                type="datetime-local"
                value={datetime}
                onChange={(e) => setDatetime(e.target.value)}
                className="search-input datetime-input"
                disabled={loading}
                required
              />
            </div>
            <button
              id="aed-search-button"
              type="submit"
              className="search-button"
              disabled={loading || !formReady}
              aria-busy={loading}
            >
              {loading
                ? <span className="spinner" aria-label="Searching…" />
                : "Find AEDs"}
            </button>
          </div>
        </form>

        {/* Error */}
        {error && (
          <div className="error-banner" role="alert">⚠ {error}</div>
        )}

        {/* Results */}
        {response && (
          <div className="results-area">
            {/* Backend safety banner (from the API response itself) */}
            <div className="api-safety-banner" role="note">
              🛡 {response.safety_banner}
            </div>

            {response.abstained ? (
              <AbstainState
                reason={response.abstain_reason}
                safety_banner={response.safety_banner}
              />
            ) : (
              <div className="results-layout">
                {/* Left: ranked list */}
                <div className="results-column">
                  <p className="results-count">
                    {response.ranked.length} AED{response.ranked.length !== 1 ? "s" : ""} ranked
                    {" · "}
                    {response.baseline.length} compared by straight-line
                  </p>
                  <Results
                    ranked={response.ranked}
                    baseline={response.baseline}
                    selectedId={selectedId}
                    onSelect={setSelectedId}
                  />
                </div>

                {/* Right: Leaflet route map for selected AED */}
                {selectedResult && selectedResult.geometry.length > 0 && (
                  <div className="map-column">
                    <RouteMap
                      coordinates={selectedResult.geometry}
                      facilityName={`AED ${selectedResult.aed_id}`}
                    />
                  </div>
                )}
              </div>
            )}
          </div>
        )}

        {/* Empty state */}
        {!response && !loading && !error && (
          <div className="empty-state" aria-hidden="true">
            <div className="empty-state-icon">🗺</div>
            <p>Enter coordinates or use 📍 My location and pick a time to find the nearest AED.</p>
          </div>
        )}
      </main>
    </>
  );
}
