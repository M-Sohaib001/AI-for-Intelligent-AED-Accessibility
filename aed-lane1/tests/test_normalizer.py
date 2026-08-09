import pytest

from nlp.normalizer import normalize_hours_text


# =========================================================
# Basic 12-hour normalization
# =========================================================


def test_normalize_hour_am():
    assert normalize_hours_text(
        "MON 6 AM - 9 AM"
    ) == "MON 06:00 - 09:00"


def test_normalize_hour_pm():
    assert normalize_hours_text(
        "MON 6 PM - 9 PM"
    ) == "MON 18:00 - 21:00"


def test_normalize_compact_am():
    assert normalize_hours_text(
        "MON 600 AM - 900 AM"
    ) == "MON 06:00 - 09:00"


def test_normalize_compact_pm():
    assert normalize_hours_text(
        "MON 600 PM - 900 PM"
    ) == "MON 18:00 - 21:00"


def test_normalize_compact_without_space():
    assert normalize_hours_text(
        "MON 600PM - 900PM"
    ) == "MON 18:00 - 21:00"


def test_normalize_colon_without_space():
    assert normalize_hours_text(
        "MON 6:30PM - 9:45PM"
    ) == "MON 18:30 - 21:45"


# =========================================================
# Noon / midnight
# =========================================================


def test_midnight():
    assert normalize_hours_text(
        "MON 12 AM - 6 AM"
    ) == "MON 00:00 - 06:00"


def test_noon():
    assert normalize_hours_text(
        "MON 12 PM - 6 PM"
    ) == "MON 12:00 - 18:00"


def test_12_30_am():
    assert normalize_hours_text(
        "MON 12:30 AM - 2 AM"
    ) == "MON 00:30 - 02:00"


def test_12_30_pm():
    assert normalize_hours_text(
        "MON 12:30 PM - 2 PM"
    ) == "MON 12:30 - 14:00"


# =========================================================
# Existing 24-hour input must remain unchanged
# =========================================================


def test_existing_24_hour_schedule_unchanged():
    raw = "MON 06:00 - 23:59"

    assert normalize_hours_text(raw) == raw


def test_existing_24_hour_overnight_unchanged():
    raw = "MON 06:00 - 03:00"

    assert normalize_hours_text(raw) == raw


def test_existing_24_hour_times_unchanged():
    raw = "MON 00:00 - 23:59"

    assert normalize_hours_text(raw) == raw


# =========================================================
# Multiple schedules
# =========================================================


def test_multiple_day_schedules():
    raw = (
        "MON 600 PM - 900 PM; "
        "TUE 700 AM - 500 PM"
    )

    expected = (
        "MON 18:00 - 21:00; "
        "TUE 07:00 - 17:00"
    )

    assert normalize_hours_text(raw) == expected


# =========================================================
# Overnight representation
#
# The normalizer does NOT decide that something is
# overnight. It simply converts the times.
# =========================================================


def test_overnight_time_representation():
    raw = "MON 600 PM - 300 AM"

    expected = "MON 18:00 - 03:00"

    assert normalize_hours_text(raw) == expected


# =========================================================
# Remarks
# =========================================================


def test_normalize_time_inside_remarks():
    raw = (
        "MON 06:00 - 23:59; "
        "Remarks: Mon: Closes at 3 AM"
    )

    expected = (
        "MON 06:00 - 23:59; "
        "Remarks: Mon: Closes at 03:00"
    )

    assert normalize_hours_text(raw) == expected


def test_normalize_compact_time_inside_remarks():
    raw = (
        "MON 06:00 - 23:59; "
        "Remarks: Mon: Closes at 300 AM"
    )

    expected = (
        "MON 06:00 - 23:59; "
        "Remarks: Mon: Closes at 03:00"
    )

    assert normalize_hours_text(raw) == expected


# =========================================================
# Access instructions
# =========================================================


def test_normalize_time_in_access_instruction():
    raw = "MON 09:00 - 17:00; Remarks: Please Call 600PM"

    expected = "MON 09:00 - 17:00; Remarks: Please Call 18:00"

    assert normalize_hours_text(raw) == expected


# =========================================================
# Closed / semantic text remains untouched
# =========================================================


def test_closed_text_unchanged():
    raw = "MON - FRI Closed"

    assert normalize_hours_text(raw) == raw


