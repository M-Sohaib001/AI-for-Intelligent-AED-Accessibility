"""
Maintenance utility.

Re-runs the current hours_parser against an existing
data/aeds_clean.json without rebuilding the dataset.

Normal dataset generation should use:
    build_clean_dataset.py

Use this script only when:
    - hours_parser.py has changed, and
    - you want to update parsed_hours in an existing clean dataset.

A backup of the existing dataset is created before replacement.
"""

import json
import shutil
from pathlib import Path

from hours_parser import parse_hours


INPUT_PATH = Path("data/aeds_clean.json")
BACKUP_PATH = Path("data/aeds_clean.before_parser_regeneration.json")
TEMP_PATH = Path("data/aeds_clean.regenerated.json")


def main():
    # 1. Load existing dataset
    with INPUT_PATH.open("r", encoding="utf-8") as f:
        records = json.load(f)

    print(f"Loaded {len(records)} records.")

    # 2. Create backup
    shutil.copy2(INPUT_PATH, BACKUP_PATH)
    print(f"Backup created: {BACKUP_PATH}")

    changed = 0
    failed = 0

    # 3. Re-run the CURRENT parser on every record
    for i, record in enumerate(records, 1):
        raw_hours = record.get("raw_operating_hours")

        if not raw_hours:
            continue

        try:
            new_parsed_hours = parse_hours(raw_hours)

            old_parsed_hours = record.get("parsed_hours")

            if old_parsed_hours != new_parsed_hours:
                changed += 1

            record["parsed_hours"] = new_parsed_hours

        except Exception as exc:
            failed += 1
            print(
                f"ERROR on record {i} "
                f"(aed_id={record.get('aed_id')}): {exc}"
            )

    # 4. Write regenerated dataset to temporary file first
    with TEMP_PATH.open("w", encoding="utf-8") as f:
        json.dump(
            records,
            f,
            indent=2,
            ensure_ascii=False,
        )

    # 5. Replace original only after successful write
    TEMP_PATH.replace(INPUT_PATH)

    print()
    print("Parser regeneration complete.")
    print(f"Total records: {len(records)}")
    print(f"Records changed: {changed}")
    print(f"Records failed: {failed}")
    print(f"Updated dataset: {INPUT_PATH}")
    print(f"Backup: {BACKUP_PATH}")


if __name__ == "__main__":
    main()