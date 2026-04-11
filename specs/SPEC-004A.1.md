# SPEC-004A.1

Status: COMPLETED
Description: GPSDO METROLOGY CLOCK REQUIREMENT (Rev 4.1-PIVOT)
Implementation: RF Metrology hardware stack - Raspberry Pi 5 + HackRF One + Leo Bodnar Mini GPSDO
Rationale: Achieve hardware-level ADC phase coherence by locking the SDR sampling clock directly to the GPS constellation via an external GPSDO, eliminating USB bus jitter and network timing intermediaries.

## Hardware Stack
- **Compute:** Raspberry Pi 5 (16GB) or compatible
- **SDR:** HackRF One with CLKIN port for 10 MHz reference
- **Clock Authority:** Leo Bodnar Mini GPSDO (10 MHz + 1 PPS)

## Physical Connections
1. GPSDO 10 MHz SMA Output → HackRF CLKIN (hardware ADC phase-lock)
2. GPSDO 1 PPS → Pi 5 GPIO 18 (pps-gpio kernel module)

## Software Implementation
- HAL: `hal_hardware.py` - HackRF One support with pyhackrf
- Verification: `verify_gpsdo_lock()` - Checks external clock detection
- PPS: `/dev/pps0` via pps-gpio, read via kernel ioctl

## Kill Conditions
- GPS lock loss > 60 seconds
- PPS jitter > 10 µs RMS
- HackRF clock source != "external" (GPSDO not connected)
- Calibration drift > 20%

## Deprecation Notice
Rev 4.1 formally deprecates the CM5 + Intel i210-T1 PTP-based timing approach.
RTL-SDR is relegated to Tier 2 / Testbed role only.
