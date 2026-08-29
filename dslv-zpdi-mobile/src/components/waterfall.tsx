import { useEffect, useRef, useState } from "react";
import { BINS, HISTORY, type PaletteId } from "@/lib/types";
import { rfBus } from "@/lib/rf-bus";
import { formatMhz } from "@/lib/utils";

const MAPS: [number, number, number][][] = [
  [
    [12, 16, 20],
    [22, 48, 52],
    [48, 118, 108],
    [148, 196, 184],
    [236, 240, 236],
  ],
  [
    [14, 12, 18],
    [48, 32, 62],
    [102, 70, 48],
    [196, 164, 112],
    [242, 236, 220],
  ],
  [
    [10, 14, 16],
    [24, 52, 66],
    [42, 104, 86],
    [168, 196, 92],
    [234, 238, 214],
  ],
];

function lerp(a: number, b: number, t: number) {
  return a + (b - a) * t;
}

function sampleMap(t: number, pal: PaletteId): [number, number, number] {
  const stops = MAPS[pal];
  const x = Math.max(0, Math.min(0.999, t)) * (stops.length - 1);
  const i = Math.floor(x);
  const f = x - i;
  const a = stops[i];
  const b = stops[i + 1] ?? a;
  return [lerp(a[0], b[0], f), lerp(a[1], b[1], f), lerp(a[2], b[2], f)];
}

function lift(t: number) {
  return Math.pow(Math.max(0, Math.min(1, t)), 0.42);
}

