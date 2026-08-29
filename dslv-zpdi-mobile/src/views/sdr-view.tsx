import { HotSlider } from "@/components/hot-slider";
import { Panel, Pill, Row } from "@/components/panel";
import { Button } from "@/components/ui/button";
import { Waterfall } from "@/components/waterfall";
import { isNativeApk } from "@/lib/native";
import { useApp } from "@/lib/store";
import {
  DEVICE_LABEL,
  LNA_STEPS,
  PRESETS,
  STEP_HZ,
  VGA_STEPS,
  type DemodMode,
  type WaterfallMode,
} from "@/lib/types";
import { formatHz } from "@/lib/utils";
import { useMemo, useState } from "react";

const DEMODS: DemodMode[] = ["WFM", "NFM", "AM", "USB", "LSB", "CW", "RAW"];
const MODES: WaterfallMode[] = ["SWEEP", "NARROW", "SCOPE"];

const PRESET_GROUPS: { label: string; ids: string[] }[] = [
  { label: "Broadcast", ids: ["fm_broadcast", "fm_887", "fm_1073", "am_broadcast"] },
  { label: "VHF / UHF", ids: ["nws", "airband", "marine", "2m_call", "70cm", "gmrs"] },
  { label: "HF", ids: ["cb", "20m_usb", "40m_lsb", "40m_cw"] },
  { label: "Data", ids: ["adsb"] },
];

function fmtStep(hz: number) {
  const sign = hz < 0 ? "−" : "+";
  const a = Math.abs(hz);
  if (a >= 1_000_000) return `${sign}${a / 1_000_000}M`;
  if (a >= 1000) return `${sign}${a / 1000}k`;
  return `${sign}${a}`;
}

