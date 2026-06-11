"""
SPEC-015 | Trust Tier: Certified CRM Ingestion (Tier 2 Context)
RadonEye Pro RD200P telemetry ingestor — BLE primary, HTTP fallback, simulator path.

Protocol Reference
──────────────────
BLE GATT (reverse-engineered from FTLab/Ecosense RD200 family):
  Service UUID:        00001523-1212-efde-1523-785feabcd123
  Write Char UUID:     00001524-1212-efde-1523-785feabcd123  (cmd 0x50 = request data)
  Read Char UUID:      00001525-1212-efde-1523-785feabcd123  (20-byte response)

  Response layout (little-endian):
    [0]     = 0x50 (echo of command)
    [1]     = 0x10 (status)
    [2:6]   = float  radon_10min  (Bq/m³)
    [6:10]  = float  radon_day    (Bq/m³)
    [10:14] = float  radon_month  (Bq/m³)
    [14:16] = uint16 pulse_count
    [16:18] = uint16 pulse_10min

  Conversion: 1 pCi/L = 37 Bq/m³

HTTP Fallback:
  Polls a configurable local endpoint (default http://192.168.4.1/data)
  for a JSON payload containing at minimum {radon_bq_m3, timestamp_utc, unit_id}.

Simulator:
  Generates realistic diurnal radon curves with configurable baseline.
"""

from __future__ import annotations

import asyncio
import json
import logging
import struct
import time
import uuid
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger("dslv-zpdi.radoneye")

# ── Known GATT UUIDs (FTLab/Ecosense RD200 family) ────────────────────────
_RD200_SERVICE_UUID = "00001523-1212-efde-1523-785feabcd123"
_RD200_CMD_CHAR_UUID = "00001524-1212-efde-1523-785feabcd123"
_RD200_DATA_CHAR_UUID = "00001524-1212-efde-1523-785feabcd123"
_RD200_DATA_CHAR_UUID = "00001525-1212-efde-1523-785feabcd123"

# ── Conversion constant ───────────────────────────────────────────────────
_BQ_M3_TO_PCI_L = 1.0 / 37.0


@dataclass
class RadonSample:
    """SPEC-015.1 — Normalized radon telemetry sample."""

    spec_id: str = "SPEC-015.1"
    radon_pCiL: float = 0.0  # noqa: N815 - unit-encoded schema field (pCi/L)
    radon_Bqm3: float = 0.0  # noqa: N815 - unit-encoded schema field (Bq/m^3)
    sample_timestamp_utc: float = 0.0
    device_serial: str = ""
    firmware: str = ""
    transport: str = "sim"  # ble | http | sim
    sample_quality: str = "good"  # good | suspect | poor
    provenance: dict[str, Any] = field(default_factory=dict)
    hardware_tier: int = 2

    def to_ingestion_payload(self, node_id: str = "PI5-ALPH", sensor_id: str = "RD200P-01") -> dict:
        """SPEC-015.2 — Serialize to Layer 1 ingestion contract dict."""
        from dslv_zpdi.layer1_ingestion.payload import IngestionPayload, SensorModality

        payload = IngestionPayload(
            payload_uuid=str(uuid.uuid4()),
            node_id=node_id,
            sensor_id=sensor_id,
            modality=SensorModality.RADON.value,
            timestamp_utc=self.sample_timestamp_utc,
            raw_value={
                "radon_pCiL": self.radon_pCiL,
                "radon_Bqm3": self.radon_Bqm3,
                "device_serial": self.device_serial,
                "firmware": self.firmware,
                "transport": self.transport,
                "sample_quality": self.sample_quality,
                "provenance": self.provenance,
            },
            gps_locked=False,  # Radon sensor has no GPS; system GPSDO state injected separately
            pps_jitter_ns=0.0,
            calibration_valid=self.sample_quality == "good",
            calibration_age_s=0.0,
            drift_percent=0.0,
            source_path=f"radoneye:{self.transport}",
            hardware_tier=self.hardware_tier,
            trust_state="ASSEMBLED",
        )
        return json.loads(payload.to_json())


# ── Simulator ─────────────────────────────────────────────────────────────

class RadonEyeSimulator:
    """SPEC-015.3 — Deterministic simulator for CI and offline development."""

    def __init__(self, baseline_bq_m3: float = 150.0, noise_sigma: float = 10.0):
        self.baseline = baseline_bq_m3
        self.noise = noise_sigma
        self._call_count = 0

    def read(self) -> RadonSample:
        """Generate a synthetic sample with diurnal drift + Gaussian noise."""
        import math
        import random

        self._call_count += 1
        t = time.time()
        # Weak diurnal: radon is typically higher in early morning
        hour = (t / 3600.0) % 24.0
        diurnal = 20.0 * math.sin((hour - 4.0) * math.pi / 12.0)
        value = self.baseline + diurnal + random.gauss(0, self.noise)
        value = max(0.0, value)

        return RadonSample(
            radon_Bqm3=round(value, 2),
            radon_pCiL=round(value * _BQ_M3_TO_PCI_L, 2),
            sample_timestamp_utc=t,
            device_serial="SIM-RD200P-000000",
            firmware="sim_2.1.0",
            transport="sim",
            sample_quality="good",
            provenance={
                "simulator": True,
                "call_count": self._call_count,
                "baseline_bq_m3": self.baseline,
            },
        )


