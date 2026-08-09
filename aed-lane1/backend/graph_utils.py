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

def load_aed_dataset() -> list[dict]:
    """Loads Person B's cleaned dataset from aeds_clean.json."""
    if not os.path.exists(DEFAULT_CLEAN_DATA):
        raise FileNotFoundError(
            f"Required dataset not found: {DEFAULT_CLEAN_DATA}\n"
            "Please run Person B's build_clean_dataset.py first."
        )
    
    with open(DEFAULT_CLEAN_DATA, "r", encoding="utf-8") as f:
        return json.load(f)

def validate_graph(G: nx.MultiDiGraph) -> dict:
    n_nodes, n_edges = G.number_of_nodes(), G.number_of_edges()
    is_connected = nx.is_weakly_connected(G) if G.is_directed() else nx.is_connected(G)
    stats = {"n_nodes": n_nodes, "n_edges": n_edges, "is_connected": is_connected}
    print(f"Graph Validation: {stats}")  # Log it so you can copy into data_manifest.md
    return stats

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


def node_geodesic_heuristic(u: int, v: int, G: nx.MultiDiGraph) -> float:
    """Calculates great-circle distance in meters between two graph nodes for A* heuristic search."""
    node_u = G.nodes[u]
    node_v = G.nodes[v]
    return ox.distance.great_circle(node_u["y"], node_u["x"], node_v["y"], node_v["x"])




def get_route_geometry(G: nx.MultiDiGraph, start_node: int, end_node: int) -> list[list[float]]:
    """Returns [[lon, lat], ...] coordinate path using A* search for Leaflet UI rendering."""
    try:
        # Pass a lambda wrapper so NetworkX hands node IDs (u, v) into node_euclidean_heuristic
        path = nx.astar_path(
            G, 
            start_node, 
            end_node, 
            weight="length", 
            heuristic=lambda u, v: node_geodesic_heuristic(u, v, G)
        )
        return [[G.nodes[n]["x"], G.nodes[n]["y"]] for n in path]
    except (nx.NetworkXNoPath, nx.NodeNotFound):
        return []