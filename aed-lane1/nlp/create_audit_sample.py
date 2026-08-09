import json
import random
from pathlib import Path


INPUT_PATH = Path("data/aeds_clean.json")
OUTPUT_DIR = Path("data/audit")
OUTPUT_PATH = OUTPUT_DIR / "parser_location_audit_sample.json"

RANDOM_SEED = 42
TARGET_SIZE = 200


def load_records():
    with INPUT_PATH.open("r", encoding="utf-8") as f:
        return json.load(f)


def has_flag(record, flag):
    return flag in record.get("location_info", {}).get("flags", [])


def select_random(records, count, rng):
    """Randomly select up to count records."""
    if len(records) <= count:
        return list(records)

    return rng.sample(records, count)


def main():
    rng = random.Random(RANDOM_SEED)

    records = load_records()

    print(f"Loaded {len(records)} records.")

    selected = {}
    
    def add_records(candidates, count, reason):
        candidates = [
            r for r in candidates
            if r.get("aed_id") not in selected
        ]

        chosen = select_random(candidates, count, rng)

        for record in chosen:
            selected[record["aed_id"]] = {
                "record": record,
                "selection_reasons": [reason],
            }

    # 1. Exhaust rare hours categories
    unknown = [
        r for r in records
        if r.get("parsed_hours", {}).get("status") == "unknown"
    ]

    complex_records = [
        r for r in records
        if r.get("parsed_hours", {}).get("status") == "complex"
    ]

    add_records(
        unknown,
        len(unknown),
        "hours_unknown",
    )

    add_records(
        complex_records,
        len(complex_records),
        "hours_complex",
    )

    # 2. Sample closed records
    closed = [
        r for r in records
        if r.get("parsed_hours", {}).get("status") == "closed"
    ]

    add_records(
        closed,
        min(30, len(closed)),
        "hours_closed",
    )

    # 3. Sample dominant hours categories
    always_open = [
        r for r in records
        if r.get("parsed_hours", {}).get("status") == "always_open"
    ]

    scheduled = [
        r for r in records
        if r.get("parsed_hours", {}).get("status") == "scheduled"
    ]

    add_records(
        always_open,
        40,
        "hours_always_open",
    )

    add_records(
        scheduled,
        40,
        "hours_scheduled",
    )

    # 4. Target location cases
    # These are deliberately sampled because location categories overlap.
    location_targets = [
        (
            "relational_location",
            lambda r: has_flag(r, "relational_location"),
            15,
        ),
        (
            "missing_floor_info",
            lambda r: has_flag(r, "missing_floor_info"),
            15,
        ),
        (
            "possible_indoor_access",
            lambda r: has_flag(r, "possible_indoor_access"),
            15,
        ),
        (
            "possible_building_internal_location",
            lambda r: has_flag(
                r,
                "possible_building_internal_location",
            ),
            15,
        ),
    ]

    for reason, predicate, count in location_targets:
        candidates = [r for r in records if predicate(r)]

        add_records(
            candidates,
            count,
            reason,
        )

    # 5. Fill remaining slots with a random population sample
    remaining = [
        r for r in records
        if r.get("aed_id") not in selected
    ]

    remaining_needed = max(0, TARGET_SIZE - len(selected))

    add_records(
        remaining,
        remaining_needed,
        "random_population_sample",
    )

    # 6. Build output
    audit_records = []

    for item in selected.values():
        record = dict(item["record"])

        audit_records.append(
            {
                "aed_id": record.get("aed_id"),
                "raw_operating_hours": record.get(
                    "raw_operating_hours"
                ),
                "parsed_hours": record.get("parsed_hours"),

                "raw_location_description": record.get(
                    "raw_location_description"
                ),
                "raw_floor_level": record.get(
                    "raw_floor_level"
                ),
                "location_info": record.get(
                    "location_info"
                ),

                "selection_reasons": item[
                    "selection_reasons"
                ],

                # These are intentionally left for manual auditing.
                "manual_audit": {
                    "hours_correct": None,
                    "location_flags_correct": None,
                    "notes": "",
                },
            }
        )

    # Stable ordering for reproducibility.
    audit_records.sort(key=lambda x: x["aed_id"] or "")

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    with OUTPUT_PATH.open("w", encoding="utf-8") as f:
        json.dump(
            audit_records,
            f,
            indent=2,
            ensure_ascii=False,
        )

    # 7. Print summary
    print()
    print("Audit sample created.")
    print(f"Total audit records: {len(audit_records)}")
    print(f"Output: {OUTPUT_PATH}")
    print(f"Random seed: {RANDOM_SEED}")

    print()
    print("Selection reasons:")

    reason_counts = {}

    for record in audit_records:
        for reason in record["selection_reasons"]:
            reason_counts[reason] = (
                reason_counts.get(reason, 0) + 1
            )

    for reason, count in sorted(reason_counts.items()):
        print(f"  {reason}: {count}")


if __name__ == "__main__":
    main()