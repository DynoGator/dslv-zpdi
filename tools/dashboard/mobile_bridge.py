"""Bridge thread to poll Pixel 9 status endpoint and local tier-1 secondary logs,
updating the TUI MobilePanel dynamically.
"""

import json
import logging
import os
import threading
import time
import urllib.request
from pathlib import Path

log = logging.getLogger(__name__)


class MobileBridge(threading.Thread):
    def __init__(self, mobile_panel, poll_interval: float = 5.0):
        super().__init__(daemon=True, name="mobile-bridge")
        self.mobile_panel = mobile_panel
        self.poll_interval = poll_interval
        self._stop_event = threading.Event()

        self.status_url = os.getenv(
            "DSLV_PIXEL_STATUS_URL", "http://10.29.134.63:8080/api/status"
        )
        self.registry_path = Path(
            os.getenv("DSLV_NODE_REGISTRY", "output/secondary/node_registry.jsonl")
        )
        self.secondary_log_path = Path(
            os.getenv("ZPDI_SECONDARY_LOG", "logs/tier1_secondary.jsonl")
        )

    def stop(self):
        self._stop_event.set()

    def run(self):
        while not self._stop_event.is_set():
            try:
                telem = self._fetch_telemetry()
                if telem:
                    self.mobile_panel.update(telem)
            except Exception as exc:
                log.debug("MobileBridge fetch error: %s", exc)
            self._stop_event.wait(self.poll_interval)

    def _fetch_telemetry(self) -> dict:
        now = time.time()
        telem = {
            "node_id": "dslv-zpdi/mobile-tier2",
            "timestamp_utc": 0.0,
            "online": False,
            "trust_score": 0.0,
            "trust_flags": [],
            "magnetometer_ut": None,
            "gps": {},
            "camera_frame_hash": "",
        }

        # 1. Poll Phone status URL
        phone_reachable = False
        try:
            req = urllib.request.Request(self.status_url, headers={"User-Agent": "DSLV-TUI/1.0"})
            with urllib.request.urlopen(req, timeout=2.5) as resp:
                if resp.status == 200:
                    data = json.loads(resp.read().decode("utf-8"))
                    phone_reachable = True
                    nodes = data.get("nodes", {})
                    telem_nodes = nodes.get("telemetry_nodes", [])
                    for node in telem_nodes:
                        if "mobile" in node.get("node_id", ""):
                            last_seen_s = node.get("last_seen_s", 999)
                            if last_seen_s < 120:
                                telem["timestamp_utc"] = max(telem["timestamp_utc"], now - last_seen_s)
                                telem["online"] = True
        except Exception:
            phone_reachable = False

        # 2. Check local Pi node_registry.jsonl
        if self.registry_path.exists():
            try:
                with open(self.registry_path, "r", encoding="utf-8") as f:
                    for line in f:
                        line = line.strip()
                        if not line:
                            continue
                        entry = json.loads(line)
                        if entry.get("node_id") == "dslv-zpdi/mobile-tier2":
                            ts = float(entry.get("last_seen_utc", 0.0))
                            if ts > telem["timestamp_utc"]:
                                telem["timestamp_utc"] = ts
            except Exception:
                pass

        # 3. Check latest tier1_secondary.jsonl packet
        if self.secondary_log_path.exists():
            try:
                with open(self.secondary_log_path, "rb") as f:
                    # Seek near end to read last line
                    f.seek(0, os.SEEK_END)
                    size = f.tell()
                    buffer_size = min(4096, size)
                    if buffer_size > 0:
                        f.seek(size - buffer_size)
                        lines = f.read().decode("utf-8", errors="ignore").strip().splitlines()
                        if lines:
                            last_line = lines[-1]
                            pkt = json.loads(last_line)
                            pkt_ts = pkt.get("timestamp_utc") or pkt.get("time") or 0.0
                            if pkt_ts > telem["timestamp_utc"]:
                                telem["timestamp_utc"] = pkt_ts
                            if "r_smooth" in pkt:
                                telem["trust_score"] = float(pkt["r_smooth"])
                            if "gps_fix" in pkt and isinstance(pkt["gps_fix"], dict):
                                telem["gps"] = pkt["gps_fix"]
                            if "magnetometer_ut" in pkt:
                                telem["magnetometer_ut"] = pkt["magnetometer_ut"]
                            if "camera_frame_hash" in pkt:
                                telem["camera_frame_hash"] = pkt["camera_frame_hash"]
            except Exception:
                pass

        # Build flags & online determination
        age_s = now - telem["timestamp_utc"] if telem["timestamp_utc"] > 0 else 9999
        if age_s <= 60:
            telem["online"] = True
            telem["trust_flags"].append("LIVE UPLINK")
        elif phone_reachable:
            telem["online"] = True
            telem["trust_flags"].append("PHONE ALIVE")
            if telem["timestamp_utc"] == 0.0:
                telem["timestamp_utc"] = now
        else:
            telem["online"] = False
            telem["trust_flags"].append("OFF GRID")

        return telem
