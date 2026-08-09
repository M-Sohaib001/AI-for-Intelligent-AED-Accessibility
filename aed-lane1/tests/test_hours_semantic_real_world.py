import json
from datetime import datetime, timedelta
from pathlib import Path

import pytest

from nlp.hours_parser import parse_hours_normalized, is_open_at


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATASET = PROJECT_ROOT / "data" / "scdf_aed_frozen.geojson"


def load_real_world_schedules():
    with DATASET.open(encoding="utf-8") as f:
        data = json.load(f)

    schedules = sorted(
        {
            feature.get("properties", {}).get("OPERATING_HOURS")
            for feature in data["features"]
            if isinstance(
                feature.get("properties", {}).get("OPERATING_HOURS"),
                str,
            )
            and feature.get("properties", {}).get("OPERATING_HOURS").strip()
        }
    )

    return schedules


REAL_WORLD_SCHEDULES = load_real_world_schedules()


def _parse(raw):
    parsed = parse_hours_normalized(raw)

    assert parsed["cannot_parse"] is False, (
        f"\nCould not parse real-world schedule:"
        f"\n{raw}"
        f"\nParsed: {parsed}"
    )

    return parsed


def _contains_time(text):
    """
    Return True when the schedule contains at least one
    recognizable HH:MM time expression.
    """
    import re

    return bool(re.search(r"\b\d{2}:\d{2}\b", text))



# 1. EVERY REAL-WORLD STRING REMAINS EVALUABLE
def test_every_real_world_schedule_is_evaluable():
    """
    Every real-world schedule must produce a deterministic
    parser result that is not marked as unparseable.
    """

    for raw in REAL_WORLD_SCHEDULES:
        parsed = _parse(raw)

        assert parsed["status"] in {
            "scheduled",
            "complex",
            "always_open",
            "closed",
        }, (
            f"\nUnexpected status:"
            f"\nRAW: {raw}"
            f"\nPARSED: {parsed}"
        )



# 2. SCHEDULED / COMPLEX RECORDS MUST HAVE WINDOWS
def test_real_world_scheduled_records_have_windows():
    for raw in REAL_WORLD_SCHEDULES:
        parsed = _parse(raw)

        if parsed["status"] in {"scheduled", "complex"}:
            assert parsed["windows"], (
                f"\nNo windows produced:"
                f"\nRAW: {raw}"
                f"\nPARSED: {parsed}"
            )



# 3. ALL PARSED WINDOWS HAVE VALID HH:MM VALUES
@pytest.mark.parametrize("raw", REAL_WORLD_SCHEDULES)
def test_real_world_windows_have_valid_times(raw):
    parsed = _parse(raw)

    for window in parsed.get("windows", []):
        start = window["start"]
        end = window["end"]

        assert len(start) == 5
        assert len(end) == 5

        sh, sm = map(int, start.split(":"))
        eh, em = map(int, end.split(":"))

        assert 0 <= sh <= 23
        assert 0 <= eh <= 23
        assert 0 <= sm <= 59
        assert 0 <= em <= 59



# 4. DAY NAMES MUST BE NORMALIZED
@pytest.mark.parametrize("raw", REAL_WORLD_SCHEDULES)
def test_real_world_window_days_are_normalized(raw):
    parsed = _parse(raw)

    valid_days = {
        "MON",
        "TUE",
        "WED",
        "THU",
        "FRI",
        "SAT",
        "SUN",
    }

    for window in parsed.get("windows", []):
        assert window["days"]

        for day in window["days"]:
            assert day in valid_days, (
                f"\nInvalid day:"
                f"\nRAW: {raw}"
                f"\nWINDOW: {window}"
            )



# 5. OVERNIGHT WINDOWS MUST BE INTERNALLY CONSISTENT
@pytest.mark.parametrize("raw", REAL_WORLD_SCHEDULES)
def test_overnight_flags_are_consistent(raw):
    parsed = _parse(raw)

    for window in parsed.get("windows", []):
        start = datetime.strptime(window["start"], "%H:%M")
        end = datetime.strptime(window["end"], "%H:%M")

        expected_overnight = end <= start

        assert window["overnight"] == expected_overnight, (
            f"\nOvernight inconsistency:"
            f"\nRAW: {raw}"
            f"\nWINDOW: {window}"
        )



# 6. 24/7 SCHEDULES MUST BE ALWAYS OPEN
def test_real_world_24_7_schedule_is_always_open():
    candidates = [
        raw
        for raw in REAL_WORLD_SCHEDULES
        if "00:00-23:59" in raw
        and "Remarks:" not in raw
    ]

    for raw in candidates:
        parsed = _parse(raw)

        assert parsed["status"] == "always_open", (
            f"\nExpected always_open:"
            f"\nRAW: {raw}"
            f"\nPARSED: {parsed}"
        )



# 7. CLOSED SCHEDULES MUST BE CLOSED
def test_real_world_explicitly_closed_schedule():
    candidates = [
        raw
        for raw in REAL_WORLD_SCHEDULES
        if raw.strip() == "Mon - Sun Closed;"
    ]

    for raw in candidates:
        parsed = _parse(raw)

        assert parsed["status"] == "closed"

        dt = datetime(2026, 8, 10, 12, 0)

        assert is_open_at(parsed, dt) is False



# 8. NO REAL-WORLD SCHEDULE SHOULD CRASH THE EVALUATOR
@pytest.mark.parametrize("raw", REAL_WORLD_SCHEDULES)
def test_real_world_schedule_evaluator_never_crashes(raw):
    parsed = _parse(raw)

    # Monday through Sunday, several strategically useful times.
    probe_times = [
        (0, 0),
        (0, 30),
        (1, 0),
        (5, 0),
        (6, 0),
        (8, 0),
        (9, 0),
        (12, 0),
        (13, 0),
        (17, 0),
        (18, 0),
        (21, 0),
        (23, 0),
        (23, 59),
    ]

    for weekday_offset in range(7):
        base = datetime(2026, 8, 10) + timedelta(days=weekday_offset)

        for hour, minute in probe_times:
            dt = base.replace(hour=hour, minute=minute)

            result = is_open_at(parsed, dt)

            assert result in {True, False, None}, (
                f"\nInvalid evaluator result:"
                f"\nRAW: {raw}"
                f"\nDATETIME: {dt}"
                f"\nRESULT: {result}"
                f"\nPARSED: {parsed}"
            )