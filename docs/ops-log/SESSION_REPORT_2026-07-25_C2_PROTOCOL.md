# DSLV-ZPDI Session Report — C2 Control-Plane Protocol Implementation

**Session date:** 2026-07-25  
**Device:** Google Pixel 9 Pro XL (GrapheneOS) via Debian proot-distro in Termux  
**Repo:** `/root/dslv-zpdi` @ `c0af49f561a492a336f6c006b6cc2da4a39f78b1`  
**Session owner:** Kimi Code (main agent)  
**Objective:** Complete the first development step: formalize the C2 control-plane protocol, implement the canonical control package, refactor the local C2 server to use it, add tests, and verify the overlay services still work.

---

## 1. Work performed

### 1.1 Specification and threat model

| Artifact | Path | Purpose |
|----------|------|---------|
| Control-plane protocol spec | `specs/SPEC-C2-001.md` | Defines `dslv-zpdi-c2/1` protocol, envelope, lifecycle, capabilities, API endpoints, audit format, and security requirements. Tagged with canonical `SPEC-022`. |
| Threat model | `docs/security/C2_THREAT_MODEL.md` | Assets, threat actors, attack surface, trust boundaries, mitigations, acceptance criteria, and open risks. |

### 1.2 Canonical control package (new, additive, in main repo)

Created `src/dslv_zpdi/control/`:

| File | Responsibility |
|------|----------------|
| `__init__.py` | Public exports. |
| `protocol.py` | `CommandEnvelope`, `CommandState`, `CapabilityRegistry`, validation, idempotency, expiry, nonce checks, parameter schemas. |
| `authorization.py` | `CapabilityStore`, role-based capability assignment, `authorize()` helper. |
| `audit.py` | Thread-safe append-only JSONL audit logger with rotation. |

All modules cite `SPEC-022` and pass the repo `orphan_checker.py` guard.

### 1.3 Local overlay updates (outside main repo)

| File | Change |
|------|--------|
| `control_plane/c2_server.py` | Refactored to import and use `dslv_zpdi.control`. Accepts SPEC-C2-001 envelopes as primary; retains a normalization shim for legacy shorthand (`issuer`/`target`/`params`/unix timestamps). Adds command lifecycle, audit logging, and role-based authorization for localhost callers. |
| `dashboard_ui/index.html` | Updated to send `Authorization: Bearer` header and construct SPEC-C2-001 envelopes with ISO timestamps, UUIDs, and nonces. |
| `scripts/self_check.sh` | Updated authenticated command test to use proper UUID v4 command/idempotency keys and SPEC-C2-001 envelope. |

### 1.4 Tests

Added `tests/test_control_protocol.py` with 23 test cases covering:

- Valid command acceptance
- Unknown capability rejection
- Missing/invalid protocol rejection
- Expired command rejection
- TTL-too-long rejection
- Future `issued_at` rejection
- Duplicate idempotency-key rejection
- Invalid/wrong target rejection
- Broadcast target (`*`) acceptance
- Invalid UUID rejection
- Short/malformed nonce rejection
- Parameter-object validation
- SDR frequency, mode, and baseline-reset parameter validation
- Capability registry membership
- Command `to_dict()` round-trip
- `is_expired()` behavior
- Authorization allowed/denied paths
- Audit logger record generation

### 1.5 Validation and verification

- Full repo validation: **207 passed, 1 skipped** (was 184/1 before adding control tests).
- `ruff check src/ tools/ tests/`: clean.
- `mypy src/dslv_zpdi/layer2_core`: clean.
- `orphan_checker.py`: clean.
- `repo_guard.py`: clean.
- `git diff --check`: clean.
- C2 overlay self-check: **all checks passed**.
- C2 server, HDF5 query adapter, and dashboard UI server are running and responding.

---

## 2. Changelog

### Added
- `specs/SPEC-C2-001.md` — C2 control-plane protocol specification (`SPEC-022`).
- `docs/security/C2_THREAT_MODEL.md` — threat model and security acceptance criteria.
- `src/dslv_zpdi/control/__init__.py`
- `src/dslv_zpdi/control/protocol.py`
- `src/dslv_zpdi/control/authorization.py`
- `src/dslv_zpdi/control/audit.py`
- `tests/test_control_protocol.py`

### Changed
- `dslv-zpdi-local/control_plane/c2_server.py` — rewired to use canonical `dslv_zpdi.control` package; added audit logging and role selection.
- `dslv-zpdi-local/dashboard_ui/index.html` — now sends Bearer auth and SPEC-C2-001 envelopes.
- `dslv-zpdi-local/scripts/self_check.sh` — authenticated command test uses spec-compliant UUIDs and envelope.

