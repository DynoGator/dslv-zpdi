"""SPEC-006.6 — Orientation-Weighted Coherence Fusion Engine (Rev 1.0)

Fuses Hilbert-phase coherence scores from the motion-sensor suite with spatial
orientation provided by the Android Rotation Vector sensor.

Mathematical basis
------------------
The Kuramoto r_local score (from CoherenceScorer) measures instantaneous phase
synchronisation across a rolling window of a single sensor's magnitude samples.
That score is meaningful when the device is stationary: if the device is waving
around, any phase coherence is dominated by rigid-body kinematics rather than
the signal of interest.

This engine adds a quaternion-stability weight:

    r_local_fused = r_local * w_orient

where w_orient ∈ [0, 1] is derived from the dot-product between consecutive
rotation-vector quaternions:

    w_orient = |q_{t-1} · q_t|

|q · q'| = cos(Δθ/2), so w_orient ≈ 1 when the device is nearly stationary
between samples and decreases toward 0 as angular velocity increases.  A 90°
rotation between consecutive rotation-vector samples yields w_orient ≈ 0.707;
a 180° flip yields 0.

When fewer than two quaternion samples are buffered (startup), w_orient = 1.0
(no penalty applied — trust the raw phase coherence).
"""
from __future__ import annotations

import math
from collections import deque
from typing import Tuple


class OrientationTracker:
    """Maintains a rolling window of rotation-vector quaternions and computes
    an orientation-stability weight for coherence fusion.
    """

    def __init__(self, window: int = 8) -> None:
        self._buf: deque[Tuple[float, float, float, float]] = deque(maxlen=window)

    def push(self, reading: dict) -> None:
        """Ingest a single rotation-vector sensor reading.

        Termux rotation-vector keys:
          x, y, z  — axis * sin(θ/2)
          cos_value — cos(θ/2), i.e. the scalar (w) component
        """
        qx = float(reading.get("x", 0.0))
        qy = float(reading.get("y", 0.0))
        qz = float(reading.get("z", 0.0))
        qw = float(reading.get("cos_value", reading.get("w", 1.0)))
        # Normalise to avoid numerical drift
        mag = math.sqrt(qx * qx + qy * qy + qz * qz + qw * qw)
        if mag > 1e-9:
            qx, qy, qz, qw = qx / mag, qy / mag, qz / mag, qw / mag
        self._buf.append((qx, qy, qz, qw))

    def stability(self) -> float:
        """Return orientation-stability weight in [0, 1].

        Uses the absolute dot product between the two most recent quaternions.
        Returns 1.0 when fewer than two samples have been received.
        """
        if len(self._buf) < 2:
            return 1.0
        q1 = self._buf[-2]
        q2 = self._buf[-1]
        dot = q1[0] * q2[0] + q1[1] * q2[1] + q1[2] * q2[2] + q1[3] * q2[3]
        return min(1.0, abs(dot))

    def reset(self) -> None:
        self._buf.clear()


def apply_orientation_weight(
    r_local: float,
    r_smooth: float,
    tracker: OrientationTracker,
) -> Tuple[float, float, float]:
    """Return (r_local_fused, r_smooth_fused, w_orient).

    Scales both coherence scores by the current orientation-stability weight.
    r_global is left unmodified because it aggregates across the fleet and
    orientation weighting is already embedded in each node's r_smooth.
    """
    w = tracker.stability()
    return r_local * w, r_smooth * w, w
