import { createFileRoute } from "@tanstack/react-router";
import { useState } from "react";
import { Field, NeedCampaign, Plate, Readout, Shell, Tag } from "@/components/chrome";
import {
  clockReady,
  nodesReady,
  preregComplete,
  useActive,
  useBook,
  type NodeRec,
} from "@/lib/book";
import { pairsOf } from "@/lib/metrology/report";
import { formatBaseline, formatRad, formatSeconds, sci } from "@/lib/metrology/format";
import {
  F_L1_HZ,
  betaNull,
  chromatic,
  clockIsolation,
  lEff,
  morphology,
  num,
  sigmaPhiRad,
  type ChainId,
} from "@/lib/metrology/physics";
import { PREREG, STEPS } from "@/lib/metrology/protocol";

export const Route = createFileRoute("/walk")({ component: WalkPage });

function WalkPage() {
  return (
    <Shell>
      <WalkBody />
    </Shell>
  );
}

function gate(stepId: string, c: NonNullable<ReturnType<typeof useActive>>): string | null {
  if (stepId === "hypotheses" || stepId === "path" || stepId === "resolution") {
    return c.acked.includes(stepId) ? null : "Acknowledge the step before leaving it.";
  }
  if (stepId === "nodes") return nodesReady(c) ? null : "Two nodes, each with a name, GPSDO identity, σ_y, and f_loop.";
  if (stepId === "prereg") return preregComplete(c) ? null : "The registry fields above the clock floor are still blank.";
  if (stepId === "clock") return clockReady(c) ? null : "Enter the measured non-clock floor and the bias-file hash.";
  if (stepId === "inject") {
    return c.logs.some((l) => l.kind === "injection") ? null : "Log an injection — recovered, failed, or still sealed.";
  }
  if (stepId === "freeze") return c.frozen ? null : "Freeze the registry before science entries.";
  if (stepId === "analysis-a" || stepId === "analysis-b" || stepId === "chromatic" || stepId === "switches") {
    if (!c.frozen) return "Freeze first. Science entries wait on the hash.";
    return c.acked.includes(stepId) ? null : "Acknowledge the step. An empty log is allowed. A silent skip is not.";
  }
  return null;
}

function WalkBody() {
  const c = useActive();
  const setStep = useBook((s) => s.setStep);
  const ack = useBook((s) => s.ack);
  if (!c) return <NeedCampaign />;
  const index = Math.max(0, STEPS.findIndex((s) => s.id === c.stepId));
  const step = STEPS[index]!;
  const reason = gate(step.id, c);

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between gap-3">
        <p className="kicker">
          Step {index + 1} / {STEPS.length} · {step.section}
        </p>
        <Tag tone={c.frozen ? "ok" : "steel"}>{c.frozen ? "Registry frozen" : "Registry open"}</Tag>
      </div>
      <div className="flex gap-1">
        {STEPS.map((s, i) => (
          <button
            key={s.id}
            type="button"
            aria-label={s.title}
            className={`h-1.5 flex-1 rounded-full ${i === index ? "bg-primary" : i < index ? "bg-accent" : "bg-border"}`}
            onClick={() => setStep(c.id, s.id)}
          />
        ))}
      </div>
      <Plate src={step.image} alt={step.imageAlt} caption={step.caption} />
      <div>
        <h1 className="text-2xl font-semibold">{step.title}</h1>
        <div className="mt-3 space-y-2 text-sm text-muted">
          {step.paragraphs.map((p) => (
            <p key={p}>{p}</p>
          ))}
        </div>
      </div>
      <StepPanel />
      <div className="flex gap-2">
        <button
          type="button"
          className="btn btn-ghost flex-1"
          disabled={index === 0}
          onClick={() => setStep(c.id, STEPS[index - 1]!.id)}
        >
          Back
        </button>
        <button
          type="button"
          className="btn btn-primary flex-1"
          disabled={index === STEPS.length - 1 || !!reason}
          onClick={() => {
            ack(c.id, step.id);
            setStep(c.id, STEPS[index + 1]!.id);
          }}
        >
          Next
        </button>
      </div>
      {reason ? <p className="text-sm text-warn">{reason}</p> : null}
    </div>
  );
}

