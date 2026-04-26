
import os
path = '../MASTER_SPEC.md'
with open(path, 'r') as f:
    content = f.read()

content = content.replace('  - : 1 Hz', '  - `Out1`: 1 Hz', 1)
content = content.replace('  - : 1 Hz', '  - `Out2`: 1 Hz', 1)

with open(path, 'w') as f:
    f.write(content)
print('Fixed MASTER_SPEC.md labels')
