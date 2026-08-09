from datetime import datetime

import pytest

from nlp.hours_parser import parse_hours, is_open_at

# HELPER
def assert_open(raw: str, dt: datetime, expected: bool | None):
    parsed = parse_hours(raw)
    result = is_open_at(parsed, dt)
    assert result == expected, (
        f"\nRAW: {raw}"
        f"\nDATETIME: {dt}"
        f"\nPARSED: {parsed}"
        f"\nEXPECTED: {expected}"
        f"\nRESULT: {result}"
    )

# 1. BASIC SCHEDULES
@pytest.mark.parametrize(
    "raw, dt, expected",
    [
        (
            "Mon 09:00-17:00",
            datetime(2026, 8, 10, 9, 0),
            True,
        ),
        (
            "Mon 09:00-17:00",
            datetime(2026, 8, 10, 12, 0),
            True,
        ),
        (
            "Mon 09:00-17:00",
            datetime(2026, 8, 10, 16, 59),
            True,
        ),
        (
            "Mon 09:00-17:00",
            datetime(2026, 8, 10, 17, 0),
            False,
        ),
        (
            "Mon 09:00-17:00",
            datetime(2026, 8, 10, 8, 59),
            False,
        ),
        (
            "Mon - Fri 09:00-17:00",
            datetime(2026, 8, 12, 12, 0),
            True,
        ),
        (
            "Mon - Fri 09:00-17:00",
            datetime(2026, 8, 15, 12, 0),
            False,
        ),
        (
            "Sat - Sun 10:00-18:00",
            datetime(2026, 8, 16, 12, 0),
            True,
        ),
    ],
)
def test_basic_schedules(raw, dt, expected):
    assert_open(raw, dt, expected)

# 2. OVERNIGHT WINDOWS
@pytest.mark.parametrize(
    "raw, dt, expected",
    [
        (
            "Fri 22:00-02:00",
            datetime(2026, 8, 14, 22, 0),
            True,
        ),
        (
            "Fri 22:00-02:00",
            datetime(2026, 8, 14, 23, 30),
            True,
        ),
        (
            "Fri 22:00-02:00",
            datetime(2026, 8, 15, 0, 30),
            True,
        ),
        (
            "Fri 22:00-02:00",
            datetime(2026, 8, 15, 1, 59),
            True,
        ),
        (
            "Fri 22:00-02:00",
            datetime(2026, 8, 15, 2, 0),
            False,
        ),
        (
            "Fri 22:00-02:00",
            datetime(2026, 8, 15, 2, 1),
            False,
        ),
        (
            "Fri 22:00-02:00",
            datetime(2026, 8, 15, 21, 0),
            False,
        ),
        (
            "Sat 23:00-01:00",
            datetime(2026, 8, 16, 0, 30),
            True,
        ),
        (
            "Sun 23:00-01:00",
            datetime(2026, 8, 17, 0, 30),
            True,
        ),
        (
            "Sun 23:00-01:00",
            datetime(2026, 8, 17, 1, 0),
            False,
        ),
    ],
)
def test_overnight_windows(raw, dt, expected):
    assert_open(raw, dt, expected)

# 3. CLOSING-TIME OVERRIDES
@pytest.mark.parametrize(
    "raw, dt, expected",
    [
        (
            "Mon - Fri 05:00-23:59; "
            "Remarks: Mon: Closes at 1:00 AM;",
            datetime(2026, 8, 10, 0, 30),
            False,
        ),
        (
            "Mon - Fri 05:00-23:59; "
            "Remarks: Mon: Closes at 1:00 AM;",
            datetime(2026, 8, 10, 1, 0),
            False,
        ),
        (
            "Mon - Fri 05:00-23:59; "
            "Remarks: Mon: Closes at 1:00 AM;",
            datetime(2026, 8, 10, 5, 0),
            True,
        ),
        (
            "Mon - Fri 05:00-23:59; "
            "Remarks: Mon: Closes at 1:00 AM;",
            datetime(2026, 8, 10, 23, 0),
            True,
        ),
        (
            "Mon - Fri 05:00-23:59; "
            "Remarks: Mon: Closes at 12:00 AM;",
            datetime(2026, 8, 10, 0, 0),
            False,
        ),
        (
            "Mon - Fri 05:00-23:59; "
            "Remarks: Mon: Closes at 12:00 AM;",
            datetime(2026, 8, 10, 5, 0),
            True,
        ),
        (
            "Mon - Fri 05:00-23:59; "
            "Remarks: Mon: Closes at 12:00 PM;",
            datetime(2026, 8, 10, 11, 59),
            True,
        ),
        (
            "Mon - Fri 05:00-23:59; "
            "Remarks: Mon: Closes at 12:00 PM;",
            datetime(2026, 8, 10, 12, 0),
            False,
        ),
        (
            "Mon - Fri 05:00-23:59; "
            "Remarks: Mon: Closes at 12:00 PM;",
            datetime(2026, 8, 10, 13, 0),
            False,
        ),
        (
            "Mon - Fri 05:00-23:59; "
            "Remarks: Tue: Closes at 1:00 AM;",
            datetime(2026, 8, 11, 0, 30),
            False,
        ),
    ],
)
def test_closing_time_overrides(raw, dt, expected):
    assert_open(raw, dt, expected)