function StepPanel() {
  const c = useActive();
  if (!c) return null;
  switch (c.stepId) {
    case "hypotheses":
    case "path":
    case "resolution":
    case "analysis-a":
    case "analysis-b":
    case "chromatic":
    case "switches":
      return <AckAndExtra />;
    case "nodes":
      return <Nodes />;
    case "prereg":
      return <Prereg />;
    case "clock":
      return <ClockStep />;
    case "inject":
      return <InjectStep />;
    case "freeze":
      return <FreezeStep />;
    case "release":
      return <ReleaseHint />;
    default:
      return null;
  }
}

function AckAndExtra() {
  const c = useActive()!;
  const ack = useBook((s) => s.ack);
  const on = c.acked.includes(c.stepId);
  return (
    <div className="space-y-4">
      {c.stepId === "resolution" ? <ResolutionList /> : null}
      {c.stepId === "analysis-a" ? <AnalysisA /> : null}
      {c.stepId === "analysis-b" ? <AnalysisB /> : null}
      {c.stepId === "chromatic" ? <ChromaticStep /> : null}
      {c.stepId === "switches" ? <SwitchStep /> : null}
      <label className="card flex items-start gap-3 p-4">
        <input
          type="checkbox"
          className="mt-1 h-5 w-5"
          checked={on}
          onChange={() => {
            if (!on) ack(c.id, c.stepId);
          }}
        />
        <span className="text-sm">
          I have read this step against the paper. Leaving it blank is not the same as a null result.
        </span>
      </label>
    </div>
  );
}

