import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

export function clamp(n: number, min: number, max: number) {
  return Math.min(max, Math.max(min, n));
}

export function formatMhz(hz: number, digits = 3) {
  return `${(hz / 1e6).toFixed(digits)}`;
}

export function formatHz(hz: number) {
  if (hz >= 1e9) return `${(hz / 1e9).toFixed(3)} GHz`;
  if (hz >= 1e6) return `${(hz / 1e6).toFixed(3)} MHz`;
  if (hz >= 1e3) return `${(hz / 1e3).toFixed(1)} kHz`;
  return `${hz.toFixed(0)} Hz`;
}

export function formatNs(ns: number) {
  if (ns >= 1000) return `${(ns / 1000).toFixed(2)} µs`;
  return `${ns.toFixed(1)} ns`;
}

export function pad2(n: number) {
  return n.toString().padStart(2, "0");
}

export function utcStamp(ms = Date.now()) {
  const d = new Date(ms);
  return `${d.getUTCFullYear()}-${pad2(d.getUTCMonth() + 1)}-${pad2(d.getUTCDate())} ${pad2(d.getUTCHours())}:${pad2(d.getUTCMinutes())}:${pad2(d.getUTCSeconds())}.${Math.floor(d.getUTCMilliseconds() / 10)
    .toString()
    .padStart(2, "0")}Z`;
}

export function shortHash(s: string, n = 12) {
  return s.slice(0, n);
}
