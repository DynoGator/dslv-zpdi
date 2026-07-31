#!/usr/bin/env bash
# Link system python3-libiio and python3-soapysdr into the project venv.
# Must be run after any venv recreation.
set -euo pipefail
REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VENV_SITE=$("$REPO/.venv/bin/python" -c 'import site; print(site.getsitepackages()[0])')
SYS_DIST="/usr/lib/python3/dist-packages"

mkdir -p "$VENV_SITE"
for pattern in '*iio*' '*SoapySDR*'; do
    for src in $SYS_DIST/$pattern; do
        [ -e "$src" ] || continue
        target="$VENV_SITE/$(basename "$src")"
        if [ ! -e "$target" ]; then
            ln -s "$src" "$target"
            echo "Linked $(basename "$src")"
        fi
    done
done

"$REPO/.venv/bin/python" -c "import iio, SoapySDR; print('libiio + SoapySDR linked OK')"
