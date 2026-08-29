import { BINS, HISTORY } from "./types";

type Listener = () => void;

const bins = new Float32Array(BINS);
const peakHold = new Float32Array(BINS).fill(-120);
const history: Float32Array[] = Array.from({ length: HISTORY }, () => new Float32Array(BINS).fill(-110));
let head = 0;
let frame = 0;
const listeners = new Set<Listener>();

function notify() {
  listeners.forEach((fn) => fn());
}

export const rfBus = {
  bins,
  peakHold,
  frame: () => frame,
  row(i: number) {
    return history[(head + i) % HISTORY];
  },
  push(src: Float32Array) {
    bins.set(src);
    head = (head + HISTORY - 1) % HISTORY;
    history[head].set(src);
    for (let i = 0; i < BINS; i++) {
      peakHold[i] = Math.max(src[i], peakHold[i] * 0.985 + src[i] * 0.015);
    }
    frame++;
    notify();
  },
  reset(floor = -120) {
    bins.fill(floor);
    peakHold.fill(floor);
    for (const row of history) row.fill(floor);
    frame++;
    notify();
  },
  subscribe(fn: Listener) {
    listeners.add(fn);
    return () => listeners.delete(fn);
  },
};
