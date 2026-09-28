# Distributed Carrier-Phase Coherence Metrology as a Probe of Vacuum Structure

## An instrumented research program with pre-registered kill switches

**Author:** Joseph Robert Fross
**Affiliation:** Resonant Genesis LLC, Penrose, Colorado
**Document class:** White paper / pre-registered instrument program (preprint; prepared for peer-review submission)
**Date:** September 28, 2026 — **Revision 3.4**

**Changes from Rev 3.3.**

- Common-clock calibration run (§4.4, §6). One GPSDO split to two front ends at a single site: Chain C on that pair contains site-common phase and inter-channel biases but no relative clock wander by construction, measuring the non-clock systematic floor directly. The independent-clock co-located pair measures site-common plus relative clock; differencing the two configurations isolates the clock term. Chain C's bound is set by this measured floor. Common-clock failure routes to Switch 3. The run also yields the per-band inter-channel bias calibration (Switch 2's phase-offset-class confound).
- Two hypotheses named in §1. **H_S**: direction-dependent (sky-gradient, anisotropic) anomalous phase → Chain S. **H_C**: isotropic common phase, the title hypothesis → Chain C only. A null on one chain does not constrain the other.
- Chain-S estimator input disambiguated (§4.0). Analysis A consumes per-node post-IGS single-difference residuals (satellite clocks subtracted per node before any inter-node comparison); the double difference is a consistency cross-check, not the primary estimator input.
- Chain-C deliverable (§5). Bound set by the measured relative-clock floor from the common-clock calibration — no Chain-C number quoted tighter than that floor.

**Instrument program:** DSLV-ZPDI — the program's distributed GPS-disciplined SDR receiver array. All "array" references herein denote DSLV-ZPDI nodes unless stated otherwise.

### Epistemic legend

- **[E]** Established experimental or textbook result.
- **[I]** Interpretive synthesis; not required by the data.
- **[H]** Hypothesis of this program. Contingent. Kill-switched.

---

### Abstract

We describe a distributed array of GPS-disciplined software-defined-radio receivers (DSLV-ZPDI) that measures pairwise carrier-phase coherence residuals on the GPS L1/L5 broadcast carriers after subtraction of electromagnetic propagation (Helmholtz), site multipath, clock terms, common-view GNSS errors, tropospheric delay, and ionospheric gradients. Two processing chains are distinct by construction. Chain S uses between-satellite single differences and is blind to isotropic site-common phase; it tests direction-differential (sky-gradient) residuals (H_S). Chain C uses same-satellite inter-node differences and keeps receiver-common phase; it tests isotropic common phase (H_C), the title hypothesis, with receiver clocks carried by IGS products, measured GPSDO stability, and a pre-registered common-clock calibration that isolates the relative-clock floor. The per-node tracking product is prompt-correlator carrier phase at dump rate f_d. Two pre-registered analyses are distinct. Analysis A bounds stationary residual coherence of the windowed spectra of the post-subtraction chain residual against a closed-form Beta null and a moving-block bootstrap; its floor is set by the effective number of independent samples, not calendar seconds, with block length set by Politis–White selection on pilot data. Analysis B forms a lag-resolved cross-correlation on a pre-registered τ grid with bootstrap-max multiplicity control and lag resolution f_d⁻¹; the test |τ|≪τ_c is claimed only on baselines with τ_c≫f_d⁻¹. At nominal dump rates, regional baselines are resolution-limited for that morphology. Analysis A runs continuously and selects windows for deep Analysis-B follow-up; the joint selection-to-detection false-alarm rate is calibrated end-to-end by time-slides on the post-subtraction residuals. A worked dual-frequency L-band budget shows the run is systematics-limited, with a per-snapshot differential phase floor of ≈ 0.3–0.8 rad set by troposphere and multipath under standard geodetic site engineering. This program tests no predicted amplitude: it sets chain-specific upper bounds on anomalous RF phase coherence — Chain C's bound set by the measured relative-clock floor — and a null is the expected result. Six instrument kill switches are stated, including a chromatic (uncombined L1/L5) falsification pathway for any candidate excess. Bio-acoustic and aqueous-coherence studies remain companion work and do not gate the array. Any positive result is a data result, not an ontology.

**Keywords:** distributed metrology, carrier-phase coherence, GPS-disciplined oscillators, software-defined radio, magnitude-squared coherence, null experiments, pre-registration

---

## 1. The operational question

Textbook QED on Minkowski space treats the vacuum as the Poincaré-invariant ground state and localized excitations as particles. That account works in scattering and precision spectroscopy **[E]**. This program does not replace it.

Operational question: after subtracting everything standard physics predicts — propagation, multipath, clocks, common-view GNSS, troposphere, ionospheric gradients, and catalogued transmitters — does a residual pairwise phase coherence remain that is inconsistent with the pre-registered null?

That question is not unique. An isotropic phase common to every tracked carrier at one antenna is cancelled by a between-satellite single difference. A satellite-common term is cancelled by a same-satellite inter-node difference. The program therefore states two observables and two bounds (§3).

Two hypotheses, named so the bounds mean something. **H_S**: an anomalous phase coupling that depends on propagation direction — a sky gradient, anisotropic vacuum structure. Tested by Chain S, which cancels isotropic site-common phase by construction. **H_C**: an isotropic common phase, identical at every antenna regardless of which satellite is tracked — the title hypothesis. Tested only by Chain C, which keeps receiver-common phase and therefore inherits the receiver-clock problem (§§3.1, 4.4, 5). The two chains are complementary and neither subsumes the other: a null on Chain S does not constrain H_C, and a null on Chain C does not constrain H_S. The title hypothesis lives on the harder chain. That asymmetry is the point of naming them.

Carrier-phase GNSS already treats phase as the primary observable; RTK resolves cycles to millimetre precision **[E]**. This program extends that practice from positioning to a null search on distributed residuals. The array is a phase microscope pointed at zero.

What counts as interesting is defined in §§4–6. Everything else is scaffolding.

---

## 2. Prior art and the gap

**Holometer (Fermilab).** Closest interferometric prior art: two co-located 39 m Michelson interferometers, cross-spectrum to tens of MHz, including frequencies above the inverse light-crossing time of the apparatus. First published sensitivity 2.1×10⁻²⁰ m/√Hz after 2×10⁸ independent spectra; nulls reported on holographic shear/length noise at that floor **[E]** (Chou *et al.*, *Phys. Rev. Lett.* **117**, 111102 (2016); instrument paper arXiv:1611.08265).

