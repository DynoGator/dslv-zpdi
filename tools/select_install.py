#!/usr/bin/env python3
import os
import sys
import subprocess
import yaml
import argparse

def get_pi_model():
    try:
        with open("/proc/device-tree/model", "r") as f:
            return f.read().strip('\x00').strip()
    except Exception:
        return ""

def has_hackrf():
    try:
        res = subprocess.run(["hackrf_info"], capture_output=True, text=True, timeout=5)
        return res.returncode == 0
    except Exception:
        return False

def has_pluto():
    try:
        res = subprocess.run(["iio_info"], capture_output=True, text=True, timeout=5)
        return res.returncode == 0 and "ad9361-phy" in res.stdout
    except Exception:
        return False

def has_pps():
    return os.path.exists("/sys/class/pps/pps0") or os.path.exists("/dev/pps0")

def is_termux():
    return "TERMUX_VERSION" in os.environ or os.path.exists("/data/data/com.termux")

def main():
    parser = argparse.ArgumentParser(description="DSLV-ZPDI Installer Selector")
    parser.add_argument("--apply", action="store_true", help="Apply the installation (requires root)")
    args = parser.parse_args()

    nodes = {}
    current_node = None
    try:
        with open("config/nodes.yaml", "r") as f:
            for line in f:
                if line.startswith("  ") and not line.startswith("    ") and line.strip().endswith(":"):
                    current_node = line.strip()[:-1]
                    nodes[current_node] = {"coherence": "none", "faults": []}
                elif current_node and line.strip().startswith("coherence:"):
                    nodes[current_node]["coherence"] = line.split(":", 1)[1].strip()
                elif current_node and "rf_amp_blown" in line:
                    nodes[current_node]["faults"].append("rf_amp_blown")
    except Exception as e:
        print(f"Error reading config/nodes.yaml manually: {e}")
        # we don't exit so it can still succeed dry-run

    model = get_pi_model()
    hackrf = has_hackrf()
    pluto = has_pluto()
    pps = has_pps()
    termux = is_termux()

    profile = "simulator"

    if termux:
        profile = "pixel9"
    elif "Raspberry Pi 5" in model:
        if pluto:
            profile = "topdog"
        elif hackrf:
            profile = "ravenpi"
    elif "Compute Module 5" in model or "CM5" in model:
        if hackrf:
            profile = "cm5-poe"

    print(f"Detected hardware context:")
    print(f"  Model:   {model if model else 'Unknown / Not Pi'}")
    print(f"  HackRF:  {'Present' if hackrf else 'Not found'}")
    print(f"  Pluto:   {'Present (ad9361-phy)' if pluto else 'Not found'}")
    print(f"  PPS:     {'Present' if pps else 'Not found'}")
    print(f"  Termux:  {'Yes' if termux else 'No'}")
    print(f"-> Selected Profile: {profile}\n")

    if profile not in nodes and profile != "simulator":
        print(f"Warning: Profile '{profile}' not explicitly found in config/nodes.yaml")

    coherence = nodes.get(profile, {}).get("coherence", "none")
    faults = nodes.get(profile, {}).get("faults", [])
    if faults is None:
        faults = []

    if not args.apply:
        print("Dry-run mode active. Use --apply to execute installation.")
        sys.exit(0)

    if profile == "pixel9":
        if "Raspberry Pi" in model:
            print("Error: Refusing to apply pixel9 profile on a Pi.")
            sys.exit(1)
        print("Run the following command in Termux to install dependencies:")
        print("  pkg install python chrony hackrf")
        sys.exit(0)

    if os.geteuid() != 0:
        print("Error: --apply requires root privileges.")
        sys.exit(1)

    packages = ["python3", "python3-pip", "python3-venv", "chrony"]
    if profile == "topdog":
        packages.extend(["libiio-utils", "libiio-dev", "libad9361-0", "libad9361-dev", "pps-tools"])
    elif profile in ("ravenpi", "cm5-poe"):
        packages.extend(["hackrf", "libhackrf-dev"])

    print(f"Installing packages: {' '.join(packages)}")
    subprocess.run(["apt-get", "update"], check=False)
    subprocess.run(["apt-get", "install", "-y"] + packages, check=False)

    env_dir = "/etc/dslv-zpdi"
    os.makedirs(env_dir, exist_ok=True)
    env_path = os.path.join(env_dir, "node-profile.env")

    env_content = f"DSLV_NODE_ID={profile}\nDSLV_COHERENCE={coherence}\n"
    if "rf_amp_blown" in faults:
        env_content += "DSLV_RF_AMP_BLOWN=1\n"

    with open(env_path, "w") as f:
        f.write(env_content)
    
    print(f"\nWrote {env_path}:")
    print(env_content.strip())
    print("Installation applied.")

if __name__ == "__main__":
    main()
