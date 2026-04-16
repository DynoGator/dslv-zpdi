"""Mock-based tests for hardware failure paths (Priority 1, Item 9)."""

from unittest import mock

import pytest

from dslv_zpdi.core.exceptions import (
    ClockVerificationError,
    DriverUnavailableError,
    HardwareInitializationError,
)
from dslv_zpdi.layer1_ingestion import hal_hardware as hal_hw_module
from dslv_zpdi.layer1_ingestion.hal_hardware import HardwareHAL


class TestSoapySDRFailurePaths:
    def test_no_devices_found_raises_driver_unavailable(self):
        mock_soapy = mock.MagicMock()
        mock_soapy.Device.enumerate.return_value = []
        patches = {
            "SoapySDR": mock_soapy,
            "SOAPYSDR_AVAILABLE": True,
            "PYHACKRF_AVAILABLE": False,
        }
        with mock.patch.dict(hal_hw_module.__dict__, patches):
            with pytest.raises(DriverUnavailableError):
                HardwareHAL()

    def test_hackrf_not_found_raises_hardware_initialization(self):
        mock_soapy = mock.MagicMock()
        mock_soapy.Device.enumerate.return_value = [{"driver": "rtlsdr"}]
        patches = {
            "SoapySDR": mock_soapy,
            "SOAPYSDR_AVAILABLE": True,
            "PYHACKRF_AVAILABLE": False,
        }
        with mock.patch.dict(hal_hw_module.__dict__, patches):
            with pytest.raises(HardwareInitializationError):
                HardwareHAL()

    def test_clock_mismatch_raises_clock_verification(self):
        mock_device = mock.MagicMock()
        mock_device.getClockSource.return_value = "internal"
        mock_soapy = mock.MagicMock()
        mock_soapy.Device.enumerate.return_value = [{"driver": "hackrf"}]
        mock_soapy.Device.return_value = mock_device
        patches = {
            "SoapySDR": mock_soapy,
            "SOAPYSDR_AVAILABLE": True,
            "PYHACKRF_AVAILABLE": False,
        }
        with mock.patch.dict(hal_hw_module.__dict__, patches):
            with pytest.raises(ClockVerificationError):
                HardwareHAL()


class TestPyhackrfFailurePaths:
    def test_pyhackrf_internal_clock_raises_clock_verification(self):
        mock_device = mock.MagicMock()
        mock_device.clock_source = "internal"
        mock_pyhackrf = mock.MagicMock()
        mock_pyhackrf.HackRF.return_value = mock_device
        patches = {
            "pyhackrf": mock_pyhackrf,
            "SOAPYSDR_AVAILABLE": False,
            "PYHACKRF_AVAILABLE": True,
        }
        with mock.patch.dict(hal_hw_module.__dict__, patches):
            with pytest.raises(ClockVerificationError):
                HardwareHAL()

    def test_pyhackrf_unknown_clock_raises_clock_verification(self):
        mock_device = mock.MagicMock()
        mock_device.clock_source = "unknown"
        mock_pyhackrf = mock.MagicMock()
        mock_pyhackrf.HackRF.return_value = mock_device
        patches = {
            "pyhackrf": mock_pyhackrf,
            "SOAPYSDR_AVAILABLE": False,
            "PYHACKRF_AVAILABLE": True,
        }
        with mock.patch.dict(hal_hw_module.__dict__, patches):
            with pytest.raises(ClockVerificationError):
                HardwareHAL()


class TestIngestionFailurePaths:
    def test_ingest_sdr_no_driver_returns_error_payload(self):
        patches = {
            "SOAPYSDR_AVAILABLE": False,
            "PYHACKRF_AVAILABLE": False,
        }
        with mock.patch.dict(hal_hw_module.__dict__, patches):
            hal = HardwareHAL()
            payload = hal.ingest_sdr()
            assert "error" in payload.raw_value
            assert payload.raw_value["clock_source"] == "external"

    def test_ingest_sdr_unverified_clock_raises(self):
        hal = object.__new__(HardwareHAL)
        hal.sdr_device = None
        hal._clock_verified = False
        patches = {
            "SOAPYSDR_AVAILABLE": True,
            "PYHACKRF_AVAILABLE": False,
        }
        with mock.patch.dict(hal_hw_module.__dict__, patches):
            with mock.patch.object(
                hal,
                "verify_tier1_phase_lock",
                return_value={"phase_lock_verified": False},
            ):
                with pytest.raises(ClockVerificationError):
                    hal.ingest_sdr()


class TestNMEAFailurePaths:
    def test_no_nmea_sentences(self):
        mock_serial = mock.MagicMock()
        mock_serial.readline.return_value = b""
        patches = {"serial": mock_serial}
        with mock.patch.dict(hal_hw_module.__dict__, patches):
            result = HardwareHAL.verify_nmea_telemetry()
            assert result["nmea_available"] is False
            assert result["gps_fix"] is False

    def test_serial_timeout(self):
        patches = {
            "serial": mock.MagicMock(side_effect=OSError("Port not found")),
        }
        with mock.patch.dict(hal_hw_module.__dict__, patches):
            result = HardwareHAL.verify_nmea_telemetry()
            assert result["nmea_available"] is False
            assert any("Serial port error" in w for w in result["warnings"])


class TestHDF5Unavailable:
    @mock.patch("dslv_zpdi.layer3_telemetry.hdf5_writer.HDF5_AVAILABLE", False)
    def test_primary_write_skipped_when_hdf5_unavailable(self):
        from dslv_zpdi.layer3_telemetry.hdf5_writer import HDF5Writer

        writer = HDF5Writer()
        writer.current_file = None
        # Should not raise even though h5py is unavailable
        writer._write_primary(mock.MagicMock(), "{}")
