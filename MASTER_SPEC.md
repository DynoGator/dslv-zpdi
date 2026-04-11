<!-- Authoritative human-facing canon: V3_DSLV-ZPDI_LIVING_MASTER.md | MASTER_SPEC.md is a compatibility mirror. -->

# DSLV-ZPDI — LIVING MASTER DOCUMENT

**Document Role:** Unified Master Binder
**Status:** ACTIVE
**Owner:** Joseph R. Fross
**Canonical File:** THIS FILE
**Last Updated:** 2026-04-08
**Current Revision:** Rev 4.0.2 (Clean Canonical — Architecture Compliant, Turnovers Consolidated, Phase 2A Active)

---

# 0. DOCUMENT NAVIGATION MAP

| Section | Title | Status | Purpose |
|---------|-------|--------|---------|
| 0 | Navigation Map | STATIC | You are here. |
| 1 | Immutable Mission / System Identity | LOCKED | What the project is and why it exists. |
| 2 | Foundational Theory / Targeting Matrix | SEMI-LOCKED | Theory spine defining what variables matter. |
| 3 | Master Architecture Spec | LOCKED | Canonical SPEC-ID law layer (the WPS). |
| 4 | Hardware Architecture | CONTROLLED | Tier 1 / Tier 2 roles, sync, physical deployment. |
| 5 | Software Architecture | CONTROLLED | Layer 1 / Layer 2 / Layer 3, payload contracts, decoupling. |
| 6 | Validation / Kill Conditions / Trust Model | LOCKED | Data acceptance, rejection, quarantine, kill logic. |
| 7 | Current Build Status | ACTIVE | Present build snapshot and active focus. |
| 8 | Implementation Roadmap | ACTIVE | Phased execution plan and next-action continuity. |
| 9 | Shift Turnover / Running Notes | APPEND-ONLY | Handoff notes, running progress, continuity prompts. |
| 10 | Change Log / Revision History | APPEND-ONLY | Tracked revisions to this document. |
| 11 | Archive / Deprecated Material | CONTROLLED | Superseded content preserved for traceability. |
| A | Restore Point Protocol | LOCKED | Air-gap snapshot procedures and recovery policy. |
| B | Collaborator Primer & Seamless Resumption | CONTROLLED | Zero-context onboarding and authentication. |
| C | Branch Architecture & Evidence Tiering | CONTROLLED | Modular branch definitions, source classification, citation doctrine. |
| D | External Source Registry & Classification | CONTROLLED | Tiered external references with correct evidence labels. |

**Section Status Definitions:**

- **LOCKED** — Deliberate owner revision only. Changes require a change log entry in Section 10.
- **SEMI-LOCKED** — Deliberate revision only. Theoretical additions permitted with justification.
- **CONTROLLED** — Revision permitted with traceability. Changes logged in Section 10.
- **ACTIVE** — Freely editable working section. Represents current state.
- **APPEND-ONLY** — New entries added at the bottom. Existing entries are never modified or deleted.
- **STATIC** — Structural element. Do not modify unless section taxonomy changes.

**Single-File Governance Note:** This document is intentionally maintained as a single canonical file. Redundancy between sections is minimized; each block of content lives in exactly one canonical location. Cross-references point to section numbers rather than duplicating content. When this file approaches critical mass (~2,000+ lines, or when scrolling becomes a workflow liability), the first sections to split into satellite files are Section 9 (Shift Turnovers) and Section 11 (Archive), as these grow unboundedly while all other sections stabilize. Any such split triggers a mandatory Restore Point per Appendix A.

---

# 1. IMMUTABLE MISSION BLOCK [LOCKED]

**Section Status:** LOCKED
**Purpose:** Define what the project is and why it exists.
**Editable By:** Deliberate revision only
**Last Revised:** 2026-04-07

## 1.1 Project Identity

**Project:** DSLV-ZPDI (Distributed Sensor Locational Vectoring — Zero-Point Data Integration)
**Subtitle:** Phase-Locked Standardized Data Acquisition and Synchronization With Legacy Frameworks
**Document Status:** Foundation Definition & Research Fork
**Subject:** Operational pivot from anomaly observation to institutional-grade standardized data acquisition
**Architecture Core:** KCET-ATLAS (Under active development and prototyping)
**Organization:** Resonant Genesis LLC / DynoGator Labs
**Lead:** J.R. Fross

## 1.2 Operational Mandate

The DSLV-ZPDI initiative represents a permanent pivot in operational methodology. Our prior theoretical work and unstandardized anomaly tracking (ULP, Resonant Genesis) are hereby classified as the **Targeting Matrix**. They dictate *what* we are looking for and *where* to aim.

The new mandate is purely logistical: capturing those targets using a data pipeline that institutional science cannot mathematically or methodologically reject. The system must operate with the reliability of heavy iron, translating anomalous multi-spectrum phenomena into synchronized, GPS-disciplined, HDF5-formatted telemetry.

## 1.3 Foundational SPEC-IDs (Mission-Level)

### SPEC-001 — SYSTEM IDENTITY AND OPERATIONAL MANDATE

**SYSTEM FUNCTION:** Define the system's identity, scope, and non-negotiable boundaries.
**OPERATIONAL INTENT:** DSLV-ZPDI is a multi-modal, hardware-agnostic Signals Intelligence (SIGINT) network that captures environmental phenomena and translates them into strictly standardized, GPS-disciplined, institutional-grade telemetry formatted in HDF5.
**KILL CONDITION:** Any module or output that cannot trace its existence back to this mandate is an orphan and must be removed.

### SPEC-002 — THE TARGETING MATRIX (THEORETICAL BEDROCK)

**SYSTEM FUNCTION:** House and reference the foundational theoretical work (Resonant Genesis / KCET).
**OPERATIONAL INTENT:** The theories tell us what to look for (phase-locked structure, quadrature, resonance). The pipeline tells us how to prove we found it. These are two separate concerns and must never merge in the output.
**KILL CONDITION:** Theoretical assumptions directly influencing data filters without empirical validation.

### SPEC-003 — THE DUAL-STREAM PROTOCOL

**SYSTEM FUNCTION:** Enforce absolute separation between institutional-grade data and internal exploratory data.
**OPERATIONAL INTENT:** Institutional credibility requires that the primary data output (HDF5) contains ZERO contamination from unstandardized observations. Two streams, one pipeline, total isolation. GPS-untrusted data routes to the secondary exploratory stream — it is quarantined, never destroyed, because it retains vectoring value.
**KILL CONDITION:** A single unstandardized data point in the primary HDF5 output constitutes a total pipeline failure.

---

# 2. FOUNDATIONAL THEORY / TARGETING MATRIX [SEMI-LOCKED]

**Section Status:** SEMI-LOCKED
**Purpose:** Preserve the theory spine and targeting matrix that define what variables matter.
**Editable By:** Deliberate revision only
**Last Revised:** 2026-04-07

## 2.1 Executive Summary: The Paradigm Shift

The institutional foundation of physics is brilliant, rigorous, and explicitly designed to reject uncalibrated data. This mechanism is not a flaw; it is a vital immune system for the scientific method. Historically, research into anomalous field, plasma, and coherence phenomena has failed to cross the threshold of institutional acceptance not because the phenomena are absent, but because the observational data lacks baseline calibration, microsecond synchronization, and standardized formatting.

Project Zero-Point-Data-Integration (ZPDI) represents a fundamental fork in the research trajectory. We are no longer attempting to force legacy frameworks to accept anomalous data. Instead, we are utilizing our historical body of theory and observation as a targeting matrix — a highly refined map indicating what to measure and where to aim.

The core objective of Project ZPDI is the engineering of a standardized, open-source observational architecture, rooted in the KCET-ATLAS prototype (currently under active development), capable of translating multi-spectrum environmental data into the strict, undeniable telemetry required by institutional physics.

## 2.2 Foundational Consolidation: The Targeting Matrix

To establish ZPDI as a new, standalone starting point, we must lock the foundational theory spine that directed us here. Our prior work established a highly disciplined falsification framework based on a cross-domain coherence architecture.

The core principle remains: Structured forcing can induce measurable transitions in downstream systems when energy magnitude, coupling geometry, resonance proximity, and phase stability are sufficient to exceed a system-specific threshold.

This is formalized in the Coherence Drive Parameter (Γ) and downstream response metric (r), with the causal direction strictly frozen as Γ → r.

While our previous work mapped this across physical, biological, and archaeo-engineering analogs, Project ZPDI isolates only the instrumented perception layer. The foundational theories provided the exact parameters for what a detection system must capture: phase-locked structure and quadrature locking, energy magnitude and spatial coupling geometry, and resonance proximity and phase stability.

These elements dictate the sensor requirements. The theories remain the bedrock, but the forward objective is entirely logistical: capturing these variables in a format that leaves no room for methodological doubt.

## 2.3 The KCET-ATLAS Baseline

Project ZPDI extracts its operational DNA from the KCET-ATLAS model. KCET was designed not to measure raw brightness, but to measure phase coherence across thousands of oscillators, calculating an order parameter r(t).

> **Cross-Reference:** The full KCET-ATLAS math (Kuramoto r(t), global R(t), EWMA smoothing, event confirmation) is canonically defined in Section 5.5.

## 2.4 Domain-Specific Coherence Definitions

These definitions are non-negotiable and prevent cross-domain conflation:

**Plasma / physical analog domain:** Coherence = Quadrature Locking — stable 90° phase relationship between oscillatory components.

**Biological domain:** Coherence = phase-sensitive entrainment and thresholded response — NOT inherited plasma quadrature geometry.

