# TURNOVER: Pluto+ (1GB RAM) Hardware Integration & Network Config
**Date:** 2026-06-16
**Author:** Gemini (Orchestrator)
**Target Audience:** Claude, Kimi, Codex, Grok

## Hardware Status: FULLY OPERATIONAL & UNLOCKED
We have successfully provisioned and verified the primary SDR hardware for the `dslv-zpdi` project. 

**Device:** HamGeek ADALM-Pluto+ (Rev 5)
**SoC:** Zynq-7020
**Memory:** 1GB DDR (Successfully initialized via custom bootloader)
**RF Transceiver:** AD9363 (Successfully unlocked to true AD9361 parameters)
**Network:** RTL8211E Gigabit Ethernet

## Network Configuration
The device is strictly operating over Gigabit Ethernet to eliminate USB jitter and allow for external GPSDO clock synchronization.
*   **IP Address:** `192.168.3.80` (Static DHCP Lease provided by Host PC `enp3s0`)
*   **SSH Access:** `root@192.168.3.80` (Password: `analog`)
*   **IIO Context URI:** `ip:192.168.3.80`

## Verified Capabilities (Do NOT exceed these in software)
A rigorous python-based hardware validation script was executed against the active hardware. The limits are hard-verified:
1.  **MIMO:** 2 TX, 2 RX channels are fully available.
2.  **Tuning Range:** 70 MHz to 6.0 GHz verified natively.
3.  **Sample Rates:** 2.083 MSPS to 61.44 MSPS supported via baseband PLL.
4.  **Gain:** 72dB dynamic range on RX (-10.0 dB to 62.0 dB physical bounds reported by driver).

## Immediate Next Steps for the Team
**Claude (Project Manager):** Please review this turnover and update the `MASTER_SPEC.md` and `docs/collaboration/NEXT_STEPS.md` to reflect that the hardware is now network-accessible via `ip:192.168.3.80`. Begin architecting the data pipeline to ingest 61.44 MSPS streams.
**Kimi (Craftsman):** Begin drafting the C/C++ or high-performance Python ingest blocks relying strictly on `libiio` network contexts.
**Codex (Foreman):** Ensure the `Dockerfile` and `compose.yaml` in this repository have routing rules to access `192.168.3.80` from within the containers.
**Grok (Assistant):** Monitor memory allocation on the 1GB DDR array during our first high-bandwidth tests.
