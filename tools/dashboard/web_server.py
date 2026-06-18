"""
DSLV-ZPDI Web Dashboard — remote telemetry view.

Serves a read-only HTML dashboard at http://<pi-ip>:8080/ that mirrors the
key metrics panels from the Rich TUI (system, pipeline, hardware, swarm node
status).  The page auto-refreshes every 5 seconds.

Run standalone:
    python -m dashboard.web_server

Or via systemd unit dslv-zpdi-webdash.service.

No authentication — intended for the shared LAN (10.128.24.x / PiRepo 10.42.0.x).
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
    from flask import Flask, Response

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
    """Pull node list from deployment.yaml registered block if available."""
    try:
        import yaml  # type: ignore
        cfg_path = Path(__file__).parents[2] / "config" / "deployment.yaml"
        if cfg_path.exists():
            with open(cfg_path) as f:
                cfg = yaml.safe_load(f)
            return cfg.get("nodes", {}).get("registered", [])
    except Exception:
        pass
    return _BUILTIN_NODES


# ── HTML template ─────────────────────────────────────────────────────────────

_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>DSLV-ZPDI Operations Dashboard</title>
<style>
  :root{--bg:#0d1117;--card:#161b22;--border:#30363d;--cyan:#58d5e8;
        --green:#3fb950;--yellow:#d29922;--red:#f85149;--dim:#8b949e}
  *{box-sizing:border-box;margin:0;padding:0}
  body{background:var(--bg);color:#e6edf3;font-family:'Courier New',monospace;
       font-size:13px;padding:12px}
  h1{color:var(--cyan);font-size:16px;margin-bottom:10px;letter-spacing:2px}
  .grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(280px,1fr));
        gap:10px;margin-bottom:10px}
  .card{background:var(--card);border:1px solid var(--border);border-radius:6px;
        padding:10px}
  .card h2{font-size:11px;text-transform:uppercase;letter-spacing:1px;
           color:var(--dim);margin-bottom:8px}
  .row{display:flex;justify-content:space-between;align-items:center;margin:3px 0;gap:8px}
  .label{color:var(--dim);white-space:nowrap}
  .val{font-weight:bold;text-align:right}
  .ok{color:var(--green)}.warn{color:var(--yellow)}.bad{color:var(--red)}
  .cyan{color:var(--cyan)}
  #ts{color:var(--dim);font-size:11px;margin-top:8px}
  .badge{display:inline-block;padding:1px 6px;border-radius:3px;font-size:11px;margin-left:4px}
  .badge-green{background:#1a3a1a;color:var(--green);border:1px solid var(--green)}
  .badge-yellow{background:#3a2e00;color:var(--yellow);border:1px solid var(--yellow)}
  .badge-red{background:#3a1a1a;color:var(--red);border:1px solid var(--red)}
  .node-card{border-color:var(--cyan)}
  .node-link{color:var(--cyan);text-decoration:none;font-size:11px}
  .node-link:hover{text-decoration:underline}
  hr{border:none;border-top:1px solid var(--border);margin:6px 0}
</style>
</head>
<body>
<h1>&#9632; DSLV-ZPDI OPERATIONS DASHBOARD</h1>
<div class="grid" id="panels">
  <div class="card" id="c-system"><h2>System</h2><p class="val cyan">Loading…</p></div>
  <div class="card" id="c-pipeline"><h2>Pipeline</h2><p class="val cyan">Loading…</p></div>
  <div class="card node-card" id="c-nodes"><h2>Swarm Nodes</h2><p class="val cyan">Loading…</p></div>
  <div class="card" id="c-sdr"><h2>SDR / HackRF</h2><p class="val cyan">Loading…</p></div>
</div>
<div id="ts">Last update: —</div>
<script>
function row(label,val,cls){
  return '<div class="row"><span class="label">'+label+'</span>'
        +'<span class="val '+(cls||'')+'">'+val+'</span></div>';
}
function badge(txt,ok,bad){
  var c = ok ? 'badge-green' : (bad ? 'badge-red' : 'badge-yellow');
  return '<span class="badge '+c+'">'+txt+'</span>';
}
async function refresh(){
  try{
    const r=await fetch('/api/status');
    if(!r.ok)return;
    const d=await r.json();
    const s=d.system||{};
    const p=d.pipeline||{};
    const n=d.nodes||{};
    const sdr=d.sdr||{};

    document.getElementById('c-system').innerHTML=
      '<h2>System</h2>'+
      row('Hostname',s.hostname||'?','cyan')+
      row('CPU',s.cpu_pct!=null?s.cpu_pct.toFixed(1)+'%':'?',s.cpu_pct>80?'bad':s.cpu_pct>60?'warn':'ok')+
      row('RAM',s.ram_pct!=null?s.ram_pct.toFixed(1)+'%':'?',s.ram_pct>85?'bad':s.ram_pct>70?'warn':'ok')+
      row('Temp',s.cpu_temp!=null?s.cpu_temp.toFixed(1)+'&deg;C':'?',s.cpu_temp>80?'bad':s.cpu_temp>70?'warn':'ok')+
      row('Uptime',s.uptime||'?')+
      row('Pi IP',s.pi_ip||'?','dim');

    document.getElementById('c-pipeline').innerHTML=
      '<h2>Pipeline</h2>'+
      row('Service',badge(p.active?'ACTIVE':'INACTIVE',p.active,!p.active))+
      row('Primary writes',p.primary_written??'?','ok')+
      row('Secondary logs',p.secondary_logged??'?','warn')+
      row('Integrity fails',p.integrity_failed??'?',p.integrity_failed>0?'bad':'ok')+
      row('Chrony stratum',p.chrony_stratum!=null?p.chrony_stratum:'?',
          p.chrony_stratum<=2?'ok':p.chrony_stratum<=5?'warn':'bad')+
      row('Receiver',':'+p.receiver_port,'dim');

    // ── Swarm nodes ─────────────────────────────────────────────────────────
    let nodeHtml='<h2>Swarm Nodes</h2>';

    // Tier 1 (this Pi)
    nodeHtml+='<div class="row"><span class="label">Pi 5 · Tier 1 Anchor</span>'
             +'<span class="val">'+badge('ONLINE',true,false)+'</span></div>';
    if(s.pi_ip) nodeHtml+=row('→ IP',s.pi_ip,'dim');

    nodeHtml+='<hr>';

    // Registered Tier 2 nodes (live-probed by the server)
    (n.registered_nodes||[]).forEach(function(nd){
      var online = nd.online;
      nodeHtml+='<div class="row"><span class="label">'+nd.node_id+'</span>'
               +'<span class="val">'+badge(online?'ONLINE':'OFFLINE',online,!online)+'</span></div>';
      nodeHtml+=row('→ Platform',nd.platform||'?','dim');
      nodeHtml+=row('→ IP',nd.ip,'dim');
      if(online && nd.probe_ms!=null)
        nodeHtml+=row('→ Latency',nd.probe_ms+'ms',nd.probe_ms<50?'ok':nd.probe_ms<200?'warn':'bad');
      if(nd.dashboard_url){
        nodeHtml+='<div class="row"><span class="label">→ Dashboard</span>'
                 +'<span class="val"><a class="node-link" href="'+nd.dashboard_url
                 +'" target="_blank">open ↗</a></span></div>';
      }
    });

    // Telemetry-posting nodes (seen via ingest endpoint)
    var telNodes = n.telemetry_nodes||[];
    if(telNodes.length){
      nodeHtml+='<hr>';
      telNodes.forEach(function(nd){
        nodeHtml+=row(nd.node_id,badge(nd.online?'ONLINE':'STALE',nd.online,false));
        if(nd.last_seen_s!=null) nodeHtml+=row('→ last POST',nd.last_seen_s.toFixed(0)+'s ago','dim');
      });
    }

    document.getElementById('c-nodes').innerHTML=nodeHtml;

    document.getElementById('c-sdr').innerHTML=
      '<h2>SDR / HackRF</h2>'+
      row('Mode',badge(sdr.mode||'SIM',sdr.mode==='REAL',false))+
      row('Center',sdr.center_hz!=null?(sdr.center_hz/1e6).toFixed(3)+' MHz':'?','cyan')+
      row('Amp','LOCKED OUT (blown — parts on order)','bad')+
      row('Clock src',sdr.clock_src||'?',sdr.clock_src==='external'?'ok':'warn');

    document.getElementById('ts').textContent=
      'Last update: '+new Date().toUTCString();
  }catch(e){console.warn('refresh failed',e)}
}
refresh();
setInterval(refresh,5000);
</script>
</body>
</html>"""


