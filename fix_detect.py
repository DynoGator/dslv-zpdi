with open("tools/dashboard/demod_app.py") as f:
    lines = f.readlines()
with open("tools/dashboard/demod_app.py", "w") as f:
    in_detect = False
    for line in lines:
        if "def _detect_player" in line:
            f.write(line)
            f.write('        if shutil.which("pw-play"):\n')
            f.write('            self.player_cmd = ["pw-play", "--raw", "--rate", str(self.sample_rate), "--channels", "1", "--format", "s16", "-"]\n')
            f.write('            self.player_name = "pw-play (PipeWire)"\n')
            f.write('        elif shutil.which("paplay"):\n')
            f.write('            self.player_cmd = ["paplay", "--raw", f"--rate={self.sample_rate}", "--channels=1", "--format=s16le"]\n')
            f.write('            self.player_name = "paplay (PulseAudio)"\n')
            f.write('        elif shutil.which("aplay"):\n')
            f.write('            self.player_cmd = ["aplay", "-t", "raw", "-r", str(self.sample_rate), "-c", "1", "-f", "S16_LE", "-q", "-"]\n')
            f.write('            self.player_name = "aplay (ALSA)"\n')
            f.write('        elif shutil.which("ffplay"):\n')
            f.write('            self.player_cmd = ["ffplay", "-nodisp", "-autoexit", "-f", "s16le", "-ar", str(self.sample_rate), "-ac", "1", "-i", "-"]\n')
            f.write('            self.player_name = "ffplay (FFmpeg)"\n')
            f.write('        else:\n')
            f.write('            self.player_cmd = None\n')
            f.write('            self.player_name = None\n')
            in_detect = True
        elif in_detect and "def start(" in line:
            in_detect = False
            f.write(line)
        elif not in_detect:
            f.write(line)
