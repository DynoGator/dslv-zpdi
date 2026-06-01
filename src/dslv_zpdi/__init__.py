"""DSLV-ZPDI — Distributed Sensor Locational Vectoring · Zero-Point Data Integration.

Institutional-grade SIGINT / RF-metrology pipeline: hardware-anchored ingestion
(Layer 1) → Kuramoto coherence analysis (Layer 2) → attested HDF5 persistence and
swarm telemetry (Layer 3).

``__version__`` is the in-process source of truth and is kept in lock-step with
``pyproject.toml`` by ``tools/check_version_sync.py``.
"""

__version__ = "4.7.2"

__all__ = ["__version__"]
