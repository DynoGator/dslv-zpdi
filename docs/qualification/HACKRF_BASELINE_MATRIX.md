# HackRF One Baseline Matrix

## Role

The HackRF One is the historical minimum Tier-1 performance floor ("poverty
line"). It is no longer the canonical Tier-1 target.

## Measured / Observed Baseline

| Dimension | Baseline Value | Evidence |
|-----------|---------------|----------|
| ADC amplitude resolution | 8-bit | Device datasheet |
| Typical usable bandwidth | 20 MHz | SoapySDR/HackRF driver |
| RF coverage | 1 MHz – 6 GHz | Device datasheet |
| External clock input | CLKIN, 10 MHz | Hardware design |
| PPS hardware timestamp | Not available | Architecture limitation |
| Sample accounting | Buffer-level | Driver-dependent |

## Notes

HackRF-specific code lives in the optional `[hackrf]` dependency group and the
legacy backend path. It remains available for regression tests and Tier-2
nodes.
