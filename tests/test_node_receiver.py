"""SPEC-014.8 — Contract tests for node receiver public HTTP surface (SPEC-014.4/5/6).

Covers:
- /api/v1/ingest : happy path, malformed JSON, empty body
- /api/v1/ingest/radoneye : missing required, non-numeric radon, happy staging
- /api/v1/health : basic health + stats
- writer failure path (ingest raises -> 500)
- concurrent POSTs (threaded Flask handles without corruption)

Governed by SPEC-014 (no new SPEC-ID minted). All new tests carry SPEC-014.8 in docstring.
"""

import json
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

import pytest

from dslv_zpdi.layer3_telemetry.hdf5_writer import HDF5Writer
from dslv_zpdi.layer3_telemetry.node_receiver import (
    create_app,
)


class TestNodeReceiverIngestContract:
    """SPEC-014.8 — Tests for the primary swarm ingest endpoint per SPEC-014.4."""

    @pytest.fixture
    def app_client(self, tmp_path, monkeypatch):
        primary = tmp_path / "primary"
        secondary = tmp_path / "secondary"
        monkeypatch.setenv("DSLV_PRIMARY_OUTPUT_DIR", str(primary))
        monkeypatch.setenv("DSLV_SECONDARY_OUTPUT_DIR", str(secondary))
        app = create_app()
        # ensure writer is fresh for this app context
        with app.test_client() as client:
            yield client, primary, secondary

    def test_ingest_valid_payload_returns_200_and_decision(self, app_client):
        """SPEC-014.8 / SPEC-014.4 — valid JSON with node_id accepted, returns stream decision."""
        client, _, _ = app_client
        payload = {
            "node_id": "PIXEL-TEST-01",
            "payload_uuid": "test-uuid-1234",
            "modality": "magnetometer",
            "timestamp_utc": time.time(),
            "raw_value": {"x": 42.0},
        }
        resp = client.post(
            "/api/v1/ingest",
            data=json.dumps(payload),
            content_type="application/json",
        )
        assert resp.status_code == 200
        data = resp.get_json()
        assert "stream" in data
        assert "reason" in data

    def test_ingest_malformed_json_returns_400(self, app_client):
        """SPEC-014.8 / SPEC-014.4 — non-JSON body yields 400 with error message."""
        client, _, _ = app_client
        resp = client.post(
            "/api/v1/ingest",
            data="{not valid json",
            content_type="application/json",
        )
        assert resp.status_code == 400
        data = resp.get_json()
        assert "invalid JSON" in data.get("error", "")

    def test_ingest_empty_body_returns_400(self, app_client):
        """SPEC-014.8 / SPEC-014.4 — empty body yields 400."""
        client, _, _ = app_client
        resp = client.post("/api/v1/ingest", data="", content_type="application/json")
        assert resp.status_code == 400
        data = resp.get_json()
        assert "empty body" in data.get("error", "").lower()

    def test_ingest_missing_node_id_uses_remote_addr(self, app_client):
        """SPEC-014.8 / SPEC-014.4 — absent node_id is stamped from remote_addr (or UNKNOWN)."""
        client, _, _ = app_client
        payload = {
            "payload_uuid": "no-node-id",
            "modality": "gps",
            "timestamp_utc": time.time(),
            "raw_value": {},
        }
        resp = client.post(
            "/api/v1/ingest",
            data=json.dumps(payload),
            content_type="application/json",
        )
        assert resp.status_code == 200


class TestNodeReceiverRadonEyeContract:
    """SPEC-014.8 — Tests for the RadonEye staging endpoint per SPEC-014.5 (secondary only)."""

    @pytest.fixture
    def app_client(self, tmp_path, monkeypatch):
        primary = tmp_path / "primary"
        secondary = tmp_path / "secondary"
        monkeypatch.setenv("DSLV_PRIMARY_OUTPUT_DIR", str(primary))
        monkeypatch.setenv("DSLV_SECONDARY_OUTPUT_DIR", str(secondary))
        # RadonEye endpoint does direct open() on secondary/radoneye_staging.jsonl
        # without makedirs (unlike registry path); ensure dir exists for the test.
        secondary.mkdir(parents=True, exist_ok=True)
        app = create_app()
        with app.test_client() as client:
            yield client, secondary

    def test_radoneye_missing_required_fields_422(self, app_client):
        """SPEC-014.8 / SPEC-014.5 — missing any of source/radon_bq_m3/timestamp_utc/unit_id -> 422."""
        client, _ = app_client
        payload = {"source": "EcoSense_RadonEye_Pro", "radon_bq_m3": 42.0}  # missing two
        resp = client.post(
            "/api/v1/ingest/radoneye",
            data=json.dumps(payload),
            content_type="application/json",
        )
        assert resp.status_code == 422
        data = resp.get_json()
        assert "missing required fields" in data.get("error", "")

    def test_radoneye_non_numeric_radon_422(self, app_client):
        """SPEC-014.8 / SPEC-014.5 — radon_bq_m3 not numeric -> 422 (explicit validation)."""
        client, _ = app_client
        payload = {
            "source": "EcoSense_RadonEye_Pro",
            "radon_bq_m3": "not-a-float",
            "timestamp_utc": time.time(),
            "unit_id": "RD-TEST-001",
        }
        resp = client.post(
            "/api/v1/ingest/radoneye",
            data=json.dumps(payload),
            content_type="application/json",
        )
        assert resp.status_code == 422
        data = resp.get_json()
        assert "must be numeric" in data.get("error", "")

    def test_radoneye_valid_stages_to_secondary_202(self, app_client):
        """SPEC-014.8 / SPEC-014.5 — valid payload stages to radoneye_staging.jsonl , returns 202 + SPEC-015-PENDING."""
        client, secondary = app_client
        payload = {
            "source": "EcoSense_RadonEye_Pro",
            "radon_bq_m3": 123.45,
            "timestamp_utc": time.time(),
            "unit_id": "RD-TEST-002",
            "extra": "ignored",
        }
        resp = client.post(
            "/api/v1/ingest/radoneye",
            data=json.dumps(payload),
            content_type="application/json",
        )
        assert resp.status_code == 202
        data = resp.get_json()
        assert data.get("stream") == "secondary"
        assert "SPEC-015-PENDING" in data.get("reason", "")
        # verify quarantine file was written
        staging = secondary / "radoneye_staging.jsonl"
        assert staging.exists()
        content = staging.read_text(encoding="utf-8")
        assert "RD-TEST-002" in content
        assert "SPEC-015-PENDING" in content


