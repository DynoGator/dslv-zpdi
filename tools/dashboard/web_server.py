"""
DSLV-ZPDI Web Dashboard — remote telemetry view & control.

Serves an interactive HTML dashboard at http://<pi-ip>:8080/ that mirrors the
key metrics panels from the Rich TUI (system, pipeline, hardware, swarm node
status). The page auto-refreshes every 5 seconds. Includes SDR control and
demodulation presets.
"""

from __future__ import annotations

import json
import logging
import os
import socket
import subprocess
import time
import urllib.error
import urllib.request
from pathlib import Path
from urllib.parse import urlparse

try:
    from flask import Flask, Response, jsonify, request
    FLASK_AVAILABLE = True
except ImportError:
    FLASK_AVAILABLE = False

from dashboard.mobile_bridge import (
    _read_last_json_object,
    collect_mobile_telemetry,
    load_registered_nodes,
)

logger = logging.getLogger("dslv-zpdi.webdash")

# ── Registered nodes (loaded from deployment.yaml if available) ───────────────

_BUILTIN_NODES = [
    {
        "node_id": "pixel-9-pro-xl",
        "ip": "10.128.24.165",
        "probe_url": "http://10.128.24.165:5173/",
        "platform": "GrapheneOS / Termux",
        "description": "Pixel 9 Pro XL — Tier 2 mobile node",
        "dashboard_url": "http://10.128.24.165:5173/",
    },
]

def _load_registered_nodes() -> list:
    registered = load_registered_nodes()
    return registered if registered else _BUILTIN_NODES

# ── Global SDR State for Simulation / Control ──────────────────────────────────
# This represents the user's selected configuration.
GLOBAL_SDR_CONFIG = {
    "active_device": "pluto_iio",
    "preset": "fm_broadcast",
    "center_hz": 98_100_000,
    "demod_mode": "WFM",
    "volume": 50,
}

# ── HTML template ─────────────────────────────────────────────────────────────

