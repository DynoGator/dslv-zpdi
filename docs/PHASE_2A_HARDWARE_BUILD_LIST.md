# PHASE 2A HARDWARE BUILD LIST

## Procurement Configurations & Hardware Components

1. **RF Phase Lock (ADC Slave):** Connect SMA cable from LBE-1421 `Out2` port (set to 10 MHz) directly to HackRF One `CLKIN` port (50 Ω). This phase-locks the SDR's ADC to the GPS constellation.
2. **OS Timestamping (Heartbeat):** Run jumper wire from LBE-1421 `Out1` port (set to 1 PPS mode) to Pi 5 GPIO Pin 18 (Physical Pin 12). Bridge ground between GPSDO and Pi. *Note: LBE-1421 outputs 100 ms 3.3V CMOS natively — no level-shifter required.*

## Build Sheet Instructions

**Step 4.** **RF Phase Lock (ADC Slave):** Connect SMA Male-to-Male cable (50 Ohm, ≤ 1FT) from the LBE-1421 `Out2` port (set to 10 MHz) to the HackRF One `CLKIN` port (50 Ω).
