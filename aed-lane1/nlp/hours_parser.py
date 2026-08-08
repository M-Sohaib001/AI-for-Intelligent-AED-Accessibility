from datetime import datetime

def is_open_at(parsed_hours: dict, dt: datetime) -> bool | None:
    # MOCK: Treat every AED as "open" until Person B gives us the real parser.
    return True