from pathlib import Path
from collections import Counter
import sys
import json

PROJECT_ROOT = Path(__file__).resolve().parents[1]

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from nlp.hours_parser import parse_hours_normalized


GEOJSON_PATH = Path("data/scdf_aed_frozen.geojson")


with GEOJSON_PATH.open(encoding="utf-8") as f:
    data = json.load(f)


schedules = sorted(
    {
        feature.get("properties", {}).get("OPERATING_HOURS")
        for feature in data["features"]
        if feature.get("properties", {}).get("OPERATING_HOURS")
    }
)


status_counts = Counter()
failures = []


for raw in schedules:
    try:
        parsed = parse_hours_normalized(raw)

        status_counts[parsed.get("status")] += 1

        if parsed.get("cannot_parse"):
            failures.append(
                {
                    "raw": raw,
                    "parsed": parsed,
                }
            )

    except Exception as exc:
        failures.append(
            {
                "raw": raw,
                "error": repr(exc),
            }
        )


print("=" * 80)
print("REAL-WORLD HOURS AUDIT")
print("=" * 80)

print(f"Unique schedules: {len(schedules)}")
print()

print("STATUS DISTRIBUTION")
for status, count in status_counts.most_common():
    print(f"{status!r}: {count}")

print()
print(f"FAILURES: {len(failures)}")
print("=" * 80)

for i, failure in enumerate(failures, 1):
    print()
    print(f"[{i}]")
    print("RAW:")
    print(failure["raw"])

    if "error" in failure:
        print("EXCEPTION:")
        print(failure["error"])
    else:
        print("PARSED:")
        print(failure["parsed"])