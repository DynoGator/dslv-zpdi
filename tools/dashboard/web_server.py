"""
DSLV-ZPDI Web Dashboard — remote telemetry view.

Serves a read-only HTML dashboard at http://<pi-ip>:8080/ that mirrors the
key metrics panels from the Rich TUI (system, pipeline, hardware, swarm node
status).  The page auto-refreshes every 5 seconds via SSE or polling.

Run standalone:
    python -m dashboard.web_server

Or via systemd unit dslv-zpdi-webdash.service.

No authentication — intended for the PiRepo LAN (10.42.0.x) only.
"""

from __future__ import annotations

import json
import logging
import os
import subprocess
import time

try:
    from flask import Flask, Response, render_template_string, stream_with_context

    FLASK_AVAILABLE = True
except ImportError:
    FLASK_AVAILABLE = False

logger = logging.getLogger("dslv-zpdi.webdash")

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
  .row{display:flex;justify-content:space-between;margin:3px 0}
  .label{color:var(--dim)}
  .val{font-weight:bold}
  .ok{color:var(--green)}.warn{color:var(--yellow)}.bad{color:var(--red)}
  .cyan{color:var(--cyan)}
  #ts{color:var(--dim);font-size:11px;margin-top:8px}
  .badge{display:inline-block;padding:1px 6px;border-radius:3px;font-size:11px;
         margin-left:4px}
  .badge-green{background:#1a3a1a;color:var(--green);border:1px solid var(--green)}
  .badge-yellow{background:#3a2e00;color:var(--yellow);border:1px solid var(--yellow)}
</style>
</head>
<body>
<h1>&#9632; DSLV-ZPDI OPERATIONS DASHBOARD</h1>
<div class="grid" id="panels">
  <div class="card" id="c-system"><h2>System</h2><p class="val cyan">Loading…</p></div>
  <div class="card" id="c-pipeline"><h2>Pipeline</h2><p class="val cyan">Loading…</p></div>
  <div class="card" id="c-nodes"><h2>Swarm Nodes</h2><p class="val cyan">Loading…</p></div>
  <div class="card" id="c-sdr"><h2>SDR / HackRF</h2><p class="val cyan">Loading…</p></div>
</div>
<div id="ts">Last update: —</div>
<script>
function row(label,val,cls){
  return '<div class="row"><span class="label">'+label+'</span>'
        +'<span class="val '+(cls||'')+'">'+val+'</span></div>';
}
function badge(txt,ok){
  return '<span class="badge '+(ok?'badge-green':'badge-yellow')+'">'+txt+'</span>';
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
      row('Temp',s.cpu_temp!=null?s.cpu_temp.toFixed(1)+'°C':'?',s.cpu_temp>80?'bad':s.cpu_temp>70?'warn':'ok')+
      row('Uptime',s.uptime||'?');

    document.getElementById('c-pipeline').innerHTML=
      '<h2>Pipeline</h2>'+
      row('Service',badge(p.active?'ACTIVE':'INACTIVE',p.active))+
      row('Primary writes',p.primary_written??'?','ok')+
      row('Secondary logs',p.secondary_logged??'?','warn')+
      row('Integrity fails',p.integrity_failed??'?',p.integrity_failed>0?'bad':'ok')+
      row('Chrony stratum',p.chrony_stratum!=null?p.chrony_stratum:'?',
          p.chrony_stratum<=2?'ok':p.chrony_stratum<=5?'warn':'bad');

    let nodeHtml='<h2>Swarm Nodes</h2>';
    if(n.tier1){
      nodeHtml+=row('Tier1 Anchor',badge('ONLINE',true));
    }
    (n.mobile_nodes||[]).forEach(function(nd){
      nodeHtml+=row(nd.node_id||'mobile',badge('ONLINE',nd.online));
      if(nd.last_seen_s!=null) nodeHtml+=row('→ last seen',nd.last_seen_s.toFixed(0)+'s ago');
    });
    if(!(n.mobile_nodes||[]).length) nodeHtml+=row('Mobile nodes','none','warn');
    document.getElementById('c-nodes').innerHTML=nodeHtml;

    document.getElementById('c-sdr').innerHTML=
      '<h2>SDR / HackRF</h2>'+
      row('Mode',badge(sdr.mode||'SIM',sdr.mode==='REAL'))+
      row('Center',sdr.center_hz!=null?(sdr.center_hz/1e6).toFixed(3)+' MHz':'?','cyan')+
      row('Amp','LOCKED OUT (blown — parts on order)','bad')+
      row('Clock src',sdr.clock_src||'?',sdr.clock_src==='external'?'ok':'warn');

    document.getElementById('ts').textContent=
      'Last update: '+new Date().toUTCString()+
      (d.receiver_port?' | receiver on :'+d.receiver_port:'');
  }catch(e){console.warn('refresh failed',e)}
}
refresh();
setInterval(refresh,5000);
</script>
</body>
</html>"""


# ── Status data collector ─────────────────────────────────────────────────────

def _get_status() -> dict:
    import socket
    status: dict = {}

    # System
    try:
        import psutil
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
            "cpu_pct": psutil.cpu_percent(interval=None),
            "ram_pct": vm.percent,
            "cpu_temp": cpu_temp,
            "uptime": f"{h}h {m}m {s}s",
        }
    except Exception:
        status["system"] = {"hostname": "?"}

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

    # HDF5 writer stats from latest stats file (written by pipeline)
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

    status["pipeline"] = {
        "active": active,
        "chrony_stratum": chrony_stratum,
        **hdf5_stats,
    }

    # Node registry — read from secondary dir node-registry.jsonl if present
    mobile_nodes: list = []
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
                mobile_nodes.append({
                    "node_id": nid,
                    "online": (now - last) < 60,
                    "last_seen_s": now - last,
                })
    except Exception:
        pass

    status["nodes"] = {"tier1": True, "mobile_nodes": mobile_nodes}

    # SDR state from env file written by pipeline/dashboard
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
    status["receiver_port"] = int(os.getenv("DSLV_RECEIVER_PORT", "5775"))

    return status


# ── Flask application ─────────────────────────────────────────────────────────

def create_app() -> "Flask":
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

    return app


def main() -> None:
    port = int(os.getenv("DSLV_WEBDASH_PORT", "8080"))
    logging.basicConfig(level=logging.INFO)
    app = create_app()
    logger.info("DSLV-ZPDI web dashboard starting on 0.0.0.0:%d", port)
    app.run(host="0.0.0.0", port=port, threaded=True)


if __name__ == "__main__":
    main()
