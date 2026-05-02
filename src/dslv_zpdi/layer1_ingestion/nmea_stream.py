"""
SPEC-004A.3-NMEA — Non-blocking NMEA GGA stream reader.

Runs a background daemon thread that continuously reads sentences from the
LBE-1421's USB-C virtual serial port (/dev/ttyACMx). The latest parsed GGA
fix is cached in a dict protected by a lock; callers read that dict without
any serial I/O on their hot path.

On serial error or disconnect the thread waits retry_delay_s then re-opens,
so it recovers automatically when the GPSDO is reconnected.
"""

from __future__ import annotations

import logging
import threading
import time
from typing import Optional

logger = logging.getLogger("dslv-zpdi.nmea")


class NmeaStream:
    """
    Background NMEA reader that caches the latest GGA fix without blocking.

    Usage:
        stream = NmeaStream(port="/dev/ttyACM0")
        stream.start()
        ...
        fix = stream.latest()   # fast, non-blocking
        if fix["gps_fix"]:
            ...
        stream.stop()
    """

    def __init__(
        self,
        port: str = "/dev/ttyACM0",
        baud: int = 9600,
        retry_delay_s: float = 5.0,
    ) -> None:
        self._port = port
        self._baud = baud
        self._retry_delay = retry_delay_s

        self._lock = threading.Lock()
        self._stop = threading.Event()
        self._thread: Optional[threading.Thread] = None
        self._latest: dict = _empty_fix()

    # ------------------------------------------------------------------ #
    # Lifecycle                                                            #
    # ------------------------------------------------------------------ #

    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            return
        self._stop.clear()
        self._thread = threading.Thread(
            target=self._run, name="nmea-stream", daemon=True
        )
        self._thread.start()
        logger.info("NmeaStream: started on %s @ %d baud", self._port, self._baud)

    def stop(self) -> None:
        self._stop.set()
        if self._thread:
            self._thread.join(timeout=3.0)
        logger.info("NmeaStream: stopped")

    # ------------------------------------------------------------------ #
    # Public API                                                           #
    # ------------------------------------------------------------------ #

    def latest(self) -> dict:
        """Return a thread-safe copy of the most recently parsed GGA sentence."""
        with self._lock:
            return dict(self._latest)

    # ------------------------------------------------------------------ #
    # Reader thread                                                        #
    # ------------------------------------------------------------------ #

    def _run(self) -> None:
        while not self._stop.is_set():
            try:
                import serial  # pylint: disable=import-outside-toplevel
            except ImportError:
                logger.error("NmeaStream: pyserial not installed — pip install pyserial")
                self._stop.wait(60.0)
                continue

            try:
                with serial.Serial(
                    self._port,
                    self._baud,
                    timeout=1.0,    # readline() returns after 1 s with no data
                    exclusive=True, # prevent other processes from opening same port
                ) as ser:
                    logger.info("NmeaStream: port open")
                    self._reader_loop(ser)
            except serial.SerialException as exc:
                logger.warning(
                    "NmeaStream: serial error on %s: %s — retry in %.0f s",
                    self._port, exc, self._retry_delay,
                )
                self._stop.wait(self._retry_delay)
            except Exception as exc:  # pylint: disable=broad-except
                logger.error("NmeaStream: unexpected error: %s", exc)
                self._stop.wait(self._retry_delay)

    def _reader_loop(self, ser) -> None:  # type: ignore[no-untyped-def]
        import serial  # pylint: disable=import-outside-toplevel
        while not self._stop.is_set():
            try:
                raw = ser.readline()
            except serial.SerialException:
                raise  # propagate to _run for reconnect handling
            if not raw:
                continue  # timeout with no data
            try:
                line = raw.decode("ascii", errors="ignore").strip()
            except Exception:  # pylint: disable=broad-except
                continue
            if not (line.startswith("$GNGGA") or line.startswith("$GPGGA")):
                continue
            parsed = parse_gga(line)
            if parsed is not None:
                with self._lock:
                    self._latest = parsed


# ------------------------------------------------------------------ #
# Module-level helpers (also importable for testing)                 #
# ------------------------------------------------------------------ #

def _empty_fix() -> dict:
    return {
        "gps_fix": False,
        "fix_quality": 0,
        "satellites_used": 0,
        "hdop": 99.9,
        "utc_time": "",
        "ts": 0.0,
    }


def parse_gga(sentence: str) -> Optional[dict]:
    """
    Parse a single GGA sentence with NMEA checksum validation.

    Returns a fix dict on success, None on checksum failure or missing fields.

    GGA field layout (0-indexed after split on ','):
        0  = message ID ($GPGGA / $GNGGA)
        1  = UTC time (hhmmss.ss)
        2  = latitude
        3  = N/S
        4  = longitude
        5  = E/W
        6  = fix quality (0=invalid, 1=GPS, 2=DGPS, 4=RTK fixed, 5=RTK float)
        7  = satellites in use
        8  = HDOP
        9  = altitude (MSL)
        ...
        checksum after '*'
    """
    # Validate NMEA checksum: XOR of all bytes between '$' (exclusive) and '*' (exclusive)
    if "*" in sentence:
        star = sentence.rfind("*")
        body = sentence[1:star]
        chk_str = sentence[star + 1 : star + 3]
        computed = 0
        for ch in body:
            computed ^= ord(ch)
        try:
            if computed != int(chk_str, 16):
                logger.debug("NmeaStream: checksum mismatch: %s", sentence[:60])
                return None
        except ValueError:
            return None

    parts = sentence.split(",")
    if len(parts) < 10:
        return None

    try:
        utc_time = parts[1].strip()
        fix_raw = parts[6].strip()
        sats_raw = parts[7].strip()
        hdop_raw = parts[8].strip()

        fix_quality = int(fix_raw) if fix_raw else 0
        sats = int(sats_raw) if sats_raw else 0
        hdop = float(hdop_raw) if hdop_raw else 99.9
    except (ValueError, IndexError):
        return None

    return {
        "gps_fix": fix_quality > 0,
        "fix_quality": fix_quality,
        "satellites_used": sats,
        "hdop": hdop,
        "utc_time": utc_time,
        "ts": time.time(),
    }