export function SdrView() {
  const sdr = useApp((s) => s.sdr);
  const tel = useApp((s) => s.tel);
  const usb = useApp((s) => s.usb);
  const mode = useApp((s) => s.mode);
  const setCenterHz = useApp((s) => s.setCenterHz);
  const setSpanMode = useApp((s) => s.setSpanMode);
  const zoom = useApp((s) => s.zoom);
  const setGain = useApp((s) => s.setGain);
  const setDemod = useApp((s) => s.setDemod);
  const setDevice = useApp((s) => s.setDevice);
  const setFloorCeil = useApp((s) => s.setFloorCeil);
  const cyclePalette = useApp((s) => s.cyclePalette);
  const applyPreset = useApp((s) => s.applyPreset);
  const toggleAudio = useApp((s) => s.toggleAudio);
  const togglePause = useApp((s) => s.togglePause);
  const setVolume = useApp((s) => s.setVolume);
  const setSquelch = useApp((s) => s.setSquelch);
  const stepHz = useApp((s) => s.stepHz);
  const usbScan = useApp((s) => s.usbScan);
  const usbOpen = useApp((s) => s.usbOpen);
  const usbClose = useApp((s) => s.usbClose);
  const usbRx = useApp((s) => s.usbRx);
  const [mhz, setMhz] = useState("");
  const native = isNativeApk();
  const liveUsb = usb.rx && usb.source === "usb";
  const listening = sdr.audio || usb.listen;
  const squelched = Boolean(liveUsb && usb.muted);
  const steps = STEP_HZ[sdr.demod];
  const grouped = useMemo(
    () =>
      PRESET_GROUPS.map((g) => ({
        ...g,
        items: g.ids.map((id) => PRESETS.find((p) => p.id === id)).filter(Boolean) as typeof PRESETS,
      })),
    [],
  );

  return (
    <div className="flex flex-col gap-3">
      <Panel
        title="HackRF · PortaPack"
        action={
          <Pill tone={listening ? "ok" : liveUsb ? "ok" : usb.open ? "warn" : "default"}>
            {listening ? "LISTEN" : liveUsb ? "RX" : usb.open ? "OPEN" : native ? "OTG" : "PWA"}
          </Pill>
        }
      >
        <p className="mb-2 text-xs leading-relaxed text-muted">
          {native
            ? "USB-C OTG auto-connects. Listen demodulates through the Pixel speaker. No Alpha required."
            : "Same instrument as the APK. Sideload on GrapheneOS for real HackRF IQ and speaker demod."}
        </p>
        <Row label="Radio" value={usb.board || DEVICE_LABEL[sdr.device]} tone={usb.open ? "primary" : "default"} />
        <Row
          label="Audio"
          value={squelched ? "squelched" : listening ? `${sdr.demod} · speaker` : "muted"}
          tone={squelched ? "warn" : listening ? "ok" : "default"}
        />
        {usb.error ? <p className="mt-2 font-mono text-xs text-danger">{usb.error}</p> : null}
        {usb.devices.length > 0 ? (
          <ul className="mt-2 flex flex-col gap-1">
            {usb.devices.map((d) => (
              <li key={d.deviceId} className="font-mono text-xs text-muted">
                {d.vid}:{d.pid} · {d.kind} · {d.name}
                {d.hasPermission === false ? " · need grant" : ""}
              </li>
            ))}
          </ul>
        ) : null}
        <div className="mt-3 grid grid-cols-2 gap-2">
          <Button variant="outline" onClick={() => usbScan()} disabled={!native}>
            Scan OTG
          </Button>
          <Button variant="outline" onClick={() => usbOpen("hackrf")} disabled={!native}>
            Open HackRF
          </Button>
          <Button variant={usb.rx ? "primary" : "outline"} onClick={() => usbRx(!usb.rx)} disabled={!native}>
            {usb.rx ? "Hold RX" : "Start RX"}
          </Button>
          <Button variant="outline" onClick={() => usbClose()} disabled={!native}>
            Close
          </Button>
        </div>
      </Panel>

      <Panel title="Tune">
        <div className="mb-3 flex items-end justify-between">
          <div>
            <div className="text-[0.6875rem] uppercase tracking-[0.14em] text-muted">Center</div>
            <div className="font-mono text-3xl font-medium tabular-nums leading-none text-foreground">
              {(sdr.centerHz / 1e6).toFixed(4)}
              <span className="ml-2 text-sm font-normal text-muted">MHz</span>
            </div>
          </div>
          <div className="text-right font-mono text-xs text-muted">
            <div>
              {sdr.demod} · {(sdr.spanHz / 1e6).toFixed(2)} MHz
            </div>
            <div className="text-primary">{DEVICE_LABEL.hackrf1.split(" / ")[0]}</div>
          </div>
        </div>

        <Button
          className="mb-3 h-12 w-full text-base"
          variant={listening ? "primary" : "outline"}
          onClick={toggleAudio}
        >
          {listening ? (squelched ? "Listening · squelched" : `Listening · ${sdr.demod}`) : `Listen · ${sdr.demod}`}
        </Button>

        <div className="grid grid-cols-4 gap-2">
          {steps.map((hz) => (
            <Button key={hz} variant="outline" size="sm" onClick={() => stepHz(hz)}>
              {fmtStep(hz)}
            </Button>
          ))}
        </div>
        <div className="mt-2 grid grid-cols-4 gap-2">
          <Button variant="outline" size="sm" onClick={() => zoom(1)}>
            Zoom in
          </Button>
          <Button variant="outline" size="sm" onClick={() => zoom(-1)}>
            Zoom out
          </Button>
          <Button variant="outline" size="sm" onClick={togglePause}>
            {sdr.paused ? "Resume" : "Pause"}
          </Button>
          <Button variant="outline" size="sm" onClick={cyclePalette}>
            Pal {sdr.palette + 1}
          </Button>
        </div>
        <form
          className="mt-3 flex gap-2"
          onSubmit={(e) => {
            e.preventDefault();
            const v = parseFloat(mhz);
            if (!Number.isFinite(v)) return;
            setCenterHz(v * 1e6);
            setMhz("");
          }}
        >
          <input
            inputMode="decimal"
            value={mhz}
            onChange={(e) => setMhz(e.target.value)}
            placeholder="MHz"
            className="h-11 min-w-0 flex-1 rounded-md bg-elevated px-3 font-mono text-sm text-foreground shadow-[var(--shadow-border)] outline-none placeholder:text-subtle focus-visible:ring-2 focus-visible:ring-ring"
          />
          <Button type="submit" variant="primary">
            Tune
          </Button>
        </form>
        <div className="mt-3 flex flex-wrap gap-1.5">
          {MODES.map((m) => (
            <Button
              key={m}
              size="sm"
              variant={sdr.waterfallMode === m ? "primary" : "outline"}
              onClick={() => setSpanMode(m)}
            >
              {m}
            </Button>
          ))}
        </div>

        <HotSlider
          label="Volume"
          min={0}
          max={100}
          value={Math.round(sdr.volume * 100)}
          display={`${Math.round(sdr.volume * 100)}%`}
          onChange={(n) => setVolume(n / 100)}
        />
        <div className="mt-2">
          <HotSlider
            label="Squelch"
            min={0}
            max={100}
            value={Math.round(sdr.squelch * 100)}
            display={String(Math.round(sdr.squelch * 100))}
            onChange={(n) => setSquelch(n / 100)}
          />
        </div>
      </Panel>

      <Panel
        title="Waterfall"
        action={
          <div className="flex gap-1.5">
            <Pill tone="primary">{sdr.waterfallMode}</Pill>
            <Pill tone={liveUsb ? "ok" : "default"}>{liveUsb ? "USB" : mode === "standalone" ? "HANDSET" : "SIM"}</Pill>
          </div>
        }
      >
        <Waterfall
          centerHz={sdr.centerHz}
          spanHz={sdr.spanHz}
          floorDbm={sdr.floorDbm}
          ceilDbm={sdr.ceilDbm}
          palette={sdr.palette}
          onTune={setCenterHz}
        />
        <p className="mt-2 text-xs text-muted">
          {liveUsb
            ? "Live HackRF bins · tap to retune. Dashed trace is peak-hold."
            : "Tap the waterfall to retune. Dashed trace is peak-hold."}
        </p>
        <div className="mt-2 grid grid-cols-2 gap-x-3">
          <Row label="Peak" value={`${tel.peakDbm.toFixed(1)} dBm`} />
          <Row label="Floor" value={`${tel.noiseFloorDbm.toFixed(1)} dBm`} />
          <Row label="SNR" value={`${tel.snrDb.toFixed(1)} dB`} tone={tel.snrDb > 20 ? "ok" : "warn"} />
          <Row label="At" value={formatHz(tel.peakHz)} tone="primary" />
        </div>
      </Panel>

      <Panel title="Presets">
        {grouped.map((g) => (
          <div key={g.label} className="mb-3 last:mb-0">
            <div className="mb-1.5 text-[0.6875rem] uppercase tracking-[0.14em] text-muted">{g.label}</div>
            <div className="grid grid-cols-2 gap-2">
              {g.items.map((p) => (
                <Button
                  key={p.id}
                  variant={sdr.preset === p.id ? "primary" : "outline"}
                  size="sm"
                  onClick={() => applyPreset(p.id)}
                >
                  {p.label}
                  <span className="font-mono text-[0.625rem] opacity-70">{p.demod}</span>
                </Button>
              ))}
            </div>
          </div>
        ))}
      </Panel>

      <Panel title="Front end">
        <div className="mb-3 flex flex-wrap gap-1.5">
          {DEMODS.map((d) => (
            <Button key={d} size="sm" variant={sdr.demod === d ? "primary" : "ghost"} onClick={() => setDemod(d)}>
              {d}
            </Button>
          ))}
        </div>
        <HotSlider
          label="LNA"
          min={0}
          max={LNA_STEPS.length - 1}
          value={Math.max(0, LNA_STEPS.indexOf(sdr.lnaGain))}
          display={`${sdr.lnaGain} dB`}
          onChange={(n) => setGain("lna", LNA_STEPS[n] ?? 24)}
        />
        <div className="mb-3 mt-2">
          <HotSlider
            label="VGA"
            min={0}
            max={VGA_STEPS.length - 1}
            value={Math.max(0, VGA_STEPS.indexOf(sdr.vgaGain))}
            display={`${sdr.vgaGain} dB`}
            onChange={(n) => setGain("vga", VGA_STEPS[n] ?? 32)}
          />
        </div>
        <Row label="Device" value="" />
        <div className="relative mt-1 rounded-md" data-hot>
          <select
            value={sdr.device}
            onChange={(e) => setDevice(e.target.value as typeof sdr.device)}
            className="h-11 w-full rounded-md bg-elevated px-3 font-mono text-sm text-foreground shadow-[var(--shadow-border)] outline-none"
          >
            <option value="hackrf1">HackRF One / PortaPack</option>
            <option value="pluto_iio">PlutoSDR+ / HamGeek AD9363</option>
            <option value="libresdr">LibreSDR</option>
          </select>
        </div>
        <div className="mt-3 grid grid-cols-2 gap-2">
          <Button size="sm" variant="outline" onClick={() => setFloorCeil(sdr.floorDbm - 5, undefined)}>
            Floor −5
          </Button>
          <Button size="sm" variant="outline" onClick={() => setFloorCeil(sdr.floorDbm + 5, undefined)}>
            Floor +5
          </Button>
          <Button size="sm" variant="outline" onClick={() => setFloorCeil(undefined, sdr.ceilDbm - 5)}>
            Ceil −5
          </Button>
          <Button size="sm" variant="outline" onClick={() => setFloorCeil(undefined, sdr.ceilDbm + 5)}>
            Ceil +5
          </Button>
        </div>
      </Panel>
    </div>
  );
}
