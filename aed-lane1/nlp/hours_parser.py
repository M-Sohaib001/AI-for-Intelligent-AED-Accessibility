import re
from datetime import datetime

from nlp.normalizer import normalize_hours_text


DAY_ORDER = ["MON", "TUE", "WED", "THU", "FRI", "SAT", "SUN"]

DAY_ALIASES = {
    "MON": "MON",
    "TUE": "TUE",
    "TUES": "TUE",
    "WED": "WED",
    "THU": "THU",
    "THUR": "THU",
    "THURS": "THU",
    "FRI": "FRI",
    "SAT": "SAT",
    "SUN": "SUN",
}


RANGE_PATTERN = re.compile(
    r"^([A-Za-z]{3,5})\s*-\s*([A-Za-z]{3,5})\s+"
    r"(\d{1,2}:\d{2})\s*-\s*(\d{1,2}:\d{2})$"
)


SINGLE_DAY_PATTERN = re.compile(
    r"^([A-Za-z]{3,5})\s+"
    r"(\d{1,2}:\d{2})\s*-\s*(\d{1,2}:\d{2})$"
)


CLOSED_PATTERN = re.compile(
    r"^([A-Za-z]{3,5})(?:\s*-\s*([A-Za-z]{3,5}))?\s+Closed$",
    re.IGNORECASE,
)


_DAY_TAG_RE = re.compile(
    r"\b(Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday|"
    r"Tues|Thurs|Mon|Tue|Wed|Thu|Fri|Sat|Sun)\s*:\s*",
    re.IGNORECASE,
)


# Supports both:
#
#   12:00 to 13:00
#   12 PM to 1 PM
#   12:30 AM to 1:30 AM
#   23:00 to 01:00
#
_TIME_TOKEN_RE = r"\d{1,2}(?::\d{2})?\s*(?:AM|PM)?"

_INTERVAL_PAIR_RE = re.compile(
    rf"({_TIME_TOKEN_RE})\s+to\s+({_TIME_TOKEN_RE})",
    re.IGNORECASE,
)


# Supports:
#
#   Closes at 1:00 AM
#   Closes at 12:30 AM
#   Closes at 13:00
#
_CLOSING_OVERRIDE_RE = re.compile(
    rf"\bcloses?\s+at\s+({_TIME_TOKEN_RE})\b",
    re.IGNORECASE,
)


_CLOSED_FROM_RE = re.compile(
    r"\bclosed\s+from\b",
    re.IGNORECASE,
)


_CONDITIONAL_KEYWORDS_RE = re.compile(
    r"\b(depend(?:ing|s)?\s+on|subject\s+to|weather\s+permitting)\b",
    re.IGNORECASE,
)


_ACCESS_KEYWORDS_RE = re.compile(
    r"\b(call|guard|security|phone|counter|reception)\b",
    re.IGNORECASE,
)


_PHONE_RE = re.compile(
    r"\b\d{7,8}\b"
)


def _parse_time_value(raw: str) -> str | None:
    """
    Convert either 24-hour or 12-hour time into canonical HH:MM.

    Examples:
        09:30      -> 09:30
        23:00      -> 23:00
        1:00 PM    -> 13:00
        12:00 PM   -> 12:00
        12:30 AM   -> 00:30
        1:30 AM    -> 01:30

    Returns None for invalid input.
    """

    if not raw:
        return None

    value = raw.strip().upper()

    match = re.fullmatch(
        r"(\d{1,2}):(\d{2})\s*(AM|PM)?",
        value,
    )

    if not match:
        return None

    hour = int(match.group(1))
    minute = int(match.group(2))
    meridiem = match.group(3)

    if not 0 <= minute <= 59:
        return None

    # 12-hour clock.
    if meridiem:

        if not 1 <= hour <= 12:
            return None

        if meridiem == "AM":
            hour = 0 if hour == 12 else hour

        else:  # PM
            hour = 12 if hour == 12 else hour + 12

        return f"{hour:02d}:{minute:02d}"

    # 24-hour clock.
    if not 0 <= hour <= 23:
        return None

    return f"{hour:02d}:{minute:02d}"


