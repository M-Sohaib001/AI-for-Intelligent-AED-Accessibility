from enum import Enum
from datetime import datetime
import networkx as nx
import osmnx as ox

from nlp.hours_parser import is_open_at

class Feasibility(str, Enum):
    ELIGIBLE = "ELIGIBLE"
    CLOSED = "CLOSED"
    UNKNOWN = "UNKNOWN"
    LOCATION_UNCERTAIN = "LOCATION_UNCERTAIN"
    UNREACHABLE = "UNREACHABLE"
    OUTSIDE_THRESHOLD = "OUTSIDE_THRESHOLD"


def evaluate_aed_feasibility(aed: dict, start_node: int, G: nx.MultiDiGraph, 
                             requested_datetime: datetime, max_distance_m: float) -> dict:
    """6-State Feasibility evaluation machine."""
    
    # 1. Operating Hours Check (Person B's parser as single source of truth)
    parsed_hours = aed.get("parsed_hours", {})
    open_status = is_open_at(parsed_hours, requested_datetime)

    if open_status is None:
        return {"state": Feasibility.UNKNOWN, "detail": "Operating hours status is unknown or unparseable."}
    if open_status is False:
        return {"state": Feasibility.CLOSED, "detail": "AED is closed at requested test time."}

    # 2. Coordinate Snap Quality Check
    graph_info = aed.get("graph_info", {})
    if graph_info.get("snap_quality") == "outlier":
        return {
            "state": Feasibility.LOCATION_UNCERTAIN, 
            "detail": f"Snap distance ({graph_info.get('snap_distance_m')}m) exceeds reliable threshold."
        }

    # 3. Graph Traversal Check with A* (meters)
    graph_node = graph_info.get("graph_node")
    if graph_node is None:
        return {"state": Feasibility.UNREACHABLE, "detail": "AED not mapped to graph node."}

    try:
        dist_m = nx.astar_path_length(
            G, 
            start_node, 
            graph_node, 
            weight="length",
            heuristic=lambda u, v: ox.distance.great_circle(
                G.nodes[u]["y"], G.nodes[u]["x"], 
                G.nodes[v]["y"], G.nodes[v]["x"]
            )
        )
    except (nx.NetworkXNoPath, nx.NodeNotFound):
        return {"state": Feasibility.UNREACHABLE, "detail": "No walking path exists on graph."}

    # 4. Maximum Catchment Distance Check
    if dist_m > max_distance_m:
        return {
            "state": Feasibility.OUTSIDE_THRESHOLD, 
            "detail": f"Path length {dist_m:.0f}m exceeds catchment limit of {max_distance_m}m."
        }

    return {
        "state": Feasibility.ELIGIBLE, 
        "detail": f"Path found: {dist_m:.0f}m.", 
        "distance_m": dist_m
    }