"""
SPEC-018 | Trust Tier: Institutional Persistence (Extended Schema)
HDF5 schema extension for the 48-hour radon validation metrology session.

Additive only — all existing research-pipeline groups (event_*) are left
untouched.  New top-level branches are created alongside them:

  /certified_crm      — radon series, device serial, calibration status,
                         archived certified report + SHA256
  /macro_atmosphere   — barometric P, dP/dt, RH, wind, local weather
  /space_weather      — Kp, IMF Bz, solar wind (NOAA-derived)
  /mobile_node_tier2  — Pixel magnetometer, GPS, camera hashes, trust scores
  /validation_index   — BCI χ, pilot threshold state, review flag
  /manifest           — signed manifest with per-branch checksums

Integrity Model
───────────────
Every branch is independently checksummed (SHA-256 of dataset values).
The signed manifest records branch checksums, device serials, calibration
status, operator ID, timestamps, and an analysis hash (SHA-256 of the
ordered branch checksums).  HMAC-SHA256 with the same enclave key as
SPEC-007 protects manifest authenticity.

Language
────────
The output is "tamper-evident" (hashes, signed manifest, chain-of-custody).
It is NOT "immutable/unalterable."  Per v2.1 proposal correction.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import logging
import time
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np

try:
    import h5py

    HDF5_AVAILABLE = True
except (ImportError, OSError):
    # Rev 4.8.x: broaden for hosts where h5py C extension or libhdf5.so load
    # raises OSError instead of (or in addition to) ImportError. Matches
    # pattern for native libs (cf. libhackrf in hal_hardware). SPEC-018.
    HDF5_AVAILABLE = False

logger = logging.getLogger("dslv-zpdi.radon-session")

MANIFEST_VERSION = "1.0"


@dataclass
class CertifiedCRMRecord:
    """SPEC-018.1 — Single certified CRM radon reading."""

    timestamp_utc: float
    radon_pCiL: float  # noqa: N815 - unit-encoded schema field (pCi/L)
    radon_Bqm3: float  # noqa: N815 - unit-encoded schema field (Bq/m^3)
    device_serial: str
    sample_quality: str = "good"


@dataclass
class AtmosphereRecord:
    """SPEC-018.2 — Macro-atmosphere boundary-layer reading."""

    timestamp_utc: float
    pressure_hPa: float | None = None  # noqa: N815 - unit-encoded schema field (hPa)
    dp_dt_hPa_h: float | None = None  # noqa: N815 - unit-encoded schema field (hPa/h)
    relative_humidity_pct: float | None = None
    wind_speed_ms: float | None = None
    wind_dir_deg: float | None = None
    local_temp_c: float | None = None


@dataclass
class SpaceWeatherRecord:
    """SPEC-018.3 — Space weather snapshot."""

    timestamp_utc: float
    kp_index: float | None = None
    imf_bz_nt: float | None = None
    solar_wind_density_cm3: float | None = None
    solar_wind_speed_kms: float | None = None


@dataclass
class MobileNodeRecord:
    """SPEC-018.4 — Tier 2 mobile node sample."""

    timestamp_utc: float
    magnetometer_ut: list[float] | None = None
    gps_lat: float | None = None
    gps_lon: float | None = None
    gps_alt: float | None = None
    gps_accuracy: float | None = None
    camera_frame_hash: str | None = None
    trust_score: float = 0.0
    trust_flags: list[str] = field(default_factory=list)


@dataclass
class ValidationIndexRecord:
    """SPEC-018.5 — Barometric Coherence Index output."""

    timestamp_utc: float
    chi_tau: float = 0.0
    pilot_threshold: float = 0.65
    review_flag: bool = False
    review_reason: str = ""


class RadonSessionWriter:
    """SPEC-018.6 — Extended HDF5 writer for the 48-hour radon audit envelope."""

    def __init__(
        self,
        filepath: str,
        operator_id: str = "operator_unknown",
        enclave_key: bytes | None = None,
    ):
        if not HDF5_AVAILABLE:
            raise RuntimeError("h5py is required for RadonSessionWriter")

        self.filepath = Path(filepath)
        self.filepath.parent.mkdir(parents=True, exist_ok=True)
        self.operator_id = operator_id
        self.key = enclave_key or b"dev_key_replace_before_field_deploy"
        self._file: h5py.File | None = None
        self._branch_counts: dict[str, int] = {}
        self._open()

    # ── Lifecycle ──────────────────────────────────────────────────────────

    def _open(self):
        self._file = h5py.File(self.filepath, "a")
        # Ensure top-level groups exist (additive, idempotent)
        for name in (
            "certified_crm",
            "macro_atmosphere",
            "space_weather",
            "mobile_node_tier2",
            "validation_index",
            "manifest",
        ):
            if name not in self._file:
                self._file.create_group(name)
            # Resume count from existing datasets so we never collide
            grp = self._file[name]
            existing = [k for k in grp.keys() if not k.startswith("report_")]
            self._branch_counts[name] = len(existing)

    def close(self):
        if self._file is not None:
            self._file.close()
            self._file = None

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
        return False

    # ── Branch writers ─────────────────────────────────────────────────────

    def write_certified_crm(self, record: CertifiedCRMRecord) -> str:
        """Append a radon sample to /certified_crm."""
        grp = self._file["certified_crm"]
        idx = self._branch_counts["certified_crm"]
        ds_name = f"r_{idx:08d}"
        ds = grp.create_dataset(ds_name, data=record.radon_pCiL)
        ds.attrs["timestamp_utc"] = record.timestamp_utc
        ds.attrs["radon_Bqm3"] = record.radon_Bqm3
        ds.attrs["device_serial"] = record.device_serial
        ds.attrs["sample_quality"] = record.sample_quality
        self._branch_counts["certified_crm"] += 1
        return ds_name

    def write_macro_atmosphere(self, record: AtmosphereRecord) -> str:
        """Append an atmosphere sample to /macro_atmosphere."""
        grp = self._file["macro_atmosphere"]
        idx = self._branch_counts["macro_atmosphere"]
        ds_name = f"a_{idx:08d}"
        # Store as a compact float32 array: [P, dP/dt, RH, wind_spd, wind_dir, temp]
        arr = np.array(
            [
                record.pressure_hPa or np.nan,
                record.dp_dt_hPa_h or np.nan,
                record.relative_humidity_pct or np.nan,
                record.wind_speed_ms or np.nan,
                record.wind_dir_deg or np.nan,
                record.local_temp_c or np.nan,
            ],
            dtype=np.float32,
        )
        ds = grp.create_dataset(ds_name, data=arr)
        ds.attrs["timestamp_utc"] = record.timestamp_utc
        self._branch_counts["macro_atmosphere"] += 1
        return ds_name

    def write_space_weather(self, record: SpaceWeatherRecord) -> str:
        """Append a space-weather snapshot to /space_weather."""
        grp = self._file["space_weather"]
        idx = self._branch_counts["space_weather"]
        ds_name = f"sw_{idx:08d}"
        arr = np.array(
            [
                record.kp_index or np.nan,
                record.imf_bz_nt or np.nan,
                record.solar_wind_density_cm3 or np.nan,
                record.solar_wind_speed_kms or np.nan,
            ],
            dtype=np.float32,
        )
        ds = grp.create_dataset(ds_name, data=arr)
        ds.attrs["timestamp_utc"] = record.timestamp_utc
        self._branch_counts["space_weather"] += 1
        return ds_name

    def write_mobile_node(self, record: MobileNodeRecord) -> str:
        """Append a Tier 2 mobile node sample to /mobile_node_tier2."""
        grp = self._file["mobile_node_tier2"]
        idx = self._branch_counts["mobile_node_tier2"]
        ds_name = f"m_{idx:08d}"
        mag = np.array(record.magnetometer_ut or [np.nan, np.nan, np.nan], dtype=np.float32)
        ds = grp.create_dataset(ds_name, data=mag)
        ds.attrs["timestamp_utc"] = record.timestamp_utc
        ds.attrs["gps_lat"] = record.gps_lat or np.nan
        ds.attrs["gps_lon"] = record.gps_lon or np.nan
        ds.attrs["gps_alt"] = record.gps_alt or np.nan
        ds.attrs["gps_accuracy"] = record.gps_accuracy or np.nan
        ds.attrs["camera_frame_hash"] = record.camera_frame_hash or ""
        ds.attrs["trust_score"] = record.trust_score
        ds.attrs["trust_flags"] = json.dumps(record.trust_flags)
        self._branch_counts["mobile_node_tier2"] += 1
        return ds_name

    def write_validation_index(self, record: ValidationIndexRecord) -> str:
        """Append a BCI validation record to /validation_index."""
        grp = self._file["validation_index"]
        idx = self._branch_counts["validation_index"]
        ds_name = f"v_{idx:08d}"
        ds = grp.create_dataset(ds_name, data=record.chi_tau)
        ds.attrs["timestamp_utc"] = record.timestamp_utc
        ds.attrs["pilot_threshold"] = record.pilot_threshold
        ds.attrs["review_flag"] = record.review_flag
        ds.attrs["review_reason"] = record.review_reason
        self._branch_counts["validation_index"] += 1
        return ds_name

    def archive_certified_report(self, report_bytes: bytes, filename: str) -> str:
        """SPEC-018.7 — Store a read-only copy of the native certified report."""
        grp = self._file["certified_crm"]
        ds = grp.create_dataset(
            f"report_{filename}",
            data=np.frombuffer(report_bytes, dtype=np.uint8),
        )
        ds.attrs["filename"] = filename
        ds.attrs["sha256"] = hashlib.sha256(report_bytes).hexdigest()
        ds.attrs["archived_utc"] = time.time()
        ds.attrs["warning"] = "READ-ONLY — native certified report, do not modify"
        logger.info("Archived certified report %s (%d bytes)", filename, len(report_bytes))
        return str(ds.name)

    # ── Integrity ──────────────────────────────────────────────────────────

    def _branch_checksum(self, group_name: str) -> str:
        """Compute SHA-256 over all dataset values in a branch."""
        grp = self._file[group_name]
        hasher = hashlib.sha256()
        for name in sorted(grp.keys()):
            ds = grp[name]
            hasher.update(ds[()].tobytes())
            # Include attrs in canonical order
            for attr_name in sorted(ds.attrs.keys()):
                hasher.update(str(ds.attrs[attr_name]).encode())
        return hasher.hexdigest()

    def write_manifest(self) -> dict:
        """SPEC-018.8 — Finalize session and write signed manifest."""
        branches = {}
        for name in (
            "certified_crm",
            "macro_atmosphere",
            "space_weather",
            "mobile_node_tier2",
            "validation_index",
        ):
            branches[name] = {
                "checksum": self._branch_checksum(name),
                "record_count": self._branch_counts.get(name, 0),
            }

        # Analysis hash = SHA-256 of ordered branch checksums
        analysis_input = "|".join(
            f"{k}:{branches[k]['checksum']}" for k in sorted(branches.keys())
        )
        analysis_hash = hashlib.sha256(analysis_input.encode()).hexdigest()

        manifest = {
            "manifest_version": MANIFEST_VERSION,
            "session_filepath": str(self.filepath),
            "operator_id": self.operator_id,
            "created_utc": time.time(),
            "branches": branches,
            "analysis_hash": analysis_hash,
        }

        manifest_json = json.dumps(manifest, sort_keys=True)
        manifest["hmac_sha256"] = hmac.new(
            self.key, manifest_json.encode(), hashlib.sha256
        ).hexdigest()

        grp = self._file["manifest"]
        # Overwrite any previous manifest
        if "manifest_json" in grp:
            del grp["manifest_json"]
        ds = grp.create_dataset("manifest_json", data=manifest_json.encode())
        ds.attrs["hmac_sha256"] = manifest["hmac_sha256"]
        ds.attrs["written_utc"] = time.time()

        logger.info("Manifest written: analysis_hash=%s", analysis_hash)
        return manifest

    def verify_manifest(self) -> bool:
        """SPEC-018.9 — Verify manifest HMAC and recompute branch checksums."""
        grp = self._file["manifest"]
        if "manifest_json" not in grp:
            logger.error("No manifest found in file")
            return False

        raw = grp["manifest_json"][()]
        stored_json = raw.tobytes().decode() if hasattr(raw, "tobytes") else raw.decode()
        stored = json.loads(stored_json)
        stored_hmac = grp["manifest_json"].attrs.get("hmac_sha256", "")

        # Verify HMAC (manifest_json dataset does NOT include hmac_sha256 key)
        computed_hmac = hmac.new(
            self.key, json.dumps(stored, sort_keys=True).encode(), hashlib.sha256
        ).hexdigest()
        if not hmac.compare_digest(stored_hmac, computed_hmac):
            logger.error("Manifest HMAC mismatch")
            return False

        # Verify branch checksums
        for branch_name, branch_info in stored["branches"].items():
            expected = branch_info["checksum"]
            actual = self._branch_checksum(branch_name)
            if expected != actual:
                logger.error(
                    "Branch checksum mismatch: %s expected=%s actual=%s",
                    branch_name, expected, actual,
                )
                return False

        logger.info("Manifest and all branch checksums verified")
        return True
