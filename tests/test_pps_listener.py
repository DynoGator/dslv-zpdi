import pytest
import os
import threading
import time
from unittest.mock import MagicMock, patch
from dslv_zpdi.layer1_ingestion.timing.pps_listener import PpsListener

def test_pps_listener():
    with patch("dslv_zpdi.layer1_ingestion.timing.pps_listener.os") as mock_os:
        mock_os.path.basename.side_effect = os.path.basename
        mock_os.path.exists.return_value = True
        mock_os.O_RDONLY = os.O_RDONLY
        mock_os.SEEK_SET = os.SEEK_SET
        
        mock_os.open.return_value = 3
        
        seq = [1]
        def mock_read(fd, size):
            seq[0] += 1
            return f"1234567890.500000000#{seq[0]}\n".encode()
            
        mock_os.read.side_effect = mock_read
        
        listener = PpsListener(device="/dev/pps0")
        listener.start()
        time.sleep(0.15) # Wait for polling thread (10Hz)
        listener.stop()
        
        snap = listener.snapshot()
        assert snap["device"] == "/dev/pps0"
        assert snap["last_edge_mono_ns"] > 0

def test_pps_listener_no_device():
    with patch("dslv_zpdi.layer1_ingestion.timing.pps_listener.os") as mock_os:
        mock_os.path.basename.side_effect = os.path.basename
        mock_os.path.exists.return_value = False
        
        listener = PpsListener(device="/dev/does_not_exist_123")
        listener.start()
        time.sleep(0.15)
        listener.stop()
        snap = listener.snapshot()
        assert snap["last_edge_mono_ns"] == 0