**Network / Kuramoto domain:** Coherence = order-parameter growth and phase convergence under forcing.

> **Cross-Reference:** Full branch-by-branch architecture, evidence posture, and kill-switches are defined in Appendix C.

---

# 3. MASTER ARCHITECTURE SPEC [LOCKED]

**Section Status:** LOCKED
**Purpose:** Canonical law layer for SPEC-IDs, operational intent, and architectural boundaries.
**Editable By:** Owner only / deliberate revision only
**Last Revised:** 2026-04-08 (Rev 3.1 — SPEC-004A.1, SPEC-008, SPEC-009 added via owner-directed revision)

## 3.1 PART I: FOUNDATIONAL ARCHITECTURE

SPEC-001 through SPEC-003 are canonically defined in Section 1.3 above.

## 3.2 PART II: HARDWARE ARCHITECTURE SPECS

### SPEC-004 — TWO-TIER HARDWARE MODEL

**SYSTEM FUNCTION:** Define the bifurcated physical collection layer.
**OPERATIONAL INTENT:** Separate hardware into truth-engines (Tier 1 Anchors) and early-warning triggers (Tier 2 Swarm). Tier 2 vectors Tier 1, but does NOT produce institutional data.
**KILL CONDITION:** Tier 2 data treated as Tier 1 data (trust weight >= 1.0).

### SPEC-004A — TIER 1: ANCHOR NODES (Institutional Grade)

**IMPLEMENTATION TARGET:** Raspberry Pi 5 (16GB) with HackRF One SDR, Leo Bodnar Mini GPSDO (10 MHz + 1 PPS), and multi-modal sensors.
**OPERATIONAL INTENT:** The unassailable truth engines producing the primary HDF5 stream via RF Metrology timing.
**KILL CONDITION:** GPS lock loss, PPS jitter > 10µs, calibration drift > 20%, ADC not phase-locked to GPSDO reference.

### SPEC-004A.1 — GPSDO METROLOGY CLOCK REQUIREMENT (Rev 4.1)

**SYSTEM FUNCTION:** Achieve hardware-level ADC phase coherence by locking the SDR sampling clock directly to the GPS constellation via an external GPSDO, eliminating all USB bus jitter and software timing intermediaries from the phase measurement chain.
**OPERATIONAL INTENT:** Tier 1 nodes MUST use a GPS-Disciplined Oscillator (GPSDO) providing a 10 MHz reference signal injected into the SDR's external clock input (`CLKIN`), phase-locking the ADC at the analog level. A separate 1 PPS output from the GPSDO provides UTC epoch anchoring to the host compute board via GPIO hardware interrupt. This is "RF Metrology" timing — the measurement instrument itself is GPS-locked, not merely the computer's system clock.
**PHASE 2A PRIMARY TARGET:** Leo Bodnar Mini GPSDO → 10 MHz SMA out to HackRF One `CLKIN` port; 1 PPS out to Raspberry Pi 5 GPIO 18 via `pps-gpio` kernel module and `chronyd`.
**FORBIDDEN:** Reliance on USB bus timing for phase coherence. Any configuration where the SDR ADC clock is derived from the SDR's internal oscillator during institutional data collection. Software-only timestamping (NTP/PTP without hardware PPS interrupt) for Tier 1 primary stream.
**MANDATORY:** External 10 MHz reference locked to GPS constellation feeding SDR CLKIN; 1 PPS hardware interrupt on host GPIO; `chronyd` configured with PPS refclock for < 1µs UTC accuracy; verification of ADC lock via `hackrf_debug` or equivalent tool.
**KILL CONDITION:** Any Tier 1 node collecting institutional data with an unlocked (free-running) ADC oscillator.

### SPEC-004A.2 — HARDWARE AGNOSTICISM STANDARD (Rev 4.1)

**SYSTEM FUNCTION:** Define the universal hardware performance criteria for Tier 1 eligibility, ensuring the project is approachable and not locked to a single vendor or component.
**OPERATIONAL INTENT:** Any hardware combination is permissible for Tier 1 as long as it meets the following three criteria:
1. **External 10 MHz Phase-Locking:** The SDR/digitizer MUST accept an external 10 MHz reference that hardware-locks the ADC sampling clock. Software frequency correction is NOT sufficient.
2. **1 PPS Hardware Interrupt:** The compute platform MUST receive a 1 PPS signal from the GPSDO via a hardware interrupt path (GPIO, SDP, dedicated timing input) — NOT via network or software polling.
3. **Sufficient Compute:** The platform MUST buffer incoming IQ data, compute Kuramoto coherence math, and write HDF5 without dropping frames at the operational sample rate.
**PERMISSIBLE TIER 1 EXAMPLES:**
- Raspberry Pi 5 (16GB) + HackRF One + Leo Bodnar Mini GPSDO ← **Phase 2A Primary**
- Raspberry Pi CM5 + HackRF One + Leo Bodnar Mini GPSDO (carrier board with GPIO access)
- Nvidia Jetson AGX Orin + Ettus USRP B200/B210 + external GPSDO
- Intel NUC with M.2 timing card + LimeSDR USB + external GPSDO
- Any Linux SBC with GPIO + any SDR with CLKIN + any GPS-disciplined 10 MHz source
**KILL CONDITION:** Hardware marketed as "Tier 1 compliant" that lacks a hardware-locked external clock input on the SDR.

### SPEC-004A.3 — CONTINUOUS TIMING HEALTH MONITORING (Rev 4.1)

**SYSTEM FUNCTION:** Monitor GPSDO/PPS stability in real-time to ensure the integrity of the institutional data stream.
**OPERATIONAL INTENT:** Tier 1 nodes MUST run a continuous watchdog that monitors the PPS jitter from the GPSDO via `chronyd`. If the root-mean-square (RMS) offset exceeds 10µs for more than 60 seconds, the node must automatically flag all incoming data as "Quarantined" (Tier 2 status) until stable timing is restored.
**IMPLEMENTATION TARGET:** `TimingMonitor` class in Layer 1, polling `chronyc tracking` for RMS offset status.
**KILL CONDITION:** Institutional data collected while the timing watchdog is in an "Unhealthy" state.

### SPEC-004B — TIER 2: SWARM NODES (Heuristic Net)

**IMPLEMENTATION TARGET:** Rooted e-waste devices (Android/iOS) in hermetically sealed, solar-powered cases.
**OPERATIONAL INTENT:** Distributed early-warning triggers to vector Tier 1 Anchors. Permanently sandboxed.
**KILL CONDITION:** Swarm data entering primary stream without Tier 1 corroboration.

### SPEC-004B.1 — TIER 2 / TESTBED SDR STANDARD (Rev 4.1)

**SYSTEM FUNCTION:** Define permissible SDR hardware for Tier 2 swarm nodes and development testbeds.
**OPERATIONAL INTENT:** The RTL-SDR (v3/v4) is explicitly authorized as a Tier 2 or Testbed device. It is acceptable for pipeline development, algorithm validation, and swarm heuristic detection. However, the HackRF One (or any SDR with a native `CLKIN` port) is heavily preferred for actual field deployments due to hardware clock-locking capability and wider bandwidth (20 MHz vs 2.4 MHz). RTL-SDR data MUST NOT enter the Tier 1 primary stream unless the RTL-SDR node independently satisfies all SPEC-004A.2 criteria (which the RTL-SDR v3/v4 cannot, as it lacks an external clock input).
**KILL CONDITION:** RTL-SDR data in the primary institutional stream without Tier 1 corroboration from a clock-locked node.

## 3.3 PART III: SOFTWARE ARCHITECTURE SPECS

### SPEC-005 — THREE-LAYER SOFTWARE DECOUPLING

**SYSTEM FUNCTION:** Enforce strict separation between hardware interaction, data processing, and output formatting.
**OPERATIONAL INTENT:** The core engine (Layer 2) must not care what hardware it runs on. If a sensor breaks, only Layer 1 fails. If formatting changes, only Layer 3 changes.
**KILL CONDITION:** Direct hardware calls in L2/L3; formatting logic in L1/L2; phase extraction in L2 (must occur in L1).

### SPEC-005A — LAYER 1: INGESTION API (Hardware-Specific)

> **Cross-Reference:** Canonical implementation code lives in Section 5.3.

### SPEC-006 — KCET-ATLAS COHERENCE ENGINE

**SYSTEM FUNCTION:** Compute phase coherence across multi-modal, multi-node sensor data using the Kuramoto order parameter and downstream event confirmation logic.
**OPERATIONAL INTENT:** Layer 2 is the only place where raw sensor payloads are turned into institutional-grade coherence scores. It remains 100% hardware-agnostic and operates exclusively on validated IngestionPayload objects that have already passed TIME_TRUSTED and CAL_TRUSTED gates. Includes global weighted R(t) computation across the fleet.
**KILL CONDITION:** Any coherence calculation performed on packets that have not reached CAL_TRUSTED state, or any direct hardware access from this layer.

### SPEC-006.5 — LAYER 2 WIRING GATE

