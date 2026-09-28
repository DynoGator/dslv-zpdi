/** Closed-form metrology from Rev 3.4. No measured residuals live here. */

export const C_MPS = 299_792_458;
export const F_L1_HZ = 154 * 10.23e6;
export const F_L5_HZ = 115 * 10.23e6;
export const F_RATIO = 154 / 115;
export const IONO_RATIO = 115 / 154;
export const LAMBDA_L1_M = C_MPS / F_L1_HZ;
export const PAPER_REV = "3.4";

export type ChainId = "S" | "C";

export function num(raw: string | number | null | undefined): number | null {
  if (typeof raw === "number") return Number.isFinite(raw) ? raw : null;
  if (raw == null) return null;
  const t = raw.trim().replace(/,/g, "");
  if (!t) return null;
  const n = Number(t);
  return Number.isFinite(n) ? n : null;
}

/** σ_φ ≈ 2π f τ σ_y  (rad). Rev 3.4 §3.4. */
export function sigmaPhiRad(fHz: number, tauS: number, sigmaY: number): number {
  return 2 * Math.PI * fHz * tauS * sigmaY;
}

export function lightTimeS(baselineM: number): number {
  return baselineM / C_MPS;
}

/** Baseline whose light time equals n dump samples. */
export function baselineForLags(fdHz: number, nLags: number): number {
  return (nLags / fdHz) * C_MPS;
}

export function nyquistHz(fdHz: number): number {
  return fdHz / 2;
}

/** Carrier-phase radians for a geometric path at frequency f. */
export function pathToPhaseRad(pathM: number, fHz: number): number {
  return (pathM * 2 * Math.PI * fHz) / C_MPS;
}

export function phaseToPathM(phiRad: number, fHz: number): number {
  return (phiRad * C_MPS) / (2 * Math.PI * fHz);
}

/**
 * Magnitude-squared coherence null for L non-overlapped windows.
 * γ̂ ~ Beta(1, L−1). Goodman / Carter / Gish & Cochran.
 */
export function betaNull(L: number): {
  eGamma: number;
  varGamma: number;
  eR: number;
  sigmaR: number;
  rMin3: number;
} | null {
  if (!(L > 1)) return null;
  const eGamma = 1 / L;
  const varGamma = (L - 1) / (L * L * (L + 1));
  const eR = Math.sqrt(Math.PI / (4 * L));
  const sigmaR = Math.sqrt((4 - Math.PI) / (4 * L));
  return { eGamma, varGamma, eR, sigmaR, rMin3: eR + 3 * sigmaR };
}

export function lEff(durationS: number, tauCorrS: number): number | null {
  if (!(durationS > 0) || !(tauCorrS > 0)) return null;
  return durationS / tauCorrS;
}

/**
 * Shared-phase amplitude from coherence.
 * Exact: r = φ² / (φ² + σ²) ⇒ φ = σ √(r / (1−r)), for 0<r<1.
 * Paper's small-signal map φ ≈ σ √r is returned alongside it.
 */
export function weakPhase(sigmaPhi: number, r: number): { approx: number; exact: number } | null {
  if (!(sigmaPhi > 0) || !(r > 0) || !(r < 1)) return null;
  return {
    approx: sigmaPhi * Math.sqrt(r),
    exact: sigmaPhi * Math.sqrt(r / (1 - r)),
  };
}

/**
 * |ionospheric carrier phase| in radians.
 * Δρ = −40.3 TEC / f² metres on the carrier; φ = 2π Δρ / λ.
 * TEC argument is in TECU (10¹⁶ m⁻²).
 */
export function ionoPhaseRad(tecTecU: number, fHz: number): number {
  const tec = tecTecU * 1e16;
  return Math.abs((40.3 * tec * 2 * Math.PI) / (fHz * C_MPS));
}

/** σ_φ,dump ≈ 1/√(2 · C/N0 · T), T = 1/f_d. C/N0 in dB-Hz. */
export function dumpPhaseSigma(cn0DbHz: number, fdHz: number): number | null {
  if (!(fdHz > 0)) return null;
  const cn0 = 10 ** (cn0DbHz / 10);
  const T = 1 / fdHz;
  if (!(cn0 > 0) || !(T > 0)) return null;
  return 1 / Math.sqrt(2 * cn0 * T);
}

