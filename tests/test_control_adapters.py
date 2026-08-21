"""Tests for SPEC-022 C2 control adapters."""

from __future__ import annotations

import importlib.util
import json
import os
import signal
from pathlib import Path

import pytest

from dslv_zpdi.control.adapters.hdf5_query import MAX_EXPORT_RECORDS, Hdf5Adapter
from dslv_zpdi.control.adapters.pipeline import PipelineAdapter, _read_pid
from dslv_zpdi.control.adapters.sdr import SdrAdapter

# ── PipelineAdapter ────────────────────────────────────────────────────────


class TestReadPid:
    def test_missing_file_returns_none_false(self, tmp_path):
        assert _read_pid(tmp_path / "missing.pid") == (None, False)

    def test_invalid_content_returns_none_false(self, tmp_path):
        (tmp_path / "bad.pid").write_text("notanumber")
        assert _read_pid(tmp_path / "bad.pid") == (None, False)

    def test_live_pid_returns_pid_true(self, tmp_path):
        pid = os.getpid()
        (tmp_path / "self.pid").write_text(str(pid))
        result = _read_pid(tmp_path / "self.pid")
        assert result == (pid, True)

    def test_dead_pid_returns_pid_false(self, tmp_path):
        (tmp_path / "dead.pid").write_text("999999999")
        pid, alive = _read_pid(tmp_path / "dead.pid")
        assert pid == 999999999
        assert alive is False


class TestPipelineAdapterStatus:
    def test_no_pid_files_returns_inactive(self, tmp_path, monkeypatch):
        monkeypatch.setenv("DSLV_REPO_ROOT", str(tmp_path))
        import dslv_zpdi.control.adapters.pipeline as m

        monkeypatch.setattr(m, "REPO_ROOT", tmp_path)
        monkeypatch.setattr(
            m,
            "_PID_FILES",
            {
                "mobile_node": tmp_path / ".zpdi_daemon.pid",
                "tier1_server": tmp_path / ".zpdi_tier1.pid",
                "web_dashboard": tmp_path / ".zpdi_webdash.pid",
            },
        )
        monkeypatch.setattr(m, "_SUPERVISOR_LOG", tmp_path / "supervisor.log")

        result = PipelineAdapter().status()
        assert result["active"] is False
        assert all(not v["alive"] for v in result["services"].values())

    def test_live_process_shows_active(self, tmp_path, monkeypatch):
        import dslv_zpdi.control.adapters.pipeline as m

        pid = os.getpid()
        pid_file = tmp_path / ".zpdi_daemon.pid"
        pid_file.write_text(str(pid))
        monkeypatch.setattr(
            m,
            "_PID_FILES",
            {
                "mobile_node": pid_file,
                "tier1_server": tmp_path / ".missing.pid",
                "web_dashboard": tmp_path / ".missing2.pid",
            },
        )
        monkeypatch.setattr(m, "_SUPERVISOR_LOG", tmp_path / "supervisor.log")

        result = PipelineAdapter().status()
        assert result["active"] is True
        assert result["services"]["mobile_node"]["alive"] is True


class TestPipelineAdapterStop:
    def test_stop_signals_supervisor_when_found(self, monkeypatch):
        import dslv_zpdi.control.adapters.pipeline as m

        monkeypatch.setattr(m, "_find_supervisor_pid", lambda: 12345)
        killed = {}
        monkeypatch.setattr(os, "kill", lambda pid, sig: killed.update({"pid": pid, "sig": sig}))

        result = PipelineAdapter().stop()
        assert result["acknowledged"] is True
        assert killed["pid"] == 12345
        assert killed["sig"] == signal.SIGTERM

    def test_stop_falls_back_to_pid_files_when_supervisor_not_found(self, tmp_path, monkeypatch):
        import dslv_zpdi.control.adapters.pipeline as m

        monkeypatch.setattr(m, "_find_supervisor_pid", lambda: None)

        pid = os.getpid()
        pid_file = tmp_path / ".zpdi_daemon.pid"
        pid_file.write_text(str(pid))
        monkeypatch.setattr(
            m,
            "_PID_FILES",
            {
                "mobile_node": pid_file,
                "tier1_server": tmp_path / ".missing.pid",
                "web_dashboard": tmp_path / ".missing2.pid",
            },
        )

        killed = []
        monkeypatch.setattr(
            os, "kill", lambda p, sig: killed.append((p, sig)) if sig != 0 else None
        )

        result = PipelineAdapter().stop()
        assert result["acknowledged"] is True
        assert any(p == pid for p, _ in killed if _ == signal.SIGTERM)

    def test_stop_returns_error_when_no_processes_found(self, tmp_path, monkeypatch):
        import dslv_zpdi.control.adapters.pipeline as m

        monkeypatch.setattr(m, "_find_supervisor_pid", lambda: None)
        monkeypatch.setattr(
            m,
            "_PID_FILES",
            {
                "mobile_node": tmp_path / ".missing.pid",
            },
        )

        result = PipelineAdapter().stop()
        assert result["acknowledged"] is False
        assert "error" in result


