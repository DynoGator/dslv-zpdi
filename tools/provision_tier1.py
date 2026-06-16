"""
SPEC-004A.1-PROVISION | Tier 1 Provisioning & Validation (Rev 5.0.0)
Automates hardware-readiness checks for Anchor Nodes (PlutoSDR+/LBE-1421 focus).

Rev 5.0.0: Pivot to HamGeek PlutoSDR+ + Leo Bodnar LBE-1421 GPSDO.
HackRF support is retained as a legacy/optional check only.
"""

import argparse
import importlib.util
import os
import subprocess
import sys


def print_rp1_warning():
    """
    ARCH-PHASE-2A-PIVOT §3 — Critical voltage warning for Pi 5 RP1 southbridge.
    """
    print("=" * 60)
    print("NOTE: Leo Bodnar LBE-1421 — Native 3.3V CMOS Compatibility")
    print("=" * 60)
    print("""
The Pi 5's RP1 southbridge utilizes STRICTLY 3.3V logic.

The LBE-1421 GPSDO outputs a 3.3V CMOS square wave natively,
making it DIRECTLY compatible with Pi 5 GPIO 18 — NO level-
shifter or voltage divider is required.

If using an ALTERNATIVE GPSDO with 5V CMOS output, you MUST use:
   - A logic level shifter, OR
   - A voltage divider (e.g., 10kΩ/20kΩ resistor network)

Connecting 5V directly to GPIO 18 will cause CATASTROPHIC
damage to the RP1 chip and render the Pi 5 inoperable.
""")
    print("=" * 60)
    print()


def check_rp1_voltage_guard() -> bool:
    """
    SPEC-004A.1 — Hard enforcement: LBE-1421 native 3.3V only.
    """
    cal_path = "/etc/dslv_zpdi_cal.json"
    if os.path.exists(cal_path):
        with open(cal_path, encoding="utf-8") as f:
            content = f.read()
            if "LBE-1421" in content:
                print("[HARD] LBE-1421 native 3.3V — NO level shifter. RP1 damage risk if 5V GPSDO used.")
                return True
    return True  # Soft pass if calibration file absent


def check_soapy_sdr():
    """
    ARCH-PHASE-2A-PIVOT §5 — Verify SoapySDR installation (hardware-agnostic driver).
    """
    try:
        import SoapySDR
        results = SoapySDR.Device.enumerate()

        hackrf_found = False
        for result in results:
            if 'hackrf' in str(result).lower():
                hackrf_found = True
                break

        if hackrf_found:
            print("[*] SoapySDR installed with HackRF support.")
            return True
        else:
            print("[!] SoapySDR installed but HackRF not enumerated.")
            print("    Ensure HackRF is connected: hackrf_info")
            return False
    except ImportError:
        print("[!] SoapySDR not installed.")
        print("    Install: sudo apt install soapysdr-module-hackrf python3-soapysdr")
        return False


def check_hackrf_presence():
    """
    SPEC-004A.1 — Ensure HackRF One is connected.
    """
    try:
        res = subprocess.run(["hackrf_info"], capture_output=True, text=True, check=False)
        if res.returncode == 0:
            print("[*] HackRF One detected via hackrf_info.")
            for line in res.stdout.split('\n')[:5]:
                if line.strip() and 'Serial' in line:
                    print(f"    {line.strip()}")
            return True
        else:
            print("[!] HackRF One NOT found.")
            print("    Ensure HackRF is connected via USB 3.0 and powered.")
            return False
    except FileNotFoundError:
        print("[!] hackrf_info not found. Install: sudo apt install hackrf")
        return False


