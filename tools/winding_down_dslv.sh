#!/bin/bash
# ==============================================================================
# WINDING DOWN DSLV-ZPDI
# Safely ends all processes, stops services, flushes data, and preps for shutdown
# ==============================================================================

echo "=========================================="
echo "WINDING DOWN DSLV-ZPDI SYSTEM"
echo "=========================================="

# 1. Stop any background pipelines and simulators gracefully
echo "[1/4] Sending TERM signals to background processes..."

# Find and kill the simulator
pkill -TERM -f "lbe1421_simulator.py" || true

# Find and kill dashboard app
pkill -TERM -f "dashboard/app.py" || true

# Find and kill any demodulation wrappers
pkill -TERM -f "demod_app.py" || true

# Find and kill main pipeline if manually running
pkill -TERM -f "main_pipeline.py" || true

# Wait for processes to exit gracefully to ensure data is flushed
sleep 2

# Force kill any stragglers
pkill -9 -f "lbe1421_simulator.py" 2>/dev/null || true
pkill -9 -f "dashboard/app.py" 2>/dev/null || true
pkill -9 -f "main_pipeline.py" 2>/dev/null || true

# 2. Stop systemd services (if active)
echo "[2/4] Stopping dslv_zpdi systemd service (if present)..."
sudo systemctl stop dslv_zpdi 2>/dev/null || true

# 3. Deactivate virtual environment
echo "[3/4] Deactivating Python environment (shell state)..."
# In a script, we can't deactivate the parent shell's venv natively, 
# but we can ensure our own script environment is clear.
if [ -n "$VIRTUAL_ENV" ]; then
    deactivate 2>/dev/null || true
fi

# 4. Sync disks to prevent data loss
echo "[4/4] Flushing I/O buffers to disk..."
sync

echo "=========================================="
echo "[OK] DSLV-ZPDI IS SAFELY WOUND DOWN."
echo "System is ready for a safe reboot or shutdown."
echo "=========================================="
sleep 3
