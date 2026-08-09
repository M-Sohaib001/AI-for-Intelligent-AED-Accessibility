"use client";

import type { AbstainReason } from "@/types";

// ---------------------------------------------------------------------------
// AbstainState – maps backend AbstainReason enum values (abstention.py)
// to a user-friendly designed screen.
// "I don't know" is a safety feature, not a failure.
// ---------------------------------------------------------------------------

const ICONS: Record<string, string> = {
  NO_OPEN_AED: "🔒",
  HOURS_UNKNOWN: "❓",
  LOCATION_MAPPING_UNCERTAIN: "📍",
  NO_WALKING_PATH: "🚧",
  OUTSIDE_MAX_DISTANCE: "🗺",
  NO_FEASIBLE_AED: "⚠️",
};

const TITLES: Record<string, string> = {
  NO_OPEN_AED: "No open AEDs found",
  HOURS_UNKNOWN: "Operating hours unknown",
  LOCATION_MAPPING_UNCERTAIN: "Location data uncertain",
  NO_WALKING_PATH: "No walking path available",
  OUTSIDE_MAX_DISTANCE: "All AEDs beyond 1,200 m",
  NO_FEASIBLE_AED: "No feasible AED found",
};

const GUIDANCE: Record<string, string> = {
  NO_OPEN_AED:
    "All nearby AEDs appear to be closed at this time. Try a different date/time, or call 995 immediately in an emergency.",
  HOURS_UNKNOWN:
    "Operating hours for all nearby AEDs could not be determined. The system cannot confirm they are accessible. Call 995 in an emergency.",
  LOCATION_MAPPING_UNCERTAIN:
    "The precise physical location of nearby AEDs could not be reliably mapped to the walking network. Results would be unreliable.",
  NO_WALKING_PATH:
    "No continuous walking path exists between your location and any nearby AED on the pedestrian network.",
  OUTSIDE_MAX_DISTANCE:
    "All AEDs are further than 1,200 m away. At a walking pace this would take over 15 minutes — too long for defibrillation effectiveness.",
  NO_FEASIBLE_AED:
    "No AED in the dataset meets all feasibility criteria for your location and time. This prototype covers Toa Payoh, Singapore only.",
};

export default function AbstainState({
  reason,
  safety_banner,
}: {
  reason: AbstainReason | null;
  safety_banner: string;
}) {
  const key = reason ?? "NO_FEASIBLE_AED";
  const icon = ICONS[key] ?? "ℹ️";
  const title = TITLES[key] ?? "No results";
  const guidance = GUIDANCE[key] ?? "No AED could be safely recommended.";

  return (
    <div className="abstain-container" role="status" aria-live="polite" id="abstain-state">
      <div className="abstain-icon" aria-hidden="true">{icon}</div>
      <h2 className="abstain-title">{title}</h2>
      <p className="abstain-message">{guidance}</p>

      <div className="abstain-safety-note">
        <span className="safety-icon">🛡</span>
        <span>
          {safety_banner}
        </span>
      </div>

      <p className="abstain-reason-code">
        Reason code: <code>{key}</code>
      </p>
    </div>
  );
}
