import { create } from "zustand";
import { makeEnvelope, toRecord } from "./c2";
import { generateSpectrum, seedTelemetry, spectrumStats, tickTelemetry } from "./sim";
import {
  BINS,
  DEFAULT_PIPE,
  DEFAULT_SDR,
  DEFAULT_USB,
  PRESETS,
  SPAN_FOR_MODE,
  type CaptureEvent,
  type CommandRecord,
  type HalMode,
  type LinkMode,
  type PipelineNative,
  type PixelSensors,
  type SdrConfig,
  type Telemetry,
  type UsbState,
  type ViewId,
  type WaterfallMode,
} from "./types";
import { isNativeApk, nativeHost, nativeJson, nativeRequest } from "./native";
import { rfBus } from "./rf-bus";
import { clamp } from "./utils";

const SETTINGS_KEY = "dslv-zpdi-mobile-v2";

interface Settings {
  mode: LinkMode;
  nodeUrl: string;
  c2Token: string;
  operatorUnlocked: boolean;
}

function loadSettings(): Settings {
  try {
    const raw = localStorage.getItem(SETTINGS_KEY);
    if (!raw) throw new Error("empty");
    return { ...defaultSettings(), ...JSON.parse(raw) };
  } catch {
    return defaultSettings();
  }
}

function defaultSettings(): Settings {
  return {
    mode: isNativeApk() ? "standalone" : "simulated",
    nodeUrl: "http://10.42.0.1:8080",
    c2Token: "",
    operatorUnlocked: false,
  };
}

function saveSettings(s: Settings) {
  try {
    localStorage.setItem(SETTINGS_KEY, JSON.stringify(s));
  } catch {
    /* ignore quota */
  }
}

export interface AppState {
  view: ViewId;
  mode: LinkMode;
  nodeUrl: string;
  c2Token: string;
  liveOk: boolean;
  liveError: string | null;
  operatorUnlocked: boolean;
  hydrated: boolean;
  sdr: SdrConfig;
  tel: Telemetry;
  commands: CommandRecord[];
  captures: CaptureEvent[];
  usb: UsbState;
  pipe: PipelineNative;
  setView: (v: ViewId) => void;
  hydrate: () => void;
  tick: () => void;
  applyPreset: (id: string) => void;
  setCenterHz: (hz: number) => void;
  nudgeCenter: (frac: number) => void;
  setSpanMode: (m: WaterfallMode) => void;
  zoom: (dir: 1 | -1) => void;
  setGain: (which: "lna" | "vga", db: number) => void;
  setDemod: (d: SdrConfig["demod"]) => void;
  setDevice: (d: SdrConfig["device"]) => void;
  setFloorCeil: (floor?: number, ceil?: number) => void;
  cyclePalette: () => void;
  toggleAudio: () => void;
  setVolume: (v: number) => void;
  setSquelch: (v: number) => void;
  stepHz: (hz: number) => void;
  togglePause: () => void;
  setHalMode: (m: HalMode) => void;
  setPipeline: (running: boolean) => void;
  resetBaseline: (hard: boolean) => void;
  setMode: (m: LinkMode) => void;
  setNodeUrl: (u: string) => void;
  setToken: (t: string) => void;
  unlockOperator: (pin: string) => boolean;
  capture: () => void;
  applyPixelFix: (lat: number, lon: number, acc: number, alt?: number) => void;
  applyMag: (x: number, y: number, z: number) => void;
  usbScan: () => void;
  usbOpen: (hint?: string) => void;
  usbClose: () => void;
  usbRx: (on: boolean) => void;
  sealPipeline: () => void;
  rotatePipeline: () => void;
}

