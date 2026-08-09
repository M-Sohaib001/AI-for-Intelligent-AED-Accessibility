import json
from pathlib import Path

from hours_parser import parse_hours
from location_flagger import flag_location

# Config
INPUT_PATH = Path("data/scdf_aed_frozen.geojson")
OUTPUT_PATH = Path("data/aeds_clean.json")

# Helpers
def clean_string(value) -> str:
    """Convert null-like values to an empty string."""
    if value is None:
        return ""

    return str(value).strip()


def hours_parse_status(parsed_hours: dict) -> str:
    """
    Convert the hours parser's status into the dataset-level
    quality status used by the roadmap.
    """
    status = parsed_hours.get("status")

    if status in ("always_open", "scheduled", "closed"):
        return "parsed"

    if status == "complex":
        return "partial"

    return "unknown"

# Record builder
def build_clean_record(feature: dict) -> dict:
    """
    Build one normalized AED record from one GeoJSON Feature.

    The raw source schema is:

        feature["properties"]
        feature["geometry"]["coordinates"]

    No district filtering or graph information is performed here.
    """

    properties = feature.get("properties") or {}
    geometry = feature.get("geometry") or {}

    # Extracting raw fields
    aed_id = clean_string(properties.get("AED_ID"))

    operating_hours = clean_string(
        properties.get("OPERATING_HOURS")
    )

    location_description = clean_string(
        properties.get("AED_LOCATION_DESCRIPTION")
    )

    floor_level = clean_string(
        properties.get("AED_LOCATION_FLOOR_LEVEL")
    )

    # Coordinates

    # The source already provides LATITUDE/LONGITUDE, but the GeoJSON
    # geometry is also available. Prefer the explicit dataset fields when
    # present and fall back to geometry coordinates when necessary.

    latitude = properties.get("LATITUDE")
    longitude = properties.get("LONGITUDE")

    coordinates = geometry.get("coordinates")

    if (latitude is None or longitude is None) and isinstance(
        coordinates, (list, tuple)
    ) and len(coordinates) >= 2:

        # GeoJSON Point coordinates are [longitude, latitude].
        longitude = coordinates[0]
        latitude = coordinates[1]

    # Parsing hours and location
    parsed_hours = parse_hours(operating_hours)

    location_info = flag_location(
        location_description,
        floor_level,
    )

    location_flags = location_info.get("flags", [])

    # Building canonical clean record
    return {
        "aed_id": aed_id,

        "lat": latitude,
        "lon": longitude,

        "raw_operating_hours": operating_hours,
        "raw_location_description": location_description,
        "raw_floor_level": floor_level,

        "parsed_hours": parsed_hours,

        "location_info": {
            "floor": location_info.get("floor", floor_level),
            "flags": location_flags,
        },

        "data_quality": {
            "hours_parse_status": hours_parse_status(parsed_hours),
            "location_flags": location_flags,
            "floor_present": bool(floor_level),
        },

        # IMPORTANT:
        # hours_confidence_score and registry_anomaly_flags are intentionally
        # NOT added here. They belong to the later Phase 3 Bucket A step.
    
        # graph_info is also intentionally NOT added here. Person A will
        # append it later.
    }

# Dataset loader
def load_geojson(path: Path) -> list[dict]:
    """
    Load the complete AED GeoJSON FeatureCollection.

    No district filtering is performed.
    """

    if not path.exists():
        raise FileNotFoundError(
            f"Input dataset not found: {path}"
        )

    with path.open("r", encoding="utf-8") as f:
        data = json.load(f)

    if data.get("type") != "FeatureCollection":
        raise ValueError(
            "Expected a GeoJSON FeatureCollection."
        )

    features = data.get("features")

    if not isinstance(features, list):
        raise ValueError(
            "GeoJSON FeatureCollection does not contain a valid "
            "'features' list."
        )

    return features


def main():
    print(f"Loading dataset: {INPUT_PATH}")

    features = load_geojson(INPUT_PATH)

    print(f"Found {len(features)} AED features.")
    print("Cleaning complete dataset...")

    clean_records = []

    for index, feature in enumerate(features, start=1):

        try:
            record = build_clean_record(feature)
            clean_records.append(record)

        except Exception as exc:
            aed_id = (
                feature.get("properties", {}).get("AED_ID", "UNKNOWN")
            )

            raise RuntimeError(
                f"Failed to process AED {aed_id} "
                f"(feature {index}): {exc}"
            ) from exc

    # Ensure output directory exists.
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)

    with OUTPUT_PATH.open("w", encoding="utf-8") as f:
        json.dump(
            clean_records,
            f,
            indent=2,
            ensure_ascii=False,
        )

    print()
    print("Cleaning complete.")
    print(f"Records written: {len(clean_records)}")
    print(f"Output: {OUTPUT_PATH}")


if __name__ == "__main__":
    main()