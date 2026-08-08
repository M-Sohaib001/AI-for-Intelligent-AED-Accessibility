"""
Select and freeze the study district for AED-Lane1.

Inputs:
    data/scdf_aed_frozen.geojson

Outputs:
    data/district_boundary.geojson
    data/district_selection.json

Purpose:
    1. Use the EDA-derived postal-sector candidates as a screening tool.
    2. Rank candidate sectors using transparent, reproducible criteria.
    3. Print a compact comparison for human review.
    4. Freeze ONE final study boundary.

Important:
    A postal sector is only a screening unit. It is NOT automatically
    treated as the final geographic boundary.

Before running:
    pip install pandas geopandas shapely
"""

import json
from pathlib import Path

import geopandas as gpd
import pandas as pd
from shapely.geometry import Polygon


RAW_PATH = Path("data/scdf_aed_frozen.geojson")
BOUNDARY_PATH = Path("data/district_boundary.geojson")
SELECTION_PATH = Path("data/district_selection.json")

# Candidate sectors from the completed global EDA.
# These are the top sectors by AED count, not automatically the final choice.
TOP_N_CANDIDATES = 10

# Transparent screening weights.
# These are NOT scientific model weights; they only help prioritize
# candidates for human review.
WEIGHTS = {
    "aed_count": 0.35,
    "always_open_pct": 0.20,
    "building_diversity": 0.20,
    "location_ambiguity": 0.15,
    "floor_completeness": 0.10,
}

AMBIGUOUS_TERMS = [
    "near",
    "beside",
    "opposite",
    "vicinity",
    "around",
    "behind",
]


def load_aeds():
    if not RAW_PATH.exists():
        raise FileNotFoundError(f"Missing dataset: {RAW_PATH}")

    with RAW_PATH.open(encoding="utf-8") as f:
        data = json.load(f)

    rows = []

    for feature in data["features"]:
        props = feature.get("properties", {})
        geometry = feature.get("geometry")

        if not geometry or geometry.get("type") != "Point":
            continue

        lon, lat = geometry["coordinates"]

        rows.append(
            {
                **props,
                "lon": lon,
                "lat": lat,
            }
        )

    df = pd.DataFrame(rows)

    if df.empty:
        raise RuntimeError("No point AED records found.")

    required = [
        "OPERATING_HOURS",
        "BUILDING_NAME",
        "AED_LOCATION_DESCRIPTION",
        "AED_LOCATION_FLOOR_LEVEL",
        "POSTAL_CODE",
        "lat",
        "lon",
    ]

    missing = [c for c in required if c not in df.columns]
    if missing:
        raise RuntimeError(f"Dataset is missing required columns: {missing}")

    df["postal_str"] = (
        df["POSTAL_CODE"]
        .fillna("")
        .astype(str)
        .str.replace(r"\.0$", "", regex=True)
        .str.zfill(6)
    )

    # A two-digit postal sector is used only for candidate screening.
    df["postal_sector"] = df["postal_str"].str[:2]

    df["hours"] = df["OPERATING_HOURS"].fillna("").astype(str).str.strip()
    df["description"] = (
        df["AED_LOCATION_DESCRIPTION"].fillna("").astype(str).str.lower()
    )
    df["floor"] = (
        df["AED_LOCATION_FLOOR_LEVEL"].fillna("").astype(str).str.strip()
    )

    return df


def build_candidate_table(df):
    sector_counts = df["postal_sector"].value_counts()

    candidates = sector_counts.head(TOP_N_CANDIDATES).index.tolist()

    records = []

    for sector in candidates:
        subset = df[df["postal_sector"] == sector].copy()

        always_open = subset["hours"].str.contains(
            "00:00-23:59",
            regex=False,
        ).mean()

        building_diversity = (
            subset["BUILDING_NAME"]
            .replace("", pd.NA)
            .nunique(dropna=True)
            / len(subset)
            if len(subset)
            else 0
        )

        ambiguity_pattern = "|".join(AMBIGUOUS_TERMS)

        ambiguous_pct = (
            subset["description"]
            .str.contains(ambiguity_pattern, regex=True, na=False)
            .mean()
        )

        missing_floor_pct = (
            subset["floor"].eq("").mean()
        )

        records.append(
            {
                "postal_sector": str(sector),
                "aed_count": int(len(subset)),
                "always_open_pct": float(always_open),
                "building_diversity": float(building_diversity),
                "ambiguous_location_pct": float(ambiguous_pct),
                "missing_floor_pct": float(missing_floor_pct),
            }
        )

    result = pd.DataFrame(records)

    # Normalize count and diversity so the scoring components are comparable.
    result["aed_count_norm"] = (
        result["aed_count"] / result["aed_count"].max()
    )

    result["building_diversity_norm"] = (
        result["building_diversity"]
        / result["building_diversity"].max()
        if result["building_diversity"].max() > 0
        else 0
    )

    # Higher is better for floor completeness.
    result["floor_completeness"] = 1 - result["missing_floor_pct"]

    # Higher is better for lower ambiguity.
    result["location_clarity"] = 1 - result["ambiguous_location_pct"]

    result["screening_score"] = (
        WEIGHTS["aed_count"] * result["aed_count_norm"]
        + WEIGHTS["always_open_pct"] * result["always_open_pct"]
        + WEIGHTS["building_diversity"] * result["building_diversity_norm"]
        + WEIGHTS["location_ambiguity"] * result["location_clarity"]
        + WEIGHTS["floor_completeness"] * result["floor_completeness"]
    )

    return result.sort_values(
        "screening_score",
        ascending=False,
    ).reset_index(drop=True)


