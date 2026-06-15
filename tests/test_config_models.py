"""Tests for configuration profile models (SPEC-004A.CONFIG)."""

from __future__ import annotations

from pathlib import Path

import pytest

from dslv_zpdi.config_models import EnvExpansionError, NodeProfile, expand_env_vars


class TestEnvExpansion:
    def test_expands_existing_variable(self, monkeypatch):
        monkeypatch.setenv("DSLV_TEST_VAR", "hello")
        assert expand_env_vars("${DSLV_TEST_VAR}") == "hello"

    def test_uses_default_when_unset(self, monkeypatch):
        monkeypatch.delenv("DSLV_TEST_VAR", raising=False)
        assert expand_env_vars("${DSLV_TEST_VAR:-default}") == "default"

    def test_raises_when_unset_and_no_default(self, monkeypatch):
        monkeypatch.delenv("DSLV_TEST_VAR", raising=False)
        with pytest.raises(EnvExpansionError):
            expand_env_vars("${DSLV_TEST_VAR}")

    def test_recursive_expansion(self, monkeypatch):
        monkeypatch.setenv("DSLV_TEST_VAR", "world")
        result = expand_env_vars({"key": "${DSLV_TEST_VAR}", "list": ["${DSLV_TEST_VAR}"]})
        assert result == {"key": "world", "list": ["world"]}


class TestNodeProfileLoad:
    def test_loads_simulator_profile(self):
        profile = NodeProfile.from_yaml("config/node_profiles/simulator.yaml")
        assert profile.identity.profile_id == "simulator-only"
        assert profile.sdr.backend == "simulated"
        assert profile.trust.allow_simulator_fallback is True

    def test_loads_pluto_profile(self):
        profile = NodeProfile.from_yaml("config/node_profiles/tier1_pluto_lbe1421.yaml")
        assert profile.identity.profile_id == "tier1-pluto-lbe1421"
        assert profile.sdr.backend == "pluto_iio"
        assert profile.trust.fail_closed is True

    def test_env_expansion_in_profile(self, monkeypatch, tmp_path: Path):
        monkeypatch.setenv("DSLV_SDR_URI", "ip:10.0.0.42")
        profile = NodeProfile.from_yaml("config/node_profiles/tier1_pluto_lbe1421.yaml")
        assert profile.sdr.uri == "ip:10.0.0.42"
