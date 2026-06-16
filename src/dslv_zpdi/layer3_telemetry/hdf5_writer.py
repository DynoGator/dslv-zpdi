"""
SPEC-007 | Trust Tier: Institutional Persistence
Layer 3 implementation of HDF5 storage with SHA-256 attestation and HMAC.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import logging
import subprocess
import threading
import time
from pathlib import Path

from dslv_zpdi.core.exceptions import SecurityError
from dslv_zpdi.core.key_provider import DevelopmentKeyProvider, KeyProvider
from dslv_zpdi.core.states import RouteStream
from dslv_zpdi.layer2_core.coherence import CoherencePacket

from .router import DualStreamRouter, RoutingDecision

try:
    import h5py

    HDF5_AVAILABLE = True
except (ImportError, OSError):
    # Rev 4.8.x: broaden for hosts where h5py C extension or libhdf5.so load
    # raises OSError instead of (or in addition to) ImportError. Matches
    # pattern for native libs (cf. libhackrf in hal_hardware). SPEC-007.
    HDF5_AVAILABLE = False

logger = logging.getLogger("dslv-zpdi.hdf5")
FILE_VERSION = "3.3"
MAX_FILE_SIZE_BYTES = 500 * 1024 * 1024


# pylint: disable=too-many-instance-attributes
class HDF5Writer:
    """SPEC-007 — Institutional telemetry persistence with cryptographic attestation."""

    def __init__(
        self,
        output_path="./output/primary",
        secondary_path="./output/secondary",
        hardware_enclave_key: bytes | None = None,
        key_provider: KeyProvider | None = None,
        source_node: str = "tier1-anchor",
        allow_development_key: bool = True,
    ):
        """
        SPEC-007.1 — Initialize writer with output paths and attestation key.

        Args:
            hardware_enclave_key: Deprecated; raw bytes for backward compatibility.
            key_provider: Key provider abstraction (preferred).
            allow_development_key: If True and no provider/key given, use the
                well-known development key. Must be False in field mode.
        """
        self.output_dir = Path(output_path)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.secondary_dir = Path(secondary_path)
        self.secondary_dir.mkdir(parents=True, exist_ok=True)
        self.router = DualStreamRouter()
        self.source_node = source_node
        self.allow_development_key = allow_development_key
        self._key_provider = key_provider
        self._key = self._resolve_key(hardware_enclave_key)
        self.key = self._key  # backward-compatible public alias
        self.current_file = None
        self.current_filepath: Path | None = None
        self._partial_filepath: Path | None = None
        self._write_lock = threading.Lock()
        self._lockfile_handle: object | None = None
        self.event_count = 0
        self._previous_chain_hash = self._genesis_hash()
        self._event_chain_hashes: list[str] = []
        self.stats: dict[str, int] = {
            "primary_written": 0,
            "secondary_logged": 0,
            "rejected": 0,
            "integrity_failed": 0,
            "checksum_missing": 0,
            "checksum_invalid": 0,
        }

    def _resolve_key(self, raw_key: bytes | None) -> bytes:
        """SPEC-007.1 — Resolve HMAC key from provider, raw bytes, or fail closed."""
        if raw_key is not None:
            return raw_key
        if self._key_provider is not None:
            return self._key_provider.get_key()
        if self.allow_development_key:
            logger.warning(
                "SPEC-007.1: HDF5Writer using INSECURE development HMAC key — "
                "attestation is NOT field-trustworthy. Supply a KeyProvider before deployment."
            )
            return DevelopmentKeyProvider(acknowledged_simulator_use=True).get_key()
        raise SecurityError(
            "HDF5Writer requires a KeyProvider or explicit allow_development_key=True"
        )

    @staticmethod
    def _genesis_hash() -> str:
        """SPEC-007.1 — Documented genesis value for event hash chain."""
        return hashlib.sha256(b"DSLV-ZPDI event-chain genesis v5.0.0").hexdigest()

    def ingest(self, json_payload: str) -> RoutingDecision:
        """SPEC-007 — Process single packet through router and persist."""
        decision = self.router.route(json_payload)
        if decision.packet is not None:
            integrity_ok = self.verify_packet_integrity(decision.packet, json_payload)
            if not integrity_ok:
                self.stats["integrity_failed"] += 1
                # Reject primary write; log to secondary for forensics
                self._log_secondary(json_payload, decision)
                return RoutingDecision(
                    RouteStream.SECONDARY.value,
                    "integrity_failed",
                    decision.packet,
                    decision.trust_state,
                )

        if decision.stream == RouteStream.PRIMARY.value and decision.packet is not None:
            self._write_primary(decision.packet, json_payload)
            self.stats["primary_written"] += 1
        elif decision.stream == RouteStream.SECONDARY.value:
            self._log_secondary(json_payload, decision)
            self.stats["secondary_logged"] += 1
        else:
            self.stats["rejected"] += 1
        return decision

    def _write_primary(self, packet: CoherencePacket, original_json: str):
        """SPEC-007 — Write institutional-grade packet to HDF5 with attestation.

        Thread-safe: acquires self._write_lock so that concurrent ingest calls
        from the local pipeline and the node-receiver HTTP server do not corrupt
        the HDF5 file.
        """
        if not HDF5_AVAILABLE:
            logger.warning("h5py not installed — primary write skipped")
            return
        with self._write_lock:
            self._write_primary_locked(packet, original_json)

    def _write_primary_locked(self, packet: CoherencePacket, original_json: str):
        """Inner write — called with _write_lock held."""
        if self.current_file is None or self._file_size_exceeded():
            self._rotate_file()

        group_name = f"event_{self.event_count:08d}_{packet.payload_uuid[:8]}"
        grp = self.current_file.create_group(group_name)
        grp.create_dataset("r_local", data=packet.r_local)
        grp.create_dataset("r_smooth", data=packet.r_smooth)
        grp.create_dataset("r_global", data=packet.r_global)
        grp.create_dataset("payload_uuid", data=packet.payload_uuid)
        from dslv_zpdi.layer2_core.wiring import coherence_engine

        bl = coherence_engine.get_baseline_status()
        grp.attrs["dynamic_threshold"] = bl.get("threshold", 0.40)
        grp.attrs["baseline_state"] = bl.get("baseline_state", "UNKNOWN")

        try:
            payload_dict = json.loads(original_json)
            event_timestamp = payload_dict.get("timestamp_utc", time.time())
        except (json.JSONDecodeError, TypeError):
            event_timestamp = time.time()
        grp.create_dataset("timestamp_utc", data=event_timestamp)

        # Event hash chain
        payload_checksum = (
            payload_dict.get("payload_checksum", "") if isinstance(payload_dict, dict) else ""
        )
        content_bytes = json.dumps(
            {
                "r_local": packet.r_local.tolist()
                if hasattr(packet.r_local, "tolist")
                else packet.r_local,
                "r_smooth": packet.r_smooth.tolist()
                if hasattr(packet.r_smooth, "tolist")
                else packet.r_smooth,
                "r_global": packet.r_global.tolist()
                if hasattr(packet.r_global, "tolist")
                else packet.r_global,
                "payload_uuid": packet.payload_uuid,
                "timestamp_utc": event_timestamp,
            },
            sort_keys=True,
        ).encode()
        content_sha256 = hashlib.sha256(content_bytes).hexdigest()

        event_payload_sha256 = payload_checksum or content_sha256
        previous_hash = self._previous_chain_hash
        chain_input = (
            previous_hash.encode()
            + event_payload_sha256.encode()
            + json.dumps(
                {"group": group_name, "timestamp_utc": event_timestamp}, sort_keys=True
            ).encode()
        )
        event_chain_sha256 = hashlib.sha256(chain_input).hexdigest()
        self._event_chain_hashes.append(event_chain_sha256)
        self._previous_chain_hash = event_chain_sha256

        attestation = {
            "node_id": packet.node_id,
            "source_node": self.source_node,
            "modality": packet.modality,
            "trust_state": packet.trust_state,
            "event_window_id": packet.event_window_id or "",
            "written_at_utc": time.time(),
            "file_version": FILE_VERSION,
            "chronyc_tracking": self._get_chronyc_state(),
            "content_sha256": content_sha256,
            "event_payload_sha256": event_payload_sha256,
            "previous_event_chain_sha256": previous_hash,
            "event_chain_sha256": event_chain_sha256,
            "event_sequence": self.event_count,
        }

        attestation_json = json.dumps(attestation, sort_keys=True)
        attestation["hmac_sha256"] = hmac.new(
            self._key, attestation_json.encode(), hashlib.sha256
        ).hexdigest()

        for k, v in attestation.items():
            grp.attrs[k] = v if isinstance(v, (int, float, str)) else str(v)

        self.event_count += 1
        logger.info("PRIMARY WRITE: %s (r_smooth=%.4f)", group_name, packet.r_smooth)

    def _log_secondary(self, json_payload: str, decision: RoutingDecision):
        """SPEC-007 — Append quarantined packet to secondary exploratory JSONL stream."""
        quarantine_file = self.secondary_dir / "quarantine.jsonl"
        log_entry = {
            "timestamp_utc": time.time(),
            "stream": decision.stream,
            "reason": decision.reason,
            "trust_state": decision.trust_state,
            "payload_snippet": json_payload[:500],
        }
        if decision.packet is not None:
            log_entry["r_smooth"] = decision.packet.r_smooth
            log_entry["node_id"] = decision.packet.node_id
        with open(quarantine_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(log_entry) + "\n")

    def _rotate_file(self):
        """SPEC-007 — Rotate HDF5 file to prevent unbounded growth."""
        if self.current_file is not None:
            self._finalize_file()
        filename = f"dslv_zpdi_{time.strftime('%Y%m%d_%H%M%S')}.h5"
        self.current_filepath = self.output_dir / filename
        self._partial_filepath = self.output_dir / (filename + ".partial")
        self.current_file = h5py.File(self._partial_filepath, "w")
        self.current_file.attrs["system"] = "DSLV-ZPDI"
        self.current_file.attrs["file_version"] = FILE_VERSION
        self.current_file.attrs["created_utc"] = time.time()
        self.event_count = 0
        self._previous_chain_hash = self._genesis_hash()
        self._event_chain_hashes = []

    def _finalize_file(self):
        """
        SPEC-007 — Atomic HDF5 finalization.

        Flush, close, reopen read-only, verify event chain, write manifest,
        and atomically rename .partial to .h5.
        """
        if self.current_file is None or self._partial_filepath is None:
            return

        try:
            self.current_file.flush()
            self.current_file.close()
        except Exception as exc:  # pylint: disable=broad-except
            logger.error("HDF5 finalization flush/close failed: %s", exc)
            self.current_file = None
            return

        # Reopen read-only to verify
        try:
            with h5py.File(self._partial_filepath, "r") as ro:
                self._verify_event_chain(ro)
        except Exception as exc:  # pylint: disable=broad-except
            logger.error(
                "HDF5 event-chain verification failed for %s: %s", self._partial_filepath, exc
            )
            # Leave .partial; do not advertise valid .h5
            self.current_file = None
            return

        # Write detached SHA-256
        try:
            file_bytes = self._partial_filepath.read_bytes()
            file_sha256 = hashlib.sha256(file_bytes).hexdigest()
            sha_path = self._partial_filepath.with_suffix(".h5.sha256")
            sha_path.write_text(f"{file_sha256}  {self._partial_filepath.name}\n", encoding="utf-8")
        except OSError as exc:
            logger.error("Failed to write detached SHA-256: %s", exc)

        # Atomic rename
        try:
            self._partial_filepath.rename(self.current_filepath)
            logger.info("HDF5 finalized: %s", self.current_filepath)
        except OSError as exc:
            logger.error("HDF5 atomic rename failed: %s", exc)

        # Detached status record
        try:
            status_path = self.current_filepath.with_suffix(".status.json")
            status = {
                "finalized": True,
                "filename": self.current_filepath.name,
                "event_count": self.event_count,
                "final_event_chain_sha256": self._previous_chain_hash,
                "finalized_at_utc": time.time(),
            }
            status_path.write_text(json.dumps(status, sort_keys=True), encoding="utf-8")
        except OSError as exc:
            logger.error("Failed to write status record: %s", exc)

        self.current_file = None

    def _verify_event_chain(self, h5file) -> None:
        """SPEC-007 — Verify event hash chain integrity."""
        previous = self._genesis_hash()
        for i in range(self.event_count):
            group_name = f"event_{i:08d}_"
            # Find group by prefix
            matches = [k for k in h5file if k.startswith(group_name)]
            if not matches:
                raise SecurityError(f"Missing event group for sequence {i}")
            grp = h5file[matches[0]]
            stored_prev = grp.attrs.get("previous_event_chain_sha256", "")
            stored_chain = grp.attrs.get("event_chain_sha256", "")
            if stored_prev != previous:
                raise SecurityError(f"Event chain broken at sequence {i}")
            if not stored_chain:
                raise SecurityError(f"Missing event chain hash at sequence {i}")
            previous = stored_chain

    def close(self):
        """SPEC-007 — Safely finalize and close current HDF5 file."""
        with self._write_lock:
            self._finalize_file()

    def _file_size_exceeded(self) -> bool:
        """SPEC-007 — Size check for rotation trigger."""
        if self.current_file is None:
            return True
        try:
            return self.current_file.id.get_filesize() > MAX_FILE_SIZE_BYTES
        except (AttributeError, RuntimeError, OSError):
            return False

    def _get_chronyc_state(self) -> str:
        """SPEC-004A.1 — Capture chronyc tracking state for timing attestation chain of custody."""
        try:
            result = subprocess.run(
                ["chronyc", "tracking"],
                capture_output=True,
                text=True,
                timeout=2,
                check=False,
            )
            if result.returncode == 0:
                return result.stdout.strip()[:500]
        except (FileNotFoundError, subprocess.TimeoutExpired, OSError):
            pass
        return "unavailable"

    def get_stats(self) -> dict[str, int]:
        """SPEC-007 — Return pipeline statistics."""
        return {**self.stats, **self.router.stats}

    def verify_packet_integrity(self, packet: CoherencePacket, original_json: str) -> bool:
        """SPEC-010 — Verify payload checksum before persistence."""
        try:
            payload_dict = json.loads(original_json)
            stored_checksum = payload_dict.get("payload_checksum", "")

            if not stored_checksum:
                logger.error("SPEC-010 VIOLATION: Missing checksum for %s", packet.payload_uuid)
                self.stats["checksum_missing"] += 1
                return False

            # Recompute checksum
            d = payload_dict.copy()
            d["payload_checksum"] = ""
            clean_json = json.dumps(d, sort_keys=True)
            computed_checksum = hashlib.sha256(clean_json.encode()).hexdigest()

            if stored_checksum != computed_checksum:
                logger.error("SPEC-010 VIOLATION: Checksum mismatch for %s", packet.payload_uuid)
                self.stats["checksum_invalid"] += 1
                return False
            return True
        except (json.JSONDecodeError, KeyError):
            self.stats["checksum_invalid"] += 1
            return False