function Nodes() {
  const c = useActive()!;
  const addNode = useBook((s) => s.addNode);
  const updateNode = useBook((s) => s.updateNode);
  const removeNode = useBook((s) => s.removeNode);
  const [err, setErr] = useState("");

  function capture(node: NodeRec) {
    setErr("");
    if (!navigator.geolocation) {
      setErr("This browser has no geolocation. Type a surveyed coordinate.");
      return;
    }
    navigator.geolocation.getCurrentPosition(
      (pos) => {
        const ok = updateNode(c.id, node.id, {
          lat: pos.coords.latitude.toFixed(7),
          lon: pos.coords.longitude.toFixed(7),
          altM: pos.coords.altitude == null ? "" : pos.coords.altitude.toFixed(1),
          accuracyM: pos.coords.accuracy.toFixed(1),
          fixSource: "device",
          fixAt: new Date(pos.timestamp).toISOString(),
        });
        if (!ok) setErr("The registry is frozen. Amend it before editing nodes.");
      },
      (e) => setErr(e.message || "Location denied. Nothing was invented."),
      { enableHighAccuracy: true, timeout: 20000, maximumAge: 0 },
    );
  }

  return (
    <div className="space-y-3">
      {c.frozen ? <p className="text-sm text-warn">Nodes are locked with the registry.</p> : null}
      {c.nodes.map((n, i) => {
        const sy = num(n.sigmaY);
        const phi = sy == null ? null : sigmaPhiRad(F_L1_HZ, 1, sy);
        return (
          <fieldset key={n.id} className="card space-y-3 p-4">
            <legend className="px-1 text-sm font-semibold">Node {i + 1}</legend>
            <div className="grid gap-3 sm:grid-cols-2">
              <Field label="Name">
                <input className="field" disabled={!!c.frozen} value={n.name} onChange={(e) => updateNode(c.id, n.id, { name: e.target.value })} />
              </Field>
              <Field label="GPSDO identity">
                <input className="field" disabled={!!c.frozen} value={n.gpsdo} onChange={(e) => updateNode(c.id, n.id, { gpsdo: e.target.value })} placeholder="LBE-1421 serial" />
              </Field>
              <Field label="Measured σ_y at 1 s" hint="Unitless Allan deviation. 1e-12 is the paper's mid-grade example, not your unit.">
                <input className="field font-mono" disabled={!!c.frozen} value={n.sigmaY} onChange={(e) => updateNode(c.id, n.id, { sigmaY: e.target.value })} placeholder="1e-12" />
              </Field>
              <Field label="Steering loop f_loop (Hz)">
                <input className="field font-mono" disabled={!!c.frozen} value={n.fLoopHz} onChange={(e) => updateNode(c.id, n.id, { fLoopHz: e.target.value })} placeholder="0.01" />
              </Field>
            </div>
            <Field label="Antenna">
              <input className="field" disabled={!!c.frozen} value={n.antenna} onChange={(e) => updateNode(c.id, n.id, { antenna: e.target.value })} />
            </Field>
            <div className="grid gap-3 sm:grid-cols-2">
              <Field label="Latitude">
                <input className="field font-mono" disabled={!!c.frozen} value={n.lat} onChange={(e) => updateNode(c.id, n.id, { lat: e.target.value, fixSource: "surveyed" })} />
              </Field>
              <Field label="Longitude">
                <input className="field font-mono" disabled={!!c.frozen} value={n.lon} onChange={(e) => updateNode(c.id, n.id, { lon: e.target.value, fixSource: "surveyed" })} />
              </Field>
            </div>
            <Readout label="σ_φ at L1, τ = 1 s" value={formatRad(phi)} hint="2π f τ σ_y. Chain S cancels this clock. Chain C does not." />
            <div className="flex gap-2">
              <button type="button" className="btn btn-ghost flex-1" disabled={!!c.frozen} onClick={() => capture(n)}>
                Capture a device fix
              </button>
              <button type="button" className="btn btn-hot" disabled={!!c.frozen} onClick={() => removeNode(c.id, n.id)}>
                Remove
              </button>
            </div>
            {n.fixSource ? (
              <p className="text-xs text-muted">
                {n.fixSource} · accuracy {n.accuracyM || "—"} m · {n.fixAt || "time unset"}
              </p>
            ) : null}
          </fieldset>
        );
      })}
      {err ? <p className="text-sm text-hot">{err}</p> : null}
      <button type="button" className="btn btn-primary w-full" disabled={!!c.frozen} onClick={() => addNode(c.id)}>
        Add a node
      </button>
    </div>
  );
}

function Prereg() {
  const c = useActive()!;
  const setField = useBook((s) => s.setField);
  const [locked, setLocked] = useState(false);
  return (
    <div className="space-y-3">
      {PREREG.filter((f) => f.id !== "clockFloorRad" && f.id !== "biasHash").map((f) => {
        const long = ["allanNote", "transfer", "openPlan", "holdout", "slideCount", "gkm", "fdr"].includes(f.id);
        return (
          <Field key={f.id} label={f.label} hint={f.hint}>
            {long ? (
              <textarea
                className="field textarea"
                disabled={!!c.frozen}
                placeholder={f.placeholder}
                value={c.fields[f.id] ?? ""}
                onChange={(e) => {
                  const ok = setField(c.id, f.id, e.target.value);
                  setLocked(!ok);
                }}
              />
            ) : (
              <input
                className="field"
                disabled={!!c.frozen}
                placeholder={f.placeholder}
                value={c.fields[f.id] ?? ""}
                onChange={(e) => {
                  const ok = setField(c.id, f.id, e.target.value);
                  setLocked(!ok);
                }}
              />
            )}
          </Field>
        );
      })}
      {locked ? <p className="text-sm text-warn">Frozen. Amend the registry to edit these fields.</p> : null}
    </div>
  );
}