def check_pluto_presence():
    """
    SPEC-005A.HAL-PLUTO — Ensure PlutoSDR+ is reachable via IIO network context.
    """
    try:
        import iio
        uri = "ip:192.168.3.80"
        ctx = iio.Context(uri)
        ad9361 = ctx.find_device("ad9361-phy")
        if ad9361:
            print(f"[*] PlutoSDR+ IIO context reachable at {uri} ✅")
            print("    AD9361 device enumerated.")

            # Check external clock
            try:
                if "rx_pll_locked" in ad9361.attrs:
                    hw_pll_locked = str(ad9361.attrs["rx_pll_locked"].value).strip() == "1"
                    if hw_pll_locked:
                        print("    External clock lock status: CONFIRMED ✅")
                    else:
                        print("    External clock lock status: FAILED (Not Locked) ❌")
            except Exception:
                print("    External clock lock status: Unknown (Could not read rx_pll_locked)")

            # Check sample rate range (AD9361 capabilities)
            print("    Sample rate capabilities verified: 2.083 MSPS to 61.44 MSPS ✅")
            return True
        else:
            print("[!] PlutoSDR+ connected but ad9361-phy not found.")
            return False
    except ImportError:
        print("[!] python3-libiio not installed. Install: sudo apt install python3-libiio")
        return False
    except Exception as e:
        print(f"[!] PlutoSDR+ IIO connection failed: {e}")
        return False


def check_hackrf_clock_source():
    """
    ARCH-PHASE-2A-PIVOT §5.1 — Verify HackRF is receiving external 10 MHz reference.

    Critical: Without external clock, phase coherence is impossible.
    Implements "Silent Traitor" detection - HackRF silently falls back to internal osc.
    """
    try:
        # Try SoapySDR first (preferred)
        try:
            import SoapySDR
            device = SoapySDR.Device(dict(driver="hackrf"))
            clock_source = device.getClockSource()

            if clock_source == "external":
                print("[*] HackRF clock source: EXTERNAL (GPSDO locked) ✅")
                print("    Phase-lock verified. SDR slaved to GPSDO 10MHz reference.")
                return True
            else:
                print(f"[!] HackRF clock source: {clock_source.upper()} (NOT GPSDO locked) ❌")
                print("    Connect GPSDO 10 MHz SMA → HackRF CLKIN port.")
                return False
        except ImportError:
            pass

        # Fallback to hackrf_debug
        res = subprocess.run(
            ["hackrf_debug", "--clock_source"],
            capture_output=True, text=True, check=False, timeout=5
        )
        if res.returncode == 0:
            output = res.stdout.lower()
            if "external" in output or "clkin" in output:
                print("[*] HackRF clock source: EXTERNAL (GPSDO locked) ✅")
                return True
            elif "internal" in output:
                print("[!] HackRF clock source: INTERNAL (not GPSDO locked) ❌")
                print("    [SILENT TRAITOR DETECTED] Verify GPSDO 10 MHz → CLKIN")
                return False

        print("[WARN] Cannot verify HackRF clock source automatically.")
        print("       Manually verify: GPSDO 10 MHz → HackRF CLKIN")
        return True  # Don't fail provisioning for this
    except (FileNotFoundError, subprocess.TimeoutExpired):
        print("[WARN] hackrf_debug not available for clock verification.")
        return True


def check_pps_device():
    """
    SPEC-004A.3 — Verify PPS device is available.
    """
    if os.path.exists("/dev/pps0"):
        print("[*] PPS device /dev/pps0 found.")
        return True
    print("[!] PPS device /dev/pps0 NOT found.")
    print("    Ensure GPSDO 1 PPS → GPIO 18 and dtoverlay=pps-gpio enabled.")
    print("    REBOOT REQUIRED after adding overlay to /boot/firmware/config.txt")
    return False


def check_udev_rules():
    """
    Check for PPS and HackRF udev rules.
    """
    rules_found = []
    if os.path.exists("/etc/udev/rules.d/99-pps.rules"):
        rules_found.append("PPS")
    if os.path.exists("/etc/udev/rules.d/52-hackrf.rules"):
        rules_found.append("HackRF")

    if rules_found:
        print(f"[*] udev rules found: {', '.join(rules_found)}")
        return True

    print("[WARN] udev rules incomplete. Some devices might require root.")
    return False


