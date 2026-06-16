"""Tests for key provider abstraction (SPEC-018)."""

from __future__ import annotations

from pathlib import Path

import pytest

from dslv_zpdi.core.exceptions import SecurityError
from dslv_zpdi.core.key_provider import (
    DevelopmentKeyProvider,
    EnvKeyProvider,
    FileKeyProvider,
    ProductionKeyResolver,
)


class TestDevelopmentKeyProvider:
    def test_requires_explicit_simulator_acknowledgment(self):
        with pytest.raises(SecurityError):
            DevelopmentKeyProvider()

    def test_returns_predictable_key_for_simulator(self):
        provider = DevelopmentKeyProvider(acknowledged_simulator_use=True)
        key = provider.get_key()
        assert isinstance(key, bytes)
        assert key == b"dev_key_replace_before_field_deploy"


class TestFileKeyProvider:
    def test_missing_file_raises(self, tmp_path: Path):
        provider = FileKeyProvider(tmp_path / "missing.key")
        with pytest.raises(SecurityError):
            provider.get_key()

    def test_wrong_mode_raises(self, tmp_path: Path):
        key_file = tmp_path / "bad_mode.key"
        key_file.write_bytes(b"secret")
        key_file.chmod(0o644)
        provider = FileKeyProvider(key_file)
        with pytest.raises(SecurityError):
            provider.get_key()

    def test_correct_mode_returns_key(self, tmp_path: Path):
        key_file = tmp_path / "good.key"
        key_file.write_bytes(b"production-key")
        key_file.chmod(0o600)
        provider = FileKeyProvider(key_file)
        assert provider.get_key() == b"production-key"


class TestEnvKeyProvider:
    def test_unset_variable_raises(self, monkeypatch):
        monkeypatch.delenv("DSLV_TEST_KEY_FILE", raising=False)
        provider = EnvKeyProvider("DSLV_TEST_KEY_FILE")
        with pytest.raises(SecurityError):
            provider.get_key()

    def test_points_to_file_provider(self, tmp_path: Path, monkeypatch):
        key_file = tmp_path / "env.key"
        key_file.write_bytes(b"env-key")
        key_file.chmod(0o600)
        monkeypatch.setenv("DSLV_TEST_KEY_FILE", str(key_file))
        provider = EnvKeyProvider("DSLV_TEST_KEY_FILE")
        assert provider.get_key() == b"env-key"


class TestProductionKeyResolver:
    def test_no_sources_available_raises(self, monkeypatch, tmp_path: Path):
        monkeypatch.delenv("DSLV_HMAC_KEY_FILE", raising=False)
        monkeypatch.delenv("CREDENTIALS_DIRECTORY", raising=False)
        resolver = ProductionKeyResolver(file_path=str(tmp_path / "no.key"))
        with pytest.raises(SecurityError):
            resolver.get_key()

    def test_resolves_from_env(self, tmp_path: Path, monkeypatch):
        key_file = tmp_path / "prod.key"
        key_file.write_bytes(b"prod-key")
        key_file.chmod(0o600)
        monkeypatch.setenv("DSLV_HMAC_KEY_FILE", str(key_file))
        monkeypatch.delenv("CREDENTIALS_DIRECTORY", raising=False)
        resolver = ProductionKeyResolver(file_path=str(tmp_path / "no.key"))
        assert resolver.get_key() == b"prod-key"
