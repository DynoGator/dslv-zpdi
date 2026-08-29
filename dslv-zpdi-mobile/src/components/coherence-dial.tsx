import { memo } from "react";
import { cn } from "@/lib/utils";

export const CoherenceDial = memo(function CoherenceDial({
  r,
  phases,
  className,
}: {
  r: number;
  phases: number[];
  className?: string;
}) {
  const cx = 80;
  const cy = 80;
  const rad = 54;
  const order = Math.max(0, Math.min(1, r));
  const sweep = order * 360;
  return (
    <div className={cn("relative", className)}>
      <svg viewBox="0 0 160 160" className="h-full w-full text-primary">
        <circle cx={cx} cy={cy} r={rad} fill="none" stroke="currentColor" strokeOpacity="0.18" strokeWidth="8" />
        <circle
          cx={cx}
          cy={cy}
          r={rad}
          fill="none"
          stroke="currentColor"
          strokeWidth="8"
          strokeLinecap="round"
          strokeDasharray={`${(sweep / 360) * 2 * Math.PI * rad} ${2 * Math.PI * rad}`}
          transform={`rotate(-90 ${cx} ${cy})`}
        />
        {phases.map((p, i) => {
          const x = Math.round((cx + Math.cos(p) * rad) * 100) / 100;
          const y = Math.round((cy + Math.sin(p) * rad) * 100) / 100;
          return (
            <circle
              key={i}
              cx={x}
              cy={y}
              r="3.2"
              fill="currentColor"
              opacity={Math.round((0.35 + order * 0.65) * 100) / 100}
            />
          );
        })}
        <circle cx={cx} cy={cy} r="3" fill="currentColor" />
      </svg>
      <div className="pointer-events-none absolute inset-0 flex flex-col items-center justify-center">
        <div className="font-mono text-2xl font-medium tabular-nums leading-none text-foreground">
          {order.toFixed(3)}
        </div>
        <div className="mt-1 text-[0.6875rem] uppercase tracking-[0.16em] text-muted">Γ r_global</div>
      </div>
    </div>
  );
});
