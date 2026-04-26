
import os
import re

path = '../src/dslv_zpdi/layer1_ingestion/hal_simulated.py'
with open(path, 'r') as f:
    lines = f.readlines()

# We want to keep the FIRST ingest_sdr (the new one) and remove the SECOND one.
new_lines = []
found_count = 0
skip_until_next_def = False

for line in lines:
    if 'def ingest_sdr(self, **kwargs)' in line:
        found_count += 1
        if found_count > 1:
            skip_until_next_def = True
            continue
    
    if skip_until_next_def:
        if line.startswith('    def ') and 'ingest_sdr' not in line:
            skip_until_next_def = False
            new_lines.append(line)
        continue
    
    new_lines.append(line)

with open(path, 'w') as f:
    f.writelines(new_lines)
print('Cleaned up hal_simulated.py duplicate methods')
