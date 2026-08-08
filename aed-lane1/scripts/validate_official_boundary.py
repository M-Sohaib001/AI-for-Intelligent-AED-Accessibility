"""
Validate Sector 73 against Singapore's official URA Master Plan 2025
Planning Area boundaries.

This script DOES NOT freeze the final study boundary.

It:
1. Loads the frozen AED dataset.
2. Downloads the official URA Master Plan 2025 Planning Area Boundary
   (No Sea) dataset from data.gov.sg.
3. Freezes the downloaded source locally.
4. Spatially evaluates Sector 73 AEDs against official planning areas.
5. Reports AED coverage by planning area.
6. Generates an interactive inspection map.
7. Produces a machine-readable validation report.

Final boundary selection is intentionally left for human/methodological
validation after inspecting these results.
"""

from pathlib import Path
import hashlib
import json

import folium
import geopandas as gpd
import pandas as pd
import requests
from shapely.geometry import Point


# ---------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------

PROJECT_ROOT = Path(__file__).resolve().parents[1]

AED_PATH = PROJECT_ROOT / "data" / "scdf_aed_frozen.geojson"

OFFICIAL_BOUNDARY_PATH = (
    PROJECT_ROOT / "data" / "official_mp25_planning_areas.geojson"
)

OFFICIAL_SHA256_PATH = (
    PROJECT_ROOT / "data" / "official_mp25_planning_areas.sha256"
)

REPORT_PATH = (
    PROJECT_ROOT / "data" / "sector_73_official_boundary_report.json"
)

MAP_PATH = (
    PROJECT_ROOT / "scripts" / "sector_73_official_boundary_inspection.html"
)

SECTOR = "73"

DATASET_ID = "d_2cc750190544007400b2cfd5d7f53209"

POLL_URL = (
    f"https://api-open.data.gov.sg/v1/public/api/"
    f"datasets/{DATASET_ID}/poll-download"
)


# ---------------------------------------------------------------------
# Utility functions
# ---------------------------------------------------------------------

def sha256_file(path: Path) -> str:
    """Return SHA-256 checksum for a file."""

    h = hashlib.sha256()

    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)

    return h.hexdigest()


def download_official_boundary() -> None:
    """
    Download the official URA Master Plan 2025 planning-area dataset
    from data.gov.sg and freeze it locally.
    """

    if OFFICIAL_BOUNDARY_PATH.exists():
        print(
            f"Official boundary dataset already exists:\n"
            f"  {OFFICIAL_BOUNDARY_PATH}"
        )

        return

    print("Downloading official URA planning-area boundary dataset...")

    response = requests.get(POLL_URL, timeout=60)
    response.raise_for_status()

    metadata = response.json()

    if metadata.get("code") != 0:
        raise RuntimeError(
            f"data.gov.sg download request failed: "
            f"{metadata.get('errMsg')}"
        )

    download_url = metadata["data"]["url"]

    print(f"Resolved download URL:")
    print(download_url)

    data_response = requests.get(download_url, timeout=120)
    data_response.raise_for_status()

    OFFICIAL_BOUNDARY_PATH.write_bytes(data_response.content)

    checksum = sha256_file(OFFICIAL_BOUNDARY_PATH)

    OFFICIAL_SHA256_PATH.write_text(
        f"{checksum}  {OFFICIAL_BOUNDARY_PATH.name}\n",
        encoding="utf-8",
    )

    print()
    print("Official boundary dataset frozen locally.")
    print(f"  File: {OFFICIAL_BOUNDARY_PATH}")
    print(f"  SHA256: {checksum}")


def load_aeds() -> gpd.GeoDataFrame:
    """Load frozen AED dataset and return Sector 73 points."""

    print("Loading frozen AED dataset...")

    with open(AED_PATH, encoding="utf-8") as f:
        data = json.load(f)

    rows = []

    for feature in data["features"]:
        properties = feature["properties"]

        coordinates = feature["geometry"]["coordinates"]

        lon = coordinates[0]
        lat = coordinates[1]

        rows.append(
            {
                **properties,
                "lon": lon,
                "lat": lat,
            }
        )

    df = pd.DataFrame(rows)

    df["postal_str"] = (
        df["POSTAL_CODE"]
        .astype(str)
        .str.zfill(6)
    )

    df["postal_sector"] = df["postal_str"].str[:2]

    sector_df = df[df["postal_sector"] == SECTOR].copy()

    if sector_df.empty:
        raise RuntimeError(
            f"No AED records found for postal sector {SECTOR}."
        )

    geometry = [
        Point(lon, lat)
        for lon, lat in zip(
            sector_df["lon"],
            sector_df["lat"],
        )
    ]

    gdf = gpd.GeoDataFrame(
        sector_df,
        geometry=geometry,
        crs="EPSG:4326",
    )

    print(
        f"Loaded {len(gdf):,} AED records for sector {SECTOR}."
    )

    return gdf


