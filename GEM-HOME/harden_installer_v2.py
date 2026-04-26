
import os

path = '../install_dslv_zpdi.sh'
with open(path, 'r') as f:
    content = f.read()

airgap_logic = """
    # 11. Air-Gap Hardening (Day 3)
    log_info "Disabling WiFi/Bluetooth for Air-Gap (SPEC-011.3)"
    if [[ -f \"$FIRMWARE_CONFIG\" ]]; then
        if ! grep -q \"dtoverlay=disable-wifi\" \"$FIRMWARE_CONFIG\"; then
            cat >> \"$FIRMWARE_CONFIG\" << 'EOF'

# DSLV-ZPDI Air-Gap Configuration
dtoverlay=disable-wifi
dtoverlay=disable-bt
EOF
            log_ok \"WiFi/BT disabled in $FIRMWARE_CONFIG\"
        fi
    fi

    # 12. USB Power & Security
    log_info \"Setting usbcore.authorized_default=0 (speculative)\"
    # This prevents new USB devices from being authorized by default
    if ! grep -q \"usbcore.authorized_default=0\" /etc/default/grub 2>/dev/null; then
        # For Pi, we usually add to /boot/cmdline.txt
        CMDLINE=\"/boot/firmware/cmdline.txt\"
        if [[ ! -f \"$CMDLINE\" ]]; then CMDLINE=\"/boot/cmdline.txt\"; fi
        if [[ -f \"$CMDLINE\" ]] && ! grep -q \"usbcore.authorized_default=0\" \"$CMDLINE\"; then
            sed -i 's/$/ usbcore.authorized_default=0/' \"$CMDLINE\"
            log_ok \"USB authorized_default=0 added to $CMDLINE\"
        fi
    fi
"""

if '11. Air-Gap' not in content:
    content = content.replace('log_ok \"Auditd monitoring active on ${INSTALL_DIR}\"', 'log_ok \"Auditd monitoring active on ${INSTALL_DIR}\"\n' + airgap_logic)

with open(path, 'w') as f:
    f.write(content)
print('Updated install_dslv_zpdi.sh with Air-Gap hardening')