# ── Node liveness probe ───────────────────────────────────────────────────────

def _probe_node(probe_url: str, timeout: float = 3.0) -> tuple[bool, int | None]:
    """HTTP GET probe. Returns (online, latency_ms)."""
    try:
        parsed = urlparse(probe_url)
        if parsed.scheme not in {"http", "https"}:
            return False, None
        t0 = time.monotonic()
        req = urllib.request.Request(probe_url, method="GET")
        with urllib.request.urlopen(req, timeout=timeout) as resp:  # nosec B310
            resp.read(64)
        ms = int((time.monotonic() - t0) * 1000)
        return True, ms
    except Exception:
        return False, None


# ── Status data collector ─────────────────────────────────────────────────────

def _get_pi_ip() -> str:
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("10.128.24.1", 80))
        return s.getsockname()[0]
    except Exception:
        return "?"


def _get_status() -> dict:
    status: dict = {}

    # System
    try:
        import psutil  # type: ignore
        vm = psutil.virtual_memory()
        temps = psutil.sensors_temperatures() or {}
        cpu_temp = None
        for key in ("cpu_thermal", "cpu-thermal", "coretemp"):
            if key in temps and temps[key]:
                cpu_temp = temps[key][0].current
                break
        uptime_s = time.time() - psutil.boot_time()
        h, rem = divmod(int(uptime_s), 3600)
        m, s = divmod(rem, 60)
        status["system"] = {
            "hostname": socket.gethostname(),
            "pi_ip": _get_pi_ip(),
            "cpu_pct": psutil.cpu_percent(interval=None),
            "ram_pct": vm.percent,
            "cpu_temp": cpu_temp,
            "uptime": f"{h}h {m}m {s}s",
        }
    except Exception:
        status["system"] = {"hostname": "?", "pi_ip": _get_pi_ip()}

    # Pipeline service state
    try:
        result = subprocess.run(
            ["systemctl", "is-active", "dslv-zpdi"],
            capture_output=True, text=True, timeout=3, check=False,
        )
        active = result.stdout.strip() == "active"
    except Exception:
        active = False

    # Chrony stratum
    chrony_stratum = 99
    try:
        cr = subprocess.run(
            ["chronyc", "tracking"],
            capture_output=True, text=True, timeout=3, check=False,
        )
        for line in cr.stdout.splitlines():
            if "Stratum" in line:
                chrony_stratum = int(line.split(":")[-1].strip())
                break
    except Exception:
        pass

    # HDF5 writer stats
    stats_path = os.path.join(
        os.getenv("DSLV_PRIMARY_OUTPUT_DIR", "./output/primary"), ".stats.json"
    )
    hdf5_stats: dict = {}
    try:
        if os.path.exists(stats_path):
            with open(stats_path) as f:
                hdf5_stats = json.load(f)
    except Exception:
        pass

    receiver_port = int(os.getenv("DSLV_RECEIVER_PORT", "5775"))
    status["pipeline"] = {
        "active": active,
        "chrony_stratum": chrony_stratum,
        "receiver_port": receiver_port,
        **hdf5_stats,
    }

    # ── Registered nodes — live-probe each one ────────────────────────────────
    registered_node_cfgs = _load_registered_nodes()
    probed_nodes = []
    for nd in registered_node_cfgs:
        probe_url = nd.get("probe_url", f"http://{nd.get('ip', '')}:5173/")
        online, latency_ms = _probe_node(probe_url)
        probed_nodes.append({
            "node_id": nd.get("node_id", "unknown"),
            "ip": nd.get("ip", "?"),
            "platform": nd.get("platform", "?"),
            "description": nd.get("description", ""),
            "dashboard_url": nd.get("probe_url", ""),
            "online": online,
            "probe_ms": latency_ms,
        })

    # ── Telemetry-posting nodes — seen via the ingest log ────────────────────
    telemetry_nodes: list = []
    node_reg_path = os.path.join(
        os.getenv("DSLV_SECONDARY_OUTPUT_DIR", "./output/secondary"), "node_registry.jsonl"
    )
    try:
        if os.path.exists(node_reg_path):
            seen: dict = {}
            with open(node_reg_path) as f:
                for line in f:
                    try:
                        entry = json.loads(line)
                        seen[entry.get("node_id", "?")] = entry
                    except Exception:
                        pass
            now = time.time()
            for nid, entry in seen.items():
                last = entry.get("last_seen_utc", 0)
                telemetry_nodes.append({
                    "node_id": nid,
                    "online": (now - last) < 60,
                    "last_seen_s": now - last,
                })
    except Exception:
        pass

    status["nodes"] = {
        "tier1": True,
        "registered_nodes": probed_nodes,
        "telemetry_nodes": telemetry_nodes,
    }

    # SDR state
    sdr_env_path = os.path.join(
        os.getenv("DSLV_PRIMARY_OUTPUT_DIR", "./output/primary"), ".sdr_state.json"
    )
    sdr_state: dict = {"mode": "REAL", "center_hz": 100_000_000, "clock_src": "external"}
    try:
        if os.path.exists(sdr_env_path):
            with open(sdr_env_path) as f:
                sdr_state.update(json.load(f))
    except Exception:
        pass
    status["sdr"] = sdr_state

    return status


