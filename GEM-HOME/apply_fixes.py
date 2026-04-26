
import os
import re

def replace_in_file(file_path, old_text, new_text):
    if not os.path.exists(file_path):
        print(f"File not found: {file_path}")
        return
    with open(file_path, 'r') as f:
        content = f.read()
    if old_text in content:
        new_content = content.replace(old_text, new_text)
        with open(file_path, 'w') as f:
            f.write(new_content)
        print(f"Updated {file_path}")
    else:
        print(f"Pattern not found in {file_path}")

# 1. Update MASTER_SPEC.md timing wiring
replace_in_file('../MASTER_SPEC.md', 
    '- **Timing Wiring (Rev 4.1):** 10 MHz SMA out from GPSDO \u2192 HackRF One `CLKIN` port (hardware ADC lock). 1 PPS out from GPSDO \u2192 Raspberry Pi 5 GPIO 18 via `pps-gpio` kernel module + `chronyd`. This eliminates all USB bus jitter from the phase measurement chain. The ADC sampling clock is derived directly from the GPS constellation \u2014 no software intermediaries.',
    '- **Timing Wiring (Rev 4.1):** 10 MHz reference signal from LBE-1421 `Out2` port (set to 10,000,000 Hz) \u2192 HackRF One `CLKIN` port (hardware ADC lock, 50 \u03a9 termination recommended). 1 PPS signal from LBE-1421 `Out1` port (set to 1 PPS mode) \u2192 Raspberry Pi 5 GPIO 18 (Physical Pin 12) via `pps-gpio` kernel module. LBE-1421 provides a native 100 ms 3.3 V CMOS pulse (1.65 V into 50 \u03a9) which is perfectly matched to Pi 5 logic levels without level-shifters. This configuration eliminates all USB bus jitter from the phase measurement chain; the ADC sampling clock is derived directly from the GPS constellation with no software intermediaries.'
)

# 2. Update V3_DSLV-ZPDI_LIVING_MASTER.md timing wiring (same as above)
replace_in_file('../V3_DSLV-ZPDI_LIVING_MASTER.md', 
    '- **Timing Wiring (Rev 4.1):** 10 MHz SMA out from GPSDO \u2192 HackRF One `CLKIN` port (hardware ADC lock). 1 PPS out from GPSDO \u2192 Raspberry Pi 5 GPIO 18 via `pps-gpio` kernel module + `chronyd`. This eliminates all USB bus jitter from the phase measurement chain. The ADC sampling clock is derived directly from the GPS constellation \u2014 no software intermediaries.',
    '- **Timing Wiring (Rev 4.1):** 10 MHz reference signal from LBE-1421 `Out2` port (set to 10,000,000 Hz) \u2192 HackRF One `CLKIN` port (hardware ADC lock, 50 \u03a9 termination recommended). 1 PPS signal from LBE-1421 `Out1` port (set to 1 PPS mode) \u2192 Raspberry Pi 5 GPIO 18 (Physical Pin 12) via `pps-gpio` kernel module. LBE-1421 provides a native 100 ms 3.3 V CMOS pulse (1.65 V into 50 \u03a9) which is perfectly matched to Pi 5 logic levels without level-shifters. This configuration eliminates all USB bus jitter from the phase measurement chain; the ADC sampling clock is derived directly from the GPS constellation with no software intermediaries.'
)

# 3. Update build list instructions
replace_in_file('../PHASE_2A_HARDWARE_BUILD_LIST.md',
    '1. **RF Phase Lock (ADC Slave):** Connect SMA cable from LBE-1421 `Output` port directly to HackRF One `CLKIN` port. This phase-locks the SDR\'s ADC to the GPS constellation.',
    '1. **RF Phase Lock (ADC Slave):** Connect SMA cable from LBE-1421 `Out2` port (set to 10 MHz) directly to HackRF One `CLKIN` port (50 \u03a9). This phase-locks the SDR\'s ADC to the GPS constellation.'
)
replace_in_file('../PHASE_2A_HARDWARE_BUILD_LIST.md',
    '2. **OS Timestamping (Heartbeat):** Run jumper wire from LBE-1421 `1 PPS` output to Pi 5 GPIO Pin 18 (Physical Pin 12). Bridge ground between GPSDO and Pi. *Note: LBE-1421 outputs 3.3V CMOS natively \u2014 no level-shifter required.*',
    '2. **OS Timestamping (Heartbeat):** Run jumper wire from LBE-1421 `Out1` port (set to 1 PPS mode) to Pi 5 GPIO Pin 18 (Physical Pin 12). Bridge ground between GPSDO and Pi. *Note: LBE-1421 outputs 100 ms 3.3V CMOS natively \u2014 no level-shifter required.*'
)

# 4. Update build sheet instructions
replace_in_file('../PHASE_2A_TIER_1_BUILD_SHEET.md',
    '**Step 4.** **RF Phase Lock (ADC Slave):** Connect SMA Male-to-Male cable (50 Ohm, \u2264 1FT) from the LBE-1421 `Output` port to the HackRF One `CLKIN` port.',
    '**Step 4.** **RF Phase Lock (ADC Slave):** Connect SMA Male-to-Male cable (50 Ohm, \u2264 1FT) from the LBE-1421 `Out2` port (set to 10 MHz) to the HackRF One `CLKIN` port (50 \u03a9).'
)
replace_in_file('../PHASE_2A_TIER_1_BUILD_SHEET.md',
    '**Step 5.** **OS Timestamping (Heartbeat):** Run jumper wire from the LBE-1421 `1 PPS` output to Pi 5 **GPIO Pin 18** (Physical Pin 12). Run a second jumper to bridge the ground paths between the GPSDO and the Pi. *Note: LBE-1421 outputs 3.3V CMOS natively \u2014 no level-shifter required for Pi 5 RP1 chip.*',
    '**Step 5.** **OS Timestamping (Heartbeat):** Run jumper wire from the LBE-1421 `Out1` port (set to 1 PPS mode) to Pi 5 **GPIO Pin 18** (Physical Pin 12). Run a second jumper to bridge the ground paths between the GPSDO and the Pi. *Note: LBE-1421 outputs 100 ms 3.3V CMOS natively \u2014 no level-shifter required for Pi 5 RP1 chip.*'
)
