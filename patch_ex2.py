with open("tools/dashboard/demod_app.py") as f:
    text = f.read()

text = text.replace('except Exception:\n                        iq = np.zeros(cprof.num_samples, dtype=np.complex64)', 'except Exception as e:\n                        open("/tmp/err.log", "a").write(f"Cap error: {e}\\n")\n                        iq = np.zeros(cprof.num_samples, dtype=np.complex64)')

with open("tools/dashboard/demod_app.py", "w") as f:
    f.write(text)