# ── BLE Transport ─────────────────────────────────────────────────────────

class RadonEyeBleTransport:
    """SPEC-015.4 — BLE GATT transport via bleak."""

    def __init__(
        self,
        device_address: str | None = None,
        service_uuid: str = _RD200_SERVICE_UUID,
        cmd_char_uuid: str = _RD200_CMD_CHAR_UUID,
        data_char_uuid: str = _RD200_DATA_CHAR_UUID,
        timeout_sec: float = 10.0,
    ):
        self.device_address = device_address
        self.service_uuid = service_uuid
        self.cmd_char_uuid = cmd_char_uuid
        self.data_char_uuid = data_char_uuid
        self.timeout = timeout_sec
        self._discovered_uuids: list[str] = []

    async def _find_device(self) -> str | None:
        """Scan for RadonEye by name or address."""
        try:
            from bleak import BleakScanner
        except (ImportError, OSError) as exc:
            # Rev 4.8.x: bleak + dbus/bluez native stack on linux can raise
            # OSError (or dbus errors surfaced as such) at import time on
            # hosts without bluetooth libs / bus (simulator hosts). Broaden
            # per audit of native guards. SPEC-015.
            logger.error("bleak not installed — pip install bleak: %s", exc)
            return None

        logger.info("RadonEye BLE: scanning for device...")
        devices = await BleakScanner.discover(timeout=5.0)
        for dev in devices:
            name = (dev.name or "").lower()
            if self.device_address and dev.address.upper() == self.device_address.upper():
                return dev.address
            if any(k in name for k in ("radoneye", "rd200", "ftlab")):
                logger.info("RadonEye BLE: found candidate %s (%s)", dev.address, dev.name)
                return dev.address
        logger.warning("RadonEye BLE: no device found during scan")
        return None

    async def read(self) -> RadonSample:
        """Connect, request data, parse response, return sample."""
        try:
            from bleak import BleakClient
        except (ImportError, OSError) as exc:
            # Rev 4.8.x: guard bare import of BleakClient (native load via dbus)
            # so hosts without bleak/dbus degrade with clear error instead of
            # uncaught exception. SPEC-015.
            logger.error("bleak transport unavailable: %s", exc)
            raise RuntimeError(
                "RadonEye BLE: bleak not available (pip install bleak); "
                "use simulator or HTTP fallback"
            ) from exc

        address = self.device_address or await self._find_device()
        if not address:
            raise RuntimeError("RadonEye BLE: no device address known and scan found nothing")

        t0 = time.perf_counter()
        rssi: int | None = None

        try:
            async with BleakClient(address, timeout=self.timeout) as client:
                rssi = await client.get_rssi() if hasattr(client, "get_rssi") else None

                # Request fresh data: write 0x50 to cmd characteristic
                cmd_bytes = bytes([0x50])
                await client.write_gatt_char(self.cmd_char_uuid, cmd_bytes, response=True)
                await asyncio.sleep(0.5)  # sensor needs a moment

                # Read response
                data = await client.read_gatt_char(self.data_char_uuid)
                latency_ms = (time.perf_counter() - t0) * 1000.0

                sample = self._parse_data(data)
                sample.transport = "ble"
                sample.provenance = {
                    "ble_address": address,
                    "rssi_dbm": rssi,
                    "fetch_latency_ms": round(latency_ms, 2),
                    "gatt_service": self.service_uuid,
                    "raw_hex": data.hex(),
                }
                return sample
        except Exception as exc:
            logger.error("RadonEye BLE: read failed: %s", exc)
            raise

    def _parse_data(self, data: bytes) -> RadonSample:
        """Parse the 20-byte RD200 response payload."""
        if len(data) < 18:
            raise ValueError(f"RadonEye BLE: short payload ({len(data)} bytes)")

        # Expected header: 0x50 0x10
        if data[0] != 0x50:
            logger.warning("RadonEye BLE: unexpected response header 0x%02X", data[0])

        radon_10min = struct.unpack("<f", data[2:6])[0]
        radon_day = struct.unpack("<f", data[6:10])[0]
        radon_month = struct.unpack("<f", data[10:14])[0]
        puls = struct.unpack("<H", data[14:16])[0]
        puls10 = struct.unpack("<H", data[16:18])[0]

        # Use 10-minute average as the canonical live value
        bq = max(0.0, radon_10min)
        return RadonSample(
            radon_Bqm3=round(bq, 2),
            radon_pCiL=round(bq * _BQ_M3_TO_PCI_L, 2),
            sample_timestamp_utc=time.time(),
            device_serial="UNKNOWN",  # Could be extracted from BLE name or another char
            firmware="",
            sample_quality="good" if bq >= 0 else "suspect",
            provenance={
                "radon_day_bq_m3": round(radon_day, 2),
                "radon_month_bq_m3": round(radon_month, 2),
                "pulse_count": puls,
                "pulse_10min": puls10,
            },
        )

    async def probe_and_map(self) -> dict[str, Any]:
        """SPEC-015.5 — Discovery helper: connect and log all service/char UUIDs."""
        try:
            from bleak import BleakClient
        except (ImportError, OSError) as exc:
            # Rev 4.8.x: guard bare import of BleakClient (native load via dbus)
            # so hosts without bleak/dbus degrade with clear error instead of
            # uncaught exception. SPEC-015.
            logger.error("bleak transport unavailable: %s", exc)
            return {"error": "bleak not available (pip install bleak)"}

        address = self.device_address or await self._find_device()
        if not address:
            return {"error": "no device found"}

        result: dict[str, Any] = {"address": address, "services": {}}
        try:
            async with BleakClient(address, timeout=self.timeout) as client:
                for service in client.services:
                    result["services"][service.uuid] = {
                        "chars": [c.uuid for c in service.characteristics],
                    }
        except Exception as exc:
            result["error"] = str(exc)
        return result