# ── Node receiver passthrough — register telemetry POST from mobile node ──────

def _register_node_seen(node_id: str) -> None:
    """Write/update a line in node_registry.jsonl so the dashboard can track it."""
    reg_path = os.path.join(
        os.getenv("DSLV_SECONDARY_OUTPUT_DIR", "./output/secondary"), "node_registry.jsonl"
    )
    try:
        os.makedirs(os.path.dirname(reg_path), exist_ok=True)
        lines: dict = {}
        if os.path.exists(reg_path):
            with open(reg_path) as f:
                for line in f:
                    try:
                        e = json.loads(line)
                        lines[e.get("node_id", "?")] = e
                    except Exception:
                        pass
        lines[node_id] = {"node_id": node_id, "last_seen_utc": time.time()}
        with open(reg_path, "w") as f:
            for entry in lines.values():
                f.write(json.dumps(entry) + "\n")
    except Exception as exc:
        logger.warning("node registry update failed: %s", exc)


# ── Flask application ─────────────────────────────────────────────────────────

def create_app() -> Flask:
    if not FLASK_AVAILABLE:
        raise RuntimeError("flask is required for the web dashboard (pip install flask)")

    app = Flask("dslv-zpdi-webdash")

    @app.route("/")
    def index():
        return _HTML, 200, {"Content-Type": "text/html; charset=utf-8"}

    @app.route("/api/status")
    def api_status():
        return Response(
            json.dumps(_get_status()),
            mimetype="application/json",
        )

    @app.route("/api/node_seen/<node_id>", methods=["POST"])
    def node_seen(node_id: str):
        """Lightweight heartbeat endpoint — mobile nodes can POST here to register."""
        _register_node_seen(node_id)
        return Response(json.dumps({"ok": True}), mimetype="application/json")

    return app


def main() -> None:
    port = int(os.getenv("DSLV_WEBDASH_PORT", "8080"))
    host = os.getenv("DSLV_WEBDASH_HOST", "127.0.0.1")
    logging.basicConfig(level=logging.INFO)
    app = create_app()
    logger.info("DSLV-ZPDI web dashboard starting on %s:%d", host, port)
    app.run(host=host, port=port, threaded=True)


if __name__ == "__main__":
    main()