class TestPipelineAdapterStartRotate:
    def test_start_writes_marker(self, tmp_path, monkeypatch):
        import dslv_zpdi.control.adapters.pipeline as m

        marker = tmp_path / "logs" / ".start_pipeline_requested"
        monkeypatch.setattr(m, "_START_MARKER", marker)

        result = PipelineAdapter().start()
        assert result["acknowledged"] is True
        assert marker.exists()

    def test_rotate_writes_marker(self, tmp_path, monkeypatch):
        import dslv_zpdi.control.adapters.pipeline as m

        marker = tmp_path / "logs" / ".rotate_output_requested"
        monkeypatch.setattr(m, "_ROTATE_MARKER", marker)

        result = PipelineAdapter().rotate_output()
        assert result["acknowledged"] is True
        assert marker.exists()


# ── SdrAdapter ─────────────────────────────────────────────────────────────


class TestSdrAdapter:
    def test_status_returns_defaults_when_no_config(self, tmp_path, monkeypatch):
        import dslv_zpdi.control.adapters.sdr as m

        monkeypatch.setattr(m, "_RUNTIME_CONFIG", tmp_path / "sdr.json")
        monkeypatch.delenv("ZPDI_SDR_DEVICE", raising=False)

        result = SdrAdapter().status()
        assert result["device"] == "none"
        assert result["pending_restart"] is False

    def test_set_mode_persists_to_config(self, tmp_path, monkeypatch):
        import dslv_zpdi.control.adapters.sdr as m

        cfg_path = tmp_path / "sdr.json"
        monkeypatch.setattr(m, "_RUNTIME_CONFIG", cfg_path)

        result = SdrAdapter().set_mode("real")
        assert result["mode"] == "real"
        assert result["applied"] == "pending_restart"
        assert json.loads(cfg_path.read_text())["mode"] == "real"

    def test_set_center_frequency_persists(self, tmp_path, monkeypatch):
        import dslv_zpdi.control.adapters.sdr as m

        cfg_path = tmp_path / "sdr.json"
        monkeypatch.setattr(m, "_RUNTIME_CONFIG", cfg_path)

        result = SdrAdapter().set_center_frequency(144_000_000)
        assert result["center_frequency_hz"] == 144_000_000
        assert json.loads(cfg_path.read_text())["center_frequency_hz"] == 144_000_000

    def test_set_sample_rate_persists(self, tmp_path, monkeypatch):
        import dslv_zpdi.control.adapters.sdr as m

        cfg_path = tmp_path / "sdr.json"
        monkeypatch.setattr(m, "_RUNTIME_CONFIG", cfg_path)

        SdrAdapter().set_sample_rate(2_400_000)
        assert json.loads(cfg_path.read_text())["sample_rate_hz"] == 2_400_000

    def test_set_gain_persists(self, tmp_path, monkeypatch):
        import dslv_zpdi.control.adapters.sdr as m

        cfg_path = tmp_path / "sdr.json"
        monkeypatch.setattr(m, "_RUNTIME_CONFIG", cfg_path)

        SdrAdapter().set_gain(14.5)
        assert json.loads(cfg_path.read_text())["gain_db"] == 14.5

    def test_status_reads_runtime_overrides(self, tmp_path, monkeypatch):
        import dslv_zpdi.control.adapters.sdr as m

        cfg_path = tmp_path / "sdr.json"
        cfg_path.write_text(json.dumps({"mode": "simulated", "center_frequency_hz": 99_000_000}))
        monkeypatch.setattr(m, "_RUNTIME_CONFIG", cfg_path)

        result = SdrAdapter().status()
        assert result["mode"] == "simulated"
        assert result["center_frequency_hz"] == 99_000_000
        assert result["pending_restart"] is True

    def test_writes_accumulate_in_config(self, tmp_path, monkeypatch):
        import dslv_zpdi.control.adapters.sdr as m

        cfg_path = tmp_path / "sdr.json"
        monkeypatch.setattr(m, "_RUNTIME_CONFIG", cfg_path)

        SdrAdapter().set_mode("real")
        SdrAdapter().set_center_frequency(433_000_000)
        cfg = json.loads(cfg_path.read_text())
        assert cfg["mode"] == "real"
        assert cfg["center_frequency_hz"] == 433_000_000