def load_official_boundaries() -> gpd.GeoDataFrame:
    """Load official URA planning-area polygons."""

    print("Loading official planning-area polygons...")

    gdf = gpd.read_file(OFFICIAL_BOUNDARY_PATH)

    if gdf.empty:
        raise RuntimeError(
            "Official planning-area dataset is empty."
        )

    if gdf.crs is None:
        raise RuntimeError(
            "Official planning-area dataset has no CRS."
        )

    gdf = gdf.to_crs("EPSG:4326")

    required_columns = {
        "PLN_AREA_N",
        "PLN_AREA_C",
    }

    missing = required_columns - set(gdf.columns)

    if missing:
        raise RuntimeError(
            f"Official boundary dataset is missing columns: {missing}"
        )

    print(
        f"Loaded {len(gdf):,} official planning areas."
    )

    return gdf


# ---------------------------------------------------------------------
# Spatial analysis
# ---------------------------------------------------------------------

def calculate_candidate_metrics(
    aeds: gpd.GeoDataFrame,
    planning_areas: gpd.GeoDataFrame,
):
    """
    Calculate how many Sector 73 AEDs are covered by each official
    planning area.

    'covers' is used instead of 'within' so points exactly on a polygon
    boundary are counted as covered.
    """

    print()
    print("Calculating AED coverage by official planning area...")

    records = []

    for _, area in planning_areas.iterrows():

        polygon = area.geometry

        covered_mask = aeds.geometry.apply(
            polygon.covers
        )

        covered = int(covered_mask.sum())

        if covered == 0:
            continue

        subset = aeds.loc[covered_mask]

        records.append(
            {
                "planning_area": area["PLN_AREA_N"],
                "planning_area_code": area["PLN_AREA_C"],
                "aed_count": covered,
                "coverage_pct": covered / len(aeds),
                "lat_min": float(subset["lat"].min()),
                "lat_max": float(subset["lat"].max()),
                "lon_min": float(subset["lon"].min()),
                "lon_max": float(subset["lon"].max()),
                "geometry": polygon,
            }
        )

    result = gpd.GeoDataFrame(
        records,
        geometry="geometry",
        crs="EPSG:4326",
    )

    result = result.sort_values(
        by=["aed_count", "coverage_pct"],
        ascending=False,
    )

    return result


def print_results(results: gpd.GeoDataFrame, total_aeds: int):
    """Print candidate planning-area results."""

    print()
    print("=" * 80)
    print("OFFICIAL PLANNING-AREA CANDIDATE SCREENING")
    print("=" * 80)

    print()
    print(f"Sector: {SECTOR}")
    print(f"Total Sector {SECTOR} AEDs: {total_aeds:,}")

    print()
    print(
        f"{'Planning Area':<25}"
        f"{'Code':<10}"
        f"{'AEDs':>8}"
        f"{'Coverage':>12}"
    )

    print("-" * 80)

    for _, row in results.iterrows():

        print(
            f"{str(row['planning_area']):<25}"
            f"{str(row['planning_area_code']):<10}"
            f"{int(row['aed_count']):>8}"
            f"{row['coverage_pct']:>11.1%}"
        )

    print("-" * 80)

    covered_total = int(results["aed_count"].sum())

    print(
        f"Total AEDs covered by listed planning areas: "
        f"{covered_total:,}"
    )

    print()
    print(
        "IMPORTANT:"
    )
    print(
        "These results identify candidate official planning areas."
    )
    print(
        "They do NOT automatically select the final study boundary."
    )


# ---------------------------------------------------------------------
# Inspection map
# ---------------------------------------------------------------------