def _time_to_24h(raw: str) -> str | None:
    """
    Convert a time expression into canonical HH:MM.

    Supports:
        09:30
        9:30
        09:30 AM
        9:30 PM
        12 PM
        1 AM

    Returns:
        Canonical 24-hour HH:MM string, or None if invalid.
    """
    raw = raw.strip().upper()

    # 12-hour clock with AM/PM.
    meridiem_match = re.fullmatch(
        r"(\d{1,2})(?::(\d{2}))?\s*(AM|PM)",
        raw,
    )

    if meridiem_match:
        hour = int(meridiem_match.group(1))
        minute = int(meridiem_match.group(2) or "00")
        meridiem = meridiem_match.group(3)

        if not 1 <= hour <= 12:
            return None

        if not 0 <= minute <= 59:
            return None

        if meridiem == "AM":
            hour = 0 if hour == 12 else hour
        else:
            hour = 12 if hour == 12 else hour + 12

        return f"{hour:02d}:{minute:02d}"

    # Already canonical 24-hour time.
    match = re.fullmatch(
        r"(\d{1,2}):(\d{2})",
        raw,
    )

    if not match:
        return None

    hour = int(match.group(1))
    minute = int(match.group(2))

    if not 0 <= hour <= 23:
        return None

    if not 0 <= minute <= 59:
        return None

    return f"{hour:02d}:{minute:02d}"


def _time_in_interval(
    t: str,
    start: str,
    end: str,
) -> bool:
    """
    Return True if time t falls inside [start, end).

    Handles both normal and overnight intervals.

    Examples:
        10:00-14:00 -> 11:00 is inside
        23:00-02:00 -> 01:00 is inside

    Start is inclusive.
    End is exclusive.
    """

    if start < end:
        return start <= t < end

    if start > end:
        return t >= start or t < end

    # start == end represents an empty interval.
    return False


def _window_applies_to_day(
    window: dict,
    day_code: str,
    prev_day_code: str,
    t: str,
) -> bool:
    """
    Determine whether a window is active for the supplied datetime.

    Normal windows apply only to their calendar day.

    Overnight windows:
        opening portion belongs to current day
        continuation belongs to following day
    """

    if not window["overnight"]:
        return (
            day_code in window["days"]
            and window["start"] <= t < window["end"]
        )

    # Current-day opening portion.
    if day_code in window["days"] and t >= window["start"]:
        return True

    # Previous-day overnight continuation.
    if prev_day_code in window["days"] and t < window["end"]:
        return True

    return False


def _current_day_window_applies(
    window: dict,
    day_code: str,
    t: str,
) -> bool:
    """
    Determine whether a window is active because it STARTS
    on the current calendar day.

    Closing overrides are treated as same-day schedules.
    Therefore a closing time earlier than the opening time
    means the location remains open from its opening time
    through the end of that calendar day, rather than
    creating an overnight continuation.
    """

    if day_code not in window["days"]:
        return False

    if window.get("closing_override", False):
        start = window["start"]
        end = window["end"]

        # Normal same-day closing.
        if start < end:
            return start <= t < end

        # Closing time is earlier than opening time.
        # The override refers to the end of the same
        # calendar day, so the schedule is open from
        # opening until midnight.
        if start > end:
            return t >= start

        # start == end is treated as empty.
        return False

    if not window["overnight"]:
        return window["start"] <= t < window["end"]

    return t >= window["start"]


def _closed_interval_applies(
    closed: dict,
    t: str,
) -> bool:
    """
    Determine whether a timestamp falls inside a closure
    interval.

    Supports intervals crossing midnight.
    """

    return _time_in_interval(
        t,
        closed["start"],
        closed["end"],
    )


def split_day_clauses(
    remark_text: str,
) -> list[tuple[str, str]]:
    """
    Split remarks at the next Day: tag.

    Example:

        Mon: Closed from 12 PM to 1 PM and 2 PM to 3 PM,
        Tue: Depending on availability

    becomes:

        [
            ("MON", "Closed from 12 PM to 1 PM and 2 PM to 3 PM"),
            ("TUE", "Depending on availability"),
        ]
    """

    tags = list(
        _DAY_TAG_RE.finditer(remark_text)
    )

    clauses = []

    for i, match in enumerate(tags):

        day = normalize_day(match.group(1))

        if not day:
            continue

        start = match.end()

        end = (
            tags[i + 1].start()
            if i + 1 < len(tags)
            else len(remark_text)
        )

        clause = (
            remark_text[start:end]
            .strip()
            .rstrip(",;")
            .strip()
        )

        clauses.append(
            (day, clause)
        )

    return clauses


