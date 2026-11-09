"""
SPEC-005A.TIMING-NMEA — NmeaStream unit tests.

The reader thread imports ``serial`` lazily, so the parse test injects a mock
module through ``monkeypatch.setitem(sys.modules, ...)``. That restores the
real module afterwards; a bare ``sys.modules`` assignment leaks the mock into
every later test, where NmeaStream threads started by other tests spin on the
mock's ``readline()`` forever, recording calls until the process exhausts CPU
and memory.
"""

import sys
import time
from unittest.mock import MagicMock

from dslv_zpdi.layer1_ingestion.timing.nmea_stream import NmeaStream

_GGA = b"$GPGGA,123519,4807.038,N,01131.000,E,1,08,0.9,545.4,M,46.9,M,,*47\r\n"
_FIX_DEADLINE_S = 2.0
_POLL_INTERVAL_S = 0.01


def test_nmea_stream_init():
    """SPEC-005A.TIMING-NMEA — Constructor stores port and baud."""
    stream = NmeaStream(port="/dev/ttyAMA0", baud=9600)
    assert stream._port == "/dev/ttyAMA0"
    assert stream._baud == 9600


def test_nmea_stream_parse_gga(monkeypatch):
    """SPEC-005A.TIMING-NMEA — A GGA sentence from the serial port becomes the latest fix."""
    mock_serial = MagicMock()
    mock_serial_obj = MagicMock()
    mock_serial_obj.__enter__.return_value = mock_serial_obj
    mock_serial.Serial.return_value = mock_serial_obj
    mock_serial.SerialException = OSError
    mock_serial.serialutil.SerialException = OSError
    mock_serial_obj.readline.return_value = _GGA

    monkeypatch.setitem(sys.modules, "serial", mock_serial)

    stream = NmeaStream(port="/dev/ttyAMA0")
    stream.start()
    try:
        deadline = time.monotonic() + _FIX_DEADLINE_S
        fix = stream.latest()
        while fix.get("satellites_used") != 8 and time.monotonic() < deadline:
            time.sleep(_POLL_INTERVAL_S)
            fix = stream.latest()
    finally:
        stream.stop()

    assert mock_serial_obj.readline.called
    assert fix.get("satellites_used") == 8
    assert stream._thread is not None
    assert not stream._thread.is_alive()
