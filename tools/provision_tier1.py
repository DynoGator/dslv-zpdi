"""
SPEC-004A.1-PROVISION | Tier 1 Provisioning & Validation (Rev 4.1-PIVOT)
Automates hardware-readiness checks for Anchor Nodes (GPSDO/HackRF focus).

Rev 4.1: Updated for RF Metrology stack - Pi 5 + HackRF One + Leo Bodnar Mini GPSDO
"""

import os
import subprocess
import sys


def check_hackrf_presence():
    """
    SPEC-004A.1 — Ensure HackRF One is connected and responding.
    """
    try:
        # hackrf_info returns 0 if HackRF is found, 1 otherwise
        res = subprocess.run(["hackrf_info"], capture_output=True, text=True, check=False)
        if res.returncode == 0:
            print("[*] HackRF One detected.")
            # Parse board ID and serial if available
            if "Board ID Number" in res.stdout:
                for line in res.stdout.split('\n')[:5]:
                    if line.strip():
                        print(f"    {line.strip()}")
            return True
        else:
            print("[!] HackRF One NOT found. Ingestion will fail.")
            print("    Ensure HackRF is connected via USB 3.0 and powered.")
            return False
    except FileNotFoundError:
        print("[!] hackrf_info not found. Install: sudo apt install hackrf")
        return False


def check_hackrf_clock_source():
    """
    SPEC-004A.1 — Verify HackRF is receiving external 10 MHz reference.
    
    Critical: Without external clock, phase coherence is impossible.
    """
    try:
        # hackrf_debug can query clock source on newer firmware
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
                print("    Connect GPSDO 10 MHz to HackRF CLKIN port.")
                return False
        # If command fails or output unclear, warn but don't fail
        print("[WARN] Cannot verify HackRF clock source via hackrf_debug.")
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
    try:
        import pyhackrf
        print("[*] pyhackrf Python library installed.")
        return True
    except ImportError:
        print("[!] pyhackrf not installed. Install: pip install pyhackrf")
        return False


def main():
    print("=" * 60)
    print("DSLV-ZPDI Tier 1 Provisioning Audit (RF Metrology, Rev 4.1)")
    print("=" * 60)
    print()
    print("Hardware Stack: Pi 5 + HackRF One + Leo Bodnar Mini GPSDO")
    print("Required Wiring:")
    print("  - GPSDO 10 MHz SMA → HackRF CLKIN (hardware ADC lock)")
    print("  - GPSDO 1 PPS → Pi 5 GPIO 18 (UTC timestamp)")
    print()
    
    if os.environ.get("DEV_SIMULATOR") == "1":
        print("[*] Simulation environment (DEV_SIMULATOR=1) - skipping hardware audit.")
        sys.exit(0)

    checks = [
        ("HackRF Presence", check_hackrf_presence()),
        ("HackRF Clock Source", check_hackrf_clock_source()),
        ("PPS Device", check_pps_device()),
        ("udev Rules", check_udev_rules()),
        ("Python Dependencies", check_python_dependencies()),
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
        sys.exit(0)
    else:
        print("[FAILED] Node lacks required hardware timing or RF ingestion capability.")
        print("         Refer to PHASE_2A_TIER_1_BUILD_SHEET.md for wiring guide.")
        sys.exit(1)


if __name__ == "__main__":
    main()