export function rss(values: number[]): number {
  return Math.sqrt(values.reduce((s, v) => s + v * v, 0));
}

const EARTH_R_M = 6_371_008.8;

export function haversineM(
  a: { lat: number; lon: number },
  b: { lat: number; lon: number },
): number {
  const φ1 = (a.lat * Math.PI) / 180;
  const φ2 = (b.lat * Math.PI) / 180;
  const dφ = ((b.lat - a.lat) * Math.PI) / 180;
  const dλ = ((b.lon - a.lon) * Math.PI) / 180;
  const h = Math.sin(dφ / 2) ** 2 + Math.cos(φ1) * Math.cos(φ2) * Math.sin(dλ / 2) ** 2;
  return 2 * EARTH_R_M * Math.asin(Math.min(1, Math.sqrt(h)));
}

export type ChromaticClass = "delay" | "iono" | "offset" | "none";

export function chromatic(
  phi1: number,
  phi2: number,
  tolRel: number,
): { ratio: number; klass: ChromaticClass; target: number; relErr: number } | null {
  if (!(phi2 !== 0) || !Number.isFinite(phi1) || !Number.isFinite(phi2)) return null;
  const ratio = phi1 / phi2;
  const options: { klass: ChromaticClass; target: number }[] = [
    { klass: "delay", target: F_RATIO },
    { klass: "iono", target: IONO_RATIO },
    { klass: "offset", target: 1 },
  ];
  let best = options[0]!;
  let bestErr = Math.abs(ratio - best.target) / best.target;
  for (const opt of options.slice(1)) {
    const err = Math.abs(ratio - opt.target) / Math.abs(opt.target);
    if (err < bestErr) {
      best = opt;
      bestErr = err;
    }
  }
  const klass: ChromaticClass = bestErr <= tolRel ? best.klass : "none";
  return { ratio, klass, target: best.target, relErr: bestErr };
}

export type MorphCode =
  | "propagation"
  | "switch3"
  | "resolution-limited"
  | "chain-s-hardware"
  | "chain-c-candidate"
  | "follow-up"
  | "removed-by-null";

export type MorphResult = {
  tauC: number;
  deltaTau: number;
  resolutionLimited: boolean;
  syncOk: boolean;
  nearZero: boolean;
  code: MorphCode;
  title: string;
  detail: string;
  notSignaling: boolean;
};

