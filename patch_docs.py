import re, os
def patch(fp):
    if not os.path.exists(fp): return
    with open(fp, 'r', encoding='utf-8') as f: c = f.read()
    c = re.sub(r'Rev 3\.3 \(.*?\)', 'Rev 3.4 (Pre-Phase 2A Validation — Specs Airtight, Router Fixed, Schema Added)', c)
    s42 = r'Continuous logging of calibration status, GPS lock, PPS jitter, and environmental classification.'
    s43 = "\n\n## 4.3 Hardware Compatibility Matrix & Alternative Timing Architectures\n* **Approved Carrier Boards:** Waveshare CM5 IO Board.\n* **Alternative:** Timebeat Open Timecard Mini.\n* **Fallback:** Native CM5 PHC (WARNING: Retains 34µs offset)."
    if '4.3 Hardware' not in c and re.search(s42, c): c = c.replace(s42, s42 + s43)
    c = re.sub(r'# PHASE 1 LEGACY SPEC RECOVERY.*$', '', c, flags=re.DOTALL)
    with open(fp, 'w', encoding='utf-8') as f: f.write(c.strip() + '\n')
patch('V3_DSLV-ZPDI_LIVING_MASTER.md')
patch('MASTER_SPEC.md')
print("✅ Documents Patched and Orphans Purged.")
