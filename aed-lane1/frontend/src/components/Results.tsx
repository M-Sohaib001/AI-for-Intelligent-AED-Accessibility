"use client";

import type { RankedResult, BaselineResult } from "@/types";

// ---------------------------------------------------------------------------
// Snap quality helpers – matches snap_quality values from graph_utils.py
// ---------------------------------------------------------------------------
const SNAP_LABELS: Record<string, string> = {
  acceptable: "✓ Good location match",
  warning: "⚠ Approximate location",
  outlier: "✗ Location uncertain",
};

const SNAP_CLASSES: Record<string, string> = {
  acceptable: "snap-exact",
  warning: "snap-approximate",
  outlier: "snap-outlier",
};

// ---------------------------------------------------------------------------
// Flag badge – shows location_flags from data_quality
// ---------------------------------------------------------------------------
function FlagBadges({ flags }: { flags: string[] }) {
  if (!flags || flags.length === 0) return null;
  return (
    <>
      {flags.map((f) => (
        <span key={f} className="badge badge-anomaly" title={f}>
          ⚑ {f.replace(/_/g, " ")}
        </span>
      ))}
    </>
  );
}

// ---------------------------------------------------------------------------
// Straight-line vs network distance comparator chip
// ---------------------------------------------------------------------------
function NetworkVsBaseline({
  networkM,
  baselineM,
}: {
  networkM: number;
  baselineM: number | undefined;
}) {
  if (baselineM == null) return null;
  const overhead = Math.round(networkM - baselineM);
  if (overhead <= 0) return null;
  return (
    <span className="meta-chip meta-chip--overhead" title="Extra walking distance vs straight line">
      +{overhead} m detour
    </span>
  );
}

// ---------------------------------------------------------------------------
// Single AED result card
// ---------------------------------------------------------------------------
function ResultCard({
  result,
  rank,
  baselineM,
  onSelect,
  selected,
}: {
  result: RankedResult;
  rank: number;
  baselineM: number | undefined;
  onSelect: (id: string) => void;
  selected: boolean;
}) {
  const snapLabel = SNAP_LABELS[result.snap_quality] ?? result.snap_quality;
  const snapClass = SNAP_CLASSES[result.snap_quality] ?? "";

  return (
    <article
      className={`result-card ${selected ? "result-card--selected" : ""}`}
      onClick={() => onSelect(result.aed_id)}
      aria-selected={selected}
      tabIndex={0}
      onKeyDown={(e) => e.key === "Enter" && onSelect(result.aed_id)}
      id={`result-card-${result.aed_id}`}
    >
      <div className="result-rank">{rank}</div>

      <div className="result-body">
        <h2 className="result-name">AED {result.aed_id}</h2>

        <div className="result-meta">
          <span className="meta-chip">
            📍 {result.distance_m < 1000
              ? `${result.distance_m} m`
              : `${(result.distance_m / 1000).toFixed(2)} km`}
          </span>
          <span className="meta-chip">
            🚶 {result.modeled_walk_time_min} min walk
          </span>
          <span className={`meta-chip snap-chip ${snapClass}`}>
            {snapLabel}
          </span>
          <NetworkVsBaseline networkM={result.distance_m} baselineM={baselineM} />
        </div>

        <div className="result-badges">
          <FlagBadges flags={result.flags} />
        </div>
      </div>

      {result.geometry?.length > 0 && (
        <div className="result-map-hint">🗺 Route</div>
      )}
    </article>
  );
}

// ---------------------------------------------------------------------------
// Results list
// ---------------------------------------------------------------------------
export default function Results({
  ranked,
  baseline,
  selectedId,
  onSelect,
}: {
  ranked: RankedResult[];
  baseline: BaselineResult[];
  selectedId: string | null;
  onSelect: (id: string) => void;
}) {
  // Build a quick lookup for baseline straight-line distances
  const baselineMap = Object.fromEntries(
    baseline.map((b) => [b.aed_id, b.straight_line_m])
  );

  if (ranked.length === 0) {
    return (
      <p className="empty-results">
        No AEDs match the current filters.
      </p>
    );
  }

  return (
    <section className="results-list" aria-label="Ranked AED results">
      {ranked.map((r, i) => (
        <ResultCard
          key={r.aed_id}
          result={r}
          rank={i + 1}
          baselineM={baselineMap[r.aed_id]}
          selected={selectedId === r.aed_id}
          onSelect={onSelect}
        />
      ))}
    </section>
  );
}
