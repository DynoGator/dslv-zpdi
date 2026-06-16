# Pluto+ (Zynq-7020 / 1GB RAM) Preparation & Firmware Optimization Guide
**Target Hardware:** HamGeek ADALM-Pluto+ (Rev 5), featuring Zynq-7020 SoC, 1GB DDR RAM, RTL8211E Gigabit Ethernet, and an AD9363 unlocked to AD9361 (70MHz–6GHz, 2T2R).
**Target Software Base:** Tezuka LibreSDR firmware (`tezuka-libre-v0.3.12-730087d`)
**Objective:** Stabilize the 1GB RAM array, achieve zero-jitter Gigabit Ethernet synchronization (for external GPSDO usage), and fully unlock the SDR RF capabilities, bypassing all OEM firmware shortcomings.

---

## 1. Executive Summary & The Hardware Paradox
The "HamGeek Pluto+" presents a unique architectural paradox that crashes standard firmware:
1. **The Processor:** It utilizes a Zynq-7020 (a larger FPGA fabric than the standard Zynq-7010 used in the official ADI Pluto and standard Pluto+).
2. **The Memory:** It features a full 1GB DDR array, whereas standard firmware configures memory timings strictly for 512MB arrays.
3. **The Networking:** It uses the Pluto+ Gigabit Ethernet physical layout (MIO pins 16-27), whereas other Zynq-7020 SDR boards (like LibreSDR) use different configurations.

If you flash `Pluto+` firmware, the bootloader crashes due to the Zynq-7020 architecture mismatch. If you flash `LibreSDR` firmware, the device boots successfully (saving the 1GB RAM array), but the Ethernet physical layer `RTL8211E` is left dead (`NO-CARRIER`) because the Zynq's MIO pins are never multiplexed. 

**The Solution:** A surgical hybrid device tree (`devicetree.dtb`) splice. We utilize the LibreSDR bootloader and kernel to support the Zynq-7020 and 1GB RAM, but inject the Pluto+ Ethernet pinctrl hardware routing into the LibreSDR device tree.

---

## 2. Step-by-Step Implementation Guide

### Step 2.1: SD Card Formatting & Payload Base
1. Eject the MicroSD card from the Pluto+ and connect it to a host Linux PC.
2. Format the MicroSD card with a single `FAT32` partition (labeled `TEZUKA`).
3. Download the `tezuka-libre-v0.3.12-730087d.zip` release from the `plutosdr-fw` repository.
4. Extract the contents of the `sdimg/` folder to the root of the `FAT32` MicroSD card.
   *This gives us the stable `BOOT.bin` (First Stage Bootloader) that correctly initiates the 1GB DDR timings for the Zynq-7020.*

### Step 2.2: Device Tree Splice (The Ethernet Fix)
To activate the Ethernet lines, we must patch the `devicetree.dtb` file on the SD card.

1. **Decompile the Base Device Tree:**
   ```bash
   dtc -I dtb -O dts /media/dynogator/TEZUKA/devicetree.dtb -o /tmp/libre.dts
   ```
2. **Inject the Ethernet Pinctrl Node:**
   Open `/tmp/libre.dts`. Locate the `pinctrl@700` node. Insert the `gem0-default` routing matrix inside it:
   ```dts
   gem0-default {
       phandle = <0x50>;
       mux {
           function = "ethernet0";
           groups = "ethernet0_0_grp";
       };
       conf {
           groups = "ethernet0_0_grp";
           slew-rate = <0x00>;
           io-standard = <0x01>;
       };
       conf-rx {
           pins = "MIO22", "MIO23", "MIO24", "MIO25", "MIO26", "MIO27";
           bias-high-impedance;
           low-power-disable;
       };
       conf-tx {
           pins = "MIO16", "MIO17", "MIO18", "MIO19", "MIO20", "MIO21";
           low-power-disable;
       };
   };
   ```
3. **Map the Pinctrl to the Ethernet MAC:**
   Locate the `ethernet@e000b000` node. Link the newly created pin configuration to the MAC driver by adding:
   ```dts
   pinctrl-names = "default";
   pinctrl-0 = <0x50>;
   ```
4. **Recompile and Deploy:**
   ```bash
   dtc -I dts -O dtb /tmp/libre.dts -o /media/dynogator/TEZUKA/devicetree.dtb
   sync
   ```

### Step 2.3: Boot Sequence & Network Negotiation
1. Unmount the SD card from the PC and insert it back into the Pluto+.
2. Connect the Gigabit Ethernet cable between the Pluto+ and the host PC. 
3. Apply power to the Pluto+.
4. **Observe the LED Sequence:** 
   You will see a rapid blink sequence of Yellow and Blue LEDs. This is the LibreSDR FPGA initialization (`system_top.bin`) configuring the network stack. This sequence takes approximately 15-25 seconds. Do not interrupt it. Once the sequence completes, a solid Green LED will indicate a stable power and boot state.
5. **Host PC Network Configuration:** 
   Configure the host PC Ethernet interface (`enp3s0`) to provide DHCP (`Shared to other computers` via NetworkManager or manually via `dnsmasq`). 
6. The Pluto+ will automatically acquire a DHCP lease (e.g., `192.168.3.80`) over the Gigabit wire. 

### Step 2.4: Hardware Validation
With the hybrid firmware active, the device is now fully unlocked. To validate:
* **Memory Check:** SSH into the device and run `free -m`. You will observe `~1048576K` available memory.
* **IIO Context Check:** Execute `iio_info -n <Pluto_IP>` from the host PC. It should successfully build the context over the network backend.
* **Hardware Profile Validation:** Run a Python script utilizing `libiio` to test physical limits. The hardware will safely accept 61.44 MSPS sampling rates, tune seamlessly between 70MHz and 6GHz, and expose 72dB of dynamic programmable hardware gain across the full 2T2R MIMO architecture.
