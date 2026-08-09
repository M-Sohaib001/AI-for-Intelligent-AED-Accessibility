// ---------------------------------------------------------------------------
// Fixture data – mirrors the exact RankResponse shape from backend/main.py
// geometry is [[lon, lat], ...] as returned by get_route_geometry()
// (Toa Payoh, Singapore coordinates – matching the real dataset area)
// ---------------------------------------------------------------------------

import type { RankResponse } from "@/types";

/** Case 1 – Normal: multiple eligible AEDs with full routes */
export const fixture_normal: RankResponse = {
  abstained: false,
  abstain_reason: null,
  safety_banner:
    "Prototype for planning and simulation only — not for emergency use. In an emergency in Singapore, call 995 immediately and follow SCDF instructions.",
  baseline: [
    { aed_id: "AED-001", straight_line_m: 145 },
    { aed_id: "AED-002", straight_line_m: 389 },
    { aed_id: "AED-003", straight_line_m: 612 },
  ],
  ranked: [
    {
      aed_id: "AED-001",
      distance_m: 180,
      modeled_walk_time_min: 2.3,
      flags: [],
      snap_quality: "acceptable",
      geometry: [
        [103.8496, 1.3343],
        [103.8498, 1.3345],
        [103.85,   1.3347],
        [103.8502, 1.3349],
      ],
    },
    {
      aed_id: "AED-002",
      distance_m: 430,
      modeled_walk_time_min: 5.4,
      flags: [],
      snap_quality: "warning",
      geometry: [
        [103.8496, 1.3343],
        [103.8492, 1.3348],
        [103.8488, 1.3353],
        [103.8485, 1.3357],
      ],
    },
    {
      aed_id: "AED-003",
      distance_m: 780,
      modeled_walk_time_min: 9.8,
      flags: ["floor_level_missing"],
      snap_quality: "acceptable",
      geometry: [
        [103.8496, 1.3343],
        [103.849,  1.334],
        [103.8484, 1.3337],
        [103.8478, 1.3334],
      ],
    },
  ],
};

/** Case 2 – Warning snap quality + location flags */
export const fixture_warning_snap: RankResponse = {
  abstained: false,
  abstain_reason: null,
  safety_banner:
    "Prototype for planning and simulation only — not for emergency use. In an emergency in Singapore, call 995 immediately and follow SCDF instructions.",
  baseline: [{ aed_id: "AED-010", straight_line_m: 280 }],
  ranked: [
    {
      aed_id: "AED-010",
      distance_m: 310,
      modeled_walk_time_min: 3.9,
      flags: ["floor_level_missing", "description_vague"],
      snap_quality: "warning",
      geometry: [
        [103.8496, 1.3343],
        [103.8499, 1.3346],
        [103.8502, 1.3349],
      ],
    },
  ],
};

/** Case 3 – Abstain: no open AED */
export const fixture_abstain_no_open: RankResponse = {
  abstained: true,
  abstain_reason: "NO_OPEN_AED",
  safety_banner:
    "Prototype for planning and simulation only — not for emergency use. In an emergency in Singapore, call 995 immediately and follow SCDF instructions.",
  baseline: [],
  ranked: [],
};

/** Case 4 – Abstain: outside max distance (1200 m catchment) */
export const fixture_abstain_distance: RankResponse = {
  abstained: true,
  abstain_reason: "OUTSIDE_MAX_DISTANCE",
  safety_banner:
    "Prototype for planning and simulation only — not for emergency use. In an emergency in Singapore, call 995 immediately and follow SCDF instructions.",
  baseline: [],
  ranked: [],
};

/** Case 5 – Abstain: hours unknown */
export const fixture_abstain_unknown: RankResponse = {
  abstained: true,
  abstain_reason: "HOURS_UNKNOWN",
  safety_banner:
    "Prototype for planning and simulation only — not for emergency use. In an emergency in Singapore, call 995 immediately and follow SCDF instructions.",
  baseline: [],
  ranked: [],
};
