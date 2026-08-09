from enum import Enum
from backend.feasibility import Feasibility

class AbstainReason(str, Enum):
    NO_OPEN_AED = "NO_OPEN_AED"
    HOURS_UNKNOWN = "HOURS_UNKNOWN"
    LOCATION_MAPPING_UNCERTAIN = "LOCATION_MAPPING_UNCERTAIN"
    NO_WALKING_PATH = "NO_WALKING_PATH"
    OUTSIDE_MAX_DISTANCE = "OUTSIDE_MAX_DISTANCE"
    NO_FEASIBLE_AED = "NO_FEASIBLE_AED"


def determine_abstention(ranked_candidates: list[dict], feasibility_log: list[dict]) -> dict:
    """Returns explicit abstention reasons when no AED can be safely recommended."""
    if ranked_candidates:
        return {"abstained": False, "reason": None}

    if not feasibility_log:
        return {"abstained": True, "reason": AbstainReason.NO_FEASIBLE_AED}

    states = [f["state"] for f in feasibility_log]
    
    if all(s == Feasibility.CLOSED for s in states):
        return {"abstained": True, "reason": AbstainReason.NO_OPEN_AED}
    if all(s == Feasibility.UNKNOWN for s in states):
        return {"abstained": True, "reason": AbstainReason.HOURS_UNKNOWN}
    if all(s == Feasibility.LOCATION_UNCERTAIN for s in states):
        return {"abstained": True, "reason": AbstainReason.LOCATION_MAPPING_UNCERTAIN}
    if all(s == Feasibility.UNREACHABLE for s in states):
        return {"abstained": True, "reason": AbstainReason.NO_WALKING_PATH}
    if all(s == Feasibility.OUTSIDE_THRESHOLD for s in states):
        return {"abstained": True, "reason": AbstainReason.OUTSIDE_MAX_DISTANCE}

    return {"abstained": True, "reason": AbstainReason.NO_FEASIBLE_AED}