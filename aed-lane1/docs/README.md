# AED Discovery & Routing — Lane 1 Prototype
Sofstica AI Hackathon 2026 — Saving Minutes, Saving Lives

Prototype for planning and simulation only — not for emergency use.
In an emergency in Singapore, call 995 immediately and follow SCDF instructions.

## Frozen Study Area

The project study area is the **Woodlands Planning Area (WD)**, selected using the
official URA Master Plan 2025 Planning Area Boundary dataset.

- **Postal sector screened:** 73
- **AED records in Sector 73:** 529
- **AED records inside Woodlands:** 522
- **AED records outside Woodlands:** 7
- **AED containment:** 98.68%

Woodlands was selected because it contains 522 of the 529 AED records in the
selected postal sector. The final study boundary uses the official planning-area
polygon rather than an artificial convex hull or bounding box.

The original frozen AED dataset remains unchanged. AEDs outside the study
boundary are retained for provenance but excluded from downstream study-area
routing and evaluation.

