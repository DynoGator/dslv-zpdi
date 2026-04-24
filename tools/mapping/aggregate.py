"""Event aggregator for DSLV-ZPDI map rendering.

Walks every *.h5 under output/primary/ and the quarantine.jsonl under
output/secondary/ and emits a flat list of event dicts with a geo-anchor
attached.

Because the HDF5 record schema has no per-event GPS (events are anchored
to the sensor, not to a moving target), we attach the anchor's lat/lon
from config and then scatter events on a small ring around the anchor
so pins don't stack. Primary events fan out across the antenna cone;
secondary events land on a jittered secondary ring.
"""

from __future__ import annotations

import glob
import hashlib
import json
import math
import os
import random
from collections import deque
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterable

try:
    import h5py
    _HAVE_H5PY = True
except Exception:
    h5py = None  # type: ignore
    _HAVE_H5PY = False

try:
    import yaml  # optional
    _HAVE_YAML = True
except Exception:
    _HAVE_YAML = False


REPO = Path(__file__).resolve().parents[2]
PRIMARY_DIR = REPO / "output" / "primary"
SECONDARY_FILE = REPO / "output" / "secondary" / "quarantine.jsonl"

DEFAULT_CONFIG_CANDIDATES = [
    Path.home() / ".config" / "dslv-zpdi" / "sensor_location.yaml",
    REPO / "config" / "sensor_location.yaml",
    REPO / "config" / "sensor_location.example.yaml",
]

EARTH_R_M = 6_371_000.0


@dataclass
class Anchor:
    node_id: str
    site_name: str
    latitude: float
    longitude: float
    altitude_m: float
    antenna_heading_deg: float
    secondary_ring_m: float


@dataclass
class MapEvent:
    kind: str             # "primary" or "secondary"
    source_file: str
    event_id: str
    timestamp_utc: float
    latitude: float
    longitude: float
    label: str
    # Free-form metric bag for the popup table.
    metrics: dict


def _load_yaml(path: Path) -> dict:
    """Tiny YAML shim — uses PyYAML if available, otherwise a minimal
    key: value reader good enough for this one config file."""
    if _HAVE_YAML:
        return yaml.safe_load(path.read_text()) or {}
    out: dict = {}
    for line in path.read_text().splitlines():
        line = line.split("#", 1)[0].rstrip()
        if not line or ":" not in line:
            continue
        k, _, v = line.partition(":")
        k = k.strip()
        v = v.strip().strip('"').strip("'")
        if not v:
            continue
        try:
            out[k] = int(v)
            continue
        except ValueError:
            pass
        try:
            out[k] = float(v)
            continue
        except ValueError:
            pass
        out[k] = v
    return out


def load_anchor(config_path: Path | None = None) -> Anchor:
    paths = [config_path] if config_path else DEFAULT_CONFIG_CANDIDATES
    for p in paths:
        if p and p.exists():
            raw = _load_yaml(p)
            return Anchor(
                node_id=str(raw.get("node_id", "DSLV-ANCHOR")),
                site_name=str(raw.get("site_name", "Anchor")),
                latitude=float(raw.get("latitude", 0.0)),
                longitude=float(raw.get("longitude", 0.0)),
                altitude_m=float(raw.get("altitude_m", 0.0)),
                antenna_heading_deg=float(raw.get("antenna_heading_deg", 0.0)),
                secondary_ring_m=float(raw.get("secondary_ring_m", 150.0)),
            )
    # No config anywhere — return an obviously-wrong zero anchor so the
    # map still renders and the user notices.
    return Anchor("UNCONFIGURED", "UNCONFIGURED", 0.0, 0.0, 0.0, 0.0, 150.0)


def _offset(lat: float, lon: float, bearing_deg: float, distance_m: float) -> tuple[float, float]:
    """Great-circle offset — cheap flat-earth approximation, accurate within
    <1m at sub-km distances, which is all we need for pin scatter."""
    brg = math.radians(bearing_deg)
    dlat = (distance_m * math.cos(brg)) / EARTH_R_M
    dlon = (distance_m * math.sin(brg)) / (EARTH_R_M * max(0.01, math.cos(math.radians(lat))))
    return lat + math.degrees(dlat), lon + math.degrees(dlon)


def _stable_rand(seed: str) -> random.Random:
    h = hashlib.md5(seed.encode()).digest()
    return random.Random(int.from_bytes(h[:8], "big"))


def _iter_primary_files() -> Iterable[Path]:
    """Newest first, so `collect_primary` caps at the most recent captures
    rather than truncating the latest data in favor of old stuff."""
    return sorted(PRIMARY_DIR.glob("*.h5"), key=lambda p: p.stat().st_mtime, reverse=True)


def _read_event(group: h5py.Group) -> dict:
    """Pull scalar datasets out of an event group."""
    out = {}
    for k, v in group.items():
        if isinstance(v, h5py.Dataset):
            try:
                val = v[()]
                if isinstance(val, bytes):
                    val = val.decode(errors="replace")
                out[k] = val
            except Exception:
                pass
    return out


