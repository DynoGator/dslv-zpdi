import { RELEASE } from "./release-meta";
import { PRESETS, type DemodMode, type SdrConfig, type Telemetry, type UsbState, type PipelineNative } from "./types";
import { nativeHost, isNativeApk, nativeJson } from "./native";

export type CliResult = { ok: boolean; text: string; data?: unknown };

export type ScriptStep = {
  id: string;
  op: string;
  cmd?: string;
  arg?: string;
  mhz?: number;
  ms?: number;
  stage?: "lna" | "vga";
  db?: number;
};

export type ScriptDoc = { name: string; steps: ScriptStep[] };

export type CliContext = {
  sdr: () => SdrConfig;
  usb: () => UsbState;
  tel: () => Telemetry;
  pipe: () => PipelineNative;
  applyPreset: (id: string) => void;
  setCenterHz: (hz: number) => void;
  setDemod: (d: DemodMode) => void;
  setGain: (which: "lna" | "vga", db: number) => void;
  setVolume: (v: number) => void;
  setSquelch: (v: number) => void;
  toggleAudio: () => void;
  usbScan: () => void;
  usbOpen: (hint?: string) => void;
  usbClose: () => void;
  usbRx: (on: boolean) => void;
  capture: () => void;
  setPipeline: (on: boolean) => void;
  sealPipeline: () => void;
  rotatePipeline: () => void;
  scripts: () => ScriptDoc[];
  saveScript: (doc: ScriptDoc) => void;
  deleteScript: (name: string) => void;
};

export const CLI_HELP = `dslv — DSLV-ZPDI CLI ${RELEASE.version}
status                 node / sdr / pipeline
sensors                Pixel GNSS mag IMU baro
sdr scan|open|close|auto|rx on|off
sdr tune <mhz>         e.g. 98.1  146.52  7.2
sdr demod WFM|NFM|AM|USB|LSB|CW|RAW
sdr gain lna|vga <db>
sdr listen on|off      speaker demod
sdr preset <id>        fm_broadcast nws airband marine 2m 70cm gmrs am cb 20m_usb 40m_lsb 40m_cw adsb
sdr spectrum
listen on|off
capture [note]
pipeline start|stop|seal|rotate|stats
script list|show|run|save|delete
termux status|install|debian|run <cmd>
tools                  JSON function defs for agents
doctor
Aliases: dslv-status dslv-listen dslv-mute dslv-tune dslv-capture dslv-sensors dslv-spectrum
Prefix ! to send a line to Termux (APK). Add --json for machine output.
USB IQ is SECONDARY. Pi 5 remains Tier-1.`;

export const INSTALL_TERMUX = "curl -fsS http://127.0.0.1:8444/cli/install.sh | sh";
export const INSTALL_DEBIAN = "curl -fsS http://127.0.0.1:8444/cli/install.sh | DEST=/usr/local/bin sh";
export const INSTALL_FILE = `${import.meta.env.BASE_URL}dslv-termux-install.sh`;

const ALIASES: Record<string, string> = {
  "dslv-status": "status",
  "dslv-listen": "listen",
  "dslv-mute": "mute",
  "dslv-tune": "sdr tune",
  "dslv-capture": "capture",
  "dslv-sensors": "sensors",
  "dslv-spectrum": "sdr spectrum",
  "dslv-help": "help",
};

export const DEFAULT_SCRIPTS: ScriptDoc[] = [
  {
    name: "fm-watch",
    steps: [
      { id: "1", op: "preset", arg: "fm_broadcast" },
      { id: "2", op: "listen", arg: "on" },
      { id: "3", op: "wait", ms: 8000 },
      { id: "4", op: "capture", arg: "fm-watch" },
      { id: "5", op: "mute" },
    ],
  },
  {
    name: "wx-net",
    steps: [
      { id: "1", op: "preset", arg: "nws" },
      { id: "2", op: "listen", arg: "on" },
    ],
  },
  {
    name: "otg-arm",
    steps: [
      { id: "1", op: "scan" },
      { id: "2", op: "rx", arg: "on" },
    ],
  },
];