function command(capability: string, parameters: Record<string, unknown>, result: string) {
  const env = makeEnvelope(capability, parameters);
  const host = nativeHost();
  if (host?.c2) {
    try {
      const r = JSON.parse(host.c2(JSON.stringify(env))) as { state?: string; result?: string };
      return toRecord(env, (r.state as CommandRecord["state"]) ?? "COMPLETED", r.result ?? result);
    } catch {
      /* fall through */
    }
  }
  return toRecord(env, "COMPLETED", result);
}

function pushUsbConfig(sdr: SdrConfig) {
  const host = nativeHost();
  if (!host?.usbConfig) return;
  try {
    host.usbConfig(
      JSON.stringify({
        centerHz: sdr.centerHz,
        sampleRateHz: sdr.sampleRateHz,
        lnaGain: sdr.lnaGain,
        vgaGain: sdr.vgaGain,
        demod: sdr.demod,
        volume: sdr.volume,
        squelch: sdr.squelch,
      }),
    );
  } catch {
    /* ignore */
  }
}

function hintFor(device: SdrConfig["device"]) {
  if (device === "hackrf1") return "hackrf";
  if (device === "libresdr") return "libresdr";
  return "pluto";
}

function cropToSpan(src: Float32Array, sampleRate: number, spanHz: number, dest: Float32Array) {
  const n = dest.length;
  const sr = Math.max(1, sampleRate);
  if (spanHz >= sr * 0.95) {
    dest.set(src.subarray(0, n));
    return;
  }
  const frac = Math.max(0.04, spanHz / sr);
  const half = (src.length * frac) / 2;
  const mid = (src.length - 1) / 2;
  for (let i = 0; i < n; i++) {
    const t = n === 1 ? 0.5 : i / (n - 1);
    const srcIdx = mid - half + t * 2 * half;
    const i0 = Math.max(0, Math.min(src.length - 1, Math.floor(srcIdx)));
    const i1 = Math.min(src.length - 1, i0 + 1);
    const f = srcIdx - Math.floor(srcIdx);
    dest[i] = src[i0] * (1 - f) + src[i1] * f;
  }
}

let lastTick = 0;
let liveTimer = 0;
let nativeTimer = 0;
let scanTimer = 0;
const scratch = new Float32Array(BINS);
const usbFull = new Float32Array(BINS).fill(-110);

async function liveGetJson(url: string, token: string): Promise<unknown> {
  if (isNativeApk()) {
    const r = nativeRequest("GET", url, "", token);
    if (!r.ok) throw new Error(r.error || `HTTP ${r.status}`);
    return r.data;
  }
  const headers: Record<string, string> = {};
  if (token) headers.Authorization = `Bearer ${token}`;
  const res = await fetch(url, { signal: AbortSignal.timeout(2500), headers });
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return res.json();
}

