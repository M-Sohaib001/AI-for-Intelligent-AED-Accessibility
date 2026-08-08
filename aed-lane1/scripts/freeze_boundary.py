import argparse
import json
from pathlib import Path

import geopandas as gpd
import pandas as pd
import folium
from shapely.geometry import MultiPoint


RAW_PATH = Path("data/scdf_aed_frozen.geojson")
OUTPUT_DIR = Path("data")


def load_aeds():
    with RAW_PATH.open(encoding="utf-8") as f:
        data = json.load(f)

    rows = []

    for feature in data["features"]:
        geometry = feature.get("geometry")
        props = feature.get("properties", {})

        if not geometry or geometry.get("type") != "Point":
            continue

        lon, lat = geometry["coordinates"]

        postal = str(props.get("POSTAL_CODE", "")).strip()

        # Handle values that may have arrived as floats.
        postal = postal.replace(".0", "").zfill(6)

        rows.append({
            "aed_id": props.get("AED_ID"),
            "postal_code": postal,
            "postal_sector": postal[:2],
            "lat": lat,
            "lon": lon,
            "description": props.get(
                "AED_LOCATION_DESCRIPTION", ""
            ),
        })

    df = pd.DataFrame(rows)

    if df.empty:
        raise RuntimeError("No AED records found.")

    return df


def build_candidate_boundary(df, sector):
    subset = df[df["postal_sector"] == sector].copy()

    if len(subset) < 3:
        raise RuntimeError(
            f"Sector {sector} contains fewer than 3 AEDs."
        )

    points = gpd.GeoSeries(
        gpd.points_from_xy(
            subset["lon"],
            subset["lat"],
        ),
        crs="EPSG:4326",
    )

    # Project to Singapore SVY21 for meaningful metric calculations.
    points_projected = points.to_crs("EPSG:3414")

    hull = points_projected.union_all().convex_hull

    boundary = gpd.GeoDataFrame(
        {
            "postal_sector": [sector],
            "source": [
                "Convex hull of AED locations — candidate only"
            ],
        },
        geometry=[hull],
        crs="EPSG:3414",
    )

    return subset, boundary


def calculate_metrics(aeds, boundary):
    points = gpd.GeoDataFrame(
        aeds.copy(),
        geometry=gpd.points_from_xy(
            aeds["lon"],
            aeds["lat"],
        ),
        crs="EPSG:4326",
    )

    points_projected = points.to_crs("EPSG:3414")

    boundary_projected = boundary.to_crs("EPSG:3414")

    inside = points_projected.within(
        boundary_projected.geometry.iloc[0]
    )

    selected = points["postal_sector"] == (
        aeds["postal_sector"].iloc[0]
    )

    selected_points = points_projected[selected]

    contained_count = int(
        boundary_projected.geometry.iloc[0].covers(
            selected_points.geometry
        ).sum()
    )

    sector_count = int(selected.sum())

    area_km2 = (
        boundary_projected.geometry.iloc[0].area
        / 1_000_000
    )

    minx, miny, maxx, maxy = (
        boundary_projected.total_bounds
    )

    bbox_area_km2 = (
        (maxx - minx) * (maxy - miny)
    ) / 1_000_000

    compactness = (
        area_km2 / bbox_area_km2
        if bbox_area_km2 > 0
        else 0
    )

    return {
        "sector": aeds["postal_sector"].iloc[0],
        "aed_count": sector_count,
        "aed_points_inside_candidate_boundary": contained_count,
        "containment_rate": (
            contained_count / sector_count
            if sector_count
            else 0
        ),
        "candidate_area_km2": area_km2,
        "bounding_box_area_km2": bbox_area_km2,
        "compactness": compactness,
    }


def create_map(aeds, boundary, sector):
    boundary_wgs84 = boundary.to_crs("EPSG:4326")

    centroid = boundary_wgs84.geometry.iloc[0].centroid

    m = folium.Map(
        location=[
            centroid.y,
            centroid.x,
        ],
        zoom_start=12,
    )

    folium.GeoJson(
        boundary_wgs84.to_json(),
        name=f"Sector {sector} candidate boundary",
        tooltip=f"Sector {sector} — candidate only",
    ).add_to(m)

    selected = aeds[
        aeds["postal_sector"] == sector
    ]

    for _, row in selected.iterrows():
        folium.CircleMarker(
            location=[
                row["lat"],
                row["lon"],
            ],
            radius=2,
            popup=str(row["aed_id"]),
        ).add_to(m)

    folium.LayerControl().add_to(m)

    output = Path(
        f"scripts/sector_{sector}_inspection.html"
    )

    m.save(output)

    return output


def main():
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--sector",
        required=True,
        help="Two-digit postal sector to inspect.",
    )

    args = parser.parse_args()

    sector = str(args.sector).zfill(2)

    print(
        f"Loading AED dataset for sector {sector}..."
    )

    df = load_aeds()

    subset, boundary = build_candidate_boundary(
        df,
        sector,
    )

    metrics = calculate_metrics(
        subset,
        boundary,
    )

    print()
    print("Candidate boundary metrics")
    print("--------------------------")

    for key, value in metrics.items():
        if isinstance(value, float):
            print(f"{key}: {value:.4f}")
        else:
            print(f"{key}: {value}")

    boundary_path = (
        OUTPUT_DIR
        / f"sector_{sector}_candidate_boundary.geojson"
    )

    boundary.to_crs("EPSG:4326").to_file(
        boundary_path,
        driver="GeoJSON",
    )

    map_path = create_map(
        df,
        boundary,
        sector,
    )

    report_path = (
        OUTPUT_DIR
        / f"sector_{sector}_boundary_report.json"
    )

    with report_path.open(
        "w",
        encoding="utf-8",
    ) as f:
        json.dump(
            metrics,
            f,
            indent=2,
        )

    print()
    print("Files created:")
    print(f"  {boundary_path}")
    print(f"  {report_path}")
    print(f"  {map_path}")

    print()
    print(
        "IMPORTANT: this is a CANDIDATE boundary."
    )
    print(
        "Do not use it as the final study boundary yet."
    )


if __name__ == "__main__":
    main()