export const PALETTE: { op: string; label: string; arg?: string; ms?: number }[] = [
  { op: "preset", label: "Preset", arg: "fm_broadcast" },
  { op: "tune", label: "Tune", arg: "98.1" },
  { op: "demod", label: "Demod", arg: "WFM" },
  { op: "listen", label: "Listen" },
  { op: "mute", label: "Mute" },
  { op: "rx", label: "RX on", arg: "on" },
  { op: "scan", label: "Scan" },
  { op: "wait", label: "Wait", ms: 2000 },
  { op: "capture", label: "Capture" },
  { op: "pipeline", label: "Pipeline", arg: "start" },
];

export function tokenize(line: string): string[] {
  const out: string[] = [];
  let cur = "";
  let quote = false;
  for (const c of line) {
    if (c === '"') {
      quote = !quote;
      continue;
    }
    if (!quote && /\s/.test(c)) {
      if (cur) out.push(cur);
      cur = "";
      continue;
    }
    cur += c;
  }
  if (cur) out.push(cur);
  return out;
}

export function parseHz(s: string): number {
  let t = s.trim().toLowerCase().replace(/_/g, "");
  let mul = 1;
  if (t.endsWith("ghz")) {
    mul = 1e9;
    t = t.slice(0, -3);
  } else if (t.endsWith("mhz")) {
    mul = 1e6;
    t = t.slice(0, -3);
  } else if (t.endsWith("khz")) {
    mul = 1e3;
    t = t.slice(0, -3);
  } else if (t.endsWith("hz")) {
    t = t.slice(0, -2);
  } else if (t.endsWith("m")) {
    mul = 1e6;
    t = t.slice(0, -1);
  } else if (t.endsWith("k")) {
    mul = 1e3;
    t = t.slice(0, -1);
  }
  const v = Number(t);
  if (!Number.isFinite(v)) throw new Error("bad frequency " + s);
  if (mul === 1 && v < 10_000) mul = 1e6;
  return Math.round(v * mul);
}

export function stepToLine(step: ScriptStep): string {
  if (step.cmd) return step.cmd.replace(/^dslv\s+/, "");
  switch (step.op) {
    case "preset":
      return `sdr preset ${step.arg ?? "fm_broadcast"}`;
    case "tune":
      return `sdr tune ${step.mhz ?? step.arg ?? 98.1}`;
    case "demod":
      return `sdr demod ${step.arg ?? "WFM"}`;
    case "listen":
      return `listen ${step.arg ?? "on"}`;
    case "mute":
      return "listen off";
    case "rx":
      return `sdr rx ${step.arg ?? "on"}`;
    case "scan":
      return "sdr scan";
    case "wait":
      return `wait ${step.ms ?? 1000}`;
    case "capture":
      return `capture ${step.arg ?? "script"}`;
    case "pipeline":
      return `pipeline ${step.arg ?? "stats"}`;
    case "gain":
      return `sdr gain ${step.stage ?? "lna"} ${step.db ?? 24}`;
    default:
      return step.op;
  }
}

export function scriptToShell(doc: ScriptDoc): string {
  const lines = [
    "#!/bin/sh",
    `# ${doc.name} — DSLV-ZPDI`,
    "set -e",
    "dslv doctor >/dev/null",
  ];
  for (const s of doc.steps) {
    if (s.op === "wait") {
      lines.push(`sleep ${((s.ms ?? 1000) / 1000).toFixed(3)}`);
    } else {
      lines.push(`dslv ${stepToLine(s)}`);
    }
  }
  return lines.join("\n") + "\n";
}

function ok(text: string, data?: unknown): CliResult {
  return { ok: true, text, data };
}
function bad(text: string): CliResult {
  return { ok: false, text };
}

function ensureListen(ctx: CliContext, on: boolean) {
  if (ctx.sdr().audio !== on) ctx.toggleAudio();
}

