with open("tools/dashboard/demod_app.py") as f:
    text = f.read()

text = text.replace(
    'target_rate = self.sample_rate\n                    current_rate = demodulator.current_preset.sample_rate_hz',
    'target_rate = self.sample_rate\n                    current_rate = max(2083334, int(self.app.bandwidth_hz * 2))'
)

with open("tools/dashboard/demod_app.py", "w") as f:
    f.write(text)