function ClockStep() {
  const c = useActive()!;
  const setField = useBook((s) => s.setField);
  const addLog = useBook((s) => s.addLog);
  const common = num(c.fields.clockFloorRad);
  const indep = num(c.fields.indepClockRms ?? "");
  const iso = common != null && indep != null ? clockIsolation(common, indep) : null;
  const [note, setNote] = useState("");
  const [msg, setMsg] = useState("");

  return (
    <div className="space-y-3">
      <Field label="Common-clock residual RMS (rad)" hint="The non-clock floor. This number sets the Chain C bound.">
        <input
          className="field font-mono"
          disabled={!!c.frozen}
          value={c.fields.clockFloorRad ?? ""}
          onChange={(e) => setField(c.id, "clockFloorRad", e.target.value)}
          placeholder="measured"
        />
      </Field>
      <Field label="Independent-clock co-located RMS (rad)" hint="Site-common plus relative clock. Not a second hypothesis.">
        <input
          className="field font-mono"
          disabled={!!c.frozen}
          value={c.fields.indepClockRms ?? ""}
          onChange={(e) => setField(c.id, "indepClockRms", e.target.value)}
        />
      </Field>
      <Field label="Inter-channel bias file hash">
        <input
          className="field font-mono"
          disabled={!!c.frozen}
          value={c.fields.biasHash ?? ""}
          onChange={(e) => setField(c.id, "biasHash", e.target.value)}
        />
      </Field>
      <div className="grid gap-3 sm:grid-cols-2">
        <Readout
          label="Isolated clock term"
          value={iso == null ? "—" : formatRad(iso)}
          hint="√(σ²_indep − σ²_common). Blank if the common-clock run is noisier — that fails the decomposition and routes to Switch 3."
        />
        <Readout label="Chain C bound" value={common == null ? "unbounded" : formatRad(common)} hint="No tighter number is allowed." />
      </div>
      <Field label="What the run actually did">
        <textarea className="field textarea" value={note} onChange={(e) => setNote(e.target.value)} placeholder="Predicted-null pass or fail, in your words." />
      </Field>
      <button
        type="button"
        className="btn btn-primary w-full"
        onClick={() => {
          if (common == null) {
            setMsg("No floor entered. The log was not written.");
            return;
          }
          addLog(c.id, {
            kind: "calibration",
            chain: "C",
            title: iso == null ? "Common-clock run — decomposition failed" : "Common-clock calibration",
            body: `${note || "No narrative."} Floor ${common} rad. Independent ${indep ?? "∅"}. Isolation ${iso ?? "failed"}. Bias ${c.fields.biasHash || "∅"}.`,
          });
          setNote("");
          setMsg("Calibration appended to the book.");
        }}
      >
        Append the calibration
      </button>
      {msg ? <p className="text-sm text-muted">{msg}</p> : null}
    </div>
  );
}

function InjectStep() {
  const c = useActive()!;
  const addLog = useBook((s) => s.addLog);
  const [sealed, setSealed] = useState(false);
  const [chain, setChain] = useState<ChainId>("C");
  const [klass, setKlass] = useState("H_C isotropic");
  const [amp, setAmp] = useState("");
  const [lag, setLag] = useState("");
  const [recovered, setRecovered] = useState("recovered");
  const [msg, setMsg] = useState("");

  return (
    <div className="card space-y-3 p-4">
      <label className="flex items-center gap-2 text-sm">
        <input type="checkbox" className="h-5 w-5" checked={sealed} onChange={(e) => setSealed(e.target.checked)} />
        Still sealed — do not type the amplitude
      </label>
      <Field label="Chain class">
        <select className="select" value={klass} onChange={(e) => setKlass(e.target.value)}>
          <option>H_C isotropic</option>
          <option>H_S direction-differential</option>
        </select>
      </Field>
      <Field label="Where it was recovered">
        <select className="select" value={chain} onChange={(e) => setChain(e.target.value as ChainId)}>
          <option value="C">Chain C</option>
          <option value="S">Chain S</option>
        </select>
      </Field>
      {!sealed ? (
        <div className="grid gap-3 sm:grid-cols-2">
          <Field label="Amplitude (rad)">
            <input className="field font-mono" value={amp} onChange={(e) => setAmp(e.target.value)} />
          </Field>
          <Field label="Lag (s)">
            <input className="field font-mono" value={lag} onChange={(e) => setLag(e.target.value)} />
          </Field>
        </div>
      ) : null}
      <Field label="Outcome">
        <select className="select" value={recovered} onChange={(e) => setRecovered(e.target.value)}>
          <option value="recovered">Recovered inside tolerance</option>
          <option value="missed">Not recovered — Switch 3</option>
          <option value="sealed">Sealed, not yet opened</option>
        </select>
      </Field>
      <button
        type="button"
        className="btn btn-primary w-full"
        onClick={() => {
          addLog(c.id, {
            kind: "injection",
            chain,
            title: sealed ? `Blind injection sealed (${klass})` : `Injection ${recovered} (${klass})`,
            body: sealed
              ? "Seed not recorded. Holder and count live in the registry, not here."
              : `Amplitude ${amp || "∅"} rad. Lag ${lag || "∅"} s. Outcome ${recovered}. Recovered on Chain ${chain}.`,
          });
          setMsg("Injection appended.");
          setAmp("");
          setLag("");
        }}
      >
        Append injection
      </button>
      {msg ? <p className="text-sm text-muted">{msg}</p> : null}
    </div>
  );
}