export function morphology(input: {
  tauS: number;
  baselineM: number;
  fdHz: number;
  sigmaSyncS: number;
  chain: ChainId;
  colocated: boolean;
  alsoOnSeparated: boolean;
  catalogMultipath: boolean;
  vanishesWithIgs: boolean;
  commonClockExcludesHardware: boolean;
  delayClass: boolean;
}): MorphResult | null {
  const { baselineM, fdHz } = input;
  if (!(baselineM > 0) || !(fdHz > 0)) return null;
  const tauC = lightTimeS(baselineM);
  const deltaTau = 1 / fdHz;
  const resolutionLimited = !(tauC > 10 * deltaTau);
  const syncOk = input.sigmaSyncS < tauC;
  const absT = Math.abs(input.tauS);
  const nearZero = absT <= Math.max(input.sigmaSyncS, deltaTau) || absT < 0.1 * tauC;

  const base = { tauC, deltaTau, resolutionLimited, syncOk, nearZero, notSignaling: nearZero };

  if (input.vanishesWithIgs) {
    return {
      ...base,
      code: "removed-by-null",
      title: "Removed by the null",
      detail:
        "The peak vanishes when common-view, ionosphere, or IGS terms are applied. That is subtraction working. Switch 1 does not promote it.",
    };
  }

  if (input.catalogMultipath && (absT >= tauC || !nearZero)) {
    return {
      ...base,
      code: "propagation",
      title: "Catalogued multipath",
      detail:
        "The lag matches a catalogued multipath extra delay. Ordinary propagation. Switch 1 fails for this candidate.",
    };
  }

  if (absT > tauC * 1.05) {
    return {
      ...base,
      code: "switch3",
      title: "Outside the light cone of the baseline",
      detail:
        "A peak at |τ| > τ_c cannot be direct propagation. With no catalogued multipath delay, treat it as dispersive or instrumental and open Switch 3. It is not a detection.",
    };
  }

  if (!nearZero && absT >= tauC * 0.8) {
    return {
      ...base,
      code: "propagation",
      title: "Direct propagation",
      detail:
        "Peak at |τ| ≈ τ_c. Equality is the on-axis source. Ordinary propagation. Switch 1 fails for this candidate.",
    };
  }

  if (resolutionLimited) {
    return {
      ...base,
      code: "resolution-limited",
      title: "Resolution-limited baseline",
      detail: `τ_c = ${tauC.toExponential(2)} s is not ≫ δτ = ${deltaTau.toExponential(2)} s at this f_d. The pair still belongs in Analysis A. No |τ| ≪ τ_c claim is allowed. A 1 s average is not a spacelike sample.`,
    };
  }

  if (!syncOk) {
    return {
      ...base,
      code: "resolution-limited",
      title: "Time transfer is not finer than the baseline",
      detail:
        "σ_sync is not ≪ τ_c. An excess at τ≈0 is not meaningful on this baseline until the pre-registered transfer method gets there. Switch 6 is the reading if it moves under another clock.",
    };
  }

  if (input.chain === "S" && input.colocated) {
    return {
      ...base,
      code: "chain-s-hardware",
      title: "Co-located excess on Chain S",
      detail:
        "A |τ| ≪ τ_c peak that also appears on the co-located pair is site-common hardware on Chain S. Co-located excess is not anomalous under H_S.",
    };
  }

  if (
    input.chain === "C" &&
    input.colocated &&
    input.alsoOnSeparated &&
    input.commonClockExcludesHardware &&
    input.delayClass
  ) {
    return {
      ...base,
      notSignaling: true,
      code: "chain-c-candidate",
      title: "Chain C morphology — still not signaling",
      detail:
        "Present on co-located and separated pairs, common-clock decomposition has excluded the hardware reading, and Switch 2 landed in the delay class. This is the only Chain-C morphology the paper says is worth a data paper. It is common-mode. It is not superluminal signaling. No information transfer is possible via a common-mode field. It still needs a hold-out window.",
    };
  }

  return {
    ...base,
    code: "follow-up",
    title: input.chain === "C" ? "Chain C follow-up, not yet a candidate" : "Chain S follow-up",
    detail:
      input.chain === "C"
        ? "Near-zero lag on a resolved baseline. H_C still has to clear the common-clock floor, Switch 2 on the uncombined L1/L5 pair (delay class only), and Switch 6 under an independent time transfer. Until then it is a queue entry, not a result."
        : "Near-zero lag that is not confined to the co-located control. Label it H_S and send it to Switch 2. The iono-free combination is not the Switch 2 observable.",
  };
}

/** Variance split stated in §4.4. Valid only if the two runs differ by the clock. */
export function clockIsolation(commonClockRms: number, independentRms: number): number | null {
  if (!(commonClockRms >= 0) || !(independentRms >= 0)) return null;
  const diff = independentRms ** 2 - commonClockRms ** 2;
  if (diff < 0) return null;
  return Math.sqrt(diff);
}

export type IdentityCheck = {
  id: string;
  label: string;
  got: string;
  expect: string;
  pass: boolean;
};

