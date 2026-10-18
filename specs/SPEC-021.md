# SPEC-021 — Public Atlas (tamper-evident map uplink)

**Status:** Draft  
**Revision:** 1.0  
**Date:** 2026-09-15  
**Depends on:** SPEC-007 DualStreamRouter, SPEC-004 Tiering, HDF5 tamper-evidence

---

## Intent

The public face of DSLV-ZPDI is a map. Pins are visits that produced
institutional-grade metrology. Rings are points of interest for future
measurement. Nothing else belongs on the pin layer.

This spec is the GitHub-level contract for what may leave a node and appear
on Atlas. The website is a viewer. The node is the authority.

## Qualification — map pin (Alpha)

A capture may be **mapped** if and only if all of the following are true:

| Gate | Requirement |
|------|-------------|
| Tier | `alpha` (Tier-1). Pixel / USB IQ / RTL-SDR never qualify. |
| Format | HDF5 (`.h5`) with SHA-256 sidecar + HMAC-SHA256. |
| Clock | GPSDO-disciplined. LBE-1421 10 MHz → SDR `EXT_REF_CLK` and 1 PPS on GPIO. |
| Packet state | `PRIMARY_ACCEPTED` (SPEC-007 DualStreamRouter). |
| HMAC | `hmac_ok = true` |
| GNSS | 3D GPS lock |
| PPS | jitter ≤ 5000 ns |

Packet state machine (unchanged from SPEC-007):

```
RAW_CAPTURED → ASSEMBLED → TIME_TRUSTED → CAL_TRUSTED
  → CORE_PROCESSED → PRIMARY_CANDIDATE → PRIMARY_ACCEPTED
                                         ↖ SECONDARY_QUARANTINED
```

`SECONDARY_QUARANTINED` is never a pin.

## Passive uplink policy (default OFF)

The node does not push. Atlas does not pull. Uplink is operator opt-in,
off by default, and encouraged in the UI without coercion.

Even with opt-in, a qualifying capture is published only when:

1. **Idle** — the acquisition pipeline is not running. Premium data waits.
2. **Unmetered** — no uplink on cellular, save-data, or unknown-metered
   links. Fail closed if the link cannot be shown to be unmetered on a
   field node. (Desktop browsers without Network Information API may
   assume unmetered and must label that assumption.)
3. **Dwell** — passive. One file per idle window, not a burst.

Lower-tier data is **never** auto-uploaded.

## Correlated lower-tier overlay

An operator (or a requestor) may optionally load Tier-2 / SECONDARY at a
site that already has attested Alpha HDF5, when the secondary capture
overlaps the Alpha window (±6 h). This is a view flag, not a promotion.
It does not change DualStreamRouter state.

A site with only SECONDARY (e.g. Pixel GNSS, no GPSDO) stays a POI ring.

## Privacy

Location is a field site, not a person. Opt-in is per node operator.
Atlas rows are scientific: site, capture, hashes, RF/radon/E-field/Kp
metrics. No names, emails, or device identifiers beyond node IDs.

## Implementation

- Python: `src/dslv_zpdi/layer3_telemetry/atlas_uplink.py`
- Tests: `tests/test_atlas_uplink.py`
- Public map: DSLV-ZPDI Atlas landing page
