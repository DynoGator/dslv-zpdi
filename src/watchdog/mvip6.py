"""
DSLV-ZPDI Watchdog — MVIP-6 Gatekeeper
SPEC-007 | Trust Tier: Governance
"""
import time
import logging
from enum import Enum
from dataclasses import dataclass

class NodeHealthStatus(Enum):
    """SPEC-007.1 — Node Health States"""
    TRUSTED = "TRUSTED"
    DEGRADED = "DEGRADED"
    UNTRUSTED = "UNTRUSTED"

@dataclass
class HealthThresholds:
    """SPEC-007.2 — Watchdog Trigger Thresholds"""
    gps_lock_required: bool = True
    pps_jitter_degraded_ns: float = 500.0
    pps_jitter_untrusted_ns: float = 10000.0
    calibration_drift_limit: float = 0.20
    watchdog_heartbeat_interval: float = 5.0

class MVIP6Watchdog:
    """SPEC-007.3 — Watchdog Runtime"""
    
    def __init__(self, node_id: str, thresholds: HealthThresholds = None):
        self.node_id = node_id
        self.thresholds = thresholds or HealthThresholds()
        self.status = NodeHealthStatus.UNTRUSTED
        self.degraded_since: float = 0.0
        self.last_heartbeat: float = time.time()

    def evaluate(self, health_metrics: dict) -> NodeHealthStatus:
        """SPEC-007.3a — Health Evaluation Cycle"""
        try:
            self.last_heartbeat = time.time()
            
            if not health_metrics.get('gps_locked', False):
                self._transition(NodeHealthStatus.UNTRUSTED, "GPS lock lost")
                return self.status
                
            pps_jitter = health_metrics.get('pps_jitter_ns', float('inf'))
            if pps_jitter > self.thresholds.pps_jitter_untrusted_ns:
                self._transition(NodeHealthStatus.UNTRUSTED, "PPS jitter > untrusted threshold")
                return self.status
            elif pps_jitter > self.thresholds.pps_jitter_degraded_ns:
                self._transition(NodeHealthStatus.DEGRADED, "PPS jitter > degraded threshold")
                if self.degraded_since > 0 and (time.time() - self.degraded_since) > 60.0:
                    self._transition(NodeHealthStatus.UNTRUSTED, "Degraded state persisted > 60s")
                return self.status
                
            cal_drift = health_metrics.get('calibration_drift', 0.0)
            if cal_drift > self.thresholds.calibration_drift_limit:
                self._transition(NodeHealthStatus.UNTRUSTED, "Calibration drift > limit")
                return self.status

            if self.status == NodeHealthStatus.DEGRADED:
                self._transition(NodeHealthStatus.TRUSTED, "All metrics nominal — recovered")
                
            return self.status
            
        except Exception as e:
            self._transition(NodeHealthStatus.UNTRUSTED, f"Watchdog exception: {e}")
            return self.status

    def recalibrate(self, cal_result: dict) -> NodeHealthStatus:
        """SPEC-007.3b — Recalibration Gate"""
        if cal_result.get('passed', False):
            self._transition(NodeHealthStatus.TRUSTED, "Recalibration passed")
        return self.status

    def _transition(self, new_status: NodeHealthStatus, reason: str):
        """SPEC-007.3 — Watchdog Internal State Transition logic"""
        if new_status != self.status:
            logging.info(f"[SPEC-007] {self.node_id}: {self.status.value} -> {new_status.value} | {reason}")
            if new_status == NodeHealthStatus.DEGRADED and self.status == NodeHealthStatus.TRUSTED:
                self.degraded_since = time.time()
            elif new_status != NodeHealthStatus.DEGRADED:
                self.degraded_since = 0.0
            self.status = new_status
