import type { CommandRecord, CommandState } from "./types";

export const PROTOCOL = "dslv-zpdi-c2/1";
export const ISSUER = "pixel-9-pro-xl";
export const TARGET = "alpha-pi-tier1";

function uuidv4() {
  const b = new Uint8Array(16);
  crypto.getRandomValues(b);
  b[6] = (b[6] & 0x0f) | 0x40;
  b[8] = (b[8] & 0x3f) | 0x80;
  const h = Array.from(b, (x) => x.toString(16).padStart(2, "0")).join("");
  return `${h.slice(0, 8)}-${h.slice(8, 12)}-${h.slice(12, 16)}-${h.slice(16, 20)}-${h.slice(20)}`;
}

function nonce() {
  const b = new Uint8Array(16);
  crypto.getRandomValues(b);
  let s = "";
  for (let i = 0; i < b.length; i++) s += String.fromCharCode(b[i]);
  return btoa(s);
}

export function makeEnvelope(capability: string, parameters: Record<string, unknown>) {
  const now = new Date();
  const exp = new Date(now.getTime() + 60_000);
  return {
    protocol: PROTOCOL,
    command_id: uuidv4(),
    idempotency_key: uuidv4(),
    issuer_node_id: ISSUER,
    target_node_id: TARGET,
    capability,
    issued_at: now.toISOString().replace(/\.\d{3}Z$/, "Z"),
    expires_at: exp.toISOString().replace(/\.\d{3}Z$/, "Z"),
    nonce: nonce(),
    parameters,
  };
}

export function toRecord(
  envelope: ReturnType<typeof makeEnvelope>,
  state: CommandState,
  result: string,
): CommandRecord {
  return {
    commandId: envelope.command_id,
    capability: envelope.capability,
    state,
    issuedAt: envelope.issued_at,
    parameters: envelope.parameters,
    result,
  };
}
