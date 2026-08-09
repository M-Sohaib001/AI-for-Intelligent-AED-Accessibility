// ---------------------------------------------------------------------------
// Shared types – exactly matches the real /rank_aeds API response from
// AI-for-Intelligent-AED-Accessibility backend/main.py
// ---------------------------------------------------------------------------

// [lon, lat] pairs as returned by get_route_geometry() in graph_utils.py
export type Coordinate = [number, number];

// ── Ranked AED result (one entry in RankResponse.ranked) ──────────────────
export interface RankedResult {
  aed_id: string;
  distance_m: number;
  modeled_walk_time_min: number;
  flags: string[];           // location_flags from data_quality
  snap_quality: string;      // "acceptable" | "warning" | "outlier"
  geometry: Coordinate[];    // [[lon, lat], ...] – direct Leaflet Polyline input
}

// ── Baseline straight-line comparator ────────────────────────────────────
export interface BaselineResult {
  aed_id: string;
  straight_line_m: number;
}

// ── Full API response ─────────────────────────────────────────────────────
export interface RankResponse {
  ranked: RankedResult[];
  baseline: BaselineResult[];
  abstained: boolean;
  abstain_reason: string | null;   // AbstainReason enum value or null
  safety_banner: string;           // "Prototype for planning..." from backend
}

// ── Request body for POST /rank_aeds ─────────────────────────────────────
export interface RankAedsRequest {
  start_lat: number;
  start_lon: number;
  datetime: string; // ISO 8601 e.g. "2026-08-09T14:30:00"
}

// ── AbstainReason values from backend abstention.py ──────────────────────
export type AbstainReason =
  | "NO_OPEN_AED"
  | "HOURS_UNKNOWN"
  | "LOCATION_MAPPING_UNCERTAIN"
  | "NO_WALKING_PATH"
  | "OUTSIDE_MAX_DISTANCE"
  | "NO_FEASIBLE_AED";
