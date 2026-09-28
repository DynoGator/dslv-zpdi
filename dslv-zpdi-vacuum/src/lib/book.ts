import { create } from "zustand";
import { useEffect, useState } from "react";
import { PREREG, STEPS } from "@/lib/metrology/protocol";
import { paperIdentityChecks, pathToPhaseRad, type ChainId } from "@/lib/metrology/physics";
import { stamp, uid } from "@/lib/metrology/format";

export type BudgetRow = {
  id: string;
  name: string;
  kind: "path-cm" | "phase-rad";
  value: string;
  basis: "catalog" | "measured";
  note: string;
  rss: boolean;
};

export type NodeRec = {
  id: string;
  name: string;
  gpsdo: string;
  sigmaY: string;
  fLoopHz: string;
  antenna: string;
  lat: string;
  lon: string;
  altM: string;
  accuracyM: string;
  fixSource: "" | "device" | "surveyed";
  fixAt: string;
};

export type LogKind =
  | "note"
  | "calibration"
  | "injection"
  | "analysis-a"
  | "analysis-b"
  | "chromatic"
  | "switch"
  | "freeze"
  | "amendment";

export type LogEntry = {
  id: string;
  at: string;
  kind: LogKind;
  title: string;
  body: string;
  chain?: ChainId | "";
};

export type Campaign = {
  id: string;
  name: string;
  operator: string;
  site: string;
  createdAt: string;
  stepId: string;
  acked: string[];
  fields: Record<string, string>;
  nodes: NodeRec[];
  budget: BudgetRow[];
  logs: LogEntry[];
  frozen: null | { at: string; sha256: string };
  amendments: { at: string; reason: string; previousSha: string }[];
};

type BookState = {
  campaigns: Campaign[];
  activeId: string | null;
  createCampaign: (input: { name: string; operator: string; site: string }) => string;
  select: (id: string) => void;
  remove: (id: string) => void;
  patch: (id: string, fn: (c: Campaign) => Campaign) => void;
  setField: (id: string, key: string, value: string) => boolean;
  ack: (id: string, stepId: string) => void;
  setStep: (id: string, stepId: string) => void;
  addNode: (id: string) => void;
  updateNode: (id: string, nodeId: string, patch: Partial<NodeRec>) => boolean;
  removeNode: (id: string, nodeId: string) => boolean;
  updateBudget: (id: string, rowId: string, patch: Partial<BudgetRow>) => boolean;
  addLog: (id: string, entry: Omit<LogEntry, "id" | "at"> & { at?: string }) => void;
  freeze: (id: string) => Promise<string | null>;
  amend: (id: string, reason: string) => void;
  importBook: (raw: unknown) => { ok: true; n: number } | { ok: false; error: string };
};

const KEY = "dslv-zpdi-vacuum-book-v1";

export function blankNode(): NodeRec {
  return {
    id: uid(),
    name: "",
    gpsdo: "",
    sigmaY: "",
    fLoopHz: "",
    antenna: "",
    lat: "",
    lon: "",
    altM: "",
    accuracyM: "",
    fixSource: "",
    fixAt: "",
  };
}

export function catalogBudget(): BudgetRow[] {
  return [
    {
      id: uid(),
      name: "Tropospheric wet delay",
      kind: "path-cm",
      value: "1",
      basis: "catalog",
      note: "Saastamoinen-class worked example, 1 cm at L1. Replace with the mapped residual you measured.",
      rss: true,
    },
    {
      id: uid(),
      name: "Multipath, low case",
      kind: "path-cm",
      value: "0.5",
      basis: "catalog",
      note: "0.5 cm specular floor used only for the low RSS. Not both multipath rows at once.",
      rss: false,
    },
    {
      id: uid(),
      name: "Multipath, high case",
      kind: "path-cm",
      value: "2",
      basis: "catalog",
      note: "2 cm. Use this or the low case in a single RSS, then quote the span.",
      rss: false,
    },
    {
      id: uid(),
      name: "Antenna PCV + cable + front end",
      kind: "phase-rad",
      value: "0.1",
      basis: "catalog",
      note: "Placeholder. Catalog values are not accepted. Excluded from the RSS until you mark it measured.",
      rss: false,
    },
    {
      id: uid(),
      name: "Thermal noise on the carrier",
      kind: "phase-rad",
      value: "0.001",
      basis: "catalog",
      note: "1 mrad, high-SNR broadcast carriers. Not the systematic floor.",
      rss: true,
    },
  ];
}

function emptyFields(): Record<string, string> {
  const fields: Record<string, string> = {};
  for (const f of PREREG) fields[f.id] = "";
  return fields;
}

export function makeCampaign(input: { name: string; operator: string; site: string }): Campaign {
  return {
    id: uid(),
    name: input.name.trim(),
    operator: input.operator.trim(),
    site: input.site.trim(),
    createdAt: stamp(),
    stepId: STEPS[0]!.id,
    acked: [],
    fields: emptyFields(),
    nodes: [],
    budget: catalogBudget(),
    logs: [],
    frozen: null,
    amendments: [],
  };
}

