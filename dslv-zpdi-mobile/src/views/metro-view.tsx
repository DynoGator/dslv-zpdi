import { Panel, Pill, Row } from "@/components/panel";
import { Button } from "@/components/ui/button";
import { isNativeApk } from "@/lib/native";
import { useApp } from "@/lib/store";
import { GENESIS_SHA256 } from "@/lib/types";
import { formatNs, shortHash } from "@/lib/utils";

export function MetroView() {
  const tel = useApp((s) => s.tel);
  const pipe = useApp((s) => s.pipe);
  const usb = useApp((s) => s.usb);
  const mode = useApp((s) => s.mode);
  const commands = useApp((s) => s.commands);
  const captures = useApp((s) => s.captures);
  const resetBaseline = useApp((s) => s.resetBaseline);
  const setHalMode = useApp((s) => s.setHalMode);
  const setPipeline = useApp((s) => s.setPipeline);
  const sealPipeline = useApp((s) => s.sealPipeline);
  const rotatePipeline = useApp((s) => s.rotatePipeline);
  const native = isNativeApk();
  const gnss = tel.pixel.lat != null;
  const alpha = mode === "live";

  return (
    <div className="flex flex-col gap-3">
      <Panel
        title={alpha ? "Timing authority · LBE-1421" : "Timing · Pixel GNSS"}
        action={<Pill tone={alpha ? (tel.timingHealthy ? "ok" : "danger") : gnss ? "ok" : "warn"}>{alpha ? (tel.timingHealthy ? "LOCKED" : "DEGRADED") : gnss ? "GNSS" : "SEARCH"}</Pill>}
      >
        <Row
          label={alpha ? "GPSDO" : "Pixel GNSS"}
          value={alpha ? (tel.gpsLock ? "3D" : "NONE") : gnss ? "3D" : "NONE"}
          tone={(alpha ? tel.gpsLock : gnss) ? "ok" : "danger"}
        />
        {gnss ? (
          <Row
            label="Fix"
            value={`${tel.pixel.lat!.toFixed(5)}, ${tel.pixel.lon!.toFixed(5)}`}
            tone="primary"
          />
        ) : null}
        <Row label="Acc" value={tel.pixel.accM != null ? `${tel.pixel.accM.toFixed(1)} m` : "—"} />
        <Row label="Alt" value={tel.pixel.alt != null ? `${tel.pixel.alt.toFixed(0)} m` : "—"} />
        <Row label="PPS jitter" value={formatNs(tel.ppsJitterNs)} tone={tel.ppsJitterNs < 500 ? "ok" : "warn"} />
        <Row label="chrony RMS" value={`${tel.chronyOffsetUs.toFixed(2)} µs`} />
        <Row label="Stratum" value={String(tel.chronyStratum)} />
        <Row label="GPIO" value={alpha ? "PPS · pin 24 / GPIO8" : "handset · no PPS"} />
        <Row label="REF" value={alpha ? "10 MHz → EXT_REF_CLK" : "TCXO internal"} />
        <p className="mt-2 text-xs leading-relaxed text-muted">
          {alpha
            ? "Pi 5 remains Tier-1 timing/SDR/HDF5 authority. This Pixel cannot override GPSDO or promote USB IQ to institutional PRIMARY."
            : "No GPSDO required. Pixel GNSS stamps this independent node. When Alpha is live, LBE-1421 on the Pi 5 is still the only timing authority that can promote PRIMARY."}
        </p>
      </Panel>

      <Panel
        title="SPEC-007 HDF5 · tier-2"
        action={<Pill tone={pipe.running ? "ok" : "warn"}>{pipe.running ? "ARMED" : "HELD"}</Pill>}
      >
        <Row label="Route" value={usb.rx ? "SECONDARY_QUARANTINED" : pipe.route} tone={usb.rx ? "warn" : "ok"} />
        <Row label="Tier" value="2 · pixel-9-pro-xl" />
        <Row label="Clock" value="internal" tone="warn" />
        <Row label="LOCAL PRIMARY" value={String(pipe.primaryWritten || Math.floor(tel.primaryWritten))} tone="ok" />
        <Row label="SECONDARY" value={String(pipe.secondaryWritten || Math.floor(tel.secondaryWritten))} />
        <Row
          label="Integrity"
          value={pipe.integrityFailed || tel.integrityFailed ? String(pipe.integrityFailed || tel.integrityFailed) : "CLEAN"}
          tone={pipe.integrityFailed || tel.integrityFailed ? "danger" : "ok"}
        />
        <Row label="HMAC" value={pipe.hmacReady || !native ? "filesDir/hmac.key" : "pending"} tone={pipe.hmacReady || !native ? "ok" : "warn"} />
        <Row label="File ver" value={pipe.fileVersion} />
        <Row label="Buffered" value={String(pipe.buffered)} />
        <div className="mt-2 rounded-md bg-elevated px-3 py-2 font-mono text-[0.6875rem] leading-relaxed text-muted">
          <div>genesis {shortHash(GENESIS_SHA256, 16)}…</div>
          <div className="break-all">chain {shortHash(pipe.chainHead, 24)}…</div>
          {pipe.lastSha256 ? <div className="mt-1 break-all">file {pipe.lastSha256}</div> : null}
        </div>
        <p className="mt-2 text-xs leading-relaxed text-muted">
          SHA-256 sidecar + HMAC-SHA256 attestation + atomic .h5.partial rename. USB RF is quarantined JSONL. Sensor archive is local PRIMARY labeled hardware_tier=2.
        </p>
        <div className="mt-3 flex flex-wrap gap-2">
          <Button size="sm" variant={pipe.running ? "outline" : "primary"} onClick={() => setPipeline(!tel.pipelineActive)}>
            {tel.pipelineActive ? "Hold" : "Start ingest"}
          </Button>
          <Button size="sm" variant="outline" onClick={sealPipeline}>
            Seal file
          </Button>
          <Button size="sm" variant="outline" onClick={rotatePipeline}>
            Rotate
          </Button>
        </div>
      </Panel>

      <Panel title="SPEC-009 baseline FSM" action={<Pill tone={tel.baseline === "LOCKED" ? "ok" : "warn"}>{tel.baseline}</Pill>}>
        <Row label="Hours" value={tel.baselineHours.toFixed(1)} />
        <Row label="Gate" value="72 h · 240 samples" />
        <Row label="PRIMARY" value={tel.baseline === "LOCKED" ? "armed" : "held"} />
        <p className="mt-2 text-xs leading-relaxed text-muted">
          LEARNING writes SECONDARY only. A hard reset on Alpha is a C2 forward — the Pixel will not stamp Tier-1 baseline itself.
        </p>
        <div className="mt-3 flex gap-2">
          <Button variant="outline" onClick={() => resetBaseline(false)}>
            Soft reset
          </Button>
          <Button variant="danger" onClick={() => resetBaseline(true)}>
            Hard reset
          </Button>
        </div>
      </Panel>

      <Panel title="HAL">
        <Row label="Mode" value={tel.halMode} />
        <Row label="USB" value={usb.open ? usb.kind : "idle"} />
        <div className="mt-3 flex flex-wrap gap-2">
          <Button size="sm" variant="outline" onClick={() => setHalMode("SIMULATOR")}>
            Simulator
          </Button>
          <Button size="sm" variant="outline" onClick={() => setHalMode("HARDWARE")}>
            Hardware
          </Button>
          <Button size="sm" variant="outline" onClick={() => setHalMode("OFFLINE")}>
            Offline
          </Button>
        </div>
      </Panel>

      <Panel title="Captures">
        {captures.length === 0 ? (
          <p className="text-sm text-muted">No sealed captures this session.</p>
        ) : (
          <ul className="flex flex-col gap-2">
            {captures.slice(0, 8).map((c) => (
              <li key={c.id} className="rounded-md bg-elevated px-3 py-2 font-mono text-xs">
                <div className="flex justify-between text-muted">
                  <span>{c.ts.slice(11, 19)}Z</span>
                  <span className="text-primary">{(c.centerHz / 1e6).toFixed(3)} MHz</span>
                </div>
                <div className="mt-1 text-foreground">
                  peak {c.peakDbm.toFixed(1)} dBm · SNR {c.snrDb.toFixed(1)} · r {c.rGlobal.toFixed(3)}
                </div>
              </li>
            ))}
          </ul>
        )}
      </Panel>

      <Panel title="C2 audit · SPEC-022">
        {commands.length === 0 ? (
          <p className="text-sm text-muted">No commands issued. Tune, gain, USB, and pipeline actions land here.</p>
        ) : (
          <ul className="flex flex-col gap-2">
            {commands.slice(0, 12).map((c) => (
              <li key={c.commandId} className="rounded-md bg-elevated px-3 py-2">
                <div className="flex items-center justify-between gap-2">
                  <span className="font-mono text-xs text-primary">{c.capability}</span>
                  <Pill tone={c.state === "COMPLETED" ? "ok" : "warn"}>{c.state}</Pill>
                </div>
                <div className="mt-1 font-mono text-[0.6875rem] text-muted">
                  {shortHash(c.commandId)} · {c.result}
                </div>
              </li>
            ))}
          </ul>
        )}
      </Panel>
    </div>
  );
}
