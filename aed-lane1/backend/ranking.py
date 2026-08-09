import osmnx as ox
from geopy.distance import geodesic
from backend.feasibility import evaluate_aed_feasibility, Feasibility
from backend.graph_utils import get_route_geometry

def baseline_rank(start_lat: float, start_lon: float, aeds: list[dict], k: int = 5) -> list[dict]:
    """Computes direct straight-line (Haversine/Geodesic) distance comparator."""
    scored = []
    for a in aeds:
        dist_m = geodesic((start_lat, start_lon), (a["lat"], a["lon"])).meters
        scored.append({**a, "straight_line_m": round(dist_m)})
    
    scored.sort(key=lambda x: x["straight_line_m"])
    return scored[:k]


def network_rank(start_lat: float, start_lon: float, G, aeds: list[dict], 
                 requested_datetime, k: int = 5, max_distance_m: float = 1200.0):
    """Executes $A^*$ pedestrian path finding and filters by feasibility state machine."""
    start_node = ox.distance.nearest_nodes(G, X=start_lon, Y=start_lat)
    eligible = []
    feasibility_log = []

    for a in aeds:
        eval_res = evaluate_aed_feasibility(a, start_node, G, requested_datetime, max_distance_m)
        feasibility_log.append({"aed_id": a["aed_id"], **eval_res})
        
        if eval_res["state"] == Feasibility.ELIGIBLE:
            dist_m = eval_res["distance_m"]
            route_geo = get_route_geometry(G, start_node, a["graph_info"]["graph_node"])
            
            eligible.append({
                **a,
                "distance_m": round(dist_m),
                "modeled_walk_time_min": round(dist_m / 80.0, 1), # Assumes ~4.8 km/h walking pace
                "geometry": route_geo
            })

    # prioritize acceptable snaps over warnings
    eligible.sort(key=lambda x: (x["distance_m"], 0 if x["graph_info"]["snap_quality"] == "acceptable" else 1))
    return eligible[:k], feasibility_log