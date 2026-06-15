"""
SPEC-016 | Trust Tier: Tier 2 Mobile Node Context
Pixel 9 Pro XL (GrapheneOS) mobile node bridge — HTTP polling primary,
simulator path, reconnect-tolerant, with explicit trust scoring.

The Pixel serves as both Tier 2 sensor node and internet hotspot.
This bridge polls a lightweight JSON publisher running inside Termux
on the hotspot subnet.  If the Pixel drops off the LAN, the bridge
returns the last cached telemetry stamped stale — it never blocks the
pipeline and never promotes Tier 2 data to Tier 1.

Trust Model
───────────
Every poll returns a trust_score (0.0–1.0) and trust_flags list.
Thresholds are configurable; the default trust_threshold is 0.5.
Samples below threshold are still logged to the HDF5 /mobile_node_tier2
branch but carry a "quarantine" flag so they cannot influence Tier 1
processing.

Sensor Ingest
─────────────
- Magnetometer (µT, 3-axis)         → RF/EM context
- GPS (lat, lon, alt, accuracy)     → vectoring / cross-check against LBE-1421 NMEA
- Low-res camera frame              → tamper-evidence (hash stored, frame archived)
- Accelerometer, light, pressure    → opportunistic, quality-gated
"""

from __future__ import annotations

import hashlib
import json
import logging
import math
import time
import uuid
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger("dslv-zpdi.pixel-bridge")

# ── Earth's magnetic field nominal range (µT) ─────────────────────────────
_EARTH_FIELD_MIN_UT = 25.0
_EARTH_FIELD_MAX_UT = 65.0


@dataclass
class PixelTelemetry:
    """SPEC-016.1 — Normalized Pixel 9 Pro XL telemetry sample."""

    spec_id: str = "SPEC-016.1"
    timestamp_utc: float = 0.0
    magnetometer_ut: list[float] | None = None  # [x, y, z]
    gps_lat: float | None = None
    gps_lon: float | None = None
    gps_alt: float | None = None
    gps_accuracy: float | None = None
    camera_frame_hash: str | None = None
    camera_frame_path: str | None = None
    accelerometer: list[float] | None = None
    light_lux: float | None = None
    pressure_hpa: float | None = None
    trust_score: float = 0.0
    trust_flags: list[str] = field(default_factory=list)
    transport: str = "sim"  # http | sim
    hardware_tier: int = 2

    def to_ingestion_payload(
        self,
        node_id: str = "PIXEL-9PRO-T2",
        sensor_id: str = "PIXEL-NODE-01",
    ) -> dict:
        """SPEC-016.2 — Serialize to Layer 1 ingestion contract dict."""
        from dslv_zpdi.layer1_ingestion.payload import IngestionPayload, SensorModality

        # Determine modality based on what sensors are present
        modality = SensorModality.MAGNETOMETER.value
        if self.gps_lat is not None:
            modality = SensorModality.GPS_PPS.value

        payload = IngestionPayload(
            payload_uuid=str(uuid.uuid4()),
            node_id=node_id,
            sensor_id=sensor_id,
            modality=modality,
            timestamp_utc=self.timestamp_utc,
            raw_value={
                "magnetometer_ut": self.magnetometer_ut,
                "gps": {
                    "lat": self.gps_lat,
                    "lon": self.gps_lon,
                    "alt": self.gps_alt,
                    "accuracy": self.gps_accuracy,
                },
                "camera_frame_hash": self.camera_frame_hash,
                "camera_frame_path": self.camera_frame_path,
                "accelerometer": self.accelerometer,
                "light_lux": self.light_lux,
                "pressure_hpa": self.pressure_hpa,
                "trust_score": self.trust_score,
                "trust_flags": self.trust_flags,
                "transport": self.transport,
            },
            gps_locked=self.gps_accuracy is not None and self.gps_accuracy <= 50.0,
            pps_jitter_ns=0.0,
            calibration_valid=self.trust_score >= 0.5,
            calibration_age_s=0.0,
            drift_percent=0.0,
            source_path=f"pixel:{self.transport}",
            hardware_tier=self.hardware_tier,
            trust_state="ASSEMBLED",
        )
        return json.loads(payload.to_json())


# ── Trust Scorer ──────────────────────────────────────────────────────────


