import { Link, useRouterState } from "@tanstack/react-router";
import {
  BookOpen,
  Compass,
  FlaskConical,
  Radio,
  Shield,
} from "lucide-react";
import type { ReactNode } from "react";
import { useBook, useHydrateBook } from "@/lib/book";

const NAV = [
  { to: "/", label: "Deck", icon: Radio },
  { to: "/walk", label: "Walk", icon: Compass },
  { to: "/bench", label: "Bench", icon: FlaskConical },
  { to: "/book", label: "Book", icon: BookOpen },
  { to: "/doctrine", label: "Switches", icon: Shield },
] as const;

export function Shell({ children }: { children: ReactNode }) {
  useHydrateBook();
  const path = useRouterState({ select: (s) => s.location.pathname });
  const campaigns = useBook((s) => s.campaigns);
  const activeId = useBook((s) => s.activeId);
  const select = useBook((s) => s.select);

  return (
    <div className="app-grid min-h-dvh text-foreground">
      <header className="shell-top sticky top-0 z-20 border-b border-border bg-background/95 backdrop-blur-sm">
        <div className="mx-auto flex max-w-3xl items-center gap-3 px-4 py-3">
          <img src="/favicon.svg" alt="" className="h-9 w-9 shrink-0" />
          <div className="min-w-0 flex-1">
            <div className="kicker">DSLV-ZPDI</div>
            <div className="truncate text-sm font-semibold">Probing the Vacuum Structure</div>
          </div>
          {campaigns.length > 0 && (
            <label className="sr-only" htmlFor="campaign-select">
              Active campaign
            </label>
          )}
          {campaigns.length > 0 && (
            <select
              id="campaign-select"
              className="select max-w-40 truncate"
              value={activeId ?? ""}
              onChange={(e) => select(e.target.value)}
            >
              {campaigns.map((c) => (
                <option key={c.id} value={c.id}>
                  {c.name}
                </option>
              ))}
            </select>
          )}
        </div>
      </header>
      <main className="mx-auto w-full max-w-3xl px-4 pb-28 pt-4">{children}</main>
      <nav className="shell-nav fixed inset-x-0 bottom-0 z-20 border-t border-border bg-background/95 backdrop-blur-sm">
        <ul className="mx-auto grid max-w-3xl grid-cols-5">
          {NAV.map((item) => {
            const on = item.to === "/" ? path === "/" : path.startsWith(item.to);
            const Icon = item.icon;
            return (
              <li key={item.to}>
                <Link
                  to={item.to}
                  className={`flex min-h-14 flex-col items-center justify-center gap-1 text-xs ${on ? "text-primary" : "text-muted"}`}
                >
                  <Icon size={18} aria-hidden />
                  {item.label}
                </Link>
              </li>
            );
          })}
        </ul>
      </nav>
    </div>
  );
}

export function Plate({
  src,
  alt,
  caption,
}: {
  src: string;
  alt: string;
  caption: string;
}) {
  return (
    <figure className="card overflow-hidden">
      <img src={src} alt={alt} className="aspect-video w-full object-cover" />
      <figcaption className="px-3 py-2 text-xs text-muted">{caption}</figcaption>
    </figure>
  );
}

export function Tag({
  children,
  tone = "sage",
}: {
  children: ReactNode;
  tone?: "sage" | "hot" | "warn" | "ok" | "steel";
}) {
  const color =
    tone === "hot"
      ? "text-hot"
      : tone === "warn"
        ? "text-warn"
        : tone === "ok"
          ? "text-ok"
          : tone === "steel"
            ? "text-accent"
            : "text-primary";
  return (
    <span className={`font-mono text-xs tracking-wide uppercase ${color}`}>{children}</span>
  );
}

export function Readout({
  label,
  value,
  unit,
  hint,
}: {
  label: string;
  value: string;
  unit?: string;
  hint?: string;
}) {
  return (
    <div className="rounded-md border border-border bg-elevated px-3 py-3">
      <div className="text-xs text-muted">{label}</div>
      <div className="tabular mt-1 font-mono text-xl text-foreground">
        {value}
        {unit ? <span className="ml-1 text-sm text-muted">{unit}</span> : null}
      </div>
      {hint ? <p className="mt-1 text-xs text-subtle">{hint}</p> : null}
    </div>
  );
}

export function Field({
  label,
  hint,
  children,
}: {
  label: string;
  hint?: string;
  children: ReactNode;
}) {
  return (
    <label className="block">
      <span className="mb-1 block text-sm text-foreground">{label}</span>
      {children}
      {hint ? <span className="mt-1 block text-xs text-muted">{hint}</span> : null}
    </label>
  );
}

export function NeedCampaign() {
  return (
    <div className="card p-4">
      <h1 className="text-xl font-semibold">No campaign is open</h1>
      <p className="mt-2 text-sm text-muted">
        The book starts empty. Open a campaign on the deck, then walk the registry. Nothing is
        simulated in the meantime.
      </p>
      <Link to="/" className="btn btn-primary mt-4">
        Open the deck
      </Link>
    </div>
  );
}
