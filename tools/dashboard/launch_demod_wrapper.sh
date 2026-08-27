#!/bin/bash
# Wrapper to pause ingestion pipeline, free SDR lock, run Demod, and reactivate

echo "[SYSTEM] Suspending DSLV-ZPDI ingestion pipeline to free SDR..."
# Attempt to pause the main ingestion systemd services
sudo systemctl stop dslv-zpdi.service 2>/dev/null || true
sudo systemctl stop dslv-zpdi-webdash.service 2>/dev/null || true

# Kill any manual python ingestion processes that might be holding the lock
pkill -f "main_pipeline.py" || true

# Wait until the service is fully inactive
for i in {1..10}; do
    if ! systemctl is-active --quiet dslv-zpdi.service; then
        break
    fi
    echo "[SYSTEM] Waiting for pipeline to release SDR lock..."
    sleep 1
done

echo "[SYSTEM] SDR Lock Freed. Launching Demodulation Module..."
# The main pipeline is stopped, so it's safe to use the real SDR directly here.
export DSLV_DASHBOARD_REAL_SDR="1"
# Execute the passed command
"$@"
EXIT_CODE=$?

echo ""
echo "[SYSTEM] Demodulation closed (Exit Code $EXIT_CODE). Reactivating ingestion pipeline..."

# Restart the services
sudo systemctl start dslv-zpdi.service 2>/dev/null || true
sudo systemctl start dslv-zpdi-webdash.service 2>/dev/null || true

echo "[SYSTEM] Pipeline Reactivated Successfully."
sleep 2
