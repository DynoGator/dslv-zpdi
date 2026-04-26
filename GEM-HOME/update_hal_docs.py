
import os

path = '../src/dslv_zpdi/layer1_ingestion/hal_hardware.py'
with open(path, 'r') as f:
    content = f.read()

old_doc = """    Hardware Requirements (SPEC-004A.1, SPEC-004A.2):
    - Raspberry Pi 5 (16GB) or compatible compute platform
    - HackRF One with CLKIN port for 10 MHz GPSDO reference
    - Leo Bodnar LBE-1421 GPSDO (10 MHz + 1 PPS output)
    - GPSDO 10 MHz SMA \u2192 HackRF CLKIN (hardware ADC phase-lock)
    - GPSDO 1 PPS \u2192 Pi 5 GPIO 18 (UTC timestamp interrupt)

    CRITICAL WARNING (RP1 Southbridge):
    The Pi 5's RP1 southbridge uses strictly 3.3V logic. Verify GPSDO output
    voltage with a multimeter before connection. If output exceeds 3.3V,
    use a logic level shifter to prevent catastrophic RP1 damage."""

new_doc = """    Hardware Requirements (SPEC-004A.1, SPEC-004A.2, SPEC-004A.4):
    - Raspberry Pi 5 (16GB) or compatible compute platform
    - HackRF One with CLKIN port for 10 MHz GPSDO reference
    - Leo Bodnar LBE-1421 GPSDO (Out2=10 MHz reference, Out1=1 PPS)
    - GPSDO Out2 (10 MHz) \u2192 HackRF CLKIN (hardware ADC phase-lock, 50 \u03a9)
    - GPSDO Out1 (1 PPS) \u2192 Pi 5 GPIO 18 (UTC timestamp interrupt)
    - Power Budget: 250 mA \u00b110 % @ 5 V USB-C + 30 mA antenna port (active)
    - Stability: 1 \u00d7 10\u207b\u00b9\u00b2 @ 1000 s (no frequency/phase jumps on GPS loss)

    CRITICAL WARNING (RP1 Southbridge):
    The Pi 5's RP1 southbridge uses strictly 3.3V logic. LBE-1421 provides native
    3.3V CMOS (1.65V into 50 \u03a9), making it safe for direct connection. 
    Pulse width is 100 ms; use `assert_falling_edge=0` in dtoverlay."""

content = content.replace(old_doc, new_doc)

with open(path, 'w') as f:
    f.write(content)
print('Updated HardwareHAL docstrings')