def normalize_day(
    token: str,
) -> str | None:

    key = token.strip().upper()

    if key in DAY_ALIASES:
        return DAY_ALIASES[key]

    full_day_aliases = {
        "MONDAY": "MON",
        "TUESDAY": "TUE",
        "WEDNESDAY": "WED",
        "THURSDAY": "THU",
        "FRIDAY": "FRI",
        "SATURDAY": "SAT",
        "SUNDAY": "SUN",
    }

    return full_day_aliases.get(key)


def expand_day_range(
    d1: str,
    d2: str,
) -> list[str]:

    i1 = DAY_ORDER.index(d1)
    i2 = DAY_ORDER.index(d2)

    if i1 <= i2:
        return DAY_ORDER[i1:i2 + 1]

    return (
        DAY_ORDER[i1:]
        + DAY_ORDER[:i2 + 1]
    )


def parse_hours(
    raw: str,
) -> dict:
    """
    Parse operating hours into structured windows.

    Returns:

        {
            "status":
                "always_open"
                | "scheduled"
                | "closed"
                | "complex"
                | "unknown",

            "windows": [...],
            "unparsed_segments": [...],
            "remarks": [...],
            "access_conditions": [...],
            "cannot_parse": bool
        }

    "complex" does NOT mean unusable.
    Structured complex schedules can still be evaluated.
    """

    if not raw or not raw.strip():
        return {
            "status": "unknown",
            "windows": [],
            "unparsed_segments": [],
            "remarks": [],
            "access_conditions": [],
            "cannot_parse": True,
        }

    text = raw.strip()

    # ---------------------------------------------------------
    # 1. Separate main schedule from Remarks
    # ---------------------------------------------------------

    remark_match = re.search(
        r"Remarks?:\s*(.*)$",
        text,
        re.IGNORECASE,
    )

    remarks = []

    if remark_match:

        remarks.append(
            remark_match.group(1).strip()
        )

        text = (
            text[:remark_match.start()]
            .strip()
        )

    # ---------------------------------------------------------
    # 2. Parse main schedule windows
    # ---------------------------------------------------------

    segments = [
        segment.strip()
        for segment in text.split(";")
        if segment.strip()
    ]

    windows = []
    unparsed = []

    any_parsed = False
    any_window = False

    for segment in segments:

        # Explicitly closed.
        if CLOSED_PATTERN.match(segment):

            any_parsed = True
            continue

        # -----------------------------------------------------
        # Day range
        # -----------------------------------------------------

        match_range = RANGE_PATTERN.match(segment)

        if match_range:

            d1_raw, d2_raw, start_raw, end_raw = (
                match_range.groups()
            )

            d1 = normalize_day(d1_raw)
            d2 = normalize_day(d2_raw)

            start = _time_to_24h(start_raw)
            end = _time_to_24h(end_raw)

            if (
                d1
                and d2
                and start
                and end
                and start != end
            ):

                windows.append({
                    "days": expand_day_range(
                        d1,
                        d2,
                    ),
                    "start": start,
                    "end": end,
                    "overnight": end < start,
                    "closing_override": False,
                    "closed_intervals": [],
                })

                any_parsed = True
                any_window = True

                continue

        # -----------------------------------------------------
        # Single day
        # -----------------------------------------------------

        match_single = SINGLE_DAY_PATTERN.match(
            segment
        )

        if match_single:

            d_raw, start_raw, end_raw = (
                match_single.groups()
            )

            d = normalize_day(d_raw)

            start = _time_to_24h(start_raw)
            end = _time_to_24h(end_raw)

            if (
                d
                and start
                and end
                and start != end
            ):

                windows.append({
                    "days": [d],
                    "start": start,
                    "end": end,
                    "overnight": end < start,
                    "closing_override": False,
                    "closed_intervals": [],
                })

                any_parsed = True
                any_window = True

                continue

        # Could not parse this segment.
        unparsed.append(segment)

    # ---------------------------------------------------------
    # 3. Parse remark clauses
    # ---------------------------------------------------------

    close_by_day: dict[str, str] = {}

    closed_intervals_by_day: dict[
        str,
        list[dict],
    ] = {}

    access_conditions: list[dict] = []

    for day, clause in split_day_clauses(
        " ".join(remarks)
    ):

        if not clause:
            continue

        recognized = False

        # -----------------------------------------------------
        # Closing-time override
        # -----------------------------------------------------

        m_close = _CLOSING_OVERRIDE_RE.search(clause)

        if m_close:
            close_time = _time_to_24h(m_close.group(1))

            if close_time is not None:
                close_by_day[day] = close_time
                recognized = True

        # -----------------------------------------------------
        # Explicit closure interval
        # -----------------------------------------------------

        if _CLOSED_FROM_RE.search(clause):

            pairs = _INTERVAL_PAIR_RE.findall(
                clause
            )

            for start_raw, end_raw in pairs:

                start = _time_to_24h(start_raw)
                end = _time_to_24h(end_raw)

                if start and end:

                    closed_intervals_by_day.setdefault(
                        day,
                        [],
                    ).append({
                        "start": start,
                        "end": end,
                    })

                    recognized = True

        # -----------------------------------------------------
        # Conditional access
        # -----------------------------------------------------

        if _CONDITIONAL_KEYWORDS_RE.search(
            clause
        ):

            access_conditions.append({
                "day": day,
                "type": "CONDITIONAL_ACCESS",
                "text": clause,
            })

            recognized = True

        # -----------------------------------------------------
        # Explicit access instruction
        # -----------------------------------------------------

        if (
            _ACCESS_KEYWORDS_RE.search(clause)
            or _PHONE_RE.search(clause)
        ):

            access_conditions.append({
                "day": day,
                "type": "ACCESS_INSTRUCTION",
                "text": clause,
            })

            recognized = True

        # -----------------------------------------------------
        # Preserve unclassified remarks
        # -----------------------------------------------------

        if not recognized:

            access_conditions.append({
                "day": day,
                "type": "OTHER_NOTE",
                "text": clause,
            })

    # ---------------------------------------------------------
    # 4. Apply closing-time overrides
    # ---------------------------------------------------------

    if close_by_day and windows:

        adjusted_windows = []

        for window in windows:

            grouped = {}

            for day in window["days"]:

                close_time = close_by_day.get(day)

                if close_time is None:
                    key = (
                        window["start"],
                        window["end"],
                        window["overnight"],
                    )
                else:
                    overnight = close_time <= window["start"]

                    key = (
                        window["start"],
                        close_time,
                        overnight,
                    )

                grouped.setdefault(
                    key,
                    [],
                ).append(day)

            for (
                start,
                end,
                overnight,
            ), days in grouped.items():

                adjusted_windows.append({
                    "days": days,
                    "start": start,
                    "end": end,
                    "overnight": overnight,
                    "closing_override": any(
                        day in close_by_day
                        for day in days
                    ),
                    "closed_intervals": [],
                })

        windows = adjusted_windows

    # ---------------------------------------------------------
    # 5. Attach closed intervals to matching windows
    # ---------------------------------------------------------

    for day, intervals in (
        closed_intervals_by_day.items()
    ):

        for window in windows:

            if day not in window["days"]:
                continue

            for interval in intervals:

                window["closed_intervals"].append({
                    "day": day,
                    "start": interval["start"],
                    "end": interval["end"],
                })

    # ---------------------------------------------------------
    # 6. Determine status
    # ---------------------------------------------------------

    if not any_parsed and not remarks:

        status = "unknown"

    elif not any_window and not unparsed:

        status = "closed"

    elif (
        any_window
        and not unparsed
        and not remarks
    ):

        is_always = (
            len(windows) == 1
            and windows[0]["start"] == "00:00"
            and windows[0]["end"] == "23:59"
            and len(windows[0]["days"]) == 7
        )

        status = (
            "always_open"
            if is_always
            else "scheduled"
        )

    elif any_window:

        status = "complex"

    else:

        status = "unknown"

    return {
        "status": status,
        "windows": windows,
        "unparsed_segments": unparsed,
        "remarks": remarks,
        "access_conditions": access_conditions,
        "cannot_parse": status == "unknown",
    }