# 4. MULTI-DAY CLOSING OVERRIDES
@pytest.mark.parametrize(
    "raw, dt, expected",
    [
        (
            "Mon - Fri 05:00-23:59; "
            "Remarks: Mon: Closes at 1:00 AM, "
            "Tue: Closes at 1:00 AM, "
            "Wed: Closes at 1:00 AM, "
            "Thu: Closes at 1:00 AM, "
            "Fri: Closes at 1:00 AM;",
            datetime(2026, 8, 10, 0, 30),
            False,
        ),
        (
            "Mon - Fri 05:00-23:59; "
            "Remarks: Mon: Closes at 1:00 AM, "
            "Tue: Closes at 1:00 AM, "
            "Wed: Closes at 1:00 AM, "
            "Thu: Closes at 1:00 AM, "
            "Fri: Closes at 1:00 AM;",
            datetime(2026, 8, 11, 0, 30),
            False,
        ),
        (
            "Mon - Fri 05:00-23:59; "
            "Remarks: Mon: Closes at 1:00 AM, "
            "Tue: Closes at 1:00 AM, "
            "Wed: Closes at 1:00 AM, "
            "Thu: Closes at 1:00 AM, "
            "Fri: Closes at 1:00 AM;",
            datetime(2026, 8, 12, 0, 30),
            False,
        ),
        (
            "Mon - Fri 05:00-23:59; "
            "Remarks: Mon: Closes at 1:00 AM, "
            "Tue: Closes at 1:00 AM, "
            "Wed: Closes at 1:00 AM, "
            "Thu: Closes at 1:00 AM, "
            "Fri: Closes at 1:00 AM;",
            datetime(2026, 8, 15, 0, 30),
            False,
        ),
        (
            "Mon - Fri 05:00-23:59; "
            "Remarks: Mon: Closes at 1:00 AM, "
            "Tue: Closes at 1:00 AM, "
            "Wed: Closes at 1:00 AM, "
            "Thu: Closes at 1:00 AM, "
            "Fri: Closes at 1:00 AM;",
            datetime(2026, 8, 11, 5, 0),
            True,
        ),
    ],
)
def test_multi_day_closing_overrides(raw, dt, expected):
    assert_open(raw, dt, expected)

# 5. WEEKEND CLOSING OVERRIDES
@pytest.mark.parametrize(
    "raw, dt, expected",
    [
        (
            "Sat - Sun 00:00-23:59; "
            "Remarks: Sat: Closes at 12:30 AM, "
            "Sun: Closes at 12:30 AM;",
            datetime(2026, 8, 15, 0, 15),
            True,
        ),
        (
            "Sat - Sun 00:00-23:59; "
            "Remarks: Sat: Closes at 12:30 AM, "
            "Sun: Closes at 12:30 AM;",
            datetime(2026, 8, 15, 0, 30),
            False,
        ),
        (
            "Sat - Sun 00:00-23:59; "
            "Remarks: Sat: Closes at 12:30 AM, "
            "Sun: Closes at 12:30 AM;",
            datetime(2026, 8, 16, 0, 15),
            True,
        ),
        (
            "Sat - Sun 00:00-23:59; "
            "Remarks: Sat: Closes at 12:30 AM, "
            "Sun: Closes at 12:30 AM;",
            datetime(2026, 8, 16, 0, 30),
            False,
        ),
    ],
)
def test_weekend_closing_overrides(raw, dt, expected):
    assert_open(raw, dt, expected)