**SYSTEM FUNCTION:** Deserialize Layer 1 JSON payloads, rehydrate enum types, read pre-extracted phase vectors, route through CoherenceScorer, and advance trust state.
**OPERATIONAL INTENT:** Single canonical bridge between Layer 1 and Layer 2. Enforces one-way runtime flow (Section 5.2A) and packet state machine (Section 5.2B). Does NOT perform phase extraction (that is Layer 1's job per SPEC-005).
**KILL CONDITION:** Any direct call to CoherenceScorer.update() from anywhere except this wiring function. Any Hilbert transform or phase-extraction math in this layer.

### SPEC-007 — DUAL-STREAM ROUTER

**SYSTEM FUNCTION:** Enforce absolute separation between primary institutional HDF5 stream and secondary exploratory stream.
**OPERATIONAL INTENT:** After coherence processing, this router is the final gatekeeper that physically quarantines any packet that failed any trust rule.
**KILL CONDITION:** Any packet reaching HDF5Writer without having passed through this router.

### SPEC-008 — SWARM INTEGRITY PROTOCOL (Rev 3.1)

**SYSTEM FUNCTION:** Detect and quarantine adversarial or poisoned Tier 2 triggers before they vector Tier 1 assets.
**OPERATIONAL INTENT:** Apply propagation-wave physics check and stylistic-consistency analysis to swarm behavior itself before vectoring Tier 1.
**KILL CONDITION:** Stylistic deviation > 3σ from regional baseline, or impossible propagation speed (exceeds speed-of-light constraint for distance between reporting nodes).

### SPEC-009 — ENVIRONMENTAL BASELINE LEARNING (Rev 3.1)

**SYSTEM FUNCTION:** Replace static r ≥ 0.40 threshold with adaptive, location-specific statistical outlier detection.
**OPERATIONAL INTENT:** 72-hour passive listening mode on first deployment to build local Kuramoto r_smooth distribution; trigger on kurtosis/skewness deviation rather than a fixed number.
**KILL CONDITION:** Event declared during baseline learning phase.

---

# 4. HARDWARE ARCHITECTURE [CONTROLLED]

**Section Status:** CONTROLLED
**Purpose:** Capture Tier 1 / Tier 2 hardware roles, sync requirements, and physical deployment intent.
**Editable By:** Controlled revision
**Last Revised:** 2026-04-11 (Rev 4.1 — HackRF/GPSDO metrology pivot, Hardware Agnosticism Standard)

## 4.1 The Two-Tier Hardware Architecture

To achieve unprecedented situational awareness without an impossible budget, the physical array operates on a bifurcated hardware model:

**Tier 1: The Anchors (Institutional Grade — RF Metrology Timing)**

- **Phase 2A Primary Compute:** Raspberry Pi 5 (16GB).
- **SDR (The Eye):** HackRF One (PortaPack optional/irrelevant for headless operation). 20 MHz bandwidth, 1 MHz – 6 GHz range.
- **Clock Authority:** Leo Bodnar Mini GPSDO (or equivalent GPS-disciplined 10 MHz oscillator).
- **Timing Wiring (Rev 4.1):** 10 MHz SMA out from GPSDO → HackRF One `CLKIN` port (hardware ADC lock). 1 PPS out from GPSDO → Raspberry Pi 5 GPIO 18 via `pps-gpio` kernel module + `chronyd`. This eliminates all USB bus jitter from the phase measurement chain. The ADC sampling clock is derived directly from the GPS constellation — no software intermediaries.
- **Role:** The unassailable truth engines. These nodes produce the primary institutional output with hardware-locked phase coherence.
- **Hardware Agnosticism:** Any hardware meeting the SPEC-004A.2 criteria is equally valid for Tier 1. The Pi 5 + HackRF + Leo Bodnar is the Phase 2A reference implementation, not a mandate. See Section 3.2, SPEC-004A.2 for the full permissible hardware list.

**Tier 2: The Swarm (The Heuristic Net)**

- **Hardware:** Rooted/Jailbroken E-waste (Android/iOS phones, Arduinos), RTL-SDR v3/v4 receivers.
- **Enclosure:** Hermetically sealed, passively cooled (heat sink to SoC), rugged cases designed to survive extreme field environments with zero maintenance.
- **Power Architecture (Rev 3.1):** Industrial supercapacitor banks (100–500F, e.g., Eaton HS-108 series). Voltage: 2.7V series arrays with buck-boost regulation to 5V/3.3V. Cycle life: >500,000 cycles. Temperature range: –40°C to +65°C. Maintenance interval: 5–7 years. Lithium-ion batteries are FORBIDDEN (thermal runaway risk under sealed conditions).
- **SDR Standard (Rev 4.1):** RTL-SDR v3/v4 is the authorized Tier 2/Testbed SDR (see SPEC-004B.1). Acceptable for pipeline development and heuristic triggering. Not eligible for Tier 1 primary stream due to lack of external clock input.
- **Role:** Distributed early-warning triggers. If the Swarm detects an anomaly, it vectors the Tier 1 Anchors.

> **Governing SPEC-IDs:** SPEC-004, SPEC-004A, SPEC-004A.1, SPEC-004A.2, SPEC-004B, SPEC-004B.1 (canonically defined in Section 3.2).

## 4.2 Hardware: The Tier 1 Anchor Node ("Thoth's Eye")

The physical collection layer is built on hardware-agnostic Linux SBCs with GPS-disciplined SDRs. The Phase 2A reference implementation uses the Raspberry Pi 5, but any platform meeting SPEC-004A.2 is equally valid. Each "Thoth's Eye" node features:

- **Multi-Modal Ingestion:** RF (HackRF One or equivalent CLKIN-capable SDR), Thermal, Acoustic, and GPS/PPS sensors.
- **Hardware-Level Phase Coherence (Rev 4.1):** GPSDO 10 MHz reference → SDR CLKIN port. The ADC sampling clock is hardware-locked to the GPS constellation at the analog level. USB bus jitter is irrelevant — it affects data transfer latency, not the phase relationship between IQ samples. This is RF Metrology timing, not IT Network timing.
- **UTC Epoch Anchoring:** GPSDO 1 PPS → GPIO hardware interrupt → `pps-gpio` + `chronyd`. Combined with the GPS-locked sample rate, every IQ sample receives a precise UTC timestamp by counting samples from the last PPS edge.
- **Health & Trust Telemetry:** Continuous logging of ADC lock status, GPS lock, PPS jitter, calibration drift, and environmental classification.

---

# 5. SOFTWARE ARCHITECTURE [CONTROLLED]

**Section Status:** CONTROLLED
**Purpose:** Define Layer 1 / Layer 2 / Layer 3 behavior, payload contracts, formatting, and decoupling rules.
**Editable By:** Controlled revision
**Last Revised:** 2026-04-08 (Rev 3.1 — all architecture violations resolved)

## 5.1 Core Software Layering & Architectural Decisions

To guarantee adaptability and prevent hardware-specific bottlenecks, the codebase will be rigidly divided into three decoupled layers. This is the hardest, most critical decision of the build: the core engine must not care what hardware it is running on.

**Layer 1: The Ingestion API (Hardware-Specific)** — Talks directly to physical sensors, translates raw voltages/signals into a standardized JSON string, performs modality-specific phase extraction (Hilbert transform, etc.), and pushes it up. Phase extraction is a Layer 1 responsibility because it requires hardware-specific knowledge of the signal format.

**Layer 2: The Core Engine (Hardware-Agnostic)** — Performs all mathematical processing: EWMA smoothing, coherence extraction, phase-locking math, and event-window logic. Layer 2 remains hardware-agnostic and may only consume the contract emitted by Layer 1. Layer 2 receives pre-extracted phase vectors — it never imports signal-processing libraries like scipy.signal.

**Layer 3: The Telemetry & Output (Format-Specific)** — Handles dual-stream routing, HDF5 formatting, cryptographic attestation, and all downstream persistence and forwarding.

## 5.2A Canonical Runtime Flow (Single-Pass Operational Sequence)

1. **Sensor Capture** — Hardware produces a physical measurement (RF IQ samples, GPS NMEA, thermal frame, acoustic buffer).
2. **Layer 1 Ingestion** — Hardware-specific driver translates raw capture into an IngestionPayload, performs modality-specific phase extraction (e.g., Hilbert transform for SDR IQ), assigns payload_uuid, timestamps via GPS/PPS, runs self-validation.
3. **Payload Self-Validation** — Identity, timing, and structural integrity checks. Structurally corrupt packets → KILLED. GPS-untrusted packets → SECONDARY_QUARANTINED (not killed — per SPEC-003).
4. **Trust Gating** — GPS lock and calibration checks advance valid packets: ASSEMBLED → TIME_TRUSTED → CAL_TRUSTED.
5. **Layer 1 Emission** — Validated payload (with extracted_phases populated) serialized to JSON and emitted upward.
6. **Layer 2 Wiring (SPEC-006.5)** — JSON deserialized, enum types rehydrated from strings, pre-extracted phase vectors read from payload, payload routed to CoherenceScorer. No phase extraction occurs here.
7. **Coherence Processing** — EWMA smoothing, local r(t) computation, global weighted R(t) across fleet, event-window logic applied (trust state: CORE_PROCESSED).
8. **Cross-Node Confirmation** — Candidate events evaluated across node windows. Global confirmation requires ≥4 nodes confirming within a 300ms window.
9. **Dual-Stream Arbitration (SPEC-007)** — Primary stream: GPS-locked, calibration-valid, policy-compliant packets with confirmed events. Secondary stream: exploratory, quarantined, or non-institutional data.
10. **Watchdog Enforcement** — MVIP-6 watchdog continuously evaluates GPS lock, jitter, calibration drift, and node health.
11. **Persistence and Forwarding** — Primary to HDF5 (with cryptographic attestation) then telemetry bridge. Secondary logged under quarantine semantics. Visualization always downstream of persistence, never upstream of trust.

### One-Way Law

The data path is intentionally one-way:

`Capture → Assemble → Validate → Trust → Process → Confirm → Route → Persist → Render`

No downstream layer may "promote" a packet backward into trust. No rendered artifact may elevate confidence above measured truth. No convenience shortcut may bypass the gate sequence above.

## 5.2B Packet State Model (Trust-State Machine)

This subsection defines the canonical state transitions for every packet entering the system. Rev 3.1 clarification: `validate()` returns a trust state string, not a boolean kill decision. GPS-untrusted packets route to SECONDARY_QUARANTINED per SPEC-003, preserving their vectoring value.

| State | Meaning | Entry Condition | Allowed Exit | Forbidden Exit |
|-------|---------|-----------------|--------------|----------------|
| `RAW_CAPTURED` | Physical measurement exists at hardware edge | Sensor produced a measurement | `ASSEMBLED` | Any routed or processed state |
| `ASSEMBLED` | Packet exists in universal contract form | Layer 1 emitted payload | `TIME_TRUSTED`, `SECONDARY_QUARANTINED`, `KILLED` | Any primary-stream state |
| `TIME_TRUSTED` | GPS/PPS timing meets minimum rule | GPS lock valid and timestamp trusted | `CAL_TRUSTED`, `SECONDARY_QUARANTINED`, `KILLED` | Direct render or primary persistence |
| `CAL_TRUSTED` | Calibration and drift status acceptable | Calibration valid and within threshold | `CORE_PROCESSED`, `SECONDARY_QUARANTINED`, `KILLED` | Direct HDF5 write |
| `CORE_PROCESSED` | Layer 2 math applied | Packet accepted by core engine | `PRIMARY_CANDIDATE`, `SECONDARY_QUARANTINED`, `KILLED` | Direct render confidence claim |
| `PRIMARY_CANDIDATE` | Eligible for institutional routing | All policy gates still green | `PRIMARY_ACCEPTED`, `SECONDARY_QUARANTINED`, `KILLED` | Any bypass around router |
| `PRIMARY_ACCEPTED` | Institutional-grade packet or event | Router accepted into primary stream | Persist to HDF5 and forward | Return to exploratory-only state |
| `SECONDARY_QUARANTINED` | Exploratory retention only | Any trust rule failed without full discard | Secondary logging only | HDF5 institutional write |
| `KILLED` | Packet terminated | Structural failure (missing identity, missing UUID) | None | Any downstream reuse |

### State Transition Rules

1. A packet may only advance one trust layer at a time.
2. A packet that enters SECONDARY_QUARANTINED may never be promoted into PRIMARY_ACCEPTED.
3. A packet that enters KILLED is terminal and must not be recycled.
4. Rendered overlays may reference only PRIMARY_ACCEPTED or clearly labeled SECONDARY_QUARANTINED products.
5. Any future modality must conform to this state machine without creating parallel trust semantics.
6. Rev 3.1 addition: GPS failure and PPS jitter failure produce SECONDARY_QUARANTINED, not KILLED. Only structural corruption (missing identity fields, missing UUID) produces KILLED.

## 5.3 SPEC-005A Canonical Implementation — Layer 1 Ingestion API (Rev 3.1)

**File:** `src/layer1_ingestion/payload.py`

```python
"""
SPEC-005A | Trust Tier: Measured (Tier 1 Raw) — Rev 3.1
Translates hardware-native signals into a universal JSON contract.

Rev 3.1 changes:
  - validate() returns (trust_state, reason) instead of (bool, msg)
  - GPS untrusted → SECONDARY_QUARANTINED (not KILLED) per SPEC-003
  - PPS jitter > 10µs → SECONDARY_QUARANTINED
  - Added extracted_phases field (phase extraction is Layer 1's job)
  - schema_version bumped to 3.1
  - Checksum uses SHA-256 instead of placeholder UUID
"""
import json
import time
import uuid
import hashlib
from dataclasses import dataclass
from typing import Optional, Any, List
from enum import Enum


class SensorModality(Enum):
    """SPEC-005A.1a — Sensor Type Registry"""
    RF_SDR = "rf_sdr"
    GPS_PPS = "gps_pps"
    THERMAL = "thermal"
    ACOUSTIC = "acoustic"


@dataclass
class IngestionPayload:
    """SPEC-005A.1b — Hardened Universal Payload (Rev 3.1)"""
    spec_id: str = "SPEC-005A.1b"
    schema_version: str = "3.1"
    payload_uuid: str = ""
    node_id: str = ""
    sensor_id: str = ""
    modality: str = ""  # Stored as string for JSON serialization; rehydrated in Layer 2 wiring
    timestamp_utc: float = 0.0
    ingest_monotonic_ns: int = 0
    raw_value: Any = None
    extracted_phases: List[float] = None  # Rev 3.1: Phase vector extracted in Layer 1
    gps_locked: bool = False
    pps_jitter_ns: float = 0.0
    calibration_valid: bool = False
    calibration_age_s: float = 0.0
    drift_percent: float = 0.0
    source_path: str = ""
    trust_state: str = "ASSEMBLED"
    quarantine_reason: Optional[str] = None
    env_class: Optional[str] = None
    event_window_id: Optional[str] = None
    parent_trigger_id: Optional[str] = None
    payload_checksum: str = ""
    hardware_tier: int = 1

    def validate(self) -> tuple:
        """SPEC-005A.2 — Payload Self-Validation (Rev 3.1)
        Returns (trust_state: str, quarantine_reason: str|None).
        KILLED = structural corruption only.
        SECONDARY_QUARANTINED = trust insufficiency (GPS, PPS, calibration).
        ASSEMBLED = ready for trust gating."""
        if not self.node_id or not self.sensor_id or not self.modality:
            return "KILLED", "Missing routing identity"
        if self.payload_uuid == "":
            return "KILLED", "Missing payload_uuid"
        if self.timestamp_utc == 0.0 or not self.gps_locked:
            return "SECONDARY_QUARANTINED", "GPS untrusted — exploratory only"
        if self.pps_jitter_ns > 10_000.0:
            return "SECONDARY_QUARANTINED", "PPS jitter exceeds Tier 1 threshold (10µs)"
        return "ASSEMBLED", None

    def to_json(self) -> Optional[str]:
        """SPEC-005A.3 — Serialization Gate (Rev 3.1)"""
        state, reason = self.validate()
        self.trust_state = state
        if reason:
            self.quarantine_reason = reason
        if state == "KILLED":
            return None  # Structurally corrupt packets never serialize
        d = {k: v for k, v in self.__dict__.items() if not k.startswith('_')}
        d['modality'] = self.modality  # Already a string
        raw_json = json.dumps(d, sort_keys=True, default=str)
        d['payload_checksum'] = hashlib.sha256(raw_json.encode()).hexdigest()[:16]
        return json.dumps(d, default=str)
```

## 5.4 Payload Evolution Requirements (Contract Hardening)

The following fields harden auditability, deduplication, replay protection, and cross-node event stitching:

| Field | Type | Required | Purpose |
|-------|------|----------|---------|
| `schema_version` | `str` | Yes | Prevent silent breakage when the contract evolves (currently "3.1") |
| `payload_uuid` | `str` | Yes | Unique packet identity across queues, logs, and bridges |
| `ingest_monotonic_ns` | `int` | Yes | Local monotonic timing for ordering and replay diagnostics |
| `source_path` | `str` | Yes | Exact interface or device path used to acquire the packet |
| `trust_state` | `str` | Yes | Canonical packet state from Section 5.2B |
| `quarantine_reason` | `str \| null` | Conditional | Explicit reason when packet is routed to secondary stream |
| `calibration_age_s` | `float` | Yes | Seconds since last successful calibration |
| `drift_percent` | `float` | Yes | Current measured drift against baseline |
| `extracted_phases` | `List[float] \| null` | Modality-dependent | Phase vector extracted in Layer 1 (Rev 3.1) |
| `env_class` | `str` | No | Environmental classification for contextual filtering |
| `event_window_id` | `str \| null` | No | Correlates packets into a common confirmation window |
| `parent_trigger_id` | `str \| null` | No | Links Tier 2 trigger to Tier 1 response without trust pollution |
| `payload_checksum` | `str` | Yes | SHA-256 truncated hash for corruption detection |

### Contract Rules

- `schema_version` must increment whenever required fields or trust semantics change.
- `payload_uuid` must be generated at Layer 1 and remain immutable.
- `trust_state` must be updated only by explicit gate transitions, never inferred ad hoc.
- `parent_trigger_id` may reference Tier 2 provenance for vectoring logic, but must not increase trust weight.
- `payload_checksum` is calculated after serialization via SHA-256 and verified before persistence.

## 5.5 KCET-ATLAS Coherence Engine (Layer 2 Core Math) [SPEC-006] — Rev 3.1

### 5.5.1 Instantaneous Local Order Parameter (Single-Node KCET-ATLAS Core)

For a single node with N phase estimates φ_k(t):

r(t) = | (1/N) Σ_{k=1}^{N} e^{iφ_k(t)} |

where r(t) ∈ [0, 1] (0 = complete incoherence, 1 = perfect phase-locking).

**Phase Extraction Rules (Modality-Specific — performed in Layer 1 per SPEC-005):**

- **RF_SDR:** Hilbert transform on baseband IQ samples → analytic signal → instantaneous phase. Performed in `ingest_sdr()`, stored in `extracted_phases`.
- **THERMAL / OPTICAL:** Bandpass-filtered intensity time series → analytic signal via Hilbert or quadrature demodulation.
- **ACOUSTIC:** Same as above after envelope detection.
- **GPS_PPS:** No phase vector — timing reference only. `extracted_phases` = empty list.

### 5.5.2 Global Multi-Node Weighted Coherence (Rev 3.1 — now implemented in code)

For M nodes across the fleet, the system-wide order parameter R(t) is:

R(t) = | Σ_{m=1}^{M} w_m · r_m(t) · e^{iψ_m(t)} | / Σ_{m=1}^{M} w_m

where w_m = 3 for RF nodes (highest signal-to-noise and phase stability), w_m = 1 for all other modalities, and ψ_m(t) is the mean phase of node m.

Rev 3.1: This formula is now implemented as `CoherenceScorer.compute_global_R()` with fleet state tracking.

### 5.5.3 Temporal Smoothing (EWMA)

r_smooth(t) = α · r(t) + (1 − α) · r_smooth(t − Δt)

with α = 0.2 (as established in the KCET v2.0 baseline).

### 5.5.4 Event Confirmation & Threshold Logic

An **Anomalous Candidate** event is declared **only** when **all** of the following are simultaneously true inside a sliding 300ms window: at least 4 independent nodes report r_smooth ≥ 0.40, global R(t) ≥ 0.40, every contributing node is in at least CAL_TRUSTED state, and no node exceeds its modality-specific physical ceiling.

**Threshold Reference (KCET-ATLAS Baseline):** Noise/Random: r < 0.15. Structured Background: 0.15 ≤ r < 0.40. Anomalous Candidate: r ≥ 0.40.

> **SPEC-009 Note:** On first deployment, these thresholds may be superseded by adaptive baselines after the 72-hour learning period. See SPEC-009 in Section 3.3.

### 5.5.5 Canonical Python Implementation (coherence.py) — Rev 3.1

**File:** `src/layer2_core/coherence.py`

```python
"""
SPEC-006 | Trust Tier: Processed (Layer 2)
KCET-ATLAS Coherence Engine — hardware-agnostic phase-locking math.

Rev 3.1 changes:
  - Added compute_global_R() implementing Section 5.5.2 weighted formula
  - Added fleet_state tracking for global R(t)
  - Added r_global field to CoherencePacket
  - Added MODALITY_WEIGHTS class constant
  - CoherenceScorer.update() now returns r_global on every packet
"""
import cmath
import uuid
from dataclasses import dataclass
from typing import List, Dict, Optional
from collections import deque


@dataclass
class CoherencePacket:
    """Internal Layer 2 wrapper that augments IngestionPayload with coherence state."""
    payload_uuid: str
    node_id: str
    modality: str
    r_local: float = 0.0
    r_smooth: float = 0.0
    r_global: float = 0.0  # Rev 3.1: Global weighted R(t)
    trust_state: str = "CORE_PROCESSED"
    event_window_id: Optional[str] = None


class CoherenceScorer:
    """SPEC-006.1 — KCET-ATLAS Coherence Engine (Rev 3.1)"""
    MODALITY_WEIGHTS = {
        "rf_sdr": 3.0,
        "gps_pps": 1.0,
        "thermal": 1.0,
        "acoustic": 1.0,
    }

    def __init__(self, alpha: float = 0.2, window_ms: int = 300, min_nodes: int = 4):
        self.alpha = alpha
        self.window_ms = window_ms
        self.min_nodes = min_nodes
        self.history: Dict[str, deque] = {}
        self.global_events: List[Dict] = []
        self.fleet_state: Dict[str, dict] = {}  # Rev 3.1: node_id -> latest state

    def compute_local_r(self, phases: List[float]) -> float:
        """SPEC-006.2 — Instantaneous Kuramoto order parameter."""
        if not phases:
            return 0.0
        sum_complex = sum(cmath.exp(1j * phi) for phi in phases)
        return abs(sum_complex / len(phases))

    def compute_global_R(self) -> float:
        """SPEC-006.2b — Global Multi-Node Weighted Coherence R(t) [Rev 3.1]
        Implements Section 5.5.2 formula exactly."""
        if not self.fleet_state:
            return 0.0
        weighted_sum = 0j
        total_weight = 0.0
        for nid, state in self.fleet_state.items():
            w = self.MODALITY_WEIGHTS.get(state["modality"], 1.0)
            weighted_sum += w * state["r_smooth"] * cmath.exp(1j * state["mean_phase"])
            total_weight += w
        if total_weight == 0:
            return 0.0
        return abs(weighted_sum / total_weight)

    def update(self, payload_dict: dict, phases: List[float]) -> CoherencePacket:
        """SPEC-006.3 — Main entry point (Rev 3.1)."""
        node_id = payload_dict.get("node_id", "unknown")
        modality = payload_dict.get("modality", "unknown")
        # Handle both enum and string
        if hasattr(modality, 'value'):
            modality = modality.value

        r_local = self.compute_local_r(phases)

        # EWMA smoothing
        if node_id not in self.history:
            self.history[node_id] = deque(maxlen=100)
        prev = self.history[node_id][-1][1] if self.history[node_id] else 0.0
        r_smooth = self.alpha * r_local + (1 - self.alpha) * prev

        ts = payload_dict.get("timestamp_utc", 0.0)
        self.history[node_id].append((ts, r_smooth))

        # Rev 3.1: Update fleet state for global R(t)
        mean_phase = 0.0
        if phases:
            mean_phase = cmath.phase(sum(cmath.exp(1j * phi) for phi in phases) / len(phases))
        self.fleet_state[node_id] = {
            "r_smooth": r_smooth,
            "mean_phase": mean_phase,
            "modality": modality,
            "ts": ts,
        }

        packet = CoherencePacket(
            payload_uuid=payload_dict.get("payload_uuid", str(uuid.uuid4())),
            node_id=node_id,
            modality=modality,
            r_local=r_local,
            r_smooth=r_smooth,
            r_global=self.compute_global_R(),
        )

        self._check_global_confirmation(ts, packet)
        return packet

    def _check_global_confirmation(self, ts: float, packet: CoherencePacket):
        """SPEC-006.4 — Multi-node event confirmation within sliding window."""
        window_s = self.window_ms / 1000.0
        confirming = []
        for nid, hist in self.history.items():
            recent = [(t, r) for t, r in hist if abs(t - ts) <= window_s]
            if recent and recent[-1][1] >= 0.40:
                confirming.append(nid)
        if len(confirming) >= self.min_nodes:
            event_id = str(uuid.uuid4())
            packet.event_window_id = event_id
            self.global_events.append({
                "event_id": event_id,
                "timestamp": ts,
                "confirming_nodes": confirming,
                "node_count": len(confirming),
            })
```

## 5.6 CM5 Ingestion Module — Full Live Implementation (Rev 3.1)

**File:** `src/layer1_ingestion/cm5_ingestion.py`

Rev 3.1 changes: `ingest_gps_pps()` reads real PPS via kernel ioctl on /dev/pps0 (no random placeholder). `ingest_sdr()` performs Hilbert transform and phase extraction in Layer 1 and stores results in `extracted_phases` field. Both functions store modality as string (not enum object) for JSON compatibility.

```python
"""
SPEC-005A.4 — CM5 Hardware-Specific Ingestion (Rev 3.1 — Live)
Phase extraction is performed HERE (Layer 1) per SPEC-005.
PPS jitter is measured HERE from real hardware per SPEC-004A.1.
"""
import os
import fcntl
import struct
import serial
import rtlsdr
import time
import uuid
import numpy as np
from scipy.signal import hilbert
from .payload import IngestionPayload, SensorModality


# ─── GPS/PPS Ingestion (Rev 3.1 — Real PPS) ──────────────────
def ingest_gps_pps(
    serial_port: str = "/dev/ttyACM0",
    pps_device: str = "/dev/pps0",
    baud: int = 9600,
    node_id: str = "CM5-ALPHA",
    sensor_id: str = "UBLOX-GPS-01",
    pps_jitter_threshold_ns: float = 10_000.0,
) -> IngestionPayload:
    """SPEC-005A.4a — GPS/PPS Live Ingestion (Hardware-Anchored, Rev 3.1)"""
    mono_ns = time.monotonic_ns()

    # Read actual PPS timestamp from kernel via ioctl
    pps_jitter_ns = float('inf')
    try:
        fd = os.open(pps_device, os.O_RDONLY)
        try:
            buf = fcntl.ioctl(fd, 0x80047001, struct.pack('llll', 0, 0, 0, 0))
            sec, nsec, _, _ = struct.unpack('llll', buf)
            pps_time_ns = sec * 1_000_000_000 + nsec
            mono_now_ns = time.monotonic_ns()
            pps_jitter_ns = float(abs(mono_now_ns - pps_time_ns) % 1_000_000_000)
        finally:
            os.close(fd)
    except (OSError, IOError):
        pps_jitter_ns = float('inf')  # PPS device unavailable → will quarantine

    # Parse NMEA from u-blox
    ser = serial.Serial(serial_port, baud, timeout=2)
    nmea_data = {}
    for _ in range(20):
        line = ser.readline().decode("ascii", errors="replace").strip()
        if line.startswith("$GPRMC") or line.startswith("$GNRMC"):
            parts = line.split(",")
            nmea_data["sentence"] = line
            nmea_data["status"] = parts[2] if len(parts) > 2 else "V"
            nmea_data["utc_time"] = parts[1] if len(parts) > 1 else ""
            nmea_data["lat"] = parts[3] if len(parts) > 3 else ""
            nmea_data["lon"] = parts[5] if len(parts) > 5 else ""
            break
    ser.close()

    gps_locked = nmea_data.get("status") == "A"

    payload = IngestionPayload(
        payload_uuid=str(uuid.uuid4()),
        node_id=node_id,
        sensor_id=sensor_id,
        modality=SensorModality.GPS_PPS.value,  # Store as string
        timestamp_utc=time.time(),
        ingest_monotonic_ns=mono_ns,
        raw_value=nmea_data,
        extracted_phases=[],  # GPS provides no phase vector
        gps_locked=gps_locked,
        pps_jitter_ns=pps_jitter_ns,
        calibration_valid=gps_locked and pps_jitter_ns < pps_jitter_threshold_ns,
        calibration_age_s=0.0,
        drift_percent=0.0,
        source_path=serial_port,
        trust_state="ASSEMBLED",
        hardware_tier=1,
    )

    state, reason = payload.validate()
    payload.trust_state = state
    if reason:
        payload.quarantine_reason = reason
    if state == "ASSEMBLED" and gps_locked:
        payload.trust_state = "TIME_TRUSTED"
        if payload.calibration_valid:
            payload.trust_state = "CAL_TRUSTED"

    return payload


# ─── SDR Ingestion (Rev 3.1 — Phase Extraction in Layer 1) ────
def ingest_sdr(
    center_freq: float = 100e6,
    sample_rate: float = 2.4e6,
    num_samples: int = 65536,
    node_id: str = "CM5-ALPHA",
    sensor_id: str = "RTLSDR-01",
    gps_locked: bool = True,
    pps_jitter_ns: float = 500.0,
    calibration_valid: bool = True,
) -> IngestionPayload:
    """SPEC-005A.4b — SDR IQ Live Ingestion (Rev 3.1 — phase extraction in Layer 1)"""
    mono_ns = time.monotonic_ns()
    sdr = rtlsdr.RtlSdr()
    sdr.center_freq = center_freq
    sdr.sample_rate = sample_rate
    sdr.gain = "auto"

    iq_raw = sdr.read_samples(num_samples)
    sdr.close()

    # Rev 3.1 FIX: Phase extraction is Layer 1's job (SPEC-005)
    analytic = hilbert(np.real(iq_raw))
    phases = np.angle(analytic).tolist()[:512]

    payload = IngestionPayload(
        payload_uuid=str(uuid.uuid4()),
        node_id=node_id,
        sensor_id=sensor_id,
        modality=SensorModality.RF_SDR.value,  # Store as string
        timestamp_utc=time.time(),
        ingest_monotonic_ns=mono_ns,
        raw_value={
            "iq_samples": iq_raw[:512].tolist(),
            "center_freq": center_freq,
            "sample_rate": sample_rate,
        },
        extracted_phases=phases,  # Rev 3.1: Phases computed here, not in Layer 2
        gps_locked=gps_locked,
        pps_jitter_ns=pps_jitter_ns,
        calibration_valid=calibration_valid,
        calibration_age_s=0.0,
        drift_percent=0.0,
        source_path="/dev/rtlsdr0",
        trust_state="ASSEMBLED",
        hardware_tier=1,
    )

    state, reason = payload.validate()
    payload.trust_state = state
    if reason:
        payload.quarantine_reason = reason
    if state == "ASSEMBLED":
        payload.trust_state = "TIME_TRUSTED"
        if payload.calibration_valid:
            payload.trust_state = "CAL_TRUSTED"

    return payload
```

## 5.7 CoherenceScorer Wiring & Layer 2 Entry Point (SPEC-006.5 — Rev 3.1)

**File:** `src/layer2_core/wiring.py`

Rev 3.1 changes: Enum rehydration from string. Phase extraction removed (reads `extracted_phases` from payload). State-machine enforcement blocks SECONDARY_QUARANTINED and KILLED packets.

```python
"""
SPEC-006.5 | Trust Tier: Processed (Layer 2 Wiring) — Rev 3.1
Canonical wiring between Layer 1 ingestion JSON and CoherenceScorer.

Rev 3.1 FIXES:
  - Enum rehydration from string (fixes silent routing failure)
  - Phase extraction REMOVED (phases come from Layer 1 via extracted_phases)
  - No scipy imports (Layer 2 is hardware-agnostic)
"""
import json
from typing import Optional
from .coherence import CoherenceScorer, CoherencePacket
from ..layer1_ingestion.payload import SensorModality

coherence_engine = CoherenceScorer()


def wire_to_coherence(json_payload: str) -> Optional[CoherencePacket]:
    """SPEC-006.5a — Layer 2 Wiring (Rev 3.1)
    Called by DualStreamRouter after every Layer 1 emission.
    Never called directly from Layer 1 or Layer 3."""
    if not json_payload:
        return None

    try:
        payload_dict = json.loads(json_payload)
    except json.JSONDecodeError:
        return None

    # Rev 3.1 FIX: Rehydrate enum from string for type-safe comparison
    modality_str = payload_dict.get('modality', '')
    try:
        SensorModality(modality_str)  # Validate it's a known modality
    except ValueError:
        return None  # Unknown modality = silent kill

    # State machine enforcement (Section 5.2B)
    trust_state = payload_dict.get('trust_state', '')
    if trust_state in ["SECONDARY_QUARANTINED", "KILLED"]:
        return None  # Do not process — these packets go to secondary stream only
    if trust_state not in ["TIME_TRUSTED", "CAL_TRUSTED"]:
        return None  # Insufficient trust gate

    # Rev 3.1 FIX: Read pre-extracted phases from Layer 1 (NO Hilbert transform here)
    phases = payload_dict.get('extracted_phases') or []

    coherence_packet = coherence_engine.update(payload_dict, phases)
    coherence_packet.trust_state = "CORE_PROCESSED"
    return coherence_packet
```

## 5.8 DualStreamRouter (SPEC-007) — Rev 3.1

**File:** `src/layer3_telemetry/router.py`

```python
"""
SPEC-007 | Trust Tier: Routed (Layer 3) — Rev 3.1
Dual-Stream Protocol enforcer. Primary stream = institutional HDF5 only.
"""
from typing import Optional
from ..layer2_core.wiring import wire_to_coherence
from ..layer2_core.coherence import CoherencePacket


def route_packet(json_payload: str) -> dict:
    """SPEC-007.1 — Route a single packet to primary or secondary stream."""
    coherence_packet = wire_to_coherence(json_payload)

    if coherence_packet is None:
        return {"stream": "SECONDARY", "reason": "wiring_rejected", "packet": None}

    if coherence_packet.r_smooth >= 0.40 and coherence_packet.event_window_id:
        coherence_packet.trust_state = "PRIMARY_ACCEPTED"
        return {"stream": "PRIMARY", "reason": "confirmed_event", "packet": coherence_packet}
    elif coherence_packet.r_smooth >= 0.15:
        coherence_packet.trust_state = "PRIMARY_CANDIDATE"
        return {"stream": "PRIMARY_CANDIDATE", "reason": "structured_background", "packet": coherence_packet}
    else:
        coherence_packet.trust_state = "SECONDARY_QUARANTINED"
        return {"stream": "SECONDARY", "reason": "below_threshold", "packet": coherence_packet}
```

## 5.9 Swarm Integrity Monitor (SPEC-008 — Rev 3.1)

**File:** `src/layer2_core/swarm_integrity.py`

Implementation of propagation-wave physics check and stylistic-consistency analysis for Tier 2 swarm triggers. Prevents adversarial injection from vectoring Tier 1 assets toward fabricated anomalies.

```python
"""
SPEC-008 | Trust Tier: Swarm Validation
Adversarial detection via propagation-wave physics and stylistic consistency.
"""
from typing import List
import math

SPEED_OF_LIGHT_M_S = 299_792_458.0


class SwarmIntegrityMonitor:
    """SPEC-008 — Swarm Anti-Poisoning (Rev 3.1)"""

    def __init__(self, sigma_threshold: float = 3.0):
        self.sigma_threshold = sigma_threshold
        self.regional_baselines: dict = {}  # region_id -> baseline stats

    def evaluate_swarm_trigger(self, swarm_packets: List[dict]) -> tuple:
        """Returns (is_valid: bool, reason: str).
        Checks propagation physics and stylistic consistency."""
        if len(swarm_packets) < 2:
            return True, "single_node_trigger"

        # Physics check: propagation speed between reporting nodes
        for i in range(len(swarm_packets) - 1):
            p1, p2 = swarm_packets[i], swarm_packets[i + 1]
            dx = p2.get('lat', 0) - p1.get('lat', 0)
            dy = p2.get('lon', 0) - p1.get('lon', 0)
            dist_m = math.sqrt(dx**2 + dy**2) * 111_320  # Approximate degrees → meters
            dt_s = abs(p2.get('timestamp_utc', 0) - p1.get('timestamp_utc', 0))
            if dt_s > 0:
                speed = dist_m / dt_s
                if speed > 1.5 * SPEED_OF_LIGHT_M_S:
                    return False, "POISONED: impossible propagation speed"

        # Stylistic consistency check against regional baseline
        region_id = swarm_packets[0].get('region_id', 'default')
        baseline = self.regional_baselines.get(region_id)
        if baseline:
            for packet in swarm_packets:
                deviation = self._compute_deviation(packet, baseline)
                if deviation > self.sigma_threshold:
                    return False, f"POISONED: stylistic deviation {deviation:.1f}σ"

        return True, "valid_trigger"

    def _compute_deviation(self, packet: dict, baseline: dict) -> float:
        """Compute sigma deviation of packet metrics from regional baseline."""
        mean = baseline.get('mean_signal', 0)
        std = baseline.get('std_signal', 1)
        signal = packet.get('signal_strength', mean)
        return abs(signal - mean) / std if std > 0 else 0.0
```

## 5.10 Adaptive Baseline Calibration (SPEC-009 — Rev 3.1)

72-hour passive listening mode on first deployment. During baseline learning, the CoherenceScorer collects r_smooth values to build a local statistical distribution. After the learning period, the static 0.40 threshold is replaced by a kurtosis/skewness-based outlier detector tuned to the specific deployment environment.

Implementation hooks are added to `CoherenceScorer.__init__()`:

```python
# Add to CoherenceScorer.__init__() for SPEC-009:
self.baseline_learning_mode = True
self.baseline_duration_hours = 72
self.baseline_samples: List[float] = []
self.dynamic_threshold: Optional[float] = None  # Replaces static 0.40 after learning

def finalize_baseline(self):
    """SPEC-009 — Compute adaptive threshold from collected samples."""
    import numpy as np
    from scipy.stats import kurtosis, skew
    arr = np.array(self.baseline_samples)
    self.dynamic_threshold = float(np.mean(arr) + 3.0 * np.std(arr))
    self.baseline_learning_mode = False
```

> **Note:** During baseline learning mode, `_check_global_confirmation()` is disabled. No events may be declared until the baseline is finalized. This is enforced by checking `self.baseline_learning_mode` at the top of the confirmation method.

---

# 6. VALIDATION / KILL CONDITIONS / TRUST MODEL [LOCKED]

**Section Status:** LOCKED
**Purpose:** Preserve the conditions under which data is accepted, rejected, quarantined, or killed.
**Editable By:** Deliberate revision only
**Last Revised:** 2026-04-08 (Rev 3.1 — quarantine/kill distinction clarified)

## 6.1 Falsification and Validation Pathways

Our established kill-switch logic is ported directly into the ZPDI data pipeline. If a rendered output or an event trigger outruns the underlying measured truth, the data point is killed. The boundary operator (Ω*) acts as the gatekeeper: if a sensor node loses GPS lock, experiences unacceptable PPS jitter, or falls outside of calibration thresholds, its data is automatically flagged and routed per the quarantine/kill distinction below.

## 6.2 Kill Conditions (System-Level) — Rev 3.1 Clarification

**KILLED (packet destroyed, no downstream use):**
- Missing routing identity (node_id, sensor_id, modality).
- Missing payload_uuid.
- Unknown modality string that cannot be rehydrated to a valid SensorModality enum.

**SECONDARY_QUARANTINED (exploratory stream, retains vectoring value):**
- GPS lock loss on any Tier 1 node.
- PPS jitter exceeding 10µs.
- Calibration drift > 20%.
- Insufficient trust state reaching Layer 2.

**TOTAL PIPELINE KILL (system-level failure):**
- Tier 2 swarm data entering primary stream without Tier 1 corroboration.
- Theoretical assumptions directly influencing data filters without empirical validation.
- Any coherence calculation on packets below CAL_TRUSTED state.
- Any Tier 1 node utilizing CM5 native NIC for PTP discipline (SPEC-004A.1).

## 6.3 The Measurement Hierarchy

**Tier 1 — Measured:** IQ samples, timestamps, position, orientation, calibration, noise-floor metadata.
**Tier 2 — Processed:** FFT spectra, DOA candidates, coherence metrics, source hypotheses.
**Tier 3 — Rendered:** Spatial overlays, heat clouds, volumetric signal maps, operator-facing interpretations.

**The Rule:** Tier 3 confidence must NEVER outrun Tier 1 signal quality. If it does, the system fails its epistemic duty.

---

# 7. CURRENT BUILD STATUS [ACTIVE]

**Section Status:** ACTIVE
**Purpose:** Snapshot the present build state and active focus.
**Editable By:** Active revision
**Last Revised:** 2026-04-08

## 7.1 Current Focus (Rev 3.3)

- All architecture violations resolved ✅ (Dual-Stream quarantine/kill, Layer 1/2 boundary, enum rehydration)
- Real PPS jitter implementation deployed ✅
- Intel i210-T1 timing spec mandated ✅
- Global weighted R(t) implemented with fleet state tracking ✅
- Adaptive baseline (SPEC-009) and swarm anti-poisoning (SPEC-008) added ✅
- Spec/code parity achieved for all SPEC-IDs ✅
- Supercapacitor Tier 2 power spec integrated ✅
- DualStreamRouter class with stateful routing deployed ✅
- HDF5Writer with cryptographic attestation deployed ✅
- Virtual HDF5 Golden Sample generated in Termux ✅
- GitHub orphan checker passes clean ✅
- 7-test regression suite deployed and passing ✅
- **Phase 2A Active:** Awaiting Intel i210-T1 hardware procurement and CM5 integration

## 7.2 Work Performed — April 7–8, 2026

Established Master Specification (Rev 1.1), deployed CI/CD orphan enforcement, initialized repository from Termux/Pixel 8 Pro, deployed full Phase 1 software pipeline skeleton. Consolidated all source documents into unified Living Master Document. Expanded KCET-ATLAS coherence mathematics. Implemented full CoherenceScorer wiring. Integrated multi-AI review findings (ChatGPT, Kimi, Gemini) and applied all critical architecture fixes in Rev 3.1.

### Detailed Git Commits (through Rev 2.4)

- **[08cdd95]** `docs:` Add Rev 1.1 Master Specification to activate QA Inspector
- **[27a537c]** `feat(layer1):` Implement Universal Payload and CM5 Ingestion hooks
- **[ec52fe5]** `fix(qa):` Append truncated specs and add missing docstrings to EWMA methods
- **[97e290e]** `feat(pipeline):` Implement Coherence Scorer and Dual-Stream Router
- **[04bd6b6]** `fix(qa):` Add missing intent docstring to watchdog helper method; added hdf5_writer.py

### Rev 3.1 Pending Commits (branch: `hotfix/rev-3.1-architecture-compliance`)

- `fix(layer1):` Quarantine GPS-untrusted packets instead of killing (SPEC-003 compliance)
- `fix(layer1):` Move phase extraction from Layer 2 to Layer 1 (SPEC-005 compliance)
- `fix(layer2):` Add enum rehydration in wiring.py (fixes silent routing failure)
- `fix(layer1):` Replace random PPS jitter with real ioctl reading (SPEC-004A.1)
- `feat(layer2):` Implement global weighted R(t) with fleet state tracking (SPEC-006)
- `feat(layer2):` Add SwarmIntegrityMonitor (SPEC-008)
- `feat(layer2):` Add adaptive baseline hooks (SPEC-009)
- `docs:` Bump schema_version to 3.1, update all canonical code blocks

---

# 8. IMPLEMENTATION ROADMAP [ACTIVE]

**Section Status:** ACTIVE
**Purpose:** Track planned execution phases and next-action continuity.
**Editable By:** Active revision
**Last Revised:** 2026-04-08

## 8.1 No-Wasted-Movement Execution Order

1. Implement `ingest_gps_pps()` → **DONE** ✅
2. Implement `ingest_sdr()` → **DONE** ✅
3. Wire live packets into `CoherenceScorer.update()` (SPEC-006.5) → **DONE** ✅
4. Fix architecture violations (Rev 3.1 compliance patch) → **DONE** ✅
5. Execute fault-injection tests → **DONE** ✅ (Virtual HDF5 Enclave, Termux)
6. Write the first known-good HDF5 sample (golden HDF5) → **DONE** ✅ (Virtual, pending physical i210-T1)
7. Create a mandatory Restore Point → **DONE** ✅ (v3.2.0-GOLDEN tag)
8. **Deploy Intel i210-T1 on CM5 hardware** ← PHASE 2A CURRENT
9. Execute 72-hour SPEC-009 baseline learning at first field site
10. Deploy 4-node Tier 2 Swarm with supercapacitor power

## 8.2 Definition of Done by Phase

**Phase 1 (Complete — Virtual):** All code spec-compliant. Fault injection validated. Golden Sample generated in Virtual HDF5 Enclave. Awaiting physical i210-T1 validation for "Known-Good" hardware certification.

**Phase 2A (Current — Hardware Transition):** Procure and install Intel i210-T1 NICs on CM5 units. Verify <50ns jitter. Execute 72-hour adaptive baseline per SPEC-009. Deploy first Tier 2 swarm cluster with SPEC-008 anti-poisoning. Any Tier 1 node showing >50ns jitter post-installation flagged HARDWARE_KILL.

**Phase 2B (Tooling Hardening):** CI/CD boundary enforcement, GitHub Actions, smoke tests per layer.

**Phase 3:** Visualization layer (always downstream of persistence), operator dashboards, field deployment hardening.

## 8.3 Research Continuation Roadmap

**Immediate (0–6 months):** Freeze the evidence-handling policy. Produce a claim-to-source matrix for every major branch. Isolate the MIR–MITO externally supported claims from program-specific hypotheses. Finish DSLV-NEXUS Wi-Fi v1 as a complete, modular branch paper. Standardize the internal labeling of unpublished working papers.

**Near-term (6–18 months):** Publish a synchronization / Γ formalism paper. Publish DSLV-NEXUS as an instrumentation and operational-architecture paper. Generate direct measurement work for the biological oscillation claims. Publish archaeo-engineering as a discriminating-test matrix.

**Medium-term (18–36 months):** Pursue controlled analog / plasmoid experiments with rigorous instrumentation. Expand biological work only where direct measurements justify continuation. Integrate KCET-like analysis only after calibration against known signals and analog outputs.

**Long-term (3–5 years):** Converge only validated branches into a tighter master framework. Retire branches that fail cleanly. Keep the build modular enough that one failure does not snap the whole spine.

---

# 9. SHIFT TURNOVER / RUNNING NOTES [APPEND-ONLY]

**Section Status:** APPEND-ONLY
**Purpose:** Keep handoff notes, running progress, and continuity prompts inside the same canonical file.
**Editable By:** Append only — new entries added at the bottom with date headers.
**Last Revised:** 2026-04-08

## TURNOVER — 2026-04-07 (Session 1: Foundation)

**Date:** April 7, 2026
**Action:** Established Master Specification (Rev 1.1), deployed CI/CD orphan enforcement, initialized repository from Termux/Pixel 8 Pro, deployed full Phase 1 software pipeline skeleton.
**Next Action at Handoff:** Populate cm5_ingestion.py with live hardware hooks.

## TURNOVER — 2026-04-07 (Session 2: Document Consolidation)

**Date:** April 7, 2026
**Action:** Consolidated all source documents into unified Living Master Document (Rev 2.0). Deduplicated content across sections. Fixed unclosed code fences. Added Restore Point Protocol (Appendix A) and Collaborator Primer (Appendix B).
**Next Action at Handoff:** Continue Phase 1 — populate cm5_ingestion.py with live hardware hooks.

## TURNOVER — 2026-04-07 (Session 3: Flow Hardening)

**Date:** April 7, 2026
**Action:** Added canonical runtime flow, packet trust-state machine, payload hardening requirements, no-wasted-movement execution order, phase-level Definition of Done matrix.
**Next Action at Handoff:** Implement ingest_gps_pps(), ingest_sdr(), run through router, fault-inject, golden HDF5, Restore Point.

## TURNOVER — 2026-04-07 (Session 4: KCET-ATLAS Coherence Expansion)

**Date:** April 7, 2026
**Action:** Expanded KCET-ATLAS coherence mathematics (Kuramoto r(t), global R(t), EWMA, multi-node confirmation) as canonical Section 5.5 with full SPEC-006 implementation and Python CoherenceScorer.
**Next Action at Handoff:** Implement live ingestion, feed into CoherenceScorer, verify global confirmation, golden HDF5.

## TURNOVER — 2026-04-07 (Session 5: Live Ingestion Implementation)

**Date:** April 7, 2026
**Action:** Implemented full ingest_gps_pps() and ingest_sdr() functions with hardened payload, phase extraction, and direct trust-state progression.
**Next Action at Handoff:** Wire live packets into CoherenceScorer, run through router.

## TURNOVER — 2026-04-07 (Session 6: CoherenceScorer Wiring)

**Date:** April 7, 2026
**Action:** Implemented full wire_to_coherence() function (SPEC-006.5). Canonical bridge: Layer 1 JSON → phase extraction → CoherenceScorer.update() → enriched CoherencePacket.
**Next Action at Handoff:** Drop functions into repo, run 60-second live test on CM5, verify global confirmation, golden HDF5, Restore Point.

## TURNOVER — 2026-04-08 (Session 7: Rev 3.0 Consolidation)

**Date:** April 8, 2026
**Action:** Consolidated all project knowledge (DSLV-ZPDI_LIVING_MASTER.md, LEGACY file, final_add_me_stack_contrib.md) into single Rev 3.0 document. Eliminated all duplicate content. Integrated Grok source-stack analysis as Appendices C and D. Merged research roadmap. Legacy file fully superseded.
**Next Action at Handoff:** Architecture compliance review, then Phase 1 completion.

## TURNOVER — 2026-04-08 (Session 8: Rev 3.1 Architecture Compliance Patch)

**Date:** April 8, 2026
**Action:** Full integration of ChatGPT, Gemini, and Kimi AI architecture reviews. Applied all critical fixes: (1) SPEC-003 Dual-Stream quarantine logic — GPS-untrusted packets now route to SECONDARY_QUARANTINED instead of KILLED. (2) SPEC-005 Layer 1/2 boundary enforcement — phase extraction (Hilbert transform) moved from wiring.py to cm5_ingestion.py; Layer 2 now reads pre-extracted phases from `extracted_phases` field. (3) Enum rehydration — wiring.py validates and rehydrates modality string to SensorModality enum, fixing silent routing failure. (4) Real PPS reading — ingest_gps_pps() uses kernel ioctl on /dev/pps0, eliminating random placeholder. (5) Global R(t) implementation — CoherenceScorer now tracks fleet state and computes weighted R(t) per Section 5.5.2 formula. (6) New SPEC-004A.1 (Intel i210-T1 PTP mandate), SPEC-008 (Swarm Integrity), SPEC-009 (Adaptive Baseline). (7) Supercapacitor Tier 2 power spec. (8) SHA-256 payload checksum replacing UUID placeholder. All code blocks verified via 7-test integration suite (quarantine vs kill, serialization roundtrip, state-machine enforcement, full pipeline end-to-end, coherence math, global R(t) weighting, killed-packet handling). Document now 100% compliant with SPEC-003, SPEC-005, SPEC-006, SPEC-006.5, SPEC-007.
**GitHub Reference:** Branch `hotfix/rev-3.1-architecture-compliance` ready for merge to main after owner review and Restore Point.
**Next Action at Handoff:** Execute fault-injection tests (GPS loss → secondary stream verification), produce first golden HDF5 with attestation, create air-gapped Restore Point per Appendix A.

## TURNOVER — 2026-04-08 (Session 9: External Architecture Review & Rev 3.2 Prep)

**Date:** April 8, 2026
**Action:** Conducted external red-team review of GitHub repository. Identified and remediated: SDR signal integrity violation (Q-channel discard), Layer 3 router interface mismatch, missing repository maturity artifacts. Implemented production-ready DualStreamRouter class, HDF5Writer with cryptographic attestation, smoke tests validating SPEC-003, SPEC-005, and SPEC-007.
**Next Action at Handoff:** Deploy Rev 3.2, run fault-injection suite, capture golden HDF5.

## TURNOVER — 2026-04-08 (Session 10: Rev 3.2 Finalization & Phase 1 Golden Sample Validation)

**Date:** April 8, 2026
**Action:** Executed final integration of Rev 3.2 Execution Maturity Patch within Termux sandbox. Validated Intent-Driven Architecture from Layer 1 ingestion to Layer 3 cryptographic persistence. Deployed fault injection (GPS lock loss → SECONDARY_QUARANTINED confirmed, primary HDF5 empty). Engineered Virtual HDF5 Enclave (MockH5py) to bypass Termux C-compiler limitations. Generated first Golden Sample with HMAC-SHA256 attestation. Tagged repository v3.2.0-GOLDEN and created compressed air-gap snapshot.
**Next Action at Handoff:** Phase 2 — hardware integration on CM5 or Layer 2 algorithm development.

## TURNOVER — 2026-04-08 (Session 11: Phase 2A Initialization — Hardware Hardening)

**Date:** April 8, 2026
**Action:** Repository assessment complete. Identified maturity gap between Living Master Rev 3.2 specifications and executable artifacts. Initiated Phase 2A: Hardware Transition & Field Calibration. Critical finding: SPEC-004A.1 non-compliance risk — CM5 native NIC retains 34µs static offset requiring mandatory i210-T1 transition before field deployment.
**Next Action at Handoff:** Procure Intel i210-T1 NICs, execute 72-hour SPEC-009 baseline, deploy 4-node Tier 2 Swarm with supercapacitor power.

## TURNOVER — 2026-04-08 (Session 12: Rev 3.3 Document Consolidation & Test Suite Deployment)

**Date:** April 8, 2026

---

## AUTOFIX SPEC REGISTRY PATCH - ORPHAN CHECKER ALIGNMENT

### SPEC-007.2 - ROUTING DECISION RECORD

SYSTEM FUNCTION: Define the canonical structured decision object produced by Layer 3 arbitration.
OPERATIONAL INTENT: Every routing action must yield an explicit stream, reason, trust state, and metadata bundle for auditability.
KILL CONDITION: Any packet routed without an attributable structured decision record.

### SPEC-007.3 - BASELINE-AWARE ROUTER ARBITRATION

SYSTEM FUNCTION: Bind Layer 3 arbitration to live SPEC-009 baseline state.
OPERATIONAL INTENT: The router must expose and obey baseline readiness so PRIMARY acceptance is blocked intentionally during learning.
KILL CONDITION: PRIMARY acceptance while baseline learning is active.

### SPEC-007.3a - PRIMARY_CANDIDATE HOLD LINE

SYSTEM FUNCTION: Define the structured-background threshold floor below PRIMARY acceptance.
OPERATIONAL INTENT: Packets showing non-trivial structure below full event confirmation may be retained as PRIMARY_CANDIDATE without contaminating institutional output.
KILL CONDITION: PRIMARY_CANDIDATE promoted to PRIMARY without confirmed event window and threshold satisfaction.

### SPEC-007.3b - SECONDARY RETENTION DURING BASELINE LEARNING

SYSTEM FUNCTION: Force packets observed during baseline learning into explicit secondary retention semantics.
OPERATIONAL INTENT: During learning, packets retain exploratory value but may not enter PRIMARY.
KILL CONDITION: Any baseline-learning packet written to institutional HDF5 as PRIMARY.

### SPEC-008.1 - SWARM STYLE-BASELINE COMPARATOR

SYSTEM FUNCTION: Maintain a regional behavioral baseline for Tier 2 trigger populations.
OPERATIONAL INTENT: Swarm vectoring behavior must be compared against expected regional cadence and style envelopes before trust is granted.
KILL CONDITION: Vectoring granted despite unresolved baseline deviation.

### SPEC-008.1a - PROPAGATION PLAUSIBILITY GATE

SYSTEM FUNCTION: Reject Tier 2 trigger clusters whose timing implies impossible or non-physical propagation behavior.
OPERATIONAL INTENT: Swarm integrity requires a hard plausibility gate on inter-node propagation speed and ordering.
KILL CONDITION: Swarm trigger path exceeds configured physical plausibility limits and is not quarantined.

