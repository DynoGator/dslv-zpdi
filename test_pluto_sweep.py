import sys
import time

sys.path.append("/home/alphapi/dslv-zpdi")
sys.path.append("/home/alphapi/dslv-zpdi/src")
from tools.dashboard.panels.waterfall import PlutoSDRplusSweepStream

stream = PlutoSDRplusSweepStream()
success = stream.start(center_hz=100000000, span_hz=2000000, width=80)
print(f"Start success: {success}")
if not success:
    print(f"Error: {stream.last_error()}")
time.sleep(2)
row = stream.pop_row()
print(f"Got row: {row is not None}")
if row:
    print(f"Row len: {len(row)}, first few: {row[:5]}")
stream.stop()
