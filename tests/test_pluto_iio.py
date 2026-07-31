"""Unit tests for the native libiio Pluto backend (SPEC-004A.PLUTO)."""

from unittest import mock

from dslv_zpdi.layer1_ingestion.sdr import pluto_iio as pluto_iio_module
from dslv_zpdi.layer1_ingestion.sdr.capabilities import CaptureProfile
from dslv_zpdi.layer1_ingestion.sdr.pluto_iio import PlutoIioBackend


def _make_channel(attrs_dict):
    """Build a mock IIO channel whose attrs behave like a dict of mocks."""
    chan = mock.MagicMock()
    wrapped = {}
    for name, value in attrs_dict.items():
        attr_mock = mock.MagicMock()
        attr_mock.value = value
        wrapped[name] = attr_mock
    chan.attrs = wrapped
    return chan


def test_configure_falls_back_when_readback_empty():
    """SPEC-004A.PLUTO — Empty IIO read-back values must not crash capture."""
    profile = CaptureProfile(
        center_frequency_hz=100_000_000,
        sample_rate_sps=10_000_000,
        bandwidth_hz=10_000_000,
        gain_db=62.0,
        gain_mode="manual",
        receive_channels=(0,),
        transmit_enabled=False,
        buffer_samples=1024,
        num_samples=1024,
        external_clock_configured=True,
    )

    rx_lo = _make_channel({"frequency": ""})
    rx_chan = _make_channel(
        {
            "gain_control_mode": "",
            "hardwaregain": "",
            "rf_bandwidth": "",
            "sampling_frequency": "",
        }
    )

    mock_ad9361 = mock.MagicMock()
    mock_ad9361.find_channel.side_effect = lambda name, is_output: (
        rx_lo if name == "altvoltage0" else rx_chan if name == "voltage0" else None
    )

    mock_rx_dev = mock.MagicMock()
    mock_rx_dev.find_channel.return_value = mock.MagicMock()

    mock_ctx = mock.MagicMock()
    mock_ctx.find_device.side_effect = [mock_ad9361, mock_rx_dev]
    mock_ctx.attrs = {}

    mock_iio = mock.MagicMock()
    mock_iio.Context.return_value = mock_ctx

    with mock.patch.object(pluto_iio_module, "_get_iio", return_value=mock_iio):
        backend = PlutoIioBackend(uri="ip:192.168.2.1")
        applied = backend.configure(profile)

    assert applied.center_frequency_hz == profile.center_frequency_hz
    assert applied.sample_rate_sps == profile.sample_rate_sps
    assert applied.bandwidth_hz == profile.bandwidth_hz
    assert applied.gain_db == profile.gain_db
    assert applied.gain_mode == profile.gain_mode
    assert applied.external_clock_configured is True
