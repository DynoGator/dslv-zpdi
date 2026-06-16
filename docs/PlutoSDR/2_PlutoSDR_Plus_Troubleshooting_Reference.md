# Pluto+ (Zynq-7020 / 1GB RAM) Troubleshooting & Engineering Reference Guide

This document serves as an exhaustive reference of the failure modes, errors, and physical hardware phenomena encountered while provisioning the HamGeek ADALM-Pluto+ (1GB RAM variant). It accompanies the `1_PlutoSDR_Plus_Preparation_Guide.md` and provides the exact symptoms and engineering rationale behind the required workarounds.

---

## Error 1: Ethernet Link Failure (`NO-CARRIER`)
**Symptom:**
The device boots, and a USB OTG connection allows SSH access. `dmesg` shows the RTL8211E Gigabit Ethernet driver is loaded (`macb e000b000.ethernet eth0: PHY driver [RTL8211E Gigabit Ethernet]`). However, running `ip link show eth0` reports `<NO-CARRIER,BROADCAST,MULTICAST,UP>`. The link state remains down regardless of cable changes, and `udhcpc` hangs indefinitely. Ping attempts from the host PC return `Destination Host Unreachable`.

**Engineering Root Cause:**
The Zynq-7020 uses Multiplexed I/O (MIO) pins to route internal peripheral signals to physical pads on the chip. The LibreSDR firmware (which is required to properly boot the Zynq-7020 and its 1GB RAM configuration) relies on a physical board layout where the Ethernet PHY is connected to a different set of pins, or assumes the FSBL (First Stage Bootloader) has already multiplexed them. In the HamGeek Pluto+, the RTL8211E data lines physically reside on MIO pins 16 through 27. Because the LibreSDR `devicetree.dtb` does not explicitly map `pinctrl` for the `gem0` Ethernet block, the Zynq's internal routing leaves the MIO pins disconnected. The Linux MAC driver (`macb`) spins up perfectly, but physical data simply falls off the internal silicon edge before reaching the RTL8211E.

**Resolution:**
A custom `devicetree.dtb` must be compiled. The exact `gem0-default` pinmuxing configuration from the official Pluto+ device tree must be surgically injected into the LibreSDR device tree. Once the `pinctrl-0` pointer binds to `ethernet@e000b000`, the Linux kernel automatically aligns the internal silicon routing to the physical pads, instantly restoring the Gigabit link.

---

## Error 2: "Bricking" Risk and Bootloader Crashes
**Symptom:**
Flashing the official `tezuka-plutoplus` firmware directory to the SD card results in a device that fails to boot entirely. No lights (or solid error lights), no USB enumeration, and total loss of communication.

**Engineering Root Cause:**
"Pluto+" is heavily fragmented. The original open-source ADALM-Pluto and the standard Pluto+ iterations use the Zynq-7010 SoC. The specific board provisioned here (the HamGeek 1GB variant) utilizes the much larger Zynq-7020 SoC. The `BOOT.bin` provided in the `tezuka-plutoplus` package is strictly compiled for the Zynq-7010. Forcing a Zynq-7010 bootloader onto a Zynq-7020 fabric causes a hard initialization failure in the BootROM.

**Resolution:**
Never use the `tezuka-plutoplus` payload on the HamGeek 1GB board. The SD card must utilize the `tezuka-libre` firmware payload, which is compiled for the Zynq-7020. The BootROM will happily load this, bypassing the corrupted internal QSPI flash. (Refer to Error 1 for fixing the LibreSDR ethernet shortcomings).

---

## Error 3: RAM Instability / Kernel Panics on Boot
**Symptom:**
When operating on standard manufacturer firmware, the device randomly crashes, reboots, or fails to lock onto signals. 

**Engineering Root Cause:**
The original manufacturer firmware defines the Memory Controller timings and limits based strictly on the official 512MB DDR chip specification. The HamGeek aftermarket board solders a 1GB DDR RAM array onto the PCB without providing an updated FSBL (`BOOT.bin`) to handle the modified RAM array's timings and addressing scheme. The Linux kernel attempts to address memory locations that the memory controller is mismanaging, resulting in kernel panics.

**Resolution:**
Flashing the `tezuka-libre` bootloader updates the Zynq Memory Controller timing arrays. The kernel will cleanly recognize all `1048576K` of available RAM (`free -m`) and stabilize completely.

---

## Error 4: Rapid Blue and Yellow Flashing LEDs on Boot
**Symptom:**
Upon applying power, the device enters an extended sequence (15–25 seconds) of rapidly alternating Blue and Yellow LEDs. 

**Engineering Root Cause:**
This is *not* a kernel panic. The LibreSDR firmware utilizes a different FPGA loading and network initialization sequence compared to the stock Pluto firmware. This rapid blink indicates that `system_top.bin` is currently programming the FPGA fabric and `S99network` is attempting to negotiate the RGMII interface state. 

**Resolution:**
No action required. Wait for the sequence to complete. A solid Green LED signifies successful initialization. Interrupting power during this sequence can corrupt the boot environment.

---

## Error 5: Python Validation Script Reports `[Errno 22] Invalid argument` for Sample Rates
**Symptom:**
When querying the AD9361 limits via the `libiio` python bindings, directly assigning `channel.attrs["sampling_frequency"].value = "61440000"` fails and throws a `-EINVAL` (Error 22).

**Engineering Root Cause:**
The IIO subsystem on the Pluto+ manages an intricate clock tree. Setting the raw sampling frequency directly to arbitrary bounds without simultaneously configuring the half-band FIR filters and the BBPLL (Baseband Phase-Locked Loop) dividers will be rejected by the driver if the requested rate cannot be derived perfectly from the current clock hierarchy. 

**Resolution:**
To validate hardware capability dynamically without hard-crashing the clock tree, the script must parse the `sampling_frequency_available` attribute natively exposed by the driver, which returns a structured array (e.g., `[2083333 1 61440000]`). Parsing the boundaries of this string cleanly validates the dynamic capability of the chip without risking state desynchronization.
