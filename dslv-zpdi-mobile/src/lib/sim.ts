import { BINS, type SdrConfig, type Telemetry } from "./types";
import { clamp } from "./utils";

function hash32(n: number) {
  let x = n | 0;
  x ^= x << 13;
  x ^= x >>> 17;
  x ^= x << 5;
  return (x >>> 0) / 4294967296;
}

function noise(t: number, seed: number) {
  const a = hash32(Math.floor(t * 17 + seed * 91));
  const b = hash32(Math.floor(t * 17 + seed * 91) + 1);
  const f = (t * 17) % 1;
  return a * (1 - f) + b * f - 0.5;
}

export interface Carrier {
  freq: number;
  bw: number;
  amp: number;
  drift: number;
}

/** Front Range + Fremont corridor emitters the Alpha Pluto actually hears. */
export const FIELD_CARRIERS: Carrier[] = [
  { freq: 88_100_000, bw: 220_000, amp: 22, drift: 18 },
  { freq: 88_900_000, bw: 240_000, amp: 34, drift: 40 },
  { freq: 89_700_000, bw: 200_000, amp: 18, drift: -12 },
  { freq: 91_500_000, bw: 220_000, amp: 26, drift: 8 },
  { freq: 92_900_000, bw: 260_000, amp: 38, drift: -16 },
  { freq: 94_300_000, bw: 280_000, amp: 44, drift: 10 },
  { freq: 95_100_000, bw: 240_000, amp: 31, drift: 22 },
  { freq: 96_100_000, bw: 220_000, amp: 24, drift: -8 },
  { freq: 96_900_000, bw: 260_000, amp: 36, drift: 14 },
  { freq: 97_700_000, bw: 200_000, amp: 21, drift: 6 },
  { freq: 98_100_000, bw: 300_000, amp: 48, drift: 12 },
  { freq: 98_900_000, bw: 220_000, amp: 28, drift: -20 },
  { freq: 99_900_000, bw: 280_000, amp: 41, drift: 9 },
  { freq: 101_500_000, bw: 260_000, amp: 33, drift: -22 },
  { freq: 102_700_000, bw: 240_000, amp: 29, drift: 15 },
  { freq: 103_900_000, bw: 220_000, amp: 23, drift: -11 },
  { freq: 104_500_000, bw: 260_000, amp: 35, drift: 7 },
  { freq: 105_500_000, bw: 240_000, amp: 30, drift: -14 },
  { freq: 106_300_000, bw: 260_000, amp: 32, drift: 19 },
  { freq: 107_300_000, bw: 220_000, amp: 20, drift: -6 },
  { freq: 118_700_000, bw: 18_000, amp: 16, drift: 40 },
  { freq: 120_150_000, bw: 16_000, amp: 22, drift: 80 },
  { freq: 121_900_000, bw: 14_000, amp: 14, drift: -30 },
  { freq: 156_800_000, bw: 20_000, amp: 26, drift: 8 },
  { freq: 157_100_000, bw: 16_000, amp: 15, drift: 4 },
  { freq: 162_400_000, bw: 22_000, amp: 38, drift: 3 },
  { freq: 162_475_000, bw: 22_000, amp: 28, drift: -4 },
  { freq: 162_550_000, bw: 22_000, amp: 24, drift: -6 },
  { freq: 1_090_000_000, bw: 120_000, amp: 28, drift: 0 },
  { freq: 1_000_000, bw: 18_000, amp: 20, drift: 2 },
];

export function generateSpectrum(sdr: SdrConfig, t: number, out: Float32Array) {
  const lo = sdr.centerHz - sdr.spanHz / 2;
  const gainBoost = (sdr.lnaGain / 40) * 10 + (sdr.vgaGain / 62) * 7;
  const floor = -92 + (40 - sdr.lnaGain) * 0.16 + noise(t, 3) * 1.1;
  const binHz = sdr.spanHz / Math.max(1, BINS - 1);

  for (let i = 0; i < BINS; i++) {
    const f = lo + i * binHz;
    let p =
      floor +
      (hash32(i * 997 + Math.floor(t * 40)) - 0.5) * 5.4 +
      noise(t + i * 0.01, 9) * 1.8;

    for (let c = 0; c < FIELD_CARRIERS.length; c++) {
      const car = FIELD_CARRIERS[c];
      const freq = car.freq + Math.sin(t * 0.15 + c) * car.drift;
      const visBw = Math.max(car.bw, binHz * 2.4);
      const df = (f - freq) / visBw;
      const fade = 0.82 + 0.18 * Math.sin(t * (0.7 + c * 0.03) + c);
      p += (car.amp + gainBoost * 0.4) * fade * Math.exp(-0.5 * df * df);
    }

    const hop = 98_100_000 + Math.sin(t * 0.55) * 6_000_000;
    const hdf = (f - hop) / Math.max(50_000, binHz * 1.6);
    p += 18 * Math.exp(-0.5 * hdf * hdf) * (0.5 + 0.5 * Math.sin(t * 2.3));

    const dc = (f - sdr.centerHz) / Math.max(12_000, binHz);
    p += (7 + gainBoost * 0.15) * Math.exp(-0.5 * dc * dc);

    out[i] = p;
  }
}

