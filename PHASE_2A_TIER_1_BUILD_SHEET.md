# DSLV-ZPDI Phase 2A Tier 1 Build Sheet

**Project source:** DynoGator/dslv-zpdi
**Repo revision used:** Rev 4.0.2 / installer revision 4.0.2-CORRECTED / hardware list updated 2026-04-09
**Document purpose:** Printable procurement and assembly reference for a fresh, from-scratch build
**Document Date:** 2026-04-10

> **DISCLAIMER:** The prices, links, and availability listed in this document are based on live web checks performed on **2026-04-10**. Prices are subject to change. Taxes, tariffs, and shipping are not included.

## Short answer
For the repo's Tier 1 anchor build, do **not** use the Hailo 8 AI HAT+ on the anchor node. Keep the PCIe path dedicated to the **Intel i210-T1** timing NIC and wire PPS from the **u-blox ZED-F9P** to the NIC SDP header. Use the Hailo only on a separate sidecar/dev node if you want it later.

---

## 1. Supported compute options (top-tier filter only)

| Part number | Board / module | RAM / storage | Use level for this repo | Qty | List price | Verified purchase link |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| CM5116000 | Raspberry Pi Compute Module 5 Wireless | 16GB / Lite (0GB eMMC) | Canonical Tier 1 anchor - recommended | 1 | $300.00 | PiShop US |
| CM4108000 | Raspberry Pi Compute Module 4 Wireless | 8GB / Lite (0GB eMMC) | Canonical Tier 1 anchor - supported | 1 | $160.00 | Newark |
| PI5-16GB | Raspberry Pi 5 board | 16GB / microSD boot | Conditional anchor use only if PCIe is reserved for i210-T1; no Hailo on this node | 1 | $305.00 | CanaKit |
| PI4-8GB | Raspberry Pi 4 Model B | 8GB / microSD boot | Software-compatible fallback; not the preferred practical Tier 1 path | 1 | $165.00 | CanaKit |

*Selection rule: for a clean repo-faithful anchor build, prefer **CM5 16GB Lite Wireless** first, then **CM4 8GB Lite Wireless**. The Pi 5 board is still workable, but only if the PCIe lane is reserved for the i210 timing path.*

---

## 2. Canonical Tier 1 bill of materials

This section is organized to match the repo hardware list, then tightened into practical buy-now options.

| Category | Required component | Part / variant | Qty | List price | Verified purchase link | Notes |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| Compute | CM5 module | CM5116000 | 1 | $300.00 | PiShop US | Best primary choice for this sheet. |
| Compute | CM4 module | CM4108000 | 1 | $160.00 | Newark | Use if building on CM4 instead of CM5. |
| Carrier / breakout | CM5 IO board | Raspberry Pi CM5 IO Board Rev 2 | 1 | $26.95 | PiShop US | Recommended for CM5 builds. |
| Carrier / breakout | CM4 carrier | Waveshare Mini Base Board (B) / 19602 | 1 | $27.95 | PiShop US | Compact CM4 carrier with buyable stock page. |
| Precision timing | Timing NIC | Intel i210-T1 | 1 | $59.99 | CDW | Mandatory for repo-faithful Tier 1 timing. |
| GPS / PPS | GNSS module | u-blox ZED-F9P-04B | 1 | $127.41 | Mouser | PPS source. Repo names ZED-F9P family, then you hard-wire PPS to i210 SDP. |
| Storage | OS / endurance media | VIOFO 128GB Industrial Grade microSD | 1 | $55.99 | Amazon | Recommended for Lite modules and board boot media. |

### Repo-shared peripherals and cabling

| Category | Recommended buy | Part / variant | Qty | List price | Verified purchase link | Notes |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| SDR | Fast-ship option | Airspy R2 | 1 | $169.00 | Airspy.US | Chosen because the repo allows Airspy R2 and this listing shows it in stock. |
| SDR | Budget option | RTL-SDR Blog V4 | 1 | $39.95 | Official eBay listing | Repo-allowed, but current shipping commonly runs 3-6 weeks, so it misses your preferred wait window. |
| RF cabling | By-the-foot coax | LMR-240 | As needed | $1.37/ft | DX Ham Radio Supply | Usually ships in 1-3 business days. |
| Network cabling | Shielded patch cable | Monoprice shielded Cat6 / Cat6A | As needed | $15.44 (20 ft example) | Monoprice | Repo calls for shielded Cat6 for the PTP network. |

*Antenna note: the repo specifies a **multi-spectrum dipole / patch array for 400 MHz-2.4 GHz** but does not lock a single SKU, so antenna selection stays modality-dependent.*

---

## 3. Power, cooling, and storage medium choice

| Platform | Recommended power item | Qty | List price | Verified purchase link | Use note |
| :--- | :--- | :--- | :--- | :--- | :--- |
| CM5 / Pi 5 path | Raspberry Pi 27W USB-C Power Supply Black US - SC1158 | 1 | $12.95 | PiShop US | Use for CM5 IO Board Rev 2 or Pi 5 class builds. |
| Pi 4B path | Raspberry Pi 15W USB-C Power Supply | 1 | $8.80 | PiShop US | Pi 4 path uses the official 5.1V / 3A supply class. |

