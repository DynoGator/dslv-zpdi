#!/bin/bash
# ==============================================================================
# DSLV-ZPDI Boot Script: Tier 3 x86 HackRF Sim Mode
# Initiates the virtual environment, starts background services (simulator),
# and launches the live interactive dashboard.
# ==============================================================================

# Fail on error
set -e

PROJECT_DIR="/home/dynogator/Desktop/DSLV-ZPDI_GitHub_Dev/dslv-zpdi"
cd "$PROJECT_DIR"

echo "=========================================="
echo "Initializing DSLV-ZPDI Toolchain..."
echo "=========================================="

# 1. Ensure Python Virtual Environment
if [ ! -d ".venv" ]; then
    echo "[!] Virtual environment not found. Building..."
    python3 -m venv .venv
    .venv/bin/pip install --upgrade pip
    .venv/bin/pip install -e ".[dev]"
else
    echo "[OK] Virtual environment found."
fi

# Activate venv
source .venv/bin/activate

# Optional: Ensure dependencies are fresh (quietly)
echo "Verifying dependency trees..."
pip install -q -e ".[dev]"

# Ensure mock chronyc is available in .venv/bin for Sim Mode
if [ ! -f ".venv/bin/chronyc" ]; then
    echo "Creating mock chronyc for simulated timing data..."
    cat << 'EOF' > .venv/bin/chronyc
#!/bin/bash
if [ "$1" = "tracking" ]; then
    echo "Reference ID    : 50505300 (PPS)"
    echo "Stratum         : 1"
    echo "Ref time (UTC)  : $(date -u)"
    echo "System time     : 0.000000010 seconds fast of NTP time"
    echo "Last offset     : +0.000000010 seconds"
    echo "RMS offset      : 0.000000015 seconds"
    echo "Frequency       : 0.000 ppm fast"
    echo "Residual freq   : +0.000 ppm"
    echo "Skew            : 0.000 ppm"
    echo "Root delay      : 0.000000000 seconds"
    echo "Root dispersion : 0.000000000 seconds"
    echo "Update interval : 1.0 seconds"
    echo "Leap status     : Normal"
else
    exit 0
fi
EOF
    chmod +x .venv/bin/chronyc
fi

# 2. Start Services (LBE-1421 Simulator)
echo "Starting LBE-1421 GPSDO Simulator..."
python3 tools/lbe1421_simulator.py > /tmp/dslv_sim.log 2>&1 &
SIM_PID=$!

# Give the simulator a moment to create the virtual serial/pps ports
sleep 1.5

if kill -0 $SIM_PID 2>/dev/null; then
    echo "[OK] Simulator running (PID: $SIM_PID)."
else
    echo "[ERROR] Simulator failed to start. Check /tmp/dslv_sim.log"
    exit 1
fi

# 3. Launch Pipeline and Dashboard
echo "Igniting Pipeline and Interactive Dashboard..."
export PYTHONPATH="tools:src"
export DSLV_CONFIG_PATH="config/node_profiles/tier3_x86_hackrf_sim.yaml"
export DSLV_DASHBOARD_REAL_SDR=1

# Run the dashboard app. This will block until the user quits (q or Ctrl+C)
python3 tools/dashboard/app.py

# 4. Teardown & Cleanup
echo "=========================================="
echo "Shutting down services..."
echo "=========================================="
kill $SIM_PID 2>/dev/null || true
wait $SIM_PID 2>/dev/null || true
echo "[OK] DSLV-ZPDI Shutdown Complete."
