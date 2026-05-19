"""dslv-zpdi Tier-1 mobile metrology node.

Asynchronous daemon that polls Termux sensors from inside a Debian proot,
hashes each payload for provenance, and fans out to local HDF5 storage and
a WSS transport with silent failover to a JSONL log if the socket drops.
"""

from __future__ import annotations

import asyncio
import contextlib
import hashlib
import json
import logging
import os
import signal
import ssl
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import h5py
import numpy as np
import websockets
from websockets.exceptions import ConnectionClosed, InvalidHandshake, WebSocketException

# Absolute host path is mandatory: the Termux binary is not on $PATH inside the
# Debian proot, and a relative lookup would silently fall through to whatever
# (if anything) the proot's own PATH resolves.
TERMUX_SENSOR_BIN = "/data/data/com.termux/files/usr/bin/termux-sensor"
# Exact sensor names from `termux-sensor -l` on this device. Substring matches
# like "barometer" silently return no rows; full vendor strings are required.
SENSORS = (
    "ICM45631 Accelerometer",
    "MMC5616 Magnetometer",
    "ICP20100 Pressure Sensor",
)

DEFAULT_POLL_INTERVAL_S = float(os.environ.get("ZPDI_POLL_INTERVAL_S", "0.25"))
DEFAULT_SENSOR_TIMEOUT_S = float(os.environ.get("ZPDI_SENSOR_TIMEOUT_S", "1.5"))
DEFAULT_WSS_URI = os.environ.get("ZPDI_WSS_URI", "wss://edge.placeholder.invalid:8443/ingest")
DEFAULT_HDF5_PATH = Path(os.environ.get("ZPDI_HDF5_PATH", "./data/zpdi_stream.h5"))
DEFAULT_FALLBACK_LOG = Path(os.environ.get("ZPDI_FALLBACK_LOG", "./logs/zpdi_fallback.jsonl"))
DEFAULT_CA_BUNDLE = os.environ.get("ZPDI_WSS_CA_BUNDLE") or None

QUEUE_MAX = 4096
HDF5_DATASET = "payloads"
HDF5_CHUNK = 256

log = logging.getLogger("zpdi")


@dataclass(frozen=True)
class Payload:
    """A single hashed sensor sample ready for both sinks."""

    body: dict[str, Any]
    raw: bytes      # canonical JSON bytes — the exact bytes that were hashed
    digest: str     # hex SHA-256 of `raw`


# --- Timestamps ----------------------------------------------------------------

def _high_res_timestamps() -> dict[str, int | float]:
    """Return the most accurate clocks the kernel exposes.

    `time.time_ns()` is wall-clock (CLOCK_REALTIME); `time.monotonic_ns()` is
    immune to NTP slew and is the correct clock for inter-sample deltas.
    `clock_gettime(CLOCK_BOOTTIME)` survives device suspend, which matters on
    a mobile node where the host may sleep between polls.
    """
    out: dict[str, int | float] = {
        "wall_ns": time.time_ns(),
        "monotonic_ns": time.monotonic_ns(),
    }
    boottime = getattr(time, "CLOCK_BOOTTIME", None)
    if boottime is not None:
        out["boottime_ns"] = time.clock_gettime_ns(boottime)
    return out


# --- Sensor polling ------------------------------------------------------------

