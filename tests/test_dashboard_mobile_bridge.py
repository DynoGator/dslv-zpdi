"""Unit tests for tools.dashboard.mobile_bridge."""

import json
import time

from dashboard.mobile_bridge import MobileBridge


class MockPanel:
    def __init__(self):
        self.last_telem = None

    def update(self, telem: dict):
        self.last_telem = telem


def test_mobile_bridge_fetch_telemetry_offline(tmp_path):
    panel = MockPanel()
    bridge = MobileBridge(panel)
    bridge.status_url = "http://127.0.0.1:59999/invalid"
    bridge.registry_path = tmp_path / "node_registry.jsonl"
    bridge.secondary_log_path = tmp_path / "tier1_secondary.jsonl"

    telem = bridge._fetch_telemetry()
    assert telem["online"] is False
    assert "OFF GRID" in telem["trust_flags"]


def test_mobile_bridge_fetch_telemetry_local_registry(tmp_path):
    panel = MockPanel()
    bridge = MobileBridge(panel)
    bridge.status_url = "http://127.0.0.1:59999/invalid"

    reg_file = tmp_path / "node_registry.jsonl"
    now = time.time()
    reg_file.write_text(
        json.dumps({"node_id": "dslv-zpdi/mobile-tier2", "last_seen_utc": now}) + "\n"
    )
    bridge.registry_path = reg_file
    bridge.secondary_log_path = tmp_path / "tier1_secondary.jsonl"

    telem = bridge._fetch_telemetry()
    assert telem["online"] is True
    assert telem["timestamp_utc"] == now
    assert "LIVE UPLINK" in telem["trust_flags"]
