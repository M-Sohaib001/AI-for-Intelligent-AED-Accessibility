import json

with open("data/audit/parser_location_audit_sample.json", encoding="utf-8") as f:
    data = json.load(f)

for i, x in enumerate(data, 1):
    if x.get("parsed_hours", {}).get("status") == "complex":
        print(
            f"{i}. "
            f"RAW: {x.get('raw_operating_hours')} | "
            f"PARSED: {x.get('parsed_hours')}"
        )