class PixelTrustScorer:
    """SPEC-016.3 — Compute trust score and flags from raw telemetry."""

    def __init__(
        self,
        mag_min_ut: float = _EARTH_FIELD_MIN_UT,
        mag_max_ut: float = _EARTH_FIELD_MAX_UT,
        max_gps_accuracy_m: float = 50.0,
        staleness_sec: float = 60.0,
    ):
        self.mag_min = mag_min_ut
        self.mag_max = mag_max_ut
        self.max_gps_accuracy = max_gps_accuracy_m
        self.staleness_sec = staleness_sec

    def score(self, data: dict, received_utc: float) -> tuple[float, list[str]]:
        """Return (trust_score, trust_flags)."""
        flags: list[str] = []
        score = 1.0

        # GPS quality
        gps = data.get("gps") or {}
        acc = gps.get("accuracy")
        if acc is None:
            flags.append("no_gps")
            score -= 0.3
        elif acc > self.max_gps_accuracy:
            flags.append("coarse_gps")
            score -= 0.2

        # Magnetometer sanity
        mag = data.get("magnetometer_ut")
        if mag is None or len(mag) != 3:
            flags.append("no_magnetometer")
            score -= 0.2
        else:
            magnitude = math.sqrt(sum(v * v for v in mag))
            if not (self.mag_min <= magnitude <= self.mag_max):
                flags.append("mag_anomaly")
                score -= 0.15

        # Tamper-evidence frame
        if not data.get("camera_frame_hash"):
            flags.append("no_tamper_evidence")
            score -= 0.1

        # Staleness (if the Pixel's own timestamp is old)
        pixel_ts = data.get("timestamp_utc", received_utc)
        if received_utc - pixel_ts > self.staleness_sec:
            flags.append("stale_data")
            score -= 0.25

        # Opportunistic sensors (nice-to-have, no penalty for missing)
        if data.get("pressure_hpa") is not None:
            score += 0.05
        if data.get("light_lux") is not None:
            score += 0.05

        score = max(0.0, min(1.0, score))
        return round(score, 2), flags


# ── HTTP Transport ────────────────────────────────────────────────────────


class PixelHttpTransport:
    """SPEC-016.4 — Poll the Pixel's Termux JSON publisher over HTTP."""

    def __init__(
        self,
        host: str = "10.42.0.2",
        port: int = 8777,
        endpoint: str = "/telemetry",
        timeout_sec: float = 5.0,
        retries: int = 2,
    ):
        self.base_url = f"http://{host}:{port}"
        self.endpoint = endpoint
        self.timeout = timeout_sec
        self.retries = retries
        self._last_good: PixelTelemetry | None = None

    def _fetch(self) -> dict:
        import urllib.request

        url = f"{self.base_url}{self.endpoint}"
        req = urllib.request.Request(url, headers={"Accept": "application/json"})
        last_exc: Exception | None = None
        for attempt in range(self.retries + 1):
            try:
                with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                    return json.loads(resp.read().decode("utf-8"))
            except Exception as exc:
                last_exc = exc
                logger.debug(
                    "Pixel HTTP fetch attempt %d/%d failed: %s", attempt + 1, self.retries + 1, exc
                )
                if attempt < self.retries:
                    time.sleep(1.0)
        raise RuntimeError(f"Pixel HTTP unreachable after {self.retries + 1} attempts: {last_exc}")

    def poll(self, trust_scorer: PixelTrustScorer) -> PixelTelemetry:
        """Poll Pixel, score trust, return telemetry."""
        t0 = time.perf_counter()
        try:
            data = self._fetch()
            latency_ms = (time.perf_counter() - t0) * 1000.0
            logger.debug("Pixel poll latency: %.1f ms", latency_ms)
            received_utc = time.time()
            score, flags = trust_scorer.score(data, received_utc)

            telem = PixelTelemetry(
                timestamp_utc=float(data.get("timestamp_utc", received_utc)),
                magnetometer_ut=data.get("magnetometer_ut"),
                gps_lat=_safe_float(data.get("gps", {}).get("lat")),
                gps_lon=_safe_float(data.get("gps", {}).get("lon")),
                gps_alt=_safe_float(data.get("gps", {}).get("alt")),
                gps_accuracy=_safe_float(data.get("gps", {}).get("accuracy")),
                camera_frame_hash=data.get("camera_frame_hash"),
                camera_frame_path=data.get("camera_frame_path"),
                accelerometer=data.get("accelerometer"),
                light_lux=_safe_float(data.get("light_lux")),
                pressure_hpa=_safe_float(data.get("pressure_hpa")),
                trust_score=score,
                trust_flags=flags,
                transport="http",
            )
            self._last_good = telem
            return telem
        except Exception as exc:
            logger.warning("Pixel HTTP poll failed: %s — returning cached/stale", exc)
            if self._last_good is not None:
                stale = self._last_good
                stale.trust_flags = list(stale.trust_flags) + ["hotspot_drop"]
                stale.trust_score = max(0.0, stale.trust_score - 0.3)
                stale.timestamp_utc = time.time()
                return stale
            # No cache — return empty telemetry with zero trust
            return PixelTelemetry(
                timestamp_utc=time.time(),
                trust_score=0.0,
                trust_flags=["unreachable", "no_cache"],
                transport="http",
            )


