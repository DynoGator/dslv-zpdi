# Upconverter / Downconverter Integration

## Principle

The production default is receive-only with TX hard-locked out.

## Frequency Mapping

```
rf_frequency_hz = lo_frequency_hz + sideband_sign * if_frequency_hz
```

- `sideband_sign = +1`: upper sideband, no inversion
- `sideband_sign = -1`: lower sideband, spectral inversion present

## Preservation of Raw Evidence

Raw IQ samples remain at the native IF. Translated RF metadata is stored
alongside native metadata, never replacing it.

## Calibration

Converter calibration manifests must include:

- Schema version
- Device serial
- Operator ID
- Timestamp
- Calibration method and source instrument
- Frequency response table
- SHA-256

A missing or mismatched calibration manifest quarantines converted data from
the primary stream.
