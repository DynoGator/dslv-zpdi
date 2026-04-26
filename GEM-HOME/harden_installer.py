
import os

path = '../install_dslv_zpdi.sh'
with open(path, 'r') as f:
    content = f.read()

# 1. Add packages to BASE_PACKAGES or new HARDENING_PACKAGES
if 'HARDENING_PACKAGES' not in content:
    content = content.replace('BASE_PACKAGES=(', 'HARDENING_PACKAGES=(\n    apparmor-profiles\n    usbguard\n    auditd\n)\n\nBASE_PACKAGES=(')

# 2. Update apt-get install section
if 'apt-get install -y "${HARDENING_PACKAGES[@]}"' not in content:
    content = content.replace('apt-get install -y "${BASE_PACKAGES[@]}"', 'apt-get install -y "${BASE_PACKAGES[@]}" "${HARDENING_PACKAGES[@]}"')

# 3. Add hardening logic for usbguard/auditd
harden_logic = """
    # 9. USBGuard allow-listing (SPEC-011.1)
    log_info "Configuring USBGuard allow-list"
    # Generate a policy that allows the HackRF and LBE-1421
    # HackRF: 1d50:6089
    # LBE-1421: 1d50:604b (common Leo Bodnar) or check detected
    usbguard generate-policy > /etc/usbguard/rules.conf
    # Ensure HackRF is always allowed
    if ! grep -q "1d50:6089" /etc/usbguard/rules.conf; then
        echo "allow id 1d50:6089 serial \\"*\\" name \\"HackRF One\\" with-interface all" >> /etc/usbguard/rules.conf
    fi
    systemctl enable --now usbguard
    log_ok "USBGuard configured and active"

    # 10. Auditd monitoring (SPEC-011.2)
    log_info "Configuring auditd for project directory"
    cat > /etc/audit/rules.d/dslv-zpdi.rules <<AUDIT
-w ${INSTALL_DIR} -p wa -k dslv_zpdi_changes
AUDIT
    augenrules --load
    systemctl enable --now auditd
    log_ok "Auditd monitoring active on ${INSTALL_DIR}"
"""

if '9. USBGuard' not in content:
    content = content.replace('log_ok "Systemd hardening chain installed and started"', 'log_ok "Systemd hardening chain installed and started"\n' + harden_logic)

with open(path, 'w') as f:
    f.write(content)
print('Updated install_dslv_zpdi.sh with hardening')
