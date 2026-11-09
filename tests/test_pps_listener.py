"""
SPEC-005A.TIMING-PPS — PpsListener unit tests.

The listener runs on a background thread, so these tests wait for observable
state against a bounded deadline instead of sleeping for a fixed interval.
A fixed sleep is racy on loaded CI runners where the thread may not have been
scheduled yet when the assertion runs.
"""

import os
import time
from unittest.mock import patch

from dslv_zpdi.layer1_ingestion.timing.pps_listener import PpsListener

_EDGE_DEADLINE_S = 2.0
_POLL_INTERVAL_S = 0.01


def _wait_for_first_edge(listener: PpsListener, deadline_s: float = _EDGE_DEADLINE_S) -> dict:
    """SPEC-005A.TIMING-PPS — Poll the listener snapshot until an edge is recorded or timeout."""
    deadline = time.monotonic() + deadline_s
    snap = listener.snapshot()
    while snap["last_edge_mono_ns"] == 0 and time.monotonic() < deadline:
        time.sleep(_POLL_INTERVAL_S)
        snap = listener.snapshot()
    return snap


def test_pps_listener():
    """SPEC-005A.TIMING-PPS — A new sysfs assert sequence is captured as an edge."""
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
        try:
            snap = _wait_for_first_edge(listener)
        finally:
            listener.stop()

        assert snap["device"] == "/dev/pps0"
        assert snap["last_edge_mono_ns"] > 0
        assert snap["history_len"] >= 1


def test_pps_listener_no_device():
    """SPEC-005A.TIMING-PPS — A missing sysfs node exits the thread without recording edges."""
    with patch("dslv_zpdi.layer1_ingestion.timing.pps_listener.os") as mock_os:
        mock_os.path.basename.side_effect = os.path.basename
        mock_os.path.exists.return_value = False

        listener = PpsListener(device="/dev/does_not_exist_123")
        listener.start()
        # stop() joins the thread, so the existence check has completed
        # (inside the patch) before the snapshot is taken.
        listener.stop()
        snap = listener.snapshot()

        assert listener._thread is not None
        assert not listener._thread.is_alive()
        assert snap["last_edge_mono_ns"] == 0
        mock_os.open.assert_not_called()
