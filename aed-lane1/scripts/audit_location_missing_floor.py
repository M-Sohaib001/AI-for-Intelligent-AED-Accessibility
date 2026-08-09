"""
Focused audit of AED records where AED_LOCATION_FLOOR_LEVEL is missing.

Purpose:
    Determine whether missing floor information is genuinely absent,
    or whether useful floor/level information is already embedded in
    AED_LOCATION_DESCRIPTION.

This is an investigation script only.
It does not modify the frozen dataset.
"""

import json
import re
import sys
from collections import Counter
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

DATA_PATH = PROJECT_ROOT / "data" / "scdf_aed_frozen.geojson"

# Patterns worth investigating
FLOOR_PATTERNS = [
    re.compile(r"\blevel\s+[A-Za-z0-9]+", re.IGNORECASE),
    re.compile(r"\bfloor\s+[A-Za-z0-9]+", re.IGNORECASE),
    re.compile(r"\bground\s+floor\b", re.IGNORECASE),
    re.compile(r"\bground\s+level\b", re.IGNORECASE),
    re.compile(r"\bbasement\b", re.IGNORECASE),
    re.compile(r"\bB\d+[A-Za-z]*\b", re.IGNORECASE),
]

# Helpers
def load_features():
    if not DATA_PATH.exists():
        raise FileNotFoundError(
            f"Missing dataset: {DATA_PATH}"
        )

    with DATA_PATH.open(encoding="utf-8") as f:
        data = json.load(f)

    features = data.get("features")

    if not isinstance(features, list):
        raise RuntimeError(
            "Dataset does not contain a valid 'features' list."
        )

    return features


def find_embedded_floor_references(description):
    """Return floor-like references found inside the description."""

    if not description:
        return []

    matches = []

    for pattern in FLOOR_PATTERNS:
        for match in pattern.findall(description):
            if match not in matches:
                matches.append(match)

    return matches


def main():
    features = load_features()

    missing_floor_records = []

    for index, feature in enumerate(features):
        properties = feature.get("properties", {})

        floor = properties.get(
            "AED_LOCATION_FLOOR_LEVEL"
        )

        if floor is not None and str(floor).strip():
            continue

        description = properties.get(
            "AED_LOCATION_DESCRIPTION",
            "",
        )

        embedded = find_embedded_floor_references(
            description
        )

        missing_floor_records.append(
            {
                "index": index,
                "aed_id": properties.get("AED_ID"),
                "description": description,
                "embedded_floor": embedded,
            }
        )

    print("MISSING FLOOR INFORMATION AUDIT")
    print()
    print(
        f"Records with missing floor: "
        f"{len(missing_floor_records)}"
    )
    print()

    # Embedded floor information
    embedded_records = [
        record
        for record in missing_floor_records
        if record["embedded_floor"]
    ]

    print("EMBEDDED FLOOR INFORMATION")
    print(
        f"Records with floor-like information "
        f"in description: {len(embedded_records)}"
    )
    print(
        f"Records with no detected floor-like information: "
        f"{len(missing_floor_records) - len(embedded_records)}"
    )
    print()

    # Embedded reference distribution
    reference_counts = Counter()

    for record in embedded_records:
        for reference in record["embedded_floor"]:
            reference_counts[reference.lower()] += 1

    if reference_counts:
        print("EMBEDDED FLOOR REFERENCES")

        for reference, count in reference_counts.most_common():
            print(
                f"{count:>5}  {reference!r}"
            )

        print()

    # Examples with embedded floor information
    print("EXAMPLES WITH EMBEDDED FLOOR INFORMATION")

    if not embedded_records:
        print("None.")
    else:
        for record in embedded_records:
            print(
                f"index={record['index']} "
                f"AED_ID={record['aed_id']!r}"
            )
            print(
                f"  description={record['description']!r}"
            )
            print(
                f"  detected={record['embedded_floor']!r}"
            )

    print()

    # Examples with genuinely missing-looking floor information
    no_embedded_records = [
        record
        for record in missing_floor_records
        if not record["embedded_floor"]
    ]

    print("EXAMPLES WITHOUT DETECTED FLOOR INFORMATION")

    if not no_embedded_records:
        print("None.")
    else:
        for record in no_embedded_records:
            print(
                f"index={record['index']} "
                f"AED_ID={record['aed_id']!r}"
            )
            print(
                f"  description={record['description']!r}"
            )

    print()

    print(
        f"# MISSING FLOOR RECORDS: "
        f"{len(missing_floor_records)}"
    )

    print(
        f"# EMBEDDED FLOOR REFERENCES: "
        f"{len(embedded_records)}"
    )

    print(
        f"# NO DETECTED FLOOR REFERENCES: "
        f"{len(no_embedded_records)}"
    )


if __name__ == "__main__":
    main()