async function pullLive(get: () => AppState, set: (p: Partial<AppState>) => void) {
  const { nodeUrl, mode, c2Token } = get();
  if (mode !== "live") return;
  try {
    const url = `${nodeUrl.replace(/\/$/, "")}/api/status`;
    const d = (await liveGetJson(url, c2Token)) as {
      system?: Record<string, unknown>;
      pipeline?: Record<string, unknown>;
      sdr?: Record<string, unknown>;
      ups?: Record<string, unknown>;
      nodes?: { registered_nodes?: { node_id: string; online: boolean; probe_ms?: number }[] };
    };
    const s = d.system ?? {};
    const p = d.pipeline ?? {};
    const sdr = d.sdr ?? {};
    const u = d.ups ?? {};
    const nodes = (d.nodes?.registered_nodes ?? []).map(
      (n: { node_id: string; online: boolean; probe_ms?: number }) => ({
        id: n.node_id,
        role: "enrolled",
        platform: "remote",
        online: n.online,
        latencyMs: n.probe_ms ?? null,
        detail: "",
      }),
    );
    const tel = get().tel;
    set({
      liveOk: true,
      liveError: null,
      tel: {
        ...tel,
        hostname: (s.hostname as string | undefined) ?? tel.hostname,
        piIp: (s.pi_ip as string | undefined) ?? tel.piIp,
        cpuPct: (s.cpu_pct as number | undefined) ?? tel.cpuPct,
        ramPct: (s.ram_pct as number | undefined) ?? tel.ramPct,
        cpuTemp: (s.cpu_temp as number | undefined) ?? tel.cpuTemp,
        pipelineActive: Boolean(p.active),
        timingHealthy: Boolean(p.timing_healthy ?? true),
        primaryWritten: (p.primary_written as number | undefined) ?? tel.primaryWritten,
        integrityFailed: (p.integrity_failed as number | undefined) ?? tel.integrityFailed,
        halMode: "HARDWARE",
        upsHealth: (u.health as Telemetry["upsHealth"] | undefined) ?? tel.upsHealth,
        upsPct: (u.battery_percent as number | undefined) ?? tel.upsPct,
        upsVolt: (u.battery_voltage_v as number | undefined) ?? tel.upsVolt,
        acPresent: (u.ac_present as boolean | undefined) ?? tel.acPresent,
        nodes: nodes.length ? nodes : tel.nodes,
      },
      sdr:
        sdr.center_hz != null
          ? { ...get().sdr, centerHz: sdr.center_hz as number, device: (sdr.active_device as SdrConfig["device"]) ?? get().sdr.device }
          : get().sdr,
    });
  } catch (err) {
    set({
      liveOk: false,
      liveError: err instanceof Error ? err.message : "link failed",
    });
  }
}

async function postLive(nodeUrl: string, path: string, body: unknown, token = "") {
  const url = `${nodeUrl.replace(/\/$/, "")}${path}`;
  if (isNativeApk()) {
    const r = nativeRequest("POST", url, JSON.stringify(body), token);
    if (!r.ok) throw new Error(r.error || `HTTP ${r.status}`);
    return;
  }
  await fetch(url, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
    body: JSON.stringify(body),
    signal: AbortSignal.timeout(2500),
  });
}

function num3(v: unknown, fallback: number): [number, number, number] {
  if (Array.isArray(v) && v.length >= 3) {
    return [Number(v[0]) || 0, Number(v[1]) || 0, Number(v[2]) || 0];
  }
  return [fallback, fallback, fallback];
}

