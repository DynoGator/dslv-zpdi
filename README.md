# dslv-zpdi — Tier-1 mobile metrology node

Local scaffold for the dslv-zpdi project, configured for a Debian
`proot-distro` container running on a Pixel 9 Pro XL.

## Layout

| Path | Purpose |
| --- | --- |
| `zpdi_mobile_node.py` | Async daemon: poll → hash → HDF5 + WSS |
| `data/` | HDF5 stream (gitignored) |
| `logs/` | Fallback JSONL log when WSS is down (gitignored) |
| `.githooks/` | Local hook scripts (active via `core.hooksPath`) |
| `.env.example` | Template for the future Secure Storage Token |

## Quick start

```sh
python3 -m venv .venv && . .venv/bin/activate
pip install -r requirements.txt
python3 zpdi_mobile_node.py
```

Sensor polling uses the absolute Termux binary path
`/data/data/com.termux/files/usr/bin/termux-sensor` because the Debian proot
does not inherit Termux's `$PATH`.