# 6. EXPLICITLY CLOSED DAYS
@pytest.mark.parametrize(
    "raw, dt, expected",
    [
        (
            "Mon 09:00-17:00; Tue Closed",
            datetime(2026, 8, 11, 12, 0),
            False,
        ),
        (
            "Mon - Fri 09:00-17:00; Sat Closed; Sun Closed",
            datetime(2026, 8, 15, 12, 0),
            False,
        ),
        (
            "Mon - Fri 09:00-17:00; Sat Closed; Sun Closed",
            datetime(2026, 8, 16, 12, 0),
            False,
        ),
    ],
)
def test_explicitly_closed_days(raw, dt, expected):
    assert_open(raw, dt, expected)

# 7. EMPTY / UNKNOWN / UNPARSEABLE INPUT
@pytest.mark.parametrize(
    "raw",
    [
        "",
        " ",
        None,
        "Not available",
        "Hours unavailable",
        "Unknown schedule",
    ],
)
def test_unknown_input(raw):
    parsed = parse_hours(raw)
    assert parsed["status"] == "unknown"
    assert parsed["cannot_parse"] is True

# 8. ALWAYS OPEN
@pytest.mark.parametrize(
    "raw, dt",
    [
        (
            "Mon - Sun 00:00-23:59",
            datetime(2026, 8, 10, 0, 0),
        ),
        (
            "Mon - Sun 00:00-23:59",
            datetime(2026, 8, 12, 13, 30),
        ),
        (
            "Mon - Sun 00:00-23:59",
            datetime(2026, 8, 16, 23, 58),
        ),
    ],
)
def test_always_open(raw, dt):
    parsed = parse_hours(raw)

    assert parsed["status"] == "always_open"
    assert is_open_at(parsed, dt) is True

# 9. DAY ALIASES
@pytest.mark.parametrize(
    "raw, dt",
    [
        (
            "Tues 09:00-17:00",
            datetime(2026, 8, 11, 12, 0),
        ),
        (
            "Thurs 09:00-17:00",
            datetime(2026, 8, 13, 12, 0),
        ),
        (
            "Thur 09:00-17:00",
            datetime(2026, 8, 13, 12, 0),
        ),
        (
            "Thurs 09:00-17:00",
            datetime(2026, 8, 13, 16, 59),
        ),
    ],
)
def test_day_aliases(raw, dt):
    assert_open(raw, dt, True)

# 10. WRAPPING DAY RANGES
@pytest.mark.parametrize(
    "raw, dt, expected",
    [
        (
            "Sat - Mon 09:00-17:00",
            datetime(2026, 8, 15, 12, 0),
            True,
        ),
        (
            "Sat - Mon 09:00-17:00",
            datetime(2026, 8, 16, 12, 0),
            True,
        ),
        (
            "Sat - Mon 09:00-17:00",
            datetime(2026, 8, 17, 12, 0),
            True,
        ),
        (
            "Sat - Mon 09:00-17:00",
            datetime(2026, 8, 18, 12, 0),
            False,
        ),
    ],
)
def test_wrapping_day_ranges(raw, dt, expected):
    assert_open(raw, dt, expected)

# 11. MULTIPLE DAILY WINDOWS
@pytest.mark.parametrize(
    "raw, dt, expected",
    [
        (
            "Mon 09:00-12:00; Mon 13:00-17:00",
            datetime(2026, 8, 10, 10, 0),
            True,
        ),
        (
            "Mon 09:00-12:00; Mon 13:00-17:00",
            datetime(2026, 8, 10, 12, 30),
            False,
        ),
        (
            "Mon 09:00-12:00; Mon 13:00-17:00",
            datetime(2026, 8, 10, 14, 0),
            True,
        ),
        (
            "Mon 09:00-12:00; Mon 13:00-17:00",
            datetime(2026, 8, 10, 17, 0),
            False,
        ),
    ],
)
def test_multiple_daily_windows(raw, dt, expected):
    assert_open(raw, dt, expected)

# 12. CONDITIONAL ACCESS
@pytest.mark.parametrize(
    "raw, dt",
    [
        (
            "Mon 09:00-17:00; "
            "Remarks: Mon: Depending on availability;",
            datetime(2026, 8, 10, 12, 0),
        ),
        (
            "Mon 09:00-17:00; "
            "Remarks: Mon: Subject to weather;",
            datetime(2026, 8, 10, 12, 0),
        ),
        (
            "Mon 09:00-17:00; "
            "Remarks: Mon: Weather permitting;",
            datetime(2026, 8, 10, 12, 0),
        ),
    ],
)
def test_conditional_access_returns_unknown(raw, dt):
    assert_open(raw, dt, None)

