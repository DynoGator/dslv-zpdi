import { createFileRoute } from "@tanstack/react-router";
import { useMemo, useState } from "react";
import {
  CartesianGrid,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { Field, Readout, Shell, Tag } from "@/components/chrome";
import { rowRad, useActive, useBook } from "@/lib/book";
import { formatBaseline, formatRad, formatSeconds, sci } from "@/lib/metrology/format";
import {
  F_L1_HZ,
  F_L5_HZ,
  F_RATIO,
  baselineForLags,
  betaNull,
  chromatic,
  dumpPhaseSigma,
  haversineM,
  ionoPhaseRad,
  lEff,
  lightTimeS,
  num,
  nyquistHz,
  paperIdentityChecks,
  phaseToPathM,
  rss,
  sigmaPhiRad,
  weakPhase,
} from "@/lib/metrology/physics";

export const Route = createFileRoute("/bench")({ component: BenchPage });

function pathLabel(m: number | null): string {
  if (m == null || !Number.isFinite(m)) return "—";
  const mm = m * 1e3;
  if (Math.abs(mm) < 100) return `${mm.toFixed(2)} mm`;
  return `${m.toFixed(3)} m`;
}

function BenchPage() {
  return (
    <Shell>
      <div className="space-y-4">
        <header>
          <p className="kicker">Closed form</p>
          <h1 className="text-2xl font-semibold">Bench</h1>
          <p className="mt-1 text-sm text-muted">
            Every number on this page is an evaluation of a formula, or a row you typed. Placeholders
            are the Rev 3.4 worked example. They are not measurements, and they are not written into
            the book unless you are on the walk.
          </p>
        </header>
        <Adev />
        <Resolution />
        <Coherence />
        <Weak />
        <Chroma />
        <Iono />
        <Dump />
        <Guard />
        <BaselineTool />
        <BudgetTool />
        <Identity />
      </div>
    </Shell>
  );
}

function Adev() {
  const [sy, setSy] = useState("");
  const [tau, setTau] = useState("");
  const s = num(sy);
  const t = num(tau);
  const l1 = s != null && t != null ? sigmaPhiRad(F_L1_HZ, t, s) : null;
  const l5 = s != null && t != null ? sigmaPhiRad(F_L5_HZ, t, s) : null;
  return (
    <Tool title="Phase stability" section="§3.4" hint="σ_φ = 2π f τ σ_y. Quote the installed unit.">
      <div className="grid gap-3 sm:grid-cols-2">
        <Field label="σ_y(τ)">
          <input className="field font-mono" value={sy} placeholder="1e-12" onChange={(e) => setSy(e.target.value)} />
        </Field>
        <Field label="τ (s)">
          <input className="field font-mono" value={tau} placeholder="1" onChange={(e) => setTau(e.target.value)} />
        </Field>
      </div>
      <div className="grid gap-3 sm:grid-cols-2">
        <Readout label="L1" value={formatRad(l1)} />
        <Readout label="L5" value={formatRad(l5)} />
      </div>
    </Tool>
  );
}

function Resolution() {
  const [fd, setFd] = useState("");
  const [base, setBase] = useState("");
  const f = num(fd);
  const b = num(base);
  const rows =
    f != null && f > 0
      ? [1, 10].map((n) => ({ n, d: baselineForLags(f, n) }))
      : [];
  const tau = b != null ? lightTimeS(b) : null;
  const limited = tau != null && f != null && f > 0 ? !(tau > 10 / f) : null;
  return (
    <Tool title="Light time and lag resolution" section="§4.3">
      <div className="grid gap-3 sm:grid-cols-2">
        <Field label="f_d (Hz)">
          <input className="field font-mono" value={fd} placeholder="1000" onChange={(e) => setFd(e.target.value)} />
        </Field>
        <Field label="Baseline (m)">
          <input className="field font-mono" value={base} placeholder="10000" onChange={(e) => setBase(e.target.value)} />
        </Field>
      </div>
      <div className="grid gap-3 sm:grid-cols-3">
        <Readout label="δτ" value={f ? formatSeconds(1 / f) : "—"} />
        <Readout label="τ_c" value={formatSeconds(tau)} />
        <Readout label="|τ| ≪ τ_c" value={limited == null ? "—" : limited ? "Not claimable" : "Resolved"} />
      </div>
      <ul className="space-y-1 text-sm text-muted">
        {rows.map((r) => (
          <li key={r.n} className="tabular font-mono">
            τ_c = {r.n} δτ → {formatBaseline(r.d)}
          </li>
        ))}
      </ul>
    </Tool>
  );
}

function Coherence() {
  const [t, setT] = useState("");
  const [corr, setCorr] = useState("");
  const L = lEff(num(t) ?? NaN, num(corr) ?? NaN);
  const law = L != null && L > 1 ? betaNull(L) : null;
  const curve = useMemo(
    () =>
      [30, 100, 300, 1000, 3000, 10000, 86400].map((n) => {
        const b = betaNull(n)!;
        return { L: n, floor: b.eR, three: b.rMin3 };
      }),
    [],
  );
  return (
    <Tool
      title="Stationary coherence floor"
      section="§4.2"
      hint="The curve is E[r] ≈ √(π / 4L) under the complex-Gaussian null. It is not a spectrum."
    >
      <div className="grid gap-3 sm:grid-cols-2">
        <Field label="Record length T (s)">
          <input className="field font-mono" value={t} placeholder="86400" onChange={(e) => setT(e.target.value)} />
        </Field>
        <Field label="τ_corr (s)">
          <input className="field font-mono" value={corr} placeholder="288" onChange={(e) => setCorr(e.target.value)} />
        </Field>
      </div>
      <div className="grid gap-3 sm:grid-cols-3">
        <Readout label="L_eff" value={L == null ? "—" : sci(L, 4)} />
        <Readout label="E[γ̂]" value={law ? sci(law.eGamma) : "—"} />
        <Readout label="r_min κ=3" value={law ? sci(law.rMin3) : "—"} hint="Large-L magnitude check. The bootstrap decides." />
      </div>
      <div className="h-48 w-full">
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={curve}>
            <CartesianGrid stroke="var(--color-border)" />
            <XAxis dataKey="L" type="number" scale="log" domain={["auto", "auto"]} stroke="var(--color-muted)" tick={{ fill: "var(--color-muted)", fontSize: 11 }} />
            <YAxis scale="log" domain={["auto", "auto"]} stroke="var(--color-muted)" tick={{ fill: "var(--color-muted)", fontSize: 11 }} />
            <Tooltip
              contentStyle={{ background: "var(--color-card)", border: "1px solid var(--color-border)", color: "var(--color-foreground)" }}
              formatter={(v) => sci(typeof v === "number" ? v : Number(v))}
            />
            <Line type="monotone" dataKey="floor" name="E[r]" stroke="#8eb4ad" dot={false} strokeWidth={2} />
            <Line type="monotone" dataKey="three" name="r_min" stroke="#d4524a" dot={false} strokeWidth={2} />
          </LineChart>
        </ResponsiveContainer>
      </div>
      <p className="text-xs text-subtle">Sage: null expectation. Hot: κ=3 check. Log axes. Not campaign data.</p>
    </Tool>
  );
}

function Weak() {
  const [sig, setSig] = useState("");
  const [r, setR] = useState("");
  const w = num(sig) != null && num(r) != null ? weakPhase(num(sig)!, num(r)!) : null;
  return (
    <Tool title="Weak common phase" section="§5" hint="The paper reports φ ≈ σ √r. Exact inversion is beside it.">
      <div className="grid gap-3 sm:grid-cols-2">
        <Field label="σ_φ (rad)">
          <input className="field font-mono" value={sig} placeholder="0.3" onChange={(e) => setSig(e.target.value)} />
        </Field>
        <Field label="r">
          <input className="field font-mono" value={r} placeholder="0.0077" onChange={(e) => setR(e.target.value)} />
        </Field>
      </div>
      <div className="grid gap-3 sm:grid-cols-2">
        <Readout label="Paper map → L1 path" value={w ? pathLabel(phaseToPathM(w.approx, F_L1_HZ)) : "—"} hint={w ? formatRad(w.approx) : ""} />
        <Readout label="Exact inversion → L1 path" value={w ? pathLabel(phaseToPathM(w.exact, F_L1_HZ)) : "—"} hint={w ? formatRad(w.exact) : ""} />
      </div>
    </Tool>
  );
}

function Chroma() {
  const [a, setA] = useState("");
  const [b, setB] = useState("");
  const [tol, setTol] = useState("");
  const hit = num(a) != null && num(b) != null ? chromatic(num(a)!, num(b)!, num(tol) ?? 0.05) : null;
  return (
    <Tool title="Chromatic class" section="Switch 2" hint={`Targets: delay ${sci(F_RATIO, 4)}, ionosphere ${sci(1 / F_RATIO, 4)}, offset 1.`}>
      <div className="grid gap-3 sm:grid-cols-3">
        <Field label="φ₁">
          <input className="field font-mono" value={a} placeholder="1.339" onChange={(e) => setA(e.target.value)} />
        </Field>
        <Field label="φ₂">
          <input className="field font-mono" value={b} placeholder="1" onChange={(e) => setB(e.target.value)} />
        </Field>
        <Field label="Tolerance">
          <input className="field font-mono" value={tol} placeholder="0.05" onChange={(e) => setTol(e.target.value)} />
        </Field>
      </div>
      <Readout label="Class" value={hit ? hit.klass : "—"} hint={hit ? `ratio ${sci(hit.ratio, 4)} · relative error ${sci(hit.relErr)}` : "Radians or cycles, not metres."} />
    </Tool>
  );
}

function Iono() {
  const [tec, setTec] = useState("");
  const t = num(tec);
  return (
    <Tool title="Ionospheric carrier phase" section="§3" hint="0.1 TECU is the paper's optimistic single-frequency residual, not a forecast.">
      <Field label="TEC (TECU)">
        <input className="field font-mono" value={tec} placeholder="0.1" onChange={(e) => setTec(e.target.value)} />
      </Field>
      <div className="grid gap-3 sm:grid-cols-2">
        <Readout label="L1" value={t == null ? "—" : formatRad(ionoPhaseRad(t, F_L1_HZ))} />
        <Readout label="100 MHz" value={t == null ? "—" : formatRad(ionoPhaseRad(t, 100e6))} hint="Why the science band is L-band." />
      </div>
    </Tool>
  );
}

function Dump() {
  const [cn, setCn] = useState("");
  const [fd, setFd] = useState("");
  const s = num(cn) != null && num(fd) != null ? dumpPhaseSigma(num(cn)!, num(fd)!) : null;
  return (
    <Tool title="Per-dump phase" section="§4.0" hint="σ ≈ 1/√(2 C/N0 T), T = 1/f_d.">
      <div className="grid gap-3 sm:grid-cols-2">
        <Field label="C/N0 (dB-Hz)">
          <input className="field font-mono" value={cn} placeholder="45" onChange={(e) => setCn(e.target.value)} />
        </Field>
        <Field label="f_d (Hz)">
          <input className="field font-mono" value={fd} placeholder="1000" onChange={(e) => setFd(e.target.value)} />
        </Field>
      </div>
      <Readout label="σ_φ,dump" value={formatRad(s)} />
    </Tool>
  );
}

function Guard() {
  const [f, setF] = useState("");
  const [loop, setLoop] = useState("");
  const [fd, setFd] = useState("");
  const ff = num(f);
  const lp = num(loop);
  const d = num(fd);
  let call = "—";
  if (ff != null && lp != null && d != null) {
    if (ff < lp) call = "Excluded — inside the steering loop";
    else if (ff > nyquistHz(d)) call = "Above Nyquist of the dump";
    else call = "Inside the testable band";
  }
  return (
    <Tool title="Guard band" section="§3.4" hint="Below f_loop the GPSDOs are one clock. Mandatory on Chain C, conservative on Chain S.">
      <div className="grid gap-3 sm:grid-cols-3">
        <Field label="Fourier frequency (Hz)">
          <input className="field font-mono" value={f} onChange={(e) => setF(e.target.value)} />
        </Field>
        <Field label="f_loop (Hz)">
          <input className="field font-mono" value={loop} placeholder="0.01" onChange={(e) => setLoop(e.target.value)} />
        </Field>
        <Field label="f_d (Hz)">
          <input className="field font-mono" value={fd} placeholder="1000" onChange={(e) => setFd(e.target.value)} />
        </Field>
      </div>
      <Readout label="Band call" value={call} />
    </Tool>
  );
}

function BaselineTool() {
  const [a, setA] = useState("");
  const [b, setB] = useState("");
  const [c, setC] = useState("");
  const [d, setD] = useState("");
  const la = num(a);
  const loa = num(b);
  const lb = num(c);
  const lob = num(d);
  const m = la != null && loa != null && lb != null && lob != null ? haversineM({ lat: la, lon: loa }, { lat: lb, lon: lob }) : null;
  return (
    <Tool title="Sphere baseline" section="§4.3" hint="Mean-Earth haversine. Not a geodetic reduction. Empty coordinates stay empty.">
      <div className="grid gap-3 sm:grid-cols-2">
        <Field label="Lat A">
          <input className="field font-mono" value={a} onChange={(e) => setA(e.target.value)} />
        </Field>
        <Field label="Lon A">
          <input className="field font-mono" value={b} onChange={(e) => setB(e.target.value)} />
        </Field>
        <Field label="Lat B">
          <input className="field font-mono" value={c} onChange={(e) => setC(e.target.value)} />
        </Field>
        <Field label="Lon B">
          <input className="field font-mono" value={d} onChange={(e) => setD(e.target.value)} />
        </Field>
      </div>
      <div className="grid gap-3 sm:grid-cols-2">
        <Readout label="Baseline" value={formatBaseline(m)} />
        <Readout label="τ_c" value={formatSeconds(m == null ? null : lightTimeS(m))} />
      </div>
    </Tool>
  );
}

function BudgetTool() {
  const c = useActive();
  const update = useBook((s) => s.updateBudget);
  if (!c) {
    return (
      <Tool title="Campaign RSS" section="§5">
        <p className="text-sm text-muted">Open a campaign to edit budget rows. Catalog defaults appear with the record, labeled catalog.</p>
      </Tool>
    );
  }
  const lows: number[] = [];
  const highs: number[] = [];
  for (const row of c.budget) {
    if (row.name.startsWith("Multipath")) continue;
    if (!row.rss) continue;
    const rad = rowRad(row);
    if (rad == null) continue;
    lows.push(rad);
    highs.push(rad);
  }
  const mpLo = c.budget.find((r) => r.name.includes("low"));
  const mpHi = c.budget.find((r) => r.name.includes("high"));
  const lo = mpLo ? rowRad(mpLo) : null;
  const hi = mpHi ? rowRad(mpHi) : null;
  if (lo != null) lows.push(lo);
  if (hi != null) highs.push(hi);
  return (
    <Tool title="Chain S differential floor" section="§5" hint="RSS of included rows, with the low and high multipath cases shown as a span. Chain C is not this number.">
      <div className="grid gap-3 sm:grid-cols-2">
        <Readout label="RSS, multipath low" value={formatRad(lows.length ? rss(lows) : null)} />
        <Readout label="RSS, multipath high" value={formatRad(highs.length ? rss(highs) : null)} />
      </div>
      <ul className="space-y-3">
        {c.budget.map((row) => (
          <li key={row.id} className="rounded-md border border-border p-3">
            <div className="flex items-center justify-between gap-2">
              <span className="text-sm font-semibold">{row.name}</span>
              <Tag tone={row.basis === "measured" ? "ok" : "warn"}>{row.basis}</Tag>
            </div>
            <p className="mt-1 text-xs text-muted">{row.note}</p>
            <div className="mt-2 grid gap-2 sm:grid-cols-3">
              <input
                className="field font-mono"
                disabled={!!c.frozen}
                value={row.value}
                onChange={(e) => update(c.id, row.id, { value: e.target.value })}
              />
              <select
                className="select"
                disabled={!!c.frozen}
                value={row.basis}
                onChange={(e) => update(c.id, row.id, { basis: e.target.value as "catalog" | "measured" })}
              >
                <option value="catalog">catalog</option>
                <option value="measured">measured</option>
              </select>
              <label className="flex items-center gap-2 text-sm">
                <input
                  type="checkbox"
                  className="h-5 w-5"
                  disabled={!!c.frozen || row.name.startsWith("Multipath")}
                  checked={row.name.startsWith("Multipath") ? false : row.rss}
                  onChange={(e) => update(c.id, row.id, { rss: e.target.checked })}
                />
                In the shared RSS
              </label>
            </div>
            <p className="tabular mt-1 font-mono text-xs text-muted">{formatRad(rowRad(row))} at L1</p>
          </li>
        ))}
      </ul>
    </Tool>
  );
}

function Identity() {
  const rows = paperIdentityChecks();
  return (
    <Tool title="Identity against Rev 3.4" section="Self-check" hint="If a row fails, the app is wrong. Do not interpret it as a residual.">
      <ul className="space-y-2">
        {rows.map((r) => (
          <li key={r.id} className="flex items-start justify-between gap-3 border-b border-border pb-2 text-sm">
            <div>
              <div>{r.label}</div>
              <div className="font-mono text-xs text-muted">
                {r.got} · paper {r.expect}
              </div>
            </div>
            <Tag tone={r.pass ? "ok" : "hot"}>{r.pass ? "Hold" : "Fail"}</Tag>
          </li>
        ))}
      </ul>
    </Tool>
  );
}

function Tool({
  title,
  section,
  hint,
  children,
}: {
  title: string;
  section: string;
  hint?: string;
  children: React.ReactNode;
}) {
  return (
    <section className="card space-y-3 p-4">
      <div>
        <p className="kicker">{section}</p>
        <h2 className="text-lg font-semibold">{title}</h2>
        {hint ? <p className="mt-1 text-sm text-muted">{hint}</p> : null}
      </div>
      {children}
    </section>
  );
}