def create_map(
    aeds: gpd.GeoDataFrame,
    candidates: gpd.GeoDataFrame,
):
    """
    Create an interactive inspection map.

    The map shows:
    - Sector 73 AEDs
    - official planning-area candidate polygons
    """

    center_lat = float(aeds["lat"].mean())
    center_lon = float(aeds["lon"].mean())

    m = folium.Map(
        location=[center_lat, center_lon],
        zoom_start=12,
        control_scale=True,
    )

    # AED points
    aed_layer = folium.FeatureGroup(
        name=f"Sector {SECTOR} AEDs"
    )

    for _, row in aeds.iterrows():

        folium.CircleMarker(
            location=[row["lat"], row["lon"]],
            radius=3,
            weight=1,
            fill=True,
            fill_opacity=0.7,
            popup=(
                f"AED ID: {row.get('AED_ID', 'N/A')}<br>"
                f"Postal sector: {SECTOR}<br>"
                f"Building: "
                f"{row.get('BUILDING_NAME', 'N/A')}"
            ),
        ).add_to(aed_layer)

    aed_layer.add_to(m)

    # Planning areas
    candidate_layer = folium.FeatureGroup(
        name="Official planning-area candidates"
    )

    for _, row in candidates.iterrows():

        tooltip = (
            f"{row['planning_area']} "
            f"({row['planning_area_code']}) — "
            f"{row['aed_count']} AEDs "
            f"({row['coverage_pct']:.1%})"
        )

        folium.GeoJson(
            row.geometry.__geo_interface__,
            tooltip=tooltip,
            popup=tooltip,
        ).add_to(candidate_layer)

    candidate_layer.add_to(m)

    folium.LayerControl().add_to(m)

    m.save(MAP_PATH)

    print()
    print("Inspection map created:")
    print(f"  {MAP_PATH}")


# ---------------------------------------------------------------------
# Report
# ---------------------------------------------------------------------

def write_report(
    aeds: gpd.GeoDataFrame,
    candidates: gpd.GeoDataFrame,
):
    """Write machine-readable validation report."""

    report = {
        "sector": SECTOR,
        "total_sector_aeds": len(aeds),
        "official_dataset": {
            "dataset_id": DATASET_ID,
            "name": (
                "Master Plan 2025 Planning Area Boundary "
                "(No Sea)"
            ),
            "publisher": "Urban Redevelopment Authority",
            "source": "data.gov.sg",
            "sha256": sha256_file(
                OFFICIAL_BOUNDARY_PATH
            ),
        },
        "candidate_planning_areas": [],
        "method_notes": [
            (
                "AEDs were spatially tested against official planning "
                "area polygons."
            ),
            (
                "Polygon.covers() was used so points on polygon "
                "boundaries count as covered."
            ),
            (
                "The candidate ranking does not automatically determine "
                "the final study boundary."
            ),
        ],
    }

    for _, row in candidates.iterrows():

        report["candidate_planning_areas"].append(
            {
                "planning_area": row["planning_area"],
                "planning_area_code": row[
                    "planning_area_code"
                ],
                "aed_count": int(row["aed_count"]),
                "coverage_pct": float(
                    row["coverage_pct"]
                ),
            }
        )

    with open(
        REPORT_PATH,
        "w",
        encoding="utf-8",
    ) as f:

        json.dump(
            report,
            f,
            indent=2,
        )

    print()
    print("Validation report created:")
    print(f"  {REPORT_PATH}")


# ---------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------

def main():

    print("=" * 80)
    print("SECTOR 73 — OFFICIAL BOUNDARY VALIDATION")
    print("=" * 80)

    if not AED_PATH.exists():
        raise FileNotFoundError(
            f"Frozen AED dataset not found:\n{AED_PATH}"
        )

    download_official_boundary()

    aeds = load_aeds()

    planning_areas = load_official_boundaries()

    candidates = calculate_candidate_metrics(
        aeds,
        planning_areas,
    )

    if candidates.empty:
        raise RuntimeError(
            "No official planning areas contain Sector 73 AEDs."
        )

    print_results(
        candidates,
        len(aeds),
    )

    create_map(
        aeds,
        candidates,
    )

    write_report(
        aeds,
        candidates,
    )

    print()
    print("=" * 80)
    print("NEXT STEP")
    print("=" * 80)
    print(
        "Open the generated HTML map and inspect the candidate "
        "planning-area boundaries."
    )
    print()
    print(
        "DO NOT create data/district_boundary.geojson yet."
    )
    print(
        "DO NOT start pedestrian-network construction yet."
    )


if __name__ == "__main__":
    main()