### Fixed
- C2 server previously accepted legacy shorthand only; now validates full protocol envelope.
- Dashboard previously omitted Bearer token on command POSTs; now includes it.
- Self-check previously used non-UUID command IDs that the spec rejects.

---

## 3. Known state after this session

### Running services (verified)
- `c2_server.py` on `127.0.0.1:8444` — **running**, auth configured.
- `hdf5_query_adapter.py` on `127.0.0.1:8445` — **running**.
- Dashboard file server on `127.0.0.1:8085` — **running**.
- Main pipeline (`supervisor.sh`) with `tier1_ingestion_server.py`, `zpdi_mobile_node.py`, and existing web dashboard — **running**.

### Security material
- `/root/.config/dslv-zpdi/c2_token` — mode `600`, present.
- `/root/.config/dslv-zpdi/github_pat` — mode `600`, present (not used this session).

### Git status (main repo)
New untracked files:
- `docs/security/C2_THREAT_MODEL.md`
- `specs/SPEC-C2-001.md`
- `src/dslv_zpdi/control/`
- `tests/test_control_protocol.py`

Pre-existing modified files (not touched this session):
- `.codex/config.toml`
- `.cursorrules`
- `.env.example`
- `.githooks/pre-push`
- `AGENTS.md`
- `configure_git_auth.sh`

Pre-existing untracked files (not touched this session):
- `.claude/`
- `.codex/instructions.md`
- `.gemini/`
- `.kimi/`
- `CLAUDE.md`

No commits were made; no `git push` was performed.

---

## 4. Turnover for next agent / collaborator

### What to know before continuing
1. **Control package is canonical.** Any future C2 work should import from `dslv_zpdi.control`, not reimplement envelope logic in `c2_server.py`.
2. **Local overlay files are outside Git.** Changes to `dslv-zpdi-local/` are not tracked by the main repo. If you modify them, document them in the session report.
3. **C2 server binds to `127.0.0.1` by default.** LAN exposure requires mTLS (target phase, not implemented).
4. **Bearer token auth is current.** Token rotation is manual. mTLS node identities are future work.
5. **Tests must pass.** Run `bash /root/dslv-zpdi-local/scripts/validate.sh` before ending any session.
6. **SPEC-ID discipline.** Every new class/function in `src/dslv_zpdi/` must cite a SPEC-ID defined in `specs/`.

### Recommended next tasks (in order)
1. **Implement command adapters** in `src/dslv_zpdi/control/adapters/` for SDR, pipeline, and HDF5. Keep them narrow Python interfaces; no shell passthrough.
2. **Add node discovery service** (mDNS/DNS-SD or lightweight UDP broadcast) so mesh nodes can find the C2 plane without hardcoded IPs.
3. **Build the native Android APK** (`android/PixelControl/`) with `LocalOnlyHotspot`, Jetpack Compose dashboard, and foreground service.
4. **Add mTLS/HMAC** node identities and per-node capability mapping.
5. **Create the one-shot replacement-phone installer** (`scripts/install_pixel_c2_node.sh`).

### Open risks from this session
- `CapabilityStore` currently grants `tier2-c2-master` capabilities to all localhost callers. This is acceptable while the server is `127.0.0.1`-bound, but must change when LAN/mTLS is introduced.
- The legacy normalization shim in `c2_server.py` should be removed once all clients (dashboard, self-check, future APK) are confirmed to send spec envelopes.
- `hdf5.segment.export` capability is declared but the adapter only returns a staged acknowledgement; actual export logic is pending.
- `sdr.sample_rate.set` and `sdr.gain.set` validation is minimal; device-specific bounds should be added.

### Commands to verify state
```bash
# Full validation
bash /root/dslv-zpdi-local/scripts/validate.sh

# Overlay self-check
bash /root/dslv-zpdi-local/scripts/self_check.sh

# C2 status
curl -fsS http://127.0.0.1:8444/api/v1/status | python3 -m json.tool

# HDF5 summary
curl -fsS http://127.0.0.1:8445/api/v1/hdf5/summary | python3 -m json.tool
```

### Contact / artifacts
- This report: `/root/dslv-zpdi/SESSION_REPORT_2026-07-25_C2_PROTOCOL.md`
- Revised plan: `/data/data/com.termux/files/home/PIXEL_DEV_PLAN.md`
- System snapshot: `/data/data/com.termux/files/home/PIXEL_SNAPSHOT.md`

---

*Session complete. System is stable and ready for reboot.*