export function runCli(line: string, ctx: CliContext): CliResult {
  const raw = tokenize(line.trim());
  const argv = raw.filter((a) => a !== "--json" && a !== "-j");
  if (argv[0] === "dslv") argv.shift();
  if (argv.length === 0) return ok(CLI_HELP);
  if (argv[0].startsWith("!")) {
    const cmd = (argv[0].slice(1) + " " + argv.slice(1).join(" ")).trim();
    return termuxRun(cmd);
  }
  const c0 = argv[0].toLowerCase();
  if (ALIASES[c0]) {
    return runCli(`${ALIASES[c0]} ${argv.slice(1).join(" ")}`.trim(), ctx);
  }
  try {
    switch (c0) {
      case "help":
      case "-h":
      case "--help":
        return ok(CLI_HELP);
      case "version":
        return ok(`DSLV-ZPDI CLI ${RELEASE.version}`, { version: RELEASE.version, node: "pixel-9-pro-xl" });
      case "status":
        return ok(JSON.stringify({ sdr: ctx.sdr(), usb: ctx.usb(), tel: summarizeTel(ctx.tel()), pipe: ctx.pipe() }, null, 2));
      case "sensors":
        return ok(JSON.stringify(ctx.tel().pixel, null, 2));
      case "doctor":
        return doctor(ctx);
      case "tools":
        return ok(JSON.stringify(TOOLS, null, 2), TOOLS);
      case "commands":
        return ok(CLI_HELP);
      case "listen":
        ensureListen(ctx, argv[1] !== "off" && argv[1] !== "0");
        return ok(argv[1] === "off" ? "muted" : `LISTEN ${ctx.sdr().demod}`);
      case "mute":
        ensureListen(ctx, false);
        return ok("muted");
      case "preset":
        return doPreset(ctx, argv[1] ?? "");
      case "capture":
        ctx.capture();
        return ok("capture sealed");
      case "sdr":
        return sdr(ctx, argv.slice(1));
      case "pipeline":
        return pipeline(ctx, argv[1] ?? "stats");
      case "script":
        return scriptCmd(ctx, argv.slice(1));
      case "termux":
        return termuxCmd(argv.slice(1));
      case "wait": {
        return ok(`wait ${argv[1] ?? 1000} (use script run for delay)`);
      }
      default:
        return bad(`unknown command: ${c0}  (dslv help)`);
    }
  } catch (e) {
    return bad(e instanceof Error ? e.message : String(e));
  }
}

function summarizeTel(t: Telemetry) {
  return {
    peakDbm: t.peakDbm,
    snrDb: t.snrDb,
    gpsLock: t.gpsLock,
    lastEvent: t.lastEvent,
    pixel: t.pixel,
  };
}

function doPreset(ctx: CliContext, id: string): CliResult {
  const p = PRESETS.find((x) => x.id === id || x.id.replace(/_/g, "") === id.replace(/[-_]/g, ""));
  if (!p) return bad("unknown preset. " + PRESETS.map((x) => x.id).join(" "));
  ctx.applyPreset(p.id);
  return ok(`preset ${p.id} ${(p.hz / 1e6).toFixed(3)} MHz ${p.demod}`);
}

function sdr(ctx: CliContext, a: string[]): CliResult {
  if (!a.length) return ok(JSON.stringify(ctx.usb(), null, 2), ctx.usb());
  const op = a[0].toLowerCase();
  switch (op) {
    case "scan":
      ctx.usbScan();
      return ok(ctx.usb().devices.length ? JSON.stringify(ctx.usb().devices, null, 2) : "scan issued");
    case "open":
      ctx.usbOpen(a[1] ?? "hackrf");
      return ok("open " + (a[1] ?? "hackrf"));
    case "close":
      ctx.usbClose();
      return ok("closed");
    case "auto":
      try {
        nativeHost()?.usbAuto?.();
      } catch {
        /* pwa */
      }
      ctx.usbOpen("hackrf");
      return ok("auto");
    case "rx":
      ctx.usbRx(a[1] !== "off" && a[1] !== "0");
      return ok(a[1] === "off" ? "RX idle" : "RX");
    case "tune":
    case "freq":
    case "center": {
      if (!a[1]) return bad("usage: dslv sdr tune <mhz>");
      const hz = parseHz(a[1]);
      ctx.setCenterHz(hz);
      return ok(`tuned ${(hz / 1e6).toFixed(4)} MHz`);
    }
    case "demod": {
      const d = (a[1] ?? "").toUpperCase() as DemodMode;
      if (!["WFM", "NFM", "AM", "USB", "LSB", "CW", "RAW"].includes(d)) return bad("demod WFM|NFM|AM|USB|LSB|CW|RAW");
      ctx.setDemod(d);
      return ok("demod " + d);
    }
    case "gain": {
      if (!a[2]) return bad("usage: dslv sdr gain lna|vga <db>");
      ctx.setGain(a[1] === "vga" ? "vga" : "lna", Number(a[2]));
      return ok(`${a[1]} ${a[2]} dB`);
    }
    case "volume":
      ctx.setVolume(Number(a[1]));
      return ok("volume " + a[1]);
    case "squelch":
      ctx.setSquelch(Number(a[1]));
      return ok("squelch " + a[1]);
    case "listen":
      ensureListen(ctx, a[1] !== "off");
      return ok(a[1] === "off" ? "muted" : "LISTEN");
    case "preset":
      return doPreset(ctx, a[1] ?? "");
    case "spectrum":
    case "status":
      return ok(
        JSON.stringify(
          {
            centerHz: ctx.sdr().centerHz,
            demod: ctx.sdr().demod,
            usb: ctx.usb(),
            peakDbm: ctx.tel().peakDbm,
            snrDb: ctx.tel().snrDb,
          },
          null,
          2,
        ),
      );
    default:
      return bad("sdr ops: scan open close auto rx tune demod gain listen preset spectrum");
  }
}

