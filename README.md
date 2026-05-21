# dslv-zpdi — Tier-2 Mobile Swarm Node

> **IMPORTANT:** The mobile node on `main` is a **Tier-2 Swarm deployment**. All data produced by this Pixel 9 Pro XL is exploratory/secondary stream. Institutional-grade primary output requires **Tier-1 Anchor hardware** (Raspberry Pi CM5 + Intel i210-T1 + u-blox PPS, or equivalent GPSDO RF Metrology stack per SPEC-004A.2).

Local scaffold for the dslv-zpdi project, configured for a Debian
`proot-distro` container running on a Pixel 9 Pro XL.

## Layout

| Path | Purpose |
| --- | --- |
| `zpdi_mobile_node.py` | Async daemon: termux-sensor → Layer 1 ingestion → Layer 2 coherence → Layer 3 router → secondary JSONL |
| `src/layer1_ingestion/mobile_ingestion.py` | Layer 1 driver: `IngestionPayload` builder with trust-state validation |
| `src/layer2_core/coherence.py` | Layer 2 engine: KCET-ATLAS `CoherenceScorer` |
| `src/layer2_core/wiring.py` | Layer 2 wiring gate between JSON and coherence engine |
| `src/layer3_telemetry/mobile_router.py` | Layer 3 router: enforces Tier-2 quarantine and coherence categorisation |
| `zpdi_verifier.py` | HDF5 integrity verifier (SWMR-safe) — primary stream only |
| `edge_listener_stub.py` | WSS server stub: ingest + verify provenance |
| `configure_git_auth.sh` | Setup script for GitHub PAT authentication |
| `data/` | HDF5 primary stream (intentionally empty for Tier-2) + SQLite cache |
| `logs/` | `zpdi_fallback.jsonl` secondary exploratory stream + `health.jsonl` watchdog |

## Quick start

1. **Initialize environment**:
   ```sh
   python3 -m venv .venv && . .venv/bin/activate
   pip install -r requirements.txt
   ```

2. **Run the test suite**:
   ```sh
   pytest tests/ -v
   ```

3. **Start the Metrology Node**:
   ```sh
   python3 zpdi_mobile_node.py
   ```

4. **Verify primary HDF5 is empty and secondary JSONL is active**:
   ```sh
   python3 -c "import h5py; print(h5py.File('data/zpdi_stream.h5')['payloads'].shape[0])"
   wc -l logs/zpdi_fallback.jsonl
   ```

## Provenance Verification

The metrology node computes a SHA-256 hash of the canonical JSON payload (excluding the digest itself) and embeds it as the `sha256` field. Both the `edge_listener_stub.py` and the `zpdi_verifier.py` tool re-compute this hash to confirm the integrity of the data stream and the local datastore.

## Git Integration

To prepare the node for pushing data or code to GitHub using a Personal Access Token (PAT):
1. Copy `.env.example` to `.env`.
2. Populate `GITHUB_PAT` with your token.
3. Run `./configure_git_auth.sh`.

Sensor polling uses the absolute Termux binary path
`/data/data/com.termux/files/usr/bin/termux-sensor` because the Debian proot
does not inherit Termux's `$PATH`.
