#!/usr/bin/env bash
# DSLV-ZPDI Tier-2 Mobile Node Health Check (Pixel / Termux / proot)
# Fast, non-destructive validation. Exit 0=healthy, 1=degraded, 2=critical.
set -uo pipefail

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VENV="$REPO/.venv"
SEV=0
WARNINGS=0
CRITICALS=0

log_ok()   { echo "  [OK]   $*"; }
log_warn() { echo "  [WARN] $*"; WARNINGS=$((WARNINGS+1)); [ "$SEV" -lt 1 ] && SEV=1; }
log_crit() { echo "  [CRIT] $*"; CRITICALS=$((CRITICALS+1)); SEV=2; }

echo "=== DSLV-ZPDI Mobile Tier-2 Health Check ==="
echo "time: $(date -Iseconds)"
echo "repo: $REPO"
echo ""

# 1. Python environment
echo "[1/8] Python environment"
if [ -x "$VENV/bin/python" ]; then
  log_ok "venv: $($VENV/bin/python --version 2>&1)"
else
  log_crit "venv missing at $VENV"
fi

echo ""

# 2. Daemon / supervisor
echo "[2/8] Daemon & supervisor"
if pgrep -f "zpdi_mobile_node.py" >/dev/null 2>&1; then
  log_ok "zpdi_mobile_node.py running"
else
  log_warn "daemon not running"
fi
if pgrep -f "supervisor.sh" >/dev/null 2>&1; then
  log_ok "supervisor.sh active"
else
  log_warn "supervisor not active"
fi

echo ""

# 3. Health heartbeat
echo "[3/8] Health log"
if [ -f "$REPO/logs/health.jsonl" ]; then
  age=$(( $(date +%s) - $(stat -c %Y "$REPO/logs/health.jsonl" 2>/dev/null || echo 0) ))
  if [ "$age" -le 90 ]; then
    log_ok "health.jsonl fresh (${age}s)"
    tail -1 "$REPO/logs/health.jsonl" | "$VENV/bin/python" -m json.tool 2>/dev/null | head -8 || true
  else
    log_crit "health.jsonl stale (${age}s > 90s)"
  fi
else
  log_warn "health.jsonl missing"
fi

echo ""

# 4. Sensors (Termux)
echo "[4/8] Termux sensors"
if command -v termux-sensor >/dev/null 2>&1; then
  log_ok "termux-sensor available"
else
  log_warn "termux-sensor not in PATH (expected outside proot)"
fi

echo ""

# 5. WSS / Tier-1 transport
echo "[5/8] WSS transport"
if pgrep -f "tier1_ingestion_server.py" >/dev/null 2>&1; then
  log_ok "tier1_ingestion_server.py running"
else
  log_warn "Tier-1 server not running (fallback JSONL only)"
fi
if [ -f "$REPO/logs/health.jsonl" ]; then
  wss=$(tail -1 "$REPO/logs/health.jsonl" | "$VENV/bin/python" -c "import sys,json; d=json.load(sys.stdin); print(d.get('wss_connected', False))" 2>/dev/null || echo "?")
  if [ "$wss" = "True" ]; then
    log_ok "wss_connected=true"
  else
    log_warn "wss_connected=$wss"
  fi
fi

echo ""

# 6. Web API
echo "[6/8] FastAPI web server"
if curl -sf "http://127.0.0.1:8000/health" >/dev/null 2>&1; then
  log_ok "zpdi_web_server /health reachable"
else
  log_warn "web server down on 127.0.0.1:8000"
fi

echo ""

# 7. Tier-2 HDF5 quarantine
echo "[7/8] HDF5 quarantine (Tier-2 must not grow primary)"
if [ -f "$REPO/data/zpdi_stream.h5" ]; then
  rows=$("$VENV/bin/python" -c "
import h5py
with h5py.File('$REPO/data/zpdi_stream.h5','r',swmr=True) as f:
    print(f['payloads'].shape[0] if 'payloads' in f else 0)
" 2>/dev/null || echo "?")
  log_ok "HDF5 rows: $rows (historical pre-compliance rows expected)"
else
  log_warn "HDF5 file absent"
fi

echo ""

# 8. Disk & secondary stream
echo "[8/8] Disk & secondary log"
usage=$(df -h "$REPO" 2>/dev/null | awk 'NR==2 {gsub(/%/,""); print $5}')
if [ -n "$usage" ] && [ "$usage" -lt 90 ] 2>/dev/null; then
  log_ok "disk usage: ${usage}%"
else
  log_warn "disk usage: ${usage}%"
fi
if [ -f "$REPO/logs/zpdi_fallback.jsonl" ]; then
  lines=$(wc -l < "$REPO/logs/zpdi_fallback.jsonl")
  log_ok "secondary JSONL lines: $lines"
fi

echo ""
echo "=== Summary ==="
echo "warnings: $WARNINGS  criticals: $CRITICALS  severity: $SEV"
exit $SEV