export function paperIdentityChecks(): IdentityCheck[] {
  const phi = sigmaPhiRad(F_L1_HZ, 1, 1e-12);
  const ionoL1 = ionoPhaseRad(0.1, F_L1_HZ);
  const ionoHf = ionoPhaseRad(0.1, 100e6);
  const tau10 = lightTimeS(10_000);
  const d1 = baselineForLags(1_000, 1);
  const floor = betaNull(86_400);
  const floor300 = betaNull(300);
  const weak = weakPhase(0.3, floor?.rMin3 ?? 0);
  const weak300 = floor300 ? weakPhase(0.3, floor300.rMin3) : null;
  const pathMm = weak ? phaseToPathM(weak.approx, F_L1_HZ) * 1e3 : NaN;
  const path300 = weak300 ? phaseToPathM(weak300.approx, F_L1_HZ) * 1e3 : NaN;
  const rssLo = rss([pathToPhaseRad(0.01, F_L1_HZ), pathToPhaseRad(0.005, F_L1_HZ)]);
  const rssHi = rss([pathToPhaseRad(0.01, F_L1_HZ), pathToPhaseRad(0.02, F_L1_HZ)]);

  const near = (got: number, exp: number, frac: number) => Math.abs(got - exp) <= Math.abs(exp) * frac;

  return [
    {
      id: "phi",
      label: "GPSDO σ_φ at L1, σ_y(1 s)=10⁻¹²",
      got: phi.toExponential(3) + " rad",
      expect: "9.9×10⁻³ rad",
      pass: near(phi, 9.9e-3, 0.02),
    },
    {
      id: "ratio",
      label: "f₁/f₂",
      got: F_RATIO.toFixed(6),
      expect: "154/115 ≈ 1.339",
      pass: near(F_RATIO, 154 / 115, 1e-12),
    },
    {
      id: "iono-l1",
      label: "0.1 TECU carrier phase at L1",
      got: ionoL1.toFixed(3) + " rad",
      expect: "≈ 0.53 rad",
      pass: near(ionoL1, 0.53, 0.04),
    },
    {
      id: "iono-hf",
      label: "0.1 TECU carrier phase at 100 MHz",
      got: ionoHf.toFixed(2) + " rad",
      expect: "≈ 8.4 rad",
      pass: near(ionoHf, 8.4, 0.03),
    },
    {
      id: "tau",
      label: "Light time, 10 km",
      got: (tau10 * 1e6).toFixed(2) + " µs",
      expect: "≈ 33 µs",
      pass: near(tau10, 33e-6, 0.02),
    },
    {
      id: "res",
      label: "δτ = 1 ms baseline",
      got: (d1 / 1000).toFixed(1) + " km",
      expect: "300 km",
      pass: near(d1, 300_000, 0.01),
    },
    {
      id: "beta",
      label: "Naive L=86400 magnitude floor",
      got: floor ? floor.eR.toExponential(2) + " / " + floor.sigmaR.toExponential(2) : "—",
      expect: "E[r]≈3.0×10⁻³, σ≈1.6×10⁻³",
      pass: !!floor && near(floor.eR, 3.0e-3, 0.03) && near(floor.sigmaR, 1.6e-3, 0.05),
    },
    {
      id: "rmin",
      label: "Calendar r_min (κ=3), not the program floor",
      got: floor ? floor.rMin3.toExponential(2) : "—",
      expect: "≈ 7.7×10⁻³",
      pass: !!floor && near(floor.rMin3, 7.7e-3, 0.05),
    },
    {
      id: "weak",
      label: "σ_φ=0.3, calendar r_min → path at L1",
      got: Number.isFinite(pathMm) ? pathMm.toFixed(2) + " mm" : "—",
      expect: "≈ 0.8 mm",
      pass: near(pathMm, 0.8, 0.08),
    },
    {
      id: "weak300",
      label: "L_eff=300, κ=3 → path at L1",
      got: Number.isFinite(path300) ? path300.toFixed(2) + " mm" : "—",
      expect: "≈ 3.3 mm",
      pass: near(path300, 3.3, 0.08),
    },
    {
      id: "rss",
      label: "Chain S RSS, trop 1 cm + multipath 0.5–2 cm",
      got: rssLo.toFixed(2) + "–" + rssHi.toFixed(2) + " rad",
      expect: "inside 0.30–0.80 rad",
      pass: rssLo >= 0.3 && rssLo <= 0.5 && rssHi >= 0.6 && rssHi <= 0.8,
    },
  ];
}
