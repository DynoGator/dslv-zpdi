#!/usr/bin/env bash
# DSLV-ZPDI Hardware Preflight
# Runs before main pipeline starts. Non-fatal by design: logs warnings for
# missing hardware (e.g. GPSDO not yet delivered) but never blocks pipeline.
set -uo pipefail

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

LOG(){ logger -t dslv-zpdi-preflight -- "$*"; echo "[preflight] $*"; }
WARN(){ logger -t dslv-zpdi-preflight -p user.warning -- "$*"; echo "[preflight][WARN] $*" >&2; }

LOG "===== DSLV-ZPDI preflight starting ====="

# 1. Kill any known conflicting SDR tools
for proc in gqrx SoapySDRUtil sdrangel rtl_tcp rtl_fm openwebrx airspy_rx hackrf_transfer hackrf_sweep hackrf_spectrum; do
    if pgrep -x "$proc" >/dev/null 2>&1; then
        WARN "conflicting process detected: $proc — killing"
        pkill -TERM -x "$proc" 2>/dev/null || true
        sleep 0.5
        pkill -KILL -x "$proc" 2>/dev/null || true
    fi
done

# 2. Verify PlutoSDR+ reachability (non-fatal)
# Try USB context first, then common network addresses used by Pluto/LibreSDR.
PLUTO_REACHABLE=0
if command -v iio_info >/dev/null 2>&1; then
    for PLUTO_URI in "${DSLV_SDR_URI:-usb:}" "ip:192.168.2.1" "ip:192.168.3.80"; do
        if iio_info -u "$PLUTO_URI" >/dev/null 2>&1; then
            LOG "PlutoSDR+ reachable at $PLUTO_URI"
            PLUTO_REACHABLE=1
            break
        fi
    done
    if [ "$PLUTO_REACHABLE" -eq 0 ]; then
        WARN "PlutoSDR+ not reachable via usb:/192.168.2.1/192.168.3.80 (check network / power)"
    fi
else
    WARN "iio_info not installed; cannot verify PlutoSDR+"
fi

# 3. Verify HackRF presence (legacy / optional)
if command -v hackrf_info >/dev/null 2>&1; then
    if hackrf_info 2>&1 | grep -q "Found HackRF"; then
        LOG "HackRF detected (legacy)"
    fi
fi

# 4. Verify PPS device (non-fatal — awaiting GPSDO)
if [ -e /dev/pps0 ]; then
    LOG "PPS device /dev/pps0 present"
else
    WARN "/dev/pps0 not present (GPSDO may not be connected yet)"
fi

# 5. Verify chrony is running
if systemctl is-active --quiet chrony; then
    LOG "chrony active"
else
    WARN "chrony not active"
fi

# 6. Verify pipeline state dir exists and is writable
STATE_DIR=/var/lib/dslv_zpdi
OUT_DIR="$REPO/output"
for d in "$STATE_DIR" "$OUT_DIR" "$OUT_DIR/primary" "$OUT_DIR/secondary"; do
    if [ ! -d "$d" ]; then
        mkdir -p "$d" 2>/dev/null && LOG "created $d" || WARN "failed to create $d"
    fi
    chown -R dynogator:dynogator "$d" 2>/dev/null || true
done

# 7. Clear any root-owned files that would block unprivileged writes
find "$OUT_DIR" -not -user dynogator -exec chown dynogator:dynogator {} + 2>/dev/null || true

# 8. Log thermal & power state for post-mortem context
if command -v vcgencmd >/dev/null 2>&1; then
    TEMP=$(vcgencmd measure_temp 2>/dev/null | tr -d '\n')
    THR=$(vcgencmd get_throttled 2>/dev/null | tr -d '\n')
    LOG "$TEMP  $THR"
fi

# 9. Repo validation (non-fatal)
# REPO already defined at top of script
if [ -d "$REPO" ]; then
    if "$REPO/.venv/bin/python" "$REPO/tools/check_version_sync.py" >/dev/null 2>&1; then
        LOG "repo version sync OK"
    else
        WARN "repo version sync failed"
    fi
    if "$REPO/.venv/bin/python" "$REPO/tools/repo_guard.py" >/dev/null 2>&1; then
        LOG "repo guard OK"
    else
        WARN "repo guard failed"
    fi
fi

# 10. Governor check
GOV=$(cat /sys/devices/system/cpu/cpu0/cpufreq/scaling_governor 2>/dev/null || echo "?")
if [ "$GOV" = "performance" ]; then
    LOG "governor=performance"
else
    WARN "governor=$GOV (expected performance)"
    for c in /sys/devices/system/cpu/cpu*/cpufreq/scaling_governor; do
        echo performance > "$c" 2>/dev/null || true
    done
fi

LOG "===== preflight complete (non-fatal) ====="
exit 0
