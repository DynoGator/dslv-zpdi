# LBE-1421 to PlutoSDR+ Wiring

**Status:** PROVISIONAL — pending physical timing-port verification.

## Initial Canonical Routing

Until the SDR PPS input is verified and FPGA timestamp support proven:

- LBE-1421 frequency output → HamGeek AD9363 `10M` timing input
- LBE-1421 PPS output → host hardware PPS input (`/dev/pps0`)

## Verification Gates

See `docs/hardware/HAMGEEK_AD9363_TIMING_PORT_VERIFICATION.md`.

Do not connect the GPSDO until:

- Connector family is confirmed.
- Port direction is confirmed as input.
- Impedance and level are compatible.
- A buffered distribution solution is used if PPS must feed multiple devices.

## Prohibited Assumptions

- Do not assume the timing connectors are U.FL, MMCX, MCX, or MHF4.
- Do not assume 10 MHz vs PPS ordering from the engraving alone.
- Do not use a passive tee without load analysis.
