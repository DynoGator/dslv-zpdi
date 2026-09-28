export const ART = {
  hero: "/art/hero.jpg",
  clock: "/art/clock.jpg",
  chainS: "/art/chain-s.jpg",
  chainC: "/art/chain-c.jpg",
  chromatic: "/art/chromatic.jpg",
  null: "/art/null.jpg",
  companion: "/art/companion.jpg",
  field: "/art/field.jpg",
} as const;

export type PreregField = {
  id: string;
  label: string;
  hint: string;
  placeholder?: string;
};

export const PREREG: PreregField[] = [
  {
    id: "band",
    label: "Science band",
    hint: "L1 + L5. Any other band needs its own ionospheric row and a spectrum-survey hash.",
    placeholder: "GPS L1 + L5",
  },
  {
    id: "surveyHash",
    label: "Spectrum-survey hash",
    hint: "SHA-256 of the frozen survey. Paste the digest. This app does not invent one.",
    placeholder: "hex digest",
  },
  {
    id: "fdHz",
    label: "Prompt dump rate f_d (Hz)",
    hint: "Pre-registered. Nominal 1–10 kHz. Not tuned after the registry timestamp.",
    placeholder: "1000",
  },
  {
    id: "elevMask",
    label: "Elevation mask (degrees)",
    hint: "Satellites below the mask never enter a chain.",
    placeholder: "15",
  },
  {
    id: "windowS",
    label: "Analysis A window (s)",
    hint: "Non-overlapped. Overlapped windows are not used in the science run.",
    placeholder: "1",
  },
  {
    id: "block",
    label: "Frozen Politis–White block length",
    hint: "Selected on pilot data, reconciled with the Allan turnover, then frozen.",
    placeholder: "samples or seconds",
  },
  {
    id: "allanNote",
    label: "Allan cross-check",
    hint: "Quote the measured σ_y(τ) turnover of the installed units, not a catalog class.",
  },
  {
    id: "fdr",
    label: "FDR procedure",
    hint: "Benjamini–Hochberg under PRDS. Chain S and Chain C are separate families.",
    placeholder: "BH, PRDS, per chain",
  },
  {
    id: "catalog",
    label: "Transmitter catalog version",
    hint: "Frozen version string. Leakage is bounded by injection, not by hope.",
  },
  {
    id: "gkm",
    label: "G_km version per site",
    hint: "Multipath phase-error model identity.",
  },
  {
    id: "tauM",
    label: "Analysis B half-width M (in τ_c)",
    hint: "Grid contains {0, ±τ_c, ±τ_iono, ±τ_trop} and ±M τ_c.",
    placeholder: "4",
  },
  {
    id: "slideCount",
    label: "Time-slide count and joint FAR",
    hint: "Slides run on the post-subtraction residual streams.",
  },
  {
    id: "holdout",
    label: "Hold-out window",
    hint: "Post-window data, excluded from the detection statistic, must show the morphology on its own.",
  },
  {
    id: "iqDepth",
    label: "IQ ring-buffer depth (s)",
    hint: "Paper example is 300 s. Trigger dump is simultaneous across nodes.",
    placeholder: "300",
  },
  {
    id: "transfer",
    label: "Time transfer per baseline class",
    hint: "10 km: common-view GNSS. Sub-km: White Rabbit or two-way optical. State σ_sync.",
  },
  {
    id: "openPlan",
    label: "Open injection plan",
    hint: "Amplitudes, lags, and chain class. Include isotropic (Chain C only) and direction-differential (Chain S).",
  },
  {
    id: "blindCount",
    label: "Blind-injection count and distributions",
    hint: "The mechanism is registered. The seed is not.",
  },
  {
    id: "blindHolder",
    label: "Injection holder",
    hint: "A person who is not on the analysis team. Identity only.",
  },
  {
    id: "switch2tol",
    label: "Switch 2 relative tolerance",
    hint: "On φ₁/φ₂, classification product, radians or cycles. Example: 0.05.",
    placeholder: "0.05",
  },
  {
    id: "clockFloorRad",
    label: "Common-clock non-clock floor (rad)",
    hint: "Measured. Chain C's bound cannot be quoted tighter than this. Leave blank until the run exists.",
  },
  {
    id: "biasHash",
    label: "L1/L5 inter-channel bias file hash",
    hint: "From the common-clock run. The phase-offset-class confound for Switch 2.",
  },
];

