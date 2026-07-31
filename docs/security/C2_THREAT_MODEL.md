# C2 Threat Model — DSLV-ZPDI Node Control Plane

**Status:** Draft  
**Version:** 1.0  
**Date:** 2026-07-25  
**Scope:** Pixel 9 Pro XL Tier-2 C2 control node and enrolled swarm nodes

---

## 1. Assets

| Asset | Value | Location |
|-------|-------|----------|
| Node identity / credentials | Authenticate commands and telemetry | `/root/.config/dslv-zpdi/` |
| C2 bearer token | Authorizes control-plane commands | `/root/.config/dslv-zpdi/c2_token` |
| GitHub PAT | Repository access | `/root/.config/dslv-zpdi/github_pat` |
| HDF5 telemetry data | Field measurement records | Tier-1 anchor / local read cache |
| Command audit logs | Non-repudiation and incident response | `/root/dslv-zpdi-local/logs/c2_audit.jsonl` |
| SDR configuration | Defines active frequency, gain, mode | Tier-1 anchor runtime state |
| Pipeline availability | Continuous metrology acquisition | Tier-1 anchor process |
| Operator trust | Confidence in field command center | Pixel dashboard and APK |

---

## 2. Threat actors

| Actor | Capability | Motive |
|-------|------------|--------|
| Network eavesdropper | Passive LAN / hotspot observer | Reconnaissance, credential theft |
| Malicious mesh node | Valid network access, no valid identity | Lateral movement, command injection |
| Compromised Pixel / C2 node | Stolen bearer token or API keys | Unauthorized commands, data exfiltration |
| Insider operator | Legitimate dashboard access | Intentional or accidental destructive commands |
| Supply-chain attacker | Modified APK, agent installer, dependency | Persistent compromise |
| Physical attacker | Device theft, forensic extraction | Credential and data extraction |

---

## 3. Attack surface

### 3.1 Network
- LocalOnlyHotspot / mesh Wi-Fi LAN.
- HTTP control endpoints on `127.0.0.1` (local) and LAN (future mTLS).
- WebSocket ingestion and telemetry channels.
- mDNS/DNS-SD service advertisement.

### 3.2 Host
- Termux host scripts (`~/.termux/boot/`).
- Debian proot environment.
- Running C2 server, HDF5 adapter, dashboard.
- Agent credentials and configuration files.

### 3.3 Application
- Native Android APK (future).
- Local dashboard UI.
- CLI agent tools and their credential stores.

### 3.4 Process / human
- Operator authentication to dashboard/agents.
- GitHub PAT handling.
- Field device provisioning.

---

## 4. Trust boundaries

```
[Operator] --(local UI / APK)--> [C2 Server on Pixel] --(authenticated C2)--> [Tier-1 Anchor]
                                          |
                                          +--(read-only)--> [HDF5 Query Adapter]
                                          |
                                          +--(local telemetry)--> [Tier-2 Producer]
```

- The APK and local dashboard run on the same device as the C2 server: high trust.
- Node-to-node control crosses the hotspot LAN: medium trust, requires auth.
- Tier-1 anchor accepts commands only from authorized control identities: high trust.
- GitHub / cloud services are not in the operational data path: out of scope for runtime C2.

---

## 5. Threats and mitigations

| ID | Threat | Impact | Mitigation | Status |
|----|--------|--------|------------|--------|
| T1 | Eavesdropper reads C2 traffic | Command and telemetry disclosure | HTTPS/WSS with mTLS in target phase; bearer tokens over TLS in current phase | planned |
| T2 | Replay of captured command | Unauthorized state change | Idempotency keys, nonces, expiry, command lifecycle | implemented |
| T3 | Unauthorized node issues commands | Lateral movement | Bearer-token auth + capability authorization | implemented |
| T4 | Compromised token used remotely | Full C2 takeover | Token rotation, localhost binding by default, audit logging | partial |
| T5 | Command parameter injection / shell escape | Remote code execution | Typed capability schemas, no shell passthrough, range validation | implemented |
| T6 | Malformed envelope crashes server | Denial of service | Strict validation, exception handling, rate limiting | implemented |
| T7 | Audit log tampering | Loss of non-repudiation | Mode-600 files, append-only, rotation, future signed logs | partial |
| T8 | Operator accidentally stops pipeline | Loss of acquisition | Capability separation, destructive-command confirmation | planned |
| T9 | APK contains malicious code | Complete device compromise | Reproducible builds, signed APKs, GitHub checksums | planned |
| T10 | Physical device theft | Credential and data extraction | GrapheneOS encryption, keystore, short-lived tokens | planned |

---

## 6. Security requirements

1. **Authentication:** Every C2 command MUST carry a valid bearer token or mTLS identity.
2. **Authorization:** Capabilities MUST be checked before dispatch; default-deny.
3. **Integrity:** Commands MUST include nonce, expiry, and idempotency key.
4. **Non-repudiation:** Every attempt MUST be appended to the audit log.
5. **Least privilege:** The Pixel C2 node holds broad capabilities only in the field; unattended Tier-1 acquisition must not depend on it.
6. **No arbitrary execution:** Adapters MUST call typed Python APIs, never `shell=True` or `eval`.
7. **Fail closed:** Missing or invalid credentials MUST prevent startup in production mode.
8. **Local-first:** Dashboard and C2 server bind to `127.0.0.1` by default.

---

## 7. Acceptance criteria

- [ ] Replay of a previously accepted command is rejected.
- [ ] Expired commands are rejected without execution.
- [ ] Commands outside authorized capabilities return `403 Forbidden`.
- [ ] Invalid parameters return `400 Bad Request` before adapter invocation.
- [ ] Audit log contains every attempt with original envelope and result.
- [ ] Server fails to start when `c2_token` is missing or empty in production mode.
- [ ] No shell command strings are accepted in C2 endpoints.

---

## 8. Open risks

- mTLS and field CA are not yet implemented; bearer tokens are single-point-of-failure.
- The APK is not yet built; the local dashboard is the only control surface.
- LocalOnlyHotspot credentials are auto-generated and must be distributed out-of-band.
- Token rotation is manual in current phase.
- No formal penetration test has been performed.

---

## 9. References

- `specs/SPEC-C2-001.md` — Control-plane protocol specification.
- `src/dslv_zpdi/control/protocol.py` — Envelope and lifecycle implementation.
- `src/dslv_zpdi/control/authorization.py` — Capability and token authorization.
- `src/dslv_zpdi/control/audit.py` — Audit logging.
