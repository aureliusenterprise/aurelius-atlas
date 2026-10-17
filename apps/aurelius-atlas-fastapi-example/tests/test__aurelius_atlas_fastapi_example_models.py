"""Unit tests for the Settings transport-security validation."""

from typing import Any

import pytest
from aurelius_atlas_fastapi_example.models import Settings
from pydantic import HttpUrl, SecretStr, TypeAdapter


@pytest.fixture(autouse=True)
def _ambient_settings_env_removed(monkeypatch: pytest.MonkeyPatch) -> None:
    """Remove every Settings-derived variable from the environment.

    ``Settings`` is a ``BaseSettings`` and Nx injects the project ``.env`` into
    every task environment, so ambient values (e.g. ``AURELIUS_ATLAS_FASTAPI_DATABASE_SSLMODE``)
    would otherwise override the model defaults these scenarios deliberately
    leave unset. Deleting each field's variable (prefix from the model config,
    so it cannot drift) makes the defaults under test the model's own,
    deterministically.
    """
    prefix = Settings.model_config.get("env_prefix") or ""
    for name in Settings.model_fields:
        monkeypatch.delenv(f"{prefix}{name.upper()}", raising=False)


def _settings_kwargs(**overrides: Any) -> dict[str, Any]:  # noqa: ANN401
    """Return Settings kwargs for the given environment scenario."""
    kwargs: dict[str, Any] = {
        "auth_realm_name": "test-realm",
        "auth_server_url": TypeAdapter(HttpUrl).validate_python("http://localhost:8080"),
        "database_password": SecretStr("secret"),
    }
    kwargs.update(overrides)
    return kwargs


class TestEnforceTransportSecurity:
    """The fail-closed validator for non-development deployments."""

    def test_development_allows_plaintext_defaults(self) -> None:
        """Development mode keeps the convenient plaintext defaults."""
        settings = Settings(**_settings_kwargs(environment="development"))

        assert settings.is_development
        assert settings.database_sslmode == "prefer"

    def test_production_rejects_unverified_sslmode(self) -> None:
        """Production must not run with the default opportunistic sslmode."""
        with pytest.raises(ValueError, match="does not verify the database server"):
            Settings(**_settings_kwargs(environment="production", tls_cert_file="/c.pem", tls_key_file="/k.pem"))

    @pytest.mark.parametrize("sslmode", ["disable", "allow", "prefer"])
    def test_production_rejects_each_unverified_sslmode(self, sslmode: str) -> None:
        """Every sslmode that skips certificate verification is rejected."""
        with pytest.raises(ValueError, match="verify-ca"):
            Settings(
                **_settings_kwargs(
                    environment="production",
                    database_sslmode=sslmode,
                    tls_cert_file="/c.pem",
                    tls_key_file="/k.pem",
                )
            )

    @pytest.mark.parametrize("sslmode", ["verify-ca", "verify-full"])
    def test_production_verify_sslmodes_require_rootcert(self, sslmode: str) -> None:
        """Verification modes are unusable without the CA bundle."""
        with pytest.raises(ValueError, match="DATABASE_SSLROOTCERT"):
            Settings(
                **_settings_kwargs(
                    environment="production",
                    database_sslmode=sslmode,
                    database_sslrootcert="",
                    tls_cert_file="/c.pem",
                    tls_key_file="/k.pem",
                )
            )

    def test_production_requires_server_tls(self) -> None:
        """The API must never serve bearer tokens over plain HTTP."""
        with pytest.raises(ValueError, match="TLS_CERT_FILE"):
            Settings(
                **_settings_kwargs(
                    environment="production",
                    database_sslmode="verify-full",
                    database_sslrootcert="/ca.pem",
                )
            )

    def test_production_requires_tls_key_too(self) -> None:
        """A certificate without its key is an invalid TLS configuration."""
        with pytest.raises(ValueError, match="TLS_KEY_FILE"):
            Settings(
                **_settings_kwargs(
                    environment="production",
                    database_sslmode="verify-full",
                    database_sslrootcert="/ca.pem",
                    tls_cert_file="/c.pem",
                    tls_key_file="",
                )
            )

    def test_production_accepts_hardened_configuration(self) -> None:
        """A fully hardened configuration passes validation."""
        settings = Settings(
            **_settings_kwargs(
                environment="production",
                database_sslmode="verify-full",
                database_sslrootcert="/ca.pem",
                tls_cert_file="/c.pem",
                tls_key_file="/k.pem",
            )
        )

        assert not settings.is_development
        assert "sslmode=verify-full" in str(settings.database_url)

    def test_non_development_environment_name_is_enforced(self) -> None:
        """Anything but 'development' (e.g. 'staging') is treated as production."""
        with pytest.raises(ValueError, match="does not verify the database server"):
            Settings(**_settings_kwargs(environment="staging", tls_cert_file="/c.pem", tls_key_file="/k.pem"))
