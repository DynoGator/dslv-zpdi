"""
SPEC-006.5 | Trust Tier: Processed (Layer 2 Wiring) — Rev 3.1
Canonical wiring between Layer 1 ingestion JSON and CoherenceScorer.

Rev 3.1 FIXES:
  - Enum rehydration from string (fixes silent routing failure)
  - Phase extraction REMOVED (phases come from Layer 1 via extracted_phases)
  - No scipy imports (Layer 2 is hardware-agnostic)
"""
import os

from dslv_zpdi.layer1_ingestion.payload import IngestionPayload, SensorModality

from .coherence import CoherencePacket, CoherenceScorer


def _load_baseline_config() -> dict:
    """SPEC-009 — Load baseline learning parameters from environment."""
    cfg: dict = {}
    try:
        cfg["baseline_duration_hours"] = float(
            os.getenv("DSLV_BASELINE_HOURS", "72")
        )
    except ValueError:
        cfg["baseline_duration_hours"] = 72.0
    try:
        cfg["min_baseline_samples"] = int(
            os.getenv("DSLV_MIN_BASELINE_SAMPLES", "240")
        )
    except ValueError:
        cfg["min_baseline_samples"] = 240
    try:
        cfg["min_confirming_nodes"] = int(
            os.getenv("DSLV_MIN_CONFIRMING_NODES", "4")
        )
    except ValueError:
        cfg["min_confirming_nodes"] = 4
    cfg["baseline_state_path"] = os.getenv(
        "DSLV_BASELINE_STATE_PATH", "/var/lib/dslv_zpdi/baseline.json"
    )
    return cfg


_baseline_cfg = _load_baseline_config()
coherence_engine = CoherenceScorer(
    baseline_duration_hours=_baseline_cfg["baseline_duration_hours"],
    min_baseline_samples=_baseline_cfg["min_baseline_samples"],
    min_nodes=_baseline_cfg["min_confirming_nodes"],
    baseline_state_path=_baseline_cfg["baseline_state_path"],
)


def wire_to_coherence(payload: IngestionPayload) -> CoherencePacket | None:
    """SPEC-006.5a — Layer 2 Wiring (Rev 4.0 - Binary)
    Called by DualStreamRouter after every Layer 1 emission.
    Never called directly from Layer 1 or Layer 3.
    """
    if payload is None:
        return None

    # State machine enforcement (Section 5.2B)
    if payload.trust_state in ["SECONDARY_QUARANTINED", "KILLED"]:
        return None  # Do not process — these packets go to secondary stream only
    if payload.trust_state not in ["TIME_TRUSTED", "CAL_TRUSTED"]:
        return None  # Insufficient trust gate

    # Construct payload dict dynamically for coherence engine without json serialization
    payload_dict = {
        "node_id": payload.node_id,
        "modality": payload.modality,
        "timestamp_utc": payload.timestamp_utc,
        "payload_uuid": payload.payload_uuid,
        "trust_state": payload.trust_state
    }

    phases = payload.extracted_phases or []
    coherence_packet = coherence_engine.update(payload_dict, phases)
    coherence_packet.trust_state = "CORE_PROCESSED"
    return coherence_packet


def wire_mobile_to_coherence(payload: IngestionPayload) -> CoherencePacket | None:
    """Mobile-specific wiring that bypasses the Tier-1 trust gate.

    Tier-2 packets are inherently SECONDARY_QUARANTINED, but we still
    compute coherence scores for categorisation (noise / structured /
    anomalous) within the secondary stream per SPEC-007 mobile router.
    """
    if not payload:
        return None

    modality_str = payload.modality
    try:
        SensorModality(modality_str)
    except ValueError:
        if modality_str not in {
            "accel", "magnetometer", "barometer",
            "gyroscope", "rotation_vector", "geomagnetic_rotation", "gravity",
        }:
            return None

    trust_state = payload.trust_state
    if trust_state == "KILLED":
        return None

    payload_dict = {
        "node_id": payload.node_id,
        "modality": payload.modality,
        "timestamp_utc": payload.timestamp_utc,
        "payload_uuid": payload.payload_uuid,
        "trust_state": payload.trust_state
    }

    phases = payload.extracted_phases or []
    packet = coherence_engine.update(payload_dict, phases)
    packet.trust_state = "CORE_PROCESSED"
    return packet
