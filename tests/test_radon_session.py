"""
SPEC-020.6 — Radon session orchestrator unit and integration tests.
"""

import tempfile
import time
from pathlib import Path

import pytest

from dslv_zpdi.layer1_ingestion import radoneye_ingestor
from dslv_zpdi.orchestrator.radon_session import (
    RadonSessionOrchestrator,
    SessionConfig,
)


@pytest.fixture
def offline_radon_transports(monkeypatch):
    """SPEC-020.6 — Make RadonEye BLE and HTTP transports fail fast without I/O.

    In simulator mode the ingestor still tries BLE (bleak scan) and HTTP
    (urlopen to 192.168.4.1) before falling back to the simulator. Stub both
    so the async loop tests are hermetic and never depend on host Bluetooth
    or network reachability.
    """
    calls = {"ble": 0, "http": 0}

    async def _ble_unavailable(self):
        calls["ble"] += 1
        raise ConnectionError("BLE disabled in tests")

    def _http_unavailable(self):
        calls["http"] += 1
        raise ConnectionError("HTTP disabled in tests")

    monkeypatch.setattr(radoneye_ingestor.RadonEyeBleTransport, "read", _ble_unavailable)
    monkeypatch.setattr(radoneye_ingestor.RadonEyeHttpTransport, "read", _http_unavailable)
    return calls


class TestSessionLifecycle:
    def test_session_initialization(self):
        config = SessionConfig(session_name="test-init", operator_id="TEST-OP")
        orch = RadonSessionOrchestrator(config)
        assert orch.state.session_name == "test-init"
        assert orch.state.status == "running"
        assert orch.state.scheduled_end_utc > orch.state.started_utc

    def test_start_creates_files(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            config = SessionConfig(
                session_name="test-start",
                output_dir=tmpdir,
                simulator_mode=True,
            )
            orch = RadonSessionOrchestrator(config)
            orch.start()
            assert (Path(tmpdir) / "test-start_state.json").exists()
            assert (Path(tmpdir) / "test-start.h5").exists()
            orch._components["writer"].close()

    def test_finalize_produces_summary(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            config = SessionConfig(
                session_name="test-finalize",
                output_dir=tmpdir,
                operator_id="TEST-OP",
                simulator_mode=True,
            )
            orch = RadonSessionOrchestrator(config)
            orch.start()
            result = orch.finalize()
            assert result["session_id"] == orch.state.session_id
            assert result["state"]["status"] == "completed"
            summary_path = Path(result["summary_path"])
            assert summary_path.exists()
            text = summary_path.read_text()
            assert "Radon Session Summary" in text
            assert "TEST-OP" in text

    def test_cache_roundtrip(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            config = SessionConfig(
                session_name="test-resume",
                output_dir=tmpdir,
                simulator_mode=True,
            )
            orch = RadonSessionOrchestrator(config)
            orch.start()
            orch.state.samples_radon = 42
            orch._cache_state()

            # New orchestrator pointing at same config
            orch2 = RadonSessionOrchestrator(config)
            assert orch2.resume() is True
            assert orch2.state.samples_radon == 42
            assert orch2.state.session_id == orch.state.session_id
            orch2._components["writer"].close()

    def test_resume_returns_false_when_no_cache(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            config = SessionConfig(
                session_name="test-no-resume",
                output_dir=tmpdir,
            )
            orch = RadonSessionOrchestrator(config)
            assert orch.resume() is False

    def test_completed_session_not_resumed(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            config = SessionConfig(
                session_name="test-done",
                output_dir=tmpdir,
                simulator_mode=True,
            )
            orch = RadonSessionOrchestrator(config)
            orch.start()
            orch.finalize()

            orch2 = RadonSessionOrchestrator(config)
            assert orch2.resume() is False


@pytest.mark.usefixtures("offline_radon_transports")
class TestSessionAsyncLoop:
    @pytest.mark.asyncio
    async def test_short_run_finalizes(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            config = SessionConfig(
                session_name="test-short",
                output_dir=tmpdir,
                simulator_mode=True,
            )
            orch = RadonSessionOrchestrator(config)
            # Force a very short scheduled end so the loop exits quickly
            orch.state.scheduled_end_utc = time.time() + 2.0
            result = await orch.run()
            assert result["state"]["status"] == "completed"
            assert Path(result["hdf5_path"]).exists()

    @pytest.mark.asyncio
    async def test_stop_request_finalizes(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            config = SessionConfig(
                session_name="test-stop",
                output_dir=tmpdir,
                simulator_mode=True,
            )
            orch = RadonSessionOrchestrator(config)
            orch.start()

            async def stopper():
                await asyncio.sleep(1.5)
                orch.stop()

            import asyncio

            result = await asyncio.gather(orch.run(), stopper())
            # run() returns the finalize dict
            assert result[0]["state"]["status"] == "completed"
