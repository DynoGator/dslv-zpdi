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
import sqlite3
import ssl
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import h5py
import numpy as np
import websockets
from websockets.asyncio.client import ClientConnection
from websockets.exceptions import ConnectionClosed, InvalidHandshake, WebSocketException
from websockets.protocol import State

from src.layer1_ingestion.mobile_ingestion import (
    build_mobile_payload,
    IngestionPayload,
    SENSORS,
    TERMUX_SENSOR_BIN,
    score_mobile_payload,
)

# Cadence requested from termux-sensor's streaming mode (`-d <ms>`). The
# Termux:API service caps the true rate at whatever the slowest sensor in
# the set can deliver; values below ~50ms typically saturate without
# raising the effective frequency. 250ms is a reasonable production
# default; calibrate per-deployment.
DEFAULT_STREAM_DELAY_MS = int(os.environ.get("ZPDI_STREAM_DELAY_MS", "250"))
DEFAULT_WSS_URI = os.environ.get("ZPDI_WSS_URI", "wss://edge.placeholder.invalid:8443/ingest")
DEFAULT_HDF5_PATH = Path(os.environ.get("ZPDI_HDF5_PATH", "./data/zpdi_stream.h5"))
DEFAULT_SQLITE_PATH = Path(os.environ.get("ZPDI_SQLITE_PATH", "./data/zpdi_cache.db"))
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


# --- Sensor streaming ---------------------------------------------------------

async def _release_sensors() -> None:
    """Fire `termux-sensor -c` to tell Android to release sensor handles.

    Called on every stream teardown as a backstop in case the bash
    wrapper's own SIGTERM trap did not finish its cleanup call. Failures
    are logged at debug level; this must never block shutdown.
    """
    try:
        proc = await asyncio.create_subprocess_exec(
            TERMUX_SENSOR_BIN, "-c",
            stdout=asyncio.subprocess.DEVNULL,
            stderr=asyncio.subprocess.DEVNULL,
        )
        try:
            await asyncio.wait_for(proc.wait(), timeout=3.0)
        except asyncio.TimeoutError:
            with contextlib.suppress(ProcessLookupError):
                proc.kill()
            await proc.wait()
    except Exception as exc:
        log.debug("sensor release call failed: %s", exc)


async def _drain_stderr(stream: asyncio.StreamReader) -> None:
    """Drain termux-sensor stderr to logs so a full pipe never blocks the writer."""
    while True:
        line = await stream.readline()
        if not line:
            return
        log.debug("termux-sensor stderr: %s", line.decode("utf-8", errors="replace").rstrip())


async def _consume_stream(
    stdout: asyncio.StreamReader,
    queues: tuple[asyncio.Queue[Payload], ...],
) -> None:
    """Parse termux-sensor's continuous JSON stream and fan out to queues.

    termux-sensor emits pretty-printed JSON objects back-to-back on stdout
    in streaming mode (one line per token). We accumulate lines and call
    json.JSONDecoder.raw_decode whenever the buffer might contain a
    complete object; raw_decode tells us where parsing stopped so we
    keep the residue for the next iteration.

    The loop runs plain `await stdout.readline()` with no `wait_for`
    wrapper: empirically, wrapping readline in wait_for against a
    streaming subprocess silently starves the reader on this Python /
    asyncio build (measured 0 of 18 objects across a 6s window with
    wait_for, 18/18 without). Stop-event responsiveness is therefore
    delegated to the supervisor in `_stream`, which terminates the
    subprocess on shutdown so readline returns EOF and this loop exits.

    The timestamp is taken inside _build_payload at the instant
    raw_decode returns — the closest the daemon can stamp to the moment
    the sensor event surfaced from the kernel.
    """
    decoder = json.JSONDecoder()
    buf = ""
    while True:
        line = await stdout.readline()
        if not line:
            return  # subprocess closed stdout — supervisor will decide what next
        buf += line.decode("utf-8", errors="replace")
        while True:
            stripped = buf.lstrip()
            if not stripped:
                buf = ""
                break
            try:
                reading, idx = decoder.raw_decode(stripped)
            except json.JSONDecodeError:
                buf = stripped  # incomplete — wait for more bytes
                break
            buf = stripped[idx:]
            if not isinstance(reading, dict):
                continue
            # termux-sensor emits one dict with all requested sensors.
            # Produce one canonical IngestionPayload per sensor.
            for sensor_name, sensor_reading in reading.items():
                if sensor_name not in SENSORS:
                    continue
                ingestion = build_mobile_payload(sensor_name, sensor_reading)
                payload = _ingestion_to_legacy(ingestion)
                if payload is None:
                    continue  # KILLED packet dropped at serialization gate
                for q in queues:
                    try:
                        q.put_nowait(payload)
                    except asyncio.QueueFull:
                        with contextlib.suppress(asyncio.QueueEmpty):
                            q.get_nowait()
                        try:
                            q.put_nowait(payload)
                        except asyncio.QueueFull:
                            pass