function pipeline(ctx: CliContext, op: string): CliResult {
  if (op === "start") ctx.setPipeline(true);
  else if (op === "stop") ctx.setPipeline(false);
  else if (op === "seal") ctx.sealPipeline();
  else if (op === "rotate") ctx.rotatePipeline();
  return ok(JSON.stringify(ctx.pipe(), null, 2), ctx.pipe());
}

function scriptCmd(ctx: CliContext, a: string[]): CliResult {
  const scripts = ctx.scripts();
  if (!a.length || a[0] === "list") {
    const names = scripts.map((s) => s.name);
    return ok(names.length ? names.join("\n") : "no scripts", names);
  }
  if (a[0] === "show" && a[1]) {
    const s = scripts.find((x) => x.name === a[1]);
    return s ? ok(JSON.stringify(s, null, 2), s) : bad("no script " + a[1]);
  }
  if (a[0] === "delete" && a[1]) {
    ctx.deleteScript(a[1]);
    return ok("deleted " + a[1]);
  }
  if ((a[0] === "save" || a[0] === "put") && a[1]) {
    return bad("save scripts from the Scripts panel");
  }
  if (a[0] === "run" && a[1]) {
    return { ok: true, text: `RUN ${a[1]}`, data: { run: a[1] } };
  }
  return bad("script ops: list show run delete");
}

function termuxRun(cmd: string): CliResult {
  if (!isNativeApk()) {
    return ok(`[termux] ${cmd}\nAPK-only. Sideload, then CLI → Install aliases.`);
  }
  const r = nativeJson<Record<string, unknown>>(() => nativeHost()?.termux?.(`run:${cmd}`));
  if (!r) return bad("Termux bridge failed");
  return { ok: Boolean(r.ok ?? true), text: String(r.text ?? r.stdout ?? JSON.stringify(r, null, 2)), data: r };
}

function termuxCmd(a: string[]): CliResult {
  const op = a[0] ?? "status";
  if (!isNativeApk()) {
    if (op === "install" || op === "debian") {
      return ok(`On the Pixel APK:\nTermux: ${INSTALL_TERMUX}\nDebian: ${INSTALL_DEBIAN}`);
    }
    return ok("Termux bridge is in the signed APK. Preview shell still runs dslv against the simulator.");
  }
  const arg = op === "run" ? `run:${a.slice(1).join(" ")}` : op;
  const r = nativeJson<Record<string, unknown>>(() => nativeHost()?.termux?.(arg));
  if (!r) return bad("Termux bridge failed");
  return { ok: Boolean(r.ok ?? true), text: String(r.text ?? JSON.stringify(r, null, 2)), data: r };
}