# 13. ACCESS INSTRUCTIONS
def test_access_instruction_is_preserved():
    raw = (
        "Mon 09:00-17:00; "
        "Remarks: Mon: Call security for access;"
    )

    parsed = parse_hours(raw)

    assert parsed["access_conditions"]

    matching = [
        c
        for c in parsed["access_conditions"]
        if c["day"] == "MON"
    ]

    assert matching
    assert any(
        c["type"] == "ACCESS_INSTRUCTION"
        for c in matching
    )


def test_phone_instruction_is_preserved():
    raw = (
        "Mon 09:00-17:00; "
        "Remarks: Mon: Call 12345678 for access;"
    )

    parsed = parse_hours(raw)

    assert parsed["access_conditions"]

    matching = [
        c
        for c in parsed["access_conditions"]
        if c["day"] == "MON"
    ]

    assert any(
        c["type"] == "ACCESS_INSTRUCTION"
        for c in matching
    )

# 14. EXPLICIT CLOSED INTERVALS
@pytest.mark.parametrize(
    "raw, dt, expected",
    [
        (
            "Mon 09:00-17:00; "
            "Remarks: Mon: Closed from 12 PM to 1 PM;",
            datetime(2026, 8, 10, 11, 59),
            True,
        ),
        (
            "Mon 09:00-17:00; "
            "Remarks: Mon: Closed from 12 PM to 1 PM;",
            datetime(2026, 8, 10, 12, 0),
            False,
        ),
        (
            "Mon 09:00-17:00; "
            "Remarks: Mon: Closed from 12 PM to 1 PM;",
            datetime(2026, 8, 10, 12, 30),
            False,
        ),
        (
            "Mon 09:00-17:00; "
            "Remarks: Mon: Closed from 12 PM to 1 PM;",
            datetime(2026, 8, 10, 13, 0),
            True,
        ),
    ],
)
def test_closed_intervals(raw, dt, expected):
    assert_open(raw, dt, expected)

# 15. MULTIPLE CLOSED INTERVALS
@pytest.mark.parametrize(
    "raw, dt, expected",
    [
        (
            "Mon 09:00-18:00; "
            "Remarks: Mon: Closed from 12 PM to 1 PM and "
            "2 PM to 3 PM;",
            datetime(2026, 8, 10, 11, 30),
            True,
        ),
        (
            "Mon 09:00-18:00; "
            "Remarks: Mon: Closed from 12 PM to 1 PM and "
            "2 PM to 3 PM;",
            datetime(2026, 8, 10, 12, 30),
            False,
        ),
        (
            "Mon 09:00-18:00; "
            "Remarks: Mon: Closed from 12 PM to 1 PM and "
            "2 PM to 3 PM;",
            datetime(2026, 8, 10, 13, 30),
            True,
        ),
        (
            "Mon 09:00-18:00; "
            "Remarks: Mon: Closed from 12 PM to 1 PM and "
            "2 PM to 3 PM;",
            datetime(2026, 8, 10, 14, 30),
            False,
        ),
        (
            "Mon 09:00-18:00; "
            "Remarks: Mon: Closed from 12 PM to 1 PM and "
            "2 PM to 3 PM;",
            datetime(2026, 8, 10, 15, 30),
            True,
        ),
    ],
)
def test_multiple_closed_intervals(raw, dt, expected):
    assert_open(raw, dt, expected)

# 16. OVERNIGHT + EXPLICIT CURRENT-DAY SCHEDULE
@pytest.mark.parametrize(
    "raw, dt, expected",
    [
        (
            "Fri 05:00-01:00; Sat 00:00-00:30",
            datetime(2026, 8, 15, 0, 15),
            True,
        ),
        (
            "Fri 05:00-01:00; Sat 00:00-00:30",
            datetime(2026, 8, 15, 0, 30),
            False,
        ),
        (
            "Fri 05:00-01:00; Sat 00:00-00:30",
            datetime(2026, 8, 15, 0, 45),
            False,
        ),
    ],
)
def test_current_day_schedule_overrides_previous_overnight(
    raw,
    dt,
    expected,
):
    assert_open(raw, dt, expected)

# 17. OVERNIGHT CLOSURE INTERVALS
@pytest.mark.parametrize(
    "raw, dt, expected",
    [
        (
            "Fri 20:00-02:00; "
            "Remarks: Fri: Closed from 11 PM to 12 AM;",
            datetime(2026, 8, 14, 22, 30),
            True,
        ),
        (
            "Fri 20:00-02:00; "
            "Remarks: Fri: Closed from 11 PM to 12 AM;",
            datetime(2026, 8, 14, 23, 30),
            False,
        ),
        (
            "Fri 20:00-02:00; "
            "Remarks: Fri: Closed from 11 PM to 12 AM;",
            datetime(2026, 8, 15, 0, 30),
            True,
        ),
    ],
)
def test_overnight_closure_intervals(raw, dt, expected):
    assert_open(raw, dt, expected)