Difference, stated so a reviewer does not have to reconstruct it: the Holometer is co-located optical strain at one site. This program is RF carrier-phase residuals across geographic baselines at ~10³ MHz. A null here constrains a different observable class. It does not repeat or refute the Holometer.

**Clock networks and GNSS as exotic sensors.** A second line of prior art treats GNSS constellations and terrestrial clock networks as sensors for physics beyond the Standard Model. Derevianko & Pospelov proposed the GPS atomic-clock constellation as a detector of topological dark matter **[E]**, and Roberts *et al.* placed limits on domain-wall couplings using GPS satellite clock comparisons **[E]**. Those searches look for transient, propagating frequency modulation in clock comparisons. The present program's observable class — stationary, spatially distributed carrier-phase coherence after geodetic subtraction — is complementary: it requires no transient and compares phases, not frequencies. The two literatures do not constrain each other's channels, and a bound here is new information.

**Methodological prior art.** Morphology-agnostic detection with proper trials factors is standard practice in gravitational-wave burst searches. This program adopts the excess-power family of statistics (Anderson *et al.* 2001) and time-slide background estimation (e.g., Abadie *et al.* 2012) for Analysis B and for the joint Analysis-A→B false-alarm calibration **[E]**.

**Coherence statistic, not a dynamical model.** Pairwise phase coherence on a window ΔT:

$$r_{kl}(t)=\left\lvert\frac{1}{\Delta T}\int_t^{t+\Delta T}e^{i(\phi_k(t')-\phi_l(t'))}\,dt'\right\rvert.$$

Kuramoto/Strogatz are cited for the statistic only **[E]**. No coupled-oscillator dynamics are asserted for the hardware. (See §3 for the one sense in which the nodes are not independent — the GPSDO steering band — and how it is excluded.)

Phase distance $d_\phi(a,b)=\min_n\lvert\phi_a-\phi_b-2\pi n\rvert$ and metric distance $d_g$ are independent observables. The empirical question **[H]** is whether $d_\phi\approx0$ still predicts correlated records at large $d_g$ after every standard correlated term is removed, **on a named chain, under a named hypothesis**.

---

## 3. The instrument

A DSLV-ZPDI node: GNSS-disciplined oscillator, SDR, local E/B, optional barometric and radiogenic channels.

**Tracked carriers.** GPS broadcast carriers L1 (f₁=1575.42 MHz, λ≈19.0 cm) and L5 (f₂=1176.45 MHz, λ≈25.5 cm). Frequency ratio f₁/f₂=154/115≈1.339. The constellation is the transmitter network; IGS final orbit/clock products are part of the null. Each node's SDR front end tracks every in-view satellite against the local GPSDO. Per-dump carrier phase φₖ⁽ᵖ⁾[n] is taken from the prompt correlator.

### 3.1 Two processing chains

An additive phase that is common to every tracked satellite at one antenna cancels in a between-satellite single difference. An additive phase that is common to one satellite at every antenna cancels in a same-satellite inter-node difference. The hypothesis in the title is not a single observable. Two chains are defined and pre-registered.

**Chain S — sky-gradient (H_S).** Between-satellite single difference at node k, same band:

$$\phi_k^{(pq)}(t)\equiv\phi_k^{(p)}(t)-\phi_k^{(q)}(t).$$

This cancels the receiver clock and any isotropic site-common phase at first order **[E]**. Inter-node comparison of the same pair (p,q), and the between-node double difference

$$\nabla\Delta_{kl}^{(pq)} =\phi_k^{(pq)}-\phi_l^{(pq)},$$

additionally cancel satellite-clock and common-view ephemeris terms when combined with IGS final products **[E]**. Chain S is **blind** to isotropic site-common phase. A null on Chain S bounds anomalous *inter-satellite differential* coherence, not isotropic common-mode phase, and does not constrain H_C.

**Chain C — site-common (H_C).** Same-satellite inter-node single difference, same band:

$$\Delta_{kl}^{(p)}(t)\equiv\phi_k^{(p)}(t)-\phi_l^{(p)}(t).$$

This cancels the satellite clock at first order and **keeps** receiver-common and site-common phase **[E]**. Receiver clocks do not cancel; they are modelled with IGS products and the measured ADEV of the installed GPSDOs, and the relative-clock contribution is isolated by the common-clock calibration (§4.4). Chain C is the chain that can bound isotropic site-common phase. It is exposed to residual receiver-clock leakage below and near the steering bandwidth (guard band, below).

Double difference is Chain S's clock-killed product. It is not a third hypothesis class.

A licensed ground beacon remains a possible future secondary tone; it would require its own budget rows and is out of scope.

### 3.2 Residuals, not raw differences

Analyses A and B consume **post-subtraction residuals** of the named chain: IGS final orbit and clock, tropospheric hydrostatic and wet mapping, ionospheric first-order term (bound product) or the uncombined dual-frequency pair (classification product), and the site multipath phase-error model. Raw Chain-S single differences of the same (p,q) at two nodes are coherent because they share satellite clocks. That coherence is not a detection.

### 3.3 Bound product and classification product

- **Bound product.** Iono-free or dual-frequency-corrected residual of Chain S and, separately, of Chain C. This is the §5 number and the Analysis-A/B detection statistic for Switch 1.
- **Classification product.** L1 and L5 **uncombined**, same windows and same chain as any candidate. This is Switch 2. The iono-free combination mixes the two carriers and destroys the chromatic ratio; it is never the Switch 2 observable.

### 3.4 Timing numbers

Two timing numbers, not to be conflated:

- **Snapshot alignment.** GNSS 1 PPS / timestamp to ≪100 ns so records sit on a common grid. Bookkeeping, not the science floor. At L1, 100 ns is ≈157 full carrier cycles.
- **Phase stability.** Short-term ADEV of the disciplined OCXO sets the reference contribution to φₖ⁽ᵖ⁾ before chain combinations. For σ_y(τ)≈10⁻¹² at τ=1 s (mid-grade OCXO GPSDO **[E]**),

$$\sigma_\phi\approx 2\pi f_1\tau\sigma_y\approx 9.9\times 10^{-3}\,\mathrm{rad}$$

at f₁=1575.42 MHz. A 10⁻¹¹ unit is ten times worse. On Chain S the receiver clock cancels; the residual requirement enters through inter-channel biases and timestamping. On Chain C the receiver clock remains and the measured ADEV is load-bearing, with the relative-clock floor isolated by §4.4. Quote the measured ADEV of the installed unit, not a catalog class.

