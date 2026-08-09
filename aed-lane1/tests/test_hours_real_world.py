import json
from pathlib import Path

import pytest

from nlp.hours_parser import parse_hours_normalized, is_open_at


GEOJSON_PATH = Path("data/scdf_aed_frozen.geojson")


@pytest.fixture(scope="module")
def schedules():
    with GEOJSON_PATH.open(encoding="utf-8") as f:
        data = json.load(f)

    return sorted(
        {
            feature.get("properties", {}).get("OPERATING_HOURS")
            for feature in data["features"]
            if feature.get("properties", {}).get("OPERATING_HOURS")
        }
    )


def test_all_real_world_schedules_can_be_parsed(schedules):
    failures = []

    for raw in schedules:
        try:
            parsed = parse_hours_normalized(raw)
        except Exception as exc:
            failures.append(
                {
                    "raw": raw,
                    "error": repr(exc),
                }
            )
            continue

        assert isinstance(parsed, dict)

        if parsed.get("cannot_parse"):
            continue

        windows = parsed.get("windows", [])

        if not isinstance(windows, list):
            failures.append(
                {
                    "raw": raw,
                    "error": f"windows is not a list: {windows!r}",
                }
            )

    if failures:
        pytest.fail(
            "\n\n".join(
                f"RAW: {x['raw']}\nERROR: {x['error']}"
                for x in failures
            )
        )


def test_real_world_schedules_are_evaluable(schedules):
    """
    Smoke-test is_open_at() against every real-world schedule.

    We deliberately don't assert whether the AED is open because
    this test is validating parser/evaluator robustness rather than
    ground-truth business semantics.
    """

    from datetime import datetime

    # Monday through Sunday.
    dates = [
        datetime(2026, 8, 10, 0, 0),
        datetime(2026, 8, 10, 6, 0),
        datetime(2026, 8, 10, 12, 0),
        datetime(2026, 8, 10, 18, 0),
        datetime(2026, 8, 10, 23, 30),
        datetime(2026, 8, 15, 0, 15),
        datetime(2026, 8, 16, 12, 0),
        datetime(2026, 8, 16, 23, 30),
    ]

    failures = []

    for raw in schedules:
        try:
            parsed = parse_hours_normalized(raw)

            for dt in dates:
                result = is_open_at(parsed, dt)

                assert result in (True, False, None)

        except Exception as exc:
            failures.append(
                {
                    "raw": raw,
                    "error": repr(exc),
                }
            )

    if failures:
        pytest.fail(
            "\n\n".join(
                f"RAW: {x['raw']}\nERROR: {x['error']}"
                for x in failures
            )
        )