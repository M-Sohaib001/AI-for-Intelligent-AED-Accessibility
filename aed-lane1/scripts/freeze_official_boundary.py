"""
Freeze the final study boundary using an authoritative
URA Master Plan 2025 planning-area polygon.

Final selection:
    WOODLANDS (WD)

Selection rationale:
    522 / 529 Sector 73 AEDs fall within Woodlands
    = 98.68% containment.

The official polygon is used directly rather than constructing
an artificial convex hull or bounding box.
"""

import json
from pathlib import Path

import geopandas as gpd


# ---------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------

SECTOR = "73"
SELECTED_PLANNING_AREA = "WOODLANDS"
SELECTED_CODE = "WD"

AED_DATA = Path("data/scdf_aed_frozen.geojson")
PLANNING_AREAS = Path("data/official_mp25_planning_areas.geojson")

FINAL_BOUNDARY = Path("data/district_boundary.geojson")
SELECTION_REPORT = Path("data/district_selection.json")


# ---------------------------------------------------------------------
# Load AED dataset
# ---------------------------------------------------------------------

print("Loading frozen AED dataset...")

with AED_DATA.open("r", encoding="utf-8") as f:
    data = json.load(f)

rows = []

for feature in data["features"]:
    props = feature["properties"]
    geometry = feature["geometry"]

    lon, lat = geometry["coordinates"]

    postal_code = str(props["POSTAL_CODE"]).zfill(6)
    postal_sector = postal_code[:2]

    if postal_sector == SECTOR:
        rows.append(
            {
                "AED_ID": props["AED_ID"],
                "lon": lon,
                "lat": lat,
            }
        )

aeds = gpd.GeoDataFrame(
    rows,
    geometry=gpd.points_from_xy(
        [r["lon"] for r in rows],
        [r["lat"] for r in rows],
    ),
    crs="EPSG:4326",
)

print(f"Loaded {len(aeds):,} AEDs for postal sector {SECTOR}.")


# ---------------------------------------------------------------------
# Load official planning areas
# ---------------------------------------------------------------------

print("Loading official planning-area polygons...")

planning = gpd.read_file(PLANNING_AREAS)

selected = planning[
    (planning["PLN_AREA_N"].str.upper() == SELECTED_PLANNING_AREA)
    & (planning["PLN_AREA_C"].str.upper() == SELECTED_CODE)
].copy()

if selected.empty:
    raise RuntimeError(
        f"Could not find official planning area "
        f"{SELECTED_PLANNING_AREA} ({SELECTED_CODE})."
    )

if len(selected) > 1:
    print(
        f"WARNING: {len(selected)} polygons found for "
        f"{SELECTED_PLANNING_AREA} ({SELECTED_CODE}). "
        f"They will be dissolved into one official boundary."
    )


# ---------------------------------------------------------------------
# Ensure CRS compatibility
# ---------------------------------------------------------------------

selected = selected.to_crs(aeds.crs)


# ---------------------------------------------------------------------
# Dissolve selected official polygon(s)
# ---------------------------------------------------------------------

final_boundary = selected.dissolve(
    by=None,
    as_index=False,
)

final_boundary["planning_area"] = SELECTED_PLANNING_AREA
final_boundary["planning_area_code"] = SELECTED_CODE


# ---------------------------------------------------------------------
# Calculate AED containment
# ---------------------------------------------------------------------

boundary_geometry = final_boundary.geometry.iloc[0]

inside = aeds.geometry.apply(boundary_geometry.covers)

inside_count = int(inside.sum())
outside_count = int((~inside).sum())

containment_rate = inside_count / len(aeds)


# ---------------------------------------------------------------------
# Record excluded AED IDs
# ---------------------------------------------------------------------

excluded_aeds = aeds.loc[
    ~inside,
    "AED_ID"
].tolist()


# ---------------------------------------------------------------------
# Write final boundary
# ---------------------------------------------------------------------

FINAL_BOUNDARY.parent.mkdir(parents=True, exist_ok=True)

final_boundary.to_file(
    FINAL_BOUNDARY,
    driver="GeoJSON",
)


# ---------------------------------------------------------------------
# Write reproducibility / decision report
# ---------------------------------------------------------------------

report = {
    "study_area_status": "FROZEN",

    "postal_sector": SECTOR,

    "selected_planning_area": {
        "name": SELECTED_PLANNING_AREA,
        "code": SELECTED_CODE,
    },

    "official_dataset": {
        "path": str(PLANNING_AREAS),
        "dataset_name": "Master Plan 2025 Planning Area Boundary (No Sea)",
        "publisher": "Urban Redevelopment Authority",
        "source": "data.gov.sg",
    },

    "aed_coverage": {
        "total_sector_aeds": len(aeds),
        "aeds_inside_boundary": inside_count,
        "aeds_outside_boundary": outside_count,
        "containment_rate": containment_rate,
        "containment_rate_pct": round(
            containment_rate * 100,
            2,
        ),
    },

    "excluded_aed_ids": excluded_aeds,

    "selection_rationale": (
        "Woodlands was selected because it contains "
        f"{inside_count} of {len(aeds)} AED records from postal sector "
        f"{SECTOR}, corresponding to {containment_rate:.2%} containment. "
        "The boundary is taken directly from the authoritative "
        "URA Master Plan 2025 planning-area dataset rather than "
        "constructed using a convex hull or bounding box."
    ),

    "methodological_note": (
        "The frozen raw AED dataset remains unchanged. "
        "AEDs outside the selected study boundary are retained "
        "for provenance but are excluded from downstream "
        "study-area routing and evaluation."
    ),
}

with SELECTION_REPORT.open("w", encoding="utf-8") as f:
    json.dump(
        report,
        f,
        indent=2,
    )


# ---------------------------------------------------------------------
# Final output
# ---------------------------------------------------------------------

print()
print("========================================")
print("FINAL STUDY BOUNDARY FROZEN")
print("========================================")
print(f"Planning area:       {SELECTED_PLANNING_AREA}")
print(f"Planning-area code:  {SELECTED_CODE}")
print(f"Sector AEDs:         {len(aeds):,}")
print(f"AEDs inside:         {inside_count:,}")
print(f"AEDs outside:        {outside_count:,}")
print(f"Containment:         {containment_rate:.2%}")
print()
print("Files created:")
print(f"  {FINAL_BOUNDARY}")
print(f"  {SELECTION_REPORT}")
print()
print("NEXT:")
print("Validate the final boundary.")
print("Then begin pedestrian-network construction.")