function ResolutionList() {
  const c = useActive()!;
  const pairs = pairsOf(c);
  const fd = num(c.fields.fdHz);
  if (!pairs.length) return <p className="text-sm text-warn">No pairs yet. Add two nodes.</p>;
  return (
    <ul className="space-y-2">
      {pairs.map((p) => (
        <li key={p.a + p.b} className="card p-3 text-sm">
          <div className="font-semibold">
            {p.a} — {p.b}
          </div>
          <p className="tabular mt-1 font-mono text-muted">
            {formatBaseline(p.baselineM)} · τ_c {formatSeconds(p.tauS)}
            {fd ? ` · δτ ${formatSeconds(1 / fd)}` : " · f_d unset"}
          </p>
          <p className="mt-1 text-muted">
            {p.baselineM == null
              ? "No coordinates. No lag claim."
              : p.resolutionLimited
                ? "Resolution-limited for |τ| ≪ τ_c. Analysis A only."
                : "Light time clears 10 dump samples. σ_sync still has to."}
          </p>
        </li>
      ))}
    </ul>
  );
}

function FreezeStep() {
  const c = useActive()!;
  const freeze = useBook((s) => s.freeze);
  const amend = useBook((s) => s.amend);
  const [reason, setReason] = useState("");
  const [msg, setMsg] = useState("");
  const ready = preregComplete(c) && nodesReady(c) && clockReady(c);
  return (
    <div className="card space-y-3 p-4">
      <ul className="space-y-1 text-sm">
        <Li ok={nodesReady(c)} text="Two identified nodes" />
        <Li ok={preregComplete(c)} text="Pre-registration fields filled" />
        <Li ok={clockReady(c)} text="Common-clock floor and bias hash" />
      </ul>
      {c.frozen ? (
        <>
          <p className="break-all font-mono text-xs text-primary">{c.frozen.sha256}</p>
          <p className="text-xs text-muted">Frozen {c.frozen.at}</p>
          <Field label="Amendment reason">
            <textarea className="field textarea" value={reason} onChange={(e) => setReason(e.target.value)} />
          </Field>
          <button
            type="button"
            className="btn btn-hot w-full"
            disabled={!reason.trim()}
            onClick={() => {
              amend(c.id, reason);
              setReason("");
              setMsg("Lock cleared. The previous digest stays in the book.");
            }}
          >
            Amend and unlock
          </button>
        </>
      ) : (
        <button
          type="button"
          className="btn btn-primary w-full"
          disabled={!ready}
          onClick={async () => {
            const digest = await freeze(c.id);
            setMsg(digest ? `Frozen ${digest.slice(0, 16)}…` : "Freeze refused. A required field is empty.");
          }}
        >
          Freeze and hash
        </button>
      )}
      {c.amendments.length > 0 ? (
        <ul className="space-y-1 text-xs text-warn">
          {c.amendments.map((a) => (
            <li key={a.at}>
              {a.at}: {a.reason}
            </li>
          ))}
        </ul>
      ) : null}
      {msg ? <p className="text-sm text-muted">{msg}</p> : null}
    </div>
  );
}

