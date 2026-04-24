#!/usr/bin/env bash
# DSLV-ZPDI Tier 1 Node Health Check
# Fast, non-destructive validation of all critical subsystems.
# Exit 0 = healthy, Exit 1 = degraded, Exit 2 = critical.
set -uo pipefail

REPO="/home/dynogator/dslv-zpdi"
VENV="$REPO/venv"
STATE_DIR="/var/lib/dslv_zpdi"

SEV=0
WARNINGS=0
CRITICALS=0

log_ok()  { echo "  [OK]   $*"; }
log_warn(){ echo "  [WARN] $*"; WARNINGS=$((WARNINGS+1)); [ "$SEV" -lt 1 ] && SEV=1; }
log_crit(){ echo "  [CRIT] $*"; CRITICALS=$((CRITICALS+1)); SEV=2; }

echo "=== DSLV-ZPDI Health Check ==="
echo "time: $(date -Iseconds)"
echo "node: $(hostname)"
echo ""

# 1. Python / venv
echo "[1/8] Python environment"
if [ -x "$VENV/bin/python" ]; then
  PYVER=$("$VENV/bin/python" --version 2>&1)
  log_ok "venv present: $PYVER"
else
  log_crit "venv missing at $VENV"
fi

if "$VENV/bin/python" -c "import dslv_zpdi" 2>/dev/null; then
  log_ok "dslv_zpdi importable"
else
  log_warn "dslv_zpdi not importable (run: venv/bin/pip install -e .)"
fi

echo ""

# 2. Version sync
echo "[2/8] Version sync"
if "$VENV/bin/python" "$REPO/tools/check_version_sync.py" >/dev/null 2>&1; then
  log_ok "version sync clean"
else
  log_warn "version sync failed"
fi

echo ""

# 3. Hardware (HackRF)
echo "[3/8] RF hardware"
if command -v hackrf_info >/dev/null 2>&1; then
  if hackrf_info 2>&1 | grep -q "Found HackRF"; then
    SERIAL=$(hackrf_info 2>&1 | awk -F': *' '/Serial number/{print $2; exit}')
    log_ok "HackRF detected (s/n ${SERIAL: -12})"
  else
    log_warn "hackrf_info installed but no device found"
  fi
else
  log_warn "hackrf_info not installed"
fi

echo ""

# 4. Timing / PPS
echo "[4/8] Timing subsystem"
if systemctl is-active --quiet chrony 2>/dev/null; then
  log_ok "chrony active"
else
  log_warn "chrony not active"
fi

if [ -e /dev/pps0 ]; then
  log_ok "PPS device /dev/pps0 present"
else
  log_warn "PPS device absent (GPSDO not connected or pps-gpio not loaded)"
fi

if [ -e /dev/ttyACM0 ] || [ -e /dev/ttyACM1 ] || [ -e /dev/ttyUSB0 ]; then
  log_ok "GPSDO serial port detected"
else
  log_warn "GPSDO serial port absent"
fi

echo ""

# 5. Systemd services
echo "[5/8] Systemd services"
for unit in dslv-zpdi-tuning dslv-zpdi-preflight dslv-zpdi; do
  STATE=$(systemctl is-active "$unit" 2>/dev/null || true)
  if [ "$STATE" = "active" ]; then
    log_ok "$unit: active"
  else
    log_warn "$unit: $STATE"
  fi
done

echo ""

# 6. Data directories
echo "[6/8] Data directories"
for d in "$STATE_DIR" "$REPO/output/primary" "$REPO/output/secondary"; do
  if [ -d "$d" ] && [ -w "$d" ]; then
    log_ok "$d writable"
  else
    log_warn "$d missing or not writable"
  fi
done

echo ""

# 7. Thermal / power
echo "[7/8] Thermal & power"
if command -v vcgencmd >/dev/null 2>&1; then
  TEMP=$(vcgencmd measure_temp 2>/dev/null | sed 's/temp=//;s/..C//')
  if [ "${TEMP%.*}" -lt 75 ] 2>/dev/null; then
    log_ok "SoC temp: ${TEMP}°C"
  else
    log_warn "SoC temp high: ${TEMP}°C"
  fi
  THR=$(vcgencmd get_throttled 2>/dev/null | cut -d= -f2)
  if [ "$((THR & 0x80000))" -ne 0 ] 2>/dev/null; then
    log_crit "SoC throttled!"
  elif [ "$((THR & 0x20000))" -ne 0 ] 2>/dev/null; then
    log_warn "SoC under-voltage occurred"
  fi
else
  log_warn "vcgencmd not available"
fi

GOV=$(cat /sys/devices/system/cpu/cpu0/cpufreq/scaling_governor 2>/dev/null || echo "?")
if [ "$GOV" = "performance" ]; then
  log_ok "CPU governor: performance"
else
  log_warn "CPU governor: $GOV (expected performance)"
fi

echo ""

# 8. Disk
echo "[8/8] Disk space"
USAGE=$(df -h "$REPO/output" 2>/dev/null | awk 'NR==2 {gsub(/%/,""); print $5}')
if [ -n "$USAGE" ] && [ "$USAGE" -lt 80 ] 2>/dev/null; then
  log_ok "output partition usage: ${USAGE}%"
else
  log_warn "output partition usage: ${USAGE}%"
fi

echo ""
echo "=== Summary ==="
echo "warnings: $WARNINGS  criticals: $CRITICALS  severity: $SEV"
exit $SEV
