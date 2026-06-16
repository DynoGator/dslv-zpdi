# HamGeek AD9363 PlutoSDR+ Timing Port Physical Verification Gate

**Status:** UNVERIFIED_PHYSICAL_PROPERTY — software cannot resolve these facts.

## Observed Evidence

The owner-supplied enclosure photographs show a HamGeek-branded device with:

- Two micro-coaxial connectors engraved `10M/PPS`
- RJ45 Ethernet
- USB-C OTG
- USB-C DEBUG
- microSD slot

These markings strongly suggest a dedicated 10 MHz reference input and a 1 PPS
input/output, but the engraving alone does not establish electrical
characteristics.

## Properties That Remain Unknown

The following must be physically verified before connecting the LBE-1421 GPSDO:

| Property | Status | Required Verification |
|----------|--------|----------------------|
| Connector family (U.FL / MMCX / MCX / MHF4 / other) | UNVERIFIED_PHYSICAL_PROPERTY | Visual inspection, datasheet, or caliper measurement |
| Which connector is 10 MHz vs PPS | UNVERIFIED_PHYSICAL_PROPERTY | PCB silkscreen, schematic, or manufacturer manual |
| Port direction (input vs output) | UNVERIFIED_PHYSICAL_PROPERTY | Schematic, multimeter continuity, oscilloscope |
| Nominal impedance | UNVERIFIED_PHYSICAL_PROPERTY | Datasheet or TDR/return-loss measurement |
| Maximum voltage / RF power | UNVERIFIED_PHYSICAL_PROPERTY | Datasheet absolute-maximum ratings table |
| DC coupling or AC coupling | UNVERIFIED_PHYSICAL_PROPERTY | Schematic or DC-block test |
| Required waveform (sine / CMOS / clipped sine / LVDS) | UNVERIFIED_PHYSICAL_PROPERTY | Datasheet or oscilloscope |
| PPS polarity and threshold | UNVERIFIED_PHYSICAL_PROPERTY | Datasheet or oscilloscope |
| PPS pulse width | UNVERIFIED_PHYSICAL_PROPERTY | Oscilloscope |
| Whether PPS reaches FPGA logic | UNVERIFIED_PHYSICAL_PROPERTY | Firmware/device-tree inspection, oscilloscope on test points |
| Whether 10 MHz replaces or disciplines the onboard reference | UNVERIFIED_PHYSICAL_PROPERTY | Schematic, firmware behavior under clock injection/removal |
| Whether clock presence is software-readable | UNVERIFIED_PHYSICAL_PROPERTY | `iio` attribute scan or device-tree inspection |

## Prohibited Actions

Do **not** connect the LBE-1421 outputs until:

1. Connector family is confirmed and adapters are correct.
2. Direction is confirmed as input for both ports.
3. Input impedance is matched to the timing cable.
4. Maximum input level is not exceeded.
5. Waveform type is compatible.

Do **not** use a passive tee to split PPS to the host and SDR without:

- Verifying output drive capability
- Calculating combined load impedance
- Checking edge degradation and reflections
- Using proper termination

## Recommended Verification Procedure

1. Obtain the manufacturer schematic or manual for the exact PCB revision.
2. Inspect the PCB silkscreen near the timing connectors for pin labels.
3. With the device unpowered, trace continuity from the timing connector to:
   - The AD936x XTALN pin or external-clock input pin
   - Any FPGA PPS input ball or GPIO expander
4. Power the device and measure each timing pin with a high-impedance probe
   before connecting the GPSDO.
5. If a 10 MHz input is confirmed, inject a low-level (e.g. 0 dBm) 10 MHz sine
   and observe whether the SDR reports clock lock or whether the onboard
   oscillator frequency shifts.
6. Document the exact PCB revision, connector family, and measured levels in
   this file and update the node profile `direction_verified` and
   `electrical_level_verified` fields.

## Wiring Diagram (Tentative)

```
LBE-1421 Out1 (1 PPS)  --[verified cable]-->  host GPIO 18 / /dev/pps0
LBE-1421 Out2 (10 MHz) --[verified cable]-->  HamGeek 10M timing input
                                               (only after verification)
```

The final wiring document must not identify the connector as U.FL, MMCX, MCX,
MHF4, or another family until physically confirmed.
