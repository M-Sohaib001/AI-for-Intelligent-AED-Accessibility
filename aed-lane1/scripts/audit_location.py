"""
Audit real-world AED location descriptions using location_flagger.py.

Input:
    data/scdf_aed_frozen.geojson

Purpose:
    1. Run the location flagger against every AED record.
    2. Report the distribution of semantic location flags.
    3. Show representative real-world examples for each flag.
    4. Identify records with missing description/floor information.
    5. Verify that the flagger does not fail on real-world data.
    6. Provide evidence for deciding whether the current location
       vocabulary needs refinement.

Important:
    - This script NEVER modifies the frozen raw dataset.
    - Flags are semantic indicators, not automatic failures.
    - A floor reference is informative and is not treated as ambiguity.
"""

import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


from nlp.location_flagger import flag_location

DATA_PATH = PROJECT_ROOT / "data" / "scdf_aed_frozen.geojson"

# Audit config
EXAMPLES_PER_FLAG = 5

EXPECTED_FLAGS = [
    "missing_description",
    "missing_floor_info",
    "floor_reference",
    "relational_location",
    "possible_indoor_access",
    "possible_building_internal_location",
]

# Dataset loading
def load_features():
    """Load the frozen SCDF AED GeoJSON features."""

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

# Main audit
def main():
    print("REAL-WORLD LOCATION AUDIT")
    print()

    features = load_features()

    print(f"Total records: {len(features)}")
    print()

    flag_counts = Counter()
    combination_counts = Counter()

    examples = defaultdict(list)

    failures = []

    missing_description_count = 0
    missing_floor_count = 0

    records_with_flags = 0
    records_without_flags = 0

    # Process every AED
    for index, feature in enumerate(features):
        try:
            properties = feature.get("properties", {})

            description = properties.get(
                "AED_LOCATION_DESCRIPTION",
                "",
            )

            floor = properties.get(
                "AED_LOCATION_FLOOR_LEVEL",
                "",
            )

            result = flag_location(
                description,
                floor,
            )

            flags = result.get("flags", [])

            # Basic counts
            if "missing_description" in flags:
                missing_description_count += 1

            if "missing_floor_info" in flags:
                missing_floor_count += 1

            if flags:
                records_with_flags += 1
            else:
                records_without_flags += 1

            # Count individual flags
            for flag in flags:
                flag_counts[flag] += 1

                if len(examples[flag]) < EXAMPLES_PER_FLAG:
                    examples[flag].append(
                        {
                            "index": index,
                            "aed_id": properties.get("AED_ID"),
                            "description": description,
                            "floor": floor,
                        }
                    )

            # Count flag combinations
            combination = tuple(sorted(flags))

            combination_counts[combination] += 1

        except Exception as exc:
            failures.append(
                {
                    "index": index,
                    "error": repr(exc),
                }
            )

    # Status distribution
    print("FLAG DISTRIBUTION")

    for flag in EXPECTED_FLAGS:
        print(
            f"{flag!r}: {flag_counts[flag]}"
        )

    # Report any unexpected flags instead of silently ignoring them.
    unexpected_flags = sorted(
        set(flag_counts) - set(EXPECTED_FLAGS)
    )

    if unexpected_flags:
        print()
        print("UNEXPECTED FLAGS")

        for flag in unexpected_flags:
            print(
                f"{flag!r}: {flag_counts[flag]}"
            )

    print()

    # Record-level summary
    print("RECORD SUMMARY")

    print(
        f"records with at least one flag: "
        f"{records_with_flags}"
    )

    print(
        f"records with no flags: "
        f"{records_without_flags}"
    )

    print(
        f"missing descriptions: "
        f"{missing_description_count}"
    )

    print(
        f"missing floor information: "
        f"{missing_floor_count}"
    )

    print()

    # Flag combinations
    print("TOP FLAG COMBINATIONS")

    for combination, count in combination_counts.most_common(15):
        label = (
            "none"
            if not combination
            else " + ".join(combination)
        )

        print(
            f"{count:>5}  {label}"
        )

    print()

    # Representative examples
    print("REPRESENTATIVE EXAMPLES")

    for flag in EXPECTED_FLAGS:
        print()
        print(f"[{flag}]")

        flag_examples = examples.get(flag, [])

        if not flag_examples:
            print("  No examples.")
            continue

        for example in flag_examples:
            print(
                f"  index={example['index']} "
                f"AED_ID={example['aed_id']!r}"
            )
            print(
                f"    description={example['description']!r}"
            )
            print(
                f"    floor={example['floor']!r}"
            )

    # Failures
    print()
    print(f"# FAILURES: {len(failures)}")

    if failures:
        for failure in failures[:20]:
            print(
                f"index={failure['index']}: "
                f"{failure['error']}"
            )

        if len(failures) > 20:
            print(
                f"... {len(failures) - 20} additional failures"
            )

    print()

    # Final result
    if failures:
        print("AUDIT STATUS: FAILED")
        raise SystemExit(1)

    print("AUDIT STATUS: PASSED")


if __name__ == "__main__":
    main()