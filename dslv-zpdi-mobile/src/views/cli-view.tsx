import { Panel, Pill, Row } from "@/components/panel";
import { Button } from "@/components/ui/button";
import {
  CLI_HELP,
  HIST_KEY,
  INSTALL_DEBIAN,
  INSTALL_TERMUX,
  PALETTE,
  loadScripts,
  runCli,
  runScript,
  saveScripts,
  scriptToShell,
  stepToLine,
  type CliContext,
  type ScriptDoc,
  type ScriptStep,
} from "@/lib/cli";
import { isNativeApk, nativeHost, nativeJson } from "@/lib/native";
import { useApp } from "@/lib/store";
import { PRESETS } from "@/lib/types";
import { GripVertical, Terminal } from "lucide-react";
import { useEffect, useMemo, useRef, useState } from "react";

type Tab = "shell" | "scripts" | "bridge";

function uid() {
  return Math.random().toString(36).slice(2, 8);
}

export function CliView() {
  const native = isNativeApk();
  const [tab, setTab] = useState<Tab>("shell");
  const [input, setInput] = useState("");
  const [lines, setLines] = useState<{ k: "in" | "out" | "err"; t: string }[]>([
    { k: "out", t: native ? "DSLV CLI · APK host. Type help." : "DSLV CLI · simulator. Sideload APK for Termux aliases." },
  ]);
  const [hist, setHist] = useState<string[]>(() => {
    try {
      return JSON.parse(localStorage.getItem(HIST_KEY) || "[]");
    } catch {
      return [];
    }
  });
  const [histI, setHistI] = useState(-1);
  const [scripts, setScripts] = useState<ScriptDoc[]>(loadScripts);
  const [current, setCurrent] = useState(0);
  const [running, setRunning] = useState(false);
  const [drag, setDrag] = useState<number | null>(null);
  const logRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  const get = useApp.getState;
  const ctx: CliContext = useMemo(
    () => ({
      sdr: () => get().sdr,
      usb: () => get().usb,
      tel: () => get().tel,
      pipe: () => get().pipe,
      applyPreset: (id) => get().applyPreset(id),
      setCenterHz: (hz) => get().setCenterHz(hz),
      setDemod: (d) => get().setDemod(d),
      setGain: (w, db) => get().setGain(w, db),
      setVolume: (v) => get().setVolume(v),
      setSquelch: (v) => get().setSquelch(v),
      toggleAudio: () => get().toggleAudio(),
      usbScan: () => get().usbScan(),
      usbOpen: (h) => get().usbOpen(h),
      usbClose: () => get().usbClose(),
      usbRx: (on) => get().usbRx(on),
      capture: () => get().capture(),
      setPipeline: (on) => get().setPipeline(on),
      sealPipeline: () => get().sealPipeline(),
      rotatePipeline: () => get().rotatePipeline(),
      scripts: () => scripts,
      saveScript: (doc) => {
        setScripts((prev) => {
          const next = [...prev.filter((s) => s.name !== doc.name), doc];
          saveScripts(next);
          return next;
        });
      },
      deleteScript: (name) => {
        setScripts((prev) => {
          const next = prev.filter((s) => s.name !== name);
          saveScripts(next);
          return next;
        });
      },
    }),
    [get, scripts],
  );

  useEffect(() => {
    logRef.current?.scrollTo(0, logRef.current.scrollHeight);
  }, [lines]);

  const push = (k: "in" | "out" | "err", t: string) => setLines((xs) => [...xs.slice(-200), { k, t }]);

  const exec = (raw: string) => {
    const line = raw.trim();
    if (!line) return;
    if (line.toLowerCase() === "clear") {
      setLines([]);
      setInput("");
      return;
    }
    push("in", `› ${line}`);
    const nextHist = [line, ...hist.filter((h) => h !== line)].slice(0, 40);
    setHist(nextHist);
    try {
      localStorage.setItem(HIST_KEY, JSON.stringify(nextHist));
    } catch {
      /* ignore */
    }
    setHistI(-1);
    const stripped = line.replace(/^dslv\s+/i, "").trim();
    const runMatch = stripped.match(/^script\s+run\s+(.+)$/i);
    if (runMatch) {
      const name = runMatch[1].replace(/^["']|["']$/g, "").trim();
      const doc = scripts.find((s) => s.name === name);
      if (!doc) {
        push("err", "no script " + name);
        return;
      }
      void runNamed(doc);
      return;
    }
    const r = runCli(line, ctx);
    const runName = r.data && typeof r.data === "object" && "run" in r.data ? String((r.data as { run?: string }).run ?? "") : "";
    if (runName) {
      const doc = scripts.find((s) => s.name === runName);
      if (!doc) {
        push("err", "no script " + runName);
        return;
      }
      void runNamed(doc);
      return;
    }
    push(r.ok ? "out" : "err", r.text);
  };

  const runNamed = async (doc: ScriptDoc) => {
    setRunning(true);
    push("out", `run ${doc.name} · ${doc.steps.length} steps`);
    const r = await runScript(doc, ctx, (s) => push("out", s));
    if (!r.ok) push("err", "aborted");
    setRunning(false);
  };

  const doc = scripts[current] ?? scripts[0];

  const patchSteps = (steps: ScriptStep[]) => {
    if (!doc) return;
    const next = scripts.map((s, i) => (i === current ? { ...s, steps } : s));
    setScripts(next);
    saveScripts(next);
  };

  const addStep = (op: string, arg?: string, ms?: number) => {
    if (!doc) {
      const name = `script-${scripts.length + 1}`;
      const created: ScriptDoc = { name, steps: [{ id: uid(), op, arg, ms }] };
      const next = [...scripts, created];
      setScripts(next);
      saveScripts(next);
      setCurrent(next.length - 1);
      return;
    }
    const step: ScriptStep = { id: uid(), op, arg, ms };
    patchSteps([...doc.steps, step]);
  };

  const move = (i: number, dir: -1 | 1) => {
    if (!doc) return;
    const j = i + dir;
    if (j < 0 || j >= doc.steps.length) return;
    const steps = [...doc.steps];
    const [x] = steps.splice(i, 1);
    steps.splice(j, 0, x!);
    patchSteps(steps);
  };

  const drop = (i: number) => {
    if (drag == null || drag === i || !doc) return;
    const steps = [...doc.steps];
    const [x] = steps.splice(drag, 1);
    steps.splice(i, 0, x!);
    patchSteps(steps);
    setDrag(null);
  };

  const termuxSt = native ? nativeJson<{ termux?: boolean; hint?: string }>(() => nativeHost()?.termux?.("status")) : null;

  return (
    <div className="flex flex-col gap-3">
      <Panel
        title="DSLV CLI"
        action={<Pill tone={native ? "ok" : "default"}>{native ? "HOST" : "SIM"}</Pill>}
      >
        <p className="mb-3 text-sm leading-relaxed text-muted">
          Same command surface as Termux and proot Debian. CLI agents call <span className="font-mono text-foreground">dslv</span> after
          aliases are installed. The app must be running.
        </p>
        <div className="grid grid-cols-3 gap-2">
          {(["shell", "scripts", "bridge"] as Tab[]).map((t) => (
            <Button key={t} size="sm" variant={tab === t ? "primary" : "outline"} onClick={() => setTab(t)}>
              {t === "shell" ? "Shell" : t === "scripts" ? "Scripts" : "Bridge"}
            </Button>
          ))}
        </div>
      </Panel>

      {tab === "shell" ? (
        <Panel title="Shell" action={<Terminal className="size-4 text-primary" />}>
          <div
            ref={logRef}
            className="mb-3 h-56 overflow-auto rounded-lg bg-background px-3 py-2 font-mono text-xs leading-relaxed shadow-[var(--shadow-border)]"
          >
            {lines.map((ln, i) => (
              <div
                key={i}
                className={ln.k === "in" ? "text-primary" : ln.k === "err" ? "text-danger" : "text-foreground whitespace-pre-wrap"}
              >
                {ln.t}
              </div>
            ))}
          </div>
          <div className="mb-2 flex flex-wrap gap-1.5">
            {["help", "status", "doctor", "sdr scan", "listen on", "listen off", "capture"].map((c) => (
              <Button key={c} size="sm" variant="ghost" onClick={() => exec(c)}>
                {c}
              </Button>
            ))}
          </div>
          <form
            className="flex gap-2"
            onSubmit={(e) => {
              e.preventDefault();
              exec(input);
              setInput("");
            }}
          >
            <input
              ref={inputRef}
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "ArrowUp") {
                  e.preventDefault();
                  const i = Math.min(hist.length - 1, histI + 1);
                  if (hist[i]) {
                    setHistI(i);
                    setInput(hist[i]);
                  }
                }
                if (e.key === "ArrowDown") {
                  e.preventDefault();
                  const i = histI - 1;
                  if (i < 0) {
                    setHistI(-1);
                    setInput("");
                  } else {
                    setHistI(i);
                    setInput(hist[i] ?? "");
                  }
                }
              }}
              placeholder="dslv status --json"
              autoCapitalize="none"
              autoCorrect="off"
              spellCheck={false}
              className="h-11 min-w-0 flex-1 rounded-md bg-elevated px-3 font-mono text-sm text-foreground shadow-[var(--shadow-border)] outline-none placeholder:text-subtle focus-visible:ring-2 focus-visible:ring-ring"
            />
            <Button type="submit" variant="primary">
              Run
            </Button>
          </form>
        </Panel>
      ) : null}

      {tab === "scripts" ? (
        <>
          <Panel title="Palette">
            <p className="mb-2 text-xs text-muted">Tap to append. Drag rows or use arrows to reorder.</p>
            <div className="flex flex-wrap gap-1.5">
              {PALETTE.map((p) => (
                <Button key={p.op + (p.arg ?? "")} size="sm" variant="outline" onClick={() => addStep(p.op, p.arg, p.ms)}>
                  {p.label}
                </Button>
              ))}
            </div>
          </Panel>
          <Panel
            title={doc?.name ?? "Script"}
            action={
              <Pill tone={running ? "warn" : "default"}>{running ? "RUN" : `${doc?.steps.length ?? 0} steps`}</Pill>
            }
          >
            <div className="mb-3 flex flex-wrap gap-1.5">
              {scripts.map((s, i) => (
                <Button key={s.name} size="sm" variant={i === current ? "primary" : "outline"} onClick={() => setCurrent(i)}>
                  {s.name}
                </Button>
              ))}
              <Button
                size="sm"
                variant="ghost"
                onClick={() => {
                  const name = `script-${scripts.length + 1}`;
                  const next = [...scripts, { name, steps: [] }];
                  setScripts(next);
                  saveScripts(next);
                  setCurrent(next.length - 1);
                }}
              >
                New
              </Button>
            </div>
            <div className="mb-3 grid grid-cols-2 gap-2">
              <Button variant="primary" disabled={running || !doc} onClick={() => doc && void runNamed(doc)}>
                Run script
              </Button>
              <Button
                variant="outline"
                onClick={() => {
                  if (!doc) return;
                  const sh = scriptToShell(doc);
                  void navigator.clipboard?.writeText(sh);
                  push("out", sh);
                  setTab("shell");
                }}
              >
                Copy shell
              </Button>
            </div>
            {(doc?.steps ?? []).length === 0 ? (
              <p className="mb-2 text-sm text-muted">Empty. Tap a palette op to add a step.</p>
            ) : null}
            <div className="flex flex-col gap-1.5">
              {(doc?.steps ?? []).map((step, i) => (
                <div
                  key={step.id}
                  draggable
                  onDragStart={() => setDrag(i)}
                  onDragOver={(e) => e.preventDefault()}
                  onDrop={() => drop(i)}
                  className="flex items-center gap-2 rounded-lg bg-elevated px-2 py-1.5"
                >
                  <GripVertical className="size-4 shrink-0 text-subtle" />
                  <span className="w-16 shrink-0 font-mono text-xs text-primary">{step.op}</span>
                  {step.op === "preset" ? (
                    <select
                      value={step.arg}
                      onChange={(e) => {
                        const steps = doc.steps.map((s, n) => (n === i ? { ...s, arg: e.target.value } : s));
                        patchSteps(steps);
                      }}
                      className="h-9 min-w-0 flex-1 rounded-md bg-background px-2 font-mono text-xs text-foreground"
                    >
                      {PRESETS.map((p) => (
                        <option key={p.id} value={p.id}>
                          {p.label}
                        </option>
                      ))}
                    </select>
                  ) : step.op === "wait" ? (
                    <input
                      inputMode="numeric"
                      value={step.ms ?? 1000}
                      onChange={(e) => {
                        const steps = doc.steps.map((s, n) => (n === i ? { ...s, ms: Number(e.target.value) || 0 } : s));
                        patchSteps(steps);
                      }}
                      className="h-9 min-w-0 flex-1 rounded-md bg-background px-2 font-mono text-xs text-foreground"
                    />
                  ) : (
                    <input
                      value={step.arg ?? step.cmd ?? ""}
                      onChange={(e) => {
                        const steps = doc.steps.map((s, n) => (n === i ? { ...s, arg: e.target.value } : s));
                        patchSteps(steps);
                      }}
                      placeholder={stepToLine(step)}
                      className="h-9 min-w-0 flex-1 rounded-md bg-background px-2 font-mono text-xs text-foreground"
                    />
                  )}
                  <Button size="sm" variant="ghost" onClick={() => move(i, -1)}>
                    ↑
                  </Button>
                  <Button size="sm" variant="ghost" onClick={() => move(i, 1)}>
                    ↓
                  </Button>
                  <Button
                    size="sm"
                    variant="ghost"
                    onClick={() => patchSteps(doc.steps.filter((_, n) => n !== i))}
                  >
                    ×
                  </Button>
                </div>
              ))}
            </div>
          </Panel>
        </>
      ) : null}

      {tab === "bridge" ? (
        <Panel title="Termux · Debian" action={<Pill tone={termuxSt?.termux ? "ok" : "default"}>{termuxSt?.termux ? "TERMUX" : native ? "NO APP" : "PWA"}</Pill>}>
          <p className="mb-3 text-sm leading-relaxed text-muted">
            After install, Claude Code, Gemini CLI, Grok, Kimi, and any shell agent can run <span className="font-mono text-foreground">dslv</span> inside
            Termux or proot Debian. Loopback only — the APK is the radio.
          </p>
          <Row label="Termux" value={termuxSt?.termux ? "present" : native ? "not installed" : "APK"} />
          <Row label="Debian" value="proot-distro login debian" />
          <Row label="Content" value="content://labs.dynogator.dslvzpdi.cli" />
          <div className="mt-3 rounded-lg bg-elevated px-3 py-2 font-mono text-xs leading-relaxed text-muted">
            <div>Termux</div>
            <div className="break-all text-foreground">{INSTALL_TERMUX}</div>
            <div className="mt-2">Debian</div>
            <div className="break-all text-foreground">{INSTALL_DEBIAN}</div>
            <div className="mt-2">Agents</div>
            <div className="break-all text-foreground">dslv tools &nbsp;·&nbsp; dslv status --json</div>
          </div>
          <div className="mt-3 grid grid-cols-1 gap-2">
            <Button
              variant="primary"
              disabled={!native}
              onClick={() => {
                const r = nativeJson<Record<string, unknown>>(() => nativeHost()?.termux?.("install"));
                push("out", String(r?.text ?? "install issued"));
                setTab("shell");
              }}
            >
              Install Termux aliases
            </Button>
            <Button
              variant="outline"
              disabled={!native}
              onClick={() => {
                const r = nativeJson<Record<string, unknown>>(() => nativeHost()?.termux?.("debian"));
                push("out", String(r?.text ?? "debian install issued"));
                setTab("shell");
              }}
            >
              Install into Debian proot
            </Button>
            <Button
              variant="outline"
              onClick={() => {
                void navigator.clipboard?.writeText(INSTALL_TERMUX);
              }}
            >
              Copy Termux one-liner
            </Button>
          </div>
          <p className="mt-3 text-xs leading-relaxed text-muted">
            Termux → Settings → Allow external apps. GrapheneOS will ask for RUN_COMMAND. Aliases: dslv-status, dslv-listen, dslv-mute,
            dslv-tune, dslv-capture, dslv-sensors, dslv-spectrum. Agents: <span className="font-mono">dslv tools</span> and{" "}
            <span className="font-mono">/cli/AGENTS.md</span>.
          </p>
          {termuxSt?.hint ? <p className="mt-2 text-xs text-warn">{termuxSt.hint}</p> : null}
        </Panel>
      ) : null}

      {tab !== "shell" ? (
        <p className="font-mono text-xs text-subtle">help · {CLI_HELP.split("\n")[1]}</p>
      ) : null}
    </div>
  );
}