export function spectrumStats(bins: Float32Array, sdr: SdrConfig) {
  const lo = sdr.centerHz - sdr.spanHz / 2;
  let peak = -200;
  let peakI = 0;
  const sorted = Array.from(bins).sort((a, b) => a - b);
  const floor = sorted[Math.floor(sorted.length * 0.5)] ?? -90;
  let anomalies = 0;
  for (let i = 0; i < bins.length; i++) {
    const v = bins[i];
    if (v > peak) {
      peak = v;
      peakI = i;
    }
    if (v > floor + 10) anomalies += 1;
  }
  const peakHz = lo + (peakI / (bins.length - 1)) * sdr.spanHz;
  return {
    peakDbm: peak,
    peakHz,
    noiseFloorDbm: floor,
    snrDb: peak - floor,
    anomalyBins: anomalies,
  };
}

export function tickTelemetry(
  prev: Telemetry,
  sdr: SdrConfig,
  stats: ReturnType<typeof spectrumStats>,
  dt: number,
  liveOverride?: Partial<Telemetry>,
): Telemetry {
  const t = prev.t + dt;
  const lock = prev.halMode !== "OFFLINE";
  const gps = lock;
  const jitter = gps ? 48 + noise(t, 11) * 36 + Math.abs(Math.sin(t * 0.2)) * 22 : 4200;
  const rTarget = lock ? 0.86 + noise(t, 7) * 0.08 + (stats.snrDb > 25 ? 0.04 : 0) : 0.18;
  const rGlobal = clamp(prev.rGlobal + (rTarget - prev.rGlobal) * 0.12, 0.05, 0.99);
  const rLocal = clamp(rGlobal + noise(t, 19) * 0.04, 0.05, 0.99);
  const rSmooth = clamp(prev.rSmooth + (rGlobal - prev.rSmooth) * 0.06, 0.05, 0.99);
  const phases = prev.phases.map((p, i) => p + dt * (0.7 + i * 0.11) * (0.4 + rGlobal));
  const cpu = clamp(18 + sdr.lnaGain * 0.35 + stats.anomalyBins * 0.08 + noise(t, 4) * 8, 6, 96);
  const ram = clamp(41 + noise(t, 5) * 4, 28, 88);
  const temp = clamp(46 + cpu * 0.18 + noise(t, 6) * 1.4, 38, 82);
  const ingest = sdr.paused ? 0 : 9.4 + noise(t, 8) * 1.2;
  const writes = sdr.paused ? 0 : Math.max(0, ingest * dt);

  const magX = 12.4 + Math.sin(t * 0.31) * 1.6 + noise(t, 21) * 0.8;
  const magY = -38.2 + Math.cos(t * 0.27) * 1.1 + noise(t, 22) * 0.7;
  const magZ = 31.6 + Math.sin(t * 0.19) * 0.9 + noise(t, 23) * 0.6;
  const magAbs = Math.hypot(magX, magY, magZ);
  const heading = (Math.atan2(magY, magX) * 180) / Math.PI;
  const radon = clamp(9.4 + Math.sin(t * 0.04) * 1.8 + noise(t, 31) * 0.6, 4.2, 16);
  const kp = clamp(2.8 + Math.sin(t * 0.01) * 1.4 + noise(t, 41) * 0.5, 0, 8);

  const next: Telemetry = {
    ...prev,
    t,
    cpuPct: cpu,
    ramPct: ram,
    cpuTemp: temp,
    uptimeS: prev.uptimeS + dt,
    pipelineActive: !sdr.paused && prev.halMode !== "OFFLINE",
    timingHealthy: jitter < 500,
    gpsLock: gps,
    ppsJitterNs: Math.max(8, jitter),
    chronyOffsetUs: gps ? 0.62 + noise(t, 12) * 0.35 : 48,
    chronyStratum: gps ? 1 : 8,
    rLocal,
    rSmooth,
    rGlobal,
    phases,
    peakDbm: stats.peakDbm,
    peakHz: stats.peakHz,
    noiseFloorDbm: stats.noiseFloorDbm,
    snrDb: stats.snrDb,
    anomalyBins: stats.anomalyBins,
    primaryWritten: prev.baseline === "LOCKED" ? prev.primaryWritten + writes : prev.primaryWritten,
    secondaryWritten: prev.secondaryWritten + writes,
    ingestHz: ingest,
    kp,
    sfi: 142 + Math.sin(t * 0.008) * 8,
    auroraPct: clamp(kp * 9.5, 0, 90),
    storm: kp > 5 ? "G2 watch — Fremont corridor" : kp > 4 ? "Unsettled geomagnetic" : "Quiet",
    radonPci: radon,
    upsPct: clamp(96.4 - (prev.acPresent ? 0 : dt * 0.02) + noise(t, 51) * 0.2, 8, 100),
    upsVolt: 4.08 + noise(t, 52) * 0.04,
    lastEvent:
      stats.anomalyBins > 28
        ? `RF excursion ${stats.anomalyBins} bins @ ${(stats.peakHz / 1e6).toFixed(3)} MHz`
        : prev.lastEvent,
    nodes: prev.nodes.map((n) =>
      n.id === "alpha-pi-tier1"
        ? { ...n, online: true, latencyMs: 4 + Math.abs(noise(t, 61)) * 10 }
        : n.id === "pixel-9-pro-xl"
          ? { ...n, online: true, latencyMs: 1 }
          : n,
    ),
    pixel: prev.pixel.available
      ? prev.pixel
      : {
          ...prev.pixel,
          magUt: [magX, magY, magZ],
          magAbs,
          headingDeg: (heading + 360) % 360,
          lat: 38.4286 + noise(t, 71) * 0.0004,
          lon: -105.227 + noise(t, 72) * 0.0004,
          alt: 1628 + noise(t, 73) * 3,
          accM: 4.8,
          baroHpa: 834.2 + Math.sin(t * 0.05) * 0.6,
        },
  };

  if (liveOverride) Object.assign(next, liveOverride);
  return next;
}

