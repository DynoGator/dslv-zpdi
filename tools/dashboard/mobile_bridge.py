"""Bridge thread to poll Pixel 9 status endpoint and local tier-1 secondary logs,
updating the TUI MobilePanel dynamically.
"""

from __future__ import annotations

import json
import logging
import os
import threading
import time
import urllib.request
from pathlib import Path
from urllib.parse import urlparse

log = logging.getLogger(__name__)

_MOBILE_NODE_HINTS = ("mobile", "pixel", "-t2", "tier2", "tier-2")


def _is_mobile_node_id(node_id: str) -> bool:
    n = (node_id or "").lower()
    return any(h in n for h in _MOBILE_NODE_HINTS)


def load_registered_nodes() -> list[dict]:
    """Load registered swarm nodes from config/deployment.yaml if present."""
    try:
        import yaml

        cfg_path = Path(__file__).resolve().parents[2] / "config" / "deployment.yaml"
        if cfg_path.exists():
            with open(cfg_path, encoding="utf-8") as f:
                cfg = yaml.safe_load(f) or {}
            registered = (cfg.get("nodes") or {}).get("registered") or []
            if isinstance(registered, list):
                return [n for n in registered if isinstance(n, dict)]
    except Exception:
        log.debug("registered-node load failed", exc_info=True)
    return []


def _default_pixel_status_url() -> str | None:
    env = os.getenv("DSLV_PIXEL_STATUS_URL", "").strip()
    if env:
        return env
    for nd in load_registered_nodes():
        url = nd.get("dashboard_url") or nd.get("status_url") or nd.get("probe_url")
        if url:
            return str(url)
    return None


def _read_last_json_object(path: Path, tail_bytes: int = 65536) -> dict | None:
    """Return the last complete JSON object from a JSONL file, or None."""
    try:
        if not path.exists():
            return None
        with open(path, "rb") as f:
            f.seek(0, os.SEEK_END)
            size = f.tell()
            if size <= 0:
                return None
            buf = min(tail_bytes, size)
            f.seek(size - buf)
            data = f.read().decode("utf-8", errors="ignore")
        for line in reversed(data.splitlines()):
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
            except json.JSONDecodeError:
                continue
            if isinstance(obj, dict):
                return obj
    except OSError:
        log.debug("jsonl tail read failed for %s", path, exc_info=True)
    return None


def coerce_magnetometer(value) -> list[float] | None:
    """Normalize mag samples from list, tuple, or {x,y,z}/{values:[...]}."""
    if value is None:
        return None
    if isinstance(value, dict):
        if isinstance(value.get("values"), (list, tuple)):
            value = value["values"]
        elif all(k in value for k in ("x", "y", "z")):
            value = [value["x"], value["y"], value["z"]]
        else:
            return None
    try:
        seq = list(value)
    except TypeError:
        return None
    if len(seq) != 3:
        return None
    try:
        return [float(seq[0]), float(seq[1]), float(seq[2])]
    except (TypeError, ValueError):
        return None


def coerce_gps(pkt: dict) -> dict:
    """Normalize gps / gps_fix / lat-lon fields into {lat, lon, alt, accuracy}."""
    gps = pkt.get("gps") if isinstance(pkt.get("gps"), dict) else {}
    if not gps and isinstance(pkt.get("gps_fix"), dict):
        gps = pkt["gps_fix"]
    extras = pkt.get("swarm_extras") if isinstance(pkt.get("swarm_extras"), dict) else {}
    raw = pkt.get("raw_value") if isinstance(pkt.get("raw_value"), dict) else {}
    raw_gps = raw.get("gps") if isinstance(raw.get("gps"), dict) else {}

    def _pick(*keys):
        for src in (gps, raw_gps, extras, raw, pkt):
            for k in keys:
                if src.get(k) is not None:
                    return src.get(k)
        return None

    lat = _pick("lat", "latitude")
    lon = _pick("lon", "longitude")
    alt = _pick("alt", "altitude")
    acc = _pick("accuracy")
    out: dict = {}
    try:
        if lat is not None:
            out["lat"] = float(lat)
    except (TypeError, ValueError):
        pass
    try:
        if lon is not None:
            out["lon"] = float(lon)
    except (TypeError, ValueError):
        pass
    try:
        if alt is not None:
            out["alt"] = float(alt)
    except (TypeError, ValueError):
        pass
    try:
        if acc is not None:
            out["accuracy"] = float(acc)
    except (TypeError, ValueError):
        pass
    return out


def _extract_sample_fields(pkt: dict, telem: dict) -> None:
    """Copy mag/gps/hash/trust from a packet dict into telem (in place)."""
    mag_val = pkt.get("magnetometer_ut")
    if mag_val is None and isinstance(pkt.get("raw_value"), dict):
        mag_val = pkt["raw_value"].get("magnetometer_ut")
    mag = coerce_magnetometer(mag_val)
    if mag is not None:
        telem["magnetometer_ut"] = mag
    gps = coerce_gps(pkt)
    if gps:
        telem["gps"] = gps
    cam = pkt.get("camera_frame_hash")
    if not cam and isinstance(pkt.get("raw_value"), dict):
        cam = pkt["raw_value"].get("camera_frame_hash")
    if cam:
        telem["camera_frame_hash"] = cam
    if "r_smooth" in pkt:
        try:
            telem["trust_score"] = float(pkt["r_smooth"])
        except (TypeError, ValueError):
            pass
    if "trust_score" in pkt:
        try:
            telem["trust_score"] = float(pkt["trust_score"])
        except (TypeError, ValueError):
            pass


