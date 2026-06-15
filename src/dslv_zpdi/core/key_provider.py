"""
SPEC-018 | Production key provider abstraction for HMAC-SHA256 manifest authentication.

The key material is never logged, serialized, or exposed in exception messages.
"""

from __future__ import annotations

import os
import stat
from abc import ABC, abstractmethod
from pathlib import Path

from dslv_zpdi.core.exceptions import SecurityError


class KeyProvider(ABC):
    """SPEC-018.1 — Abstract source of HMAC key bytes."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Human-readable provider name (no key material)."""
        ...

    @abstractmethod
    def get_key(self) -> bytes:
        """Return raw key bytes. Raises SecurityError if unavailable."""
        ...


class FileKeyProvider(KeyProvider):
    """SPEC-018.2 — Load key from a root-owned file with mode 0600."""

    def __init__(self, path: str | Path, required_mode: int = 0o600) -> None:
        self.path = Path(path)
        self.required_mode = required_mode

    @property
    def name(self) -> str:
        return f"file:{self.path}"

    def get_key(self) -> bytes:
        if not self.path.exists():
            raise SecurityError(f"Key file does not exist: {self.path}")
        mode = stat.S_IMODE(self.path.stat().st_mode)
        if mode != self.required_mode:
            raise SecurityError(
                f"Key file {self.path} has mode {oct(mode)}; require {oct(self.required_mode)}"
            )
        try:
            return self.path.read_bytes()
        except OSError as exc:
            raise SecurityError(f"Cannot read key file {self.path}: {exc}") from exc


class EnvKeyProvider(KeyProvider):
    """SPEC-018.3 — Load key from an environment variable pointing to a key file."""

    def __init__(self, env_var: str = "DSLV_HMAC_KEY_FILE") -> None:
        self.env_var = env_var

    @property
    def name(self) -> str:
        return f"env:{self.env_var}"

    def get_key(self) -> bytes:
        path = os.getenv(self.env_var)
        if not path:
            raise SecurityError(f"Environment variable {self.env_var} is not set")
        return FileKeyProvider(path).get_key()


class SystemdCredentialKeyProvider(KeyProvider):
    """SPEC-018.4 — Load key from a systemd credential (LoadCredential=)."""

    def __init__(self, credential_id: str = "hmac_key") -> None:
        self.credential_id = credential_id

    @property
    def name(self) -> str:
        return f"systemd-credential:{self.credential_id}"

    def get_key(self) -> bytes:
        cred_dir = os.getenv("CREDENTIALS_DIRECTORY")
        if not cred_dir:
            raise SecurityError("CREDENTIALS_DIRECTORY not set; not running under systemd with LoadCredential=")
        path = Path(cred_dir) / self.credential_id
        if not path.exists():
            raise SecurityError(f"Systemd credential not found: {path}")
        try:
            return path.read_bytes()
        except OSError as exc:
            raise SecurityError(f"Cannot read systemd credential {path}: {exc}") from exc


class DevelopmentKeyProvider(KeyProvider):
    """
    SPEC-018.5 — Predictable key for simulator/CI use only.

    Never use in field mode. The constructor requires explicit opt-in to make
    accidental production use obvious in code review.
    """

    _KEY = b"dev_key_replace_before_field_deploy"

    def __init__(self, *, acknowledged_simulator_use: bool = False) -> None:
        if not acknowledged_simulator_use:
            raise SecurityError(
                "DevelopmentKeyProvider must be constructed with acknowledged_simulator_use=True"
            )

    @property
    def name(self) -> str:
        return "development-simulator"

    def get_key(self) -> bytes:
        return self._KEY


class ProductionKeyResolver(KeyProvider):
    """
    SPEC-018.6 — Resolve a production key from file, environment, or systemd credential.

    Order: file (default /etc/dslv-zpdi/hmac.key) → env → systemd credential.
    """

    def __init__(
        self,
        file_path: str | Path = "/etc/dslv-zpdi/hmac.key",
        env_var: str = "DSLV_HMAC_KEY_FILE",
        credential_id: str = "hmac_key",
    ) -> None:
        self.providers: list[KeyProvider] = [
            FileKeyProvider(file_path),
            EnvKeyProvider(env_var),
            SystemdCredentialKeyProvider(credential_id),
        ]

    @property
    def name(self) -> str:
        return "production-resolver"

    def get_key(self) -> bytes:
        errors: list[str] = []
        for provider in self.providers:
            try:
                return provider.get_key()
            except SecurityError as exc:
                errors.append(f"{provider.name}: {exc}")
        raise SecurityError(
            "No production HMAC key available; " + "; ".join(errors)
        )
