"""Tests for new CLI entry points (SPEC-011.CLI)."""

from __future__ import annotations

import json

from dslv_zpdi.cli.preflight import preflight_main
from dslv_zpdi.cli.probe import probe_main
from dslv_zpdi.cli.verify import verify_main


class TestProbeCli:
    def test_version_flag(self, capsys):
        with pytest.raises(SystemExit) as exc:
            probe_main(["--version"])
        assert exc.value.code == 0
        captured = capsys.readouterr()
        assert "dslv-zpdi" in captured.out

    def test_discover_json_output(self, capsys):
        probe_main(["--discover"])
        captured = capsys.readouterr()
        report = json.loads(captured.out)
        assert report["mode"] == "discover"
        assert "iio_available" in report


class TestPreflightCli:
    def test_simulator_preflight_runs(self, capsys):
        preflight_main(
            [
                "--profile",
                "config/node_profiles/simulator.yaml",
                "--simulator",
            ]
        )
        captured = capsys.readouterr()
        report = json.loads(captured.out)
        assert report["profile_id"] == "simulator-only"
        assert "checks" in report


class TestVerifyCli:
    def test_missing_path_returns_2(self, capsys):
        code = verify_main(["/nonexistent/path.h5"])
        assert code == 2


import pytest  # noqa: E402, F401
