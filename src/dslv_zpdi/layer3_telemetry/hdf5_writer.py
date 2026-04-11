"""
SPEC-007 | Trust Tier: Institutional Persistence
Layer 3 implementation of HDF5 storage with SHA-256 attestation and HMAC.
"""

import hashlib
import hmac
import json
import logging
import subprocess
import time
from pathlib import Path
from typing import Dict, Optional

from dslv_zpdi.core.states import RouteStream
from dslv_zpdi.layer2_core.coherence import CoherencePacket
from .router import DualStreamRouter, RoutingDecision

try:
    import h5py

    HDF5_AVAILABLE = True
except ImportError:
    HDF5_AVAILABLE = False

logger = logging.getLogger("dslv-zpdi.hdf5")
FILE_VERSION = "3.1"
MAX_FILE_SIZE_BYTES = 500 * 1024 * 1024


# pylint: disable=too-many-instance-attributes
class HDF5Writer:
    """SPEC-007 — Institutional telemetry persistence with cryptographic attestation."""

    def __init__(
        self,
        output_path="./output/primary",
        secondary_path="./output/secondary",
        hardware_enclave_key: Optional[bytes] = None,
    ):
        """SPEC-007.1 — Initialize writer with output paths and attestation key."""
        self.output_dir = Path(output_path)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.secondary_dir = Path(secondary_path)
        self.secondary_dir.mkdir(parents=True, exist_ok=True)
        self.router = DualStreamRouter()
        self.key = hardware_enclave_key or b"dev_key_replace_before_field_deploy"
        self.current_file = None
        self.current_filepath: Optional[Path] = None
        self.event_count = 0
        self.stats: Dict[str, int] = {
            "primary_written": 0,
            "secondary_logged": 0,
            "rejected": 0,
        }

    def ingest(self, json_payload: str) -> RoutingDecision:
        """SPEC-007 — Process single packet through router and persist."""
        decision = self.router.route(json_payload)
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
        """SPEC-007 — Write institutional-grade packet to HDF5 with attestation."""
        if not HDF5_AVAILABLE:
            logger.warning("h5py not installed — primary write skipped")
            return
        if self.current_file is None or self._file_size_exceeded():
            self._rotate_file()

        group_name = f"event_{self.event_count:08d}_{packet.payload_uuid[:8]}"
        grp = self.current_file.create_group(group_name)
        grp.create_dataset("r_local", data=packet.r_local)
        grp.create_dataset("r_smooth", data=packet.r_smooth)
        grp.create_dataset("r_global", data=packet.r_global)
        grp.create_dataset("payload_uuid", data=packet.payload_uuid)

        try:
            payload_dict = json.loads(original_json)
            event_timestamp = payload_dict.get("timestamp_utc", time.time())
        except (json.JSONDecodeError, TypeError):
            event_timestamp = time.time()
        grp.create_dataset("timestamp_utc", data=event_timestamp)

        attestation = {
            "node_id": packet.node_id,
            "modality": packet.modality,
            "trust_state": packet.trust_state,
            "event_window_id": packet.event_window_id or "",
            "written_at_utc": time.time(),
            "file_version": FILE_VERSION,
            "chronyc_tracking": self._get_chronyc_state(),
        }

        content_bytes = json.dumps(
            {
                "r_local": packet.r_local,
                "r_smooth": packet.r_smooth,
                "r_global": packet.r_global,
                "payload_uuid": packet.payload_uuid,
                "timestamp_utc": event_timestamp,
            },
            sort_keys=True,
        ).encode()
        attestation["content_sha256"] = hashlib.sha256(content_bytes).hexdigest()

        attestation_json = json.dumps(attestation, sort_keys=True)
        attestation["hmac_sha256"] = hmac.new(
            self.key, attestation_json.encode(), hashlib.sha256
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
            self.current_file.close()
        filename = f"dslv_zpdi_{time.strftime('%Y%m%d_%H%M%S')}.h5"
        self.current_filepath = self.output_dir / filename
        self.current_file = h5py.File(self.current_filepath, "w")
        self.current_file.attrs["system"] = "DSLV-ZPDI"
        self.current_file.attrs["file_version"] = FILE_VERSION
        self.current_file.attrs["created_utc"] = time.time()
        self.event_count = 0

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

    def close(self):
        """SPEC-007 — Safely close current HDF5 file."""
        if self.current_file is not None:
            self.current_file.close()
            self.current_file = None

    def get_stats(self) -> Dict[str, int]:
        """SPEC-007 — Return pipeline statistics."""
        return {**self.stats, **self.router.stats}

    def verify_packet_integrity(
        self, packet: CoherencePacket, original_json: str
    ) -> bool:
        """SPEC-010 — Verify payload checksum before persistence."""
        try:
            payload_dict = json.loads(original_json)
            stored_checksum = payload_dict.get("payload_checksum", "")

            # Recompute checksum
            d = payload_dict.copy()
            d["payload_checksum"] = ""
            clean_json = json.dumps(d, sort_keys=True)
            computed_checksum = hashlib.sha256(clean_json.encode()).hexdigest()

            if stored_checksum != computed_checksum:
                logger.error(
                    "SPEC-010 VIOLATION: Checksum mismatch for %s", packet.payload_uuid
                )
                return False
            return True
        except (json.JSONDecodeError, KeyError):
            return False
