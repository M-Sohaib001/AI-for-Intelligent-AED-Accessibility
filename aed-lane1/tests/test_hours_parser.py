from datetime import datetime

from nlp.hours_parser import parse_hours, is_open_at


def test_always_open():
    parsed = parse_hours("Mon - Sun 00:00-23:59;")

    assert parsed["status"] == "always_open"

    assert is_open_at(
        parsed,
        datetime(2026, 8, 9, 3, 15),
    ) is True


def test_weekday_schedule():
    parsed = parse_hours("Mon - Fri 08:30-18:00;")

    assert parsed["status"] == "scheduled"

    assert is_open_at(
        parsed,
        datetime(2026, 8, 10, 12, 0),
    ) is True

    assert is_open_at(
        parsed,
        datetime(2026, 8, 10, 20, 0),
    ) is False


def test_weekend_schedule():
    parsed = parse_hours("Sat - Sun 10:00-18:00;")

    assert parsed["status"] == "scheduled"


def test_closed():
    parsed = parse_hours("Mon - Sun Closed;")

    assert parsed["status"] == "closed"

    assert is_open_at(
        parsed,
        datetime(2026, 8, 10, 12, 0),
    ) is False


def test_multiple_segments():
    parsed = parse_hours(
        "Mon - Fri 08:30-18:00; "
        "Sat 08:30-13:00; "
        "Sun Closed;"
    )

    assert parsed["status"] == "scheduled"
    assert len(parsed["windows"]) == 2


def test_overnight_window_correctly_spans_midnight():
    parsed = parse_hours("Fri - Fri 22:00-02:00;")

    assert is_open_at(
        parsed,
        datetime(2026, 8, 14, 23, 59),
    ) is True

    assert is_open_at(
        parsed,
        datetime(2026, 8, 15, 1, 59),
    ) is True

    assert is_open_at(
        parsed,
        datetime(2026, 8, 15, 2, 1),
    ) is False

    assert is_open_at(
        parsed,
        datetime(2026, 8, 14, 21, 59),
    ) is False


def test_remarks_are_complex():
    parsed = parse_hours(
        "Mon - Sun 05:00-23:59; "
        "Remarks: Mon: Closes at 1:30 AM;"
    )

    assert parsed["status"] == "complex"
    assert parsed["remarks"]


def test_empty_is_unknown():
    parsed = parse_hours("")

    assert parsed["status"] == "unknown"
    assert parsed["cannot_parse"] is True


def test_none_is_unknown():
    parsed = parse_hours(None)

    assert parsed["status"] == "unknown"
    assert parsed["cannot_parse"] is True


def test_malformed_is_unknown():
    parsed = parse_hours("Monday sometime maybe")

    assert parsed["status"] == "unknown"
    assert parsed["cannot_parse"] is True


def test_mixed_parsed_and_unparsed():
    parsed = parse_hours(
        "Mon - Fri 08:30-18:00; "
        "SOMETHING_UNSUPPORTED;"
    )

    assert parsed["status"] == "complex"
    assert len(parsed["windows"]) == 1
    assert len(parsed["unparsed_segments"]) == 1