#!/bin/sh
# =============================================================================
#  DSLV-ZPDI  —  Termux / Debian installer
#  DynoGator Labs · Pixel 9 Pro XL · GrapheneOS
#
#  DROP THIS IN TERMUX AND PRESS ENTER.
#  No root. Writes dslv + aliases even if the app is closed.
#  Debian proot:  DEST=/usr/local/bin sh dslv-termux-install.sh
# =============================================================================
set -e

HOST="${DSLV_HOST:-127.0.0.1}"
PORT="${DSLV_PORT:-8444}"
PKG="labs.dynogator.dslvzpdi"
ALIASES="dslv-status dslv-listen dslv-mute dslv-tune dslv-capture dslv-sensors dslv-spectrum dslv-help"

echo ""
echo "DSLV-ZPDI installer"
echo "-------------------"

need=""
command -v curl >/dev/null 2>&1 || need="$need curl"
command -v python3 >/dev/null 2>&1 || need="$need python"
if [ -n "$need" ] && [ -n "${PREFIX:-}" ] && command -v pkg >/dev/null 2>&1; then
  echo "pkg install$need"
  # shellcheck disable=SC2086
  pkg install -y $need || true
fi

write_dslv() {
  dest="$1"
  mkdir -p "$(dirname "$dest")"
  cat > "$dest" << 'DSLV_WRAPPER_EOF'
#!/bin/sh
# dslv — DynoGator Labs DSLV-ZPDI CLI (Termux, proot Debian)
# The Pixel APK must be running for commands. Loopback HTTP, no root.
set -eu
HOST="${DSLV_HOST:-127.0.0.1}"
PORT="${DSLV_PORT:-8444}"
JSON=0
CMD=""
self=$(basename "$0")
case "$self" in
  dslv-status) set -- status --json "$@" ;;
  dslv-listen) set -- listen on "$@" ;;
  dslv-mute) set -- listen off "$@" ;;
  dslv-tune) set -- sdr tune "$@" ;;
  dslv-capture) set -- capture "$@" ;;
  dslv-sensors) set -- sensors --json "$@" ;;
  dslv-spectrum) set -- sdr spectrum --json "$@" ;;
  dslv-help) set -- help "$@" ;;
esac
for a in "$@"; do
  case "$a" in
    --json|-j) JSON=1 ;;
    --host=*) HOST="${a#--host=}" ;;
    --port=*) PORT="${a#--port=}" ;;
    --help|-h)
      CMD="help"
      break
      ;;
    *)
      if [ -z "$CMD" ]; then CMD="$a"; else CMD="$CMD $a"; fi
      ;;
  esac
done
[ -n "$CMD" ] || CMD="help"
URL="http://${HOST}:${PORT}/cli/exec"
fetch() {
  if command -v curl >/dev/null 2>&1; then
    curl -fsS --max-time 90 -G "$URL" --data-urlencode "cmd=$CMD" --data-urlencode "json=$JSON"
  elif command -v wget >/dev/null 2>&1; then
    wget -qO- --timeout=90 "$URL?cmd=$(printf '%s' "$CMD" | sed 's/ /%20/g')&json=$JSON"
  else
    echo "dslv: need curl or wget" >&2
    return 1
  fi
}
if ! OUT=$(fetch); then
  echo "dslv: cannot reach DSLV-ZPDI at ${HOST}:${PORT}." >&2
  echo "Open the app on this Pixel (Handset mode), then retry." >&2
  echo "GrapheneOS → DSLV-ZPDI → Network → Allow." >&2
  exit 2
fi
if [ "$JSON" = "1" ]; then
  printf '%s\n' "$OUT"
  echo "$OUT" | grep -q '"ok":false' && exit 1 || exit 0
fi
if command -v python3 >/dev/null 2>&1; then
  printf '%s' "$OUT" | python3 -c '
import json,sys
raw=sys.stdin.read()
try:
    o=json.loads(raw)
except Exception:
    sys.stdout.write(raw if raw.endswith("\n") else raw+"\n")
    sys.exit(0)
if isinstance(o, dict) and o.get("text"):
    t=o["text"]
    sys.stdout.write(t if t.endswith("\n") else t+"\n")
    sys.exit(0 if o.get("ok", True) else 1)
print(json.dumps(o, indent=2))
sys.exit(0 if (not isinstance(o, dict) or o.get("ok", True)) else 1)
'
else
  printf '%s\n' "$OUT"
fi
DSLV_WRAPPER_EOF
  chmod 755 "$dest"
  echo "  $dest"
}

link_aliases() {
  bin="$1"
  for a in $ALIASES; do
    ln -sf "$bin/dslv" "$bin/$a" 2>/dev/null || cp "$bin/dslv" "$bin/$a"
  done
}

