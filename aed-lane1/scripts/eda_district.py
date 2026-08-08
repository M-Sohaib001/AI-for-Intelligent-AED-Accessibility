import json
from pathlib import Path

import pandas as pd


AED_DATASET = Path("data/scdf_aed_frozen.geojson")
OUTPUT_PATH = Path("data/district_eda_summary.json")


def load_aed_dataset(path: Path) -> pd.DataFrame:
    """Load the frozen AED GeoJSON into a DataFrame."""

    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    rows = []

    for feature in data["features"]:
        properties = feature["properties"]
        coordinates = feature["geometry"]["coordinates"]

        lon, lat = coordinates

        rows.append({
            **properties,
            "lon": lon,
            "lat": lat,
        })

    return pd.DataFrame(rows)


def run_district_eda(
    clean_df: pd.DataFrame,
    output_path=OUTPUT_PATH,
):
    """Generate the descriptive EDA summary for the study area."""

    summary = {
        "aed_count": len(clean_df),

        "always_open_pct": (
            clean_df["OPERATING_HOURS"]
            .fillna("")
            .str.contains("00:00-23:59")
        ).mean(),

        "has_remarks_pct": (
            clean_df["OPERATING_HOURS"]
            .fillna("")
            .str.contains("Remark", case=False)
        ).mean(),

        "multi_segment_pct": (
            clean_df["OPERATING_HOURS"]
            .fillna("")
            .str.count(";") > 1
        ).mean(),

        "unknown_hours_pct": (
            clean_df["OPERATING_HOURS"]
            .fillna("")
            .str.strip() == ""
        ).mean(),

        "missing_floor_pct": (
            clean_df["AED_LOCATION_FLOOR_LEVEL"]
            .fillna("")
            .str.strip() == ""
        ).mean(),

        "building_diversity": (
            clean_df["BUILDING_NAME"]
            .nunique()
        ),

        "relational_language_pct": (
            clean_df["AED_LOCATION_DESCRIPTION"]
            .fillna("")
            .str.lower()
            .str.contains(
                "near|beside|opposite|behind"
            )
        ).mean(),
    }

    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)

    print("\nDistrict EDA summary:")
    print(json.dumps(summary, indent=2))

    print(f"\nSaved to: {output_path}")

    return summary


def main():
    print("Loading frozen AED dataset...")

    df = load_aed_dataset(AED_DATASET)

    print(f"Loaded {len(df):,} AED records.")

    # ---------------------------------------------------------
    # Restrict to frozen study area.
    #
    # Sector 73 contains 529 AEDs.
    # The frozen official Woodlands boundary contains 522 of them.
    #
    # We use the frozen boundary rather than re-selecting the
    # district here.
    # ---------------------------------------------------------

    boundary_path = Path("data/district_boundary.geojson")

    if not boundary_path.exists():
        raise FileNotFoundError(
            "Frozen district boundary not found: "
            f"{boundary_path}"
        )

    import geopandas as gpd

    boundary = gpd.read_file(boundary_path)

    aed_gdf = gpd.GeoDataFrame(
        df,
        geometry=gpd.points_from_xy(
            df["lon"],
            df["lat"],
        ),
        crs="EPSG:4326",
    )

    # Make sure boundary and AED points use the same CRS.
    boundary = boundary.to_crs(aed_gdf.crs)

    # Keep AEDs covered by the frozen official boundary.
    study_area_gdf = gpd.sjoin(
        aed_gdf,
        boundary[["geometry"]],
        how="inner",
        predicate="covered_by",
    )

    study_area_df = pd.DataFrame(
        study_area_gdf.drop(
            columns=["geometry", "index_right"],
            errors="ignore",
        )
    )

    print(
        f"AED records inside frozen study boundary: "
        f"{len(study_area_df):,}"
    )

    run_district_eda(
        study_area_df,
        OUTPUT_PATH,
    )


if __name__ == "__main__":
    main()