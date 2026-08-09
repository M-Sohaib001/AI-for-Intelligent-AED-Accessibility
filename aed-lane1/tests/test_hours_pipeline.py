from nlp.hours_parser import parse_hours_normalized

def test_pipeline_normalizes_and_parses_12_hour_schedule():
    raw = "MON 6 PM - 9 PM"

    parsed = parse_hours_normalized(raw)

    assert parsed["status"] == "scheduled"
    assert len(parsed["windows"]) == 1

    window = parsed["windows"][0]

    assert window["days"] == ["MON"]
    assert window["start"] == "18:00"
    assert window["end"] == "21:00"


def test_pipeline_handles_compact_time():
    raw = "MON 600 PM - 300 AM"

    parsed = parse_hours_normalized(raw)

    window = parsed["windows"][0]

    assert window["start"] == "18:00"
    assert window["end"] == "03:00"
    assert window["overnight"] is True


def test_pipeline_handles_closing_override():
    raw = (
        "MON 06:00 - 23:59; "
        "Remarks: Mon: Closes at 3 AM"
    )

    parsed = parse_hours_normalized(raw)

    window = parsed["windows"][0]

    assert window["start"] == "06:00"
    assert window["end"] == "03:00"
    assert window["overnight"] is True
    assert window["closing_override"] is True


def test_pipeline_handles_closed_interval():
    raw = (
        "MON 09:00 - 17:00; "
        "Remarks: Mon: Closed from 12 PM to 1 PM"
    )

    parsed = parse_hours_normalized(raw)

    window = parsed["windows"][0]

    assert window["closed_intervals"] == [
        {
            "day": "MON",
            "start": "12:00",
            "end": "13:00",
        }
    ]


def test_pipeline_handles_conditional_access():
    raw = (
        "MON 09:00 - 17:00; "
        "Remarks: Mon: Depending on security"
    )

    parsed = parse_hours_normalized(raw)

    assert any(
        item["type"] == "CONDITIONAL_ACCESS"
        for item in parsed["access_conditions"]
    )


def test_pipeline_handles_access_instruction():
    raw = (
        "MON 09:00 - 17:00; "
        "Remarks: Mon: Please Call 600PM"
    )

    parsed = parse_hours_normalized(raw)

    assert any(
        item["type"] == "ACCESS_INSTRUCTION"
        for item in parsed["access_conditions"]
    )