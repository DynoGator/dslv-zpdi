"""Unit tests for CoherenceScorer engine."""
import numpy as np
from src.layer2_core.coherence import CoherenceScorer

def test_baseline_calculation():
    scorer = CoherenceScorer()
    scorer.baseline_learning_mode = True
    
    # Simulate low coherence samples
    # np.random.uniform(0, 2*np.pi, 100) has low r
    for _ in range(10):
        phases = np.random.uniform(0, 2*np.pi, 100).tolist()
        scorer.update({"node_id": "test"}, phases)
        
    scorer.finalize_baseline()
    assert not scorer.baseline_learning_mode
    # Expected mean r is low for random phases.
    # Floor is 0.25.
    assert scorer.dynamic_threshold == 0.25

def test_outlier_detection():
    scorer = CoherenceScorer()
    # Mock a high threshold
    scorer.dynamic_threshold = 0.5
    
    # Low coherence
    phases_low = np.random.uniform(0, 2*np.pi, 100).tolist()
    pkt_low = scorer.update({"node_id": "test"}, phases_low)
    assert pkt_low.event_window_id is None
    
    # High coherence (event)
    # Perfectly coherent phases (all the same)
    phases_high = [1.0] * 100
    pkt_high = scorer.update({"node_id": "test"}, phases_high)
    assert pkt_high.r_local > 0.99
    assert pkt_high.event_window_id is not None

if __name__ == "__main__":
    test_baseline_calculation()
    test_outlier_detection()
    print("Coherence tests passed.")