function pullNative(get: () => AppState, set: (p: Partial<AppState>) => void) {
  const host = nativeHost();
  if (!host) return;
  const spec = nativeJson<{
    rx?: boolean;
    open?: boolean;
    listen?: boolean;
    muted?: boolean;
    kind?: UsbState["kind"];
    bins?: number[];
    source?: string;
    sampleRateHz?: number;
  }>(() => host.usbSpectrum?.());
  const sns = nativeJson<Record<string, unknown>>(() => host.sensors?.());
  const st = nativeJson<Record<string, unknown>>(() => host.usbScan?.());
  const pipe = nativeJson<Record<string, unknown>>(() => host.pipeline?.("stats"));

  const usbStatus = (st?.status as Record<string, unknown> | undefined) ?? st ?? {};
  const devices = Array.isArray(st?.devices)
    ? (st!.devices as UsbState["devices"])
    : Array.isArray(usbStatus.devices)
      ? (usbStatus.devices as UsbState["devices"])
      : get().usb.devices;

  const usb: UsbState = {
    ...get().usb,
    available: true,
    devices,
    open: Boolean(usbStatus.open ?? spec?.open),
    kind: (usbStatus.kind as UsbState["kind"]) ?? spec?.kind ?? get().usb.kind,
    rx: Boolean(spec?.rx ?? usbStatus.rx),
    listen: Boolean(spec?.listen ?? usbStatus.listen),
    muted: Boolean(spec?.muted),
    version: String(usbStatus.version ?? get().usb.version ?? ""),
    board: String(usbStatus.board ?? get().usb.board ?? ""),
    error: String(usbStatus.error ?? ""),
    source: spec?.rx ? "usb" : get().usb.source,
    sampleRateHz: Number(spec?.sampleRateHz ?? usbStatus.sampleRateHz ?? get().usb.sampleRateHz),
    pending: Boolean(usbStatus.pending),
    iio: Boolean(usbStatus.iio),
  };

  const next: Partial<AppState> = { usb };

  if (spec?.rx && Array.isArray(spec.bins) && spec.bins.length === BINS) {
    for (let i = 0; i < BINS; i++) usbFull[i] = Number(spec.bins[i]) || -120;
    next.usb = { ...usb, source: "usb" };
  }

  if (sns) {
    const mag = num3(sns.magUt, 0);
    const pixel: PixelSensors = {
      ...get().tel.pixel,
      available: Boolean(sns.available),
      magUt: mag,
      magAbs: Number(sns.magAbs) || Math.hypot(mag[0], mag[1], mag[2]),
      headingDeg: Number(sns.headingDeg) || 0,
      lat: sns.lat == null ? get().tel.pixel.lat : Number(sns.lat),
      lon: sns.lon == null ? get().tel.pixel.lon : Number(sns.lon),
      alt: sns.alt == null ? get().tel.pixel.alt : Number(sns.alt),
      accM: sns.accM == null ? get().tel.pixel.accM : Number(sns.accM),
      baroHpa: sns.baroHpa == null ? get().tel.pixel.baroHpa : Number(sns.baroHpa),
      cameraHash: String(sns.cameraHash ?? get().tel.pixel.cameraHash),
      accMs2: num3(sns.accMs2, 0),
      gyroRads: num3(sns.gyroRads, 0),
      lightLux: sns.lightLux == null ? get().tel.pixel.lightLux : Number(sns.lightLux),
      tempC: sns.tempC == null ? get().tel.pixel.tempC : Number(sns.tempC),
      trustScore: Number(sns.trustScore ?? get().tel.pixel.trustScore),
      hardwareTier: 2,
    };
    next.tel = { ...(next.tel ?? get().tel), pixel };
  }

  if (pipe) {
    next.pipe = {
      ...get().pipe,
      running: Boolean(pipe.running),
      primaryWritten: Number(pipe.primaryWritten ?? 0),
      secondaryWritten: Number(pipe.secondaryWritten ?? 0),
      integrityFailed: Number(pipe.integrityFailed ?? 0),
      lastFile: String(pipe.lastFile ?? ""),
      chainHead: String(pipe.chainHead ?? get().pipe.chainHead),
      genesis: String(pipe.genesis ?? get().pipe.genesis),
      hmacReady: Boolean(pipe.hmacReady),
      lastSha256: String(pipe.lastSha256 ?? ""),
      lastHmac: String(pipe.lastHmac ?? ""),
      fileVersion: String(pipe.fileVersion ?? "3.3"),
      buffered: Number(pipe.buffered ?? 0),
      route: String(pipe.route ?? "LOCAL_PRIMARY"),
      hardwareTier: 2,
      clockSource: "internal",
    };
  }

  set(next);
}

