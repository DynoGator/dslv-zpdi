"""NOAA SWPC live space-weather feed.

A single background thread polls NOAA endpoints on a slow cadence and
publishes the latest snapshot into a thread-safe dict. Panels read from
the snapshot — they never block on the network.

Endpoints:
    * planetary K-index (1-minute estimated)
    * solar wind plasma (ACE/DSCOVR — speed, density, temp)
    * solar wind IMF (Bt, Bz)
    * GOES X-ray flux (flare class — CME proxy)
    * 10.7 cm radio flux
    * NOAA alerts (CME warnings, geomagnetic storm watches)
"""

from __future__ import annotations

import json
import math
import threading
import time
import urllib.error
import urllib.request


_TIMEOUT = 6.0
_USER_AGENT = "DSLV-ZPDI-Dashboard/1.0 (+https://dynogatorlabs)"

ENDPOINTS = {
    "kp": "https://services.swpc.noaa.gov/json/planetary_k_index_1m.json",
    "plasma": "https://services.swpc.noaa.gov/products/solar-wind/plasma-1-day.json",
    "mag": "https://services.swpc.noaa.gov/products/solar-wind/mag-1-day.json",
    "xray": "https://services.swpc.noaa.gov/json/goes/primary/xrays-1-day.json",
    "f107": "https://services.swpc.noaa.gov/json/f107_cm_flux.json",
    "alerts": "https://services.swpc.noaa.gov/products/alerts.json",
}


def _fetch_json(url: str):
    req = urllib.request.Request(url, headers={"User-Agent": _USER_AGENT})
    with urllib.request.urlopen(req, timeout=_TIMEOUT) as resp:
        return json.loads(resp.read().decode("utf-8", errors="replace"))


def _xray_flare_class(watts_per_m2: float) -> str:
    """Map GOES long-wavelength flux to NOAA flare letter+magnitude."""
    if watts_per_m2 is None or watts_per_m2 <= 0 or math.isnan(watts_per_m2):
        return "—"
    if watts_per_m2 < 1e-7:
        return "A"
    if watts_per_m2 < 1e-6:
        mag = watts_per_m2 / 1e-7
        return f"B{mag:.1f}"
    if watts_per_m2 < 1e-5:
        mag = watts_per_m2 / 1e-6
        return f"C{mag:.1f}"
    if watts_per_m2 < 1e-4:
        mag = watts_per_m2 / 1e-5
        return f"M{mag:.1f}"
    mag = watts_per_m2 / 1e-4
    return f"X{mag:.1f}"


def _r_scale(flare: str) -> str:
    """NOAA R-scale (radio blackout) from flare class letter."""
    if not flare or flare == "—":
        return "R0"
    head = flare[0]
    try:
        mag = float(flare[1:]) if len(flare) > 1 else 0.0
    except ValueError:
        mag = 0.0
    if head == "X":
        if mag >= 20:
            return "R5"
        if mag >= 10:
            return "R4"
        return "R3"
    if head == "M":
        if mag >= 5:
            return "R2"
        return "R1"
    return "R0"


def _g_scale(kp: float) -> str:
    """NOAA G-scale from planetary K-index."""
    if kp is None or math.isnan(kp):
        return "G0"
    if kp >= 9:
        return "G5"
    if kp >= 8:
        return "G4"
    if kp >= 7:
        return "G3"
    if kp >= 6:
        return "G2"
    if kp >= 5:
        return "G1"
    return "G0"


def _parse_kp(payload) -> dict:
    """Returns {kp_now, kp_history (list[float, recent first → oldest])}."""
    if not isinstance(payload, list) or not payload:
        return {"kp_now": float("nan"), "kp_history": []}
    sample = payload[-1]
    kp_now = float(sample.get("estimated_kp", sample.get("kp_index", float("nan"))))
    history = []
    for row in payload[-32:]:
        try:
            history.append(float(row.get("estimated_kp", row.get("kp_index", float("nan")))))
        except (TypeError, ValueError):
            history.append(float("nan"))
    return {"kp_now": kp_now, "kp_history": history}


def _parse_plasma(payload) -> dict:
    """Two-row CSV-style array: [headers, [time, density, speed, temp], ...]."""
    if not isinstance(payload, list) or len(payload) < 2:
        return {"speed_kms": float("nan"), "density": float("nan"), "temp_k": float("nan")}
    last = payload[-1]
    try:
        density = float(last[1]) if last[1] not in (None, "") else float("nan")
        speed = float(last[2]) if last[2] not in (None, "") else float("nan")
        temp = float(last[3]) if last[3] not in (None, "") else float("nan")
    except (ValueError, IndexError, TypeError):
        return {"speed_kms": float("nan"), "density": float("nan"), "temp_k": float("nan")}
    return {"speed_kms": speed, "density": density, "temp_k": temp}


def _parse_mag(payload) -> dict:
    """[headers, [time, bx, by, bz, lon, lat, bt], ...]."""
    if not isinstance(payload, list) or len(payload) < 2:
        return {"bt_nt": float("nan"), "bz_nt": float("nan")}
    last = payload[-1]
    try:
        bz = float(last[3]) if last[3] not in (None, "") else float("nan")
        bt = float(last[6]) if len(last) > 6 and last[6] not in (None, "") else float("nan")
    except (ValueError, IndexError, TypeError):
        return {"bt_nt": float("nan"), "bz_nt": float("nan")}
    return {"bt_nt": bt, "bz_nt": bz}


