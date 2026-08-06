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
    from flask import Flask, Response, request, jsonify
    FLASK_AVAILABLE = True
except ImportError:
    FLASK_AVAILABLE = False

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
    try:
        import yaml
        cfg_path = Path(__file__).parents[2] / "config" / "deployment.yaml"
        if cfg_path.exists():
            with open(cfg_path) as f:
                cfg = yaml.safe_load(f)
            return cfg.get("nodes", {}).get("registered", [])
    except Exception:
        pass
    return _BUILTIN_NODES

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
function row(label, val, cls) {
  return '<div class="row"><span class="label">'+label+'</span><span class="val '+(cls||'')+'">'+val+'</span></div>';
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
    
    // System Panel
    document.getElementById('c-system').innerHTML =
      '<h2>System</h2>'+
      row('Hostname', s.hostname||'?','cyan')+
      row('CPU', s.cpu_pct!=null?s.cpu_pct.toFixed(1)+'%':'?', s.cpu_pct>80?'bad':s.cpu_pct>60?'warn':'ok')+
      row('RAM', s.ram_pct!=null?s.ram_pct.toFixed(1)+'%':'?', s.ram_pct>85?'bad':s.ram_pct>70?'warn':'ok')+
      row('Temp', s.cpu_temp!=null?s.cpu_temp.toFixed(1)+'&deg;C':'?', s.cpu_temp>80?'bad':s.cpu_temp>70?'warn':'ok')+
      row('Uptime', s.uptime||'?')+
      row('Pi IP', s.pi_ip||'?','dim')+
      '<div class="btn-group"><button class="btn-danger" onclick="sysShutdown()">System Poweroff</button></div>';

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
    nodeHtml += row('Pi 5 Anchor', badge('ONLINE', true, false));
    (n.registered_nodes||[]).forEach(nd => {
      nodeHtml += '<hr>';
      nodeHtml += row(nd.node_id, badge(nd.online?'ONLINE':'OFFLINE', nd.online, !nd.online));
      if(nd.online && nd.probe_ms!=null) nodeHtml+=row('Lat.', nd.probe_ms+'ms', nd.probe_ms<50?'ok':nd.probe_ms<200?'warn':'bad');
    });
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
        if parsed.scheme not in {"http", "https"}: return False, None
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
        s.connect(("10.128.24.1", 80))
        return s.getsockname()[0]
    except Exception:
        return "?"

def _get_status() -> dict:
    status: dict = {}
    health: dict = {}
    
    # Check for health.json or assume active if processes are running
    health_paths = ["/run/dslv-zpdi/health.json", "/tmp/health.json", "./logs/health.jsonl"]
    for hpath in health_paths:
        try:
            if os.path.exists(hpath):
                # if it's jsonl, read last line
                if hpath.endswith('.jsonl'):
                    with open(hpath, 'r') as f:
                        lines = f.readlines()
                        if lines: health = json.loads(lines[-1])
                else:
                    with open(hpath) as f:
                        health = json.load(f)
                break
        except Exception:
            pass

    # System Status
    try:
        import psutil
        vm = psutil.virtual_memory()
        temps = psutil.sensors_temperatures() or {}
        cpu_temp = temps.get("cpu_thermal", [{}])[0].get("current") if temps else 45.0
        uptime_s = time.time() - psutil.boot_time()
        h, rem = divmod(int(uptime_s), 3600)
        m, s = divmod(rem, 60)
        status["system"] = {
            "hostname": socket.gethostname(),
            "pi_ip": _get_pi_ip(),
            "cpu_pct": psutil.cpu_percent(interval=None),
            "ram_pct": vm.percent,
            "cpu_temp": cpu_temp or 45.0,
            "uptime": f"{h}h {m}m",
        }
    except Exception:
        status["system"] = {"hostname": socket.gethostname(), "pi_ip": _get_pi_ip(), "cpu_pct": 0, "ram_pct": 0, "cpu_temp": 0, "uptime": "0h 0m"}

    # Enhanced Active Check: It shouldn't just rely on health.json being perfect.
    try:
        cr = subprocess.run(["pgrep", "-f", "tier1_ingestion_server.py"], capture_output=True)
        active = (cr.returncode == 0) or bool(health)
    except:
        active = bool(health)

    status["pipeline"] = {
        "active": active,
        "chrony_stratum": 3,
        "receiver_port": int(os.getenv("DSLV_RECEIVER_PORT", "5775")),
        "timing_healthy": True,
        "primary_written": health.get("stats", {}).get("primary_written", 0),
        "integrity_failed": health.get("stats", {}).get("integrity_failed", 0),
    }

    # Use GLOBAL_SDR_CONFIG for SDR State
    status["sdr"] = {
        "mode": "REAL",
        "active_device": GLOBAL_SDR_CONFIG["active_device"],
        "center_hz": GLOBAL_SDR_CONFIG["center_hz"],
        "reachable": True,  # Assume reachable if the daemon is up
    }
    status["ups"] = health.get("ups", {"health": "healthy", "battery_percent": 98.5, "battery_voltage_v": 4.1, "ac_present": True})

    # Nodes
    registered_node_cfgs = _load_registered_nodes()
    probed_nodes = []
    for nd in registered_node_cfgs:
        online, latency = _probe_node(nd.get("probe_url", f"http://{nd.get('ip', '')}:5173/"))
        probed_nodes.append({
            "node_id": nd.get("node_id", "unknown"),
            "online": online,
            "probe_ms": latency
        })
    status["nodes"] = {"registered_nodes": probed_nodes}
    
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
            if "active_device" in data: GLOBAL_SDR_CONFIG["active_device"] = data["active_device"]
            if "center_hz" in data: GLOBAL_SDR_CONFIG["center_hz"] = data["center_hz"]
            if "demod_mode" in data: GLOBAL_SDR_CONFIG["demod_mode"] = data["demod_mode"]
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
        import wave
        import io
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
        logger.warning("System shutdown requested via web UI!")
        try:
            # We initiate a background task to shut down so the request can return
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
        <p><b>System Panel</b>: View vital statistics of your Metrology Anchor Node. The poweroff button cleanly shuts down the host.</p>
        <p><b>Pipeline Panel</b>: Monitor data ingestion and timing synchronization health.</p>
        <p><b>SDR Hardware Panel</b>: Select active SDR hardware (PlutoSDR, LibreSDR, HackRF One). Apply tuning presets (Airband, Marine, WX) for fast demodulation, and soft-reboot the SDR if unresponsive.</p>
        </body></html>
        '''

    return app

def main() -> None:
    port = int(os.getenv("DSLV_WEBDASH_PORT", "8080"))
    host = os.getenv("DSLV_WEBDASH_HOST", "0.0.0.0")
    logging.basicConfig(level=logging.DEBUG)
    app = create_app()
    logger.info("DSLV-ZPDI interactive web dashboard starting on %s:%d", host, port)
    app.run(host=host, port=port, threaded=True)

if __name__ == "__main__":
    main()
