# PlutoSDR+ Acceptance Matrix

## Candidate

- Enclosure: HamGeek-branded AD9363 Pluto-family SDR
- Transceiver: AD9363 (claimed, pending verification)
- Interfaces: RJ45, USB-C OTG, USB-C DEBUG, microSD
- Timing ports: two micro-coaxial connectors engraved `10M/PPS`

## Acceptance Status

| Dimension | Status | Evidence |
|-----------|--------|----------|
| SDR discovered via libiio | PROVISIONAL | `dslv-zpdi-probe` when hardware connected |
| Exact PCB revision | UNVERIFIED | Owner-supplied photos only |
| Timing connector family | UNVERIFIED | Owner-supplied photos only |
| 10 MHz direction | UNVERIFIED | Requires physical verification |
| PPS direction | UNVERIFIED | Requires physical verification |
| Electrical level | UNVERIFIED | Requires oscilloscope / power meter |
| External reference consumed | UNVERIFIED | Requires clock injection test |
| PPS healthy | UNVERIFIED | Requires LBE-1421 connection |
| Sample epoch synchronized | UNVERIFIED | Requires FPGA/fabric test |
| Sustained capture | PROVISIONAL | `dslv-zpdi-soak-test` when hardware connected |
| HDF5 verification | PASS | Simulator validation |
| Tier-1 qualification | PROVISIONAL_TIER1_PENDING_HARDWARE_QUALIFICATION | |

## Required Owner Actions

1. Verify timing-port electrical characteristics.
2. Connect LBE-1421 and run `dslv-zpdi-preflight --strict`.
3. Run 10-minute qualification with `dslv-zpdi-qualify`.
4. Run 1-hour soak test with `dslv-zpdi-soak-test --duration 1h`.
5. Submit generated evidence for final qualification review.
