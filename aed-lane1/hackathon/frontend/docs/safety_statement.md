# Safety Statement

This document walks through the SOFISTICA AI Hackathon safety checklist item by item, citing exactly where each item is enforced in the codebase.

---

## 1. Prototype Disclaimer Visible on Every Page

**Requirement**: Every page/screen must clearly state this is a prototype and not for clinical use.

**Enforcement**:
- `src/components/SafetyBanner.tsx` — renders a sticky red banner at the top of every page reading: *"Prototype — not for clinical use. Results are ranked by AI and may be incomplete or inaccurate."*
- `src/app/layout.tsx` — root layout ensures every route in the app renders through it; `SafetyBanner` is mounted inside `page.tsx` which is the only page, guaranteeing it appears on every load.
- The banner is `position: sticky; top: 0; z-index: 100` — it cannot be scrolled away.

---

## 2. System Must Not Guess

**Requirement**: If the system cannot produce a trustworthy result, it must abstain rather than display unreliable information.

**Enforcement**:
- `src/components/AbstainState.tsx` — dedicated designed screen for when `status === "abstain"`. Reasons handled: `no_open_facilities`, `out_of_bounds`, `low_confidence`, `api_error`.
- `src/app/page.tsx` line ~87 — before rendering any results, the code checks `response.status === "abstain"` and renders `AbstainState` instead of a result list.
- The abstain screen includes a visible safety note: *"This system will not guess. Displaying low-confidence or out-of-scope results could direct you to a closed or unsuitable facility."*

---

## 3. Confidence and Data Quality Must Be Communicated

**Requirement**: Users must be informed of any uncertainty in the data.

**Enforcement**:
- `src/components/Results.tsx` — `ConfidenceBadge` renders green/amber/red-outline treatment based on `hours_confidence_score` (high ≥0.7, medium 0.4–0.7, low <0.4).
- `src/components/Results.tsx` — `AnomalyBadge` renders a ⚑ badge listing all `registry_anomaly_flags` when present.
- `src/components/Results.tsx` — snap quality chip shows `"⚠ Outlier – position uncertain"` for `snap_quality === "outlier"`.
- `src/components/ThresholdSlider.tsx` — users can raise the minimum confidence threshold and see the result list shrink in real time, making the effect of confidence visible.
- Both badge fields use defensive null-checks: if the backend doesn't yet include the field, no badge renders and the app does not crash. Absence of a badge does not imply certainty.

---

## 4. Emergency Contacts Always Accessible

**Requirement**: Users in urgent situations must always be able to reach emergency services.

**Enforcement**:
- `src/components/SafetyBanner.tsx` — links to `tel:999` and `tel:111` (NHS 111) are present in the safety banner on every page load.

---

## 5. Map Attribution (OpenStreetMap Licence)

**Requirement**: OpenStreetMap data requires attribution on every map tile display.

**Enforcement**:
- `src/components/RouteMap.tsx` — the Leaflet tile layer is initialised with the required attribution string: `© OpenStreetMap contributors` with a link to the copyright page.
- A code comment reads: *"Attribution line is required by OpenStreetMap's licence – never drop it, even in a rushed final commit."*

---

## 6. API Errors Are Handled Safely

**Requirement**: Network or API failures must not crash the UI or display partial/misleading data.

**Enforcement**:
- `src/app/page.tsx` `fetchResults()` — wraps the API call in a try/catch; on error, returns an `APIResponseAbstain` with `reason: "api_error"`.
- Non-2xx HTTP responses are caught by the `!res.ok` check and also return an abstain response.
- The UI renders `AbstainState` for any abstain response, including API errors.

---

## 7. Scope Limitation Communicated

**Requirement**: Users outside the supported geographic area must be informed.

**Enforcement**:
- `src/components/AbstainState.tsx` — `out_of_bounds` reason renders: *"Your location falls outside the area this prototype covers. This prototype is currently limited to Greater London."*
- `src/app/page.tsx` — app header subtitle reads: *"AI-ranked pharmacies near you · Greater London prototype"*
- `src/fixtures.ts` — `fixture_abstain_out_of_bounds` provides a testable fixture for this case.

---

## Summary Table

| Safety Item | Enforced In |
|---|---|
| Prototype disclaimer on every page | `SafetyBanner.tsx`, `layout.tsx` |
| System abstains rather than guessing | `page.tsx`, `AbstainState.tsx` |
| Confidence communicated visually | `Results.tsx` (badges + snap chips) |
| User can adjust confidence threshold | `ThresholdSlider.tsx` |
| Emergency contacts always present | `SafetyBanner.tsx` |
| Map attribution (OSM licence) | `RouteMap.tsx` |
| API errors handled safely | `page.tsx` `fetchResults()` |
| Geographic scope communicated | `AbstainState.tsx`, app header |
