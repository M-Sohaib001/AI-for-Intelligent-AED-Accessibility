import re


# =========================================================
# Time normalization
# =========================================================
#
# Converts recoverable 12-hour expressions into canonical
# 24-hour HH:MM format.
#
# Supported:
#
#   6 PM       -> 18:00
#   6PM        -> 18:00
#   600 PM     -> 18:00
#   600PM      -> 18:00
#   6:00 PM    -> 18:00
#   6:30PM     -> 18:30
#   12 AM      -> 00:00
#   12 PM      -> 12:00
#
# Existing 24-hour times such as:
#
#   06:00
#   18:00
#   23:59
#
# are deliberately left unchanged.
#
# This module ONLY normalizes representation.
# It does not interpret schedule semantics.
# =========================================================


_TIME_12H_RE = re.compile(
    r"""
    (?<![\d:])
    (?P<time>
        \d{1,4}
        (?:
            :
            \d{2}
        )?
    )
    \s*
    (?P<meridiem>
        [AaPp][Mm]
    )
    (?![A-Za-z])
    """,
    re.VERBOSE,
)


def _parse_12_hour_time(
    raw_time: str,
    meridiem: str,
) -> str | None:
    """
    Convert a 12-hour time expression into HH:MM.

    Supported forms:

        6       -> 06:00
        6:30    -> 06:30
        600     -> 06:00
        630     -> 06:30

    Returns None when the expression cannot be safely
    interpreted.
    """

    raw_time = raw_time.strip()

    # -----------------------------------------------------
    # Explicit HH:MM
    # -----------------------------------------------------

    if ":" in raw_time:

        hour_text, minute_text = raw_time.split(":", 1)

        if not hour_text.isdigit() or not minute_text.isdigit():
            return None

        hour = int(hour_text)
        minute = int(minute_text)

    # -----------------------------------------------------
    # Compact format
    #
    # 600 -> 6:00
    # 630 -> 6:30
    # 6   -> 6:00
    # -----------------------------------------------------

    else:

        if not raw_time.isdigit():
            return None

        if len(raw_time) <= 2:

            hour = int(raw_time)
            minute = 0

        elif len(raw_time) == 3:

            hour = int(raw_time[0])
            minute = int(raw_time[1:])

        else:

            # Four-digit compact times such as 1234 PM
            # are intentionally rejected for now.
            #
            # We should not guess unless the dataset proves
            # that this format is used consistently.

            return None

    # -----------------------------------------------------
    # Validate 12-hour clock
    # -----------------------------------------------------

    if not 1 <= hour <= 12:
        return None

    if not 0 <= minute <= 59:
        return None

    meridiem = meridiem.upper()

    # -----------------------------------------------------
    # Convert to 24-hour time
    # -----------------------------------------------------

    if hour == 12:
        hour = 0

    if meridiem == "PM":
        hour += 12

    return f"{hour:02d}:{minute:02d}"


def _normalize_time_match(match: re.Match) -> str:
    """
    Normalize one matched 12-hour time.

    Invalid expressions are returned unchanged rather
    than guessed.
    """

    raw_time = match.group("time")
    meridiem = match.group("meridiem")

    normalized = _parse_12_hour_time(
        raw_time,
        meridiem,
    )

    if normalized is None:
        return match.group(0)

    return normalized


def normalize_hours_text(raw: str) -> str:
    """
    Normalize recoverable 12-hour time expressions into
    canonical 24-hour HH:MM format.

    This function ONLY normalizes representation.

    It does NOT:

        - determine whether a schedule is overnight
        - interpret "Closed"
        - interpret "Closes at"
        - interpret "Closed from"
        - interpret conditional access
        - interpret access instructions
        - determine whether a location is open

    Examples:

        "MON 6 PM - 9 PM"
            -> "MON 18:00 - 21:00"

        "MON 600 PM - 900 PM"
            -> "MON 18:00 - 21:00"

        "MON 600PM - 300AM"
            -> "MON 18:00 - 03:00"

        "MON 06:00 - 23:59"
            -> unchanged
    """

    if not raw:
        return raw

    return _TIME_12H_RE.sub(
        _normalize_time_match,
        raw,
    )


def parse_hours_normalized(raw: str) -> dict:
    """
    Normalize recoverable time expressions first,
    then pass the normalized text to the existing parser.

    This keeps normalization and semantic parsing
    separated.
    """

    normalized = normalize_hours_text(raw)

    return parse_hours(normalized)