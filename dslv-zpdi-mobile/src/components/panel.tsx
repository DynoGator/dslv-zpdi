import type { ReactNode } from "react";
import { cn } from "@/lib/utils";

export function Panel({
  title,
  action,
  children,
  className,
}: {
  title: string;
  action?: ReactNode;
  children: ReactNode;
  className?: string;
}) {
  return (
    <section
      className={cn(
        "panel-cv rounded-xl bg-card p-4 shadow-[var(--shadow-border)]",
        className,
      )}
    >
      <header className="mb-3 flex items-center justify-between gap-3">
        <h2 className="text-xs font-medium uppercase tracking-[0.16em] text-muted">{title}</h2>
        {action}
      </header>
      {children}
    </section>
  );
}

export function Row({
  label,
  value,
  tone = "default",
}: {
  label: string;
  value: ReactNode;
  tone?: "default" | "ok" | "warn" | "danger" | "primary";
}) {
  const toneClass =
    tone === "ok"
      ? "text-ok"
      : tone === "warn"
        ? "text-warn"
        : tone === "danger"
          ? "text-danger"
          : tone === "primary"
            ? "text-primary"
            : "text-foreground";
  return (
    <div className="flex items-baseline justify-between gap-3 py-1.5">
      <span className="font-mono text-xs text-muted">{label}</span>
      <span className={cn("font-mono text-sm tabular-nums", toneClass)}>{value}</span>
    </div>
  );
}

export function Pill({
  children,
  tone = "default",
}: {
  children: ReactNode;
  tone?: "default" | "ok" | "warn" | "danger" | "primary";
}) {
  const cls =
    tone === "ok"
      ? "text-ok bg-ok/10"
      : tone === "warn"
        ? "text-warn bg-warn/10"
        : tone === "danger"
          ? "text-danger bg-danger/10"
          : tone === "primary"
            ? "text-primary bg-primary/10"
            : "text-muted bg-elevated";
  return (
    <span className={cn("inline-flex h-6 items-center rounded-full px-2.5 font-mono text-[0.6875rem] font-medium uppercase tracking-wide", cls)}>
      {children}
    </span>
  );
}

export function Metric({
  label,
  value,
  unit,
  tone = "default",
}: {
  label: string;
  value: string;
  unit?: string;
  tone?: "default" | "ok" | "warn" | "danger" | "primary";
}) {
  const toneClass =
    tone === "ok"
      ? "text-ok"
      : tone === "warn"
        ? "text-warn"
        : tone === "danger"
          ? "text-danger"
          : tone === "primary"
            ? "text-primary"
            : "text-foreground";
  return (
    <div className="rounded-lg bg-elevated px-3 py-3">
      <div className="text-[0.6875rem] uppercase tracking-[0.14em] text-muted">{label}</div>
      <div className={cn("mt-1 font-mono text-xl font-medium tabular-nums leading-none", toneClass)}>
        {value}
        {unit ? <span className="ml-1 text-xs font-normal text-muted">{unit}</span> : null}
      </div>
    </div>
  );
}
