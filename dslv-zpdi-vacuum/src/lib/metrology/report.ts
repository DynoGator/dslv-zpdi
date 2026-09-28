import type { Campaign } from "@/lib/book";
import { rowRad } from "@/lib/book";
import { formatBaseline, formatRad, formatSeconds, sci } from "@/lib/metrology/format";
import {
  F_L1_HZ,
  baselineForLags,
  betaNull,
  haversineM,
  lightTimeS,
  num,
  rss,
  sigmaPhiRad,
} from "@/lib/metrology/physics";

export function pairsOf(c: Campaign) {
  const out: {
    a: string;
    b: string;
    baselineM: number | null;
    tauS: number | null;
    resolutionLimited: boolean | null;
  }[] = [];
  const fd = num(c.fields.fdHz);
  for (let i = 0; i < c.nodes.length; i++) {
    for (let j = i + 1; j < c.nodes.length; j++) {
      const A = c.nodes[i]!;
      const B = c.nodes[j]!;
      const la = num(A.lat);
      const loa = num(A.lon);
      const lb = num(B.lat);
      const lob = num(B.lon);
      const baselineM =
        la != null && loa != null && lb != null && lob != null
          ? haversineM({ lat: la, lon: loa }, { lat: lb, lon: lob })
          : null;
      const tauS = baselineM != null ? lightTimeS(baselineM) : null;
      const resolutionLimited =
        tauS != null && fd != null && fd > 0 ? !(tauS > 10 / fd) : null;
      out.push({
        a: A.name || "unnamed",
        b: B.name || "unnamed",
        baselineM,
        tauS,
        resolutionLimited,
      });
    }
  }
  return out;
}

export function chainSRss(c: Campaign): { measured: number | null; catalog: number | null; mixed: number | null } {
  const measured: number[] = [];
  const catalog: number[] = [];
  const mixed: number[] = [];
  for (const row of c.budget) {
    if (!row.rss) continue;
    if (row.name.startsWith("Multipath")) continue;
    const rad = rowRad(row);
    if (rad == null) continue;
    mixed.push(rad);
    if (row.basis === "measured") measured.push(rad);
    else catalog.push(rad);
  }
  const mp = c.budget.filter((r) => r.name.startsWith("Multipath") && r.rss);
  for (const row of mp) {
    const rad = rowRad(row);
    if (rad == null) continue;
    mixed.push(rad);
    if (row.basis === "measured") measured.push(rad);
    else catalog.push(rad);
  }
  return {
    measured: measured.length ? rss(measured) : null,
    catalog: catalog.length ? rss(catalog) : null,
    mixed: mixed.length ? rss(mixed) : null,
  };
}

