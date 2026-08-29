package labs.dynogator.dslvzpdi;

import android.content.Context;

import java.io.ByteArrayOutputStream;
import java.io.InputStream;
import java.nio.charset.StandardCharsets;

/** Shell installers and agent docs served at /cli/*. Pure Java, no JNI. */
final class CliAssets {
    private CliAssets() {}

    static String read(Context ctx, String name, String fallback) {
        if (ctx == null) return fallback;
        try (InputStream in = ctx.getAssets().open(name)) {
            ByteArrayOutputStream out = new ByteArrayOutputStream();
            byte[] buf = new byte[8192];
            int n;
            while ((n = in.read(buf)) >= 0) out.write(buf, 0, n);
            String s = new String(out.toByteArray(), StandardCharsets.UTF_8);
            return s.isEmpty() ? fallback : s;
        } catch (Exception e) {
            return fallback;
        }
    }

    static String dslvSh(Context ctx) {
        return read(ctx, "cli/dslv.sh", DSLV_SH);
    }

    static String installSh(Context ctx) {
        return read(ctx, "cli/termux-install.sh", INSTALL_SH);
    }

    static String agentsMd(Context ctx) {
        return AGENTS_MD;
    }

    static final String DSLV_SH = """
#!/bin/sh
# dslv — DynoGator Labs DSLV-ZPDI CLI (Termux, proot Debian, host)
# The Pixel APK must be running. Loopback HTTP, no root.
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
  echo "Open the app on this Pixel (Handset mode), then retry. GrapheneOS → Network → Allow." >&2
  exit 2
fi
if [ "$JSON" = "1" ]; then
  printf '%s\\n' "$OUT"
  echo "$OUT" | grep -q '"ok":false' && exit 1 || exit 0
fi
if command -v python3 >/dev/null 2>&1; then
  printf '%s' "$OUT" | python3 -c '
import json,sys
raw=sys.stdin.read()
try:
    o=json.loads(raw)
except Exception:
    sys.stdout.write(raw if raw.endswith("\\n") else raw+"\\n")
    sys.exit(0)
if isinstance(o, dict) and o.get("text"):
    t=o["text"]
    sys.stdout.write(t if t.endswith("\\n") else t+"\\n")
    sys.exit(0 if o.get("ok", True) else 1)
print(json.dumps(o, indent=2))
sys.exit(0 if (not isinstance(o, dict) or o.get("ok", True)) else 1)
'
else
  printf '%s\\n' "$OUT"
fi
""";

    static final String INSTALL_SH = """
#!/bin/sh
echo "DSLV-ZPDI installer asset missing. Open CLI → Bridge → Copy installer."
exit 1
""";

    static final String AGENTS_MD = """
# DSLV-ZPDI CLI

You are on a Pixel running DynoGator Labs DSLV-ZPDI. The `dslv` command is the supported interface for CLI agents (Claude Code, Gemini CLI, Grok, Kimi, Codex, Aider, OpenCode).

## Rules
- Prefer `dslv <cmd> --json` for machine output.
- The Android app must be in the foreground or cached; if a call fails, tell the operator to open DSLV-ZPDI.
- USB IQ from HackRF is `clock_source=internal` → SECONDARY. Never claim it is Tier-1 PRIMARY.
- Do not issue `baseline.reset` hard against Alpha GPSDO / LBE-1421 timing authority.
- Transmit is RX-only in this build.

## Install
Termux — paste `dslv-termux-install.sh` and press Enter, or:
```
curl -fsS http://127.0.0.1:8444/cli/install.sh | sh
```
proot Debian:
```
curl -fsS http://127.0.0.1:8444/cli/install.sh | DEST=/usr/local/bin sh
```

## Commands
```
dslv help
dslv status --json
dslv sensors --json
dslv sdr scan | open [hackrf] | close | auto | rx on|off
dslv sdr tune <mhz>
dslv sdr demod WFM|NFM|AM|USB|LSB|CW|RAW
dslv sdr gain lna|vga <db>
dslv sdr listen on|off
dslv sdr preset fm_broadcast|nws|airband|marine|2m_call|70cm|gmrs|am_broadcast|cb|20m_usb|40m_lsb|40m_cw|adsb
dslv sdr spectrum --json
dslv listen on|off
dslv capture [note]
dslv pipeline start|stop|seal|rotate|stats
dslv script list|show <name>|run <name>
dslv tools          # JSON function definitions
dslv doctor
```

Aliases: `dslv-status`, `dslv-listen`, `dslv-mute`, `dslv-tune`, `dslv-capture`, `dslv-sensors`, `dslv-spectrum`.

Env: `DSLV_HOST` (default 127.0.0.1), `DSLV_PORT` (default 8444).
""";
}
