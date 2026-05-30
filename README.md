# dslv-zpdi — Tier-2 Mobile Swarm Node (Rev 3.5)

> **Tier classification:** This node runs on a Pixel 9 Pro XL inside a Debian proot-distro container. It is a **Tier-2 Swarm node** — it has no GPS-disciplined oscillator, no PPS hardware, and no external clock. Every packet it produces is `SECONDARY_QUARANTINED` by design. Institutional-grade primary-stream data requires Tier-1 Anchor hardware (Raspberry Pi CM5 + Intel i210-T1 + u-blox GPSDO or equivalent per SPEC-004A.2).

---

## Table of Contents

1. [What this node does](#what-this-node-does)
2. [Architecture overview](#architecture-overview)
3. [Installation](#installation)
4. [Tier-1 Integration — connecting to the ingestion server](#tier-1-integration)
   - [Generating credentials](#generating-credentials)
   - [Configuring the mobile node](#configuring-the-mobile-node)
   - [Running the Tier-1 server](#running-the-tier-1-server)
   - [TLS / WSS setup](#tls--wss-setup)
5. [Environment variable reference](#environment-variable-reference)
6. [Running the node](#running-the-node)
7. [Sensor suite and GPS](#sensor-suite-and-gps)
8. [Reading the output streams](#reading-the-output-streams)
9. [Web API](#web-api)
10. [Health monitoring and supervision](#health-monitoring-and-supervision)
11. [Tuning for maximum data quality](#tuning-for-maximum-data-quality)
12. [Testing](#testing)
13. [Project layout](#project-layout)

---

## What this node does

The daemon (`zpdi_mobile_node.py`) runs continuously inside the Debian proot, polling Android sensors via `termux-sensor` and optionally a GPS fix via `termux-location`. For each sensor reading it:

1. **Layer 1 — Ingestion:** Builds a hardened `IngestionPayload` with provenance fields, extracts instantaneous Hilbert-transform phases from the magnitude signal, and stamps a wall-clock + monotonic timestamp pair.
2. **Layer 2 — Coherence:** Scores the payload with the KCET-ATLAS Kuramoto order parameter (`r_local`), EWMA-smoothed over a rolling window (`r_smooth`), and weights both scores by an orientation-stability factor derived from the rotation-vector sensor (`r_local_fused`, `r_smooth_fused` — SPEC-006.6).
3. **Layer 3 — Routing:** Enforces the dual-stream protocol. Because `hardware_tier = 2`, every packet routes to `SECONDARY` regardless of coherence score — Tier-2 data can never enter the primary HDF5 stream.
4. **Signing and encryption:** Embeds a SHA-256 integrity digest, an HMAC-SHA256 authentication signature, and optionally wraps the payload in AES-256-GCM before transmission.
5. **Fan-out:** Writes to three sinks in parallel — HDF5 (primary, intentionally empty for Tier-2), SQLite WAL cache (for the web API), and the WSS transport to the Tier-1 server with silent failover to a local JSONL log.

---

## Architecture overview

```
Android sensors (termux-sensor)
        │
        ▼
 ┌─────────────────────────────────────────┐
 │        zpdi_mobile_node.py (Rev 3.5)    │
 │                                         │
 │  Layer 1  build_mobile_payload()        │
 │           • IngestionPayload            │
 │           • Hilbert phase extraction    │
 │           • GPS location enrichment     │
 │                                         │
 │  Layer 2  score_mobile_payload()        │
 │           • Kuramoto r_local / r_smooth │
 │           • Orientation fusion weight   │
 │                                         │
 │  Layer 3  route_packet()               │
 │           • Always SECONDARY (Tier-2)  │
 │           • SHA-256 + HMAC-SHA256      │
 │           • Optional AES-256-GCM       │
 └─────────────┬───────────────┬──────────┘
               │               │
       ┌───────┘       ┌───────┘
       ▼               ▼
 HDF5 (empty)    SQLite cache ──► zpdi_web_server.py
                                        │
                         WebSocket / REST API
                                        │
                         logs/zpdi_fallback.jsonl ◄─── WSS failover
                                        │
                         WSS ──────────► tier1_ingestion_server.py
                                               │
                                         Secondary JSONL
                                         (tier1_secondary.jsonl)
```

---

## Installation

### Prerequisites

- Android device running Termux with **Termux:API** and **Termux:Boot** installed (F-Droid builds recommended — Play Store builds have reduced permissions)
- `proot-distro` installed in Termux: `pkg install proot-distro`
- Debian proot provisioned: `proot-distro install debian`

### Inside the Debian proot

```bash
proot-distro login debian

# System packages
apt-get update && apt-get install -y python3 python3-venv python3-pip libhdf5-dev git

# Clone (or navigate to) the project
cd /root/dslv-zpdi

# Create virtualenv and install dependencies
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### Termux-side (outside proot)

```bash
# Install Termux:API binaries used by the daemon
pkg install termux-api

# Grant sensor and location permissions in Android Settings
# → Apps → Termux:API → Permissions → enable Location and Physical Activity
```

---

## Tier-1 Integration

The Tier-1 ingestion server (`tier1_ingestion_server.py`) receives, authenticates, decrypts, and verifies payloads from this mobile node over a WebSocket connection. Three independent security layers protect the channel:

| Layer | Mechanism | Required |
|---|---|---|
| Connection auth | Bearer token in `Authorization` header | Recommended |
| Payload auth | HMAC-SHA256 over canonical JSON | Recommended |
| Payload confidentiality | AES-256-GCM envelope | Optional |

All three use **shared secrets** — the same values must appear in `.env` on both the mobile node and the machine running `tier1_ingestion_server.py`.

### Generating credentials

Run these commands once on any machine with Python 3 and `cryptography` installed. **Store the output securely** — treat these like passwords.

#### Bearer token

```bash
python3 -c "import secrets; print(secrets.token_urlsafe(32))"
# Example output: gX9kLmN2pQrStUvWxYzAaBbCcDdEeFfGg
```

Copy the output to `ZPDI_WSS_TOKEN` in `.env`.

#### HMAC secret

```bash
python3 -c "import secrets; print(secrets.token_hex(32))"
# Example output: a1b2c3d4e5f6...64-hex-chars...
```

Copy the output to `ZPDI_HMAC_SECRET` in `.env`. Any printable string works; 32+ random bytes is recommended.

#### AES-256-GCM key (optional — encrypt payload content in transit)

```bash
python3 -c "
import secrets, base64
key = secrets.token_bytes(32)
print(base64.b64encode(key).decode())
"
# Example output: xK3mN7pQrStUvWxYzAaBbCcDdEeFfGgHhIi...==
```

Copy the output to `ZPDI_AES_KEY` in `.env`. This is a 32-byte (256-bit) key, base64-encoded. If omitted, payloads are sent as signed plain JSON over the WSS channel — the connection itself is still authenticated via Bearer token and HMAC.

### Configuring the mobile node

Edit `/root/dslv-zpdi/.env`:

```dotenv
# Where the Tier-1 server is listening
ZPDI_WSS_URI=ws://192.168.1.100:8443/ingest   # plain WebSocket
# or
ZPDI_WSS_URI=wss://your.domain.com:8443/ingest # TLS WebSocket

# Auth credentials — must match the server's .env exactly
ZPDI_WSS_TOKEN=gX9kLmN2pQrStUvWxYzAaBbCcDdEeFfGg
ZPDI_HMAC_SECRET=a1b2c3d4e5f6...64-hex-chars...
ZPDI_AES_KEY=xK3mN7pQ...base64-key...==       # omit if not using AES

# Node identity (appears in every payload's "node" field)
ZPDI_NODE_ID=dslv-zpdi/mobile-tier2
```

> **Note on `ws://` vs `wss://`:** For a server on the same local network you can use plain `ws://`. For a remote server always use `wss://` with a valid TLS certificate. See [TLS setup](#tls--wss-setup) below.

### Running the Tier-1 server

On the machine that will receive data from this mobile node (can be the same device, another phone, a laptop, or a server):

```bash
cd /path/to/dslv-zpdi
source .venv/bin/activate

# Set server-side credentials (must match mobile node's .env)
export ZPDI_WSS_TOKEN="gX9kLmN2pQrStUvWxYzAaBbCcDdEeFfGg"
export ZPDI_HMAC_SECRET="a1b2c3d4e5f6...64-hex-chars..."
export ZPDI_AES_KEY="xK3mN7pQ...base64-key...=="   # optional

# Optional: bind address and port
export ZPDI_SERVER_HOST=0.0.0.0
export ZPDI_SERVER_PORT=8443

# Start the server
python3 tier1_ingestion_server.py
```

The server logs one line per accepted packet:
```
2026-05-30 16:00:01 INFO zpdi.tier1: ACCEPTED node=dslv-zpdi/mobile-tier2 modality=accel r_smooth=0.214 stream=SECONDARY
```

Rejected packets (bad HMAC, tampered digest, wrong token) are logged at WARNING with the reason and are never written to the secondary log.

#### Running both on the same Pixel 9 Pro XL

```bash
# Terminal 1 — inside proot
python3 tier1_ingestion_server.py

# Terminal 2 — inside proot
python3 zpdi_mobile_node.py
# or use the supervised launcher:
bash launch_daemon.sh
```

Set `ZPDI_WSS_URI=ws://127.0.0.1:8443/ingest` in `.env` when co-locating.

### TLS / WSS setup

For remote deployments, terminate TLS at the server. Generate a self-signed cert for development:

```bash
openssl req -x509 -newkey rsa:4096 -keyout key.pem -out cert.pem \
    -days 365 -nodes -subj "/CN=zpdi-tier1"
```

Then add to the server's environment:
```dotenv
ZPDI_SERVER_TLS_CERT=/path/to/cert.pem
ZPDI_SERVER_TLS_KEY=/path/to/key.pem
```

And point the mobile node at `wss://` with the CA bundle if self-signed:
```dotenv
ZPDI_WSS_URI=wss://192.168.1.100:8443/ingest
ZPDI_WSS_CA_BUNDLE=/path/to/cert.pem
```

For a publicly trusted cert (Let's Encrypt, etc.) leave `ZPDI_WSS_CA_BUNDLE` unset — the system trust store is used automatically.

---

## Environment variable reference

### Mobile node (`zpdi_mobile_node.py`)

| Variable | Default | Description |
|---|---|---|
| `ZPDI_WSS_URI` | `wss://edge.placeholder.invalid:8443/ingest` | Tier-1 server WebSocket address |
| `ZPDI_WSS_TOKEN` | *(empty)* | Bearer token sent in `Authorization` header at connect |
| `ZPDI_HMAC_SECRET` | *(empty)* | Shared secret for HMAC-SHA256 payload signing |
| `ZPDI_AES_KEY` | *(empty)* | Base64-encoded 32-byte AES-256-GCM key (omit to disable encryption) |
| `ZPDI_WSS_CA_BUNDLE` | *(system trust store)* | Path to CA cert PEM for self-signed Tier-1 server |
| `ZPDI_NODE_ID` | `dslv-zpdi/mobile-tier2` | Node identity string embedded in every payload |
| `ZPDI_HDF5_PATH` | `./data/zpdi_stream.h5` | Primary HDF5 path (intentionally stays empty for Tier-2) |
| `ZPDI_SQLITE_PATH` | `./data/zpdi_cache.db` | SQLite WAL cache for web API |
| `ZPDI_FALLBACK_LOG` | `./logs/zpdi_fallback.jsonl` | Local JSONL fallback when WSS is down |
| `ZPDI_HEALTH_LOG` | `./logs/health.jsonl` | Supervisor heartbeat log (written every 30s) |
| `ZPDI_STREAM_DELAY_MS` | `250` | Polling interval passed to `termux-sensor -d` |
| `ZPDI_GPS_INTERVAL_S` | `15.0` | How often the GPS poller requests a new fix |
| `ZPDI_GPS_TIMEOUT_S` | `10.0` | Per-provider timeout for a single `termux-location` call |
| `ZPDI_GPS_ACCURACY_M` | `50.0` | Accuracy threshold (metres) — fixes worse than this are kept as tentative |
| `ZPDI_LOG_LEVEL` | `INFO` | Python logging level (`DEBUG`, `INFO`, `WARNING`) |

### Tier-1 server (`tier1_ingestion_server.py`)

| Variable | Default | Description |
|---|---|---|
| `ZPDI_WSS_TOKEN` | *(empty — accepts all)* | Bearer token required in `Authorization` header |
| `ZPDI_HMAC_SECRET` | *(empty — disabled)* | Shared HMAC-SHA256 secret; if set, unsigned payloads are rejected |
| `ZPDI_AES_KEY` | *(empty — disabled)* | Base64 32-byte AES-256-GCM key; required if mobile node encrypts |
| `ZPDI_SERVER_HOST` | `0.0.0.0` | Bind address |
| `ZPDI_SERVER_PORT` | `8443` | Bind port |
| `ZPDI_SERVER_TLS_CERT` | *(plain WS)* | Path to TLS certificate PEM |
| `ZPDI_SERVER_TLS_KEY` | *(plain WS)* | Path to TLS private key PEM |
| `ZPDI_SECONDARY_LOG` | `./logs/tier1_secondary.jsonl` | Accepted payload archive |
| `ZPDI_LOG_LEVEL` | `INFO` | Logging level |

---

## Running the node

### Interactive (development / debugging)

```bash
cd /root/dslv-zpdi
source .venv/bin/activate
python3 zpdi_mobile_node.py
```

Logs stream to stdout. Press Ctrl+C for a clean shutdown — the daemon drains its queues before exiting.

### Supervised (production)

The supervisor (`supervisor.sh`) runs inside the proot as a foreground process, restarts the daemon on crash with exponential backoff (2 s → 4 → 8 → … → 60 s), and force-kills the daemon if the health log goes stale for more than 90 seconds.

```bash
# From inside the proot OR from Termux
bash /root/dslv-zpdi/launch_daemon.sh
```

### Automatic start on device boot

`Termux:Boot` fires `~/.termux/boot/99-start-zpdi.sh` on every Android boot, which launches the supervisor in an independent proot session. No manual action needed after a reboot — verify with:

```bash
tail -f /root/dslv-zpdi/logs/supervisor.log
```

### Checking status

```bash
# Live supervisor + daemon events
tail -f /root/dslv-zpdi/logs/supervisor.log

# Health heartbeat (written every 30s by the daemon)
tail -f /root/dslv-zpdi/logs/health.jsonl | python3 -m json.tool

# Live secondary stream (one JSON line per accepted packet)
tail -f /root/dslv-zpdi/logs/zpdi_fallback.jsonl | python3 -m json.tool

# Packet count in secondary stream
wc -l /root/dslv-zpdi/logs/zpdi_fallback.jsonl

# Primary HDF5 row count (should be 0 for Tier-2)
python3 -c "
import h5py
with h5py.File('data/zpdi_stream.h5', 'r', swmr=True) as f:
    print(f['payloads'].shape[0], 'rows')
"
```

---

## Sensor suite and GPS

### Sensors polled (Pixel 9 Pro XL)

| Sensor name | Modality | Phase extraction | Notes |
|---|---|---|---|
| ICM45631 Accelerometer | `accel` | Hilbert on magnitude | Primary motion sensor |
| MMC5616 Magnetometer | `magnetometer` | Hilbert on magnitude | Magnetic field anomalies |
| ICP20100 Pressure Sensor | `barometer` | None (scalar reference) | Atmospheric baseline |
| ICM45631 Gyroscope | `gyroscope` | Hilbert on magnitude | Angular velocity |
| Rotation Vector Sensor | `rotation_vector` | None — feeds orientation tracker | Quaternion fused by Android |
| Geomagnetic Rotation Vector | `geomagnetic_rotation` | None — feeds orientation tracker | Lower-power orientation |
| Gravity Sensor | `gravity` | Hilbert on magnitude | Gravity direction vector |

Phase extraction uses a rolling 32-sample FFT-based Hilbert transform computed in Layer 1. The rotation-vector sensors do not produce phase vectors — they feed the `OrientationTracker` (SPEC-006.6) which computes a quaternion-stability weight that scales `r_local` and `r_smooth` downward during device motion.

### GPS enrichment

When `termux-location` is available and permissions are granted, the GPS poller runs as a background task and attaches the latest fix to each payload (`latitude`, `longitude`, `altitude`, `accuracy`, `location_provider`). The poller tries providers in priority order: `gps` → `network` → `passive`.

To enable GPS:
1. Grant Location permission to Termux:API in Android Settings.
2. Set `ZPDI_GPS_INTERVAL_S`, `ZPDI_GPS_TIMEOUT_S`, and `ZPDI_GPS_ACCURACY_M` as needed (see [Environment variables](#environment-variable-reference)).

GPS data in the payload **does not affect the trust state** — this is a Tier-2 node and will always be `SECONDARY_QUARANTINED`. The location data is exploratory metadata for swarm correlation.

---

## Reading the output streams

### Secondary JSONL (`logs/zpdi_fallback.jsonl`)

Every payload that the transport consumer processes is written here, whether or not the WSS connection to the Tier-1 server succeeded. One JSON object per line.

Key fields in each record:

| Field | Description |
|---|---|
| `node` | Node identity string |
| `modality` | Sensor type (`accel`, `gyroscope`, etc.) |
| `trust_state` | Always `SECONDARY_QUARANTINED` for this node |
| `hardware_tier` | Always `2` |
| `r_local` | Instantaneous Kuramoto order parameter (0–1) |
| `r_smooth` | EWMA-smoothed coherence score (0–1) |
| `r_global` | Fleet-weighted global coherence (0 in single-node deployment) |
| `route.stream` | Always `SECONDARY` |
| `route.reason` | `anomalous_candidate_tier2` / `structured_background_tier2` / `noise_tier2` |
| `sha256` | SHA-256 of canonical payload bytes |
| `hmac` | HMAC-SHA256 signature (present when `ZPDI_HMAC_SECRET` is set) |
| `timestamps.wall_ns` | Wall-clock nanoseconds (Unix epoch) |
| `timestamps.monotonic_ns` | Monotonic nanoseconds (for local ordering) |
| `latitude`, `longitude` | GPS fix if available |
| `extracted_phases` | Hilbert phase vector (empty for barometer / rotation sensors) |

### Coherence score interpretation

| `r_smooth` range | `route.reason` | Meaning |
|---|---|---|
| ≥ 0.40 | `anomalous_candidate_tier2` | Strong phase coherence — potential signal of interest |
| 0.15 – 0.39 | `structured_background_tier2` | Moderate coherence — structured but sub-threshold |
| < 0.15 | `noise_tier2` | Incoherent noise floor |

Because orientation weighting is applied, `r_smooth` values during active device motion will be lower than during stationary measurements. Keep the device still for the highest-quality coherence readings.

### Log rotation

The secondary JSONL log auto-rotates at 10 MB, keeping up to 5 gzip-compressed backups (`zpdi_fallback.jsonl.1.gz` through `.5.gz`). No manual intervention needed.

---

## Web API

The FastAPI web server (`zpdi_web_server.py`) reads from the SQLite WAL cache and exposes the latest sensor state via HTTP and WebSocket.

```bash
# Start the web server (inside proot)
source .venv/bin/activate
python3 zpdi_web_server.py
```

> **Important:** The web server must bind to `127.0.0.1` (default) inside the proot. Android blocks external interfaces for proot processes — binding to `0.0.0.0` causes permission error 13. Access the API from the same device via `localhost`.

### Endpoints

| Method | Path | Description |
|---|---|---|
| `GET` | `/health` | Node status and timestamp of last sample |
| `GET` | `/latest` | Full JSON of the most recent sensor payload |
| `WS` | `/ws/live` | WebSocket stream of live payloads as they arrive |

```bash
# Health check
curl http://127.0.0.1:8000/health

# Latest payload (pretty-printed)
curl http://127.0.0.1:8000/latest | python3 -m json.tool

# Live stream (requires wscat or similar)
wscat -c ws://127.0.0.1:8000/ws/live
```

---

## Health monitoring and supervision

### Health log fields

The daemon writes a JSON record to `logs/health.jsonl` every 30 seconds:

```json
{
  "ts_utc": 1748621461.3,
  "pid": 6981,
  "sensor_alive": true,
  "queue_depths": [0, 0, 0],
  "wss_connected": false,
  "wss_circuit_open": false,
  "gps_fix": {
    "latitude": 37.7749,
    "longitude": -122.4194,
    "altitude": 12.3,
    "accuracy": 8.5,
    "provider": "gps",
    "ts": 1748621455.1
  }
}
```

| Field | What to watch for |
|---|---|
| `sensor_alive` | `false` for two consecutive ticks means `termux-sensor` is stalling — restart the daemon |
| `queue_depths` | Non-zero for sustained periods means a sink is backing up |
| `wss_connected` | `false` while Tier-1 server should be reachable — check `ZPDI_WSS_URI` |
| `wss_circuit_open` | `true` means 5+ consecutive connect failures; server will retry in 30 s |
| `gps_fix` | `null` means no fix yet — check Termux:API location permission |

### Supervisor watchdog

If `health.jsonl` is not updated for more than 90 seconds, the supervisor sends SIGTERM to the daemon, waits 2 seconds, then SIGKILL, and restarts. The 90-second threshold gives the daemon three missed health ticks before intervention.

### WSS circuit breaker

After 5 consecutive WebSocket connection failures the mobile node opens the circuit breaker for 30 seconds — no connection attempts are made during that window, and all packets fall over to the local JSONL log. This prevents CPU churn and log spam when the Tier-1 server is temporarily unreachable. The breaker resets on the next successful connection.

---

## Tuning for maximum data quality

### Sensor polling rate

```dotenv
ZPDI_STREAM_DELAY_MS=100    # 100ms — near the minimum reliably delivered by Termux:API
ZPDI_STREAM_DELAY_MS=250    # 250ms — default; good balance of throughput and battery
ZPDI_STREAM_DELAY_MS=500    # 500ms — lower power; for background / overnight deployments
```

The Termux:API service caps the true delivery rate at the slowest sensor in the set. Below ~50ms you get no additional samples.

### GPS polling rate

```dotenv
ZPDI_GPS_INTERVAL_S=5.0    # Aggressive — highest location freshness, drains battery faster
ZPDI_GPS_INTERVAL_S=15.0   # Default — good balance
ZPDI_GPS_INTERVAL_S=60.0   # Background deployments or indoor (GPS rarely fixes indoors)
ZPDI_GPS_ACCURACY_M=20.0   # Only accept fixes accurate to 20m (stricter — may reject more)
ZPDI_GPS_ACCURACY_M=100.0  # Accept coarser network fixes — useful indoors
```

### Orientation weighting

Keep the device **stationary and level** for the highest coherence scores. The orientation-stability weight (`w_orient`) is computed from the dot product between consecutive rotation-vector quaternions — any angular velocity between samples reduces `r_local` and `r_smooth` proportionally. A 90° rotation between samples reduces both scores by ~29%.

### Log verbosity

```dotenv
ZPDI_LOG_LEVEL=DEBUG    # Detailed per-packet and WSS connection logs
ZPDI_LOG_LEVEL=INFO     # Default — one line per connection event and health tick
ZPDI_LOG_LEVEL=WARNING  # Quiet — only anomalies and rejections
```

---

## Testing

```bash
cd /root/dslv-zpdi
source .venv/bin/activate

# Full suite (42 tests)
pytest tests/ -v

# SPEC compliance and mobile pipeline only (14 tests, fast)
pytest tests/test_mobile_compliance.py -v -k "not hdf5_run"

# Tier-1 server crypto pipeline only (19 tests, very fast)
pytest tests/test_tier1_server.py -v

# Live integration test — starts the daemon for 12 seconds
pytest tests/test_mobile_compliance.py::test_primary_hdf5_is_empty_after_mobile_run -v
```

---

## Project layout

```
dslv-zpdi/
├── zpdi_mobile_node.py          Tier-2 async daemon (Rev 3.5)
├── tier1_ingestion_server.py    Tier-1 WSS ingestion server (SPEC-008)
├── zpdi_web_server.py           FastAPI REST + WebSocket API
├── zpdi_verifier.py             HDF5 integrity verifier
├── edge_listener_stub.py        Lightweight WSS server stub
├── supervisor.sh                Foreground supervisor with health watchdog
├── launch_daemon.sh             Start supervised daemon from Termux or proot
├── run_node.sh                  One-shot run (no supervisor, for debugging)
├── requirements.txt             Python dependencies
├── .env                         Runtime configuration (gitignored)
│
├── src/
│   ├── layer1_ingestion/
│   │   ├── mobile_ingestion.py  IngestionPayload, Hilbert transform, GPS enrichment
│   │   ├── gps_poller.py        Async termux-location wrapper
│   │   └── payload.py           SensorModality enum
│   ├── layer2_core/
│   │   ├── coherence.py         KCET-ATLAS CoherenceScorer (Kuramoto + EWMA)
│   │   ├── fusion_engine.py     OrientationTracker + apply_orientation_weight
│   │   └── wiring.py            Layer 2 wiring gate
│   └── layer3_telemetry/
│       └── mobile_router.py     Dual-stream router + SecondaryLog
│
├── tests/
│   ├── test_mobile_compliance.py   SPEC-005/006/007 compliance + mobile regressions
│   └── test_tier1_server.py        SPEC-008 crypto pipeline (19 tests)
│
├── data/
│   ├── zpdi_stream.h5           Primary HDF5 (empty for Tier-2)
│   └── zpdi_cache.db            SQLite WAL cache
│
└── logs/
    ├── zpdi_fallback.jsonl      Secondary stream (all Tier-2 packets)
    ├── health.jsonl             30s supervisor heartbeat
    ├── supervisor.log           Supervisor events
    └── daemon.log               Daemon stdout/stderr
```
