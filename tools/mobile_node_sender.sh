#!/usr/bin/env bash
# DSLV-ZPDI Mobile Node Telemetry Sender
# Run this on the Pixel 9 Pro XL (Termux / GrapheneOS) to register with
# the Pi 5 anchor and POST periodic telemetry to the node receiver.
#
# Usage:
#   bash mobile_node_sender.sh              # default interval: 30s
#   bash mobile_node_sender.sh 10           # custom interval in seconds
#   bash mobile_node_sender.sh --once       # send one packet and exit
#
# Prerequisites (pkg install these in Termux if missing):
#   pkg install curl termux-api
#
# The Pi receiver is at http://10.128.24.69:5775/api/v1/ingest
# The Pi web dashboard is at http://10.128.24.69:8080/

set -euo pipefail

PI_IP="${DSLV_PI_IP:-10.128.24.69}"
RECEIVER_URL="http://${PI_IP}:5775/api/v1/ingest"
HEARTBEAT_URL="http://${PI_IP}:8080/api/node_seen/pixel-9-pro-xl"
NODE_ID="pixel-9-pro-xl"
INTERVAL="${1:-30}"
ONE_SHOT=false
[[ "${1:-}" == "--once" ]] && ONE_SHOT=true && INTERVAL=0

log() { printf "[%s] %s\n" "$(date +'%H:%M:%S')" "$*"; }

send_telemetry() {
    local ts; ts=$(date +%s.%N)
    local battery="unknown"
    local temp_c="null"

    # termux-battery-status is available if termux-api is installed
    if command -v termux-battery-status &>/dev/null; then
        local bat_json; bat_json=$(termux-battery-status 2>/dev/null || echo '{}')
        battery=$(echo "$bat_json" | grep -oP '"percentage":\s*\K[0-9]+' || echo "unknown")
        temp_c=$(echo "$bat_json"  | grep -oP '"temperature":\s*\K[0-9.]+' || echo "null")
    fi

    local payload
    payload=$(cat <<EOF
{
  "node_id": "${NODE_ID}",
  "timestamp_utc": ${ts},
  "platform": "GrapheneOS/Termux",
  "modality": "mobile_telemetry",
  "battery_pct": ${battery},
  "battery_temp_c": ${temp_c},
  "signal_strength": 0.5,
  "lat": 0.0,
  "lon": 0.0,
  "region_id": "mobile"
}
EOF
)

    local http_code
    http_code=$(curl -s -o /dev/null -w "%{http_code}" \
        -X POST \
        -H "Content-Type: application/json" \
        -d "$payload" \
        --max-time 5 \
        "$RECEIVER_URL" 2>/dev/null || echo "000")

    if [[ "$http_code" == "200" ]]; then
        log "Telemetry sent OK (battery=${battery}%)"
    else
        log "Telemetry send failed — HTTP ${http_code} (Pi reachable?)"
    fi

    # Also ping the heartbeat endpoint so the web dashboard knows we're alive
    curl -s -X POST --max-time 3 "$HEARTBEAT_URL" >/dev/null 2>&1 || true
}

log "DSLV-ZPDI Mobile Node Sender starting"
log "Node ID : ${NODE_ID}"
log "Receiver: ${RECEIVER_URL}"
log "Interval: ${INTERVAL}s"
echo "---"

while true; do
    send_telemetry
    $ONE_SHOT && break
    sleep "$INTERVAL"
done
