# DSLV-ZPDI Cyberdeck Chassis: RF & Magnetic Shielding Design

**Document ID:** `SHIELD-DESIGN-001`
**Status:** IN DEVELOPMENT — Expanding as build progresses
**Target Baseline:** Rev 4.2-LBE-1421
**Author:** J.R. Fross (@DynoGator) / Resonant Genesis LLC

---

## 1. Design Philosophy

We don't need a complicated Rube Goldberg machine; we need a submarine. Build a rigid, multi-chambered hull, seal the bulkheads, and rigorously control every single penetration point. Given the operator's background in heavy fabrication and metalwork, the chassis will be built from raw materials — bypassing flimsy plastics for a true isolation deck.

---

## 2. Hull & Thermal Strategy: Conduction Cooling

Standard fan ventilation is not an option. A hole that lets air in also lets high-frequency RF and plasma transients in. The deck must be **airtight**.

### The Fix: The Exoskeleton Heat Sink

Instead of circulating air, we use **conduction cooling**:

- Build the core chassis out of **thick aluminum plate** (at least 1/8" to 1/4" thick). Aluminum is an excellent thermal conductor and serves as the primary Faraday cage.
- Inside the Pi 5 compartment, mount the Pi so that the CPU (RP1 and Broadcom chips) presses directly against the *inside* of the outer aluminum hull using **thick, high-performance thermal silicone pads**.
- Do the same for the HackRF's main processors.
- The entire external casing of the cyberdeck becomes the heat sink. Heat transfers directly from the chips into the hull and dissipates externally.

**Result:** Zero signal drift from heat, and zero holes in the armor.

---

## 3. Compartmentalization: The Bulkheads

The noisy digital brain (Pi 5) must be separated from the sensitive metrology gear (HackRF + LBE-1421 GPSDO), and all of it shielded from the outside.

### Chamber Layout

| Chamber | Contents | Purpose |
|---------|----------|---------|
| **Chamber A** | Raspberry Pi 5 | Digital compute — noisy |
| **Chamber B** | HackRF One + LBE-1421 GPSDO | RF metrology — sensitive |

### Construction

- Fabricate the interior with **solid aluminum divider walls (bulkheads)** welded or bolted tight.
- Line the *inside* of both chambers completely with **Mu-Metal foil tape**.
  - The aluminum stops RF/electrical fields.
  - The Mu-Metal absorbs low-frequency magnetic pulses that accompany high-energy events.

---

## 4. The USB "Breaker": Galvanic Isolation

An **Industrial USB Optoisolator (Galvanic Isolator)** provides breaker-equivalent protection for the external USB hub.

### How It Works

- The optoisolator literally cuts the copper wire inside the USB connection.
- It takes USB data, turns it into a **pulse of light**, shoots it across a physical microscopic air gap to a light receiver, and turns it back into data.
- Because there is no physical electrical connection bridging the gap, a massive voltage spike hitting the external USB hub **physically cannot travel** into the Pi 5.

### Implementation

- Mount a high-speed **USB 3.0 Optoisolator** inside the Pi 5 chamber (Chamber A), right at the bulkhead wall.
- External USB hub plugs into the outside of the deck, hits the isolator, and cleanly passes data to the Pi.

---

## 5. Securing the Pass-Throughs (The Leaks)

The only things crossing bulkheads are the DSI ribbon, RF cables, and power.

### 5.1 DSI Ribbon Cable

Ribbon cables are notorious antennas.

- Wrap the **entire length** of the exposed ribbon in **conductive copper foil tape**.
- When passing through the slit in the hull, ensure the copper tape makes **physical contact with the bare aluminum chassis**.
- This grounds the shield directly to the hull, preventing the slit from acting as a waveguide.

### 5.2 SMA Bulkheads

- RF limiters mount on the outside of the chassis.
- Clean, safe signal passes through **standard SMA bulkhead connectors** drilled directly into the metal hull.

### 5.3 Power Entry

If running an external battery:

- **Ferrite chokes** clamped onto DC power lines right where they enter the deck.
- Inline **transient voltage suppression (TVS) diode** to clamp power surges.

---

## 6. Signal Flow Summary: "The Vault"

```
1. ANOMALY HITS
   └─→ Bounces off solid aluminum hull (RF)
   └─→ Absorbed by Mu-Metal lining (Magnetic)

2. SURGE HITS ANTENNA
   └─→ Inline RF Limiter clamps it (energy → heat)
   └─→ Clean 10MHz/RF passes through SMA bulkhead → Chamber B

3. SURGE HITS EXTERNAL USB HUB
   └─→ Hits USB Optoisolator in bulkhead
   └─→ Data passes as light, voltage spike dies at air gap

4. INTERNAL HEAT BUILDS UP
   └─→ Conducts through thermal pads → aluminum hull
   └─→ Dissipates harmlessly into ambient air
```

---

## 7. Materials Reference (Preliminary)

| Material | Purpose | Specification |
|----------|---------|---------------|
| Aluminum plate | Hull + bulkheads | 6061-T6, 1/8" to 1/4" thick |
| Mu-Metal foil tape | Magnetic shielding liner | High-permeability nickel-iron alloy |
| Thermal silicone pads | CPU-to-hull heat transfer | High thermal conductivity, 1-3mm thick |
| Conductive copper foil tape | Ribbon cable shielding | Adhesive-backed, conductive adhesive |
| SMA bulkhead connectors | RF pass-through | 50 Ohm, panel-mount |
| USB 3.0 Optoisolator | Galvanic USB isolation | Industrial grade, high-speed |
| Ferrite chokes | Power line filtering | Snap-on, appropriate for DC gauge |
| TVS diode | Power surge clamping | Rated for system voltage |

---

## 8. Development Notes

- [ ] Finalize internal chamber dimensions based on Pi 5 + HackRF + LBE-1421 footprints
- [ ] Source and test specific Mu-Metal tape products
- [ ] Validate thermal pad compression for optimal CPU-to-hull contact
- [ ] Design SMA bulkhead layout for antenna and GPSDO connections
- [ ] Prototype USB optoisolator integration
- [ ] Measure thermal performance under sustained 20MHz IQ ingestion load
- [ ] Test shielding effectiveness with spectrum analyzer

---

*This is a brute-force, mathematically sound approach. It requires precise metal cuts and absolute dedication to sealing the gaps, but it will survive exactly the kind of chaotic environments we are hunting.*

**Technical integrity is our only metric of success.**
