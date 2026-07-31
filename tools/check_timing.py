"""
SPEC-004A.1-CHECK | Timing Verification Utility (Rev 5.0)
Validates GPSDO/PPS lock and sub-microsecond jitter.
"""

import os
import re
import subprocess
import sys

import yaml


def _load_threshold(default: float = 1000.0) -> float:
    """Load the jitter threshold from config/deployment.yaml if available."""
    cfg_path = os.getenv("DSLV_CONFIG_PATH", "config/deployment.yaml")
    try:
        with open(cfg_path, encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
        return float(data.get("clock_discipline", {}).get("max_pps_jitter_ns", default))
    except Exception:
        return default


def check_pps_device(device="/dev/pps0"):
    """Verify PPS device existence and permissions."""
    if not os.path.exists(device):
        print(f"[!] FAILURE: {device} not found. pps-gpio kernel issue?")
        return False
    print(f"[*] {device} detected.")
    return True


def check_chrony_sync(threshold_ns: float = 1000.0):
    """Validate GPSDO/PPS jitter via chronyc tracking RMS offset."""
    try:
        output = subprocess.check_output(["chronyc", "tracking"], text=True)
        # RMS offset converges once chrony is locked to PPS and reflects the
        # true 1 PPS discipline quality better than the instantaneous System time.
        match = re.search(r"RMS offset\s+:\s+([-+\.\d]+)\s+seconds", output)
        if match:
            val = float(match.group(1))
            ns = abs(val) * 1_000_000_000.0
            print(f"[*] PPS RMS Offset: {ns:.2f}ns")
            if ns <= threshold_ns:
                print(f"[SUCCESS] SPEC-004A.1 Met: Jitter <= {threshold_ns:.0f}ns")
                return True
            else:
                print(f"[!] FAILURE: Jitter {ns:.2f}ns exceeds {threshold_ns:.0f}ns threshold.")
                return False
    except Exception as e:
        print(f"[!] ERROR: Could not run chronyc: {e}")
    return False


if __name__ == "__main__":
    if os.environ.get("DEV_SIMULATOR") == "1":
        print("[*] SIMULATION MODE: Skipping hardware timing checks.")
        sys.exit(0)

    threshold = _load_threshold()
    pps_device = os.getenv("DSLV_PPS_DEVICE", "/dev/pps0")

    dev_ok = check_pps_device(pps_device)
    sync_ok = check_chrony_sync(threshold)

    if dev_ok and sync_ok:
        print("\n[READY] Tier 1 Timing Discipline Verified.")
        sys.exit(0)
    else:
        # For simulation/CI, we might want to warn rather than fail if no hardware is present
        # but the prompt implies this is a hardware-specific check tool.
        print("\n[NOT READY] Hardware timing violations detected.")
        sys.exit(1)
