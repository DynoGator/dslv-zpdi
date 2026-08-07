# DSLV-ZPDI Dashboard User Guide

Welcome to the DSLV-ZPDI Interactive Metrology Dashboard. This highly polished, field-grade interface allows operators to actively monitor and control the Tier-1 Metrology Anchor Node and its connected Swarm (Tier-2 nodes).

## Overview
The dashboard features real-time polling to ensure maximum situational awareness.

### System Panel
*   **Hostname / Pi IP**: Identifies the current anchor node on the LAN.
*   **CPU / RAM / Temp**: Metrics for Pi hardware health. If these turn yellow or red, consider adding active cooling.
*   **System Poweroff**: Issues a `sudo shutdown -P now` command to safely down the anchor. Use this only at the end of a session.

### Pipeline Panel
*   **Service**: Displays ACTIVE if the ingestion server is running.
*   **Timing**: Confirms Chrony synchronization (LOCKED vs DEGRADED).
*   **Writes / Integrity**: Shows the amount of primary telemetry written and highlights any ingestion faults.

### Swarm Nodes Panel
*   **Tier 1 Anchor**: Shows the status of this local device.
*   **Tier 2 Devices**: Probes known devices (e.g., Pixel 9 Pro XL) to ensure they are connected and responsive on the network.

### SDR Hardware & Demodulation
*   **Active Device Selection**: Allows you to instantly switch the pipeline between PlutoSDR (IIO), LibreSDR, and HackRF (legacy/optional) One. 
*   **Hardware Status**: Shows if the device is reachable and its current tuning.
*   **Demodulation Presets**: We have loaded standard frequency profiles for field use:
    *   **VHF Airband (120 MHz, AM)**: Best for listening to local aviation traffic.
    *   **Marine VHF (156.8 MHz, FM)**: Standard marine hail and distress (Channel 16).
    *   **NOAA Wx (162.4 MHz, FM)**: National Weather Service continuous broadcasts.
    *   **ADS-B (1090 MHz, RAW)**: For aircraft tracking pipelines.
*   **Custom Tuning**: Enter a frequency (in MHz) and mode (WFM, NFM, AM, USB, LSB, RAW) to apply an on-the-fly tuning configuration.
*   **Toggle Audio Listen**: Start or stop simulated/streamed audio directly from the dashboard interface for monitoring.
*   **Soft Reboot Hardware**: Issues a reset command to the USB host/device if the SDR locks up in the field.

### UPS / Power
*   **Status**: Healthy / Critical warnings.
*   **Battery & Voltage**: Keeps track of your uninterruptible power supply in field deployments.

---
*Created automatically during metrology stack refinement.*
