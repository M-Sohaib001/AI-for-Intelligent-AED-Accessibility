import os
import json
import osmnx as ox
import networkx as nx
import geopandas as gpd
from geopy.distance import geodesic

DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data")
DEFAULT_GRAPH_PATH = os.path.join(DATA_DIR, "district_walk.graphml")
DEFAULT_CLEAN_DATA = os.path.join(DATA_DIR, "aeds_clean.json")
DEFAULT_RAW_DATA = os.path.join(DATA_DIR, "raw", "scdf_aed_frozen.geojson") # FOr now raw using when filtered then will use:  os.path.join(DATA_DIR, "scdf_aed_frozen.geojson")


def load_or_create_graph(graph_path=DEFAULT_GRAPH_PATH, place_query="Toa Payoh, Singapore") -> nx.MultiDiGraph:
    """Loads frozen GraphML or pulls walking network from OpenStreetMap if not found."""
    if os.path.exists(graph_path):
        return ox.load_graphml(graph_path)
    
    print(f"Graph file not found at {graph_path}. Pulling walking network for '{place_query}'...")
    gdf = ox.geocode_to_gdf(place_query)
    polygon = gdf.geometry.iloc[0]
    G = ox.graph_from_polygon(polygon, network_type="walk")
    
    os.makedirs(os.path.dirname(graph_path), exist_ok=True)
    ox.save_graphml(G, graph_path)
    print(f"Graph saved to {graph_path}")
    return G


def validate_graph(G: nx.MultiDiGraph) -> dict:
    n_nodes, n_edges = G.number_of_nodes(), G.number_of_edges()
    is_connected = nx.is_weakly_connected(G) if G.is_directed() else nx.is_connected(G)
    stats = {"n_nodes": n_nodes, "n_edges": n_edges, "is_connected": is_connected}
    print(f"Graph Validation: {stats}")  # Log it so you can copy into data_manifest.md
    return stats

def load_aed_dataset() -> list[dict]:
    """Loads Person B's cleaned dataset if available and non-empty; falls back to raw GeoJSON otherwise."""
    if os.path.exists(DEFAULT_CLEAN_DATA) and os.path.getsize(DEFAULT_CLEAN_DATA) > 0:
        try:
            with open(DEFAULT_CLEAN_DATA, "r", encoding="utf-8") as f:
                return json.load(f)
        except json.JSONDecodeError:
            print("Warning: aeds_clean.json is invalid. Falling back to raw GeoJSON...")

    print("Warning: aeds_clean.json not found or empty. Using raw GeoJSON fallback for testing...")
    if not os.path.exists(DEFAULT_RAW_DATA):
        print(f"Error: Raw dataset not found at {DEFAULT_RAW_DATA}")
        return []

    with open(DEFAULT_RAW_DATA, "r", encoding="utf-8") as f:
        geojson = json.load(f)

    aeds = []
    for idx, feature in enumerate(geojson.get("features", [])):
        props = feature.get("properties", {})
        coords = feature.get("geometry", {}).get("coordinates", [0.0, 0.0])
        lon, lat = coords[0], coords[1]
        
        aeds.append({
            "aed_id": str(props.get("AED_ID", f"RAW-{idx}")),
            "lat": lat,
            "lon": lon,
            "raw_operating_hours": props.get("OPERATING_HOURS", "Mon - Sun 00:00-23:59;"),
            "raw_location_description": props.get("AED_LOCATION_DESCRIPTION", ""),
            "raw_floor_level": props.get("AED_LOCATION_FLOOR_LEVEL", ""),
            "parsed_hours": {
                "status": "always_open" if "00:00-23:59" in str(props.get("OPERATING_HOURS", "")) else "unknown",
                "windows": [],
                "cannot_parse": False
            },
            "location_info": {
                "floor": str(props.get("AED_LOCATION_FLOOR_LEVEL", "")),
                "flags": []
            },
            "data_quality": {
                "hours_parse_status": "parsed",
                "location_flags": [],
                "floor_present": bool(props.get("AED_LOCATION_FLOOR_LEVEL"))
            }
        })
    return aeds


def snap_aeds_to_graph(G: nx.MultiDiGraph, aeds: list[dict]) -> list[dict]:
    """Snaps lat/lon coordinates of AEDs to the nearest pedestrian graph nodes."""
    if not aeds:
        return []

    lats = [a["lat"] for a in aeds]
    lons = [a["lon"] for a in aeds]
    nearest_nodes = ox.distance.nearest_nodes(G, X=lons, Y=lats)

    snapped_aeds = []
    for aed, node in zip(aeds, nearest_nodes):
        node_data = G.nodes[node]
        snap_m = geodesic((aed["lat"], aed["lon"]), (node_data["y"], node_data["x"])).meters
        
        snap_quality = "acceptable"
        if snap_m > 150:
            snap_quality = "outlier"
        elif snap_m > 50:
            snap_quality = "warning"

        aed_copy = dict(aed)
        aed_copy["graph_info"] = {
            "graph_node": int(node),
            "snap_distance_m": round(snap_m, 1),
            "snap_quality": snap_quality
        }
        snapped_aeds.append(aed_copy)

    return snapped_aeds


def node_euclidean_heuristic(u: int, v: int, G: nx.MultiDiGraph) -> float:
    """Calculates Euclidean distance between two graph node IDs for A* heuristic search."""
    node_u = G.nodes[u]
    node_v = G.nodes[v]
    return ox.distance.euclidean(node_u["y"], node_u["x"], node_v["y"], node_v["x"])


def get_route_geometry(G: nx.MultiDiGraph, start_node: int, end_node: int) -> list[list[float]]:
    """Returns [[lon, lat], ...] coordinate path using A* search for Leaflet UI rendering."""
    try:
        # Pass a lambda wrapper so NetworkX hands node IDs (u, v) into node_euclidean_heuristic
        path = nx.astar_path(
            G, 
            start_node, 
            end_node, 
            weight="length", 
            heuristic=lambda u, v: node_euclidean_heuristic(u, v, G)
        )
        return [[G.nodes[n]["x"], G.nodes[n]["y"]] for n in path]
    except (nx.NetworkXNoPath, nx.NodeNotFound):
        return []