import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from backend.graph_utils import load_or_create_graph, load_aed_dataset, snap_aeds_to_graph
from backend.ranking import network_rank
from datetime import datetime

G = load_or_create_graph()
aeds = load_aed_dataset()
snapped = snap_aeds_to_graph(G, aeds)
dt = datetime(2026, 8, 9, 14, 30)

test_points = [
    (1.3343, 103.8496, "Toa Payoh Central"),
]

thresholds = [600, 800, 1000, 1200, 1500]

print("Threshold | Ranked Count | Abstained")
for t in thresholds:
    ranked, _ = network_rank(1.3343, 103.8496, G, snapped, dt, max_distance_m=t)
    print(f"{t:9}m | {len(ranked):12} | {len(ranked)==0}")