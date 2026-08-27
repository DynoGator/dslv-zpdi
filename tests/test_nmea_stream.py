import pytest
import time
import sys
from unittest.mock import MagicMock
from dslv_zpdi.layer1_ingestion.timing.nmea_stream import NmeaStream

def test_nmea_stream_init():
    stream = NmeaStream(port="/dev/ttyAMA0", baud=9600)
    assert stream._port == "/dev/ttyAMA0"
    assert stream._baud == 9600

def test_nmea_stream_parse_gga():
    mock_serial = MagicMock()
    mock_serial_obj = MagicMock()
    mock_serial_obj.__enter__.return_value = mock_serial_obj
    mock_serial.Serial.return_value = mock_serial_obj
    mock_serial.serialutil.SerialException = Exception
    mock_serial_obj.readline.return_value = b"$GPGGA,123519,4807.038,N,01131.000,E,1,08,0.9,545.4,M,46.9,M,,*47\r\n"
    
    sys.modules['serial'] = mock_serial

    stream = NmeaStream(port="/dev/ttyAMA0")
    stream.start()
    time.sleep(0.15)
    stream.stop()
    
    assert mock_serial_obj.readline.called
    
    fix = stream.latest()
    assert fix.get("satellites_used") == 8