export type StepDef = {
  id: string;
  section: string;
  title: string;
  image: string;
  imageAlt: string;
  caption: string;
  paragraphs: string[];
};

export const STEPS: StepDef[] = [
  {
    id: "hypotheses",
    section: "§1",
    title: "Name the two hypotheses",
    image: ART.chainS,
    imageAlt: "Night sky with two satellite glints and a survey tripod, standing in for a sky gradient.",
    caption: "H_S lives on direction. H_C does not. A null on one chain does not constrain the other.",
    paragraphs: [
      "H_S is a direction-dependent anomalous phase — a sky gradient. Chain S, the between-satellite single difference, cancels isotropic site-common phase by construction. A null on Chain S does not touch H_C.",
      "H_C is an isotropic common phase, identical at every antenna regardless of which satellite is tracked. Only Chain C keeps receiver-common phase. It inherits the receiver clock. The title hypothesis lives on the harder chain.",
      "The array is a phase microscope pointed at zero. This program tests no predicted amplitude. A null is the expected result, and the bound is the product.",
    ],
  },
  {
    id: "path",
    section: "§4.0",
    title: "From carrier to estimator",
    image: ART.field,
    imageAlt: "A field kit: handset, antenna cable, and hard hat on a flight case at dusk.",
    caption: "The phone keeps the book. The node tracks the carrier. Do not swap them.",
    paragraphs: [
      "Raw wideband IQ stays in a ring buffer. Tracking loops dump prompt-correlator I/Q at f_d. Carrier phase is atan2(Q, I) on that dump.",
      "Chain S is formed per node, then IGS satellite-clock correction is applied per node before any inter-node comparison. Analysis A consumes those post-IGS single-difference residuals. The double difference is a consistency cross-check, not the estimator input.",
      "Chain C is the same-satellite inter-node difference. The satellite clock cancels. The receiver clock does not. Below the GPSDO steering bandwidth the nodes are one clock, and those frequencies are excluded on both chains.",
    ],
  },
  {
    id: "nodes",
    section: "§3",
    title: "Put the array on the page",
    image: ART.hero,
    imageAlt: "Two choke-ring antennas and a field rack under a desert night sky.",
    caption: "DSLV-ZPDI nodes. Two front ends are the minimum that makes a pair.",
    paragraphs: [
      "Each node is a GNSS-disciplined oscillator, an SDR, and a surveyed antenna. Record the installed unit's identity. Catalog ADEV is not accepted where the paper says the measured curve is load-bearing.",
      "A device fix from this handset is a real GNSS solution if the radio returns one. It is not a carrier-phase residual, and it is not a substitute for a geodetic monument. You can type a surveyed coordinate instead. Empty stays empty.",
    ],
  },
  {
    id: "prereg",
    section: "§6",
    title: "Write the registry before the run",
    image: ART.null,
    imageAlt: "A dark optical table with a straight null fringe.",
    caption: "Frozen means frozen. The analysis of record is not tuned on the science data.",
    paragraphs: [
      "Every item below is a blank until you fill it from the real plan: survey hash, dump rate, block length, catalog version, slide count, holder identity. Nothing here is seeded from a simulator.",
      "Chain S and Chain C stay separate families. The resolution-limited baseline list is part of the registry, computed on the next step from the coordinates and f_d you actually entered.",
    ],
  },
  {
    id: "clock",
    section: "§4.4",
    title: "Split one clock",
    image: ART.clock,
    imageAlt: "One oscillator, a splitter, and two SDR front ends on a bench.",
    caption: "Common-clock Chain C has site phase and inter-channel bias, and no relative clock wander by construction.",
    paragraphs: [
      "One GPSDO output drives two complete front ends at one site, antennas a metre apart. That pair measures the non-clock floor. The independent-clock co-located pair measures site-common plus relative clock. Differencing the configurations isolates the clock term.",
      "If the common-clock pair does not sit on its predicted null, the campaign stops at Switch 3. No science claim. Chain C's bound is this measured floor — not the atmospheric RSS, whatever the RSS says.",
    ],
  },
  {
    id: "inject",
    section: "§4.4",
    title: "Prove the pipeline on both classes",
    image: ART.chainC,
    imageAlt: "Two co-located antennas under one even glow.",
    caption: "Isotropic injection must appear on Chain C and vanish on Chain S. The reverse pattern is H_S.",
    paragraphs: [
      "Open injections test the pipeline. Blind injections test the analysts. Log recovery only after you have actually run it. A sealed blind injection is logged as sealed — do not type an amplitude you are not supposed to know.",
      "A chain that fails its distinctive injection has no standing to report an excess. Off-injection must return to the null floor.",
    ],
  },
  {
    id: "resolution",
    section: "§4.3",
    title: "Mark the baselines that cannot see a lag",
    image: ART.chainS,
    imageAlt: "Sky gradient over the desert, the direction-differential chain.",
    caption: "At 1 kHz, a 10 km pair is resolution-limited for |τ| ≪ τ_c. That is arithmetic, not a mood.",
    paragraphs: [
      "The morphology test |τ| ≪ τ_c requires τ_c ≫ f_d⁻¹. This step lists every pair from the coordinates on the nodes. No coordinate, no baseline, no claim.",
      "Regional baselines still enter Analysis A. They do not get a spacelike sentence in the book.",
    ],
  },
  {
    id: "freeze",
    section: "§6",
    title: "Timestamp the registry",
    image: ART.null,
    imageAlt: "Null fringe on an optical table, the expected picture.",
    caption: "SHA-256 of the canonical registry. Amendments stay visible.",
    paragraphs: [
      "Freezing hashes the nodes, the pre-registration fields, and the budget rows you have marked. Science logs after this point are append-only.",
      "An amendment clears the lock, stores the previous digest, and stamps the reason. The book does not pretend the original registry is still the one you froze.",
    ],
  },
  {
    id: "analysis-a",
    section: "§4.2",
    title: "Enter Analysis A as measured",
    image: ART.hero,
    imageAlt: "The field array the residuals actually come from.",
    caption: "Type γ̂ from the node reduction. The Beta law is computed. The residual is not.",
    paragraphs: [
      "Calendar seconds are not independent. Use L_eff from the frozen block length, or type the γ̂ you measured and the L you are willing to defend.",
      "The large-L floor with L = 86400 is shown only as the paper's trap. It is not the program floor. Systematics sit above both.",
    ],
  },
  {
    id: "analysis-b",
    section: "§4.3",
    title: "Classify a lag you actually saw",
    image: ART.chainS,
    imageAlt: "Two bearings in the sky — lag is a place, not a vibe.",
    caption: "The classifier quotes the pre-registered rules. It does not invent a peak.",
    paragraphs: [
      "Enter the peak lag from the reduction, the baseline, and the flags. The book applies the §4.3 reading: propagation, Switch 3, resolution limit, Chain S hardware, or a Chain C candidate that is still not signaling.",
      "A τ≈0 excess, even if every switch is passed, is common-mode noise. No information transfer is possible via a common-mode field.",
    ],
  },
  {
    id: "chromatic",
    section: "§7.2",
    title: "Switch 2 on the uncombined pair",
    image: ART.chromatic,
    imageAlt: "A short copper helix and a longer amber helix over a survey mark.",
    caption: "φ in radians or cycles. Delay class tracks f₁/f₂. Ionosphere tracks the inverse. Equal radians is a processing artifact.",
    paragraphs: [
      "The iono-free combination mixes the carriers and destroys the chromatic ratio. It is never the Switch 2 observable.",
      "Delay class, ratio ≈ 1.339: equal in seconds or metres. Ionospheric class, ratio ≈ 0.747: routes back to the null. Phase-offset class, ratio = 1: instrumental. Anything that matches none of them does not pass.",
    ],
  },
  {
    id: "switches",
    section: "§7",
    title: "Adjudicate the kill switches",
    image: ART.null,
    imageAlt: "The null fringe is a result, not a failure.",
    caption: "Instrument switches only. Appendix B does not gate the array.",
    paragraphs: [
      "A null on Chain S is not a null on Chain C. Switch 2 cannot fire on a null. Switch 3 stops the campaign until the pipeline is repaired. Switch 6 is load-bearing on H_C.",
      "Record the call you are actually making. The book will not mark a switch passed because a field was left on its default.",
    ],
  },
  {
    id: "release",
    section: "§6",
    title: "Publish the book, null included",
    image: ART.field,
    imageAlt: "The handset that carries the record off the hill.",
    caption: "JSON for the archive. Markdown for a human. Both are the campaign you typed.",
    paragraphs: [
      "Raw IQ stays on the nodes. This export is the pre-registration, the measured floors, the injection log, and the adjudications. A null is a publishable pair of upper bounds.",
      "Chain S is bounded by troposphere and multipath under the rows you marked measured — catalog rows stay labeled catalog. Chain C is bounded by the common-clock floor, or it is not bounded.",
    ],
  },
];

