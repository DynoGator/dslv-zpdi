export function sci(n: number | null | undefined, sig = 3): string {
  if (n == null || !Number.isFinite(n)) return "—";
  const a = Math.abs(n);
  if (a !== 0 && (a < 1e-2 || a >= 1e4)) return n.toExponential(sig);
  const digits = a >= 100 ? 1 : a >= 10 ? 2 : sig;
  return n.toFixed(digits);
}

export function formatBaseline(m: number | null): string {
  if (m == null || !Number.isFinite(m)) return "not surveyed";
  if (m < 1000) return `${m.toFixed(m < 10 ? 2 : 1)} m`;
  return `${(m / 1000).toFixed(3)} km`;
}

export function formatSeconds(s: number | null): string {
  if (s == null || !Number.isFinite(s)) return "—";
  const a = Math.abs(s);
  if (a >= 1) return `${s.toFixed(3)} s`;
  if (a >= 1e-3) return `${(s * 1e3).toFixed(3)} ms`;
  if (a >= 1e-6) return `${(s * 1e6).toFixed(2)} µs`;
  return `${(s * 1e9).toFixed(1)} ns`;
}

export function formatRad(rad: number | null): string {
  if (rad == null || !Number.isFinite(rad)) return "—";
  const a = Math.abs(rad);
  if (a !== 0 && a < 0.01) return `${rad.toExponential(2)} rad`;
  return `${rad.toFixed(3)} rad`;
}

export function uid(): string {
  return crypto.randomUUID();
}

export function stamp(d = new Date()): string {
  return d.toISOString();
}
