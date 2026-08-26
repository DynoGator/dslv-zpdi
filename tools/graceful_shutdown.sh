#!/bin/bash
# DSLV-ZPDI Graceful Shutdown Script
# Prepares the stack for a clean re-initiation or system reboot.

echo -e "\033[1;36m=== DSLV-ZPDI Graceful Shutdown ===\033[0m"

echo "1. Stopping Production Pipeline..."
sudo systemctl stop dslv-zpdi.service 2>/dev/null || true

echo "2. Stopping Web Dashboard..."
sudo systemctl stop dslv-zpdi-webdash.service 2>/dev/null || true

echo "3. Stopping Preflight & Tuning Services..."
sudo systemctl stop dslv-zpdi-tuning.service 2>/dev/null || true
sudo systemctl stop dslv-zpdi-preflight.service 2>/dev/null || true

echo "4. Terminating Manual Processes..."
pkill -f "python -m dashboard" || true
pkill -f "demod_app.py" || true
pkill -f "main_pipeline.py" || true

echo "5. Cleaning up GPIO Exports..."
sudo systemctl stop dslv-zpdi-gpio-setup.service 2>/dev/null || true
echo 575 | sudo tee /sys/class/gpio/unexport 2>/dev/null || true
echo 585 | sudo tee /sys/class/gpio/unexport 2>/dev/null || true

echo "6. Flushing Log Buffers..."
sync

echo -e "\033[1;32m[✓] DSLV-ZPDI Stack is securely wound down and ready for clean initiation.\033[0m"
sleep 3
