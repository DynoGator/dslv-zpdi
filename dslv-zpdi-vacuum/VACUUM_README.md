# DSLV-ZPDI-Probing-The-Vacuum-Structure

Field book for the Rev 3.4 carrier-phase program (28 Sep 2026). Sibling of `dslv-zpdi-mobile` (`labs.dynogator.dslvzpdi`). The handset is the campaign record. The Pi 5 / GPSDO / SDR nodes remain the array.

This book does not synthesize residuals, IQ, or a detection. Chain C stays unbounded until a measured common-clock floor is entered. Closed forms are checked against the numbers quoted in the white paper (`attachments/1A_CARRIER_PHASE_COHEARENCE.md`).

GrapheneOS / Pixel 9 Pro XL: install from Vanadium as a standalone window. No Play Services. The campaign book stays on the device. A device GNSS fix, if granted, is a coordinate, not carrier phase.

Intended native applicationId, when wrapped the same way as the existing shell: `labs.dynogator.dslvzpdi.vacuum`.