def collect_mobile_telemetry(
    status_url: str | None,
    registry_path: Path,
    secondary_log_path: Path,
    now: float | None = None,
) -> dict:
    """Assemble a MobilePanel telemetry dict from HTTP + local sinks.

    Online is determined from actual last-seen timestamps, not from a bare
    HTTP 200 on an unrelated dashboard.
    """
    now = time.time() if now is None else now
    telem = {
        "node_id": "dslv-zpdi/mobile-tier2",
        "timestamp_utc": 0.0,
        "online": False,
        "trust_score": 0.0,
        "trust_flags": [],
        "magnetometer_ut": None,
        "gps": {},
        "camera_frame_hash": "",
        "phone_reachable": False,
    }

    phone_reachable = False
    phone_has_sample = False
    if status_url:
        try:
            parsed = urlparse(status_url)
            if parsed.scheme in {"http", "https"}:
                req = urllib.request.Request(
                    status_url, headers={"User-Agent": "DSLV-TUI/1.0", "Accept": "application/json"}
                )
                with urllib.request.urlopen(req, timeout=2.5) as resp:  # nosec B310
                    if resp.status == 200:
                        raw_body = resp.read().decode("utf-8")
                        try:
                            data = json.loads(raw_body)
                        except json.JSONDecodeError:
                            data = None
                        if isinstance(data, dict):
                            phone_reachable = True
                            nodes = data.get("nodes") if isinstance(data.get("nodes"), dict) else {}
                            node_lists = []
                            for key in ("telemetry_nodes", "registered_nodes"):
                                lst = nodes.get(key)
                                if isinstance(lst, list):
                                    node_lists.extend(lst)
                            for node in node_lists:
                                if not isinstance(node, dict):
                                    continue
                                if not _is_mobile_node_id(str(node.get("node_id", ""))):
                                    continue
                                last_seen_s = node.get("last_seen_s")
                                last_seen_utc = node.get("last_seen_utc")
                                if last_seen_utc:
                                    try:
                                        telem["timestamp_utc"] = max(
                                            telem["timestamp_utc"], float(last_seen_utc)
                                        )
                                        phone_has_sample = True
                                    except (TypeError, ValueError):
                                        pass
                                elif last_seen_s is not None:
                                    try:
                                        age = float(last_seen_s)
                                        telem["timestamp_utc"] = max(
                                            telem["timestamp_utc"], now - age
                                        )
                                        phone_has_sample = True
                                    except (TypeError, ValueError):
                                        pass
                                if node.get("online"):
                                    phone_has_sample = True
                            if data.get("magnetometer_ut") or data.get("gps") or data.get("gps_fix"):
                                _extract_sample_fields(data, telem)
                                ts = data.get("timestamp_utc") or data.get("ts_utc")
                                if ts:
                                    try:
                                        telem["timestamp_utc"] = max(
                                            telem["timestamp_utc"], float(ts)
                                        )
                                        phone_has_sample = True
                                    except (TypeError, ValueError):
                                        pass
                            last_sample_ts = data.get("last_sample_ts")
                            if last_sample_ts:
                                try:
                                    ts = float(last_sample_ts)
                                    # health endpoint uses wall_ns
                                    if ts > 1e12:
                                        ts = ts / 1e9
                                    telem["timestamp_utc"] = max(telem["timestamp_utc"], ts)
                                    phone_has_sample = True
                                except (TypeError, ValueError):
                                    pass
        except Exception:
            phone_reachable = False

    telem["phone_reachable"] = phone_reachable

    if registry_path.exists():
        try:
            with open(registry_path, encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        entry = json.loads(line)
                    except json.JSONDecodeError:
                        continue
                    if not isinstance(entry, dict):
                        continue
                    if not _is_mobile_node_id(str(entry.get("node_id", ""))):
                        continue
                    ts = float(entry.get("last_seen_utc", 0.0) or 0.0)
                    if ts > telem["timestamp_utc"]:
                        telem["timestamp_utc"] = ts
                        telem["node_id"] = entry.get("node_id", telem["node_id"])
        except Exception:
            log.debug("node registry read failed", exc_info=True)

    pkt = _read_last_json_object(secondary_log_path)
    if pkt is not None:
        pkt_ts = pkt.get("timestamp_utc") or pkt.get("time") or pkt.get("ts_utc") or 0.0
        try:
            pkt_ts = float(pkt_ts)
        except (TypeError, ValueError):
            pkt_ts = 0.0
        if pkt_ts > telem["timestamp_utc"]:
            telem["timestamp_utc"] = pkt_ts
        _extract_sample_fields(pkt, telem)

    age_s = now - telem["timestamp_utc"] if telem["timestamp_utc"] > 0 else 9999
    if telem["timestamp_utc"] > 0 and age_s <= 60:
        telem["online"] = True
        telem["trust_flags"].append("LIVE UPLINK")
    elif phone_reachable and phone_has_sample and age_s < 300:
        telem["online"] = True
        telem["trust_flags"].append("PHONE ALIVE")
    else:
        telem["online"] = False
        telem["trust_flags"].append("OFF GRID")

    return telem


class MobileBridge(threading.Thread):
    def __init__(self, mobile_panel, poll_interval: float = 5.0):
        super().__init__(daemon=True, name="mobile-bridge")
        self.mobile_panel = mobile_panel
        self.poll_interval = poll_interval
        self._stop_event = threading.Event()

        self.status_url = _default_pixel_status_url()
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
        return collect_mobile_telemetry(
            self.status_url, self.registry_path, self.secondary_log_path
        )
