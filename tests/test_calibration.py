"""Unit tests for Factory Calibration."""
import os
import json
from tools.factory_calibration import generate_calibration_artifact

def test_calibration_artifact_generation():
    node_id = "TEST-NODE"
    drift = 0.123
    generate_calibration_artifact(node_id, drift)
    
    # Check if local file was created (since /etc/ will fail)
    path = "dslv_zpdi_cal.json"
    assert os.path.exists(path)
    
    with open(path, "r") as f:
        data = json.load(f)
        assert data["node_id"] == node_id
        assert data["drift_percent"] == drift
        assert "signature_sha256" in data
        
    os.remove(path)

if __name__ == "__main__":
    test_calibration_artifact_generation()
    print("Calibration tests passed.")