export const SWITCHES: {
  n: number;
  title: string;
  blast: string;
  body: string;
}[] = [
  {
    n: 1,
    title: "Array residual",
    blast: "The hypothesis as tested by that chain. The array remains a disciplined SDR network.",
    body: "Analysis A consistent with the Beta or bootstrap null, FDR-controlled, separately for Chain S and Chain C. Analysis B's bootstrap-max consistent with the time-slide null. The |τ| ≪ τ_c class is claimed only on baselines with τ_c ≫ f_d⁻¹.",
  },
  {
    n: 2,
    title: "Chromaticity",
    blast: "The candidate, not the array. This switch cannot fire on a null.",
    body: "Uncombined L1 and L5. Delay class φ₁/φ₂ = f₁/f₂. Ionospheric class φ₁/φ₂ = f₂/f₁. Phase-offset class φ₁/φ₂ = 1. Only the delay class, inside the pre-registered tolerance, survives.",
  },
  {
    n: 3,
    title: "Pipeline non-recovery",
    blast: "The campaign, until the pipeline is repaired. No science claim.",
    body: "Open or blind injection not recovered, off-injection not back on the null floor, time-slide background disagrees with the bootstrap, or the common-clock pair misses its predicted null.",
  },
  {
    n: 4,
    title: "Möbius holonomy as physics",
    blast: "Appendix A as physics. Keep as bookkeeping if useful.",
    body: "A closed RF or fiber loop of controlled area and reversed chirality yields only standard Berry, Faraday, or Sagnac phase. No extra discrete π.",
  },
  {
    n: 5,
    title: "Gravitating plenum",
    blast: "Literal Dirac-sea ontology. The phase program never needed it.",
    body: "Already thrown by cosmology. Vacuum energy and a Planck-cutoff zero-point estimate do not load the carrier-phase bound.",
  },
  {
    n: 6,
    title: "Simultaneity convention",
    blast: "Any non-local reading of that dataset. Load-bearing on Chain C.",
    body: "If a |τ| ≪ τ_c excess moves under an independent time transfer — two-way optical, common-view versus all-in-view, or a second constellation — it is a clock-ensemble artifact.",
  },
];
