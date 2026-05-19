# dslv-zpdi — Tier-1 mobile metrology node

Local scaffold for the dslv-zpdi project, configured for a Debian
`proot-distro` container running on a Pixel 9 Pro XL.

## Layout

| Path | Purpose |
| --- | --- |
| `zpdi_mobile_node.py` | Async daemon: poll → hash → HDF5 + WSS |
| `zpdi_verifier.py` | HDF5 integrity verifier (SWMR-safe) |
| `edge_listener_stub.py` | WSS server stub: ingest + verify provenance |
| `configure_git_auth.sh` | Setup script for GitHub PAT authentication |
| `data/` | HDF5 stream (gitignored) |
| `logs/` | Fallback JSONL log when WSS is down (gitignored) |

## Quick start

1. **Initialize environment**:
   ```sh
   python3 -m venv .venv && . .venv/bin/activate
   pip install -r requirements.txt
   ```

2. **Start the Edge Listener Stub** (for testing):
   ```sh
   python3 edge_listener_stub.py
   ```

3. **Start the Metrology Node**:
   ```sh
   # Point the node to the local stub
   export ZPDI_WSS_URI=ws://localhost:8443
   python3 zpdi_mobile_node.py
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