const LOCKED_WHEN_FROZEN = new Set(PREREG.map((f) => f.id));

export function canonical(c: Campaign): string {
  const payload = {
    rev: "3.4",
    app: "DSLV-ZPDI-Probing-The-Vacuum-Structure",
    name: c.name,
    operator: c.operator,
    site: c.site,
    createdAt: c.createdAt,
    nodes: c.nodes.map((n) => ({
      name: n.name,
      gpsdo: n.gpsdo,
      sigmaY: n.sigmaY,
      fLoopHz: n.fLoopHz,
      antenna: n.antenna,
      lat: n.lat,
      lon: n.lon,
      altM: n.altM,
      fixSource: n.fixSource,
    })),
    fields: c.fields,
    budget: c.budget.map((b) => ({
      name: b.name,
      kind: b.kind,
      value: b.value,
      basis: b.basis,
      rss: b.rss,
    })),
    acked: [...c.acked].sort(),
  };
  return JSON.stringify(payload);
}

export async function sha256(text: string): Promise<string> {
  const buf = await crypto.subtle.digest("SHA-256", new TextEncoder().encode(text));
  return [...new Uint8Array(buf)].map((b) => b.toString(16).padStart(2, "0")).join("");
}

function isNode(x: unknown): x is NodeRec {
  if (!x || typeof x !== "object") return false;
  const n = x as NodeRec;
  return typeof n.id === "string" && typeof n.name === "string";
}

function isLog(x: unknown): x is LogEntry {
  if (!x || typeof x !== "object") return false;
  const n = x as LogEntry;
  return typeof n.id === "string" && typeof n.title === "string" && typeof n.kind === "string";
}

function isBudget(x: unknown): x is BudgetRow {
  if (!x || typeof x !== "object") return false;
  const n = x as BudgetRow;
  return typeof n.id === "string" && typeof n.name === "string" && typeof n.value === "string";
}

export function isCampaign(x: unknown): x is Campaign {
  if (!x || typeof x !== "object") return false;
  const c = x as Campaign;
  return (
    typeof c.id === "string" &&
    typeof c.name === "string" &&
    c.fields != null &&
    typeof c.fields === "object" &&
    Array.isArray(c.nodes) &&
    c.nodes.every(isNode) &&
    Array.isArray(c.logs) &&
    c.logs.every(isLog) &&
    Array.isArray(c.budget) &&
    c.budget.every(isBudget)
  );
}

function normalize(c: Campaign): Campaign {
  const fields = emptyFields();
  for (const [k, v] of Object.entries(c.fields)) {
    if (typeof v === "string") fields[k] = v;
  }
  return {
    ...c,
    operator: c.operator ?? "",
    site: c.site ?? "",
    stepId: STEPS.some((s) => s.id === c.stepId) ? c.stepId : STEPS[0]!.id,
    acked: Array.isArray(c.acked) ? c.acked.filter((a) => typeof a === "string") : [],
    fields,
    amendments: Array.isArray(c.amendments) ? c.amendments : [],
    frozen: c.frozen && typeof c.frozen.sha256 === "string" ? c.frozen : null,
  };
}

export function preregComplete(c: Campaign): boolean {
  return PREREG.every((f) => {
    if (f.id === "clockFloorRad" || f.id === "biasHash") return true;
    return (c.fields[f.id] ?? "").trim().length > 0;
  });
}

export function clockReady(c: Campaign): boolean {
  return (c.fields.clockFloorRad ?? "").trim().length > 0 && (c.fields.biasHash ?? "").trim().length > 0;
}

export function nodesReady(c: Campaign): boolean {
  return (
    c.nodes.length >= 2 &&
    c.nodes.every((n) => n.name.trim() && n.gpsdo.trim() && n.sigmaY.trim() && n.fLoopHz.trim())
  );
}