function Li({ ok, text }: { ok: boolean; text: string }) {
  return (
    <li className={ok ? "text-ok" : "text-muted"}>
      {ok ? "Ready" : "Open"} — {text}
    </li>
  );
}

function AnalysisA() {
  const c = useActive()!;
  const addLog = useBook((s) => s.addLog);
  const [chain, setChain] = useState<ChainId>("S");
  const [gamma, setGamma] = useState("");
  const [tDur, setTDur] = useState("");
  const [tau, setTau] = useState("");
  const [call, setCall] = useState("consistent-with-null");
  const [msg, setMsg] = useState("");
  const L = lEff(num(tDur) ?? NaN, num(tau) ?? NaN);
  const law = L != null ? betaNull(L) : null;
  const g = num(gamma);

  return (
    <div className="card space-y-3 p-4">
      {!c.frozen ? <p className="text-sm text-warn">You can draft the arithmetic. The log waits until the registry is frozen.</p> : null}
      {!c.logs.some((l) => l.kind === "injection" && l.title.includes("recovered")) ? (
        <p className="text-sm text-warn">No recovered injection is in the book. Switch 3 is live for any claim.</p>
      ) : null}
      <Field label="Chain">
        <select className="select" value={chain} onChange={(e) => setChain(e.target.value as ChainId)}>
          <option value="S">Chain S · H_S</option>
          <option value="C">Chain C · H_C</option>
        </select>
      </Field>
      <div className="grid gap-3 sm:grid-cols-3">
        <Field label="Measured γ̂">
          <input className="field font-mono" value={gamma} onChange={(e) => setGamma(e.target.value)} />
        </Field>
        <Field label="Duration T (s)">
          <input className="field font-mono" value={tDur} onChange={(e) => setTDur(e.target.value)} />
        </Field>
        <Field label="τ_corr (s)">
          <input className="field font-mono" value={tau} onChange={(e) => setTau(e.target.value)} />
        </Field>
      </div>
      <div className="grid gap-3 sm:grid-cols-3">
        <Readout label="L_eff" value={L == null ? "—" : sci(L, 4)} hint="T / τ_corr" />
        <Readout label="E[γ̂] null" value={law ? sci(law.eGamma) : "—"} hint="1/L_eff" />
        <Readout label="γ̂ / E[γ̂]" value={law && g != null ? sci(g / law.eGamma) : "—"} hint="Not a detection threshold." />
      </div>
      <Field label="Operator call">
        <select className="select" value={call} onChange={(e) => setCall(e.target.value)}>
          <option value="consistent-with-null">Consistent with the null</option>
          <option value="excess-hold">Excess — hold for switches</option>
          <option value="no-measurement">No measurement this session</option>
        </select>
      </Field>
      <button
        type="button"
        className="btn btn-primary w-full"
        disabled={!c.frozen}
        onClick={() => {
          addLog(c.id, {
            kind: "analysis-a",
            chain,
            title: `Analysis A · Chain ${chain} · ${call}`,
            body: `γ̂ ${gamma || "∅"}. T ${tDur || "∅"} s. τ_corr ${tau || "∅"} s. L_eff ${L ?? "∅"}. E[γ] ${law ? law.eGamma : "∅"}.`,
          });
          setMsg("Analysis A appended. The residual itself was not generated here.");
        }}
      >
        Append Analysis A
      </button>
      {msg ? <p className="text-sm text-muted">{msg}</p> : null}
    </div>
  );
}