export function campaignMarkdown(c: Campaign): string {
  const lines: string[] = [];
  lines.push(`# ${c.name}`);
  lines.push("");
  lines.push(`DSLV-ZPDI — Probing the Vacuum Structure. White paper Rev 3.4.`);
  lines.push(`Operator: ${c.operator || "—"}`);
  lines.push(`Site: ${c.site || "—"}`);
  lines.push(`Opened: ${c.createdAt}`);
  lines.push(
    c.frozen
      ? `Registry: FROZEN ${c.frozen.at}`
      : c.amendments.length
        ? `Registry: OPEN — amended ${c.amendments.length} time(s) after a prior freeze`
        : `Registry: OPEN — not frozen`,
  );
  if (c.frozen) lines.push(`SHA-256: ${c.frozen.sha256}`);
  for (const a of c.amendments) {
    lines.push(`Amendment ${a.at}: ${a.reason} (previous ${a.previousSha})`);
  }
  lines.push("");
  lines.push("This file contains operator entries and closed-form reductions of those entries. It contains no simulated residuals.");
  lines.push("");
  lines.push("## Nodes");
  if (!c.nodes.length) lines.push("None recorded.");
  for (const n of c.nodes) {
    const sy = num(n.sigmaY);
    const phi = sy != null ? sigmaPhiRad(F_L1_HZ, 1, sy) : null;
    lines.push(
      `- ${n.name || "unnamed"} · GPSDO ${n.gpsdo || "—"} · σ_y(1 s)=${n.sigmaY || "—"} · σ_φ(L1, 1 s)=${formatRad(phi)} · f_loop=${n.fLoopHz || "—"} Hz · antenna ${n.antenna || "—"}`,
    );
    if (n.lat && n.lon) {
      lines.push(
        `  - fix ${n.lat}, ${n.lon} alt ${n.altM || "—"} m · ${n.fixSource || "unspecified"} · ${n.fixAt || ""} · accuracy ${n.accuracyM || "—"} m`,
      );
    } else {
      lines.push("  - no coordinates");
    }
  }
  lines.push("");
  lines.push("## Pairs");
  const fd = num(c.fields.fdHz);
  lines.push(fd ? `f_d = ${fd} Hz · δτ = ${formatSeconds(1 / fd)} · baselines with τ_c ≤ 10 δτ are resolution-limited.` : "f_d not registered. Resolution flags withheld.");
  for (const p of pairsOf(c)) {
    const flag =
      p.resolutionLimited == null ? "baseline unknown" : p.resolutionLimited ? "RESOLUTION-LIMITED for |τ|≪τ_c" : "lag test admissible if σ_sync≪τ_c";
    lines.push(`- ${p.a} — ${p.b}: ${formatBaseline(p.baselineM)} · τ_c ${formatSeconds(p.tauS)} · ${flag}`);
  }
  if (c.nodes.length < 2) lines.push("Fewer than two nodes.");
  lines.push("");
  lines.push("## Reference distances at this f_d");
  if (fd && fd > 0) {
    for (const n of [1, 10]) {
      lines.push(`- τ_c = ${n} δτ → ${formatBaseline(baselineForLags(fd, n))}`);
    }
  }
  lines.push("");
  lines.push("## Pre-registration");
  for (const [k, v] of Object.entries(c.fields)) {
    lines.push(`- ${k}: ${v.trim() ? v : "∅"}`);
  }
  lines.push("");
  lines.push("## Chain bounds");
  const floor = num(c.fields.clockFloorRad);
  lines.push(
    floor == null
      ? "Chain C (H_C): unbounded — common-clock floor not entered."
      : `Chain C (H_C): upper bound set by the measured common-clock floor ${formatRad(floor)}. Do not quote tighter.`,
  );
  const span = chainSRss(c);
  lines.push(
    `Chain S RSS of rows marked included: mixed ${formatRad(span.mixed)} · measured-only ${formatRad(span.measured)} · catalog-only ${formatRad(span.catalog)}.`,
  );
  lines.push("Catalog rows are the Rev 3.4 worked example, not this campaign's measurement.");
  lines.push("");
  lines.push("## Budget rows");
  for (const row of c.budget) {
    lines.push(
      `- [${row.basis}] ${row.name}: ${row.value} ${row.kind} → ${formatRad(rowRad(row))} · RSS ${row.rss ? "in" : "out"} · ${row.note}`,
    );
  }
  lines.push("");
  lines.push("## Log");
  if (!c.logs.length) lines.push("No entries.");
  for (const log of c.logs) {
    lines.push(`- ${log.at} · ${log.kind}${log.chain ? " · Chain " + log.chain : ""} · ${log.title}`);
    lines.push(`  ${log.body}`);
  }
  const L = num(c.fields.windowS);
  if (L && L > 1) {
    const b = betaNull(L);
    if (b) {
      lines.push("");
      lines.push("## Analytic null at the registered window count (not a measurement)");
      lines.push(`If someone wrongly treated each ${c.fields.windowS} s window as independent, that is a different number from L_eff.`);
      lines.push(`Beta E[γ̂]=${sci(b.eGamma)} at L=${c.fields.windowS} only if that L is the effective count.`);
    }
  }
  lines.push("");
  lines.push("A null is the expected result.");
  return lines.join("\n");
}

export function download(filename: string, text: string, type: string) {
  const blob = new Blob([text], { type });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  a.click();
  URL.revokeObjectURL(url);
}
