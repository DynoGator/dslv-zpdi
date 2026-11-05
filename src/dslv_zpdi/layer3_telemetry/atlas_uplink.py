"""
SPEC-021 | Trust Tier: Atlas uplink (Layer 3)
Passive map publish for PRIMARY_ACCEPTED Alpha HDF5 only.
Kill condition: any SECONDARY or non-GPSDO packet reaching Atlas.
"""

from __future__ import annotations

from dataclasses import dataclass

ATLAS_TIER = "alpha"
ATLAS_FORMAT = "hdf5"
ATLAS_STATE = "PRIMARY_ACCEPTED"
MAX_PPS_JITTER_NS = 5000.0
CORRELATION_WINDOW_S = 6 * 60 * 60


@dataclass(frozen=True)
class CaptureGate:
    tier: str
    format: str
    gpsdo_disciplined: bool
    packet_state: str
    hmac_ok: bool
    gps_lock: bool
    pps_jitter_ns: float | None = None


def qualifies_for_atlas(capture: CaptureGate) -> tuple[bool, list[str]]:
    """SPEC-021.1 — Return whether a capture may appear as an Atlas pin."""
    reasons: list[str] = []
    if capture.tier != ATLAS_TIER:
        reasons.append("Not Alpha / Tier-1")
    if capture.format != ATLAS_FORMAT:
        reasons.append("Not HDF5")
    if not capture.gpsdo_disciplined:
        reasons.append("GPSDO not disciplining")
    if capture.packet_state != ATLAS_STATE:
        reasons.append("Not PRIMARY_ACCEPTED")
    if not capture.hmac_ok:
        reasons.append("HMAC attestation failed")
    if not capture.gps_lock:
        reasons.append("No GPS 3D lock")
    if (
        capture.pps_jitter_ns is not None
        and capture.pps_jitter_ns > MAX_PPS_JITTER_NS
    ):
        reasons.append("PPS jitter exceeds 5 µs")
    return (not reasons, reasons)


@dataclass(frozen=True)
class UplinkPolicy:
    """SPEC-021.2 — Operator policy. opt_in defaults OFF. Fail closed on metered."""

    opt_in: bool = False
    node_idle: bool = False
    metered: bool = True


def may_uplink(qualify: bool, policy: UplinkPolicy) -> tuple[bool, list[str]]:
    """SPEC-021.3 — Passive publish: opt-in AND idle AND unmetered AND qualified."""
    reasons: list[str] = []
    if not policy.opt_in:
        reasons.append("Operator opt-in is OFF")
    if not policy.node_idle:
        reasons.append("Node is busy")
    if policy.metered:
        reasons.append("Link is metered")
    if not qualify:
        reasons.append("Capture is not Alpha HDF5 GPSDO PRIMARY")
    return (not reasons, reasons)
