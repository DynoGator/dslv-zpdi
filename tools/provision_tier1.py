"""
SPEC-004A.1-PROVISION | Tier 1 Provisioning & Validation (Rev 4.1)
Automates hardware-readiness checks for Anchor Nodes (GPSDO/HackRF focus).
"""

import os
import subprocess
import sys


def check_hackrf_presence():
    """Ensure HackRF One is connected."""
    try:
        # hackrf_info returns 0 if HackRF is found, 1 otherwise
        res = subprocess.run(["hackrf_info"], capture_output=True, text=True, check=False)
        if res.returncode == 0:
            print("[*] HackRF One detected.")
            return True
        else:
            print("[!] HackRF One NOT found. Ingestion will fail.")
            return False
    except FileNotFoundError:
        print("[!] hackrf tools not installed.")
        return False


def check_udev_rules():
    """Check for PPS udev rules."""
    if os.path.exists("/etc/udev/rules.d/99-pps.rules"):
        print("[*] PPS udev rules found.")
        return True
    print("[WARN] 99-pps.rules missing. PPS device might require root.")
    return False


def main():
    print("=== DSLV-ZPDI Tier 1 Provisioning Audit (RF Metrology) ===")
    if os.environ.get("DEV_SIMULATOR") == "1":
        print("[*] Simulation environment - skipping hardware audit.")
        sys.exit(0)

    checks = [
        check_hackrf_presence(),
        check_udev_rules(),
    ]

    # Run the check_timing utility
    try:
        timing_res = subprocess.call([sys.executable, "tools/check_timing.py"])
        checks.append(timing_res == 0)
    except:
        checks.append(False)

    if all(checks):
        print("\n[PASSED] Node is compliant with Phase 2A mandates.")
        sys.exit(0)
    else:
        print("\n[FAILED] Node lacks hardware timing or RF ingestion capability.")
        sys.exit(1)


if __name__ == "__main__":
    main()
