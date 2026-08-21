import os
import re

def process_file(filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    orig = content
    # Replace HDMI references
    content = re.sub(r'(?i)5"\s*HDMI\b', '10" Lenovo HDMI touchscreen', content)
    content = re.sub(r'(?i)7"\s*HDMI\b', '10" Lenovo HDMI touchscreen', content)
    content = re.sub(r'(?i)\bDSI\b', 'HDMI', content)
    
    # Replace LBE-1421
    content = re.sub(r'\bLBE-1420\b', 'LBE-1421', content)
    
    # Replace GPIO configs
    content = re.sub(r'gpiopin=8', 'gpiopin=8', content)
    content = re.sub(r'gpiopin=8', 'gpiopin=8', content)
    content = re.sub(r'GPIO 8', 'GPIO 8', content)
    content = re.sub(r'GPIO 8', 'GPIO 8', content)
    content = re.sub(r'physical pin 24', 'physical pin 24', content)
    
    if orig != content:
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"Updated {filepath}")

for root, _, files in os.walk('.'):
    if '.git' in root or '.venv' in root or '__pycache__' in root or 'build' in root or 'egg-info' in root:
        continue
    for f in files:
        if f.endswith(('.py', '.md', '.sh', '.toml', '.txt', '.yaml', '.yml', '.example')):
            process_file(os.path.join(root, f))
