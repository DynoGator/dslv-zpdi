# DSLV-ZPDI v5.3.0

## Zero-Copy Binary Ingestion & Hardware-Anchored Chain of Custody Refactor

This major release implements a complete end-to-end binary payload ingestion pipeline, removing all intermediate text/JSON serialization from SDR capture to HDF5 storage.

### Key Changes
*   **Zero-Copy Binary Pipeline:** Raw SDR data is now directly packed into structured binary structs without intermediate JSON processing, significantly reducing CPU overhead.
*   **Hardware-Anchored Cryptographic Hashing:** BLAKE2b hashing is now performed immediately upon payload generation directly on the binary buffer, enforcing a zero-trust hardware-anchored chain of custody.
*   **Strict Binary Coherence Engine:** The layer-2 Coherence Engine and DualStreamRouter were refactored to work seamlessly with binary configurations, accepting pre-extracted metrics and routing efficiently without un-packaging the primary streams.
*   **100% Test Suite Stability:** Resolved all legacy `test_payload.py` and `test_pipeline.py` assumptions. All 230 system and integration tests are verified passing for the new binary structure.
*   **Dashboard Preservation:** The peripheral Layer-3 dashboards remain fully operational. `quarantine.jsonl` and `health.json` outputs remain decoupled from the primary `HDF5Writer`, ensuring dashboards continue parsing without conflict.
*   **Dependency Update:** Rebuilt and upgraded the local `.venv` dependencies, including `h5py`, `numpy`, `msgpack`, and `cryptography` to support native binary interactions.