async def _stream(
    queues: tuple[asyncio.Queue[Payload], ...],
    stop: asyncio.Event,
) -> None:
    """Keep a termux-sensor subprocess alive for the daemon's lifetime.

    Restarts on EOF or spawn failure with capped exponential backoff so a
    transient Termux:API hiccup never takes the node down silently.
    """
    backoff = 0.5
    while not stop.is_set():
        cmd = [
            TERMUX_SENSOR_BIN,
            "-s", ",".join(SENSORS),
            "-d", str(DEFAULT_STREAM_DELAY_MS),
        ]
        try:
            # start_new_session=True puts the bash wrapper into its own
            # process group so we can SIGTERM the whole group on shutdown,
            # not just the wrapper. Without it, the underlying termux-api
            # streaming child is orphaned and continues holding sensor
            # handles in the Android service, eventually starving fresh
            # invocations until manually cleaned up.
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                start_new_session=True,
            )
        except (FileNotFoundError, OSError) as exc:
            log.error("failed to spawn termux-sensor: %s", exc)
            try:
                await asyncio.wait_for(stop.wait(), timeout=backoff)
                return
            except asyncio.TimeoutError:
                backoff = min(backoff * 2, 5.0)
                continue

        log.info("termux-sensor stream started pid=%s delay=%dms", proc.pid, DEFAULT_STREAM_DELAY_MS)
        backoff = 0.5
        assert proc.stdout is not None and proc.stderr is not None
        stderr_task = asyncio.create_task(_drain_stderr(proc.stderr))
        consume_task = asyncio.create_task(_consume_stream(proc.stdout, queues))
        stop_task = asyncio.create_task(stop.wait())
        try:
            # Race the consumer against the stop signal. Whichever wins,
            # we tear down the subprocess so the other side unblocks.
            await asyncio.wait(
                {consume_task, stop_task},
                return_when=asyncio.FIRST_COMPLETED,
            )
        finally:
            # Kill the whole process group so the underlying termux-api
            # child dies with the bash wrapper. ProcessLookupError fires
            # if the group already exited via consumer-EOF — harmless.
            with contextlib.suppress(ProcessLookupError, PermissionError):
                os.killpg(proc.pid, signal.SIGTERM)
            try:
                await asyncio.wait_for(proc.wait(), timeout=2.0)
            except asyncio.TimeoutError:
                with contextlib.suppress(ProcessLookupError, PermissionError):
                    os.killpg(proc.pid, signal.SIGKILL)
                await proc.wait()
            # Defense in depth: tell Android to release sensor handles
            # whether or not the bash trap completed its own cleanup call.
            await _release_sensors()
            for t in (consume_task, stderr_task, stop_task):
                if not t.done():
                    t.cancel()
            for t in (consume_task, stderr_task, stop_task):
                with contextlib.suppress(asyncio.CancelledError, Exception):
                    await t

        if stop.is_set():
            return
        log.warning("termux-sensor stream ended (rc=%s); restarting", proc.returncode)
        await asyncio.sleep(0.5)


def _ingestion_to_legacy(ingestion: IngestionPayload) -> Payload | None:
    """Convert a canonical IngestionPayload to the legacy Payload shape.

    trust_state is set inside ingestion.to_json() (SPEC-005A.3 gate).
    KILLED packets return None and are silently dropped.
    Coherence scores are computed here (Layer 2) and embedded for routing.
    """
    json_str = ingestion.to_json()
    if json_str is None:
        return None
    body = json.loads(json_str)
    # Backward-compat fields for existing sinks / verifier
    body["node"] = ingestion.node_id
    body["schema"] = ingestion.schema_version
    body["timestamps"] = {
        "wall_ns": int(ingestion.timestamp_utc * 1e9),
        "monotonic_ns": ingestion.ingest_monotonic_ns,
    }
    # Layer 2 coherence scoring (SPEC-006)
    coherence = score_mobile_payload(ingestion)
    if coherence is not None:
        body["r_local"] = coherence.r_local
        body["r_smooth"] = coherence.r_smooth
        body["r_global"] = coherence.r_global
    # Canonical JSON without sha256 for digest computation
    canonical = {k: v for k, v in body.items() if k != "sha256"}
    raw = json.dumps(canonical, sort_keys=True, separators=(",", ":")).encode("utf-8")
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
                ("payload", h5py.vlen_dtype(bytes)),
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
        # Serialize the body (which includes the sha256) for the log
        full_raw = json.dumps(p.body, sort_keys=True, separators=(",", ":")).encode("utf-8")
        with self._path.open("ab") as fh:
            fh.write(full_raw)
            fh.write(b"\n")