**Synchronization requirement, per baseline.** Let τ_c=d_g/c. Any claim about lag structure requires σ_sync≪τ_c, where σ_sync is the residual uncertainty of the time-transfer method *after* common-view correction. For 10 km (τ_c=33 µs), common-view GNSS (ns-level) suffices. For co-located or sub-km baselines (τ_c≲1 µs), White Rabbit or two-way optical transfer is required **[E]**. GPS 1 PPS alignment is a simultaneity *convention*, not a measurement; the transfer method per baseline is pre-registered (§6). An excess at "τ≈0" is only meaningful against the stated σ_sync of its baseline.

**Guard band: where the nodes are not independent.** Every GPSDO slaves its OCXO to GPS time through a steering loop of bandwidth 10⁻³–10⁻² Hz. Below that bandwidth, receiver-clock leakage is common-mode by construction. Frequencies below the measured loop bandwidth of the installed units (pre-registered per unit) are excluded from both analyses on **both chains**. The exclusion is mandatory on Chain C and conservative on Chain S. The testable frequency band is bounded below by the steering loop and above by half the prompt dump rate (§4.0); the number of independent samples within that band is bounded by the atmospheric correlation time (§4.2).

| Symbol | Quantity | Unit |
|---|---|---|
| φₖ⁽ᵖ⁾(t) | carrier phase, satellite p, vs local GPSDO | rad |
| φₖ⁽ᵖᑫ⁾(t) | Chain S: between-satellite single difference | rad |
| Δₖₗ⁽ᵖ⁾(t) | Chain C: same-satellite inter-node difference | rad |
| ∇Δₖₗ⁽ᵖᑫ⁾ | between-node double difference (Chain-S cross-check) | rad |
| f_d | prompt-correlator dump rate | Hz |
| rₖₗ | pairwise coherence (Analysis A) | 1 |
| Ĉₖₗ(τ), r̂ₖₗ(τ) | lag cross-correlation / normalized lag coherence (Analysis B) | rad² / 1 |
| Qₖ(t) | quadrature residual after lock | V |
| τₖ | clock offset to ensemble | s |
| Γ_ext(t) | Kp, local B, pressure; optional radon | mixed |

