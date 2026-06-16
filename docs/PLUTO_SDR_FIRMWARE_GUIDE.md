# PlutoSDR+ Firmware & Setup Guide

## 1. Initial Device Preparation
* The PlutoSDR+ acts as a USB Ethernet device. Plug it directly into your Raspberry Pi 5.
* It will mount a mass storage drive named `PlutoSDR` and create a network interface with the IP `192.168.2.1`.

## 2. Firmware Update
1. Download the latest custom firmware (`pluto.frm`) required for Phase 2A/2B metrology support from Analog Devices or the designated secure repository.
2. Drag and drop `pluto.frm` onto the `PlutoSDR` mass storage drive.
3. Eject the drive. The PlutoSDR+ will automatically reboot. Do not disconnect power during the LED flashing sequence (this indicates the firmware is writing).

## 3. Configuration for DSLV-ZPDI Pipeline
1. SSH into the PlutoSDR+: `ssh root@192.168.2.1` (Default password: `analog`).
2. Verify firmware version: `cat /etc/os-release`.
3. Enable 2R2T (if not default on PlutoSDR+): 
   ```bash
   fw_setenv attr_name compatible
   fw_setenv attr_val ad9361
   reboot
   ```
4. Verify libiio visibility from the Pi 5: `iio_info -u ip:192.168.2.1`

## Troubleshooting

### "Device Not Found" or Network Issues
* **Symptom:** `ping 192.168.2.1` fails.
* **Fix:** Ensure the `rndis_host` and `cdc_ether` kernel modules are loaded on your Debian Trixie Pi 5: `sudo modprobe cdc_ether`.

### High Latency or Jitter
* **Symptom:** Buffer overruns when running `dslv-zpdi-pipeline`.
* **Fix:** Ensure the PlutoSDR+ is connected directly to a high-speed USB 3.0 port on the Pi 5. Do not use a hub.

### Clock Synchronization Failure
* **Symptom:** The pipeline reports phase unlock.
* **Fix:** Ensure the 10 MHz reference signal from the LBE-1421 GPSDO is connected to the PlutoSDR+ external clock input and that the firmware is set to external reference: `fw_setenv ad9361_ext_refclk '<10000000>'`.
