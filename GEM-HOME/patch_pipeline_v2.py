
import os

path = '../src/dslv_zpdi/main_pipeline.py'
with open(path, 'r') as f:
    lines = f.readlines()

new_lines = []
skip = False
for line in lines:
    if 'simulator_mode = _resolve_simulator(args)' in line:
        new_lines.append('    simulator_mode = _resolve_simulator(args)\n')
        new_lines.append('    # Day 4: Layer 1 Initialization with Retry + Fallback\n')
        new_lines.append('    hal = None\n')
        new_lines.append('    max_retries = 3\n')
        new_lines.append('    for attempt in range(max_retries):\n')
        new_lines.append('        try:\n')
        new_lines.append('            hal = get_hal(simulator=simulator_mode)\n')
        new_lines.append('            break\n')
        new_lines.append('        except Exception as e:\n')
        new_lines.append('            logger.warning(f"HAL Init Attempt {attempt+1} failed: {e}")\n')
        new_lines.append('            if attempt < max_retries - 1:\n')
        new_lines.append('                time.sleep(2)\n')
        new_lines.append('            else:\n')
        new_lines.append('                if not simulator_mode:\n')
        new_lines.append('                    logger.error("Hardware HAL failed after 3 attempts. Falling back to --simulator")\n')
        new_lines.append('                    simulator_mode = True\n')
        new_lines.append('                    hal = get_hal(simulator=True)\n')
        new_lines.append('                else:\n')
        new_lines.append('                    logger.error("Simulator HAL failed initialization.")\n')
        new_lines.append('                    raise\n')
        skip = True
        continue
    if skip and 'hal = get_hal(simulator=simulator_mode)' in line:
        skip = False
        continue
    if not skip:
        new_lines.append(line)

with open(path, 'w') as f:
    f.writelines(new_lines)
print('Patched main_pipeline.py v2')
