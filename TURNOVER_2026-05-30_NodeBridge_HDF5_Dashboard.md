# DSLV-ZPDI Turnover Notes — 2026-05-30
**Session:** Node Bridging, HDF5 Multi-Node Aggregation & Dashboard Finalisation  
**Version delivered:** 4.7.0  
**Node:** Tier 1 Anchor — Raspberry Pi 5 (16 GB)  
**Operator:** DynoGator / jrfross@gmail.com

---

## Summary of Work Completed

### Phase 1 — Networking & HackRF Boot

| File | Purpose |
|------|---------|
| `config/PiRepo.nmconnection` | NetworkManager AP keyfile — SSID `PiRepo`, WPA2, Pi IP `10.42.0.1/24` |
| `config/dslv-zpdi-hackrf-init.service` | Runs `hackrf_info` once after udev settle; wakes HackRF before preflight |

**To activate the hotspot:**
```bash
sudo cp config/PiRepo.nmconnection /etc/NetworkManager/system-connections/
sudo chmod 600 /etc/NetworkManager/system-connections/PiRepo.nmconnection
sudo nmcli connection reload
sudo nmcli connection up PiRepo
```

**To enable HackRF boot service:**
```bash
sudo cp config/dslv-zpdi-hackrf-init.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now dslv-zpdi-hackrf-init
```

The Pixel 9 Pro XL (GrapheneOS) connects to `PiRepo` using password `2444666667`.  
Once connected, its IP will be in the `10.42.0.x` range (DHCP from NetworkManager shared mode).

---

### Phase 2 — HDF5 Multi-Node Aggregation

**New module:** `src/dslv_zpdi/layer3_telemetry/node_receiver.py`  
Flask micro-service listening on `10.42.0.1:5775`. Accepts:

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/api/v1/ingest` | POST | Standard telemetry from any swarm node |
| `/api/v1/ingest/radoneye` | POST | EcoSense RadonEye Pro staging (SPEC-015 placeholder) |
| `/api/v1/health` | GET | Service health + pipeline stats |

**To enable:**
```bash
# Requires flask in the venv:
source venv/bin/activate && pip install flask

sudo cp config/dslv-zpdi-node-receiver.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now dslv-zpdi-node-receiver
```

**HDF5 integrity (concurrent writes):**  
`HDF5Writer._write_primary` now acquires a `threading.Lock` before writing.  
File version bumped to `3.3`. Each event group now carries a `source_node` attribute
(default `"tier1-anchor"`) identifying the physical node that produced the packet.

**RadonEye Pro integration path:**  
POST to `/api/v1/ingest/radoneye` with:
```json
{
  "source": "EcoSense_RadonEye_Pro",
  "radon_bq_m3": 12.5,
  "timestamp_utc": 1748560000.0,
  "unit_id": "RE200-XXXXXX"
}
```
Packets are staged to `output/secondary/radoneye_staging.jsonl`.  
Promote to primary stream once SPEC-015 calibration baseline is ratified.

---

### Phase 3 — Dashboard Finalisation

**HackRF ON by default:**  
Dashboard now sets `DSLV_DASHBOARD_REAL_SDR=1` at launch.  
Use `--no-real-sdr` to start in simulated mode.

**Web dashboard:** `tools/dashboard/web_server.py`  
Auto-refresh HTML panel at `http://10.42.0.1:8080/` showing system, pipeline,
swarm nodes, and SDR state. Pixel 9 Pro XL can browse this from the PiRepo LAN.

**To enable:**
```bash
sudo cp config/dslv-zpdi-webdash.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now dslv-zpdi-webdash
```

---

### Phase 4 — Testing

- **47/47 tests passing** (previously 46/47 — `test_no_devices_found_raises_driver_unavailable` was failing).
- Fixed `HardwareHAL` fallback: SoapySDR error + no pyhackrf now re-raises the original exception.

---

## Known Limitations / Deferred Items

| Item | Status |
|------|--------|
| SPEC-015 RadonEye calibration baseline | Not yet ratified — RadonEye endpoint is staging-only |
| Web dashboard authentication | None — LAN-only, not exposed to WAN |
| Pixel 9 Pro XL client app | Telemetry sender app is out of scope for this session; the receiver endpoint is ready |
| `psutil` / `flask` in venv | Must be `pip install`ed if not already present (`pip install flask psutil`) |

---

## Service Boot Order (updated)

```
dslv-zpdi-tuning
    └─ dslv-zpdi-hackrf-init   [NEW]
        └─ dslv-zpdi-preflight
            └─ dslv-zpdi (pipeline)
                └─ dslv-zpdi-node-receiver  [NEW]
                └─ dslv-zpdi-webdash        [NEW]
```

---

## Files Changed This Session

```
config/PiRepo.nmconnection                              [NEW]
config/dslv-zpdi-hackrf-init.service                    [NEW]
config/dslv-zpdi-node-receiver.service                  [NEW]
config/dslv-zpdi-webdash.service                        [NEW]
src/dslv_zpdi/layer1_ingestion/hal_hardware.py          [FIXED — fallback re-raise]
src/dslv_zpdi/layer3_telemetry/hdf5_writer.py           [CHANGED — threading.Lock, source_node, v3.3]
src/dslv_zpdi/layer3_telemetry/node_receiver.py         [NEW]
tools/dashboard/app.py                                  [CHANGED — real_sdr default ON]
tools/dashboard/web_server.py                           [NEW]
CHANGELOG.md                                            [UPDATED — v4.7.0]
README.md                                               [REVISED — hardware prereqs, network config]
```
