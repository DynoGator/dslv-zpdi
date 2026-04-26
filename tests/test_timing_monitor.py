import pytest
import time
from dslv_zpdi.layer1_ingestion.lock_monitor import GPSDOLockMonitor
from dslv_zpdi.layer1_ingestion.hal_simulated import SimulatedHAL

def test_lbe1421_stability_mock():
    """Verify monitor accepts 1e-12 stability (~1ns jitter)."""
    monitor = GPSDOLockMonitor(jitter_threshold_ns=10.0)
    hal = SimulatedHAL()
    
    # Simulate 1ns jitter (perfect LBE-1421)
    monitor._get_chronyc_jitter = lambda: 1.0
    monitor._verify_hackrf_clock = lambda: True
    status = monitor.check_lock_state(hal)
    assert status["healthy"] == True
    assert status["metrics"]["pps_jitter_ns"] < 10.0

def test_lbe1421_jitter_quarantine():
    """Verify quarantine after jitter grace period (60s)."""
    monitor = GPSDOLockMonitor(jitter_threshold_ns=10.0, jitter_grace_period_s=0.1)
    hal = SimulatedHAL()
    
    # 1. Healthy start
    status = monitor.check_lock_state(hal)
    assert status["quarantine"] == False
    
    # 2. Inject jitter
    def mock_jitter(): return 50000.0
    monitor._get_chronyc_jitter = mock_jitter
    
    # First violation (should be in grace period)
    status = monitor.check_lock_state(hal)
    assert status["quarantine"] == False
    
    # Wait for grace period to expire
    time.sleep(0.2)
    
    status = monitor.check_lock_state(hal)
    assert status["quarantine"] == True

def test_lbe1421_holdover_seamless():
    """Verify holdover within 2s threshold."""
    monitor = GPSDOLockMonitor(unlock_threshold_s=0.5)
    hal = SimulatedHAL()
    
    # 1. Lock active
    monitor.check_lock_state(hal)
    
    # 2. GPS Loss (Mock NMEA to show no fix)
    class LostGPSHAL:
        def verify_nmea_telemetry(self): return {"gps_fix": False}
        def _get_chronyc_jitter(self): return 1.0 
        def _verify_hackrf_clock(self): return True
    
    lost_hal = LostGPSHAL()
    
    status = monitor.check_lock_state(lost_hal)
    assert status["healthy"] == False
    assert status["quarantine"] == False
    
    # Wait for holdover to expire
    time.sleep(0.6)
    status = monitor.check_lock_state(lost_hal)
    assert status["quarantine"] == True
