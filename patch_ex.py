with open("tools/dashboard/demod_app.py") as f:
    lines = f.readlines()
with open("tools/dashboard/demod_app.py", "w") as f:
    for line in lines:
        if "except Exception:" in line:
            f.write(line.replace("except Exception:", "except Exception as e:"))
            f.write('                        open("/tmp/err.log", "a").write(str(e) + "\\n")\n')
        else:
            f.write(line)
