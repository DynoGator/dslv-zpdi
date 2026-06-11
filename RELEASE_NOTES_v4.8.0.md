# Release Notes — v4.8.0

**Date:** 2026-06-05 (release notes reconciled 2026-06-10)
**Phase:** 2B — Radon Validation Metrology Stack (Tier 2)
**Tag:** `v4.8.0`

## Summary

Phase 2B adds a Tier 2 radon-validation metrology stack alongside the existing
Tier 1 RF/GPSDO anchor. The new stack is additive and trust-subordinate: nothing
in this release alters the Tier 1 primary stream, the Kuramoto coherence core, or
the existing HDF5 event schema. All new sensor paths ship with a simulator so the
full suite validates with `DEV_SIMULATOR=1` and no physical hardware.

## Added

- **RadonEye Pro RD200P ingestor** (SPEC-015) — BLE GATT primary transport with
  HTTP fallback and a CI simulator. Reads radon concentration with BLE → HTTP →
  SIM graceful degradation. Remains **secondary-only** pending SPEC-015 promotion
  criteria.
- **Pixel 9 Pro XL mobile node bridge** (SPEC-016) — HTTP polling bridge with
  trust scoring (0.0–1.0); surfaces magnetometer, GPS fix, and camera perceptual
  hash. Sub-threshold scores are flagged for review.
- **Pi–Pixel uplink manager** (SPEC-017) — classifies hotspot connectivity as
  online / offline / degraded and triggers backfill replay on restore. Never
  blocks the Tier 1 primary stream.
- **HDF5 schema extension** (SPEC-018) — five new top-level branches
  (`certified_crm`, `macro_atmosphere`, `space_weather`, `mobile_node_tier2`,
  `validation_index`) with a signed manifest (per-branch SHA-256 + HMAC
  attestation). Existing event groups are unchanged.
- **Barometric coherence engine** (SPEC-019) — χ(τ) cross-correlation between
  radon and barometric pressure with optional RH weighting. The review flag is
  explicitly subordinate to certified CRM data and never overrides it.
- **48-hour session orchestrator** (SPEC-020) — full campaign lifecycle
  (init → run → finalize → summary) with resume-from-cache and a compound `.h5`
  audit file plus a human-readable summary.
- **Dashboard panel suite** (SPEC-021) — RADON, MOBILE/T2, and BCI panels added
  to the existing compact/wide layout with zero regression to current panels.
- **`SensorModality.RADON`** added to the ingestion enum contract.
- **`bleak>=0.21.0`** dependency for BLE GATT transport.

## Fixed

- Closed 27 pre-existing SPEC-ID orphan gaps (`node_receiver`, `pps_listener`,
  `nmea_stream`, `hal_hardware`) and added real `specs/SPEC-014.md`.
- Corrected LBE-1420 → LBE-1421 dual-output references in the living master and
  build sheet.

## Validation

- Full simulator suite green (`DEV_SIMULATOR=1`).
- `orphan_checker`, `repo_guard`, and `pip check` clean.

## Notes

Hardware-only paths (BLE radon transport, PPS/NMEA, HackRF) are validated in
simulator mode here and must still be confirmed on the Tier 1 Pi 5 per
`docs/collaboration/NEXT_STEPS.md`.
