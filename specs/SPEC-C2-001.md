# SPEC-C2-001 / SPEC-022 — DSLV-ZPDI Node Control Plane Protocol

**Status:** Draft  
**Version:** 1.0  
**Date:** 2026-07-25  
**Authority:** Pixel 9 Pro XL Tier-2 C2 Control Node feature track  
**Canonical SPEC-ID:** SPEC-022  

---

## 1. Purpose

Define a secure, authenticated, capability-based command and control (C2) protocol for operating DSLV-ZPDI nodes in the field. The protocol lets an authorized control node (e.g., the Pixel 9 Pro XL) issue typed, audited, expiring commands to other nodes (Tier-1 anchor, Tier-2/3 edge nodes) without granting arbitrary remote shell or arbitrary-code execution.

---

## 2. Scope

- Applies to control traffic between the Pixel C2 node and any enrolled swarm node.
- Commands are limited to a fixed capability registry; no free-form shell strings.
- Transport is initially HTTPS/WSS over the local mesh LAN; future revisions require mTLS.
- The Pi 5 remains the canonical Tier-1 timing/SDR/HDF5 authority; the C2 plane cannot override that.

---

## 3. Protocol identity

| Field | Value |
|-------|-------|
| Protocol name | `dslv-zpdi-c2` |
| Version | `1` |
| Content-Type | `application/json` |
| Default control port | `8444` (local); configurable per node |

---

## 4. Transport and binding

### 4.1 Current phase
- Bind to `127.0.0.1` on the control node for the local dashboard.
- Node-to-node control uses HTTPS over the mesh LAN with Bearer-token authentication.
- All C2 listeners MUST be behind authentication; unauthenticated endpoints are limited to `/health`.

### 4.2 Target phase
- mTLS with per-node X.509 identities issued by a field CA.
- WebSocket control channel for asynchronous command status and push events.
- Certificate pinning for offline field operation.

---

## 5. Authentication

### 5.1 Bearer token (current)
- Token is a high-entropy random string (≥256 bits).
- Stored in `/root/.config/dslv-zpdi/c2_token` with mode `600`.
- Transmitted in `Authorization: Bearer <token>` header.
- Token rotation MUST be supported without restarting the pipeline.

### 5.2 mTLS (target)
- Each node has an Ed25519/X.509 identity.
- Mutual TLS handshake proves node identity.
- Authorization layer maps identity → capabilities.

---

## 6. Authorization model

### 6.1 Capabilities
Capabilities are fine-grained strings. A node may hold one or more capabilities.

Initial registry:

| Capability | Description | Target scope |
|------------|-------------|--------------|
| `node.status.read` | Read node health and role | any node |
| `pipeline.status.read` | Read pipeline state | any node |
| `pipeline.start` | Start the main pipeline | Tier-1, anchor |
| `pipeline.stop` | Stop the main pipeline | Tier-1, anchor |
| `pipeline.rotate_output` | Rotate HDF5/JSONL output files | Tier-1, anchor |
| `sdr.status.read` | Read SDR device state | Tier-1 |
| `sdr.mode.set` | Set SDR mode (real/simulated/offline) | Tier-1 |
| `sdr.center_frequency.set` | Set SDR center frequency | Tier-1 |
| `sdr.sample_rate.set` | Set SDR sample rate | Tier-1 |
| `sdr.gain.set` | Set SDR gain | Tier-1 |
| `baseline.reset` | Request baseline reset | Tier-1, anchor |
| `hdf5.summary.read` | Read local HDF5 file summary | any node |
| `hdf5.segment.export` | Export a bounded telemetry segment | Tier-1, anchor |

### 6.2 Capability assignment
- Default control node (`tier2-c2-master`) holds all capabilities for field operations.
- Tier-1 anchor holds capabilities that affect timing/SDR/HDF5.
- Tier-2/3 nodes hold only `node.status.read`, `pipeline.status.read`, and `hdf5.summary.read`.

---

## 7. Command envelope

```json
{
  "protocol": "dslv-zpdi-c2/1",
  "command_id": "018fb...",
  "idempotency_key": "018fb...",
  "issuer_node_id": "pixel-control-01",
  "target_node_id": "tier1-anchor-01",
  "capability": "sdr.center_frequency.set",
  "issued_at": "2026-07-25T18:00:00Z",
  "expires_at": "2026-07-25T18:01:00Z",
  "nonce": "base64...",
  "parameters": {
    "hz": 144390000
  },
  "signature": "base64..."
}
```

### 7.1 Field requirements

