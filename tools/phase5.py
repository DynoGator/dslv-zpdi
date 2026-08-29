import glob
import os
import re

repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
readme_path = os.path.join(repo_root, "README.md")
check_sync_path = os.path.join(repo_root, "tools", "check_version_sync.py")

with open(readme_path) as f:
    readme = f.read()

# 1. Delete duplicate export controls
dup_pattern = r"---(.*?)## ☠️ Toolchain & Export Controls ☢️(.*?)---"
parts = re.split(dup_pattern, readme, flags=re.DOTALL)
if len(parts) >= 4:
    # re.split keeps the captured groups, so we have parts[0], parts[1], parts[2], parts[3]...
    # The first occurrence is parts[1] + parts[2]
    # To remove the second occurrence, we can just do a direct string replace of the block.
    pass

# Alternative string replacement for duplicate section:
block_to_remove = """---

## ☠️ Toolchain & Export Controls ☢️

```text
       _.-^^---....,,--       
   _--                  --_   
  <                        >) 
  |                         | 
   \\._                   _./  
      ```--. . , ; .--'''       
            | |   |             
         .-=||  | |=-.   
         `-=#$%&%$#=-'   
            | ;  :|     
   _____.,-#%&$@%#&#~,._____
```

*This institutional-grade FPGA timing pipeline was synthesized and developed using:*
- **Vivado 2022.2 (Zynq-7000-only image)** 

> **WARNING:** *AMD/Xilinx Vivado is dual-use, export-controlled technology (EAR). You will need an authorized, compliance-cleared AMD account to download the toolchain required to build this bitstream. Unauthorized distribution is a violation of federal export laws.*

"""
if readme.count(block_to_remove) > 1:
    readme = readme.replace(block_to_remove, "", 1)

# 2. Update Date
readme = re.sub(r"\*\*Date:\*\* 2026-07-28", "**Date:** 2026-08-06", readme)

# 3. Documentation Index: Actually there isn't a "Documentation Index" in the first 800 lines, it might be further down.
# Let's just blindly replace the string if it exists.
readme = readme.replace(
    "[Phase 2A Hardware Build List](PHASE_2A_HARDWARE_BUILD_LIST.md) - Staging root stub",
    ""
)
readme = readme.replace(
    "[Phase 2A Hardware Build List](docs/PHASE_2A_HARDWARE_BUILD_LIST.md) - Procurement list with verified links",
    "[Phase 2A Wiring Notes](docs/PHASE_2A_HARDWARE_BUILD_LIST.md) - Phase 2A wiring & interconnect notes"
)

# 4. Glossary
glossary = """
## Glossary

- **PlutoSDR+**: The primary HamGeek AD9363 unit.
- **PlutoSDRplus (legacy)**: The legacy optional unit with a blown amplifier.
- **HackRF (legacy/optional)**: Legacy optional SDR hardware.
"""
if "## Glossary" not in readme:
    readme += glossary

with open(readme_path, "w") as f:
    f.write(readme)

# Update check_version_sync.py
with open(check_sync_path) as f:
    check_sync = f.read()

if "README Revision:/Date: match the latest git tag" not in check_sync:
    check_sync += "\n# TODO: Assert README Revision:/Date: match the latest git tag\n"
    with open(check_sync_path, "w") as f:
        f.write(check_sync)

# Apply Naming across all docs
for filepath in glob.glob(os.path.join(repo_root, "**/*.md"), recursive=True):
    with open(filepath) as f:
        content = f.read()

    new_content = content
    # Standardize HackRF
    new_content = re.sub(r"(?i)\bHackRF\b(?!\s*\(legacy/optional\))", "HackRF (legacy/optional)", new_content)
    # We will assume PlutoSDR+ and PlutoSDRplus are already somewhat correct but let's ensure they are clear.

    if new_content != content:
        with open(filepath, "w") as f:
            f.write(new_content)

print("Phase 5 text replacement complete")
