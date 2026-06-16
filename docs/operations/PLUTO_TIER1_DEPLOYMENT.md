# PlutoSDR+ Tier-1 Deployment Guide

## Prerequisites

- Debian 13 Trixie host
- LBE-1421 GPSDO
- HamGeek AD9363 PlutoSDR+ class device
- Physical timing-port verification completed (see
  `docs/hardware/HAMGEEK_AD9363_TIMING_PORT_VERIFICATION.md`)

## Installation

```bash
sudo ./install_dslv_zpdi.sh --tier1-pluto
```

For simulator-only validation:

```bash
sudo ./install_dslv_zpdi.sh --simulator
```

## Discovery

```bash
dslv-zpdi-probe --discover
dslv-zpdi-probe --uri ip:<address> --json output/pluto_probe.json
```

## Preflight

```bash
dslv-zpdi-preflight \
  --profile config/node_profiles/tier1_pluto_lbe1421.yaml \
  --strict \
  --json output/preflight.json
```

Do not proceed to capture unless every mandatory check is PASS.

## Capture

```bash
DSLV_SDR_URI=ip:<address> dslv-zpdi-pipeline \
  --profile config/node_profiles/tier1_pluto_lbe1421.yaml
```

## Verification

```bash
dslv-zpdi-verify output/primary/*.h5 --deep
```

## Key Provisioning

```bash
sudo mkdir -p /etc/dslv-zpdi
sudo install -m 0600 /dev/stdin /etc/dslv-zpdi/hmac.key <<< "$(openssl rand -hex 32)"
```

## Soak Tests

```bash
dslv-zpdi-soak-test --duration 10m
```

Long-duration tests must be run by the operator; do not fabricate results.