**Null model, correlated terms included.** Thermal noise, oscillator phase noise (residual after the chain's clock cancellation), multipath, clock residuals appropriate to the chain, common-view GNSS, tropospheric hydrostatic and wet delay, ionospheric TEC gradients, and catalogued transmitters through G_km. Dual-frequency GNSS and IGS final orbit/clock products are part of the null **[E]**. Any of these produces real inter-site coherence that is not new physics.

**Band selection and the 1/f² argument.** Ionospheric *group* delay (and ionospheric *range* on the carrier, opposite sign) scales as 1/f² in metres: Δt=40.3·TEC/(c·f²). A 0.1 TECU uncorrected residual — optimistic for single-frequency work — is ≈8.4 rad of differential *phase* at 100 MHz but ≈0.53 rad at L1, a factor of (15.75)²≈248. Carrier phase **in radians or cycles** scales as 1/f. The dual-frequency iono-free combination removes the first-order term in the **bound product** **[E]**, leaving higher-order residuals at the millimetre level. The worked budget in §5 is L-band (L1 + L5). A sub-100 MHz carrier-phase coherence measurement across km baselines is uncorrectable with current TEC products; any band other than L-band (or higher) requires its own ionospheric error row and a spectrum-survey hash before the science run.

---

## 4. Estimators

### 4.0 Data path: from tracked carrier to analysis streams

The tracking loop is standard GNSS practice **[E]** (Kaplan & Hegarty).

1. **Raw.** Wideband complex IQ at sample rate f_s, held in a ring buffer (depth pre-registered; e.g. 300 s) for reprocessing and forensics.
2. **Tracking.** Per-satellite carrier and code tracking loops produce prompt-correlator I/Q dumps at dump rate f_d (pre-registered; nominal 1–10 kHz). Per-dump carrier phase φₖ⁽ᵖ⁾[n]=atan2(Q_p[n],I_p[n]).
3. **Chain construction.** Form Chain S (φₖ⁽ᵖᑫ⁾) and Chain C (Δₖₗ⁽ᵖ⁾) at rate f_d. Subtract the §3 null models (IGS geometry and clocks, troposphere, ionosphere as appropriate to the product, multipath phase-error model). The post-subtraction residual of each chain is recorded continuously. For Chain S, IGS satellite-clock correction is applied **per node before any inter-node comparison**: Analysis A consumes the per-node post-IGS single-difference residuals. The between-node double difference ∇Δₖₗ⁽ᵖᑫ⁾ is formed as a consistency cross-check on the same data, not as the primary estimator input — the estimator equation (§4.2) takes per-node series.
4. **Analysis A** consumes windowed spectra of the post-subtraction residual of a named chain (§4.2). **Analysis B** consumes that residual in the time domain (§4.3).

**Dump-rate tradeoff.** Coherent integration time T=1/f_d sets both per-dump phase precision, σ_φ,dump≈1/√(2·C/N₀·T), and lag resolution δτ=1/f_d. Raising f_d sharpens the lag grid at the cost of per-dump SNR; lag-correlation integration over the trigger window recovers sensitivity per the radiometer equation. f_d is pre-registered (§6). The Analysis-B morphology test |τ|≪τ_c additionally requires τ_c≫f_d⁻¹ (§4.3).

A wideband residual-RF lag correlation at f_s (IQ minus reconstructed known signals) is a natural Analysis-B extension with microsecond lag resolution; it requires its own subtraction-fidelity budget row and is out of scope for this revision. Until it is in scope, regional baselines do not support a spacelike morphology claim.

### 4.1 Residual snapshot

On the post-subtraction residual of a named chain (or its windowed spectrum),

$$y_k(\omega)=s_k(\omega)+n_k(\omega),$$

$$\hat s_k(\omega)=\sum_m G_{km}(\omega)\,q_m(\omega)\,e^{-i\omega\tau_k},$$

$$\tilde y_k(\omega)=\bigl(y_k(\omega)-\hat s_k(\omega)\bigr)e^{i\omega\hat\tau_k}.$$

Implemented on the chain observable, the q_m are the tracked GNSS carriers, the sum runs over the satellites entering that chain product, and G_km is the multipath phase-error model plus geometric terms. **Definition for §§4.2–4.3:** ỹₖ(ω) denotes the windowed Fourier coefficients of the post-subtraction residual of the named chain; in §4.3 the same residual series is used in the time domain as ỹₖ[n]. Chain index (S or C) and product (bound or classification) are part of the series name in the archive.

### 4.2 Analysis A — stationary coherence (bound)

On L non-overlapped windows of the named-chain residual:

$$\hat r_{kl}^{\mathrm{(res)}}(\omega) = \frac{\bigl\lvert\sum_{\ell=1}^{L}\tilde y_k^{(\ell)}\tilde y_l^{(\ell)*}\bigr\rvert} {\sqrt{\sum_\ell\lvert\tilde y_k^{(\ell)}\rvert^2}\sqrt{\sum_\ell\lvert\tilde y_l^{(\ell)}\rvert^2}}.$$

Magnitude-squared coherence γ̂=(r̂^(res))². For windowed spectral coefficients that are complex-Gaussian under the null (asymptotic for stationary series; approximate for 1/f-type residuals — hence the bootstrap below), γ̂∼Beta(1,L−1) **[E]** (Goodman; Carter; Gish and Cochran invariance), so

$$\mathbb{E}[\hat\gamma]_{\mathrm{null}}=\frac{1}{L}, \qquad \mathrm{Var}(\hat\gamma)_{\mathrm{null}}=\frac{L-1}{L^2(L+1)}\sim\frac{1}{L^2}.$$

Two qualifications: (i) the Beta law assumes non-overlapped windows and nominal degrees of freedom; overlapped windows alter the DOF and are not used in the science run; (ii) the per-window re-phasing e^{iωτ̂ₖ} consumes degrees of freedom and perturbs the null at O(1/L²); the block bootstrap, not the analytic tail, is the decision statistic.

Large-L magnitude floor, used only as a check against the Beta tail:

$$\mathbb{E}[\hat r]_{\mathrm{null}}\approx\sqrt{\frac{\pi}{4L}}, \qquad \sigma_{\mathrm{null}}\approx\sqrt{\frac{4-\pi}{4L}}\approx\frac{0.463}{\sqrt{L}}.$$

**Independence is not free.** Calendar seconds are not independent. Multipath dwell, flicker frequency noise, GNSS geometry (≈11.97 h repeat), and diurnal ionosphere set a correlation time τ_corr. Oscillator and atmospheric residuals are 1/f-type processes, for which a lag-1 autocorrelation is ≈1 at almost any sampling and carries almost no information about the effective sample size. Accordingly

$$L_{\mathrm{eff}}=\frac{T}{\tau_{\mathrm{corr}}}$$

with τ_corr obtained two ways on pilot data and reconciled before the science run: (a) the Politis–White automatic block-length selection for the moving-block bootstrap applied to ỹₖ **[E]**; (b) an Allan-deviation-informed independence time from the measured σ_y(τ) turnover of the installed units **[E]**. The block length is then frozen in the pre-registration (§6). Detection uses L_eff or the bootstrap, never raw L.

Cramér–Rao phase floor on a tone, complex AWGN, N_s samples **[E]** (Kay 1993):

$$\mathrm{Var}(\hat\phi)\ge\frac{1}{2N_s\,\mathrm{SNR}}.$$

**Multiplicity across pairs, bands, and chains.** N nodes yield N(N−1)/2 pairs whose test statistics share nodes and are therefore positively correlated; bands and the two chains are likewise correlated through common systematics. Benjamini–Hochberg FDR control remains valid under positive regression dependence (PRDS) **[E]** (Benjamini–Yekutieli 2001). Chain S and Chain C are separate families in the pre-registration; FDR is applied within family and the joint accounting is stated.

### 4.3 Analysis B — lag-resolved cross-correlation

On the named-chain residual at dump rate f_d, lag resolution δτ=f_d⁻¹:

$$\hat C_{kl}(\tau)=\frac{1}{N}\sum_{n}\tilde y_k[n]\,\tilde y_l^*[n-\tau f_d],$$

$$\hat r_{kl}(\tau)=\frac{\lvert\hat C_{kl}(\tau)\rvert}{\sqrt{\hat C_{kk}(0)\,\hat C_{ll}(0)}}.$$

Light-travel time on baseline d_g: τ_c=d_g/c.

**Resolution requirement.** The morphology test |τ|≪τ_c requires τ_c≫f_d⁻¹. Baselines not satisfying this at the pre-registered f_d are **resolution-limited** for the lag test: they contribute fully to Analysis A and to the coarse Analysis-B grid; no |τ|≪τ_c claim is made on them.

| f_d | δτ=f_d⁻¹ | d_g at τ_c=δτ | d_g at τ_c=10δτ |
|---|---|---|---|
| 1 kHz | 1 ms | 300 km | 3000 km |
| 10 kHz | 100 µs | 30 km | 300 km |
| IQ @ 2 MHz (deferred) | 0.5 µs | 150 m | 1.5 km |

At nominal dump rates, a 10 km pair (τ_c=33 µs) and a 100 km pair (τ_c=333 µs) are resolution-limited for |τ|≪τ_c. Analysis B on those baselines is a coarse-lag companion to Analysis A, not a spacelike morphology test. Raising f_d or activating the deferred IQ path extends the testable set; that choice is pre-registered, not tuned post hoc.

A 1 s Analysis-A window cannot locate a peak to better than 1 s and cannot declare a lag spacelike on any terrestrial baseline. Analysis B publishes r̂ₖₗ(τ) on a pre-registered τ grid containing {0, ±τ_c, ±τ_iono, ±τ_trop} and a uniform span of ±Mτ_c (M pre-registered), at native resolution δτ=f_d⁻¹.

**Multiplicity control.** The detection statistic is the maximum of r̂ₖₗ(τ) over the grid. Significance is set by a moving-block bootstrap of that maximum (block length per §4.2). No per-lag κ claims are permitted.

**Trigger-selection bias and its closure.** Deep Analysis-B follow-up runs on windows selected because Analysis A crossed threshold — the same noise realization. The pipeline is calibrated end-to-end: the full chain (A selection → B on selected windows) is run on time-slides — one node's residual shifted by unphysical offsets ≫τ_corr — with the slide count and the joint false-alarm rate pre-registered **[E]**. Slides are applied to the **post-subtraction residual streams**, so the slide background measures the background of the residual null. Correlated residuals that survive the §3 subtraction are not part of the slide background; they are the subject of Switch 1. A candidate must additionally survive a hold-out confirmation window: post-window residual data, excluded from the detection statistic, must independently show the morphology at the pre-registered level.

**Triggered architecture and data volume.** Analysis A runs continuously on each chain residual. Each node maintains the wideband-IQ ring buffer (§4.0) for reprocessing and forensics; when Analysis A exceeds its pre-registered trigger threshold in any band, the buffer (± window) is dumped at all nodes simultaneously. Trigger-distribution latency (≪1 s over any terrestrial IP path) is negligible against the 300 s dwell. Continuous full-rate B recording is not required. Chain residuals are continuous and cheap (tens of kB/s per node).

Interpretation, pre-registered, **per chain, under a named hypothesis**:

- Direct propagation from any single source satisfies |τ|≤τ_c, with equality only for a source on the baseline axis. Peak at τ=τ_c or a catalogued multipath extra delay: ordinary propagation. Switch 1 fails for that candidate.
- A peak at |τ|>τ_c cannot be direct propagation. If it matches no catalogued multipath delay, it is dispersive or instrumental and triggers a pipeline investigation under Switch 3.
- Peak at |τ|≪τ_c (including τ≈0 within the baseline's stated σ_sync), **on a baseline satisfying** τ_c≫f_d⁻¹, that vanishes in the co-located control and vanishes when IGS/iono terms are applied: a candidate for injection-matched follow-up, subject to Switch 2, labelled with its chain and hypothesis (H_S or H_C).
- Peak at |τ|≪τ_c that also appears in the co-located pair is site-common hardware (RFI, supply, local field) unless Chain C is the intended target *and* the common-clock calibration (§4.4) has excluded the hardware reading. Co-located excess is not anomalous on Chain S.
- A common mode that is real on Chain C (H_C) would appear at |τ|≪τ_c in both co-located and separated pairs, with δτ≪τ_c and σ_sync≪τ_c, would survive the common-clock decomposition in §4.4, and would pass Switch 2 in the delay class. That is the only Chain-C morphology worth a data paper, and only on baselines that are not resolution-limited.
- A τ≈0 excess, even if every switch is passed, is common-mode noise. It is not superluminal signaling. No information transfer is possible via a common-mode field.

### 4.4 Injection / recovery

Before any science run: inject synthetic correlated phase at known amplitude and known lag into the raw stream; run the full pipeline on **both chains**; require recovery of amplitude and lag within pre-registered tolerance; require return to the null floor with injection off. Injections include (i) isotropic site-common phase (must appear on Chain C and vanish on Chain S — the H_C signature) and (ii) direction-differential phase (must appear on Chain S — the H_S signature). A chain that fails its distinctive injection has no standing to report an excess.

**Blind injections.** A pre-registered number of injections per campaign are seeded by an injection holder who is not on the analysis team, with amplitude, lag, and chain-class drawn from pre-registered distributions and revealed only after the analysis of record is frozen. Open injections test the pipeline; blind injections test the analysts. Small-team implementation: a sealed-seed script held by a designated non-analyst; the mechanism is pre-registered, not the seed.

**Common-clock calibration (breaks the Chain-C clock degeneracy).** Before the science run, and repeated per campaign: one GPSDO output split to drive two complete front-end + SDR chains at a single site (common clock; independent RF paths and antennas at metre-scale separation). Chain C formed between these two front ends contains site-common phase and inter-channel biases but **no relative clock wander by construction** — it measures the non-clock systematic floor of Chain C directly, including per-channel L1/L5 inter-channel bias differences (the phase-offset-class confound for Switch 2). The independent-clock co-located pair measures site-common *plus* relative clock wander; differencing the two co-located configurations isolates the relative-clock contribution. **Chain C's bound (§5) is set by this measured floor.** A common-clock pair that does not sit on its predicted null routes to Switch 3 before any science claim.

---

## 5. Sensitivity budget (worked example, Analysis A, L-band)

Order-of-magnitude engineering estimates, except where marked measured. Differential noise sets the per-snapshot floor σ_φ; correlated threats must be subtracted by the null, and whatever survives is adjudicated by Switch 1. Numbers below are for the **bound product**.

**(a) Differential noise rows → per-snapshot σ_φ (RSS):**

| Parameter | Assumed value | Basis |
|---|---|---|
| Carriers f₀ | GPS L1 1575.42 MHz + L5 1176.45 MHz | §3 |
| Chain S observable | per-node post-IGS SD residual; DD as cross-check | receiver clock and isotropic site phase cancel **[E]** |
| Chain C observable | same-satellite inter-node SD residual + IGS | satellite clock cancels; receiver clock remains **[E]** |
| Tropospheric wet-delay residual | 1 cm ⇒ ≈0.33 rad at L1 | mapping-function and water-vapor limits **[E]** (Saastamoinen class) |
| Multipath residual, post-model | 0.5–2 cm ⇒ 0.17–0.66 rad | site-dependent; specular ground bounce **[E]** |
| Antenna PCV + cable + front-end phase | placeholder 0.1 rad; measured per unit | catalog values not accepted |
| Thermal noise on carrier | 1 mrad | high-SNR broadcast carriers |
| GPSDO reference | 10 mrad at 1 s before combination | installed ADEV; cancels on Chain S |
| Chain-C relative-clock floor | **measured, per campaign** | common-clock calibration (§4.4); **sets the Chain-C bound, not the RSS** |
| **Per-snapshot σ_φ (RSS), Chain S** | **≈0.3–0.8 rad** | **troposphere + multipath** |

**(b) Correlated-threat rows → null subtraction + Switch 1 (not in the RSS):**

| Threat | Handling |
|---|---|
| Common-view satellite orbit/clock residuals (IGS final: orbit ≈2 cm, clock ≈75 ps class) | subtracted per-node via IGS on Chain S and via IGS on Chain C **[E]**; survival → Switch 1 |
| Ionospheric gradients (first order removed in the bound product) | dual-frequency combination **[E]**; higher-order residual characterized on pilot data; survival → Switch 1 |
| Site-common RFI / supply / local field | co-located pair (independent clocks, shared site, metre-scale antenna separation — mutual coupling characterized, not created; multipath similarity measured, not assumed). On Chain S this class must vanish; on Chain C it is the hypothesis class (H_C) and is separated from hardware by the common-clock calibration (§4.4), Switch 2, and Switch 6 |
| Inter-channel (L1/L5) bias differences | calibrated per campaign in the common-clock run; the phase-offset-class confound for Switch 2 |
| Transmitter catalog leakage | catalog version frozen; injection bounds pipeline leakage |

| Run parameters | |
|---|---|
| Calendar snapshots | 86,400 (24 h at 1 s Analysis-A windows) |
| L_eff (illustrative) | 10²–10³ (§4.2 on pilot data) |
| Detection | block-bootstrap null on γ̂, FDR (PRDS) per chain family; bootstrap-max over τ grid for B; joint FAR by time-slides on residuals |

If one incorrectly used L=86400:

$$\mathbb{E}[\hat r]_{\mathrm{null}}\approx 3.0\times 10^{-3}, \quad \sigma_{\mathrm{null}}\approx 1.6\times 10^{-3}, \quad r_{\min}(\kappa=3)\approx 7.7\times 10^{-3}.$$

That number is not the program floor. For L_eff=300 (τ_corr=288 s): E[γ̂]_null=1/300≈3.3×10⁻³, r_min∼O(10⁻¹). The statistical floor moves as √(86400/L_eff). Systematics sit above both.

**Weak common phase.** Two nodes, shared phase φ_s (rms), independent residual phase σ_φ, treating the phase records as the measured quantity:

$$r\approx\frac{\varphi_s^2}{\varphi_s^2+\sigma_\phi^2}\approx\frac{\varphi_s^2}{\sigma_\phi^2}, \qquad \varphi_s\approx\sigma_\phi\sqrt{r},$$

when φ_s≪σ_φ. The RSS floor σ_φ≈0.3–0.8 rad is not ≪1; the millimetre conversion is an order-of-magnitude map, not an estimator.

With σ_φ=0.3 rad: calendar r_min=7.7×10⁻³ gives φ_s≈26 mrad, ≈0.8 mm equivalent path at L1. With L_eff=300: φ_s≈0.11 rad, ≈3.3 mm. Report both, report the measured L_eff, and report Chain S and Chain C separately. The systematic floor governs.

**Deliverable.** Two bounds, set by different floors. **Chain S (H_S):** upper bound on anomalous sky-gradient residual phase at O(0.1 rad) (mm–cm equivalent path at L1) under standard geodetic site engineering, improving only as the measured rows improve. **Chain C (H_C):** upper bound on isotropic site-common phase set by the **measured relative-clock floor** from the common-clock calibration (§4.4) — no Chain-C number is quoted tighter than that floor, whatever the atmospheric RSS says. Multipath and troposphere decorrelate between nodes and inflate σ_φ rather than fake a signal; correlated terms are the danger and are handled by subtraction plus Switch 1.

---

## 6. Pre-registration and data release

Frozen before first science run, timestamped public registry:

- science band and spectrum-survey hash
- signal definition: tracked signals, f_d, elevation masks, per-dump SNR characterization
- chain definitions: Chain S construction (per-node post-IGS SD residuals as estimator input; DD as cross-check), Chain C construction; distinctive injection waveforms for H_S and H_C
- product definitions: bound product (iono-free / dual-frequency-corrected) vs classification product (L1 and L5 uncombined)
- Analysis A: window length (non-overlapped), Politis–White parameters and frozen block length, Allan cross-check, guard band f_loop per installed unit, selection thresholds to B, FDR procedure with PRDS clause and per-chain families, transmitter catalog version, G_km version per site
- Analysis B: τ grid (M, special lags), bootstrap-max procedure, peak-location classifier, time-slide count and joint FAR target, hold-out window criteria, **resolution-limited baseline list at the chosen f_d**
- IQ ring-buffer depth, dump window, multi-node dump coordination
- per-baseline time-transfer method and stated σ_sync
- open injection schedule, amplitudes, lags, chain-class, pass/fail windows; blind-injection count, distributions, and the identity (not the data) of the injection holder
- **common-clock calibration: splitter and front-end configuration, run schedule per campaign, predicted-null pass/fail criteria, per-band inter-channel bias calibration file hashes**
- installed GPSDO ADEV curves; measured per-node analog-chain phase vs temperature; antenna PCV calibration file hashes; co-located-pair mutual-coupling characterization
- Switch 2 pass criteria: chromatic scaling classes and tolerances on the classification product, φ in radians or cycles
- exact null including §3 correlated terms, per chain, per hypothesis

Raw IQ or residuals, pipeline code, injection logs (open and, after unblinding, blind), and slide backgrounds published regardless of outcome. A null is a publishable pair of upper bounds (Chain S → H_S, Chain C → H_C) on anomalous distributed RF phase coherence at the measured L_eff and systematic floor.

---

## 7. Kill switches

Instrument switches only. Companion biology is Appendix B and does not gate §§1–6.

1. **Array residual (primary), per chain, per hypothesis.** Analysis A: γ̂ consistent with the Beta / bootstrap null after pre-registered subtraction, FDR-controlled (PRDS), every pair and band, **separately for Chain S (H_S) and Chain C (H_C)**. Analysis B: the bootstrap-max over the τ grid is consistent with the time-slide-calibrated null; any excess peaks at |τ|≥τ_c (noting that |τ|>τ_c without a catalogued multipath explanation routes to Switch 3), vanishes when common-view/ionospheric/IGS terms are included, or — on Chain S — is confined to the co-located control. The anomalous morphology class |τ|≪τ_c is claimed only on baselines with τ_c≫f_d⁻¹. A null on Chain S is not a null on Chain C. **Blast radius:** the hypothesis **as tested by that chain**. The array remains a disciplined SDR network.
2. **Chromaticity (classification product only).** GPS L1 and L5 are separated by f₁/f₂≈1.339. Let φ be the candidate residual **in radians or cycles**, not metres. Three classes:
   - **Delay class:** φ₁/φ₂=f₁/f₂≈1.339 — equal in seconds (clock, time-transfer) or metres (path). Signature of a genuine common temporal or path modulation.
   - **Ionospheric class:** φ₁/φ₂=f₂/f₁≈0.747 — carrier-phase ionospheric residual in radians/cycles scales as 1/f. (Ionospheric *range* in metres scales as 1/f², same as group delay with opposite sign.) Routes to the null as ionosphere.
   - **Phase-offset class:** φ₁/φ₂=1 — equal in radians. Digital/processing artifact. Routes to instrumental investigation.

   Any candidate surviving Switch 1 must land in the delay class at the pre-registered tolerance on the **uncombined** L1/L5 pair. The iono-free bound product is not used here. **Blast radius:** the candidate, not the array. This switch cannot fire on a null.
3. **Pipeline non-recovery.** Open or blind injection of known correlated phase at known lag and known chain-class is not recovered within the pre-registered window (including the distinctive S-vs-C pattern), or the off-injection state does not return to the null floor, or the time-slide background disagrees with the bootstrap null at the pre-registered level, or the common-clock calibration pair does not sit on its predicted null (non-clock floor uncharacterized). **Blast radius:** the campaign, until the pipeline is repaired. No science claim is permitted.
4. **Möbius holonomy as physics.** Closed RF or fiber loop of controlled area and reversed chirality yields only standard Berry / Faraday / Sagnac phases; no extra discrete π. **Blast radius:** Appendix A as physics. Keep as bookkeeping if useful.
5. **Gravitating plenum.** Already thrown by cosmology: ρ_Λ∼6×10⁻¹⁰ J m⁻³ versus a Planck-cutoff zero-point estimate larger by tens to ~120 orders of magnitude depending on regularization **[E]**. **Blast radius:** literal Dirac-sea ontology. The phase program never needed it.
6. **Simultaneity convention.** If an Analysis-B |τ|≪τ_c excess is unstable under substitution of an independent time transfer (two-way optical, common-view vs all-in-view, or a second GNSS constellation), the excess is a clock-ensemble artifact. **Blast radius:** any non-local reading of that dataset. Load-bearing on Chain C (H_C).

Landauer / collapse identification is not testable with node chassis heat. It remains Appendix A. Aqueous QED, somatic 6.8–7.5 Hz, and Schumann coupling remain Appendix B.

---

## 8. Closing

Delayed light is still light. A correlation is a subtraction artifact until the null model — including every *known* correlated term and the measured correlation time — fails to contain it. GPS alignment is a convention. A 1 s average is not a spacelike sample on Earth. Below the steering bandwidth of a disciplined oscillator, two GPSDOs are one clock. A between-satellite single difference is blind to isotropic site phase. A dump-rate lag axis that is coarser than d_g/c cannot test |τ|≪τ_c. An isotropic common phase is indistinguishable from relative clock wander until a common clock says otherwise.

This program tests no predicted amplitude. It sets two upper bounds on anomalous distributed RF phase coherence — Chain S on the sky gradient (H_S), Chain C on isotropic common phase (H_C) — at a measured L_eff and measured systematic floors. A null is the expected result. "Systematics-limited" describes the bound, not a failure.

Build clocks good enough that phase is a spatial field. Name the chain and the hypothesis it tests. Cancel the clock that chain is allowed to cancel. Subtract Helmholtz, multipath, the troposphere, IGS, and the ionosphere. Define the data path from tracked carrier to estimator before the first science run. Measure τ_corr with an estimator that respects 1/f noise. State σ_sync and δτ per baseline. Split one clock across two front ends and measure Chain C's non-clock floor before quoting a Chain-C bound. Slide the residuals against themselves until the background is measured. Inject known lags on both chain-classes — some of them blind — and prove the pipeline finds them and puts them on the correct chain. Publish residuals, r̂ₖₗ^(res), and r̂ₖₗ(τ). If they sit on the null, the vacuum is not speaking in that channel, and the bound is the result. If they do not, the candidate still has to survive chromaticity on the uncombined pair, an independent clock, and a hold-out window — and only then is the next paper a data paper, not another ontology.

---

## Appendix A. Interpretive ontology **[I/H]** — firewalled

*Nothing in §§1–7 depends on this appendix.*

**A.1.** QED vacuum as a Lorentz-covariant fluctuation background whose local coherence is empirical **[H]**. Matter as a region of reduced phase coherence, not a Dirac hole (1930 hole theory is not the modern vacuum **[E]**). No operator is specified. Until one is, this is a story about the data.

**A.2.** Toroidal–Möbius identification on S¹×S¹ with π holonomy per toroidal circuit; 4-cube recursion

$$\mathcal{C}_n=\bigl(S^1\times S^1\bigr)^{\times n}\big/\sim_g$$

as multi-scale phase-lock bookkeeping. No metric, no stress-energy. Switch 4 is the reading. Not LQG. Not AdS/CFT.

**A.3.** Zeno as "locking," Darwinism as redundancy, Landauer as rendering cost: glosses **[I]** on established physics **[E]**. None load-bearing for the array.

**A.4.** ℓ_P≈1.616255×10⁻³⁵ m. Bekenstein bound S≤2πk_BRE/ħc **[E]**. Cells below ℓ_P are not extra degrees of freedom.

---

## Appendix B. Companion studies — gated separately

**B.1 Somatic oscillator.** BCG micromotion is real **[E]**; heart rate ∼1 Hz. Hypothesis **[H]**: aortic–iliac mechanical peak at 6.8–7.5 Hz predicts cranial accelerometer and EEG alpha–theta coherence after heart-rate harmonics are partialled out. Control: abdominal counter-phase actuator.

**B.2 Schumann coupling.** Ideal f₁≈10.6 Hz; measured f₁≈7.8 Hz, f₂≈14.1 Hz, f₃≈20.3 Hz, ambient B∼0.1–few pT **[E]**. Hypothesis **[H]**: energetic biological entrainment. Kill: ≥40 dB Faraday versus Helmholtz reconstruction at ambient and 10×.

**B.3 Aqueous coherence.** Del Giudice–Preparata–Vitiello domains (*Phys. Rev. Lett.* **61**, 1085 (1988)) are the hypothesis source **[H]**, not established fact. Kill: no collective electronic mode at ∼10² nm, ∼0.1 eV-class gap, 310.0±0.5 K, independent labs.

---

## Data availability

All raw IQ or residual streams, pipeline code, injection logs (open and blind, the latter after unblinding), time-slide backgrounds, and the frozen pre-registration will be published regardless of outcome, per §6. No part of the analysis of record may be tuned on the science data after the registry timestamp.

## Competing interests

The author declares no competing financial interests. Resonant Genesis LLC funds the instrument program.

---

## References

**Vacuum and fields.**
Dirac, P. A. M., "A Theory of Electrons and Protons," *Proc. R. Soc. Lond. A* **126**, 360–365 (1930).
Weinberg, S., *The Quantum Theory of Fields, Vol. I: Foundations* (Cambridge University Press, 1995).
Rugh, S. E. & Zinkernagel, H., "The Quantum Vacuum and the Cosmological Constant Problem," *Stud. Hist. Philos. Mod. Phys.* **33**, 663–705 (2002).

**Interferometric null prior art.**
Chou, A. S. *et al.* (Holometer Collaboration), "First Measurements of High Frequency Cross-Spectra from a Pair of Large Michelson Interferometers," *Phys. Rev. Lett.* **117**, 111102 (2016).
Chou, A. S. *et al.*, "The Holometer: An Instrument to Probe Planckian Quantum Geometry," *Class. Quantum Grav.* **34**, 065005 (2017), arXiv:1611.08265.

**GNSS and clock networks as exotic-physics sensors.**
Derevianko, A. & Pospelov, M., "Hunting for Topological Dark Matter with Atomic Clocks," *Nat. Phys.* **10**, 933–936 (2014).
Roberts, B. M. *et al.*, "Search for Domain Wall Dark Matter with Atomic Clocks on Board Global Positioning System Satellites," *Nat. Commun.* **8**, 1195 (2017).

**Morphology-agnostic detection methodology.**
Anderson, W. G., Brady, P. R., Creighton, J. D. E. & Flanagan, É. É., "An Excess Power Statistic for Detection of Burst Sources of Gravitational Radiation," *Phys. Rev. D* **63**, 042003 (2001).
Abadie, J. *et al.* (LIGO Scientific Collaboration & Virgo Collaboration), "All-Sky Search for Gravitational-Wave Bursts in the Second Joint LIGO–Virgo Run," *Phys. Rev. D* **85**, 122007 (2012).

**Carrier-phase metrology and GNSS systems.**
Teunissen, P. J. G. & Montenbruck, O., eds., *Springer Handbook of Global Navigation Satellite Systems* (Springer, 2017).
Kaplan, E. D. & Hegarty, C. J., eds., *Understanding GPS/GNSS: Principles and Applications* (Artech House, 3rd ed., 2017).
Dow, J. M., Neilan, R. E. & Rizos, C., "The International GNSS Service in a Changing Landscape of Global Navigation Satellite Systems," *J. Geod.* **83**(3–4), 191–198 (2009).
Saastamoinen, J., "Atmospheric Correction for the Troposphere and Stratosphere in Radio Ranging of Satellites," in *The Use of Artificial Satellites for Geodesy*, Geophys. Monogr. 15, AGU, 247–251 (1972).
Lombardi, M. A., NIST GPSDO evaluations, NCSLI (2013).
Lipiński, M., Włostowski, T., Serrano, J. & Alvarez, P., "White Rabbit: A PTP Application for Robust Sub-Nanosecond Synchronization," *Proc. IEEE Int. Symp. on Precision Clock Synchronization (ISPCS)*, 25–30 (2011).

**Coherence statistics and estimation.**
Goodman, N. R., "Statistical Analysis Based on a Certain Multivariate Complex Gaussian Distribution (an Introduction)," *Ann. Math. Statist.* **34**(1), 152–177 (1963).
Carter, G. C., Knapp, C. H. & Nuttall, A. H., "Estimation of the Magnitude-Squared Coherence Function via Overlapped Fast Fourier Transform Processing," *IEEE Trans. Audio Electroacoust.* **21**(4), 337–344 (1973).
Gish, H. & Cochran, D., "Invariance of the Magnitude-Squared Coherence Estimate with Respect to Second-Channel Statistics," *IEEE Trans. Acoust. Speech Signal Process.* **35**(12), 1777–1779 (1987).
Kay, S. M., *Fundamentals of Statistical Signal Processing: Estimation Theory* (Prentice Hall, 1993).
Benjamini, Y. & Yekutieli, D., "The Control of the False Discovery Rate in Multiple Testing under Dependency," *Ann. Statist.* **29**(4), 1165–1188 (2001).
Politis, D. N. & White, H., "Automatic Block-Length Selection for the Dependent Bootstrap," *Econometric Reviews* **23**(1), 53–70 (2004); corrigendum: Patton, A., Politis, D. N. & White, H., *Econometric Reviews* **28**(4), 372–375 (2009).
Allan, D. W., "Statistics of Atomic Frequency Standards," *Proc. IEEE* **54**(2), 221–230 (1966).

**Zeno and measurement.**
Misra, B. & Sudarshan, E. C. G., "The Zeno's Paradox in Quantum Theory," *J. Math. Phys.* **18**, 756–763 (1977).
Itano, W. M., Heinzen, D. J., Bollinger, J. J. & Wineland, D. J., "Quantum Zeno Effect," *Phys. Rev. A* **41**, 2295–2300 (1990).
Zurek, W. H., "Decoherence, Einselection, and the Quantum Origins of the Classical," *Rev. Mod. Phys.* **75**, 715–775 (2003).

**Information thermodynamics.**
Landauer, R., "Irreversibility and Heat Generation in the Computing Process," *IBM J. Res. Dev.* **5**, 183–191 (1961).
Bérut, A. *et al.*, "Experimental Verification of Landauer's Principle Linking Information and Thermodynamics," *Nature* **483**, 187–189 (2012).

**Bounds.**
Bekenstein, J. D., "Black Holes and Entropy," *Phys. Rev. D* **7**, 2333–2346 (1973); "Universal Upper Bound on the Entropy-to-Energy Ratio for Bounded Systems," *Phys. Rev. D* **23**, 287–298 (1981).
Hawking, S. W., "Particle Creation by Black Holes," *Commun. Math. Phys.* **43**, 199–220 (1975).
Maldacena, J. & Susskind, L., "Cool Horizons for Entangled Black Holes," *Fortschr. Phys.* **61**, 781–811 (2013), arXiv:1306.0533.

**Synchronization (statistic only).**
Kuramoto, Y., *Chemical Oscillations, Waves, and Turbulence* (Springer, 1984).
Strogatz, S. H., "From Kuramoto to Crawford: Exploring the Onset of Synchronization in Populations of Coupled Oscillators," *Physica D* **143**, 1–20 (2000).

**Water QED (App. B.3 source).**
Del Giudice, E., Preparata, G. & Vitiello, G., "Water as a Free Electric Dipole Laser," *Phys. Rev. Lett.* **61**, 1085–1088 (1988).
Preparata, G., *QED Coherence in Matter* (World Scientific, 1995).

**ELF background.**
Schumann, W. O., "Über die strahlungslosen Eigenschwingungen einer leitenden Kugel, die von einer Lufthülle und einer Ionosphärenhülle umgeben ist," *Z. Naturforsch. A* **7**, 149–154 (1952).
Nickolaenko, A. & Hayakawa, M., *Schumann Resonance for Tyros* (Springer, 2014).
