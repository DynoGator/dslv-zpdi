
import os

path = '../src/dslv_zpdi/main_pipeline.py'
with open(path, 'r') as f:
    content = f.read()

retry_logic = \"\"\"
    simulator_mode = _resolve_simulator(args)
    
    # Day 4: Layer 1 Initialization with Retry + Fallback
    hal = None
    max_retries = 3
    for attempt in range(max_retries):
        try:
            hal = get_hal(simulator=simulator_mode)
            break
        except Exception as e:
            logger.warning(f\"HAL Init Attempt {attempt+1} failed: {e}\")
            if attempt < max_retries - 1:
                time.sleep(2)
            else:
                if not simulator_mode:
                    logger.error(\"Hardware HAL failed after 3 attempts. Falling back to --simulator\")
                    simulator_mode = True
                    hal = get_hal(simulator=True)
                else:
                    logger.error(\"Simulator HAL failed initialization.\")
                    raise
\"\"\"

# Replace the simple hal init
content = content.replace('    simulator_mode = _resolve_simulator(args)', '')
content = content.replace('    hal = get_hal(simulator=simulator_mode)', retry_logic)

with open(path, 'w') as f:
    f.write(content)
print('Patched main_pipeline.py with retry + fallback logic')
