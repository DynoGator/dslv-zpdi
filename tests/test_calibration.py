"""Unit tests for Factory Calibration."""

import json
import os

from tools.factory_calibration import generate_calibration_artifact


def test_calibration_artifact_generation(tmp_path):
    node_id = "TEST-NODE"
    drift = 0.123
    # Write to a guaranteed-writable temp path so the test is hermetic regardless
    # of process privileges (root could otherwise write to /etc and bypass the
    # local fallback). The function returns the path it actually wrote.
    target = tmp_path / "dslv_zpdi_cal.json"
    written = generate_calibration_artifact(node_id, drift, path=str(target))

    assert os.path.exists(written)

    with open(written) as f:
        data = json.load(f)
        assert data["node_id"] == node_id
        assert data["drift_percent"] == drift
        assert "signature_sha256" in data


if __name__ == "__main__":
    import tempfile

    with tempfile.TemporaryDirectory() as d:
        out = generate_calibration_artifact("TEST-NODE", 0.123, path=f"{d}/cal.json")
        assert os.path.exists(out)
    print("Calibration tests passed.")
