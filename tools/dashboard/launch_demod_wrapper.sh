#!/bin/bash
# Wrapper to pause ingestion pipeline, free SDR lock, run Demod, and reactivate

echo "[SYSTEM] Suspending DSLV-ZPDI ingestion pipeline to free SDR..."
# Attempt to pause the main ingestion systemd services
sudo systemctl stop dslv-zpdi-tier1 2>/dev/null || true
sudo systemctl stop dslv-zpdi-node-receiver 2>/dev/null || true

# Also kill any manual python ingestion processes that might be holding the lock
pkill -f "tier1_ingestion_server.py" || true

echo "[SYSTEM] SDR Lock Freed. Launching Demodulation Module..."
# Execute the passed command
"$@"
EXIT_CODE=$?

echo ""
echo "[SYSTEM] Demodulation closed (Exit Code $EXIT_CODE). Reactivating ingestion pipeline..."

# Restart the services
sudo systemctl start dslv-zpdi-tier1 2>/dev/null || true
sudo systemctl start dslv-zpdi-node-receiver 2>/dev/null || true

echo "[SYSTEM] Pipeline Reactivated Successfully."
sleep 2