export const useBook = create<BookState>((set, get) => ({
  campaigns: [],
  activeId: null,
  createCampaign: (input) => {
    const c = makeCampaign(input);
    set((s) => ({ campaigns: [c, ...s.campaigns], activeId: c.id }));
    return c.id;
  },
  select: (id) => set({ activeId: id }),
  remove: (id) =>
    set((s) => {
      const campaigns = s.campaigns.filter((c) => c.id !== id);
      const activeId = s.activeId === id ? (campaigns[0]?.id ?? null) : s.activeId;
      return { campaigns, activeId };
    }),
  patch: (id, fn) =>
    set((s) => ({
      campaigns: s.campaigns.map((c) => (c.id === id ? fn(c) : c)),
    })),
  setField: (id, key, value) => {
    const c = get().campaigns.find((x) => x.id === id);
    if (!c) return false;
    if (c.frozen && LOCKED_WHEN_FROZEN.has(key)) return false;
    get().patch(id, (cur) => ({ ...cur, fields: { ...cur.fields, [key]: value } }));
    return true;
  },
  ack: (id, stepId) =>
    get().patch(id, (c) => ({
      ...c,
      acked: c.acked.includes(stepId) ? c.acked : [...c.acked, stepId],
    })),
  setStep: (id, stepId) => get().patch(id, (c) => ({ ...c, stepId })),
  addNode: (id) => {
    const c = get().campaigns.find((x) => x.id === id);
    if (!c || c.frozen) return;
    get().patch(id, (cur) => ({ ...cur, nodes: [...cur.nodes, blankNode()] }));
  },
  updateNode: (id, nodeId, patch) => {
    const c = get().campaigns.find((x) => x.id === id);
    if (!c || c.frozen) return false;
    get().patch(id, (cur) => ({
      ...cur,
      nodes: cur.nodes.map((n) => (n.id === nodeId ? { ...n, ...patch } : n)),
    }));
    return true;
  },
  removeNode: (id, nodeId) => {
    const c = get().campaigns.find((x) => x.id === id);
    if (!c || c.frozen) return false;
    get().patch(id, (cur) => ({ ...cur, nodes: cur.nodes.filter((n) => n.id !== nodeId) }));
    return true;
  },
  updateBudget: (id, rowId, patch) => {
    const c = get().campaigns.find((x) => x.id === id);
    if (!c || c.frozen) return false;
    get().patch(id, (cur) => ({
      ...cur,
      budget: cur.budget.map((r) => (r.id === rowId ? { ...r, ...patch } : r)),
    }));
    return true;
  },
  addLog: (id, entry) =>
    get().patch(id, (c) => ({
      ...c,
      logs: [{ ...entry, id: uid(), at: entry.at ?? stamp(), chain: entry.chain ?? "" }, ...c.logs],
    })),
  freeze: async (id) => {
    const c = get().campaigns.find((x) => x.id === id);
    if (!c || c.frozen) return null;
    if (!preregComplete(c) || !nodesReady(c) || !clockReady(c)) return null;
    const digest = await sha256(canonical(c));
    const at = stamp();
    get().patch(id, (cur) => ({
      ...cur,
      frozen: { at, sha256: digest },
      logs: [
        {
          id: uid(),
          at,
          kind: "freeze",
          title: "Registry frozen",
          body: digest,
          chain: "",
        },
        ...cur.logs,
      ],
    }));
    return digest;
  },
  amend: (id, reason) => {
    const c = get().campaigns.find((x) => x.id === id);
    if (!c?.frozen) return;
    const previousSha = c.frozen.sha256;
    const at = stamp();
    get().patch(id, (cur) => ({
      ...cur,
      frozen: null,
      amendments: [...cur.amendments, { at, reason: reason.trim(), previousSha }],
      logs: [
        {
          id: uid(),
          at,
          kind: "amendment",
          title: "Registry amended",
          body: `${reason.trim()} Previous ${previousSha}`,
          chain: "",
        },
        ...cur.logs,
      ],
    }));
  },
  importBook: (raw) => {
    const body = raw as { campaigns?: unknown; campaign?: unknown };
    const list = Array.isArray(raw)
      ? raw
      : Array.isArray(body?.campaigns)
        ? body.campaigns
        : body?.campaign
          ? [body.campaign]
          : null;
    if (!list) return { ok: false, error: "That file is not a campaign book." };
    const campaigns = list.filter(isCampaign).map(normalize);
    if (!campaigns.length) return { ok: false, error: "No campaign records in that file." };
    set((s) => {
      const ids = new Set(s.campaigns.map((c) => c.id));
      const fresh = campaigns.map((c) => (ids.has(c.id) ? { ...c, id: uid() } : c));
      return { campaigns: [...fresh, ...s.campaigns], activeId: fresh[0]!.id };
    });
    return { ok: true, n: campaigns.length };
  },
}));

let started = false;

export function useHydrateBook(): boolean {
  const [ready, setReady] = useState(started);
  useEffect(() => {
    if (started) {
      setReady(true);
      return;
    }
    started = true;
    try {
      const raw = localStorage.getItem(KEY);
      if (raw) {
        const parsed = JSON.parse(raw) as { campaigns?: unknown; activeId?: unknown };
        const campaigns = Array.isArray(parsed.campaigns)
          ? parsed.campaigns.filter(isCampaign).map(normalize)
          : [];
        const activeId =
          typeof parsed.activeId === "string" && campaigns.some((c) => c.id === parsed.activeId)
            ? parsed.activeId
            : (campaigns[0]?.id ?? null);
        useBook.setState({ campaigns, activeId });
      }
    } catch {
      /* corrupt book — start empty rather than invent a campaign */
    }
    useBook.subscribe((s) => {
      localStorage.setItem(KEY, JSON.stringify({ campaigns: s.campaigns, activeId: s.activeId }));
    });
    setReady(true);
  }, []);
  return ready;
}

export function useActive(): Campaign | null {
  return useBook((s) => s.campaigns.find((c) => c.id === s.activeId) ?? null);
}

export function rowRad(row: BudgetRow): number | null {
  const v = Number(row.value);
  if (!Number.isFinite(v)) return null;
  if (row.kind === "path-cm") return pathToPhaseRad(v / 100, 154 * 10.23e6);
  return v;
}

export function identityPassCount(): { pass: number; total: number } {
  const rows = paperIdentityChecks();
  return { pass: rows.filter((r) => r.pass).length, total: rows.length };
}
