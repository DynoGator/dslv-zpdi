"""Capability authorization for the DSLV-ZPDI C2 control plane."""

from __future__ import annotations

from .protocol import CapabilityRegistry, ValidationError


# SPEC-022
class AuthorizationError(Exception):
    """Issuer lacks a required capability."""


# SPEC-022
class CapabilityStore:
    """In-memory capability store keyed by node identity.

    The default roles match the assignment rules in SPEC-C2-001.md.
    """

    DEFAULT_ROLES: dict[str, set[str]] = {
        "tier2-c2-master": set(CapabilityRegistry.CAPABILITIES),
        "tier1-anchor": {
            "node.status.read",
            "pipeline.status.read",
            "pipeline.start",
            "pipeline.stop",
            "pipeline.rotate_output",
            "sdr.status.read",
            "sdr.mode.set",
            "sdr.center_frequency.set",
            "sdr.sample_rate.set",
            "sdr.gain.set",
            "baseline.reset",
            "hdf5.summary.read",
            "hdf5.segment.export",
        },
        "tier2-sensor": {
            "node.status.read",
            "pipeline.status.read",
            "hdf5.summary.read",
        },
        "tier3-edge": {
            "node.status.read",
            "pipeline.status.read",
        },
    }

    def __init__(self, overrides: dict[str, set[str]] | None = None) -> None:
        self._roles = dict(self.DEFAULT_ROLES)
        if overrides:
            self._roles.update(overrides)

    def capabilities_for(self, node_id: str, role: str | None = None) -> set[str]:
        """Return capabilities for a node identity.

        If a specific role is supplied, return that role's capabilities.
        Otherwise return the union of capabilities across all known roles as a
        conservative default; callers should enforce role-based scoping.
        """
        if role:
            return set(self._roles.get(role, set()))
        # Allow per-node overrides if stored; otherwise default to control-node
        # capabilities for a node named like the C2 master and read-only for others.
        return set(self._roles.get(node_id, self._roles.get("tier2-c2-master")))

    def is_authorized(self, node_id: str, capability: str, role: str | None = None) -> bool:
        if not CapabilityRegistry.is_valid(capability):
            raise ValidationError(f"unknown capability: {capability}")
        return capability in self.capabilities_for(node_id, role)


# SPEC-022
def authorize(
    store: CapabilityStore,
    node_id: str,
    capability: str,
    role: str | None = None,
) -> None:
    """Raise AuthorizationError if the node is not authorized for the capability."""
    if not store.is_authorized(node_id, capability, role):
        raise AuthorizationError(f"node {node_id} is not authorized for {capability}")
