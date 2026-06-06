# SPEC-017 — Network / Uplink Manager

**Status:** ACTIVE
**Trust Tier:** Network Infrastructure
**Layer:** Layer 1 Ingestion

## Overview

Monitors the Pi 5 ↔ Pixel 9 Pro XL hotspot relationship, exposes `network_status` for dashboard HW/PIPE panels, and coordinates offline-cache mode. When the hotspot drops, the node continues logging locally and flags samples as `offline_cached`. When the uplink returns, a `backfill_pending` flag alerts downstream consumers.

## Design Principles

- **Read-only:** Never modifies routing tables, NetworkManager state, or firewall rules.
- **Fail-safe:** A blipped hotspot must never corrupt or truncate an HDF5 session.
- **Observable:** All state is exposed via `NetworkStatus.to_dict()` for dashboard rendering.

## Sub-Specs

### SPEC-017.1 — NetworkStatus dataclass
Canonical snapshot: `online`, `mode` (online/offline/degraded), `primary_interface`, `gateway_ip`, `pixel_reachable`, `internet_reachable`, `dns_working`, `offline_since`, `backfill_pending`.

### SPEC-017.2 — UplinkManager
Runs connectivity checks using ICMP echo (ping) and DNS resolution. Detects default route via `ip route`. Pixel reachability is the primary criterion; internet reachability distinguishes "degraded" (hotspot up, no passthrough) from "offline".

### SPEC-017.3 — OfflineCacheCoordinator
Thin policy wrapper that returns a metadata tag (`offline_cached`, `backfill_pending`, etc.) for consumers to attach to every sample.

### SPEC-017.4 — Test suite
Unit tests for online/offline/degraded detection, backfill trigger logic, and coordinator tagging.

## Kill Conditions
- Modifying network configuration (routes, iptables, nmcli) → rejected by architecture review
- Dropping cached samples on uplink restore → pipeline violation
- Reporting online when Pixel is unreachable → trust erosion
