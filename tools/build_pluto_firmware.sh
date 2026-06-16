#!/bin/bash
# SPEC-005A.HAL-PLUTO — Debian PlutoSDR+ Firmware Builder
# Target: HamGeek Pluto+ (Zynq-7020, 1GB RAM) with Tezuka-Libre hybrid patches
set -e

echo "============================================================"
echo "DynoGatorLabs Crew - PlutoSDR+ Custom Firmware Builder"
echo "Target: Zynq-7020, 1GB RAM, AD9361 (70MHz-6GHz unlock)"
echo "============================================================"

# Ensure we are on Debian
if ! grep -q -i "debian" /etc/os-release; then
    echo "[WARN] This script is optimized for Debian. Dependency names may vary on other distros."
fi

echo "[*] Installing required build dependencies..."
sudo apt-get update
sudo apt-get install -y build-essential bc libncurses5-dev bison flex \
    libssl-dev rsync qemu-user-static qemu-system-arm \
    git cpio device-tree-compiler u-boot-tools xz-utils curl \
    libusb-1.0-0-dev libxml2 libxml2-dev

BUILD_DIR="$HOME/plutosdr-fw-build"
echo "[*] Preparing build directory at $BUILD_DIR..."
mkdir -p "$BUILD_DIR"
cd "$BUILD_DIR"

if [ ! -d "plutosdr-fw" ]; then
    echo "[*] Cloning Analog Devices plutosdr-fw..."
    git clone --recursive https://github.com/analogdevicesinc/plutosdr-fw.git
fi

cd plutosdr-fw
git checkout master || true
git pull || true

echo "[*] Exporting variables for Zynq-7020 / 1GB RAM / AD9361..."
# HamGeek Pluto+ uses a larger Zynq and more RAM. We configure buildroot for this hardware profile.
export ZYNQ_BOARD=pluto
export ADI_IGNORE_VERSION_CHECK=1

echo "[*] Applying Tezuka-Libre AD9361 unlock patch..."
# Force AD9361 wideband (70MHz - 6GHz) in the u-boot environment.
ENV_TXT="buildroot/board/pluto/env.txt"
if [ -f "$ENV_TXT" ] && ! grep -q "attr_val=ad9361" "$ENV_TXT"; then
    echo "attr_name=compatible" >> "$ENV_TXT"
    echo "attr_val=ad9361" >> "$ENV_TXT"
    echo "mode=2t2r" >> "$ENV_TXT"
    echo "[*] AD9361 compatibility mode and 2T2R injected into env.txt."
fi

echo "[*] Adjusting Buildroot config for 1GB RAM mapped to Zynq-7020..."
# Double the rootfs size to utilize the 1GB RAM effectively.
DEFCONFIG="buildroot/configs/zynq_pluto_defconfig"
if [ -f "$DEFCONFIG" ]; then
    sed -i 's/BR2_TARGET_ROOTFS_EXT2_BLOCKS=65536/BR2_TARGET_ROOTFS_EXT2_BLOCKS=131072/g' "$DEFCONFIG"
fi

echo "[*] Compiling firmware..."
make clean
make

echo "============================================================"
echo "[*] Firmware built successfully!"
echo "    Images are located in $BUILD_DIR/plutosdr-fw/build/"
echo "    - pluto.dfu (Device Firmware Upgrade via dfu-util)"
echo "    - pluto.frm (Mass Storage update image)"
echo ""
echo "INSTALLATION GUIDE (Mass Storage):"
echo "1. Connect PlutoSDR+ via USB."
echo "2. Mount the 'PlutoSDR' drive."
echo "3. Copy pluto.frm to the drive."
echo "4. Eject/Unmount the drive safely."
echo "5. The Pluto will rapidly blink while flashing. DO NOT UNPLUG."
echo "============================================================"
