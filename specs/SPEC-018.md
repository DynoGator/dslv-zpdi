# SPEC-018 — HDF5 Schema Extension (48-Hour Radon Audit Envelope)

**Status:** ACTIVE
**Trust Tier:** Institutional Persistence (Extended)
**Layer:** Layer 3 Telemetry

## Overview

Surgical, additive extension to the existing HDF5 schema. All existing research-pipeline groups (`event_*`) remain untouched. Five new top-level branches are created alongside them, plus a signed manifest group.

## New Branches

### /certified_crm
**SPEC-018.1** — Radon series R(t), device serial, calibration status, archived native certified report + SHA256.

### /macro_atmosphere
**SPEC-018.2** — Barometric pressure P, dP/dt, relative humidity, wind speed/direction, local temperature.

### /space_weather
**SPEC-018.3** — NOAA-derived Kp index, IMF Bz, solar wind density and speed.

### /mobile_node_tier2
**SPEC-018.4** — Pixel 9 Pro XL magnetometer, GPS lat/lon/alt/accuracy, camera frame hashes, per-sample trust scores and flags.

### /validation_index
**SPEC-018.5** — Barometric Coherence Index χ(τ), pilot threshold state, review flag and reason.

### /manifest
**SPEC-018.8** — Signed manifest with per-branch checksums, analysis hash, HMAC-SHA256 attestation.

## Integrity Model

- Every branch is independently checksummed (SHA-256 of dataset values + sorted attrs).
- Manifest contains branch checksums, device serials, calibration status, operator ID, timestamps.
- Analysis hash = SHA-256 of ordered branch checksum concatenation.
- HMAC-SHA256 with the same enclave key as SPEC-007 protects manifest authenticity.
- Language: "tamper-evident" (hashes, signed manifest, chain-of-custody). NOT "immutable/unalterable."

## Sub-Specs

### SPEC-018.6 — RadonSessionWriter
Context-manager class that opens/creates an HDF5 file, ensures all branches exist, and provides write methods for each record type.

### SPEC-018.7 — Certified report archiving
`archive_certified_report()` stores a read-only copy of the native certified report with its SHA-256 and a `warning` attribute: "READ-ONLY — native certified report, do not modify."

### SPEC-018.8 — Manifest finalization
`write_manifest()` computes branch checksums, builds the manifest dict, signs it with HMAC-SHA256, and writes it to `/manifest/manifest_json`.

### SPEC-018.9 — Manifest verification
`verify_manifest()` recomputes branch checksums and verifies the HMAC. Returns True only if all checks pass.

### SPEC-018.10 — Test suite
Integration tests: create/close, write all branches, manifest checksum round-trip, 48-hour mock envelope, additive re-open.

## Kill Conditions
- Modifying or deleting existing `event_*` groups → pipeline violation
- Altering the native certified report after archive → legal/contract breach
- Missing manifest or mismatched checksums → integrity alert