function AnalysisB() {
  const c = useActive()!;
  const addLog = useBook((s) => s.addLog);
  const pairs = pairsOf(c);
  const [pair, setPair] = useState(0);
  const [chain, setChain] = useState<ChainId>("S");
  const [tau, setTau] = useState("");
  const [sync, setSync] = useState("");
  const [flags, setFlags] = useState({
    colocated: false,
    alsoOnSeparated: false,
    catalogMultipath: false,
    vanishesWithIgs: false,
    commonClockExcludesHardware: false,
    delayClass: false,
  });
  const [msg, setMsg] = useState("");
  const chosen = pairs[pair];
  const fd = num(c.fields.fdHz);
  const result =
    chosen?.baselineM != null && fd != null && num(tau) != null && num(sync) != null
      ? morphology({
          tauS: num(tau)!,
          baselineM: chosen.baselineM,
          fdHz: fd,
          sigmaSyncS: num(sync)!,
          chain,
          ...flags,
        })
      : null;

  return (
    <div className="card space-y-3 p-4">
      {!pairs.length ? <p className="text-sm text-warn">No surveyed pair. Classification withheld.</p> : null}
      <Field label="Pair">
        <select className="select" value={pair} onChange={(e) => setPair(Number(e.target.value))}>
          {pairs.map((p, i) => (
            <option key={p.a + p.b} value={i}>
              {p.a} — {p.b} ({formatBaseline(p.baselineM)})
            </option>
          ))}
        </select>
      </Field>
      <Field label="Chain">
        <select className="select" value={chain} onChange={(e) => setChain(e.target.value as ChainId)}>
          <option value="S">Chain S</option>
          <option value="C">Chain C</option>
        </select>
      </Field>
      <div className="grid gap-3 sm:grid-cols-2">
        <Field label="Peak lag τ (s)">
          <input className="field font-mono" value={tau} onChange={(e) => setTau(e.target.value)} />
        </Field>
        <Field label="σ_sync (s)">
          <input className="field font-mono" value={sync} onChange={(e) => setSync(e.target.value)} />
        </Field>
      </div>
      <div className="grid gap-2 text-sm sm:grid-cols-2">
        {(
          [
            ["colocated", "Also on the co-located pair"],
            ["alsoOnSeparated", "Also on a separated pair"],
            ["catalogMultipath", "Matches catalogued multipath"],
            ["vanishesWithIgs", "Vanishes when IGS / iono applied"],
            ["commonClockExcludesHardware", "Common-clock run excluded hardware"],
            ["delayClass", "Switch 2 delay class already passed"],
          ] as const
        ).map(([key, label]) => (
          <label key={key} className="flex items-center gap-2">
            <input
              type="checkbox"
              className="h-5 w-5"
              checked={flags[key]}
              onChange={(e) => setFlags({ ...flags, [key]: e.target.checked })}
            />
            {label}
          </label>
        ))}
      </div>
      {result ? (
        <div className="rounded-md border border-border bg-elevated p-3">
          <Tag tone={result.code === "chain-c-candidate" ? "warn" : "sage"}>{result.code}</Tag>
          <h3 className="mt-1 font-semibold">{result.title}</h3>
          <p className="mt-1 text-sm text-muted">{result.detail}</p>
        </div>
      ) : (
        <p className="text-sm text-muted">Enter a surveyed pair, f_d in the registry, a lag, and σ_sync.</p>
      )}
      <button
        type="button"
        className="btn btn-primary w-full"
        disabled={!c.frozen || !result}
        onClick={() => {
          if (!result || !chosen) return;
          addLog(c.id, {
            kind: "analysis-b",
            chain,
            title: `Analysis B · ${result.code}`,
            body: `${chosen.a}—${chosen.b}. ${result.title}. ${result.detail}`,
          });
          setMsg("Lag classification appended.");
        }}
      >
        Append the classification
      </button>
      {msg ? <p className="text-sm text-muted">{msg}</p> : null}
    </div>
  );
}

