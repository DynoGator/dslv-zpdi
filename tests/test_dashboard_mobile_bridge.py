"""Unit tests for tools.dashboard.mobile_bridge and 10-inch layout."""

import json
import time
from unittest.mock import patch

from dashboard.app import _is_ten_inch, build_layout
from dashboard.config import PanelsCfg
from dashboard.mobile_bridge import (
    MobileBridge,
    coerce_gps,
    coerce_magnetometer,
    collect_mobile_telemetry,
)


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
    reg_file.write_text(json.dumps({"node_id": "dslv-zpdi/mobile-tier2", "last_seen_utc": now}) + "\n")
    bridge.registry_path = reg_file
    bridge.secondary_log_path = tmp_path / "tier1_secondary.jsonl"

    telem = bridge._fetch_telemetry()
    assert telem["online"] is True
    assert telem["timestamp_utc"] == now
    assert "LIVE UPLINK" in telem["trust_flags"]


def test_http_200_without_mobile_sample_is_not_online(tmp_path):
    """A reachable but empty dashboard must not spoof PHONE ALIVE / LIVE."""
    dummy = json.dumps({"nodes": {"registered_nodes": [{"node_id": "unrelated", "online": True}]}})

    class _Resp:
        status = 200

        def read(self):
            return dummy.encode()

        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

    with patch("urllib.request.urlopen", return_value=_Resp()):
        telem = collect_mobile_telemetry(
            "http://127.0.0.1:8080/api/status",
            tmp_path / "missing_registry.jsonl",
            tmp_path / "missing_secondary.jsonl",
        )
    assert telem["online"] is False
    assert "OFF GRID" in telem["trust_flags"]
    assert telem["phone_reachable"] is True


def test_secondary_log_gps_fix_and_dict_mag(tmp_path):
    now = time.time()
    pkt = {
        "timestamp_utc": now,
        "gps_fix": {"latitude": 38.4, "longitude": -105.0, "accuracy": 8.0},
        "magnetometer_ut": {"x": 30.0, "y": 10.0, "z": 40.0},
        "r_smooth": 0.42,
        "camera_frame_hash": "abcdef123456",
    }
    log_path = tmp_path / "tier1_secondary.jsonl"
    log_path.write_text("not json\n" + json.dumps(pkt) + "\n")
    telem = collect_mobile_telemetry(None, tmp_path / "none.jsonl", log_path)
    assert telem["online"] is True
    assert telem["gps"]["lat"] == 38.4
    assert telem["gps"]["accuracy"] == 8.0
    assert telem["magnetometer_ut"] == [30.0, 10.0, 40.0]
    assert telem["trust_score"] == 0.42
    assert telem["camera_frame_hash"] == "abcdef123456"


def test_coerce_magnetometer_and_gps():
    assert coerce_magnetometer({"values": [1, 2, 3]}) == [1.0, 2.0, 3.0]
    assert coerce_magnetometer("nope") is None
    gps = coerce_gps({"latitude": "1.5", "longitude": "-2", "accuracy": "9"})
    assert gps["lat"] == 1.5
    assert gps["lon"] == -2.0
    assert gps["accuracy"] == 9.0


def test_is_ten_inch_honors_env(monkeypatch):
    monkeypatch.setenv("DSLV_DASHBOARD_10IN", "0")
    assert _is_ten_inch() is False
    monkeypatch.setenv("DSLV_DASHBOARD_10IN", "1")
    assert _is_ten_inch() is True
    monkeypatch.setenv("DSLV_DASHBOARD_10IN", "false")
    assert _is_ten_inch() is False


def test_ten_inch_layout_includes_mobile_panel():
    layout = build_layout(False, False, False, True, PanelsCfg())
    assert layout["mobile"] is not None
    assert layout["waterfall"] is not None
    assert layout["settings"] is not None
    assert layout["system"] is not None


def test_default_status_url_is_not_hardcoded_lan_ip(monkeypatch):
    monkeypatch.delenv("DSLV_PIXEL_STATUS_URL", raising=False)
    with patch("dashboard.mobile_bridge.load_registered_nodes", return_value=[]):
        panel = MockPanel()
        bridge = MobileBridge(panel)
    assert bridge.status_url is None or "10.29.134.63" not in str(bridge.status_url)
