import os
import sys

sys.path.append('/home/alphapi/dslv-zpdi')
sys.path.append('/home/alphapi/dslv-zpdi/src')
from dslv_zpdi.layer1_ingestion.sdr.capabilities import CaptureProfile
from dslv_zpdi.layer1_ingestion.sdr.pluto_iio import PlutoIioBackend

try:
    sdr = PlutoIioBackend(uri=os.environ.get('ZPDI_SDR_URI', 'ip:192.168.2.1'))
    cprof = CaptureProfile(center_frequency_hz=100000000, sample_rate_sps=2083334, bandwidth_hz=2000000, gain_db=40, num_samples=2048)
    cap = sdr.capture(cprof)
    print("Capture succeeded, IQ samples:", len(cap.samples))
except Exception:
    import traceback
    traceback.print_exc()