function doctor(ctx: CliContext): CliResult {
  const native = isNativeApk();
  const t = native ? nativeJson<Record<string, unknown>>(() => nativeHost()?.termux?.("status")) : null;
  const lines = [
    `native ${native ? "apk" : "pwa"}`,
    `version ${RELEASE.version}`,
    `demod ${ctx.sdr().demod} @ ${(ctx.sdr().centerHz / 1e6).toFixed(3)} MHz`,
    `usb ${ctx.usb().open ? ctx.usb().kind : "idle"}`,
    `termux ${t?.termux ? "yes" : native ? "not seen" : "apk-only"}`,
    `install ${INSTALL_TERMUX}`,
  ];
  return ok(lines.join("\n"), t);
}

export async function runScript(doc: ScriptDoc, ctx: CliContext, onLine?: (s: string) => void): Promise<CliResult> {
  const log: string[] = [];
  for (const step of doc.steps) {
    if (step.op === "wait") {
      const ms = Math.min(60_000, Math.max(0, step.ms ?? 1000));
      onLine?.(`wait ${ms}ms`);
      log.push(`wait ${ms}ms`);
      await new Promise((r) => setTimeout(r, ms));
      continue;
    }
    const line = stepToLine(step);
    const r = runCli(line, ctx);
    log.push(`$ ${line}`, r.text);
    onLine?.(`$ ${line}`);
    onLine?.(r.text);
    if (!r.ok) return { ok: false, text: log.join("\n") };
  }
  return { ok: true, text: log.join("\n") };
}

function tool(name: string, description: string, parameters: Record<string, unknown>) {
  return { type: "function", function: { name, description, parameters } };
}

export const TOOLS = [
  tool("dslv_status", "DSLV-ZPDI node / SDR / pipeline snapshot", { type: "object", properties: {} }),
  tool("dslv_sensors", "Pixel GNSS magnetometer IMU baro", { type: "object", properties: {} }),
  tool("dslv_sdr_tune", "Tune HackRF center frequency in MHz", {
    type: "object",
    properties: { mhz: { type: "number" } },
    required: ["mhz"],
  }),
  tool("dslv_sdr_listen", "Start or stop speaker demod", {
    type: "object",
    properties: { on: { type: "boolean" } },
    required: ["on"],
  }),
  tool("dslv_sdr_preset", "Apply a named RF preset", {
    type: "object",
    properties: { id: { type: "string" } },
    required: ["id"],
  }),
  tool("dslv_sdr_demod", "Set demodulator", {
    type: "object",
    properties: { demod: { type: "string", enum: ["WFM", "NFM", "AM", "USB", "LSB", "CW", "RAW"] } },
    required: ["demod"],
  }),
  tool("dslv_capture", "Seal a capture into the HDF5 chain", {
    type: "object",
    properties: { note: { type: "string" } },
  }),
  tool("dslv_pipeline", "HDF5 pipeline control", {
    type: "object",
    properties: { op: { type: "string", enum: ["start", "stop", "seal", "rotate", "stats"] } },
    required: ["op"],
  }),
  tool("dslv_script_run", "Run a saved visual/CLI script", {
    type: "object",
    properties: { name: { type: "string" } },
    required: ["name"],
  }),
];

export const SCRIPTS_KEY = "dslv-zpdi-scripts-v1";
export const HIST_KEY = "dslv-zpdi-cli-hist-v1";

export function loadScripts(): ScriptDoc[] {
  try {
    const raw = localStorage.getItem(SCRIPTS_KEY);
    if (!raw) return DEFAULT_SCRIPTS.map((s) => ({ ...s, steps: s.steps.map((x) => ({ ...x })) }));
    const parsed = JSON.parse(raw) as ScriptDoc[];
    return parsed.length ? parsed : DEFAULT_SCRIPTS;
  } catch {
    return DEFAULT_SCRIPTS;
  }
}

export function saveScripts(docs: ScriptDoc[]) {
  try {
    localStorage.setItem(SCRIPTS_KEY, JSON.stringify(docs));
  } catch {
    /* quota */
  }
  if (isNativeApk()) {
    const host = nativeHost();
    for (const d of docs) {
      try {
        host?.cli?.(`script put ${d.name} ${JSON.stringify({ name: d.name, steps: d.steps })}`);
      } catch {
        /* ignore */
      }
    }
  }
}
