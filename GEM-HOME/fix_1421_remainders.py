
import os

files_to_fix = [
    '../src/dslv_zpdi/layer1_ingestion/hal_hardware.py',
    '../src/dslv_zpdi/layer1_ingestion/hal_simulated.py',
    '../MASTER_SPEC.md',
    '../V3_DSLV-ZPDI_LIVING_MASTER.md',
    '../.github/ISSUE_TEMPLATE/bug_report.md'
]

for path in files_to_fix:
    if not os.path.exists(path):
        continue
    with open(path, 'r') as f:
        content = f.read()
    
    # Replace lbe1420 with lbe1421 (case insensitive, but preserving case if possible)
    # We want to be careful with 1420 MHz.
    content = content.replace('lbe1420', 'lbe1421')
    content = content.replace('LBE1420', 'LBE1421')
    # If it was LBE-1420 it might have been missed if I didn't use the hyphen in previous run
    content = content.replace('LBE-1420', 'LBE-1421')
    
    with open(path, 'w') as f:
        f.write(content)
    print(f'Fixed {path}')