# ── Hdf5Adapter ────────────────────────────────────────────────────────────


class TestHdf5AdapterMissingFile:
    def test_summary_missing_file(self, tmp_path, monkeypatch):
        import dslv_zpdi.control.adapters.hdf5_query as m

        monkeypatch.setattr(m, "HDF5_PATH", tmp_path / "nonexistent.h5")

        result = Hdf5Adapter().summary()
        assert "error" in result

    def test_export_missing_file(self, tmp_path, monkeypatch):
        import dslv_zpdi.control.adapters.hdf5_query as m

        monkeypatch.setattr(m, "HDF5_PATH", tmp_path / "nonexistent.h5")

        result = Hdf5Adapter().export_segment()
        assert "error" in result
        assert result["records"] == []


class TestHdf5AdapterLiveFile:
    """Tests against the live HDF5 file (skipped if file absent or h5py unavailable)."""

    @pytest.fixture(autouse=True)
    def _check(self):
        if importlib.util.find_spec("h5py") is None:
            pytest.skip("h5py not available")
        hdf5_path = Path(
            os.environ.get("ZPDI_HDF5_PATH", "/home/dynogator/dslv-zpdi/data/zpdi_stream.h5")
        )
        if not hdf5_path.exists():
            pytest.skip("live HDF5 file not present")

    def test_summary_returns_record_count(self):
        result = Hdf5Adapter().summary()
        assert "records" in result
        assert isinstance(result["records"], int)
        assert result["records"] > 0
        assert result["file_size_bytes"] > 0

    def test_summary_has_timestamp_range(self):
        result = Hdf5Adapter().summary()
        assert "first_wall_ns" in result
        assert "last_wall_ns" in result
        assert result["last_wall_ns"] >= result["first_wall_ns"]

    def test_export_returns_bounded_records(self):
        result = Hdf5Adapter().export_segment(limit=5)
        assert result["count"] <= 5
        assert len(result["records"]) == result["count"]

    def test_export_respects_hard_cap(self):
        result = Hdf5Adapter().export_segment(limit=MAX_EXPORT_RECORDS + 999)
        assert result["limit"] == MAX_EXPORT_RECORDS

    def test_export_record_structure(self):
        result = Hdf5Adapter().export_segment(limit=1)
        if result["count"] == 0:
            pytest.skip("no records in time window")
        rec = result["records"][0]
        assert "wall_ns" in rec
        assert "wall_ts" in rec
        assert "sha256" in rec
        assert "payload" in rec

    def test_export_time_window_filtering(self):
        summary = Hdf5Adapter().summary()
        if not isinstance(summary.get("records"), int) or summary["records"] < 2:
            pytest.skip("insufficient records for window test")
        mid_ts = summary["first_ts"] + (summary["last_ts"] - summary["first_ts"]) / 2
        result = Hdf5Adapter().export_segment(start_ts=mid_ts, limit=10)
        for rec in result["records"]:
            assert rec["wall_ts"] >= mid_ts