def _parse_xray(payload) -> dict:
    """GOES x-ray flux. Use long channel (0.1-0.8 nm) — that's the 'class'."""
    if not isinstance(payload, list) or not payload:
        return {"flux": float("nan"), "flare": "—"}
    long_rows = [r for r in payload if r.get("energy") in ("0.1-0.8nm", "long")]
    if not long_rows:
        long_rows = payload
    last = long_rows[-1]
    try:
        flux = float(last.get("flux", float("nan")))
    except (ValueError, TypeError):
        flux = float("nan")
    return {"flux": flux, "flare": _xray_flare_class(flux)}


def _parse_f107(payload) -> dict:
    """10.7cm solar radio flux (sfu)."""
    if not isinstance(payload, list) or not payload:
        return {"f107_sfu": float("nan")}
    last = payload[-1]
    try:
        return {"f107_sfu": float(last.get("flux", last.get("f107", float("nan"))))}
    except (ValueError, TypeError):
        return {"f107_sfu": float("nan")}


def _parse_alerts(payload) -> list[dict]:
    """Recent NOAA alert messages (most recent first)."""
    if not isinstance(payload, list):
        return []
    out: list[dict] = []
    for entry in payload[:12]:
        msg = entry.get("message", "") or ""
        first_line = msg.strip().splitlines()[0] if msg.strip() else "(no message)"
        out.append({
            "issued": entry.get("issue_datetime", entry.get("issued", "?")),
            "code": entry.get("product_id", "?"),
            "headline": first_line[:140],
        })
    return out


def storm_phase(kp_history: list[float]) -> str:
    """Classify storm progression from recent Kp slope.

    Returns one of: QUIET, ESCALATING, PEAK, RECEDING.
    """
    clean = [v for v in kp_history if not (v is None or math.isnan(v))]
    if len(clean) < 3:
        return "UNKNOWN"
    now = clean[-1]
    if now < 4.0 and max(clean[-6:]) < 5.0:
        return "QUIET"
    recent = clean[-3:]
    earlier = clean[-6:-3] if len(clean) >= 6 else clean[:-3]
    avg_recent = sum(recent) / len(recent)
    avg_earlier = sum(earlier) / len(earlier) if earlier else avg_recent
    delta = avg_recent - avg_earlier
    if delta > 0.3:
        return "ESCALATING"
    if delta < -0.3:
        return "RECEDING"
    if avg_recent >= 5.0:
        return "PEAK"
    return "QUIET"


class SpaceWeatherFeed:
    """Background poller for NOAA SWPC. Singleton-ish; instantiate once."""

    POLL_INTERVAL = 90.0  # seconds — NOAA updates these on minute-scale, no need to hammer
    BACKOFF_ON_FAIL = 30.0

    def __init__(self):
        self._lock = threading.Lock()
        self._snapshot: dict = {
            "kp_now": float("nan"),
            "kp_history": [],
            "g_scale": "G0",
            "speed_kms": float("nan"),
            "density": float("nan"),
            "temp_k": float("nan"),
            "bt_nt": float("nan"),
            "bz_nt": float("nan"),
            "flux": float("nan"),
            "flare": "—",
            "r_scale": "R0",
            "f107_sfu": float("nan"),
            "phase": "UNKNOWN",
            "alerts": [],
            "last_update": 0.0,
            "last_error": None,
            "ok": False,
        }
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None

    def start(self):
        if self._thread is not None:
            return
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()

    def stop(self):
        self._stop.set()

    def snapshot(self) -> dict:
        with self._lock:
            return dict(self._snapshot)

    def _loop(self):
        while not self._stop.is_set():
            try:
                self._poll_once()
                self._stop.wait(self.POLL_INTERVAL)
            except Exception as e:
                with self._lock:
                    self._snapshot["last_error"] = f"{type(e).__name__}: {e}"
                self._stop.wait(self.BACKOFF_ON_FAIL)

    def _poll_once(self):
        results = {}
        first_error = None
        for key, url in ENDPOINTS.items():
            try:
                results[key] = _fetch_json(url)
            except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as e:
                if first_error is None:
                    first_error = f"{key}: {type(e).__name__}"
                results[key] = None

        merged: dict = {"last_update": time.time(), "last_error": first_error}

        if results.get("kp") is not None:
            merged.update(_parse_kp(results["kp"]))
            merged["g_scale"] = _g_scale(merged.get("kp_now", float("nan")))
            merged["phase"] = storm_phase(merged.get("kp_history", []))
        if results.get("plasma") is not None:
            merged.update(_parse_plasma(results["plasma"]))
        if results.get("mag") is not None:
            merged.update(_parse_mag(results["mag"]))
        if results.get("xray") is not None:
            x = _parse_xray(results["xray"])
            merged.update(x)
            merged["r_scale"] = _r_scale(x["flare"])
        if results.get("f107") is not None:
            merged.update(_parse_f107(results["f107"]))
        if results.get("alerts") is not None:
            merged["alerts"] = _parse_alerts(results["alerts"])

        merged["ok"] = first_error is None or any(
            results.get(k) is not None for k in ("kp", "plasma", "mag")
        )

        with self._lock:
            self._snapshot.update(merged)


_FEED: SpaceWeatherFeed | None = None


def get_feed() -> SpaceWeatherFeed:
    """Module-level singleton — panels call this and start() is idempotent."""
    global _FEED
    if _FEED is None:
        _FEED = SpaceWeatherFeed()
        _FEED.start()
    return _FEED