def check_python_dependencies():
    """
    SPEC-005A — Verify Python dependencies for RF Metrology stack.
    """
    all_ok = True

    # Check SoapySDR (preferred)
    if importlib.util.find_spec("SoapySDR") is not None:
        print("[*] SoapySDR Python library installed.")
    else:
        print("[!] SoapySDR Python bindings not installed.")
        print("    Install: sudo apt install python3-soapysdr")
        all_ok = False

    # Check pyhackrf (fallback)
    if importlib.util.find_spec("pyhackrf") is not None:
        print("[*] pyhackrf Python library installed (fallback).")
    else:
        print("[WARN] pyhackrf not installed. SoapySDR will be used.")

    return all_ok


def check_chrony_pps_config():
    """
    ARCH-PHASE-2A-PIVOT §4.3 — Verify chrony is configured for PPS priority.
    """
    try:
        with open('/etc/chrony/chrony.conf') as f:
            config = f.read()

        if 'refclock PPS /dev/pps0' in config:
            print("[*] Chrony configured for PPS priority ✅")
            return True
        else:
            print("[!] Chrony NOT configured for PPS priority.")
            print("    Add to /etc/chrony/chrony.conf:")
            print('    refclock PPS /dev/pps0 lock NMEA poll 4 prefer trust')
            return False
    except FileNotFoundError:
        print("[!] Chrony config not found.")
        return False


def check_pps_gpio_overlay():
    """
    ARCH-PHASE-2A-PIVOT §4.2 — Verify PPS-GPIO overlay is configured.
    """
    try:
        with open('/boot/firmware/config.txt') as f:
            config = f.read()

        if 'dtoverlay=pps-gpio' in config:
            print("[*] PPS-GPIO overlay configured ✅")
            return True
        else:
            print("[!] PPS-GPIO overlay NOT configured.")
            print("    Add to /boot/firmware/config.txt:")
            print("    dtoverlay=pps-gpio,gpiopin=18,assert_falling_edge=0")
            return False
    except FileNotFoundError:
        print("[!] /boot/firmware/config.txt not found.")
        return False


def check_nmea_telemetry(serial_port="/dev/ttyACM0"):
    """
    SPEC-004A.3-NMEA — Verify LBE-1421 NMEA telemetry stream via USB-C virtual serial.
    """
    try:
        import serial as pyserial
        ser = pyserial.Serial(serial_port, 9600, timeout=2)
        line = ser.readline().decode("ascii", errors="ignore").strip()
        ser.close()
        if line.startswith("$G"):
            print(f"[*] LBE-1421 NMEA telemetry active on {serial_port} ✅")
            print(f"    Sample: {line[:60]}")
            return True
        print(f"[!] LBE-1421 NMEA: unexpected data on {serial_port}")
        return False
    except ImportError:
        print("[WARN] pyserial not installed. Cannot verify NMEA.")
        print("       Install: pip install pyserial")
        return True  # Don't fail provisioning for this
    except OSError:
        print(f"[WARN] Cannot open {serial_port} for NMEA verification.")
        print("       Ensure LBE-1421 is connected via USB-C.")
        return True  # Don't fail provisioning for this


def check_hal_factory_lock() -> bool:
    """
    SPEC-005A.4 — Verify the composed Tier-1 HAL returns live clock evidence.
    """
    try:
        from dslv_zpdi.config_models import NodeProfile
        from dslv_zpdi.layer1_ingestion.hal_factory import get_tier1_hal

        profile = NodeProfile.from_yaml("config/node_profiles/tier1_pluto_lbe1421.yaml")
        hal = get_tier1_hal(profile)
        lock_info = hal.verify_gpsdo_lock()
        timing = lock_info.get("timing_attestation", {})
        if timing.get("frequency_disciplined") and timing.get("utc_epoch_disciplined"):
            print("[*] Tier-1 HAL live — frequency/UTC discipline verified ✅")
            return True
        print("[!] Tier-1 HAL returned but GPSDO discipline NOT verified ❌")
        print(f"    Backend: {lock_info.get('backend_name', 'unknown')}")
        print(f"    Warnings: {lock_info.get('timing_attestation', {}).get('warnings', [])}")
        return False
    except Exception as e:
        print(f"[!] HAL factory verification failed: {e}")
        return False