_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>DSLV-ZPDI Operations Dashboard</title>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;600;800&family=JetBrains+Mono:wght@400;700&display=swap" rel="stylesheet">
<style>
  :root {
    --bg: #0b0f19; --card: #151b2b; --card-hover: #1e253c;
    --border: #2a3441; --cyan: #00e5ff; --cyan-dim: #00e5ff33;
    --green: #00e676; --yellow: #ffea00; --red: #ff1744;
    --text: #e2e8f0; --dim: #94a3b8; --accent: #3b82f6;
  }
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body {
    background: var(--bg); color: var(--text);
    font-family: 'Inter', sans-serif; font-size: 14px;
    padding: 20px; line-height: 1.5;
  }
  h1 {
    color: var(--cyan); font-size: 24px; margin-bottom: 20px;
    letter-spacing: 2px; font-weight: 800; text-transform: uppercase;
    text-shadow: 0 0 10px var(--cyan-dim);
  }
  .header-controls { display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px; }
  .grid {
    display: grid; grid-template-columns: repeat(auto-fit, minmax(320px, 1fr));
    gap: 16px; margin-bottom: 20px;
  }
  .card {
    background: var(--card); border: 1px solid var(--border);
    border-radius: 12px; padding: 16px;
    box-shadow: 0 4px 6px -1px rgba(0,0,0,0.3);
    transition: transform 0.2s, box-shadow 0.2s;
  }
  .card:hover { transform: translateY(-2px); box-shadow: 0 8px 12px -2px rgba(0,0,0,0.4); border-color: #3b4b5e; }
  .card h2 {
    font-size: 13px; text-transform: uppercase; letter-spacing: 1.5px;
    color: var(--cyan); margin-bottom: 12px; font-weight: 600;
    border-bottom: 1px solid var(--border); padding-bottom: 8px;
  }
  .row { display: flex; justify-content: space-between; align-items: center; margin: 6px 0; gap: 8px; }
  .label { color: var(--dim); white-space: nowrap; font-family: 'JetBrains Mono', monospace; font-size: 13px; }
  .val { font-weight: 600; text-align: right; font-family: 'JetBrains Mono', monospace; font-size: 13px; }
  .ok { color: var(--green); } .warn { color: var(--yellow); } .bad { color: var(--red); }
  .cyan { color: var(--cyan); }
  #ts { color: var(--dim); font-size: 12px; margin-top: 10px; text-align: center; }
  .badge {
    display: inline-block; padding: 2px 8px; border-radius: 12px;
    font-size: 11px; font-weight: 700; letter-spacing: 0.5px; margin-left: 4px;
    text-transform: uppercase;
  }
  .badge-green { background: rgba(0, 230, 118, 0.15); color: var(--green); border: 1px solid rgba(0,230,118,0.3); }
  .badge-yellow { background: rgba(255, 234, 0, 0.15); color: var(--yellow); border: 1px solid rgba(255,234,0,0.3); }
  .badge-red { background: rgba(255, 23, 68, 0.15); color: var(--red); border: 1px solid rgba(255,23,68,0.3); }
  .badge-blue { background: rgba(0, 229, 255, 0.15); color: var(--cyan); border: 1px solid rgba(0,229,255,0.3); }
  hr { border: none; border-top: 1px solid var(--border); margin: 12px 0; }

  /* Buttons & Controls */
  button {
    background: var(--border); color: var(--text); border: none;
    padding: 6px 12px; border-radius: 6px; cursor: pointer;
    font-family: 'Inter', sans-serif; font-size: 12px; font-weight: 600;
    transition: all 0.2s;
  }
  button:hover { background: var(--accent); color: #fff; }
  button:active { transform: scale(0.95); }
  .btn-danger { background: rgba(255,23,68,0.2); color: var(--red); border: 1px solid var(--red); }
  .btn-danger:hover { background: var(--red); color: #fff; }
  .btn-group { display: flex; gap: 8px; margin-top: 10px; flex-wrap: wrap; }
  select {
    background: #0b0f19; color: var(--cyan); border: 1px solid var(--border);
    padding: 6px; border-radius: 6px; font-family: 'JetBrains Mono', monospace; font-size: 12px;
  }

  /* Demodulator UI */
  .demod-panel { background: rgba(0,229,255,0.05); border: 1px solid var(--cyan-dim); border-radius: 8px; padding: 12px; margin-top: 12px; }
  .demod-panel h3 { font-size: 12px; color: var(--cyan); margin-bottom: 8px; text-transform: uppercase; }
  .preset-btns { display: grid; grid-template-columns: 1fr 1fr; gap: 8px; margin-bottom: 12px; }

</style>
</head>
<body>
<div class="header-controls">
  <h1>&#9632; DSLV-ZPDI INTERACTIVE METROLOGY DASHBOARD</h1>
  <div>
    <button onclick="window.open('/user_guide', '_blank')">User Guide</button>
  </div>
</div>

<div class="grid" id="panels">
  <!-- System -->
  <div class="card" id="c-system"><h2>System</h2><p class="val cyan">Loading…</p></div>

  <!-- Pipeline -->
  <div class="card" id="c-pipeline"><h2>Pipeline</h2><p class="val cyan">Loading…</p></div>

  <!-- Swarm Nodes -->
  <div class="card" id="c-nodes"><h2>Swarm Nodes</h2><p class="val cyan">Loading…</p></div>

  <!-- SDR Control Panel -->
  <div class="card" id="c-sdr-ctrl">
    <h2>SDR Hardware & Demodulation</h2>
    <div class="row">
      <span class="label">Active Device</span>
      <select id="sdr-device" onchange="updateSDR()">
        <option value="pluto_iio">PlutoSDR (IIO)</option>
        <option value="libresdr">LibreSDR</option>
        <option value="hackrf1">HackRF One</option>
      </select>
    </div>
    <div class="row">
      <span class="label">Hardware Status</span>
      <span class="val" id="sdr-hw-status">--</span>
    </div>
    <div class="btn-group" style="justify-content: flex-end;">
      <button class="btn-danger" onclick="rebootSDR()">Soft Reboot Hardware</button>
    </div>

    <div class="demod-panel">
      <h3>Demodulation Control Center</h3>
      <div class="row" style="margin-bottom: 12px;">
        <span class="label">Quick Presets</span>
        <select id="demod-preset" onchange="applyPresetDropdown()" style="flex-grow: 1; margin-left: 10px;">
          <option value="">-- Select Preset --</option>
          <option value="airband">VHF Airband (120 MHz, AM)</option>
          <option value="marine">Marine VHF (156 MHz, FM)</option>
          <option value="weather">NOAA Wx (162.4 MHz, FM)</option>
          <option value="adsb">ADS-B (1090 MHz, RAW)</option>
          <option value="am_broadcast">AM Broadcast (1 MHz, AM)</option>
          <option value="fm_broadcast">FM Broadcast (98.1 MHz, WFM)</option>
        </select>
      </div>
      <hr>
      <div class="row">
        <span class="label">Custom Freq (MHz)</span>
        <input type="number" id="freq-input" step="0.1" style="width: 100px; background: #0b0f19; color: var(--cyan); border: 1px solid var(--border); padding: 6px; border-radius: 4px; font-family: monospace;">
      </div>
      <div class="row">
        <span class="label">Demod Mode</span>
        <select id="demod-mode" style="width: 100px;">
          <option value="WFM">WFM</option>
          <option value="NFM">NFM</option>
          <option value="AM">AM</option>
          <option value="USB">USB</option>
          <option value="LSB">LSB</option>
          <option value="CW">CW</option>
          <option value="RAW">RAW</option>
        </select>
      </div>
      <div class="btn-group" style="margin-top: 15px; justify-content: space-between;">
        <button onclick="applyCustomFreq()" style="background: var(--cyan); color: #0b0f19; width: 48%;">TUNE</button>
        <button id="audio-btn" onclick="toggleAudio()" style="background: var(--green); color: #0b0f19; width: 48%;">START AUDIO</button>
      </div>
      <audio id="audio-player" style="display: none;" controls preload="none"></audio>
    </div>
  </div>

  <!-- UPS -->
  <div class="card" id="c-ups"><h2>UPS / Power</h2><p class="val cyan">Loading…</p></div>
</div>

<div id="ts">Last update: —</div>

<script>
function esc(s) {
  return String(s==null?'':s)
    .replace(/&/g,'&amp;')
    .replace(/</g,'&lt;')
    .replace(/>/g,'&gt;')
    .replace(/"/g,'&quot;');
}
function row(label, val, cls) {
  return '<div class="row"><span class="label">'+esc(label)+'</span><span class="val '+(cls||'')+'">'+val+'</span></div>';
}
function badge(txt, ok, bad) {
  var c = ok ? 'badge-green' : (bad ? 'badge-red' : 'badge-yellow');
  if(txt === 'ACTIVE' || txt === 'ONLINE') c = 'badge-green';
  return '<span class="badge '+c+'">'+txt+'</span>';
}

let isAudioPlaying = false;

async function refresh() {
  try {
    const r = await fetch('/api/status');
    if(!r.ok) return;
    const d = await r.json();
    const s = d.system || {};
    const p = d.pipeline || {};
    const n = d.nodes || {};
    const sdr = d.sdr || {};
    const u = d.ups || {};
    const m = d.mobile || {};

    // System Panel
    document.getElementById('c-system').innerHTML =
      '<h2>System</h2>'+
      row('Hostname', esc(s.hostname||'?'),'cyan')+
      row('CPU', s.cpu_pct!=null?s.cpu_pct.toFixed(1)+'%':'?', s.cpu_pct>80?'bad':s.cpu_pct>60?'warn':'ok')+
      row('RAM', s.ram_pct!=null?s.ram_pct.toFixed(1)+'%':'?', s.ram_pct>85?'bad':s.ram_pct>70?'warn':'ok')+
      row('Temp', s.cpu_temp!=null?s.cpu_temp.toFixed(1)+'&deg;C':'?', s.cpu_temp>80?'bad':s.cpu_temp>70?'warn':'ok')+
      row('Uptime', esc(s.uptime||'?'))+
      row('Pi IP', esc(s.pi_ip||'?'),'dim');

    // Pipeline Panel
    document.getElementById('c-pipeline').innerHTML =
      '<h2>Pipeline</h2>'+
      row('Service', badge(p.active?'ACTIVE':'INACTIVE', p.active, !p.active))+
      row('Timing', badge(p.timing_healthy?'LOCKED':'DEGRADED', p.timing_healthy, !p.timing_healthy))+
      row('Writes', p.primary_written??'?','ok')+
      row('Int. Fails', p.integrity_failed??'?', p.integrity_failed>0?'bad':'ok')+
      row('Receiver Port', ':'+p.receiver_port,'dim');

    // Nodes Panel
    let nodeHtml='<h2>Swarm Nodes</h2>';
    nodeHtml += row('Pi 5 Anchor', badge('LOCAL', true, false));
    (n.registered_nodes||[]).forEach(nd => {
      nodeHtml += '<hr>';
      nodeHtml += row(esc(nd.node_id), badge(nd.online?'ONLINE':'OFFLINE', nd.online, !nd.online));
      if(nd.online && nd.probe_ms!=null) nodeHtml+=row('Lat.', nd.probe_ms+'ms', nd.probe_ms<50?'ok':nd.probe_ms<200?'warn':'bad');
      if(nd.last_seen_utc) nodeHtml+=row('Last seen', new Date(nd.last_seen_utc*1000).toUTCString(), 'dim');
    });
    nodeHtml += '<hr>'+row('Mobile T2', badge(m.online?'ONLINE':'OFFLINE', m.online, !m.online));
    if(m.trust_score!=null) nodeHtml+=row('Trust', Number(m.trust_score).toFixed(2), m.trust_score>=0.7?'ok':m.trust_score>=0.5?'warn':'bad');
    document.getElementById('c-nodes').innerHTML = nodeHtml;

    // Update SDR HW Status display (without overriding the whole card so we keep inputs)
    const hwStat = document.getElementById('sdr-hw-status');
    if(hwStat) {
      hwStat.innerHTML = badge(sdr.reachable?'READY':'OFFLINE', sdr.reachable, !sdr.reachable) + ' ' + (sdr.center_hz? (sdr.center_hz/1e6).toFixed(2)+'MHz' : '');
    }

    // UPS Panel
    let upsHtml='<h2>UPS / Power</h2>';
    if(u.health==='absent'){
      upsHtml+=row('Status','ABSENT','bad');
    } else {
      upsHtml+=row('Status', badge(u.health||'?', u.health==='healthy', u.health==='critical'));
      upsHtml+=row('Battery', u.battery_percent!=null?u.battery_percent.toFixed(1)+'%':'?');
      upsHtml+=row('Voltage', u.battery_voltage_v!=null?u.battery_voltage_v.toFixed(2)+'V':'?');
      upsHtml+=row('AC Power', u.ac_present?'YES':'NO', u.ac_present?'ok':'bad');
    }
    document.getElementById('c-ups').innerHTML = upsHtml;

    document.getElementById('ts').textContent = 'Last update: ' + new Date().toUTCString();
  } catch(e) { console.warn('refresh failed', e); }
}

async function updateSDR() {
  const dev = document.getElementById('sdr-device').value;
  await fetch('/api/sdr/config', {
    method: 'POST', headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({ active_device: dev })
  });
  refresh();
}

async function applyPresetDropdown() {
  const select = document.getElementById('demod-preset');
  const presetName = select.value;
  if(!presetName) return;
  await fetch('/api/sdr/preset', {
    method: 'POST', headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({ preset: presetName })
  });
  alert('Preset ' + presetName + ' applied!');
  refresh();
}

async function applyPreset(presetName) {
  await fetch('/api/sdr/preset', {
    method: 'POST', headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({ preset: presetName })
  });
  alert('Preset ' + presetName + ' applied!');
  refresh();
}

async function applyCustomFreq() {
  const freqMHz = parseFloat(document.getElementById('freq-input').value);
  const mode = document.getElementById('demod-mode').value;
  if(isNaN(freqMHz)) return alert('Invalid frequency');
  await fetch('/api/sdr/config', {
    method: 'POST', headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({ center_hz: freqMHz * 1e6, demod_mode: mode })
  });
  alert('Tuned to ' + freqMHz + ' MHz (' + mode + ')');
  refresh();
}

async function rebootSDR() {
  if(confirm("Are you sure you want to soft-reboot the selected SDR hardware? This will interrupt acquisition.")) {
    await fetch('/api/sdr/reboot', { method: 'POST' });
    alert('Reboot command issued to SDR.');
  }
}

async function sysShutdown() {
  if(confirm("DANGER: Are you sure you want to completely power off the Metrology Node? You will lose connection.")) {
    await fetch('/api/system/shutdown', { method: 'POST' });
    alert('Shutdown sequence initiated. Goodbye.');
  }
}

function toggleAudio() {
  const player = document.getElementById('audio-player');
  const btn = document.getElementById('audio-btn');
  isAudioPlaying = !isAudioPlaying;

  if (isAudioPlaying) {
    player.src = '/api/audio/stream?t=' + Date.now();
    player.play().catch(e => {
        console.warn('Audio play failed:', e);
        alert('Could not start audio stream. Ensure SDR is tuned.');
        isAudioPlaying = false;
        btn.textContent = 'START AUDIO';
        btn.style.background = 'var(--green)';
    });
    if(isAudioPlaying) {
        btn.textContent = 'STOP AUDIO';
        btn.style.background = 'var(--red)';
    }
  } else {
    player.pause();
    player.src = '';
    btn.textContent = 'START AUDIO';
    btn.style.background = 'var(--green)';
  }
}

refresh();
setInterval(refresh, 5000); // 5 sec refresh as requested
</script>
</body>
</html>"""

# ── Node liveness probe ───────────────────────────────────────────────────────

def _probe_node(probe_url: str, timeout: float = 2.0) -> tuple[bool, int | None]:
    try:
        parsed = urlparse(probe_url)
        if parsed.scheme not in {"http", "https"}:
            return False, None
        t0 = time.monotonic()
        req = urllib.request.Request(probe_url, method="GET")
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            resp.read(64)
        return True, int((time.monotonic() - t0) * 1000)
    except Exception:
        return False, None

def _get_pi_ip() -> str:
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.settimeout(0)
        # UDP connect does not send packets; used only to resolve the egress IP.
        s.connect(("1.1.1.1", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "?"


def _cpu_temp_c(temps: dict) -> float | None:
    if not temps:
        return None
    for key in ("cpu_thermal", "soc_thermal", "coretemp"):
        entries = temps.get(key) or []
        if not entries:
            continue
        entry = entries[0]
        val = getattr(entry, "current", None)
        if val is None and isinstance(entry, dict):
            val = entry.get("current")
        if val is not None:
            try:
                return float(val)
            except (TypeError, ValueError):
                return None
    for entries in temps.values():
        if not entries:
            continue
        entry = entries[0]
        val = getattr(entry, "current", None)
        if val is not None:
            try:
                return float(val)
            except (TypeError, ValueError):
                return None
    return None


def _read_health() -> dict:
    env_path = os.getenv("DSLV_HEALTH_JSON", "").strip()
    health_paths = (
        [env_path]
        if env_path
        else ["/run/dslv-zpdi/health.json", "/tmp/health.json", "./logs/health.jsonl"]
    )
    for hpath in health_paths:
        try:
            if not os.path.exists(hpath):
                continue
            if hpath.endswith(".jsonl"):
                obj = _read_last_json_object(Path(hpath))
                if obj:
                    return obj
            else:
                with open(hpath, encoding="utf-8") as f:
                    data = json.load(f)
                if isinstance(data, dict):
                    return data
        except Exception:
            continue
    return {}


def _load_registry_by_id() -> dict[str, dict]:
    reg_path = Path(os.getenv("DSLV_SECONDARY_OUTPUT_DIR", "./output/secondary")) / "node_registry.jsonl"
    entries: dict[str, dict] = {}
    if not reg_path.exists():
        return entries
    try:
        with open(reg_path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    entry = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if isinstance(entry, dict) and entry.get("node_id"):
                    entries[str(entry["node_id"])] = entry
    except OSError as exc:
        logger.debug("Could not read telemetry nodes: %s", exc)
    return entries


def _shutdown_allowed(remote_addr: str | None) -> bool:
    flag = os.getenv("DSLV_WEBDASH_ALLOW_SHUTDOWN", "").strip().lower() in ("1", "true", "yes")
    return flag and remote_addr in ("127.0.0.1", "::1")


def _get_status() -> dict:
    status: dict = {}
    health = _read_health()

    try:
        import psutil
        vm = psutil.virtual_memory()
        temps = psutil.sensors_temperatures() or {}
        cpu_temp = _cpu_temp_c(temps)
        uptime_s = time.time() - psutil.boot_time()
        h, rem = divmod(int(uptime_s), 3600)
        m, _s = divmod(rem, 60)
        status["system"] = {
            "hostname": socket.gethostname(),
            "pi_ip": _get_pi_ip(),
            "cpu_pct": psutil.cpu_percent(interval=None),
            "ram_pct": vm.percent,
            "cpu_temp": cpu_temp,
            "uptime": f"{h}h {m}m",
        }
    except Exception:
        status["system"] = {
            "hostname": socket.gethostname(),
            "pi_ip": _get_pi_ip(),
            "cpu_pct": 0,
            "ram_pct": 0,
            "cpu_temp": None,
            "uptime": "0h 0m",
        }

    try:
        cr = subprocess.run(["pgrep", "-f", "tier1_ingestion_server.py"], capture_output=True)
        active = (cr.returncode == 0) or bool(health.get("stats"))
    except Exception:
        active = bool(health.get("stats"))

    stats = health.get("stats") if isinstance(health.get("stats"), dict) else {}
    timing_healthy = bool(health.get("timing_healthy", health.get("gps_locked", False)))
    sdr_health = health.get("sdr") if isinstance(health.get("sdr"), dict) else {}

    status["pipeline"] = {
        "active": active,
        "chrony_stratum": health.get("chrony_stratum"),
        "receiver_port": int(os.getenv("DSLV_RECEIVER_PORT", "5775")),
        "timing_healthy": timing_healthy,
        "primary_written": stats.get("primary_written", 0),
        "integrity_failed": stats.get("integrity_failed", 0),
        "min_nodes_required": int(os.getenv("DSLV_MIN_CONFIRMING_NODES", "4")),
    }

    status["sdr"] = {
        "mode": sdr_health.get("mode", GLOBAL_SDR_CONFIG.get("preset")),
        "active_device": GLOBAL_SDR_CONFIG["active_device"],
        "center_hz": GLOBAL_SDR_CONFIG["center_hz"],
        "reachable": bool(sdr_health.get("reachable", False)),
    }
    ups = health.get("ups") if isinstance(health.get("ups"), dict) else None
    status["ups"] = ups if ups else {"health": "absent"}

    registry = _load_registry_by_id()
    now = time.time()
    registered_node_cfgs = _load_registered_nodes()
    probed_nodes = []
    for nd in registered_node_cfgs:
        node_id = nd.get("node_id", "unknown")
        online, latency = _probe_node(nd.get("probe_url", f"http://{nd.get('ip', '')}:5173/"))
        last_seen = None
        entry = registry.get(node_id)
        if entry is None:
            for rid, rent in registry.items():
                if "mobile" in rid.lower() or "pixel" in rid.lower():
                    entry = rent
                    break
        if entry is not None:
            try:
                last_seen = float(entry.get("last_seen_utc") or 0.0) or None
            except (TypeError, ValueError):
                last_seen = None
        if not online and last_seen and (now - last_seen) <= 120:
            online = True
        probed_nodes.append({
            "node_id": node_id,
            "online": online,
            "probe_ms": latency,
            "last_seen_utc": last_seen,
            "last_seen_s": (now - last_seen) if last_seen else None,
        })
    telemetry_nodes = list(registry.values())
    status["nodes"] = {
        "registered_nodes": probed_nodes,
        "telemetry_nodes": telemetry_nodes,
    }

    registry_path = Path(os.getenv("DSLV_SECONDARY_OUTPUT_DIR", "./output/secondary")) / "node_registry.jsonl"
    secondary_log = Path(os.getenv("ZPDI_SECONDARY_LOG", "logs/tier1_secondary.jsonl"))
    status["mobile"] = collect_mobile_telemetry(
        os.getenv("DSLV_PIXEL_STATUS_URL") or None,
        registry_path,
        secondary_log,
        now=now,
    )
    return status


def create_app() -> Flask:
    if not FLASK_AVAILABLE:
        raise RuntimeError("Flask required.")

    app = Flask("dslv-zpdi-webdash")

    @app.route("/")
    def index():
        return _HTML, 200, {"Content-Type": "text/html; charset=utf-8"}

    @app.route("/api/status")
    def api_status():
        return jsonify(_get_status())

    @app.route("/api/sdr/config", methods=["POST"])
    def update_sdr_config():
        data = request.json
        if data:
            if "active_device" in data:
                GLOBAL_SDR_CONFIG["active_device"] = data["active_device"]
            if "center_hz" in data:
                GLOBAL_SDR_CONFIG["center_hz"] = data["center_hz"]
            if "demod_mode" in data:
                GLOBAL_SDR_CONFIG["demod_mode"] = data["demod_mode"]
        return jsonify({"status": "ok"})

    @app.route("/api/sdr/preset", methods=["POST"])
    def apply_preset():
        data = request.json
        preset = data.get("preset") if data else None
        presets = {
            "airband": {"hz": 120_000_000, "mode": "AM"},
            "marine": {"hz": 156_800_000, "mode": "WFM"},
            "weather": {"hz": 162_400_000, "mode": "NFM"},
            "adsb": {"hz": 1_090_000_000, "mode": "RAW"},
            "am_broadcast": {"hz": 1_000_000, "mode": "AM"},
            "fm_broadcast": {"hz": 98_100_000, "mode": "WFM"}
        }
        if preset in presets:
            GLOBAL_SDR_CONFIG["center_hz"] = presets[preset]["hz"]
            GLOBAL_SDR_CONFIG["demod_mode"] = presets[preset]["mode"]
        return jsonify({"status": "ok"})

    @app.route("/api/audio/stream")
    def audio_stream():
        # Simulated audio stream endpoint that would normally route samples from the demodulator
        # For now, it returns a 404 or a silent wav stream to satisfy the UI player
        import io
        import wave
        buf = io.BytesIO()
        with wave.open(buf, 'wb') as wav:
            wav.setnchannels(1)
            wav.setsampwidth(2)
            wav.setframerate(48000)
            wav.writeframes(b'\x00' * 48000 * 2) # 1 second of silence
        return Response(buf.getvalue(), mimetype="audio/wav")

    @app.route("/api/sdr/reboot", methods=["POST"])
    def reboot_sdr():
        logger.info(f"Soft rebooting SDR device: {GLOBAL_SDR_CONFIG['active_device']}")
        # In a real scenario, this might call USB reset or IIO device reset.
        # e.g., subprocess.run(["usbreset", "some-device"])
        return jsonify({"status": "rebooting"})

    @app.route("/api/system/shutdown", methods=["POST"])
    def sys_shutdown():
        # Unauthenticated LAN shutdown is forbidden. Opt-in from localhost only.
        if not _shutdown_allowed(request.remote_addr):
            logger.warning("Rejected dashboard shutdown from %s", request.remote_addr)
            return jsonify({"error": "shutdown disabled"}), 403
        logger.warning("System shutdown requested via web UI from localhost")
        try:
            subprocess.Popen(["sudo", "shutdown", "now", "-P"])
            return jsonify({"status": "shutting_down"})
        except Exception as e:
            return jsonify({"error": str(e)}), 500

    @app.route("/user_guide")
    def user_guide():
        # A simple route to display a local copy of the user guide
        return '''
        <html><head><style>body{background:#0b0f19;color:#e2e8f0;font-family:sans-serif;padding:20px;}</style></head>
        <body>
        <h1>DSLV-ZPDI Dashboard User Guide</h1>
        <p><b>System Panel</b>: View vital statistics of your Metrology Anchor Node. Host poweroff is disabled on the LAN dashboard (localhost + DSLV_WEBDASH_ALLOW_SHUTDOWN=1 only).</p>
        <p><b>Pipeline Panel</b>: Monitor data ingestion and timing synchronization health.</p>
        <p><b>SDR Hardware Panel</b>: Select active SDR hardware (PlutoSDR, LibreSDR, HackRF One). Apply tuning presets (Airband, Marine, WX) for fast demodulation, and soft-reboot the SDR if unresponsive.</p>
        </body></html>
        '''

    return app

def main() -> None:
    port = int(os.getenv("DSLV_WEBDASH_PORT", "8080"))
    host = os.getenv("DSLV_WEBDASH_HOST", "127.0.0.1")
    logging.basicConfig(level=logging.DEBUG)
    app = create_app()
    logger.info("DSLV-ZPDI interactive web dashboard starting on %s:%d", host, port)
    app.run(host=host, port=port, threaded=True)

if __name__ == "__main__":
    main()
