"""
SPEC-004A.3 | GPSDOLockMonitor (Rev 4.6.0-LBE1421)
Robust timing verification for production SIGINT.
"""

import logging
import time
import subprocess
from typing import Dict, Any
from .hal_hardware import HardwareHAL

logger = logging.getLogger("dslv-zpdi.layer1.lock")

class GPSDOLockMonitor:
    """
    SPEC-004A.3 | Monitors LBE-1421 lock status using triple-validation:
    1. NMEA telemetry via virtual serial (Fix quality, Sats, HDOP)
    2. chronyc RMS offset (Kernel PPS discipline health)
    3. hackrf_info (Silent Traitor check)
    """

    def __init__(
        self,
        jitter_threshold_ns: float = 10000.0,  # 10 µs limit
        unlock_threshold_s: float = 30.0,      # 30s unlock limit
        jitter_grace_period_s: float = 60.0    # 60s jitter grace
    ):
        """SPEC-004A.3.INIT | Initialize lock monitor."""
        self.jitter_threshold = jitter_threshold_ns
        self.unlock_threshold = unlock_threshold_s
        self.jitter_grace_period = jitter_grace_period_s
        
        self.last_lock_time = time.time()
        self.jitter_violation_start = None
        self.is_quarantined = False

    def check_lock_state(self, hardware_hal: HardwareHAL) -> Dict[str, Any]:
        """
        SPEC-004A.3.CHECK | Performs triple-validation and returns stability metrics.
        Returns: Dict containing 'healthy', 'quarantine', and metrics.
        """
        metrics = {
            "nmea": hardware_hal.verify_nmea_telemetry(),
            "pps_jitter_ns": 0.0,
            "hackrf_lock": False,
            "timestamp": time.time()
        }

        # 1. NMEA Validation
        gps_fix = metrics["nmea"].get("gps_fix", False)
        
        # 2. chronyc RMS offset (Kernel PPS jitter)
        metrics["pps_jitter_ns"] = self._get_chronyc_jitter()
        
        # 3. HackRF Silent Traitor check
        metrics["hackrf_lock"] = self._verify_hackrf_clock()

        now = time.time()
        
        # Stability Logic
        healthy_jitter = metrics["pps_jitter_ns"] < self.jitter_threshold
        
        if gps_fix and metrics["hackrf_lock"] and healthy_jitter:
            self.last_lock_time = now
            self.jitter_violation_start = None
            self.is_quarantined = False
        else:
            # Handle Jitter violations with grace period
            if not healthy_jitter:
                if self.jitter_violation_start is None:
                    self.jitter_violation_start = now
                elif now - self.jitter_violation_start > self.jitter_grace_period:
                    self.is_quarantined = True
            
            # Handle total unlock with short threshold
            if now - self.last_lock_time > self.unlock_threshold:
                self.is_quarantined = True

        return {
            "healthy": not self.is_quarantined and gps_fix,
            "quarantine": self.is_quarantined,
            "metrics": metrics
        }

    def _get_chronyc_jitter(self) -> float:
        """SPEC-004A.3.CHRONY | Read RMS offset from chrony."""
        try:
            result = subprocess.run(
                ["chronyc", "tracking"],
                capture_output=True, text=True, timeout=1
            )
            for line in result.stdout.splitlines():
                if "RMS offset" in line:
                    return float(line.split(":")[1].strip().split()[0]) * 1e9
        except:
            pass
        return float('inf')

    def _verify_hackrf_clock(self) -> bool:
        """SPEC-004A.3.HACKRF | Verify external clock source."""
        try:
            result = subprocess.run(
                ["hackrf_debug", "--clock_source"],
                capture_output=True, text=True, timeout=1
            )
            return "external" in result.stdout.lower()
        except:
            pass
        return False