def create_sector_boundary(df, sector):
    """
    Create a simple convex-hull polygon around AED points in the selected
    postal sector.

    This is a provisional geometry only.

    IMPORTANT:
    The final project should replace this with a defensible administrative
    or planning boundary if an authoritative boundary dataset is available.
    """
    subset = df[df["postal_sector"] == str(sector)]

    points = gpd.GeoSeries(
        gpd.points_from_xy(subset["lon"], subset["lat"]),
        crs="EPSG:4326",
    )

    if len(points) < 3:
        raise RuntimeError(
            f"Sector {sector} has fewer than 3 points; "
            "cannot construct a polygon."
        )

    hull = points.union_all().convex_hull

    if hull.geom_type != "Polygon":
        raise RuntimeError(
            f"Could not create polygon boundary for sector {sector}."
        )

    return gpd.GeoDataFrame(
        {
            "postal_sector": [str(sector)],
            "boundary_source": ["AED point convex hull — provisional"],
        },
        geometry=[hull],
        crs="EPSG:4326",
    )


def main():
    df = load_aeds()

    print(f"Loaded {len(df):,} AED records.")
    print()

    candidates = build_candidate_table(df)

    display_cols = [
        "postal_sector",
        "aed_count",
        "always_open_pct",
        "building_diversity",
        "ambiguous_location_pct",
        "missing_floor_pct",
        "screening_score",
    ]

    print("Candidate postal-sector screening:")
    print(
        candidates[display_cols].to_string(
            index=False,
            formatters={
                "always_open_pct": "{:.1%}".format,
                "building_diversity": "{:.1%}".format,
                "ambiguous_location_pct": "{:.1%}".format,
                "missing_floor_pct": "{:.1%}".format,
                "screening_score": "{:.3f}".format,
            },
        )
    )

    print()
    print(
        "IMPORTANT: the screening score does NOT select the final "
        "district automatically."
    )
    print(
        "It only identifies candidates for human/geographic validation."
    )

    recommended = str(candidates.iloc[0]["postal_sector"])

    print()
    print(f"Highest screening score: sector {recommended}")

    # Allow the team to explicitly freeze a sector.
    selected = input(
        f"Enter the FINAL postal sector to freeze "
        f"(press Enter to use {recommended}): "
    ).strip()

    selected = selected or recommended

    if selected not in set(candidates["postal_sector"]):
        raise ValueError(
            f"{selected!r} is not one of the top {TOP_N_CANDIDATES} "
            "screened sectors."
        )

    boundary = create_sector_boundary(df, selected)

    BOUNDARY_PATH.parent.mkdir(parents=True, exist_ok=True)

    boundary.to_file(
        BOUNDARY_PATH,
        driver="GeoJSON",
    )

    selected_row = candidates[
        candidates["postal_sector"] == selected
    ].iloc[0]

    selection_record = {
        "selected_postal_sector": selected,
        "selection_method": (
            "Top-sector screening followed by explicit human selection"
        ),
        "screening_weights": WEIGHTS,
        "candidate_count": TOP_N_CANDIDATES,
        "screening_metrics": {
            "aed_count": int(selected_row["aed_count"]),
            "always_open_pct": float(selected_row["always_open_pct"]),
            "building_diversity": float(selected_row["building_diversity"]),
            "ambiguous_location_pct": float(
                selected_row["ambiguous_location_pct"]
            ),
            "missing_floor_pct": float(
                selected_row["missing_floor_pct"]
            ),
            "screening_score": float(
                selected_row["screening_score"]
            ),
        },
        "boundary_file": str(BOUNDARY_PATH),
        "boundary_source": (
            "Convex hull of AED points in selected postal sector; "
            "PROVISIONAL — replace with authoritative administrative/"
            "planning boundary before final evaluation if available."
        ),
    }

    with SELECTION_PATH.open("w", encoding="utf-8") as f:
        json.dump(selection_record, f, indent=2)

    print()
    print("Study-area files created:")
    print(f"  {BOUNDARY_PATH}")
    print(f"  {SELECTION_PATH}")
    print()
    print(
        "NEXT: inspect the generated boundary on a map. "
        "Do NOT start final routing/evaluation until the boundary is "
        "accepted and frozen."
    )


if __name__ == "__main__":
    main()