async def _poll_sensors(timeout_s: float) -> dict[str, Any] | None:
    """Invoke termux-sensor once and parse its JSON output.

    Returns None on any failure — the caller decides whether to retry. We never
    raise out of this function; a flaky sensor must not take down the daemon.
    """
    cmd = [TERMUX_SENSOR_BIN, "-s", ",".join(SENSORS), "-n", "1"]
    try:
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
    except FileNotFoundError:
        log.error("termux-sensor binary not found at %s", TERMUX_SENSOR_BIN)
        return None
    except OSError as exc:
        log.error("failed to spawn termux-sensor: %s", exc)
        return None

    try:
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=timeout_s)
    except asyncio.TimeoutError:
        proc.kill()
        with contextlib.suppress(ProcessLookupError):
            await proc.wait()
        log.warning("termux-sensor timed out after %.2fs", timeout_s)
        return None

    if proc.returncode != 0:
        log.warning("termux-sensor exit=%s stderr=%s", proc.returncode, stderr[:200])
        return None

    try:
        return json.loads(stdout.decode("utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        log.warning("termux-sensor produced unparseable output: %s", exc)
        return None


def _build_payload(reading: dict[str, Any]) -> Payload:
    body = {
        "node": "dslv-zpdi/tier1",
        "schema": 1,
        "timestamps": _high_res_timestamps(),
        "sensors": reading,
    }
    raw = json.dumps(body, sort_keys=True, separators=(",", ":")).encode("utf-8")
    digest = hashlib.sha256(raw).hexdigest()
    body["sha256"] = digest
    return Payload(body=body, raw=raw, digest=digest)


# --- HDF5 sink ----------------------------------------------------------------

class HDF5Sink:
    """Append-only, resizable HDF5 dataset of JSON-encoded payloads + digests."""

    def __init__(self, path: Path) -> None:
        self._path = path
        self._file: h5py.File | None = None
        self._dset: h5py.Dataset | None = None
        self._lock = asyncio.Lock()

    def open(self) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._file = h5py.File(self._path, "a", libver="latest")
        if HDF5_DATASET in self._file:
            self._dset = self._file[HDF5_DATASET]
        else:
            dtype = np.dtype([
                ("wall_ns", "<u8"),
                ("sha256", "S64"),
                ("payload", h5py.special_dtype(vlen=bytes)),
            ])
            self._dset = self._file.create_dataset(
                HDF5_DATASET,
                shape=(0,),
                maxshape=(None,),
                chunks=(HDF5_CHUNK,),
                dtype=dtype,
            )
        # SWMR lets an external reader tail the file while we write.
        with contextlib.suppress(Exception):
            self._file.swmr_mode = True

    def close(self) -> None:
        if self._file is not None:
            with contextlib.suppress(Exception):
                self._file.flush()
            self._file.close()
            self._file = None
            self._dset = None

    async def append(self, p: Payload) -> None:
        if self._dset is None:
            return
        async with self._lock:
            await asyncio.to_thread(self._append_sync, p)

    def _append_sync(self, p: Payload) -> None:
        assert self._dset is not None and self._file is not None
        n = self._dset.shape[0]
        self._dset.resize((n + 1,))
        self._dset[n] = (
            int(p.body["timestamps"]["wall_ns"]),
            p.digest.encode("ascii"),
            p.raw,
        )
        self._file.flush()


# --- Fallback JSONL log -------------------------------------------------------

class FallbackLog:
    def __init__(self, path: Path) -> None:
        self._path = path
        self._lock = asyncio.Lock()

    def prepare(self) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)

    async def write(self, p: Payload) -> None:
        async with self._lock:
            await asyncio.to_thread(self._write_sync, p)

    def _write_sync(self, p: Payload) -> None:
        with self._path.open("ab") as fh:
            fh.write(p.raw)
            fh.write(b"\n")


# --- WSS transport ------------------------------------------------------------

class WSSTransport:
    """Maintains a single WSS connection with reconnect; silently fails over."""

    def __init__(self, uri: str, ca_bundle: str | None, fallback: FallbackLog) -> None:
        self._uri = uri
        self._ssl_ctx = self._build_ssl_ctx(ca_bundle)
        self._fallback = fallback
        self._ws: websockets.WebSocketClientProtocol | None = None
        self._connect_lock = asyncio.Lock()

    @staticmethod
    def _build_ssl_ctx(ca_bundle: str | None) -> ssl.SSLContext:
        ctx = ssl.create_default_context()
        if ca_bundle:
            ctx.load_verify_locations(cafile=ca_bundle)
        return ctx

    async def _ensure_connection(self) -> bool:
        if self._ws is not None and self._ws.state.name == "OPEN":
            return True
        async with self._connect_lock:
            if self._ws is not None and self._ws.state.name == "OPEN":
                return True
            try:
                self._ws = await asyncio.wait_for(
                    websockets.connect(
                        self._uri,
                        ssl=self._ssl_ctx,
                        ping_interval=20,
                        ping_timeout=10,
                        close_timeout=2,
                        max_size=2**20,
                    ),
                    timeout=5.0,
                )
                log.info("WSS connected: %s", self._uri)
                return True
            except (OSError, asyncio.TimeoutError, InvalidHandshake, WebSocketException) as exc:
                log.debug("WSS connect failed: %s", exc)
                self._ws = None
                return False

    async def send(self, p: Payload) -> None:
        if await self._ensure_connection():
            try:
                assert self._ws is not None
                await self._ws.send(p.raw)
                return
            except (ConnectionClosed, WebSocketException, OSError) as exc:
                log.debug("WSS send failed, will fail over: %s", exc)
                with contextlib.suppress(Exception):
                    await self._ws.close()
                self._ws = None
        # Silent failover — never raise out of the transport.
        await self._fallback.write(p)

    async def aclose(self) -> None:
        if self._ws is not None:
            with contextlib.suppress(Exception):
                await self._ws.close()
            self._ws = None


# --- Orchestration ------------------------------------------------------------

async def _storage_consumer(
    queue: asyncio.Queue[Payload],
    sink: HDF5Sink,
    stop: asyncio.Event,
) -> None:
    while not (stop.is_set() and queue.empty()):
        try:
            p = await asyncio.wait_for(queue.get(), timeout=0.5)
        except asyncio.TimeoutError:
            continue
        try:
            await sink.append(p)
        except Exception as exc:
            log.exception("HDF5 append failed: %s", exc)


async def _transport_consumer(
    queue: asyncio.Queue[Payload],
    transport: WSSTransport,
    stop: asyncio.Event,
) -> None:
    while not (stop.is_set() and queue.empty()):
        try:
            p = await asyncio.wait_for(queue.get(), timeout=0.5)
        except asyncio.TimeoutError:
            continue
        try:
            await transport.send(p)
        except Exception as exc:
            log.exception("transport send failed unexpectedly: %s", exc)


async def main() -> int:
    logging.basicConfig(
        level=os.environ.get("ZPDI_LOG_LEVEL", "INFO"),
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )

    hdf5_sink = HDF5Sink(DEFAULT_HDF5_PATH)
    hdf5_sink.open()
    fallback = FallbackLog(DEFAULT_FALLBACK_LOG)
    fallback.prepare()
    transport = WSSTransport(DEFAULT_WSS_URI, DEFAULT_CA_BUNDLE, fallback)

    # One queue per consumer so a stalled sink can't starve the other.
    storage_q: asyncio.Queue[Payload] = asyncio.Queue(maxsize=QUEUE_MAX)
    transport_q: asyncio.Queue[Payload] = asyncio.Queue(maxsize=QUEUE_MAX)
    stop = asyncio.Event()

    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        with contextlib.suppress(NotImplementedError):
            loop.add_signal_handler(sig, stop.set)

    async def fanout() -> None:
        while not stop.is_set():
            loop_start = time.monotonic()
            reading = await _poll_sensors(DEFAULT_SENSOR_TIMEOUT_S)
            if reading is not None:
                p = _build_payload(reading)
                for q in (storage_q, transport_q):
                    if q.full():
                        with contextlib.suppress(asyncio.QueueEmpty):
                            q.get_nowait()
                    q.put_nowait(p)
            elapsed = time.monotonic() - loop_start
            try:
                await asyncio.wait_for(stop.wait(), timeout=max(0.0, DEFAULT_POLL_INTERVAL_S - elapsed))
            except asyncio.TimeoutError:
                pass

    tasks = [
        asyncio.create_task(fanout(), name="producer"),
        asyncio.create_task(_storage_consumer(storage_q, hdf5_sink, stop), name="storage"),
        asyncio.create_task(_transport_consumer(transport_q, transport, stop), name="transport"),
    ]

    log.info("zpdi node up — poll=%.3fs sensors=%s", DEFAULT_POLL_INTERVAL_S, SENSORS)
    try:
        await stop.wait()
    finally:
        log.info("shutdown signal received — draining")
        for t in tasks:
            t.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)
        await transport.aclose()
        hdf5_sink.close()
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
