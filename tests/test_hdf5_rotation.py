"""Tests for real HDF5 file rotation behavior (SPEC-007)."""

import json
import os
import tempfile
import time
import uuid
from unittest import mock

from dslv_zpdi.core.states import RouteStream, TrustState
from dslv_zpdi.layer3_telemetry.hdf5_writer import HDF5Writer
from dslv_zpdi.layer3_telemetry.router import RoutingDecision
from dslv_zpdi.layer2_core.coherence import CoherencePacket


def _primary_decision():
    return RoutingDecision(
        stream=RouteStream.PRIMARY.value,
        reason="confirmed_event",
        packet=CoherencePacket(
            payload_uuid=str(uuid.uuid4()),
            node_id="N1",
            modality="rf_sdr",
            r_local=0.8,
            r_smooth=0.8,
            r_global=0.8,
            trust_state=TrustState.PRIMARY_ACCEPTED.value,
            event_window_id=str(uuid.uuid4()),
        ),
        trust_state=TrustState.PRIMARY_ACCEPTED.value,
    )


def test_real_file_rotation():
    with tempfile.TemporaryDirectory() as td:
        writer = HDF5Writer(output_path=td, secondary_path=td)
        call_count = [0]
        original_method = HDF5Writer._file_size_exceeded

        def _always_exceed(self):
            call_count[0] += 1
            return call_count[0] > 0  # Exceed on first actual call (second write)

        HDF5Writer._file_size_exceeded = _always_exceed
        counter = [0]

        def _fake_strftime(fmt):
            counter[0] += 1
            return f"20260101_120000_{counter[0]:03d}"

        try:
            with mock.patch.object(
                writer.router, "route", return_value=_primary_decision()
            ):
                with mock.patch.object(
                    writer, "verify_packet_integrity", return_value=True
                ):
                    with mock.patch(
                        "dslv_zpdi.layer3_telemetry.hdf5_writer.time.strftime",
                        _fake_strftime,
                    ):
                        # First write — should open file_1
                        decision = writer.ingest(
                            json.dumps({"timestamp_utc": time.time()})
                        )
                file_1 = writer.current_filepath
                event_count_1 = writer.event_count

                assert file_1 is not None
                assert file_1.exists()
                assert event_count_1 == 1
                assert decision.stream == RouteStream.PRIMARY.value

                # Second write — should rotate to file_2
                with mock.patch.object(
                    writer, "verify_packet_integrity", return_value=True
                ):
                    with mock.patch(
                        "dslv_zpdi.layer3_telemetry.hdf5_writer.time.strftime",
                        _fake_strftime,
                    ):
                        decision = writer.ingest(
                            json.dumps({"timestamp_utc": time.time()})
                        )
                file_2 = writer.current_filepath
                event_count_2 = writer.event_count

                assert file_2 is not None
                assert file_2.exists()
                assert file_2 != file_1
                assert event_count_2 == 1  # Reset after rotation
        finally:
            HDF5Writer._file_size_exceeded = original_method
            writer.close()


def test_event_count_resets_on_rotation():
    with tempfile.TemporaryDirectory() as td:
        writer = HDF5Writer(output_path=td, secondary_path=td)
        original_method = HDF5Writer._file_size_exceeded

        def _always_exceed(self):
            return True

        HDF5Writer._file_size_exceeded = _always_exceed
        counter = [0]

        def _fake_strftime(fmt):
            counter[0] += 1
            return f"20260101_120000_{counter[0]:03d}"

        try:
            with mock.patch.object(
                writer.router, "route", return_value=_primary_decision()
            ):
                for i in range(3):
                    with mock.patch.object(
                        writer, "verify_packet_integrity", return_value=True
                    ):
                        with mock.patch(
                            "dslv_zpdi.layer3_telemetry.hdf5_writer.time.strftime",
                            _fake_strftime,
                        ):
                            writer.ingest(json.dumps({"timestamp_utc": time.time()}))
                    assert writer.event_count == 1
                    assert writer.current_filepath is not None
        finally:
            HDF5Writer._file_size_exceeded = original_method
            writer.close()