def collect_primary(anchor: Anchor, max_events: int | None = None,
                    since_utc: float | None = None, until_utc: float | None = None) -> list[MapEvent]:
    if not _HAVE_H5PY:
        return []
    events: list[MapEvent] = []
    cone_half_deg = 35.0  # directional spread
    ring_m = 80.0         # primary pins fall inside this ring
    for h5_path in _iter_primary_files():
        try:
            f = h5py.File(h5_path, "r")
        except OSError:
            continue
        with f:
            # Events are inserted in time order (event_00000000, 00000001, ...)
            # so reverse-sorting gives us latest-first within a file.
            for name, group in sorted(f.items(), key=lambda kv: kv[0], reverse=True):
                if not isinstance(group, h5py.Group):
                    continue
                rec = _read_event(group)
                if not rec:
                    continue
                ts = float(rec.get("timestamp_utc", 0.0) or 0.0)
                if since_utc is not None and ts < since_utc:
                    continue
                if until_utc is not None and ts > until_utc:
                    continue
                rng = _stable_rand(f"primary::{h5_path.name}::{name}")
                bearing = anchor.antenna_heading_deg + rng.uniform(-cone_half_deg, cone_half_deg)
                r_s = float(rec.get("r_smooth", 0.0) or 0.0)
                dist = ring_m * (1.0 - min(1.0, r_s)) * 0.5 + rng.uniform(0, ring_m * 0.3)
                lat, lon = _offset(anchor.latitude, anchor.longitude, bearing, dist)
                r_g = float(rec.get("r_global", 0.0) or 0.0)
                r_l = float(rec.get("r_local", 0.0) or 0.0)
                label = f"PRIMARY {name.split('_')[1]}  r={r_s:.3f}"
                events.append(MapEvent(
                    kind="primary",
                    source_file=h5_path.name,
                    event_id=name,
                    timestamp_utc=ts,
                    latitude=lat,
                    longitude=lon,
                    label=label,
                    metrics={
                        "r_global": r_g,
                        "r_local": r_l,
                        "r_smooth": r_s,
                        "payload_uuid": str(rec.get("payload_uuid", "")),
                    },
                ))
                if max_events and len(events) >= max_events:
                    return events
    return events


def _tail_lines(path: Path, max_lines: int) -> list[tuple[int, str]]:
    """Read the last max_lines of path without slurping the whole file.

    Returns a list of (line_no, line) pairs (line_no is 0-based in the
    original file). Used instead of enumerate(fh) so that big JSONL logs
    give us the *most recent* events, not the first N at startup.
    """
    if max_lines <= 0:
        return []
    dq: deque[tuple[int, bytes]] = deque(maxlen=max_lines)
    line_no = 0
    with open(path, "rb") as fh:
        leftover = b""
        for chunk_bytes in iter(lambda: fh.read(1 << 16), b""):
            chunk_bytes = leftover + chunk_bytes
            lines = chunk_bytes.split(b"\n")
            leftover = lines.pop()
            for line in lines:
                dq.append((line_no, line))
                line_no += 1
        if leftover:
            dq.append((line_no, leftover))
            line_no += 1
    return [(i, line.decode("utf-8", errors="replace")) for i, line in dq]


def collect_secondary(anchor: Anchor, max_events: int | None = None,
                      since_utc: float | None = None, until_utc: float | None = None) -> list[MapEvent]:
    events: list[MapEvent] = []
    if not SECONDARY_FILE.exists():
        return events
    cap = max_events or 100_000
    tail = _tail_lines(SECONDARY_FILE, cap)
    for idx, line in tail:
        line = line.strip()
        if not line:
            continue
        try:
            rec = json.loads(line)
        except json.JSONDecodeError:
            continue
        ts = float(rec.get("timestamp_utc", 0.0) or 0.0)
        if since_utc is not None and ts < since_utc:
            continue
        if until_utc is not None and ts > until_utc:
            continue
        rng = _stable_rand(f"secondary::{idx}")
        bearing = rng.uniform(0, 360)
        dist = anchor.secondary_ring_m * (0.8 + rng.random() * 0.4)
        lat, lon = _offset(anchor.latitude, anchor.longitude, bearing, dist)
        node = str(rec.get("node_id", "?"))
        reason = str(rec.get("reason", ""))
        r_s = rec.get("r_smooth")
        metrics = {
            "node_id": node,
            "stream": rec.get("stream"),
            "reason": reason,
            "trust_state": rec.get("trust_state"),
            "r_smooth": r_s,
        }
        label = f"SECONDARY {node}  {reason}"
        events.append(MapEvent(
            kind="secondary",
            source_file=SECONDARY_FILE.name,
            event_id=f"q#{idx}",
            timestamp_utc=ts,
            latitude=lat,
            longitude=lon,
            label=label,
            metrics=metrics,
        ))
        if max_events and len(events) >= max_events:
            break
    return events


def collect_all(config_path: Path | None = None,
                max_primary: int | None = 2000,
                max_secondary: int | None = 2000,
                since_utc: float | None = None,
                until_utc: float | None = None) -> tuple[Anchor, list[MapEvent]]:
    anchor = load_anchor(config_path)
    prim = collect_primary(anchor, max_events=max_primary, since_utc=since_utc, until_utc=until_utc)
    sec = collect_secondary(anchor, max_events=max_secondary, since_utc=since_utc, until_utc=until_utc)
    return anchor, prim + sec


def to_jsonable(events: list[MapEvent]) -> list[dict]:
    return [asdict(e) for e in events]


if __name__ == "__main__":
    anchor, events = collect_all()
    print(f"anchor: {anchor}")
    print(f"events: {len(events)}  "
          f"(primary={sum(1 for e in events if e.kind=='primary')}, "
          f"secondary={sum(1 for e in events if e.kind=='secondary')})")
    if events:
        print("first:", events[0])