def test_closed_interval_is_only_time_normalized():
    raw = (
        "MON 09:00 - 17:00; "
        "Remarks: Mon: Closed from 12 PM to 1 PM"
    )

    expected = (
        "MON 09:00 - 17:00; "
        "Remarks: Mon: Closed from 12:00 to 13:00"
    )

    assert normalize_hours_text(raw) == expected


# =========================================================
# Invalid input
# =========================================================


def test_empty_string():
    assert normalize_hours_text("") == ""


def test_none_like_empty_input():
    assert normalize_hours_text(None) is None


def test_invalid_hour_is_not_guessed():
    raw = "MON 13 PM - 2 PM"

    expected = "MON 13 PM - 14:00"

    assert normalize_hours_text(raw) == expected


def test_invalid_minute_is_not_guessed():
    raw = "MON 6:99 PM - 9 PM"

    expected = "MON 6:99 PM - 21:00"

    assert normalize_hours_text(raw) == expected


# =========================================================
# Important malformed formats
# =========================================================


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        (
            "MON 600 PM - 900 PM",
            "MON 18:00 - 21:00",
        ),
        (
            "MON 600PM - 900PM",
            "MON 18:00 - 21:00",
        ),
        (
            "MON 6 PM - 9 PM",
            "MON 18:00 - 21:00",
        ),
        (
            "MON 6PM - 9PM",
            "MON 18:00 - 21:00",
        ),
        (
            "MON 6:00PM - 9:00PM",
            "MON 18:00 - 21:00",
        ),
        (
            "MON 6:30 PM - 9:45 PM",
            "MON 18:30 - 21:45",
        ),
        (
            "MON 600 AM - 900 AM",
            "MON 06:00 - 09:00",
        ),
    ],
)
def test_common_malformed_formats(raw, expected):
    assert normalize_hours_text(raw) == expected

# =========================================================
# Additional boundary / safety tests
# =========================================================

def test_single_digit_minutes_are_not_guessed():
    raw = "MON 6:5 PM - 9 PM"

    # The normalizer requires HH:MM when a colon is present.
    # It should leave the malformed expression unchanged.
    expected = "MON 6:5 PM - 21:00"

    assert normalize_hours_text(raw) == expected


def test_four_digit_compact_time_is_not_guessed():
    raw = "MON 1234 PM - 2 PM"

    # Deliberately unsupported for now.
    expected = "MON 1234 PM - 14:00"

    assert normalize_hours_text(raw) == expected


def test_lowercase_meridiem():
    raw = "MON 6 pm - 9 pm"

    expected = "MON 18:00 - 21:00"

    assert normalize_hours_text(raw) == expected


def test_mixed_case_meridiem():
    raw = "MON 6 Pm - 9 aM"

    expected = "MON 18:00 - 09:00"

    assert normalize_hours_text(raw) == expected


def test_time_embedded_in_word_is_not_modified():
    raw = "MON 6PMservice - 9 PM"

    expected = "MON 6PMservice - 21:00"

    assert normalize_hours_text(raw) == expected


def test_phone_number_is_not_treated_as_time():
    raw = "MON 09:00 - 17:00; Remarks: Call 123456789"

    expected = raw

    assert normalize_hours_text(raw) == expected


def test_multiple_times_inside_remark():
    raw = (
        "MON 09:00 - 17:00; "
        "Remarks: Mon: Closed from 12 PM to 1 PM "
        "and 3 PM to 4 PM"
    )

    expected = (
        "MON 09:00 - 17:00; "
        "Remarks: Mon: Closed from 12:00 to 13:00 "
        "and 15:00 to 16:00"
    )

    assert normalize_hours_text(raw) == expected


def test_multiple_day_remarks():
    raw = (
        "MON 06:00 - 23:59; "
        "Remarks: Mon: Closes at 3 AM, "
        "Tue: Closes at 2 AM"
    )

    expected = (
        "MON 06:00 - 23:59; "
        "Remarks: Mon: Closes at 03:00, "
        "Tue: Closes at 02:00"
    )

    assert normalize_hours_text(raw) == expected


def test_whitespace_between_time_and_meridiem():
    raw = "MON 6     PM - 9     PM"

    expected = "MON 18:00 - 21:00"

    assert normalize_hours_text(raw) == expected


def test_24_hour_time_with_am_text_is_not_relevant():
    raw = "MON 18:00 - 21:00"

    expected = raw

    assert normalize_hours_text(raw) == expected