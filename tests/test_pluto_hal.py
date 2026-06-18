"""Mock-based tests for PlutoSDR+ HAL integration (SPEC-004A.5)."""

from unittest import mock

import pytest

from dslv_zpdi.core.exceptions import (
    ClockVerificationError,
    DriverUnavailableError,
    HardwareInitializationError,
)
from dslv_zpdi.layer1_ingestion import hal_pluto as pluto_module
from dslv_zpdi.layer1_ingestion.hal_pluto import PlutoHAL


def _real_pluto_accessible() -> bool:
    """Probe whether a real Pluto is reachable at the default URI."""
    try:
        import iio  # pylint: disable=import-outside-toplevel

        ctx = iio.Context("ip:192.168.3.80")
        return ctx.find_device("ad9361-phy") is not None
    except Exception:
        return False


_REAL_PLUTO_ACCESSIBLE = _real_pluto_accessible()


class TestPlutoInitialization:
    def test_no_driver_available_raises_driver_unavailable(self):
        patches = {
            "IIO_AVAILABLE": False,
            "SOAPYSDR_AVAILABLE": False,
        }
        with mock.patch.dict(pluto_module.__dict__, patches):
            with pytest.raises(DriverUnavailableError):
                PlutoHAL()

    def test_context_missing_devices_raises_hardware_initialization(self):
        mock_ctx = mock.MagicMock()
        mock_ctx.find_device.return_value = None
        mock_iio = mock.MagicMock()
        mock_iio.Context.return_value = mock_ctx
        patches = {
            "iio": mock_iio,
            "IIO_AVAILABLE": True,
            "SOAPYSDR_AVAILABLE": False,
        }
        with mock.patch.dict(pluto_module.__dict__, patches):
            with pytest.raises(HardwareInitializationError):
                PlutoHAL()

    @pytest.mark.skipif(
        _REAL_PLUTO_ACCESSIBLE,
        reason="Real Pluto reachable; mocks would be bypassed",
    )
    def test_external_clock_without_pps_raises_clock_verification(self):
        mock_ctx = mock.MagicMock()
        mock_ctx.find_device.return_value = mock.MagicMock()
        mock_iio = mock.MagicMock()
        mock_iio.Context.return_value = mock_ctx
        patches = {
            "iio": mock_iio,
            "IIO_AVAILABLE": True,
            "SOAPYSDR_AVAILABLE": False,
        }
        with mock.patch.dict(pluto_module.__dict__, patches):
            with pytest.raises(ClockVerificationError):
                PlutoHAL(external_clock=True)


class TestPlutoIngestion:
    @pytest.mark.skipif(
        _REAL_PLUTO_ACCESSIBLE,
        reason="Real Pluto reachable; mocks would be bypassed",
    )
    def test_ingest_sdr_internal_clock_quarantined(self):
        mock_chan = mock.MagicMock()
        mock_rx = mock.MagicMock()
        mock_rx.find_channel.return_value = mock_chan
        mock_ad9361 = mock.MagicMock()
        mock_ad9361.find_channel.return_value = mock.MagicMock()
        mock_ctx = mock.MagicMock()
        mock_ctx.find_device.side_effect = [mock_ad9361, mock_rx]
        mock_ctx.attrs = {}

        mock_buf = mock.MagicMock()
        # 4096 complex samples = 8192 int16 values
        import numpy as np

        mock_buf.read.return_value = np.zeros(8192, dtype=np.int16).tobytes()
        mock_iio = mock.MagicMock()
        mock_iio.Context.return_value = mock_ctx
        mock_iio.Buffer.return_value = mock_buf

        patches = {
            "iio": mock_iio,
            "IIO_AVAILABLE": True,
            "SOAPYSDR_AVAILABLE": False,
        }
        with mock.patch.dict(pluto_module.__dict__, patches):
            hal = PlutoHAL(external_clock=False)
            payload = hal.ingest_sdr(center_freq=400e6, sample_rate=2e6, num_samples=4096)
            assert payload.modality == "rf_sdr"
            assert payload.raw_value["clock_source"] == "internal"
            assert "iq_samples" in payload.raw_value
            hal.shutdown()


class TestPlutoVerifyLock:
    def test_verify_gpsdo_lock_with_mock_context(self):
        mock_ctx = mock.MagicMock()
        mock_ctx.find_device.return_value = mock.MagicMock()
        mock_ctx.attrs = {
            "hw_model": "PlutoSDR Rev.C",
            "fw_version": "v0.37",
            "ad9361-phy,model": "ad9363a",
        }
        mock_iio = mock.MagicMock()
        mock_iio.Context.return_value = mock_ctx
        patches = {
            "iio": mock_iio,
            "IIO_AVAILABLE": True,
            "SOAPYSDR_AVAILABLE": False,
        }
        with mock.patch.dict(pluto_module.__dict__, patches):
            hal = PlutoHAL(external_clock=False)
            info = hal.verify_gpsdo_lock()
            assert info["pluto_detected"] is True
            assert info["hw_model"] == "PlutoSDR Rev.C"
            hal.shutdown()