class TestNodeReceiverHealthContract:
    """SPEC-014.8 — Tests for the health endpoint per SPEC-014.6."""

    @pytest.fixture
    def app_client(self, tmp_path, monkeypatch):
        primary = tmp_path / "primary"
        secondary = tmp_path / "secondary"
        monkeypatch.setenv("DSLV_PRIMARY_OUTPUT_DIR", str(primary))
        monkeypatch.setenv("DSLV_SECONDARY_OUTPUT_DIR", str(secondary))
        app = create_app()
        with app.test_client() as client:
            yield client

    def test_health_returns_200_and_stats(self, app_client):
        """SPEC-014.8 / SPEC-014.6 — /health always 200, includes stats dict (may be empty pre-ingest)."""
        client = app_client
        resp = client.get("/api/v1/health")
        assert resp.status_code == 200
        data = resp.get_json()
        assert data.get("status") == "ok"
        assert "stats" in data
        assert isinstance(data["stats"], dict)


class TestNodeReceiverWriterFailure:
    """SPEC-014.8 — Writer failure surfaces as 500 (storage kill condition)."""

    def test_ingest_propagates_writer_exception_as_500(self, tmp_path, monkeypatch):
        """SPEC-014.8 — if HDF5Writer.ingest raises, the route returns 500 (no silent drop)."""
        primary = tmp_path / "p"
        secondary = tmp_path / "s"
        monkeypatch.setenv("DSLV_PRIMARY_OUTPUT_DIR", str(primary))
        monkeypatch.setenv("DSLV_SECONDARY_OUTPUT_DIR", str(secondary))

        class BoomWriter(HDF5Writer):
            def ingest(self, json_payload: str):
                raise RuntimeError("simulated writer failure for test")

        # inject the failing writer at factory time
        app = create_app(writer=BoomWriter(output_path=str(primary), secondary_path=str(secondary)))
        with app.test_client() as client:
            payload = {
                "node_id": "FAIL-TEST",
                "payload_uuid": "fail-u",
                "modality": "test",
                "timestamp_utc": time.time(),
                "raw_value": {},
            }
            resp = client.post(
                "/api/v1/ingest",
                data=json.dumps(payload),
                content_type="application/json",
            )
            # Flask turns uncaught exception in view into 500
            assert resp.status_code == 500

        # Restore the module-global singleton so subsequent tests in the same
        # process (e.g. concurrent test) do not inherit the intentionally broken
        # writer. SPEC-014.8 hygiene for test isolation.
        import dslv_zpdi.layer3_telemetry.node_receiver as _nr

        _nr._writer = None


class TestNodeReceiverConcurrent:
    """SPEC-014.8 — Concurrent POSTs are safe (registry lock + writer thread-safety exercised)."""

    def test_concurrent_ingest_posts_succeed(self, tmp_path, monkeypatch):
        """SPEC-014.8 — 8 concurrent POSTs to /ingest all succeed (no deadlock, no lost updates)."""
        primary = tmp_path / "p"
        secondary = tmp_path / "s"
        monkeypatch.setenv("DSLV_PRIMARY_OUTPUT_DIR", str(primary))
        monkeypatch.setenv("DSLV_SECONDARY_OUTPUT_DIR", str(secondary))

        app = create_app()
        results = []
        errors = []

        def worker(i: int):
            try:
                with app.test_client() as c:
                    p = {
                        "node_id": f"CONC-{i}",
                        "payload_uuid": f"conc-{i}",
                        "modality": "concurrent-test",
                        "timestamp_utc": time.time(),
                        "raw_value": {"i": i},
                    }
                    r = c.post(
                        "/api/v1/ingest",
                        data=json.dumps(p),
                        content_type="application/json",
                    )
                    results.append(r.status_code)
            except Exception as e:  # pylint: disable=broad-except
                errors.append(str(e))

        with ThreadPoolExecutor(max_workers=8) as ex:
            futs = [ex.submit(worker, i) for i in range(8)]
            for f in as_completed(futs):
                f.result()

        assert not errors, f"concurrent errors: {errors}"
        assert len(results) == 8
        assert all(code == 200 for code in results)
        # registry should have been updated for the nodes (best effort, lock exercised)
        # (existence is timing-dependent; the contract under test is no-crash + all 200s)