function ChromaticStep() {
  const c = useActive()!;
  const addLog = useBook((s) => s.addLog);
  const [p1, setP1] = useState("");
  const [p2, setP2] = useState("");
  const [msg, setMsg] = useState("");
  const tol = num(c.fields.switch2tol) ?? 0.05;
  const hit = num(p1) != null && num(p2) != null ? chromatic(num(p1)!, num(p2)!, tol) : null;
  const label =
    hit?.klass === "delay"
      ? "Delay class — candidate may proceed"
      : hit?.klass === "iono"
        ? "Ionospheric class — back to the null"
        : hit?.klass === "offset"
          ? "Phase-offset class — instrumental"
          : hit
            ? "No class inside tolerance"
            : "—";
  return (
    <div className="card space-y-3 p-4">
      <p className="text-sm text-muted">Tolerance from the registry: {sci(tol)}. Uncombined radians or cycles.</p>
      <div className="grid gap-3 sm:grid-cols-2">
        <Field label="φ₁ (L1)">
          <input className="field font-mono" value={p1} onChange={(e) => setP1(e.target.value)} />
        </Field>
        <Field label="φ₂ (L5)">
          <input className="field font-mono" value={p2} onChange={(e) => setP2(e.target.value)} />
        </Field>
      </div>
      <Readout label="φ₁/φ₂" value={hit ? sci(hit.ratio, 4) : "—"} hint={label} />
      <button
        type="button"
        className="btn btn-primary w-full"
        disabled={!c.frozen || !hit}
        onClick={() => {
          if (!hit) return;
          addLog(c.id, {
            kind: "chromatic",
            title: `Switch 2 · ${hit.klass}`,
            body: `φ1 ${p1}, φ2 ${p2}, ratio ${hit.ratio}, nearest ${hit.klass} (target ${hit.target}), relative error ${hit.relErr}. Tolerance ${tol}.`,
          });
          setMsg("Chromatic call appended.");
        }}
      >
        Append Switch 2
      </button>
      {msg ? <p className="text-sm text-muted">{msg}</p> : null}
    </div>
  );
}

function SwitchStep() {
  const c = useActive()!;
  const addLog = useBook((s) => s.addLog);
  const [n, setN] = useState("1");
  const [status, setStatus] = useState("null-holds");
  const [note, setNote] = useState("");
  const [msg, setMsg] = useState("");
  return (
    <div className="card space-y-3 p-4">
      <Field label="Switch">
        <select className="select" value={n} onChange={(e) => setN(e.target.value)}>
          <option value="1">1 Array residual</option>
          <option value="2">2 Chromaticity</option>
          <option value="3">3 Pipeline</option>
          <option value="4">4 Möbius holonomy</option>
          <option value="5">5 Gravitating plenum</option>
          <option value="6">6 Simultaneity</option>
        </select>
      </Field>
      <Field label="Call">
        <select className="select" value={status} onChange={(e) => setStatus(e.target.value)}>
          <option value="null-holds">Null holds</option>
          <option value="fired">Fired — blast radius applies</option>
          <option value="candidate-passed">Candidate passed this switch</option>
          <option value="not-applicable">Not applicable on a null</option>
        </select>
      </Field>
      <Field label="Note">
        <textarea className="field textarea" value={note} onChange={(e) => setNote(e.target.value)} />
      </Field>
      <button
        type="button"
        className="btn btn-primary w-full"
        disabled={!c.frozen || (n === "2" && status === "fired" && !c.logs.some((l) => l.kind === "analysis-a" || l.kind === "analysis-b"))}
        onClick={() => {
          if (n === "2" && status === "candidate-passed" && !c.logs.some((l) => l.kind === "chromatic")) {
            setMsg("Switch 2 cannot pass without an uncombined L1/L5 entry.");
            return;
          }
          addLog(c.id, {
            kind: "switch",
            title: `Switch ${n} · ${status}`,
            body: note || "No note.",
          });
          setNote("");
          setMsg(`Switch ${n} recorded.`);
        }}
      >
        Record the switch
      </button>
      {msg ? <p className="text-sm text-muted">{msg}</p> : null}
    </div>
  );
}

function ReleaseHint() {
  return (
    <p className="text-sm text-muted">
      Export lives in the book. Take the JSON off the handset the way you take any other file. The
      nodes still hold the IQ.
    </p>
  );
}
