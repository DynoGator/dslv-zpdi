# SPEC-015 — RadonEye Pro RD200P Certified CRM Ingestion

**Status:** ACTIVE
**Trust Tier:** Certified CRM Context (Tier 2)
**Layer:** Layer 1 Ingestion

## Overview

Ingest telemetry from the EcoSense RadonEye Pro RD200P (NRPP CR-8306 / NRSB 31827) certified continuous radon monitor. The device runs natively and produces its own ANSI/AARST-aligned certified report (Deliverable A). This module produces the telemetry context (Deliverable B) — normalized radon readings with full provenance for the tamper-evident HDF5 audit.

**Critical rule:** Our code never edits, regenerates, or improves the RadonEye Pro's native certified report. We read its telemetry; we archive a copy + SHA256 of its report for chain-of-custody only.

## Transport Priority

1. **BLE GATT (primary)** — Most robust for field node. Uses `bleak`.
2. **HTTP fallback** — Polls local dashboard JSON endpoint when BLE unavailable.
3. **Simulator** — Deterministic synthetic data for CI and no-hardware development.

## BLE Protocol (FTLab/Ecosense RD200 Family)

| UUID | Role |
|------|------|
| `00001523-1212-efde-1523-785feabcd123` | Service |
| `00001524-1212-efde-1523-785feabcd123` | Command characteristic (write `0x50` to request data) |
| `00001525-1212-efde-1523-785feabcd123` | Data characteristic (20-byte response) |

Response bytes (little-endian):
- `[2:6]` float — 10-minute average radon (Bq/m³)
- `[6:10]` float — day average radon (Bq/m³)
- `[10:14]` float — month average radon (Bq/m³)
- `[14:16]` uint16 — pulse count
- `[16:18]` uint16 — 10-minute pulse count

Conversion: 1 pCi/L = 37 Bq/m³

## Sub-Specs

### SPEC-015.1 — RadonSample dataclass
Normalized radon telemetry sample with fields: `radon_pCiL`, `radon_Bqm3`, `sample_timestamp_utc`, `device_serial`, `firmware`, `transport`, `sample_quality`, `provenance`, `hardware_tier`.

### SPEC-015.2 — Layer 1 payload serialization
`RadonSample.to_ingestion_payload()` converts to a standard `IngestionPayload` with modality `radon` and `hardware_tier=2`.

### SPEC-015.3 — Simulator
Deterministic synthetic radon with configurable baseline, Gaussian noise, and weak diurnal drift.

### SPEC-015.4 — BLE transport
`RadonEyeBleTransport` handles device discovery, GATT write/read, and response parsing.

### SPEC-015.5 — GATT discovery helper
`probe_and_map()` connects and logs all service/characteristic UUIDs for documentation.

### SPEC-015.6 — HTTP fallback transport
`RadonEyeHttpTransport` polls a configurable JSON endpoint and normalizes the response.

### SPEC-015.7 — Unified ingestor
`RadonEyeIngestor` implements auto-failover: BLE → HTTP → SIM. Never raises on total failure.

### SPEC-015.8 — Test suite
Unit tests for parsing, serialization, simulator math, and failover behavior. All tests run without hardware.

## Kill Conditions
- Transport returns structurally invalid payload → SECONDARY_QUARANTINED
- Checksum/HMAC mismatch on archived certified report → integrity alert (do not alter report)
- Serial number mismatch between expected and observed → flag as `suspect` quality
