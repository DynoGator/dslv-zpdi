"""DSLV-ZPDI auto-email: bundle tier 1 + tier 2 data and send.

Reads the email config from ~/.config/dslv-zpdi/email.yaml (or the
example config), aggregates the latest primary HDF5 + secondary JSONL,
optionally regenerates the satellite map, bundles everything into a
.tar.gz, and sends to the configured recipients via the configured
backend (Gmail by default).

Invoke via the desktop icon (tools/mailer/send_data.sh) or directly:
    venv/bin/python tools/mailer/send_data.py --config <path> --dry-run
"""

from __future__ import annotations

import argparse
import datetime as dt
import getpass
import hashlib
import io
import json
import os
import socket
import subprocess
import sys
import tarfile
from email.message import EmailMessage
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from mailer import backends  # type: ignore  # noqa: E402

try:
    import yaml
    _HAVE_YAML = True
except Exception:
    _HAVE_YAML = False


REPO = Path(__file__).resolve().parents[2]
PRIMARY_DIR = REPO / "output" / "primary"
SECONDARY_FILE = REPO / "output" / "secondary" / "quarantine.jsonl"
MAP_PATH = Path.home() / ".local" / "share" / "dslv-zpdi" / "map.html"

CONFIG_CANDIDATES = [
    Path.home() / ".config" / "dslv-zpdi" / "email.yaml",
    REPO / "config" / "email.yaml",
    REPO / "config" / "email.example.yaml",
]


def _load_yaml(path: Path) -> dict:
    if _HAVE_YAML:
        return yaml.safe_load(path.read_text()) or {}
    # Minimal fallback parser - handles the example file shape only.
    out: dict = {}
    current_list_key: str | None = None
    for raw in path.read_text().splitlines():
        line = raw.split("#", 1)[0].rstrip()
        if not line:
            continue
        if line.lstrip().startswith("- "):
            item = line.lstrip()[2:].strip().strip('"').strip("'")
            if current_list_key:
                out.setdefault(current_list_key, []).append(item)
            continue
        if ":" not in line:
            continue
        k, _, v = line.partition(":")
        k = k.strip()
        v = v.strip()
        if not v:
            current_list_key = k
            out.setdefault(k, [])
            continue
        current_list_key = None
        v = v.strip('"').strip("'")
        if v.lower() in ("true", "false"):
            out[k] = v.lower() == "true"
            continue
        try:
            out[k] = int(v); continue
        except ValueError:
            pass
        try:
            out[k] = float(v); continue
        except ValueError:
            pass
        out[k] = v
    return out


def load_config(override: Path | None) -> tuple[dict, Path]:
    paths = [override] if override else CONFIG_CANDIDATES
    for p in paths:
        if p and p.exists():
            return _load_yaml(p), p
    raise FileNotFoundError(
        "No email config found. Copy config/email.example.yaml to "
        "~/.config/dslv-zpdi/email.yaml and fill it in."
    )


def _latest_primary() -> Path | None:
    files = sorted(PRIMARY_DIR.glob("*.h5"), key=lambda p: p.stat().st_mtime, reverse=True)
    return files[0] if files else None


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _regen_map() -> Path | None:
    script = REPO / "tools" / "mapping" / "render_map.py"
    if not script.exists():
        return None
    venv_py = REPO / "venv" / "bin" / "python"
    py = str(venv_py) if venv_py.exists() else sys.executable
    try:
        subprocess.run(
            [py, str(script), "--out", str(MAP_PATH),
             "--max-primary", "2000", "--max-secondary", "2000"],
            check=True, cwd=str(REPO), timeout=120,
        )
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired) as e:
        print(f"[email] WARN: map regen failed: {e}", file=sys.stderr)
        return None
    return MAP_PATH if MAP_PATH.exists() else None


