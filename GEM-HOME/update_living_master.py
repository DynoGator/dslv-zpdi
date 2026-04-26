
import os
path = '../V3_DSLV-ZPDI_LIVING_MASTER.md'
with open(path, 'r') as f:
    content = f.read()

lbe_section = """
### SPEC-004A.4 — Leo Bodnar LBE-1421 GPSDO (Clock Authority)

**SYSTEM FUNCTION:** Provide the primary 10 MHz reference and 1 PPS epoch anchor for the SIGINT network.
**OPERATIONAL INTENT:** The LBE-1421 replaces the deprecated LBE-1420 to provide simultaneous high-frequency reference and physical PPS.

**Datasheet Verbatim Specifications:**
- **Dual Outputs:** 
  - `Out1`: 1 Hz – 800 MHz or 1 PPS mode.
  - `Out2`: 1 Hz – 1.4 GHz.
- **Stability:** 1 × 10⁻¹² @ 1000 s.
- **Output Level:** 3.3 V CMOS (native), 1.65 V into 50 Ω.
- **Pulse Width (PPS):** 100 ms.
- **Power:** 250 mA ±10 % @ 5 V USB-C + 30 mA antenna port.
- **Frequency/Phase Stability:** "No frequency/phase jumps on GPS loss."
- **Holdover:** TCXO high-Q oscillator ensures stability during transient GPS loss.
- **Telemetry:** NMEA virtual serial output for lock status, satellite count, and DOP.

**KILL CONDITION:** Any Tier 1 node utilizing a single-output GPSDO (e.g., LBE-1420) that cannot provide simultaneous 10 MHz + 1 PPS.
"""

if '### SPEC-004A.4' not in content:
    content = content.replace('### SPEC-004A.3', lbe_section + '\n### SPEC-004A.3')
    with open(path, 'w') as f:
        f.write(content)
    print('Added SPEC-004A.4 to V3_DSLV-ZPDI_LIVING_MASTER.md')
