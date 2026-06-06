# SPEC-021 — Dashboard Phase 2B Panel Extensions

**Status:** ACTIVE
**Layer:** Operator-Facing TUI

## Overview

Extended the existing Rich-based Live TUI dashboard with three new panels while preserving the glitch/plasma terminal aesthetic, snarky NOTE puns, and all existing panels.

## New Panels

### RADON (`tools/dashboard/panels/radon.py`)
**SPEC-021.1** — Live pCi/L, transport (BLE/HTTP/SIM), device serial tail, sample age, and quality. Color-coded: green for good quality, yellow for suspect, red for poor.

### MOBILE / Tier 2 (`tools/dashboard/panels/mobile.py`)
**SPEC-021.2** — Pixel link status, magnetometer magnitude, GPS fix accuracy, last camera-frame hash tail, trust score. Color-coded trust score.

### BCI / Validation (`tools/dashboard/panels/bci.py`)
**SPEC-021.3** — Current χ, pilot-threshold state, review-flag status. Red when flagged, green when clear, yellow when approaching threshold.

## Layout Integration

- **Compact mode:** New panels join `status_row_b` alongside anomaly, weather, and storm.
- **Wide mode:** New panels join the `space` row alongside weather and storm.
- All panels are optional and controlled by `dashboard.toml` `[dashboard.panels]` flags (`radon`, `mobile`, `bci`).

## New Humor Lines

Added to `tools/dashboard/humor.py`:
- "SNIFFING NOBLE GASES — POLITELY"
- "DARCY'S LAW IS PUMPING"
- "RD200P WHISPERING OVER BLE"
- "WAITING FOR RADON TO MAKE A MOVE (IT'S SHY)"
- "BAROMETRIC PRESSURE IS THE REAL MAIN CHARACTER"
- "CALCULATING DARCY PUMP STRENGTH WITH FEELINGS"
- "RADON-222: RELIABLE, RADIOACTIVE, AND RUDE ABOUT IT"
- "PLOT TWIST: THE BASEMENT IS THE ANOMALY"
- "NOBLE GAS DETECTED — OFFERING IT TEA"
- "ALPHA DECAY IS JUST MICROSCOPE AGGRESSION"
- "Bq/m³ OR BREATHE-CUBED? YOU DECIDE"

## Kill Conditions
- Regressing existing SYS / PIPE / HW / ANOM / WX / STORM / WF / LOG / NOTE panels → rejected
- Removing or altering existing humor lines → rejected
- Changing the color palette or terminal aesthetic → rejected