def parse_hours_normalized(
    raw: str,
) -> dict:
    """
    Normalize recoverable 12-hour expressions and then
    parse the resulting operating-hours text.

    Pipeline:

        raw text
            ↓
        normalize_hours_text()
            ↓
        parse_hours()
            ↓
        structured result
    """

    normalized = normalize_hours_text(raw)

    return parse_hours(normalized)


def is_open_at(
    parsed_hours: dict,
    dt: datetime,
) -> bool | None:
    """
    Determine whether the location is open at a specific
    datetime.

    Returns:

        True  = confidently open
        False = confidently closed
        None  = cannot safely determine

    Important semantic rules:

    1. Normal schedules apply only to their calendar day.

    2. Overnight schedules are associated with the day
       on which they OPEN.

    3. A current-day explicit schedule takes precedence
       over an inherited overnight continuation.

    4. A current-day overnight schedule does NOT apply
       before its opening time.
    """

    status = parsed_hours.get("status")

    # ---------------------------------------------------------
    # 1. Schedule genuinely unknown
    # ---------------------------------------------------------

    if status == "unknown":
        return None

    # ---------------------------------------------------------
    # 2. Explicitly closed
    # ---------------------------------------------------------

    if status == "closed":
        return False

    # ---------------------------------------------------------
    # 3. Always open
    # ---------------------------------------------------------

    if status == "always_open":
        return True

    day_code = DAY_ORDER[
        dt.weekday()
    ]

    prev_day_code = DAY_ORDER[
        (dt.weekday() - 1) % 7
    ]

    t = dt.strftime("%H:%M")

    windows = parsed_hours.get(
        "windows",
        [],
    )

    access_conditions = parsed_hours.get(
        "access_conditions",
        [],
    )

    # ---------------------------------------------------------
    # 4. Find windows explicitly assigned to CURRENT day
    # ---------------------------------------------------------

    current_day_windows = [
        window
        for window in windows
        if day_code in window["days"]
    ]

    # ---------------------------------------------------------
    # 5. Conditional access attached to current day
    # ---------------------------------------------------------

    if any(
        condition["type"] == "CONDITIONAL_ACCESS"
        and condition["day"] == day_code
        for condition in access_conditions
    ):

        for window in current_day_windows:

            if _current_day_window_applies(
                window,
                day_code,
                t,
            ):

                return None

    # ---------------------------------------------------------
    # 6. Evaluate current day's own opening portions
    # ---------------------------------------------------------

    for window in current_day_windows:

        if not _current_day_window_applies(
            window,
            day_code,
            t,
        ):
            continue

        # -----------------------------------------------------
        # Explicit closure intervals
        # -----------------------------------------------------

        inside_closed_interval = any(
            closed.get("day") == day_code
            and _closed_interval_applies(
                closed,
                t,
            )
            for closed in window.get(
                "closed_intervals",
                [],
            )
        )

        if inside_closed_interval:
            return False

        # -----------------------------------------------------
        # Conditional access
        # -----------------------------------------------------

        if any(
            condition["type"] == "CONDITIONAL_ACCESS"
            and condition["day"] == day_code
            for condition in access_conditions
        ):

            return None

        return True

    # ---------------------------------------------------------
    # 7. Current day has an explicit schedule.
    #
    # Do not inherit yesterday's overnight window.
    # ---------------------------------------------------------

    has_explicit_current_day_schedule = bool(
        current_day_windows
    )

    if not has_explicit_current_day_schedule:

        # -----------------------------------------------------
        # 8. Consider overnight window inherited from
        #    yesterday.
        # -----------------------------------------------------

        previous_day_windows = [
            window
            for window in windows
            if (
                window["overnight"]
                and not window.get("closing_override", False)
                and prev_day_code in window["days"]
            )
        ]

        for window in previous_day_windows:

            if t >= window["end"]:
                continue

            # -------------------------------------------------
            # Closure interval.
            #
            # A closure attached to yesterday may cross
            # midnight, so _time_in_interval handles it.
            # -------------------------------------------------

            inside_closed_interval = any(
                closed.get("day") == prev_day_code
                and _closed_interval_applies(
                    closed,
                    t,
                )
                for closed in window.get(
                    "closed_intervals",
                    [],
                )
            )

            if inside_closed_interval:
                return False

            # -------------------------------------------------
            # Conditional access belongs to the day on which
            # the overnight window started.
            # -------------------------------------------------

            if any(
                condition["type"] == "CONDITIONAL_ACCESS"
                and condition["day"] == prev_day_code
                for condition in access_conditions
            ):

                return None

            return True

    # ---------------------------------------------------------
    # 9. Structured schedule exists but no open window
    #    matches.
    # ---------------------------------------------------------

    return False