*Storage medium choice for this sheet:* **boot from industrial microSD first**. That keeps the build clean on Lite modules and top-tier Pi boards. Add NVMe later only after the timing path is stable; do not consume the Tier 1 PCIe path with storage or AI hardware during initial bring-up.

---

## 4. Physical assembly and wiring procedure

**Step 1.** Choose one compute path only: **CM5 16GB Lite Wireless + CM5 IO Board Rev 2** (preferred) or **CM4 8GB Lite Wireless + CM4 carrier**.
**Step 2.** Unpack the compute module, carrier board, i210-T1, ZED-F9P, industrial microSD, power supply, SDR, and cabling. Use normal ESD discipline.
**Step 3.** Install the CM5 or CM4 into its carrier/IO board. Verify full seating before adding anything else.
**Step 4.** Install the cooling solution required by that platform. Pi 5-class silicon performs best with active cooling or at minimum a proper passive cooler. Do not enclose the board in a tight case during first bring-up.
**Step 5.** Insert the 128GB industrial microSD card into the active boot slot for the selected platform.
**Step 6.** Install the **Intel i210-T1** into the carrier board's **PCIe x1 path**. On a Pi 5 board path, that means any adapter chain must terminate in the i210-T1 and nothing else. **Do not install the Hailo 8 AI HAT+ on the anchor node.**
**Step 7.** Mount and connect the **u-blox ZED-F9P**. Attach its GNSS antenna with the shortest practical clean RF run.
**Step 8.** Perform the repo's required timing wiring: **physically wire the ZED-F9P PPS output pin directly to the Software Definable Pin (SDP) header on the Intel i210-T1**. Keep the PPS lead short, mechanically secured, and clearly labeled.
**Step 9.** Connect the timing/network side using **shielded Cat6** or better. Connect RF peripherals using **LMR-240 or better**.
**Step 10.** Attach the chosen SDR. For a buy-now path that respects your delivery constraint, the practical immediate choice is **Airspy R2**.
**Step 11.** Apply power only after re-checking: compute seating, PCIe card seating, PPS wire placement, antenna connection, microSD installed, and no Hailo or NVMe occupying the anchor PCIe path.

---

## 5. Operating system and initial software bring-up

Recommended OS for first bring-up: **Raspberry Pi OS 64-bit**. On Raspberry Pi 5-class hardware, use the current Raspberry Pi OS branch supported by Raspberry Pi 5; do not use releases older than Bookworm.

Use Raspberry Pi Imager to flash Raspberry Pi OS 64-bit to the industrial microSD.
Enable SSH during imaging if desired.
Boot the target board from the microSD and complete first-boot user setup.
Update the base OS:
```bash
sudo apt update && sudo apt full-upgrade -y
```

Clone the repo:
```bash
git clone https://github.com/DynoGator/dslv-zpdi.git
cd dslv-zpdi
```

Run the canonical installer for the anchor path:
```bash
sudo ./install_dslv_zpdi.sh --tier1
```

The installer expects Python 3.9+, creates a virtual environment, installs the repo in editable mode, runs tests/orphan checks, and when invoked with `--tier1` installs the timing/audit package set: `chrony linuxptp ethtool pciutils`.

---

## 6. Verification checklist

- **Check 1.** Confirm the hardware model is one of the repo-recognized platforms before deeper testing.
- **Check 2.** Confirm the i210 timing NIC enumerates correctly and that a PTP device node is present.
- **Check 3.** Run the repo installer with `--tier1` and let the hardware audit execute.
- **Check 4.** Verify the repo's stated timing checks: `chronyc tracking` shows disciplined timing and `ts2phc` is disciplining the i210 PHC from the PPS signal.
- **Check 5.** Run the repo test suite and orphan checker after installation.
- **Check 6.** Only after stable timing and successful test pass should you add any optional peripherals, enclosures, or workflow customizations.

---

## 7. Do-not-do list for this anchor build

- Do not put the **Hailo 8 AI HAT+** on the Tier 1 anchor.
- Do not consume the anchor PCIe path with NVMe during first bring-up.
- Do not rely on the native board clock path when the repo is explicitly built around i210 + PPS hardening.
- Do not bury the PPS wire in a messy harness. Route it cleanly and label it.
- Do not switch operating systems mid-build. Bring the node up cleanly on Raspberry Pi OS 64-bit first, then customize later.

---

## 8. Final procurement summary

Minimum clean anchor-node shopping list:

| Line | Buy one of these | Plus these required items |
| :--- | :--- | :--- |
| CM5 path | CM5116000 + CM5 IO Board Rev 2 | Intel i210-T1, u-blox ZED-F9P, 128GB industrial microSD, 27W PSU, SDR, LMR-240, shielded Cat6 |
| CM4 path | CM4108000 + Waveshare Mini Base Board (B) | Intel i210-T1, u-blox ZED-F9P, 128GB industrial microSD, suitable PSU, SDR, LMR-240, shielded Cat6 |
| Pi 5 path | Pi 5 16GB board only if PCIe is reserved for i210 | Intel i210-T1 via proper PCIe path, u-blox ZED-F9P, 128GB industrial microSD, 27W PSU, SDR, LMR-240, shielded Cat6 |

*End of build sheet.*
