# Tier-1 Hardware Qualification Standard

## Principle

Tier-1 status is awarded by evidence, not vendor name. A candidate RF
instrument and timing architecture must meet or exceed the canonical
metrology contract in every mandatory dimension.

## Mandatory Dimensions

| Dimension | Evidence Required | Kill Condition |
|-----------|------------------|----------------|
| Amplitude resolution | ADC bit depth, ENOB if measured | Below floor |
| Instantaneous bandwidth | Sustained capture at requested bandwidth | Cannot sustain requested BW |
| Sustainable sample throughput | Sustained sample rate with accounting | Unaccounted sample loss |
| Dropped-sample rate | Buffer/sequence counters | Any unexplained loss |
| Frequency accuracy/stability | GPSDO lock + external reference evidence | No external reference evidence |
| Timestamp accuracy | PPS + chrony + capture timestamps | PPS missing or excessive jitter |
| PPS health | Kernel PPS RMS jitter | > kill threshold for grace period |
| External-reference evidence | SDR-readable clock state or validated wiring | Unknown/unverified reference path |
| RF coverage | LO range and filter response | Does not cover requirement |
| Calibration traceability | Calibration manifest with SHA-256 | Missing or mismatched calibration |
| Transport reliability | Sustained soak test | Transport errors / context loss |
| Cryptographic provenance | HMAC manifest + event chain + key management | Missing key or broken chain |
| Fault observability | Deterministic fault injection results | Faults not detected or not quarantined |

## Qualification States

- **PASS:** All mandatory dimensions satisfy the threshold.
- **FAIL:** One or more mandatory dimensions fail; primary output blocked.
- **UNVERIFIED:** A mandatory dimension cannot be proven by software; not a pass.
- **DEGRADED:** A dimension is within tolerance but not ideal; may continue if policy allows.
- **NOT_APPLICABLE:** Dimension does not apply to the configuration.

## Required YAML Conditions

```yaml
tier1_requirements:
  gps_fix_required: true
  pps_required: true
  pps_hardware_path_required: true
  external_frequency_reference_required: true
  external_reference_evidence_required: true
  calibration_manifest_required: true
  cryptographic_manifest_required: true
  production_hmac_key_required: true
  no_unaccounted_sample_loss: true
  primary_stream_fail_closed: true
  simulator_fallback_forbidden_in_field_mode: true
  firmware_fingerprint_required: true
  configuration_hash_required: true
```

## No Marketing Specifications

A datasheet claim does not qualify hardware. Only runtime-discovered
capabilities, captured evidence, repeatable tests, calibration records,
sustained transport tests, fault injection, and manifest verification count.
