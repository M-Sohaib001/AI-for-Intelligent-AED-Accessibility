import re
from datetime import datetime

DAY_ORDER = ["MON", "TUE", "WED", "THU", "FRI", "SAT", "SUN"]
DAY_ALIASES = {"MON": "MON", "TUE": "TUE", "TUES": "TUE", "WED": "WED", "THU": "THU",
               "THUR": "THU", "THURS": "THU", "FRI": "FRI", "SAT": "SAT", "SUN": "SUN"}

RANGE_PATTERN = re.compile(r"^([A-Za-z]{3,5})\s*-\s*([A-Za-z]{3,5})\s+(\d{1,2}:\d{2})\s*-\s*(\d{1,2}:\d{2})$")
SINGLE_DAY_PATTERN = re.compile(r"^([A-Za-z]{3,5})\s+(\d{1,2}:\d{2})\s*-\s*(\d{1,2}:\d{2})$")
CLOSED_PATTERN = re.compile(r"^([A-Za-z]{3,5})(?:\s*-\s*([A-Za-z]{3,5}))?\s+Closed$", re.IGNORECASE)

def normalize_day(token: str) -> str | None:
    key = token.strip().upper()
    for alias, canon in DAY_ALIASES.items():
        if key.startswith(alias):
            return canon
    return None

def expand_day_range(d1: str, d2: str) -> list[str]:
    i1, i2 = DAY_ORDER.index(d1), DAY_ORDER.index(d2)
    if i1 <= i2:
        return DAY_ORDER[i1:i2 + 1]
    return DAY_ORDER[i1:] + DAY_ORDER[:i2 + 1]  # wraps, e.g. Sat - Mon

def parse_hours(raw: str) -> dict:
    """
    Returns: {status, windows, unparsed_segments, remarks, cannot_parse}
    status in: always_open | scheduled | closed | complex | unknown
    Never converts a parse failure into 'closed'.
    """
    if not raw or not raw.strip():
        return {"status": "unknown", "windows": [], "unparsed_segments": [], "remarks": [], "cannot_parse": True}

    text = raw.strip()
    remark_match = re.search(r"Remarks?:\s*(.*)$", text, re.IGNORECASE)
    remarks = []
    if remark_match:
        remarks.append(remark_match.group(1).strip())
        text = text[:remark_match.start()].strip()

    segments = [s.strip() for s in text.split(";") if s.strip()]
    windows = []
    unparsed = []
    any_parsed = False
    any_window = False

    for seg in segments:
        if CLOSED_PATTERN.match(seg):
            any_parsed = True
            continue

        m_range = RANGE_PATTERN.match(seg)
        if m_range:
            d1_raw, d2_raw, start, end = m_range.groups()
            d1, d2 = normalize_day(d1_raw), normalize_day(d2_raw)
            if d1 and d2:
                windows.append({"days": expand_day_range(d1, d2), "start": start, "end": end,
                                 "overnight": end < start})
                any_parsed = True
                any_window = True
                continue

        m_single = SINGLE_DAY_PATTERN.match(seg)
        if m_single:
            d_raw, start, end = m_single.groups()
            d = normalize_day(d_raw)
            if d:
                windows.append({"days": [d], "start": start, "end": end, "overnight": end < start})
                any_parsed = True
                any_window = True
                continue

        unparsed.append(seg)

    if remarks:
        status = "complex"
    elif not any_parsed:
        status = "unknown"
    elif any_window and not unparsed:
        is_always = (len(windows) == 1 and windows[0]["start"] == "00:00"
                     and windows[0]["end"] == "23:59" and len(windows[0]["days"]) == 7)
        status = "always_open" if is_always else "scheduled"
    elif not any_window and not unparsed:
        status = "closed"
    else:
        status = "complex" if any_window else "unknown"

    return {
        "status": status,
        "windows": windows,
        "unparsed_segments": unparsed,
        "remarks": remarks,
        "cannot_parse": status == "unknown",
    }


def is_open_at(parsed_hours: dict, dt: datetime) -> bool | None:
    """
    Returns True (open), False (confidently closed), or None (cannot safely determine).
    Callers (feasibility.py) MUST treat None as UNKNOWN, never as False.
    """
    status = parsed_hours["status"]
    if status in ("unknown", "complex"):
        return None
    if status == "closed":
        return False
    if status == "always_open":
        return True

    day_idx = dt.weekday()
    day_code = DAY_ORDER[day_idx]
    prev_day_code = DAY_ORDER[(day_idx - 1) % 7]
    t = dt.strftime("%H:%M")

    for w in parsed_hours["windows"]:
        if not w["overnight"]:
            if day_code in w["days"] and w["start"] <= t <= w["end"]:
                return True
        else:
            if day_code in w["days"] and t >= w["start"]:
                return True
            if prev_day_code in w["days"] and t <= w["end"]:
                return True
    return False