import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from backend.graph_utils import load_or_create_graph, load_aed_dataset, snap_aeds_to_graph
from backend.ranking import baseline_rank, network_rank
from datetime import datetime

def test_baseline_rank():
    G = load_or_create_graph()
    aeds = load_aed_dataset()
    snapped = snap_aeds_to_graph(G, aeds)
    result = baseline_rank(1.3343, 103.8496, snapped)
    assert len(result) == 5
    assert "straight_line_m" in result[0]
    print("✅ Baseline test passed!")

def test_network_rank():
    G = load_or_create_graph()
    aeds = load_aed_dataset()
    snapped = snap_aeds_to_graph(G, aeds)
    ranked, log = network_rank(1.3343, 103.8496, G, snapped, datetime(2026, 8, 9, 14, 30))
    assert len(log) == len(snapped)
    print(f"✅ Network rank test passed! Found {len(ranked)} eligible AEDs.")

if __name__ == "__main__":
    test_baseline_rank()
    test_network_rank()
    print("All tests passed!")