export const useApp = create<AppState>((set, get) => ({
  view: "ops",
  mode: "simulated",
  nodeUrl: "http://10.42.0.1:8080",
  c2Token: "",
  liveOk: false,
  liveError: null,
  operatorUnlocked: false,
  hydrated: false,
  sdr: { ...DEFAULT_SDR },
  tel: seedTelemetry(),
  commands: [],
  captures: [],
  usb: { ...DEFAULT_USB },
  pipe: { ...DEFAULT_PIPE },

  setView: (view) => set({ view }),

  hydrate: () => {
    if (get().hydrated) return;
    const s = loadSettings();
    const native = isNativeApk();
    const mode = s.mode;
    set({
      ...s,
      mode,
      hydrated: true,
      sdr: { ...DEFAULT_SDR, ...get().sdr, device: "hackrf1" },
      tel: {
        ...get().tel,
        halMode: mode === "simulated" ? "SIMULATOR" : "HARDWARE",
        hostname: mode === "live" ? get().tel.hostname : "pixel-9-pro-xl",
        lastEvent: native ? "Handset independent · waiting HackRF OTG" : "Simulator · Front Range",
      },
    });
    if (native) {
      try {
        nativeHost()?.usbAuto?.();
      } catch {
        /* ignore */
      }
      get().usbScan();
    }
  },

  tick: () => {
    const now = performance.now();
    const dt = lastTick ? clamp((now - lastTick) / 1000, 0.08, 0.5) : 0.2;
    lastTick = now;
    const { sdr, tel, mode } = get();
    if (sdr.paused) return;

    nativeTimer += dt;
    scanTimer += dt;
    if (isNativeApk() && nativeTimer > 0.35) {
      nativeTimer = 0;
      pullNative(get, set);
      if (scanTimer > 2.5) {
        scanTimer = 0;
        try {
          nativeHost()?.usbAuto?.();
        } catch {
          /* ignore */
        }
      }
    }

    const usbRx = get().usb.rx && get().usb.source === "usb";
    if (!usbRx) generateSpectrum(sdr, tel.t + dt, scratch);
    else cropToSpan(usbFull, get().usb.sampleRateHz || sdr.sampleRateHz, sdr.spanHz, scratch);

    const stats = spectrumStats(scratch, sdr);
    rfBus.push(scratch);
    const nextTel = tickTelemetry(tel, sdr, stats, dt);
    const pipe = get().pipe;
    if (pipe.running) {
      nextTel.primaryWritten = pipe.primaryWritten || nextTel.primaryWritten;
      nextTel.secondaryWritten = pipe.secondaryWritten || nextTel.secondaryWritten;
      nextTel.integrityFailed = pipe.integrityFailed;
      nextTel.pipelineActive = true;
    }
    if (get().usb.rx) {
      nextTel.halMode = "HARDWARE";
      nextTel.gpsLock = nextTel.pixel.lat != null;
      nextTel.timingHealthy = nextTel.gpsLock;
      nextTel.lastEvent = get().usb.listen
        ? `LISTEN ${sdr.demod} · ${(sdr.centerHz / 1e6).toFixed(3)} MHz`
        : `USB ${get().usb.kind.toUpperCase()} RX`;
    } else if (mode === "standalone") {
      nextTel.halMode = "HARDWARE";
      nextTel.gpsLock = nextTel.pixel.lat != null;
      nextTel.timingHealthy = nextTel.gpsLock;
    }
    set({ tel: nextTel });
    liveTimer += dt;
    if (mode === "live" && liveTimer > 2) {
      liveTimer = 0;
      void pullLive(get, set);
    }
  },

  applyPreset: (id) => {
    const p = PRESETS.find((x) => x.id === id);
    if (!p) return;
    const sdr = {
      ...get().sdr,
      preset: id,
      centerHz: p.hz,
      demod: p.demod,
      spanHz: p.span,
      waterfallMode: p.span >= 1.5e6 ? "SWEEP" : p.span >= 250e3 ? "NARROW" : "SCOPE",
    } as SdrConfig;
    set({
      sdr,
      commands: [
        command("sdr.center_frequency.set", { hz: p.hz }, `preset ${id}`),
        ...get().commands,
      ].slice(0, 40),
    });
    pushUsbConfig(sdr);
    if (get().sdr.audio) {
      try {
        nativeHost()?.listen?.(JSON.stringify({ on: true, demod: p.demod, centerHz: p.hz }));
      } catch {
        /* ignore */
      }
    }
    if (get().mode === "live") void postLive(get().nodeUrl, "/api/sdr/preset", { preset: id }, get().c2Token);
  },

  setCenterHz: (hz) => {
    const v = clamp(Math.round(hz), 1_000_000, 6_000_000_000);
    const sdr = { ...get().sdr, centerHz: v };
    set({
      sdr,
      commands: [command("sdr.center_frequency.set", { hz: v }, `${(v / 1e6).toFixed(3)} MHz`), ...get().commands].slice(
        0,
        40,
      ),
    });
    pushUsbConfig(sdr);
    if (get().mode === "live")
      void postLive(get().nodeUrl, "/api/sdr/config", { center_hz: v, demod_mode: get().sdr.demod }, get().c2Token);
  },

  nudgeCenter: (frac) => {
    const { sdr } = get();
    get().setCenterHz(sdr.centerHz + sdr.spanHz * frac);
  },

  setSpanMode: (m) => {
    set({ sdr: { ...get().sdr, waterfallMode: m, spanHz: SPAN_FOR_MODE[m] } });
  },

  zoom: (dir) => {
    const { sdr } = get();
    const next = dir === 1 ? sdr.spanHz / 2 : sdr.spanHz * 2;
    const spanHz = clamp(next, 50_000, 2_048_000);
    const waterfallMode: WaterfallMode = spanHz >= 1.5e6 ? "SWEEP" : spanHz >= 250e3 ? "NARROW" : "SCOPE";
    set({ sdr: { ...sdr, spanHz, waterfallMode } });
  },

  setGain: (which, db) => {
    const sdr = { ...get().sdr, [which === "lna" ? "lnaGain" : "vgaGain"]: db };
    set({
      sdr,
      commands: [command("sdr.gain.set", { gain_db: db, stage: which }, `${which} ${db} dB`), ...get().commands].slice(
        0,
        40,
      ),
    });
    pushUsbConfig(sdr);
  },

  setDemod: (demod) => {
    const sdr = { ...get().sdr, demod };
    set({ sdr });
    pushUsbConfig(sdr);
    if (sdr.audio) {
      try {
        nativeHost()?.listen?.(JSON.stringify({ on: true, demod }));
      } catch {
        /* ignore */
      }
    }
    if (get().mode === "live")
      void postLive(get().nodeUrl, "/api/sdr/config", { demod_mode: demod, center_hz: get().sdr.centerHz }, get().c2Token);
  },

  setDevice: (device) => {
    set({
      sdr: { ...get().sdr, device },
      commands: [command("sdr.mode.set", { device }, device), ...get().commands].slice(0, 40),
    });
    if (isNativeApk()) get().usbOpen(hintFor(device));
    if (get().mode === "live") void postLive(get().nodeUrl, "/api/sdr/config", { active_device: device }, get().c2Token);
  },

  setFloorCeil: (floor, ceil) => {
    const s = get().sdr;
    const floorDbm = floor ?? s.floorDbm;
    const ceilDbm = ceil ?? s.ceilDbm;
    set({
      sdr: {
        ...s,
        floorDbm: Math.min(floorDbm, ceilDbm - 5),
        ceilDbm: Math.max(ceilDbm, floorDbm + 5),
      },
    });
  },

  cyclePalette: () => {
    const p = ((get().sdr.palette + 1) % 3) as SdrConfig["palette"];
    set({ sdr: { ...get().sdr, palette: p } });
  },

  toggleAudio: () => {
    const on = !get().sdr.audio;
    const sdr = { ...get().sdr, audio: on };
    set({
      sdr,
      usb: { ...get().usb, listen: on },
      tel: { ...get().tel, lastEvent: on ? `LISTEN ${sdr.demod}` : "Speaker muted" },
    });
    const host = nativeHost();
    if (host?.listen) {
      try {
        host.listen(JSON.stringify({ on, demod: sdr.demod, volume: sdr.volume, squelch: sdr.squelch, centerHz: sdr.centerHz }));
      } catch {
        /* ignore */
      }
    }
  },
  setVolume: (v) => {
    const sdr = { ...get().sdr, volume: clamp(v, 0, 1) };
    set({ sdr });
    pushUsbConfig(sdr);
    if (sdr.audio) {
      try {
        nativeHost()?.listen?.(JSON.stringify({ on: true, volume: sdr.volume }));
      } catch {
        /* ignore */
      }
    }
  },
  setSquelch: (v) => {
    const sdr = { ...get().sdr, squelch: clamp(v, 0, 1) };
    set({ sdr });
    pushUsbConfig(sdr);
  },
  stepHz: (hz) => {
    get().setCenterHz(get().sdr.centerHz + hz);
  },
  togglePause: () => set({ sdr: { ...get().sdr, paused: !get().sdr.paused } }),

  setHalMode: (halMode) => {
    set({
      tel: { ...get().tel, halMode },
      commands: [command("sdr.mode.set", { mode: halMode.toLowerCase() }, halMode), ...get().commands].slice(0, 40),
    });
  },

  setPipeline: (running) => {
    const host = nativeHost();
    if (host?.pipeline) {
      try {
        host.pipeline(running ? "start" : "stop");
      } catch {
        /* ignore */
      }
    }
    set({
      sdr: { ...get().sdr, paused: !running },
      tel: { ...get().tel, pipelineActive: running },
      pipe: { ...get().pipe, running },
      commands: [
        command(running ? "pipeline.start" : "pipeline.stop", {}, running ? "started" : "stopped"),
        ...get().commands,
      ].slice(0, 40),
    });
  },

  resetBaseline: (hard) => {
    set({
      tel: {
        ...get().tel,
        baseline: "LEARNING",
        baselineHours: 0,
        primaryWritten: hard ? 0 : get().tel.primaryWritten,
        lastEvent: hard ? "Hard baseline reset" : "Soft baseline reset",
      },
      commands: [command("baseline.reset", { mode: hard ? "hard" : "soft" }, "LEARNING"), ...get().commands].slice(
        0,
        40,
      ),
    });
    if (get().mode === "live") {
      void postLive(get().nodeUrl, "/api/baseline/reset", { mode: hard ? "hard" : "soft" }, get().c2Token);
    }
  },

  setMode: (mode) => {
    const next = { mode, nodeUrl: get().nodeUrl, c2Token: get().c2Token, operatorUnlocked: get().operatorUnlocked };
    saveSettings(next);
    set({
      mode,
      liveError: null,
      tel: {
        ...get().tel,
        halMode: mode === "simulated" ? "SIMULATOR" : "HARDWARE",
        lastEvent: mode === "standalone" ? "Independent handset · no Alpha required" : mode === "live" ? "Alpha live" : "Simulator",
      },
    });
    if (mode === "live") void pullLive(get, set);
    if (mode === "standalone" && isNativeApk()) {
      try {
        nativeHost()?.usbAuto?.();
      } catch {
        /* ignore */
      }
    }
  },

  setNodeUrl: (nodeUrl) => {
    saveSettings({
      mode: get().mode,
      nodeUrl,
      c2Token: get().c2Token,
      operatorUnlocked: get().operatorUnlocked,
    });
    set({ nodeUrl });
  },

  setToken: (c2Token) => {
    saveSettings({
      mode: get().mode,
      nodeUrl: get().nodeUrl,
      c2Token,
      operatorUnlocked: get().operatorUnlocked,
    });
    set({ c2Token });
  },

  unlockOperator: (pin) => {
    const ok = pin === "1988";
    if (ok) {
      saveSettings({
        mode: get().mode,
        nodeUrl: get().nodeUrl,
        c2Token: get().c2Token,
        operatorUnlocked: true,
      });
      set({ operatorUnlocked: true });
    }
    return ok;
  },

  capture: () => {
    const { tel, sdr } = get();
    const ev: CaptureEvent = {
      id: `${Date.now()}`,
      ts: new Date().toISOString(),
      centerHz: sdr.centerHz,
      peakDbm: tel.peakDbm,
      peakHz: tel.peakHz,
      rGlobal: tel.rGlobal,
      snrDb: tel.snrDb,
      note: tel.lastEvent,
    };
    const host = nativeHost();
    if (host?.ingest) {
      try {
        host.ingest(JSON.stringify({ ...ev, hardware_tier: 2, modality: "capture" }));
      } catch {
        /* ignore */
      }
    }
    if (host?.pipeline) {
      try {
        host.pipeline("seal");
      } catch {
        /* ignore */
      }
    }
    set({
      captures: [ev, ...get().captures].slice(0, 24),
      tel: { ...tel, lastEvent: `Capture ${ev.id.slice(-6)} sealed` },
    });
  },

  applyPixelFix: (lat, lon, acc, alt) => {
    set({
      tel: {
        ...get().tel,
        pixel: {
          ...get().tel.pixel,
          available: true,
          lat,
          lon,
          accM: acc,
          alt: alt ?? get().tel.pixel.alt,
        },
      },
    });
  },

  applyMag: (x, y, z) => {
    const magAbs = Math.hypot(x, y, z);
    const headingDeg = ((Math.atan2(y, x) * 180) / Math.PI + 360) % 360;
    set({
      tel: {
        ...get().tel,
        pixel: {
          ...get().tel.pixel,
          available: true,
          magUt: [x, y, z],
          magAbs,
          headingDeg,
        },
      },
    });
  },

  usbScan: () => {
    const host = nativeHost();
    if (!host?.usbScan) return;
    pullNative(get, set);
  },

  usbOpen: (hint) => {
    const host = nativeHost();
    if (!host?.usbOpen) return;
    try {
      host.usbOpen(hint ?? hintFor(get().sdr.device));
      pushUsbConfig(get().sdr);
      pullNative(get, set);
      set({
        commands: [command("sdr.mode.set", { device: hint ?? get().sdr.device }, "USB open"), ...get().commands].slice(
          0,
          40,
        ),
      });
    } catch {
      /* ignore */
    }
  },

  usbClose: () => {
    const host = nativeHost();
    if (!host?.usbClose) return;
    try {
      host.usbClose();
      set({ usb: { ...get().usb, open: false, rx: false, source: "none" } });
    } catch {
      /* ignore */
    }
  },

  usbRx: (on) => {
    const host = nativeHost();
    if (!host?.usbRx) return;
    try {
      if (on && !get().usb.open) host.usbOpen?.(hintFor(get().sdr.device));
      host.usbRx(on ? "on" : "off");
      set({
        usb: { ...get().usb, rx: on, source: on ? "usb" : "none" },
        tel: {
          ...get().tel,
          halMode: on ? "HARDWARE" : get().tel.halMode,
          lastEvent: on ? "USB RX armed · clock_source=internal · SECONDARY" : "USB RX idle",
        },
        commands: [command("sdr.mode.set", { mode: on ? "real" : "simulated" }, on ? "USB RX" : "USB idle"), ...get().commands].slice(
          0,
          40,
        ),
      });
    } catch {
      /* ignore */
    }
  },

  sealPipeline: () => {
    const host = nativeHost();
    if (host?.pipeline) {
      try {
        host.pipeline("seal");
      } catch {
        /* ignore */
      }
    }
    set({
      commands: [command("hdf5.summary.read", {}, "seal"), ...get().commands].slice(0, 40),
      tel: { ...get().tel, lastEvent: "HDF5 sealed · SHA-256 sidecar written" },
    });
  },

  rotatePipeline: () => {
    const host = nativeHost();
    if (host?.pipeline) {
      try {
        host.pipeline("rotate");
      } catch {
        /* ignore */
      }
    }
    set({
      commands: [command("pipeline.rotate_output", {}, "rotated"), ...get().commands].slice(0, 40),
    });
  },
}));
