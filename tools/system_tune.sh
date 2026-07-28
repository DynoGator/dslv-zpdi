#!/usr/bin/env bash
# DSLV-ZPDI System Tuning & Power Optimization Script
# Maximizes Pi 5 performance, disables power saving, tunes network buffers, and enforces performance governor.

set -uo pipefail

# 1. CPU Scaling Governor -> performance on all cores
for c in /sys/devices/system/cpu/cpu*/cpufreq/scaling_governor; do
    [ -e "$c" ] && echo performance > "$c" 2>/dev/null || true
done

# 2. Disable USB Power Saving & Autosuspend across all USB devices
for d in /sys/bus/usb/devices/*/power/control; do
    [ -e "$d" ] && echo on > "$d" 2>/dev/null || true
done
for d in /sys/bus/usb/devices/*/power/autosuspend; do
    [ -e "$d" ] && echo -1 > "$d" 2>/dev/null || true
done

# 3. Disable Wi-Fi Power Saving
if command -v iw >/dev/null 2>&1; then
    iw dev wlan0 set power_save off 2>/dev/null || true
fi

# 4. Low-latency Network & Socket Buffer Tuning for Telemetry Ingestion
sysctl -w net.core.rmem_max=16777216 >/dev/null 2>&1 || true
sysctl -w net.core.wmem_max=16777216 >/dev/null 2>&1 || true
sysctl -w net.core.netdev_max_backlog=10000 >/dev/null 2>&1 || true
sysctl -w net.ipv4.tcp_rmem="4096 87380 16777216" >/dev/null 2>&1 || true
sysctl -w net.ipv4.tcp_wmem="4096 65536 16777216" >/dev/null 2>&1 || true
sysctl -w net.ipv4.tcp_fastopen=3 >/dev/null 2>&1 || true

# 5. Disable Display / Screen Blanking on Virtual Consoles
if [ -e /sys/module/kernel/parameters/consoleblank ]; then
    echo 0 > /sys/module/kernel/parameters/consoleblank 2>/dev/null || true
fi

exit 0
