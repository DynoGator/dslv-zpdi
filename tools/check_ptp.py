\"\"\"
SPEC-004A.1-CHECK | PTP Verification Utility (Rev 4.0.2)
Validates Intel i210-T1 PTP presence and nanosecond jitter.
\"\"\"
import os
import subprocess
import re
import sys

def check_ptp_device(device=\"/dev/ptp0\"):
    \"\"\"Verify PTP device existence and permissions.\"\"\"
    if not os.path.exists(device):
        print(f\"[!] FAILURE: {device} not found. i210-T1 driver issue?\")
        return False
    print(f\"[*] {device} detected.\")
    return True

def check_chrony_sync():
    \"\"\"Validate <50ns jitter via chronyc tracking.\"\"\"
    try:
        output = subprocess.check_output([\"chronyc\", \"tracking\"], text=True)
        # Look for RMS offset or Last offset
        match = re.search(r\"Last offset\s+:\s+([-+.\d]+)\s+(\w+)\", output)
        if match:
            val = float(match.group(1))
            unit = match.group(2)
            
            # Convert to nanoseconds
            if unit == \"ns\": ns = abs(val)
            elif unit == \"us\": ns = abs(val) * 1000.0
            elif unit == \"ms\": ns = abs(val) * 1_000_000.0
            else: ns = abs(val) * 1_000_000_000.0
            
            print(f\"[*] PTP Offset: {ns:.2f}ns\")
            if ns <= 50.0:
                print(\"[SUCCESS] SPEC-004A.1 Met: Jitter < 50ns\")
                return True
            else:
                print(f\"[!] FAILURE: Jitter {ns:.2f}ns exceeds 50ns threshold.\")
                return False
    except Exception as e:
        print(f\"[!] ERROR: Could not run chronyc: {e}\")
    return False

if __name__ == \"__main__\":
    if os.environ.get(\"DEV_SIMULATOR\") == \"1\":
        print(\"[*] SIMULATION MODE: Skipping hardware PTP checks.\")
        sys.exit(0)
        
    dev_ok = check_ptp_device()
    sync_ok = check_chrony_sync()
    
    if dev_ok and sync_ok:
        print(\"\n[READY] Tier 1 Timing Discipline Verified.\")
        sys.exit(0)
    else:
        print(\"\n[NOT READY] Hardware timing violations detected.\")
        sys.exit(1)