# 18. COMPLEX SCHEDULES REMAIN EVALUABLE
def test_complex_schedule_is_not_automatically_unknown():
    raw = (
        "Mon - Fri 05:00-23:59; "
        "Remarks: Mon: Closes at 1:00 AM;"
    )

    parsed = parse_hours(raw)

    assert parsed["status"] == "complex"
    assert parsed["cannot_parse"] is False

    assert (
        is_open_at(
            parsed,
            datetime(2026, 8, 10, 5, 0),
        )
        is True
    )

# 19. REMARKS WITH MULTIPLE DAY CLAUSES
def test_multiple_day_remarks_are_split_correctly():
    raw = (
        "Mon - Fri 05:00-23:59; "
        "Remarks: Mon: Closes at 1:00 AM, "
        "Tue: Closes at 2:00 AM, "
        "Wed: Closes at 3:00 AM;"
    )

    parsed = parse_hours(raw)

    windows = parsed["windows"]

    assert any(
        "MON" in w["days"]
        and w["end"] == "01:00"
        for w in windows
    )

    assert any(
        "TUE" in w["days"]
        and w["end"] == "02:00"
        for w in windows
    )

    assert any(
        "WED" in w["days"]
        and w["end"] == "03:00"
        for w in windows
    )

# 20. BOUNDARY SEMANTICS
@pytest.mark.parametrize(
    "raw, dt, expected",
    [
        (
            "Mon 09:00-17:00",
            datetime(2026, 8, 10, 9, 0),
            True,
        ),
        (
            "Mon 09:00-17:00",
            datetime(2026, 8, 10, 17, 0),
            False,
        ),
        (
            "Fri 22:00-02:00",
            datetime(2026, 8, 14, 22, 0),
            True,
        ),
        (
            "Fri 22:00-02:00",
            datetime(2026, 8, 15, 2, 0),
            False,
        ),
    ],
)
def test_interval_boundaries(raw, dt, expected):
    assert_open(raw, dt, expected)

# 21. FULL REAL-WORLD REGRESSION CASE
@pytest.mark.parametrize(
    "dt, expected",
    [
        (datetime(2026, 8, 10, 0, 30), False),
        (datetime(2026, 8, 10, 1, 0), False),
        (datetime(2026, 8, 10, 2, 0), False),
        (datetime(2026, 8, 10, 4, 59), False),
        (datetime(2026, 8, 10, 5, 0), True),
        (datetime(2026, 8, 11, 0, 30), False),
        (datetime(2026, 8, 11, 1, 0), False),
        (datetime(2026, 8, 11, 5, 0), True),
        (datetime(2026, 8, 15, 0, 15), True),
        (datetime(2026, 8, 15, 0, 30), False),
    ],
)
def test_full_regression_schedule(dt, expected):
    raw = (
        "Mon - Fri 05:00-23:59; "
        "Sat - Sun 00:00-23:59; "
        "Remarks: "
        "Mon: Closes at 1:00 AM, "
        "Tue: Closes at 1:00 AM, "
        "Wed: Closes at 1:00 AM, "
        "Thu: Closes at 1:00 AM, "
        "Fri: Closes at 1:00 AM, "
        "Sat: Closes at 12:30 AM, "
        "Sun: Closes at 12:30 AM;"
    )

    assert_open(raw, dt, expected)

def test_closing_override_does_not_inherit_into_next_day():
    raw = (
        "Mon - Fri 05:00-23:59; "
        "Remarks: Mon: Closes at 1:00 AM, "
        "Tue: Closes at 1:00 AM, "
        "Wed: Closes at 1:00 AM, "
        "Thu: Closes at 1:00 AM, "
        "Fri: Closes at 1:00 AM;"
    )

    assert_open(
        raw,
        datetime(2026, 8, 15, 0, 30),
        False,
    )

def test_overnight_window_correctly_spans_midnight():
    parsed = parse_hours("Fri - Fri 22:00-02:00;")

    assert is_open_at(parsed, datetime(2026, 8, 14, 23, 59)) is True
    assert is_open_at(parsed, datetime(2026, 8, 15, 1, 59)) is True
    assert is_open_at(parsed, datetime(2026, 8, 15, 2, 1)) is False
    assert is_open_at(parsed, datetime(2026, 8, 14, 21, 59)) is False