| Field | Required | Constraints |
|-------|----------|-------------|
| `protocol` | yes | Must equal `dslv-zpdi-c2/1` |
| `command_id` | yes | UUID v4, unique per command |
| `idempotency_key` | yes | UUID v4; duplicate keys within 24h rejected |
| `issuer_node_id` | yes | Must match authenticated identity |
| `target_node_id` | yes | Must match local node or broadcast `*` |
| `capability` | yes | Must be in registry and authorized |
| `issued_at` | yes | ISO 8601; not in the future by more than 5s |
| `expires_at` | yes | ISO 8601; must be after `issued_at` and ≤ 5 minutes later |
| `nonce` | yes | ≥ 16 bytes base64, unique per command |
| `parameters` | yes | Dict; schema validated per capability |
| `signature` | no | Required once mTLS/HMAC is enabled |

---

## 8. Command lifecycle

```
REQUESTED
  ↓ auth + capability check
AUTHENTICATED
  ↓ parameter validation + idempotency check
ACCEPTED
  ↓ dispatch to adapter
EXECUTING
  ↓ adapter completes
COMPLETED | FAILED | EXPIRED | CANCELLED | UNAUTHORIZED
```

- `ACCEPTED` means the command is enqueued; it has not started executing.
- `EXECUTING` means the adapter is actively performing the operation.
- `FAILED` includes validation errors, adapter exceptions, and out-of-range parameters.
- `EXPIRED` means the command reached `expires_at` before completion.
- `CANCELLED` means an operator or controller explicitly revoked it.
- `UNAUTHORIZED` means the issuer lacked the capability.

---

## 9. Capability parameter schemas

### `sdr.center_frequency.set`
```json
{"hz": 144390000}
```
- `hz`: integer, 1 MHz ≤ hz ≤ 6 GHz.

### `sdr.mode.set`
```json
{"mode": "real"}
```
- `mode`: enum `real`, `simulated`, `offline`.

### `sdr.sample_rate.set`
```json
{"sample_rate_hz": 10000000}
```
- Must be a rate supported by the SDR HAL.

### `sdr.gain.set`
```json
{"gain_db": 62.0}
```
- Must be within device-specific bounds.

### `baseline.reset`
```json
{"mode": "soft"}
```
- `mode`: enum `soft`, `hard` (hard requires confirmation capability).

---

## 10. API endpoints

### `POST /api/v1/command`
Submit a new command.

**Request headers:**
- `Authorization: Bearer <token>`
- `Content-Type: application/json`

**Responses:**
- `202 Accepted` — command accepted, returns `{command_id, state}`
- `400 Bad Request` — malformed envelope or parameters
- `401 Unauthorized` — missing/invalid token
- `403 Forbidden` — capability not authorized
- `409 Conflict` — duplicate idempotency key

### `GET /api/v1/command/<command_id>`
Query command state and result.

**Responses:**
- `200 OK` — `{command_id, state, result, audit_log_id}`
- `404 Not Found` — unknown command

### `GET /api/v1/status`
Read control node status (public).

### `GET /health`
Health check (public).

---

## 11. Audit logging

Every command MUST produce an immutable audit record:

```json
{
  "audit_log_id": "uuid",
  "command_id": "uuid",
  "idempotency_key": "uuid",
  "issuer_node_id": "...",
  "target_node_id": "...",
  "capability": "...",
  "parameters": {...},
  "state_transitions": [
    {"state": "ACCEPTED", "ts": "..."},
    {"state": "EXECUTING", "ts": "..."},
    {"state": "COMPLETED", "ts": "..."}
  ],
  "result": {...},
  "client_ip": "...",
  "user_agent": "..."
}
```

Audit logs are appended to `/root/dslv-zpdi-local/logs/c2_audit.jsonl` with mode `600`.

---

## 12. Security requirements

1. Reject any command with `expires_at` in the past or more than 5 minutes in the future.
2. Reject duplicate `idempotency_key` within a 24-hour window.
3. Reject commands whose `issuer_node_id` does not match the authenticated identity.
4. Validate all parameters against capability-specific schemas; never pass raw user input to shell or subprocess.
5. Log every command attempt, successful or not.
6. Cap audit log size; rotate at 100 MB.
7. Bind control plane to localhost by default; expose to LAN only when mTLS is active.

---

## 13. Future work

- mTLS node identities and field CA.
- HMAC-SHA256 command signatures for non-mTLS deployments.
- Command batching and transaction semantics.
- Encrypted audit log shipping to Tier-1 anchor.
- Federation: multiple control nodes with leadership lease.