# --- SQLite Cache (for Web Server) --------------------------------------------

class SQLiteCache:
    """Lightweight, WAL-mode cache for the latest sensor state."""

    def __init__(self, path: Path) -> None:
        self._path = path
        self._conn: sqlite3.Connection | None = None

    def open(self) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(str(self._path), check_same_thread=False)
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._conn.execute("PRAGMA synchronous=NORMAL")
        self._conn.execute(
            "CREATE TABLE IF NOT EXISTS latest_state ("
            "  id INTEGER PRIMARY KEY CHECK (id = 1),"
            "  wall_ns INTEGER,"
            "  payload TEXT"
            ")"
        )
        self._conn.commit()

    def close(self) -> None:
        if self._conn:
            self._conn.close()
            self._conn = None

    async def update(self, p: Payload) -> None:
        if self._conn:
            await asyncio.to_thread(self._update_sync, p)

    def _update_sync(self, p: Payload) -> None:
        assert self._conn is not None
        # Upsert the single row with the latest sample
        self._conn.execute(
            "INSERT OR REPLACE INTO latest_state (id, wall_ns, payload) "
            "VALUES (1, ?, ?)",
            (int(p.body["timestamps"]["wall_ns"]), json.dumps(p.body))
        )
        self._conn.commit()


# --- WSS transport ------------------------------------------------------------

class WSSTransport:
    """Maintains a single WSS connection with reconnect; silently fails over."""

    def __init__(self, uri: str, ca_bundle: str | None, fallback: FallbackLog) -> None:
        self._uri = uri
        self._ssl_ctx = self._build_ssl_ctx(ca_bundle)
        self._fallback = fallback
        self._ws: ClientConnection | None = None
        self._connect_lock = asyncio.Lock()

    def _build_ssl_ctx(self, ca_bundle: str | None) -> ssl.SSLContext | None:
        # Use default context; if it's a localhost/development URI, we might
        # need to relax this, but per production requirements we stick to secure.
        if self._uri.startswith("ws://"):
            # If the URI is explicitly insecure (e.g. localhost testing),
            # websockets.connect doesn't need an SSL context.
            return None
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
                # Disable SSL for localhost development if using ws://
                is_secure = self._uri.startswith("wss://")
                self._ws = await asyncio.wait_for(
                    websockets.connect(
                        self._uri,
                        ssl=self._ssl_ctx if is_secure else None,
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
                # Serialize the body (which includes the sha256) for the wire
                full_raw = json.dumps(p.body, sort_keys=True, separators=(",", ":")).encode("utf-8")
                await self._ws.send(full_raw)
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


async def _cache_consumer(
    queue: asyncio.Queue[Payload],
    cache: SQLiteCache,
    stop: asyncio.Event,
) -> None:
    while not (stop.is_set() and queue.empty()):
        try:
            p = await asyncio.wait_for(queue.get(), timeout=0.5)
        except asyncio.TimeoutError:
            continue
        try:
            await cache.update(p)
        except Exception as exc:
            log.exception("SQLite cache update failed: %s", exc)


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
    cache = SQLiteCache(DEFAULT_SQLITE_PATH)
    cache.open()
    fallback = FallbackLog(DEFAULT_FALLBACK_LOG)
    fallback.prepare()
    transport = WSSTransport(DEFAULT_WSS_URI, DEFAULT_CA_BUNDLE, fallback)

    # One queue per consumer so a stalled sink can't starve the other.
    storage_q: asyncio.Queue[Payload] = asyncio.Queue(maxsize=QUEUE_MAX)
    cache_q: asyncio.Queue[Payload] = asyncio.Queue(maxsize=QUEUE_MAX)
    transport_q: asyncio.Queue[Payload] = asyncio.Queue(maxsize=QUEUE_MAX)
    stop = asyncio.Event()

    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        with contextlib.suppress(NotImplementedError):
            loop.add_signal_handler(sig, stop.set)

    tasks = [
        asyncio.create_task(_stream((storage_q, cache_q, transport_q), stop), name="stream"),
        asyncio.create_task(_storage_consumer(storage_q, hdf5_sink, stop), name="storage"),
        asyncio.create_task(_cache_consumer(cache_q, cache, stop), name="cache"),
        asyncio.create_task(_transport_consumer(transport_q, transport, stop), name="transport"),
    ]

    log.info("zpdi node up — stream delay=%dms sensors=%s", DEFAULT_STREAM_DELAY_MS, SENSORS)
    try:
        await stop.wait()
    finally:
        log.info("shutdown signal received — draining")
        for t in tasks:
            t.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)
        await transport.aclose()
        hdf5_sink.close()
        cache.close()
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