def build_bundle(cfg: dict) -> tuple[bytes, dict]:
    """Return (tar.gz bytes, manifest dict)."""
    buf = io.BytesIO()
    manifest: dict = {
        "generated_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
        "host": socket.gethostname(),
        "user": getpass.getuser(),
        "files": [],
    }

    max_mb = float(cfg.get("max_attachment_mb", 20))
    cap_bytes = int(max_mb * 1024 * 1024)

    with tarfile.open(fileobj=buf, mode="w:gz") as tar:
        def _add(path: Path, arcname: str, category: str):
            sz = path.stat().st_size
            if sz > cap_bytes:
                manifest["files"].append({
                    "arcname": arcname, "category": category,
                    "bytes": sz, "included": False, "reason": "exceeds max_attachment_mb",
                })
                return
            tar.add(str(path), arcname=arcname)
            manifest["files"].append({
                "arcname": arcname, "category": category,
                "bytes": sz, "included": True, "sha256": _sha256(path),
            })

        if cfg.get("include_primary", True):
            latest = _latest_primary()
            if latest:
                _add(latest, f"primary/{latest.name}", "primary")

        if cfg.get("include_secondary", True) and SECONDARY_FILE.exists():
            _add(SECONDARY_FILE, f"secondary/{SECONDARY_FILE.name}", "secondary")

        if cfg.get("include_map", True):
            if not MAP_PATH.exists():
                _regen_map()
            elif (dt.datetime.now().timestamp() - MAP_PATH.stat().st_mtime) > 3600:
                _regen_map()
            if MAP_PATH.exists():
                _add(MAP_PATH, "map/map.html", "map")

        # Embed manifest last so it reflects what went in.
        manifest_bytes = json.dumps(manifest, indent=2).encode()
        info = tarfile.TarInfo(name="manifest.json")
        info.size = len(manifest_bytes)
        tar.addfile(info, io.BytesIO(manifest_bytes))

    return buf.getvalue(), manifest


def build_message(cfg: dict, tarball: bytes, manifest: dict) -> EmailMessage:
    recipients = cfg.get("recipients") or []
    if not recipients:
        raise ValueError("No recipients configured.")

    prefix = cfg.get("subject_prefix") or "[DSLV-ZPDI]"
    ts = dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    host = socket.gethostname()
    subject = f"{prefix} Telemetry bundle {ts} - {host}"

    lines = [
        f"DSLV-ZPDI automated telemetry bundle",
        f"Host:       {host}",
        f"Generated:  {manifest['generated_utc']}",
        "",
        "Bundle contents:",
    ]
    for entry in manifest["files"]:
        mb = entry["bytes"] / (1024 * 1024)
        if entry["included"]:
            lines.append(f"  [x] {entry['arcname']:40s} {mb:7.2f} MB   ({entry['category']})")
        else:
            lines.append(f"  [ ] {entry['arcname']:40s} {mb:7.2f} MB   SKIPPED: {entry.get('reason','')}")
    lines += [
        "",
        "Tier 1 (primary): institutional HDF5 - coherence scores, timestamps.",
        "Tier 2 (secondary): JSONL quarantine - pre-baseline / rejected events.",
        "map/map.html is self-contained - open in any browser to see the",
        "interactive satellite map with pinned events.",
        "",
        "- DSLV-ZPDI auto-email",
    ]

    msg = EmailMessage()
    msg["Subject"] = subject
    from_name = cfg.get("from_name") or "DSLV-ZPDI"
    from_addr = cfg.get("smtp_user") or "dslv-zpdi@localhost"
    msg["From"] = f"{from_name} <{from_addr}>"
    msg["To"] = ", ".join(recipients)
    msg.set_content("\n".join(lines))
    fname = f"dslv-zpdi-bundle-{dt.datetime.now().strftime('%Y%m%dT%H%M%S')}.tar.gz"
    msg.add_attachment(tarball, maintype="application", subtype="gzip", filename=fname)
    return msg


def main():
    ap = argparse.ArgumentParser(description="DSLV-ZPDI email sender")
    ap.add_argument("--config", type=Path, help="override path to email.yaml")
    ap.add_argument("--dry-run", action="store_true", help="build but don't send")
    ap.add_argument("--regen-map", action="store_true", help="force regenerate the map")
    args = ap.parse_args()

    cfg, cfg_path = load_config(args.config)
    print(f"[email] config: {cfg_path}")

    if args.regen_map:
        _regen_map()

    if not cfg.get("smtp_password") and not args.dry_run:
        cfg["smtp_password"] = getpass.getpass("Gmail App Password: ")

    tarball, manifest = build_bundle(cfg)
    print(f"[email] bundle: {len(tarball)/1024/1024:.2f} MB, "
          f"files={len(manifest['files'])}")

    msg = build_message(cfg, tarball, manifest)
    print(f"[email] subject: {msg['Subject']}")
    print(f"[email] to: {msg['To']}")

    if args.dry_run:
        print("[email] DRY RUN - not sending")
        return

    try:
        backends.dispatch(msg, cfg)
    except backends.SendError as e:
        print(f"[email] FAIL: {e}", file=sys.stderr)
        sys.exit(1)
    print("[email] sent OK")


if __name__ == "__main__":
    main()