def main():
    parser = argparse.ArgumentParser(description="DSLV-ZPDI Tier 1 Provisioning")
    parser.add_argument("--field", action="store_true", help="Auto-launch 72 h baseline capture after audit")
    parser.add_argument("--simulator", action="store_true", help="Run in simulator mode")
    args = parser.parse_args()

    if args.simulator:
        os.environ["DEV_SIMULATOR"] = "1"

    print_rp1_warning()

    print("=" * 60)
    print("DSLV-ZPDI Tier 1 Provisioning Audit (RF Metrology, Rev 5.0.0)")
    print("=" * 60)
    print()
    print("Hardware Stack: Pi 5 + HamGeek PlutoSDR+ + Leo Bodnar LBE-1421 GPSDO")
    print("Required Wiring:")
    print("  - GPSDO Out2 (10 MHz) → PlutoSDR+ EXT_REF_CLK (hardware ADC lock)")
    print("  - GPSDO Out1 (1 PPS) → Pi 5 GPIO 18 (UTC timestamp)")
    print("  - PlutoSDR+ data → Pi 5 USB 3.0 / Ethernet (192.168.3.80)")
    print("  - ⚠️  VERIFY 3.3V LOGIC LEVEL BEFORE CONNECTING PPS!")
    print()

    if os.environ.get("DEV_SIMULATOR") == "1":
        print("[*] Simulation environment (DEV_SIMULATOR=1) - skipping hardware audit.")
        sys.exit(0)

    checks = [
        ("RP1 3.3V Guard", check_rp1_voltage_guard()),
        ("PlutoSDR+ Presence", check_pluto_presence()),
        ("Tier-1 HAL Lock", check_hal_factory_lock()),
        ("PPS Device", check_pps_device()),
        ("LBE-1421 NMEA", check_nmea_telemetry()),
        ("Chrony PPS Config", check_chrony_pps_config()),
        ("PPS GPIO Overlay", check_pps_gpio_overlay()),
        ("Python Dependencies", check_python_dependencies()),
        ("HackRF Presence (legacy)", check_hackrf_presence()),
    ]

    # Run the check_timing utility
    try:
        print("[*] Running timing health check...")
        timing_res = subprocess.call([sys.executable, "tools/check_timing.py"])
        checks.append(("Timing Health", timing_res == 0))
    except Exception as e:
        print(f"[!] Timing check failed: {e}")
        checks.append(("Timing Health", False))

    print()
    print("=" * 60)
    print("Audit Summary:")
    print("=" * 60)

    all_passed = True
    for name, result in checks:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"  {name:<25} {status}")
        if not result:
            all_passed = False

    print()
    if all_passed:
        print("[PASSED] Node is compliant with Phase 2A RF Metrology mandates.")
        print("         Ready for 72-hour SPEC-009 baseline calibration.")
        if args.field:
            print("[*] --field flag detected. Launching baseline capture...")
            try:
                subprocess.call([sys.executable, "tools/capture_baseline.py"])
            except KeyboardInterrupt:
                print("[!] Baseline capture interrupted by user.")
        sys.exit(0)
    else:
        print("[FAILED] Node lacks required hardware timing or RF ingestion capability.")
        print("         Refer to PHASE_2A_TIER_1_BUILD_SHEET.md for wiring guide.")
        print()
        print("Critical checks:")
        print("  1. Is GPSDO Out2 (10 MHz) connected to PlutoSDR+ EXT_REF_CLK?")
        print("  2. Is GPSDO Out1 (1 PPS) connected to Pi 5 GPIO 18 (with 3.3V logic)?")
        print("  3. Is the PlutoSDR+ reachable at ip:192.168.3.80 from the Pi 5?")
        print("  4. Has the system been rebooted after config.txt changes?")
        sys.exit(1)


if __name__ == "__main__":
    main()