# ── HTTP Fallback Transport ───────────────────────────────────────────────

class RadonEyeHttpTransport:
    """SPEC-015.6 — HTTP polling fallback for local dashboard endpoint."""

    def __init__(
        self,
        base_url: str = "http://192.168.4.1",
        endpoint: str = "/data",
        timeout_sec: float = 5.0,
    ):
        self.url = base_url.rstrip("/") + endpoint
        self.timeout = timeout_sec

    def read(self) -> RadonSample:
        """Synchronous HTTP GET — returns parsed RadonSample."""
        import urllib.request

        t0 = time.perf_counter()
        req = urllib.request.Request(
            self.url,
            headers={"Accept": "application/json"},
        )
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                body = resp.read().decode("utf-8")
                latency_ms = (time.perf_counter() - t0) * 1000.0
                data = json.loads(body)
                return self._parse_json(data, latency_ms)
        except Exception as exc:
            logger.error("RadonEye HTTP: fetch failed: %s", exc)
            raise

    def _parse_json(self, data: dict, latency_ms: float) -> RadonSample:
        """Normalize a JSON payload from the local HTTP endpoint."""
        bq = float(data.get("radon_bq_m3", 0.0))
        ts = float(data.get("timestamp_utc", time.time()))
        serial = str(data.get("unit_id", data.get("serial", "UNKNOWN")))
        firmware = str(data.get("firmware", ""))
        return RadonSample(
            radon_Bqm3=round(bq, 2),
            radon_pCiL=round(bq * _BQ_M3_TO_PCI_L, 2),
            sample_timestamp_utc=ts,
            device_serial=serial,
            firmware=firmware,
            transport="http",
            sample_quality="good" if bq >= 0 else "suspect",
            provenance={
                "endpoint": self.url,
                "fetch_latency_ms": round(latency_ms, 2),
                "http_status": 200,
                "raw_keys": list(data.keys()),
            },
        )


# ── Unified Ingestor ──────────────────────────────────────────────────────

class RadonEyeIngestor:
    """SPEC-015.7 — Unified ingestor with auto-failover BLE → HTTP → SIM."""

    def __init__(
        self,
        device_address: str | None = None,
        http_url: str = "http://192.168.4.1",
        http_endpoint: str = "/data",
        simulator: RadonEyeSimulator | None = None,
        prefer_ble: bool = True,
    ):
        self.prefer_ble = prefer_ble
        self.ble = RadonEyeBleTransport(device_address=device_address)
        self.http = RadonEyeHttpTransport(base_url=http_url, endpoint=http_endpoint)
        self.sim = simulator or RadonEyeSimulator()

    async def read(self) -> RadonSample:
        """Attempt BLE, then HTTP, then simulator.  Never raises — returns sim on total failure."""
        if self.prefer_ble:
            try:
                return await self.ble.read()
            except Exception as exc:
                logger.warning("RadonEye BLE failed (%s), trying HTTP fallback", exc)
            try:
                return self.http.read()
            except Exception as exc:
                logger.warning("RadonEye HTTP failed (%s), falling back to simulator", exc)
            return self.sim.read()

        # HTTP-first mode
        try:
            return self.http.read()
        except Exception as exc:
            logger.warning("RadonEye HTTP failed (%s), trying BLE fallback", exc)
        try:
            return await self.ble.read()
        except Exception as exc:
            logger.warning("RadonEye BLE failed (%s), falling back to simulator", exc)
        return self.sim.read()

    def read_sync(self) -> RadonSample:
        """Synchronous wrapper for non-async callers."""
        try:
            return asyncio.run(self.read())
        except RuntimeError:
            # If already inside an event loop, schedule and return
            loop = asyncio.get_event_loop()
            return loop.run_until_complete(self.read())

    async def probe(self) -> dict[str, Any]:
        """Run GATT discovery and return map of services/characteristics."""
        return await self.ble.probe_and_map()