export function Waterfall({
  centerHz,
  spanHz,
  floorDbm,
  ceilDbm,
  palette,
  compact = false,
  onTune,
}: {
  centerHz: number;
  spanHz: number;
  floorDbm: number;
  ceilDbm: number;
  palette: PaletteId;
  compact?: boolean;
  onTune?: (hz: number) => void;
}) {
  const wf = useRef<HTMLCanvasElement>(null);
  const sp = useRef<HTMLCanvasElement>(null);
  const lastFrame = useRef(-1);
  const [cursor, setCursor] = useState<number | null>(null);

  useEffect(() => {
    let raf = 0;
    let row: ImageData | null = null;
    let hidden = document.hidden;
    const onVis = () => {
      hidden = document.hidden;
    };
    document.addEventListener("visibilitychange", onVis);

    const paint = () => {
      raf = requestAnimationFrame(paint);
      if (hidden) return;
      const frame = rfBus.frame();
      if (frame === lastFrame.current) return;
      lastFrame.current = frame;

      const wfc = wf.current;
      const spc = sp.current;
      if (!wfc || !spc) return;
      const wctx = wfc.getContext("2d", { alpha: false, desynchronized: true });
      const sctx = spc.getContext("2d", { alpha: true, desynchronized: true });
      if (!wctx || !sctx) return;

      if (wfc.width !== BINS || wfc.height !== HISTORY) {
        wfc.width = BINS;
        wfc.height = HISTORY;
      }

      const range = Math.max(5, ceilDbm - floorDbm);
      if (!row || row.width !== BINS) row = wctx.createImageData(BINS, 1);
      const bins = rfBus.bins;
      const data = row.data;
      for (let x = 0; x < BINS; x++) {
        const [r, g, b] = sampleMap(lift((bins[x] - floorDbm) / range), palette);
        const i = x * 4;
        data[i] = r;
        data[i + 1] = g;
        data[i + 2] = b;
        data[i + 3] = 255;
      }
      wctx.drawImage(wfc, 0, 0, BINS, HISTORY - 1, 0, 1, BINS, HISTORY - 1);
      wctx.putImageData(row, 0, 0);

      const dpr = Math.min(1.25, window.devicePixelRatio || 1);
      const cssW = spc.clientWidth || 320;
      const cssH = spc.clientHeight || 88;
      const tw = Math.floor(cssW * dpr);
      const th = Math.floor(cssH * dpr);
      if (spc.width !== tw || spc.height !== th) {
        spc.width = tw;
        spc.height = th;
      }
      sctx.setTransform(dpr, 0, 0, dpr, 0, 0);
      sctx.clearRect(0, 0, cssW, cssH);
      const ny = (v: number) => cssH - ((v - floorDbm) / range) * cssH;

      sctx.strokeStyle = "rgba(236, 238, 241, 0.06)";
      sctx.lineWidth = 1;
      for (const db of [-90, -70, -50, -30]) {
        if (db <= floorDbm || db >= ceilDbm) continue;
        const y = ny(db);
        sctx.beginPath();
        sctx.moveTo(0, y);
        sctx.lineTo(cssW, y);
        sctx.stroke();
      }
      sctx.beginPath();
      sctx.moveTo(cssW / 2, 0);
      sctx.lineTo(cssW / 2, cssH);
      sctx.strokeStyle = "rgba(142, 180, 173, 0.28)";
      sctx.stroke();

      sctx.beginPath();
      for (let i = 0; i < BINS; i++) {
        const x = (i / (BINS - 1)) * cssW;
        const y = ny(bins[i] ?? floorDbm);
        if (i === 0) sctx.moveTo(x, y);
        else sctx.lineTo(x, y);
      }
      if (!compact) {
        sctx.lineTo(cssW, cssH);
        sctx.lineTo(0, cssH);
        sctx.closePath();
        sctx.fillStyle = "rgba(142, 180, 173, 0.18)";
        sctx.fill();
        sctx.beginPath();
        for (let i = 0; i < BINS; i++) {
          const x = (i / (BINS - 1)) * cssW;
          const y = ny(bins[i] ?? floorDbm);
          if (i === 0) sctx.moveTo(x, y);
          else sctx.lineTo(x, y);
        }
      }
      sctx.strokeStyle = "rgba(142, 180, 173, 0.95)";
      sctx.lineWidth = 1.5;
      sctx.stroke();

      const peak = rfBus.peakHold;
      sctx.beginPath();
      for (let i = 0; i < BINS; i++) {
        const x = (i / (BINS - 1)) * cssW;
        const y = ny(peak[i] ?? floorDbm);
        if (i === 0) sctx.moveTo(x, y);
        else sctx.lineTo(x, y);
      }
      sctx.strokeStyle = "rgba(200, 204, 210, 0.45)";
      sctx.setLineDash([3, 4]);
      sctx.lineWidth = 1;
      sctx.stroke();
      sctx.setLineDash([]);
    };
    raf = requestAnimationFrame(paint);
    return () => {
      cancelAnimationFrame(raf);
      document.removeEventListener("visibilitychange", onVis);
    };
  }, [floorDbm, ceilDbm, palette, compact]);

  const lo = centerHz - spanHz / 2;
  const hi = centerHz + spanHz / 2;

  const hzAt = (clientX: number, target: HTMLElement) => {
    const rect = target.getBoundingClientRect();
    const t = Math.max(0, Math.min(1, (clientX - rect.left) / rect.width));
    return lo + t * spanHz;
  };

  return (
    <div className="rf-scope overflow-hidden rounded-lg bg-background" data-hot>
      <canvas ref={sp} className={compact ? "block h-16 w-full" : "block h-28 w-full"} />
      <canvas
        ref={wf}
        className={compact ? "block h-28 w-full" : "block h-52 w-full"}
        style={{ imageRendering: "pixelated" }}
        onPointerDown={(e) => {
          const hz = hzAt(e.clientX, e.currentTarget);
          setCursor(hz);
          onTune?.(hz);
        }}
        onPointerMove={(e) => {
          if (e.buttons === 0 && e.pointerType !== "touch") setCursor(hzAt(e.clientX, e.currentTarget));
        }}
        onPointerLeave={() => setCursor(null)}
      />
      <div className="flex justify-between px-2 py-1.5 font-mono text-xs tabular-nums text-muted">
        <span>{formatMhz(lo, 2)}</span>
        <span className="text-primary">
          {formatMhz(cursor ?? centerHz, 3)} MHz
          {cursor != null ? " · tap" : ""}
        </span>
        <span>{formatMhz(hi, 2)}</span>
      </div>
    </div>
  );
}
