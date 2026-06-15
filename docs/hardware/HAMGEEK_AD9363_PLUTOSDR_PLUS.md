# HamGeek AD9363 PlutoSDR+ — Tier-1 Candidate Hardware Notes

**Status:** PROVISIONAL_TIER1_PENDING_HARDWARE_QUALIFICATION

## Observed Enclosure Characteristics

Based on owner-supplied photographs:

- Brand: HamGeek
- Marking: AD9363
- Interfaces: RJ45 Ethernet, USB-C OTG, USB-C DEBUG, microSD
- Timing ports: two micro-coaxial connectors engraved `10M/PPS`

## Unknown Properties

All of the following are UNVERIFIED_PHYSICAL_PROPERTY until proven:

- Exact Analog Devices or clone PCB revision
- Timing connector family and ordering
- Whether the transceiver is truly AD9363 or an unlocked/substituted component
- Ethernet speed (100 Mb/s or 1 Gb/s)
- Standard Pluto firmware or clone firmware
- TX channel availability
- Whether both RX channels are enabled

## Software Discovery

Use the probe utility to collect evidence without modifying firmware:

```bash
dslv-zpdi-probe --discover --json output/pluto_probe.json
dslv-zpdi-probe --uri ip:<address> --json output/pluto_probe.json
```

The backend reads the following IIO attributes when available:

- `hw_model`
- `fw_version`
- `fpga_version`
- `serial`
- `ad9361-phy,model`

## Transport Notes

- Preferred: Ethernet IIO (`ip:` URI)
- Fallback: USB IIO (`usb:` URI)
- Do not hardcode `192.168.2.1` unless the device responds there.

## Qualification Requirements

See `docs/qualification/PLUTO_ACCEPTANCE_MATRIX.md` and
`docs/qualification/TIER1_HARDWARE_QUALIFICATION_STANDARD.md`.

The device cannot be declared canonical Tier-1 until:

- Timing ports are physically verified
- External reference consumption is demonstrated
- No unaccounted sample loss occurs during sustained capture
- Integrity verification passes
- Performance equals or exceeds the HackRF baseline