export function seedTelemetry(): Telemetry {
  return {
    t: 0,
    hostname: "alpha-pi",
    piIp: "10.42.0.1",
    cpuPct: 22,
    ramPct: 41,
    cpuTemp: 51,
    uptimeS: 62_411,
    pipelineActive: true,
    halMode: "SIMULATOR",
    baseline: "LOCKED",
    baselineHours: 74.2,
    timingHealthy: true,
    gpsLock: true,
    ppsJitterNs: 86,
    chronyOffsetUs: 0.7,
    chronyStratum: 1,
    rLocal: 0.84,
    rSmooth: 0.86,
    rGlobal: 0.88,
    phases: Array.from({ length: 12 }, (_, i) => (i / 12) * Math.PI * 2),
    peakDbm: -42,
    peakHz: 98_100_000,
    noiseFloorDbm: -91,
    snrDb: 49,
    anomalyBins: 6,
    primaryWritten: 184220,
    secondaryWritten: 211903,
    integrityFailed: 0,
    ingestHz: 9.6,
    kp: 3.1,
    sfi: 142,
    auroraPct: 28,
    storm: "Quiet",
    radonPci: 9.6,
    upsHealth: "healthy",
    upsPct: 97.2,
    upsVolt: 4.11,
    acPresent: true,
    lastEvent: "Baseline LOCKED — PRIMARY stream armed",
    nodes: [
      {
        id: "alpha-pi-tier1",
        role: "Tier-1 anchor",
        platform: "Pi 5 16GB · PlutoSDR+ · LBE-1421",
        online: true,
        latencyMs: 6,
        detail: "GPSDO 10 MHz + PPS GPIO8",
      },
      {
        id: "pixel-9-pro-xl",
        role: "Tier-2 C2 / mobile",
        platform: "GrapheneOS · Termux · Debian proot",
        online: true,
        latencyMs: 1,
        detail: "This handset · USB SDR · HDF5 · C2 :8444",
      },
    ],
    pixel: {
      available: false,
      magUt: [12.4, -38.2, 31.6],
      magAbs: 51.2,
      headingDeg: 288,
      lat: 38.4286,
      lon: -105.227,
      alt: 1628,
      accM: 5,
      baroHpa: 834.1,
      cameraHash: "7c3e91a0b4d2",
      accMs2: [0.12, 0.04, 9.71],
      gyroRads: [0.001, -0.002, 0.0],
      lightLux: 120,
      tempC: 31.4,
      trustScore: 0.72,
      hardwareTier: 2,
    },
  };
}
