import re


FLOOR_REF_PATTERN = re.compile(
    r"\blevel\s*\w*\b|\bb\d\w*\b|\bl\d\b",
    re.IGNORECASE,
)

RELATIONAL_TERMS = [
    "near",
    "beside",
    "opposite",
    "behind",
    "next to",
    "across from",
]

INDOOR_TERMS = [
    "lobby",
    "counter",
    "reception",
    "office",
    "corridor",
    "hallway",
]

BUILDING_INTERNAL_TERMS = [
    "car park",
    "carpark",
    "stairwell",
    "staircase",
    "lift lobby",
    "escalator",
]


def flag_location(description: str, floor: str) -> dict:
    """
    Semantic location flags rather than a single ambiguity flag.

    Floor/level mentions are treated as informative rather than
    inherently ambiguous.
    """

    desc = (description or "").lower()

    flags = []

    if not desc.strip():
        flags.append("missing_description")

    if not (floor or "").strip():
        flags.append("missing_floor_info")

    if FLOOR_REF_PATTERN.search(desc):
        flags.append("floor_reference")

    if any(term in desc for term in RELATIONAL_TERMS):
        flags.append("relational_location")

    if any(term in desc for term in INDOOR_TERMS):
        flags.append("possible_indoor_access")

    if any(term in desc for term in BUILDING_INTERNAL_TERMS):
        flags.append("possible_building_internal_location")

    return {
        "floor": floor,
        "flags": flags,
    }