
import os

path = '../src/dslv_zpdi/layer1_ingestion/hal_simulated.py'
with open(path, 'r') as f:
    lines = f.readlines()

new_lines = []
for line in lines:
    if 'def verify_gpsdo_lock' in line:
        new_lines.append('    def verify_nmea_telemetry(self) -> dict:\n')
        new_lines.append('        """Mock NMEA for SimulatedHAL."""\n')
        new_lines.append('        return {\n')
        new_lines.append("            'nmea_available': True,\n")
        new_lines.append("            'gps_fix': True,\n")
        new_lines.append("            'satellites_used': 12,\n")
        new_lines.append("            'hdop': 0.8\n")
        new_lines.append('        }\n\n')
    new_lines.append(line)

with open(path, 'w') as f:
    f.writelines(new_lines)
print('Added verify_nmea_telemetry to SimulatedHAL')
