import { HotSlider } from "@/components/hot-slider";
import { Button } from "@/components/ui/button";
import { Switch } from "@/components/ui/switch";
import { isNativeApk } from "@/lib/native";
import { useApp } from "@/lib/store";
import { PRESETS } from "@/lib/types";
import { Menu, X } from "lucide-react";
import { useEffect, useRef, useState } from "react";

export function QuickMenu() {
  const [open, setOpen] = useState(false);
  const panel = useRef<HTMLDivElement>(null);
  const native = isNativeApk();
  const listen = useApp((s) => s.sdr.audio || s.usb.listen);
  const usbRx = useApp((s) => s.usb.rx);
  const pipeline = useApp((s) => s.tel.pipelineActive);
  const paused = useApp((s) => s.sdr.paused);
  const hotZones = useApp((s) => s.hotZones);
  const mode = useApp((s) => s.mode);
  const volume = useApp((s) => s.sdr.volume);
  const squelch = useApp((s) => s.sdr.squelch);
  const preset = useApp((s) => s.sdr.preset);
  const toggleAudio = useApp((s) => s.toggleAudio);
  const setUsbRx = useApp((s) => s.usbRx);
  const setPipeline = useApp((s) => s.setPipeline);
  const togglePause = useApp((s) => s.togglePause);
  const setHotZones = useApp((s) => s.setHotZones);
  const setMode = useApp((s) => s.setMode);
  const setVolume = useApp((s) => s.setVolume);
  const setSquelch = useApp((s) => s.setSquelch);
  const capture = useApp((s) => s.capture);
  const usbScan = useApp((s) => s.usbScan);
  const usbOpen = useApp((s) => s.usbOpen);
  const applyPreset = useApp((s) => s.applyPreset);
  const setView = useApp((s) => s.setView);

  useEffect(() => {
    if (!open) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") setOpen(false);
    };
    const onDown = (e: PointerEvent) => {
      if (panel.current && !panel.current.contains(e.target as Node)) setOpen(false);
    };
    window.addEventListener("keydown", onKey);
    const id = window.setTimeout(() => window.addEventListener("pointerdown", onDown), 0);
    return () => {
      window.clearTimeout(id);
      window.removeEventListener("keydown", onKey);
      window.removeEventListener("pointerdown", onDown);
    };
  }, [open]);

  return (
    <div className="relative" ref={panel}>
      <Button
        type="button"
        size="icon"
        variant="outline"
        aria-label={open ? "Close quick settings" : "Open quick settings"}
        aria-expanded={open}
        onClick={() => setOpen((v) => !v)}
        className="size-11 shrink-0"
      >
        {open ? <X className="size-5" strokeWidth={2} /> : <Menu className="size-5" strokeWidth={2} />}
      </Button>
      {open ? (
        <div className="menu-enter absolute left-0 top-[calc(100%+0.5rem)] z-40 max-h-[min(70dvh,36rem)] w-[min(20.5rem,calc(100vw-2rem))] overflow-y-auto rounded-xl bg-card p-3 shadow-[var(--shadow-border)]">
          <div className="mb-2 text-[0.6875rem] font-medium uppercase tracking-[0.16em] text-muted">Quick settings</div>
          <Switch label="Listen" checked={listen} onCheckedChange={() => toggleAudio()} />
          <Switch label="USB RX" checked={usbRx} disabled={!native} onCheckedChange={(on) => setUsbRx(on)} />
          <Switch label="Pipeline" checked={pipeline} onCheckedChange={(on) => setPipeline(on)} />
          <Switch label="Pause RF" checked={paused} onCheckedChange={() => togglePause()} />
          <Switch label="Hot zones" checked={hotZones} onCheckedChange={setHotZones} />

          <div className="mt-3 space-y-2 border-t border-border pt-3">
            <HotSlider
              label="Volume"
              min={0}
              max={100}
              value={Math.round(volume * 100)}
              display={`${Math.round(volume * 100)}%`}
              onChange={(n) => setVolume(n / 100)}
            />
            <HotSlider
              label="Squelch"
              min={0}
              max={100}
              value={Math.round(squelch * 100)}
              display={String(Math.round(squelch * 100))}
              onChange={(n) => setSquelch(n / 100)}
            />
          </div>

          <div className="mt-3 grid grid-cols-3 gap-1.5 border-t border-border pt-3">
            <Button size="sm" className="px-1 text-[0.6875rem]" variant={mode === "standalone" ? "primary" : "outline"} onClick={() => setMode("standalone")}>
              Handset
            </Button>
            <Button size="sm" className="px-1 text-[0.6875rem]" variant={mode === "simulated" ? "primary" : "outline"} onClick={() => setMode("simulated")}>
              Sim
            </Button>
            <Button size="sm" className="px-1 text-[0.6875rem]" variant={mode === "live" ? "primary" : "outline"} onClick={() => setMode("live")}>
              Alpha
            </Button>
          </div>

          <div className="mt-3 grid grid-cols-2 gap-1.5">
            {PRESETS.filter((p) => ["fm_broadcast", "nws", "2m_call", "airband"].includes(p.id)).map((p) => (
              <Button key={p.id} size="sm" variant={preset === p.id ? "primary" : "outline"} onClick={() => applyPreset(p.id)}>
                {p.label}
              </Button>
            ))}
          </div>

          <div className="mt-3 grid grid-cols-2 gap-1.5 border-t border-border pt-3">
            <Button size="sm" variant="outline" onClick={capture}>
              Seal
            </Button>
            <Button size="sm" variant="outline" onClick={usbScan} disabled={!native}>
              Scan OTG
            </Button>
            <Button size="sm" variant="outline" onClick={() => usbOpen("hackrf")} disabled={!native}>
              Open RF
            </Button>
            <Button
              size="sm"
              variant="outline"
              onClick={() => {
                setView("cli");
                setOpen(false);
              }}
            >
              CLI
            </Button>
          </div>
          <p className="mt-3 text-[0.625rem] leading-relaxed text-subtle">
            Red pulse = you can tap it. GPU compositor on this Pixel — GrapheneOS has no TPU/JNI path.
          </p>
        </div>
      ) : null}
    </div>
  );
}
