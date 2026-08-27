"""Contract tests for the Flask operations dashboard (web_server)."""

import json
import os
import time
from pathlib import Path

import pytest

from dashboard.web_server import create_app


@pytest.fixture
def dash_client(tmp_path, monkeypatch):
    monkeypatch.setenv("DSLV_SECONDARY_OUTPUT_DIR", str(tmp_path / "secondary"))
    monkeypatch.setenv("ZPDI_SECONDARY_LOG", str(tmp_path / "tier1_secondary.jsonl"))
    monkeypatch.setenv("DSLV_HEALTH_JSON", str(tmp_path / "missing-health.json"))
    monkeypatch.delenv("DSLV_WEBDASH_ALLOW_SHUTDOWN", raising=False)
    app = create_app()
    with app.test_client() as client:
        yield client, tmp_path


def test_shutdown_disabled_by_default(dash_client):
    client, _ = dash_client
    resp = client.post("/api/system/shutdown")
    assert resp.status_code == 403
    data = resp.get_json()
    assert "disabled" in data.get("error", "").lower()


def test_status_includes_mobile_and_does_not_lie_about_timing(dash_client):
    client, _ = dash_client
    resp = client.get("/api/status")
    assert resp.status_code == 200
    data = resp.get_json()
    assert "mobile" in data
    assert data["mobile"]["online"] is False
    assert data["pipeline"]["timing_healthy"] is False
    assert data["sdr"]["reachable"] is False
    assert data["ups"]["health"] == "absent"
    assert "telemetry_nodes" in data["nodes"]
    assert "registered_nodes" in data["nodes"]


def test_status_marks_mobile_online_from_registry(dash_client):
    client, tmp_path = dash_client
    secondary = Path(os.environ["DSLV_SECONDARY_OUTPUT_DIR"])
    secondary.mkdir(parents=True, exist_ok=True)
    now = time.time()
    (secondary / "node_registry.jsonl").write_text(
        json.dumps({"node_id": "dslv-zpdi/mobile-tier2", "last_seen_utc": now}) + "\n",
        encoding="utf-8",
    )
    resp = client.get("/api/status")
    data = resp.get_json()
    assert data["mobile"]["online"] is True
    assert "LIVE UPLINK" in data["mobile"]["trust_flags"]
