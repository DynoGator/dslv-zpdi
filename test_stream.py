import sys
import time

sys.path.append("/home/alphapi/dslv-zpdi")
sys.path.append("/home/alphapi/dslv-zpdi/src")
from tools.dashboard.demod_app import SDRAudioStreamer


class DummyApp:
    paused = False
    squelch = -40.0
    freq_hz = 100000000.0
    bandwidth_hz = 200000.0
    gain_db = 40.0
app = DummyApp()
streamer = SDRAudioStreamer(app)
print(f"Starting streamer with player: {streamer.player_name}")
streamer.start()
time.sleep(3)
streamer.running = False
streamer.thread.join()
print("Done.")
