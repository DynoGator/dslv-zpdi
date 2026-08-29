import { CoherenceDial } from "@/components/coherence-dial";
import { Metric, Panel, Pill, Row } from "@/components/panel";
import { Button } from "@/components/ui/button";
import { Waterfall } from "@/components/waterfall";
import { useApp } from "@/lib/store";
import { formatHz, formatNs } from "@/lib/utils";
import { APK_HREF, isNativeApk } from "@/lib/native";
import { RELEASE } from "@/lib/release-meta";

function fmtUptime(s: number) {
  const h = Math.floor(s / 3600);
  const m = Math.floor((s % 3600) / 60);
  return `${h}h ${m}m`;
}

export function OpsView() {
  const tel = useApp((s) => s.tel);
  const sdr = useApp((s) => s.sdr);
  const usb = useApp((s) => s.usb);
  const pipe = useApp((s) => s.pipe);
  const mode = useApp((s) => s.mode);
  const capture = useApp((s) => s.capture);
  const setPipeline = useApp((s) => s.setPipeline);
  const usbRx = useApp((s) => s.usbRx);
  const toggleAudio = useApp((s) => s.toggleAudio);
  const liveError = useApp((s) => s.liveError);
  const setCenterHz = useApp((s) => s.setCenterHz);
  const setView = useApp((s) => s.setView);
  const native = isNativeApk();
  const liveUsb = usb.rx && usb.source === "usb";
  const listening = sdr.audio || usb.listen;
  const gnss = tel.pixel.lat != null;

  return (
    <div className="flex flex-col gap-3">
      {!native ? (
        <a
          href={APK_HREF}
          download={RELEASE.apk}
          data-hot
          className="flex min-h-11 items-center justify-between gap-3 rounded-xl bg-primary px-4 py-3 text-primary-foreground shadow-[var(--shadow-border)]"
        >
          <span className="text-sm font-medium">Install Pixel APK · HackRF Listen</span>
          <span className="font-mono text-xs">{RELEASE.version}</span>
        </a>
      ) : null}
      {liveError ? (
        <div className="rounded-lg bg-danger/10 px-3 py-2 font-mono text-xs text-danger">
          Alpha link: {liveError}. Local suite continues.
        </div>
      ) : null}

      <Panel
        title="Lock chain"
        action={<Pill tone={tel.pipelineActive ? "ok" : "warn"}>{tel.pipelineActive ? "ARMED" : "HELD"}</Pill>}
      >
        <div className="flex flex-wrap gap-1.5">
          <Pill tone={gnss || tel.gpsLock ? "ok" : "danger"}>
            {mode === "live" ? (tel.gpsLock ? "GPSDO lock" : "GPSDO search") : gnss ? "Pixel GNSS" : "GNSS search"}
          </Pill>
          <Pill tone={tel.timingHealthy ? "ok" : "warn"}>PPS {formatNs(tel.ppsJitterNs)}</Pill>
          <Pill tone={tel.halMode === "OFFLINE" ? "danger" : "primary"}>{tel.halMode}</Pill>
          <Pill tone={tel.baseline === "LOCKED" ? "ok" : "warn"}>FSM {tel.baseline}</Pill>
          <Pill tone={listening ? "ok" : liveUsb ? "ok" : mode === "live" ? "primary" : "default"}>
            {listening ? "LISTEN" : liveUsb ? "USB RX" : mode === "live" ? "LIVE" : mode === "standalone" ? "HANDSET" : "SIM"}
          </Pill>
        </div>
        <div className="mt-3 grid grid-cols-2 gap-2">
          <Metric label="Center" value={(sdr.centerHz / 1e6).toFixed(3)} unit="MHz" tone="primary" />
          <Metric label="SNR" value={tel.snrDb.toFixed(1)} unit="dB" tone={tel.snrDb > 20 ? "ok" : "warn"} />
          <Metric label="Peak" value={tel.peakDbm.toFixed(1)} unit="dBm" />
          <Metric
            label="Anomaly"
            value={String(tel.anomalyBins)}
            unit="bins"
            tone={tel.anomalyBins > 24 ? "warn" : "default"}
          />
        </div>
      </Panel>

      <Panel
        title={liveUsb ? "HackRF RF" : mode === "standalone" ? "Handset RF" : mode === "live" ? "Alpha RF" : "Sim RF"}
        action={
          <Button size="sm" variant="ghost" onClick={() => setView("sdr")}>
            Open RF
          </Button>
        }
      >
        <Waterfall
          centerHz={sdr.centerHz}
          spanHz={sdr.spanHz}
          floorDbm={sdr.floorDbm}
          ceilDbm={sdr.ceilDbm}
          palette={sdr.palette}
          compact
          onTune={(hz) => {
            setCenterHz(hz);
            setView("sdr");
          }}
        />
      </Panel>

      <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
        <Panel title="KCET-ATLAS">
          <CoherenceDial r={tel.rGlobal} phases={tel.phases} className="mx-auto h-44 w-44" />
          <Row label="r_local" value={tel.rLocal.toFixed(3)} />
          <Row label="r_smooth" value={tel.rSmooth.toFixed(3)} />
          <Row label="Peak bin" value={formatHz(tel.peakHz)} tone="primary" />
        </Panel>

        <Panel title="Tier-2 node">
          <Row label="Host" value={native ? "pixel-9-pro-xl" : tel.hostname} />
          <Row label="USB" value={usb.open ? usb.kind : "idle"} tone={usb.open ? "ok" : "default"} />
          <Row label="GNSS" value={gnss ? `${tel.pixel.lat!.toFixed(4)}, ${tel.pixel.lon!.toFixed(4)}` : "no fix"} tone={gnss ? "ok" : "warn"} />
          <Row label="|B|" value={`${tel.pixel.magAbs.toFixed(1)} µT`} tone="primary" />
          <Row label="Trust" value={tel.pixel.trustScore.toFixed(2)} />
          <Row label="CPU" value={`${tel.cpuPct.toFixed(0)}%`} tone={tel.cpuPct > 80 ? "danger" : "default"} />
          <Row label="Uptime" value={fmtUptime(tel.uptimeS)} />
          <Row label="Ingest" value={`${tel.ingestHz.toFixed(1)} Hz`} />
        </Panel>
      </div>

      <Panel title="Pipeline · SPEC-007">
        <Row label="Service" value={tel.pipelineActive ? "ACTIVE" : "HELD"} tone={tel.pipelineActive ? "ok" : "warn"} />
        <Row label="LOCAL PRIMARY" value={String(pipe.primaryWritten || Math.floor(tel.primaryWritten))} tone="ok" />
        <Row label="SECONDARY" value={String(pipe.secondaryWritten || Math.floor(tel.secondaryWritten))} />
        <Row
          label="Integrity"
          value={(pipe.integrityFailed || tel.integrityFailed) === 0 ? "CLEAN" : String(pipe.integrityFailed || tel.integrityFailed)}
          tone={pipe.integrityFailed || tel.integrityFailed ? "danger" : "ok"}
        />
        <Row label="Chain" value={`${pipe.chainHead.slice(0, 12)}…`} />
        <Row label="Last event" value={tel.lastEvent} />
        <div className="mt-3 flex flex-wrap gap-2">
          <Button variant={tel.pipelineActive ? "outline" : "primary"} onClick={() => setPipeline(!tel.pipelineActive)}>
            {tel.pipelineActive ? "Hold pipeline" : "Start pipeline"}
          </Button>
          <Button variant="outline" onClick={capture}>
            Seal capture
          </Button>
          <Button variant={listening ? "primary" : "outline"} onClick={toggleAudio}>
            {listening ? "Mute" : "Listen"}
          </Button>
          <Button variant={usb.rx ? "primary" : "outline"} onClick={() => usbRx(!usb.rx)} disabled={!native}>
            {usb.rx ? "USB RX on" : "USB RX"}
          </Button>
          <Button variant="outline" onClick={() => setView("cli")}>
            CLI
          </Button>
        </div>
      </Panel>

      <Panel title="Environment">
        <Row label="Kp" value={tel.kp.toFixed(1)} tone={tel.kp >= 5 ? "warn" : "default"} />
        <Row label="SFI" value={tel.sfi.toFixed(0)} />
        <Row label="Aurora" value={`${tel.auroraPct.toFixed(0)}%`} />
        <Row label="Wx" value={tel.storm} />
        <Row label="Rn" value={`${tel.radonPci.toFixed(1)} pCi/L`} tone={tel.radonPci > 8 ? "warn" : "ok"} />
        <Row
          label="UPS"
          value={`${tel.upsPct.toFixed(0)}% · ${tel.upsVolt.toFixed(2)} V`}
          tone={tel.acPresent ? "ok" : "warn"}
        />
      </Panel>

      <button
        type="button"
        onClick={() => setView("link")}
        className="flex items-center gap-3 overflow-hidden rounded-xl bg-card p-3 text-left shadow-[var(--shadow-border)]"
      >
        <img
          src="/lab-crest.jpg"
          alt=""
          className="size-14 shrink-0 rounded-lg object-cover"
        />
        <div className="min-w-0 flex-1">
          <div className="text-xs font-medium uppercase tracking-[0.16em] text-muted">DynoGator Labs</div>
          <div className="mt-0.5 truncate font-mono text-sm text-primary">Circuit galleon · bootloader watch</div>
        </div>
        <img
          src="/lab-banner.jpg"
          alt=""
          className="hidden h-14 w-32 shrink-0 rounded-md object-cover object-right sm:block"
        />
      </button>
    </div>
  );
}
