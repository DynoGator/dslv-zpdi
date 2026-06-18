# PlutoSDR+ Firmware & Setup Guide

> **Canonical Tier-1 address:** `ip:192.168.3.80` (Gigabit Ethernet via the Tezuka-Libre firmware).

## 1. Initial Device Preparation
* The HamGeek PlutoSDR+ used in the Tier-1 build runs the **Tezuka-Libre** firmware and exposes a Gigabit Ethernet interface.
* Connect the PlutoSDR+ to the Raspberry Pi 5 via Ethernet or a USB-to-Ethernet adapter on a USB 3.0 port.
* Configure the Pi 5 host interface on the `192.168.3.0/24` subnet (e.g. static address `192.168.3.10/24`). The PlutoSDR+ default address is `192.168.3.80`.

## 2. Firmware Update
1. Download the latest Tezuka-Libre firmware (`pluto.frm`) required for Phase 2A/2B metrology support from the designated secure repository.
2. If the device still exposes mass storage, drag and drop `pluto.frm` onto the `PlutoSDR` drive, eject it, and allow the device to reboot. If mass storage is not available, use the SSH-based update path documented with the firmware release.
3. After reboot, verify the device is reachable at `192.168.3.80`:
   ```bash
   ping 192.168.3.80
   iio_info -u ip:192.168.3.80
   ```

## 3. Configuration for DSLV-ZPDI Pipeline
1. SSH into the PlutoSDR+: `ssh root@192.168.3.80` (default password may vary by firmware; consult the Tezuka-Libre release notes).
2. Verify firmware version: `cat /etc/os-release`.
3. Confirm the PHY is reported as `ad9361-phy`:
   ```bash
   iio_attr -u ip:192.168.3.80 -c ad9361-phy name
   ```
4. Verify libiio visibility from the Pi 5:
   ```bash
   python -c "import iio; print(iio.Context('ip:192.168.3.80').name)"
   ```

## Troubleshooting

### "Device Not Found" or Network Issues
* **Symptom:** `ping 192.168.3.80` fails.
* **Fix:** Verify the Pi 5 interface is on the `192.168.3.0/24` subnet and that the link is up. If using USB Ethernet, ensure the adapter is connected to a USB 3.0 port and the `cdc_ether`/`ax88179_178a` driver is loaded as appropriate.

### High Latency or Jitter
* **Symptom:** Buffer overruns when running `dslv-zpdi-pipeline`.
* **Fix:** Ensure the PlutoSDR+ is connected via Gigabit Ethernet or a high-speed USB 3.0 Ethernet adapter. Do not use a hub. Verify the host CPU governor is set to `performance`.

### Clock Synchronization Failure
* **Symptom:** The pipeline reports phase unlock.
* **Fix:** Ensure the 10 MHz reference signal from the LBE-1421 GPSDO is connected to the PlutoSDR+ `EXT_REF_CLK` input and that the firmware is configured for external reference. Consult the Tezuka-Libre release notes for the exact `fw_setenv` keys; the canonical reference frequency is `10000000` Hz.
