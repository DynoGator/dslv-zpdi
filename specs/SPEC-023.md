# SPEC-023 — Demodulation Engine and MIMO Vectoring Integration Hooks

**Status:** ACTIVE (integration hooks; DSP internals staged for future work)
**Layer:** Layer 1 — Ingestion

## Overview

Rev 5.2.0 introduces two Layer-1 capability modules that expose demodulation
and Full Duplex MIMO vectoring as composable integration hooks. In this
revision both modules are deliberately stub-level: they define the canonical
interfaces, presets, and state handling so that dashboards, pipelines, and
tests can wire against them now, while the physical DSP internals land in a
future revision.

## SPEC-023.1 — Demodulation Engine (`layer1_ingestion/demodulation.py`)

- `DemodulationPreset` — immutable-style value holder for a demodulation
  preset: name, category (`audio`, `data`, `video`, `telemetry`), sample
  rate, bandwidth, and mode-specific parameters.
- `Demodulator` — preset registry and mode selector covering AM, NFM, WFM,
  LSB, USB, CW, AFSK1200 (APRS), BPSK31, AM-video (ATV), and QAM16 telemetry.
  `set_mode()` fails closed on unknown modes (`ValueError`). `process()`
  returns `{"status": "inactive"}` until a mode is selected; when active it
  currently returns a zeroed output buffer plus preset metadata as a stand-in
  for the future DSP chain.

## SPEC-023.2 — Full Duplex MIMO Vectoring (`layer1_ingestion/mimo_vectoring.py`)

- `MimoVectoringEngine` — holds TX/RX channel counts and a complex vectoring
  matrix (identity by default). Full-duplex behavior is opt-in via
  `enable_full_duplex()`; when disabled, `apply_tx_vectoring()` and
  `apply_rx_vectoring()` pass streams through unchanged (fail-safe default).
  `update_vectoring_matrix()` rejects shape mismatches with `ValueError`.

## Non-Goals (this revision)

- No physical demodulation DSP (filtering, discrimination, sync detection).
- No actual spatial multiplexing / interference-cancellation math.
- No changes to Layer-1/2/3 metrology semantics; both modules are additive
  and inert unless explicitly enabled.
