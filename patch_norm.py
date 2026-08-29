with open("tools/dashboard/demod_app.py") as f:
    text = f.read()

text = text.replace(
    'iq = cap.samples\n                    except Exception as e:',
    'iq = cap.samples / 2048.0\n                    except Exception as e:'
)

with open("tools/dashboard/demod_app.py", "w") as f:
    f.write(text)
