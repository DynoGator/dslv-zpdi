# KIMI Questions — Phase 2B

**Date:** 2026-06-05
**Agent:** KIMI_CODE_CLI

---

## Q1: Mobile branches have unrelated histories — mechanical merge rejected

**Context:** `feat/mobile-architecture-compliance` and `feat/mobile-node-hardening-phase2` share zero common ancestors with `main`. They use a flat `src/layerX/` package structure while `main` uses `src/dslv_zpdi/layerX/`. A mechanical merge would duplicate/destroy the package tree.

**Options:**
- **A.** Do not merge. Port unique algorithms manually during Phase 2B if needed. (Recommended)
- **B.** Force-merge with `--allow-unrelated-histories`, then spend hours resolving directory-level conflicts and deduplicating files.
- **C.** Ask PI whether to rebase the mobile branches onto main (rewrites published history — violates protocol).

**My recommendation:** Option A. The mobile branches are from a pre-v4 repo epoch. Main already reimplemented their core intent (node receiver, Tier-2 quarantine, Pixel bridging) with a superior structure. Unique files like `fusion_engine.py` and `gps_poller.py` can be ported surgically if the Pixel bridge design needs them.

**PI action needed:** Confirm Option A is acceptable, or explicitly request a specific file from the mobile branches be ported.

---

## Q2: LBE-1421 dual-output wiring — second output role

**Context:** The tasking order says "Output 1 → HackRF CLKIN; the second output is available as an independent reference." The README says "LBE-1421 `Output` → HackRF `CLKIN`" (vague on which output). The living master says "10 MHz reference signal from LBE-1421 `Out2` port → HackRF One `CLKIN`" and "1 PPS signal from LBE-1421 `Out1` port → Raspberry Pi 5 GPIO 18".

**Observation:** If Out2 is the 10 MHz reference and Out1 is 1 PPS, then the "second output" (Out2) is already used for HackRF. But the tasking says Output 1 → HackRF CLKIN and the second output is spare. There's a naming mismatch.

**My read:** The living master is the more detailed doc. Out1 = 1 PPS to Pi GPIO. Out2 = 10 MHz to HackRF CLKIN. The tasking order's "dual-output" point is that the LBE-1421 has TWO independent outputs (unlike the old LBE-1420 single-output). The second output (Out2) is the 10 MHz, and it's independent from Out1. This means you could repurpose Out2 to a different frequency or use it as a verification tap.

**Decision made:** I will document that Out2 is the 10 MHz reference to HackRF CLKIN, and that because the LBE-1421 has two independent outputs, Out2 can be reconfigured (e.g., to a second frequency for verification) without affecting the 1 PPS on Out1. I will also add a runtime timing-health cross-check that compares PPS timestamps against the NMEA-reported UTC to detect GPSDO health degradation.

**PI action needed:** None unless my interpretation of Out1/Out2 roles is wrong.

---

## Q3: Pixel 9 Pro XL IP address mismatch

**Context:** The README says the Pixel connects to `PiRepo` Wi-Fi hotspot and receives `10.42.0.x`. The most recent turnover says the Pixel was integrated at `10.128.24.165`. These are different subnets.

**My assumption:** `10.128.24.165` was a prior Wi-Fi LAN address before the PiRepo hotspot was set up. The current canonical network is `10.42.0.1/24` (Pi 5 static) with Pixel as DHCP client. The uplink manager and Pixel bridge should default to `10.42.0.x` but be configurable.

**Decision made:** I will make the Pixel subnet configurable via `config/deployment.yaml` with a default of `10.42.0.0/24`, avoiding hard-coding either address.

**PI action needed:** None unless the Pixel is currently on a different network than PiRepo.
