# SPEC-004A — Capability-Based Hardware and Node Profiles

## 1. Purpose

This specification defines the YAML profile format and Python models used to
configure Tier-1 RF metrology nodes independently of any specific SDR vendor.
A node profile describes the hardware identity, SDR backend, timing authority,
RF observation parameters, optional frequency-converter stage, and trust policy.

## 2. Scope

- Device-specific hardware profiles (PlutoSDR+, HackRF legacy, future SDRs)
- Timing authority profiles (LBE-1421 and successors)
- Frequency-converter profiles (direct RF and external translators)
- Combined node profiles
- Safe environment-variable expansion

## 3. Profile Schema

```yaml
schema_version: "1"
identity:
  profile_id: <string>
  enclosure_brand_observed: <string>
  enclosure_model_marking_observed: <string>
  exact_pcb_revision: <string|null>
  qualification_status: <string>
hardware:
  reference_clock:
    required: <bool>
    source: <string>
    requested_hz: <int>
    connector_label_observed: <string>
    connector_type: <string|null>
    direction_verified: <bool>
    input_impedance_ohms: <int|null>
    maximum_input_dbm: <float|null>
    electrical_level_verified: <bool>
  pps:
    required: <bool>
    canonical_host_path: <string>
    sdr_pps_support: <string>
sdr:
  backend: <simulated|pluto_iio|hackrf_legacy|auto>
  uri: <string>
  expected_iio_phy: <string>
  receive_channels: [<int>]
  transmit_enabled: <bool>
  sample_rate_hz: <int>
  rf_bandwidth_hz: <int>
  buffer_samples: <int>
  gain_mode: <string>
  gain_db: <float>
timing:
  authority: <string>
  pps_device: <string>
  nmea_port: <string>
  reference_frequency_hz: <int>
  pps_degraded_ns: <float>
  pps_kill_ns: <float>
  max_fix_age_s: <float>
rf:
  center_frequency_hz: <int>
  sample_rate_hz: <int>
  rf_bandwidth_hz: <int>
  gain_db: <float>
  gain_mode: <string>
converter:  # optional
  model: <string>
  serial: <string>
  native_if_center_hz: <int>
  lo_frequency_hz: <int>
  lo_source: <string>
  sideband_sign: <1|-1>
  gain_db: <float>
  loss_db: <float>
  filter_low_hz: <int|null>
  filter_high_hz: <int|null>
  calibration_manifest_sha256: <string>
trust:
  fail_closed: <bool>
  allow_simulator_fallback: <bool>
  require_firmware_fingerprint: <bool>
  require_calibration_manifest: <bool>
  require_production_hmac_key: <bool>
```

## 4. Environment-Variable Expansion

Only the syntax `${VAR:-default}` is supported. Arbitrary shell expansion,
command substitution, and pattern substitution are rejected.

## 5. Trust Behavior

- `fail_closed=true`: Any mandatory qualification failure blocks primary output.
- `allow_simulator_fallback=false`: Missing hardware must not silently simulate.
- `require_production_hmac_key=true`: Missing key blocks primary output.

## 6. References

- `src/dslv_zpdi/config_models.py`
- `config/node_profiles/`
- `src/dslv_zpdi/layer1_ingestion/hal_factory.py`