rc_snippet() {
  rc="$1"
  bin="$2"
  [ -f "$rc" ] || touch "$rc"
  grep -q 'DSLV-ZPDI CLI' "$rc" 2>/dev/null && return 0
  printf '\n# DSLV-ZPDI CLI\nexport PATH="%s:$PATH"\n' "$bin" >> "$rc"
}

wake_apk() {
  command -v am >/dev/null 2>&1 || return 0
  am start --user 0 -n "$PKG/.MainActivity" >/dev/null 2>&1 || \
    am start -n "$PKG/$PKG.MainActivity" >/dev/null 2>&1 || \
    am start -a android.intent.action.VIEW -d "dslv://help" >/dev/null 2>&1 || \
    true
}

wait_app() {
  echo "Waiting for DSLV-ZPDI on ${HOST}:${PORT} (open the app if this hangs)…"
  i=0
  while [ "$i" -lt 20 ]; do
    if command -v curl >/dev/null 2>&1 && curl -fsS --max-time 1 "http://${HOST}:${PORT}/health" >/dev/null 2>&1; then
      echo "  app is up"
      return 0
    fi
    i=$((i + 1))
    sleep 1
  done
  echo "  app not reached yet — dslv is installed; open DSLV-ZPDI and retry commands."
  return 0
}

install_debian() {
  command -v proot-distro >/dev/null 2>&1 || return 0
  tmp="${TMPDIR:-${PREFIX:-/tmp}/tmp}"
  mkdir -p "$tmp"
  if [ ! -f "$tmp/dslv" ]; then
    if [ -n "${PREFIX:-}" ] && [ -f "$PREFIX/bin/dslv" ]; then
      cp "$PREFIX/bin/dslv" "$tmp/dslv"
    elif [ -f "$HOME/bin/dslv" ]; then
      cp "$HOME/bin/dslv" "$tmp/dslv"
    else
      return 0
    fi
  fi
  echo "Debian proot…"
  proot-distro login debian --shared-tmp -- bash -c '
    set -e
    mkdir -p /usr/local/bin
    src=""
    for p in /tmp/dslv /usr/tmp/dslv; do
      [ -f "$p" ] && src="$p" && break
    done
    [ -n "$src" ] || exit 1
    cp "$src" /usr/local/bin/dslv
    chmod 755 /usr/local/bin/dslv
    for a in dslv-status dslv-listen dslv-mute dslv-tune dslv-capture dslv-sensors dslv-spectrum dslv-help; do
      ln -sf /usr/local/bin/dslv /usr/local/bin/$a
    done
    echo "  /usr/local/bin/dslv"
  ' || echo "  Debian skipped (pkg install proot-distro && proot-distro install debian)"
}

if [ -n "${DEST:-}" ]; then
  write_dslv "$DEST/dslv"
  link_aliases "$DEST"
  echo "dslv ready in $DEST"
  exit 0
fi

if [ -n "${PREFIX:-}" ] && [ -d "${PREFIX}/bin" ]; then
  HOME_BIN="${HOME}/bin"
  echo "Termux bins:"
  write_dslv "$HOME_BIN/dslv"
  link_aliases "$HOME_BIN"
  write_dslv "$PREFIX/bin/dslv"
  link_aliases "$PREFIX/bin"
  rc_snippet "$HOME/.bashrc" "$HOME_BIN"
  [ -f "$HOME/.zshrc" ] && rc_snippet "$HOME/.zshrc" "$HOME_BIN"
  export PATH="$HOME_BIN:$PREFIX/bin:$PATH"
  wake_apk
  wait_app
  install_debian
  echo ""
  echo "Done. Open a new session or:  source ~/.bashrc"
  echo "Then:  dslv help"
  echo ""
  echo "Termux → Settings → Allow external apps"
  echo "GrapheneOS → DSLV-ZPDI → Network → Allow"
  echo ""
  if command -v dslv >/dev/null 2>&1; then
    dslv doctor || true
  else
    "$PREFIX/bin/dslv" doctor || true
  fi
  exit 0
fi

if [ -d /usr/local/bin ] && [ -w /usr/local/bin ]; then
  write_dslv /usr/local/bin/dslv
  link_aliases /usr/local/bin
  echo "dslv ready in /usr/local/bin"
  exit 0
fi

HOME_BIN="${HOME}/bin"
write_dslv "$HOME_BIN/dslv"
link_aliases "$HOME_BIN"
rc_snippet "$HOME/.bashrc" "$HOME_BIN"
echo "installed $HOME_BIN/dslv — add it to PATH if needed"
echo "Then:  dslv help"
