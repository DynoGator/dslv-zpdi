# Pixel 9 Pro XL Node Setup — Tier 2 Mobile Bridge

**Device:** Google Pixel 9 Pro XL (GrapheneOS)
**Role:** Tier 2 sensor node + internet hotspot
**Date:** 2026-06-05

---

## 1. GrapheneOS Hotspot Configuration

1. Open **Settings → Network & Internet → Hotspot & Tethering**.
2. Enable **Wi-Fi Hotspot**.
3. Set SSID to `PiRepo` (matches Pi 5 expected network).
4. Set a strong WPA3 password.
5. The Pi 5 connects to this hotspot and receives an IP in the `10.42.0.x` range (or whatever subnet GrapheneOS uses; default is often `192.168.x.x` — verify with `ip addr` on the Pi after connection).

> **Note:** If GrapheneOS defaults to a different subnet (e.g., `192.168.43.x`), update `config/deployment.yaml` or the `DSLV_PIXEL_HOST` env variable on the Pi 5 accordingly.

---

## 2. Termux Installation & Environment

Install Termux from F-Droid (not Google Play — the Play Store version is deprecated).

```bash
pkg update
pkg install termux-api python
```

Install the **Termux:API** app from F-Droid as well — it provides the `termux-sensor`, `termux-location`, and `termux-camera-photo` commands.

---

## 3. Termux JSON Publisher (Recommended)

Create `~/zpdi_publisher.py` on the Pixel:

```python
#!/data/data/com.termux/files/usr/bin/python
"""Lightweight JSON telemetry publisher for DSLV-ZPDI Pixel bridge."""
import json, os, subprocess, time, hashlib
from http.server import BaseHTTPRequestHandler, HTTPServer

PORT = 8777


def get_magnetometer():
    try:
        out = subprocess.check_output(
            ["termux-sensor", "-s", "MAGNETOMETER", "-n", "1"],
            text=True, timeout=5,
        )
        data = json.loads(out)
        # termux-sensor returns {sensor: {values: [x,y,z], ...}}
        for sensor_name, sensor_data in data.items():
            return sensor_data.get("values")
    except Exception:
        return None


def get_location():
    try:
        out = subprocess.check_output(
            ["termux-location", "-p", "network"],
            text=True, timeout=10,
        )
        loc = json.loads(out)
        return {
            "lat": loc.get("latitude"),
            "lon": loc.get("longitude"),
            "alt": loc.get("altitude"),
            "accuracy": loc.get("accuracy"),
        }
    except Exception:
        return {}


def get_camera_frame():
    try:
        path = "/data/data/com.termux/files/home/zpdi_frame.jpg"
        subprocess.run(
            ["termux-camera-photo", "-c", "0", path],
            check=True, timeout=10,
        )
        with open(path, "rb") as f:
            h = hashlib.sha256(f.read()).hexdigest()
        return {"hash": h, "path": path}
    except Exception:
        return {}


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/telemetry":
            mag = get_magnetometer()
            gps = get_location()
            cam = get_camera_frame()
            payload = {
                "timestamp_utc": time.time(),
                "magnetometer_ut": mag,
                "gps": gps,
                "camera_frame_hash": cam.get("hash"),
                "camera_frame_path": cam.get("path"),
            }
            body = json.dumps(payload).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(body)
        else:
            self.send_response(404)
            self.end_headers()

    def log_message(self, fmt, *args):
        pass  # suppress default logging


if __name__ == "__main__":
    print(f"[*] Pixel publisher listening on 0.0.0.0:{PORT}")
    HTTPServer(("0.0.0.0", PORT), Handler).serve_forever()
```

Make it executable and run:

```bash
chmod +x ~/zpdi_publisher.py
~/zpdi_publisher.py
```

For auto-start on boot, use **Termux:Boot** (install from F-Droid):

```bash
mkdir -p ~/.termux/boot
cat > ~/.termux/boot/start-zpdi.sh << 'EOF'
#!/data/data/com.termux/files/usr/bin/sh
termux-wake-lock
python /data/data/com.termux/files/home/zpdi_publisher.py &
EOF
chmod +x ~/.termux/boot/start-zpdi.sh
```

---

## 4. SSH Pull Alternative (Documented, Not Default)

If you prefer SSH over HTTP:

1. Install `openssh` in Termux: `pkg install openssh`
2. Start sshd: `sshd -p 8022`
3. Set password: `passwd`
4. From the Pi 5:
   ```bash
   ssh -p 8022 u0_axxx@10.42.0.x "termux-sensor -s MAGNETOMETER -n 1"
   ```

The HTTP publisher is preferred because it decouples transport from command execution and is easier to retry/reconnect.

---

## 5. Pi 5 Network Setup

The Pi 5 should connect to the Pixel hotspot automatically via NetworkManager:

```bash
sudo nmcli device wifi list
sudo nmcli device wifi connect "PiRepo" password "YOUR_HOTSPOT_PASSWORD"
```

Verify connectivity:

```bash
ping -c 3 <pixel_ip>
curl http://<pixel_ip>:8777/telemetry
```

The `PixelNodeBridge` defaults to `10.42.0.2` but can be configured via:
- `config/deployment.yaml` key `pixel_node.host`
- Environment variable `DSLV_PIXEL_HOST`

---

## 6. Privacy & Security Posture

- Camera frames are **low-resolution** by design (Termux default ~640×480).
- Only the **SHA-256 hash** of the frame is transmitted to the Pi 5 over HTTP; the frame file stays on the Pixel unless explicitly pulled.
- No GPS coordinates leave the node in any customer-facing output; they are Tier 2 context only.
- The Pixel uplink is **opt-in per session** — the `uplink_manager.py` exposes a toggle.
