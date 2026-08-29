import { Mark } from "@/components/mark";
import { QuickMenu } from "@/components/quick-menu";
import { LinkView } from "@/views/link-view";
import { MetroView } from "@/views/metro-view";
import { OpsView } from "@/views/ops-view";
import { SdrView } from "@/views/sdr-view";
import { SwarmView } from "@/views/swarm-view";
import { CliView } from "@/views/cli-view";
import { startSimListen } from "@/lib/listen-audio";
import { useApp } from "@/lib/store";
import { isNativeApk } from "@/lib/native";
import { RELEASE } from "@/lib/release-meta";
import type { ViewId } from "@/lib/types";
import { pad2 } from "@/lib/utils";
import { Cable, Gauge, LayoutGrid, Radio, Terminal, Waypoints } from "lucide-react";
import { useEffect, useState, useSyncExternalStore } from "react";

const NAV: { id: ViewId; label: string; icon: typeof LayoutGrid }[] = [
  { id: "ops", label: "Ops", icon: LayoutGrid },
  { id: "sdr", label: "RF", icon: Radio },
  { id: "swarm", label: "Swarm", icon: Waypoints },
  { id: "metro", label: "Metro", icon: Gauge },
  { id: "cli", label: "CLI", icon: Terminal },
  { id: "link", label: "Link", icon: Cable },
];

function clockStamp() {
  const d = new Date();
  return `${pad2(d.getUTCHours())}:${pad2(d.getUTCMinutes())}:${pad2(d.getUTCSeconds())}Z`;
}

let clockCache = clockStamp();

function subscribeClock(cb: () => void) {
  clockCache = clockStamp();
  const id = window.setInterval(() => {
    clockCache = clockStamp();
    cb();
  }, 1000);
  return () => window.clearInterval(id);
}

function useClock() {
  return useSyncExternalStore(subscribeClock, () => clockCache, () => "—");
}

export function AppShell() {
  const view = useApp((s) => s.view);
  const setView = useApp((s) => s.setView);
  const hydrate = useApp((s) => s.hydrate);
  const tick = useApp((s) => s.tick);
  const applyPixelFix = useApp((s) => s.applyPixelFix);
  const halMode = useApp((s) => s.tel.halMode);
  const timingHealthy = useApp((s) => s.tel.timingHealthy);
  const mode = useApp((s) => s.mode);
  const sdrAudio = useApp((s) => s.sdr.audio);
  const sdrDemod = useApp((s) => s.sdr.demod);
  const sdrCenter = useApp((s) => s.sdr.centerHz);
  const sdrVolume = useApp((s) => s.sdr.volume);
  const usbRx = useApp((s) => s.usb.rx);
  const usbListen = useApp((s) => s.usb.listen);
  const hotZones = useApp((s) => s.hotZones);
  const clock = useClock();
  const [armed, setArmed] = useState(false);
  const linkTag =
    usbListen || sdrAudio ? "LISTEN" : usbRx ? "USB RX" : mode === "live" ? "LIVE" : mode === "standalone" ? "HANDSET" : "SIM";

  useEffect(() => {
    hydrate();
    setArmed(true);
  }, [hydrate]);

  useEffect(() => {
    document.documentElement.dataset.hotzones = hotZones ? "on" : "off";
  }, [hotZones]);

  useEffect(() => {
    if (!isNativeApk() || !("geolocation" in navigator)) return;
    const id = navigator.geolocation.watchPosition(
      (pos) => {
        applyPixelFix(
          pos.coords.latitude,
          pos.coords.longitude,
          pos.coords.accuracy,
          pos.coords.altitude ?? undefined,
        );
      },
      () => {
        /* denied or unavailable */
      },
      { enableHighAccuracy: true, maximumAge: 4000, timeout: 12000 },
    );
    return () => navigator.geolocation.clearWatch(id);
  }, [applyPixelFix]);

  useEffect(() => {
    if (!armed) return;
    const id = window.setInterval(tick, 400);
    return () => window.clearInterval(id);
  }, [tick, armed]);

  useEffect(() => {
    if (!sdrAudio) return;
    if (isNativeApk()) return;
    return startSimListen({
      demod: sdrDemod,
      centerHz: sdrCenter,
      volume: sdrVolume,
    });
  }, [sdrAudio, sdrDemod, sdrCenter, sdrVolume]);

  return (
    <div className="app-grid flex min-h-dvh flex-col bg-background text-foreground">
      <header className="sticky top-0 z-30 border-b border-border bg-background/95 px-4 pb-3 pt-[max(0.75rem,env(safe-area-inset-top))]">
        <div className="flex items-center justify-between gap-3">
          <div className="flex min-w-0 items-center gap-2.5">
            <QuickMenu />
            <Mark className="size-8 shrink-0 text-primary" />
            <div className="min-w-0">
              <div className="text-xs font-medium uppercase tracking-[0.22em] text-muted">
                DynoGator Labs
              </div>
              <div className="text-base font-semibold tracking-tight text-foreground">DSLV-ZPDI</div>
            </div>
          </div>
          <div className="text-right">
            <div className="font-mono text-xs tabular-nums text-muted">{clock}</div>
            <div className="font-mono text-xs uppercase tracking-wide text-primary">
              {linkTag} · {halMode}
            </div>
          </div>
        </div>
        <div className="mt-2 flex items-center justify-between font-mono text-xs text-muted">
          <span>Rev {RELEASE.version} · Pixel C2</span>
          <span className={timingHealthy ? "text-ok" : "text-warn"}>
            {timingHealthy ? "TIMING LOCK" : "TIMING DEGRADED"}
          </span>
        </div>
      </header>

      <main className="mx-auto w-full max-w-3xl flex-1 px-4 py-4 pb-28">
        {view === "ops" ? <OpsView /> : null}
        {view === "sdr" ? <SdrView /> : null}
        {view === "swarm" ? <SwarmView /> : null}
        {view === "metro" ? <MetroView /> : null}
        {view === "cli" ? <CliView /> : null}
        {view === "link" ? <LinkView /> : null}
      </main>

      <nav className="fixed inset-x-0 bottom-0 z-20 border-t border-border bg-background/95 pb-[max(0.5rem,env(safe-area-inset-bottom))]">
        <ul className="mx-auto grid max-w-3xl grid-cols-6">
          {NAV.map((item) => {
            const active = view === item.id;
            const Icon = item.icon;
            return (
              <li key={item.id}>
                <button
                  type="button"
                  onClick={() => setView(item.id)}
                  className={`flex h-14 w-full flex-col items-center justify-center gap-0.5 rounded-md text-xs transition-[color,transform] duration-150 ease-out active:scale-[0.96] ${
                    active ? "text-primary" : "text-muted"
                  }`}
                >
                  <Icon className="size-5" strokeWidth={active ? 2.2 : 1.7} />
                  {item.label}
                </button>
              </li>
            );
          })}
        </ul>
      </nav>
    </div>
  );
}
