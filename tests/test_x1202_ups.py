import pytest
from unittest.mock import MagicMock, patch
import time

smbus2 = pytest.importorskip("smbus2", reason="smbus2 not available (hardware-only dependency)")

from dslv_zpdi.layer1_ingestion.x1202_ups import X1202UpsMonitor, UpsSample


@patch("smbus2.SMBus")
def test_ups_initialization_absent(mock_smbus):
    mock_smbus.side_effect = Exception("No bus")
    ups = X1202UpsMonitor(i2c_bus=1, i2c_address=0x36)
    ups.open()
    
    sample = ups.sample()
    assert sample.health == "absent"
    assert "not available" in sample.error
    
    ups.close()

@patch("smbus2.SMBus")
@patch("dslv_zpdi.layer1_ingestion.x1202_ups.Path")
def test_ups_sample_happy_path(mock_path, mock_smbus_cls):
    mock_bus = MagicMock()
    mock_smbus_cls.return_value = mock_bus
    
    def mock_read_i2c_block_data(addr, reg, length):
        if reg == 0x02: return [0xC8, 0x00]
        if reg == 0x04: return [0x56, 0x78]
        if reg == 0x16: return [0x00, 0x00]
        if reg == 0x08: return [0x00, 0x02]
        return [0, 0]
        
    mock_bus.read_i2c_block_data.side_effect = mock_read_i2c_block_data
    
    ups = X1202UpsMonitor(i2c_bus=1, i2c_address=0x36)
    ups.open()
    
    ups.read_ac_present = MagicMock(return_value=True)
    ups.read_charging_enabled = MagicMock(return_value=True)
    
    sample = ups.sample()
    assert sample.health == "healthy"
    assert sample.ac_present is True
    
    ups.close()
