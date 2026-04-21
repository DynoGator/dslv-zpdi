"""Test-suite isolation.

Forces the module-level ``coherence_engine`` in ``wiring.py`` to start in
NOT_STARTED state regardless of any persisted baseline on the host. Without
this, tests that call ``coherence_engine.start_baseline()`` fail on hosts
where ``/var/lib/dslv_zpdi/baseline.json`` is LOCKED (FSM is one-way).
"""

import os

os.environ["DSLV_BASELINE_STATE_PATH"] = "/nonexistent/dslv-zpdi-tests/baseline.json"