# ── Simulator ─────────────────────────────────────────────────────────────


class PixelSimulator:
    """SPEC-016.5 — Deterministic simulator for CI and offline development."""

    def __init__(
        self,
        fixed_lat: float = 40.7128,
        fixed_lon: float = -74.0060,
        fixed_alt: float = 10.0,
    ):
        self.lat = fixed_lat
        self.lon = fixed_lon
        self.alt = fixed_alt
        self._call_count = 0

    def poll(self, trust_scorer: PixelTrustScorer) -> PixelTelemetry:
        import random

        self._call_count += 1
        t = time.time()

        # Simulate magnetometer with small noise around ~50 µT magnitude
        mag_base = [30.0, 10.0, 40.0]
        mag = [v + random.gauss(0, 1.0) for v in mag_base]

        # Simulate GPS accuracy jitter
        acc = random.gauss(8.0, 3.0)
        acc = max(2.0, acc)

        # Simulate camera hash every 3rd call
        cam_hash = None
        if self._call_count % 3 == 1:
            cam_hash = hashlib.sha256(f"frame_{self._call_count}".encode()).hexdigest()[:16]

        data = {
            "timestamp_utc": t,
            "magnetometer_ut": mag,
            "gps": {"lat": self.lat, "lon": self.lon, "alt": self.alt, "accuracy": acc},
            "camera_frame_hash": cam_hash,
            "accelerometer": [0.0, 0.0, 9.8],
            "light_lux": random.gauss(300, 50),
            "pressure_hpa": random.gauss(1013, 5),
        }
        score, flags = trust_scorer.score(data, t)

        return PixelTelemetry(
            timestamp_utc=t,
            magnetometer_ut=mag,
            gps_lat=self.lat,
            gps_lon=self.lon,
            gps_alt=self.alt,
            gps_accuracy=acc,
            camera_frame_hash=cam_hash,
            accelerometer=[0.0, 0.0, 9.8],
            light_lux=data["light_lux"],
            pressure_hpa=data["pressure_hpa"],
            trust_score=score,
            trust_flags=flags,
            transport="sim",
        )


# ── Unified Bridge ────────────────────────────────────────────────────────


class PixelNodeBridge:
    """SPEC-016.6 — Unified Pixel bridge with auto-failover HTTP → SIM."""

    def __init__(
        self,
        host: str = "10.42.0.2",
        http_port: int = 8777,
        timeout_sec: float = 5.0,
        trust_threshold: float = 0.5,
        simulator: PixelSimulator | None = None,
    ):
        self.trust_scorer = PixelTrustScorer()
        self.trust_threshold = trust_threshold
        self.http = PixelHttpTransport(host=host, port=http_port, timeout_sec=timeout_sec)
        self.sim = simulator or PixelSimulator()

    def poll(self) -> PixelTelemetry:
        """Poll HTTP first; on total failure return simulator (never raises)."""
        telem = self.http.poll(self.trust_scorer)
        # If HTTP transport itself is dead (no connection at all), fall back to sim
        if "unreachable" in telem.trust_flags and "no_cache" in telem.trust_flags:
            logger.info("Pixel bridge: HTTP totally unreachable, returning simulator")
            return self.sim.poll(self.trust_scorer)
        return telem

    def poll_sync(self) -> PixelTelemetry:
        """Synchronous wrapper for non-async callers."""
        return self.poll()


# ── Helpers ───────────────────────────────────────────────────────────────


# SPEC-016.8 — Safe float coercion helper
def _safe_float(value: Any) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None
