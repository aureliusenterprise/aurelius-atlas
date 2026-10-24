"""Unit tests for the app's settings (VE-05, DD-197)."""

from __future__ import annotations

from pathlib import Path

import pytest
from aurelius_atlas_validate_entity.settings import DEFAULT_PORT, ValidateEntitySettings
from pydantic import ValidationError


@pytest.fixture
def environment(monkeypatch: pytest.MonkeyPatch) -> pytest.MonkeyPatch:
    """The required settings as environment variables."""
    monkeypatch.setenv("AURELIUS_ATLAS_VALIDATE_ENTITY_AUTH_SERVER_URL", "http://keycloak.localhost:8080")
    return monkeypatch


@pytest.mark.covers("aurelius_atlas_validate_entity.settings.ValidateEntitySettings.tls", rules=["VE-05"])
def test__the_settings_are_read_from_prefixed_variables(environment: pytest.MonkeyPatch) -> None:
    """Prefixed variables set the settings; the port defaults to 21003 (VE-05)."""
    environment.setenv("PORT", "8000")

    settings = ValidateEntitySettings()  # pyright: ignore[reportCallIssue] - read from the environment

    assert settings.port == DEFAULT_PORT == 21003
    assert str(settings.auth_server_url) == "http://keycloak.localhost:8080/"
    assert settings.auth_realm == "master"
    assert settings.auth_audience == "aurelius-atlas-validate-entity"
    assert settings.otel_client_id == "otel-validate-entity"
    assert settings.otel_endpoint == "https://localhost:4319"
    # The ingest secret's value never appears in the repr (DD-196).
    environment.setenv("AURELIUS_ATLAS_VALIDATE_ENTITY_OTEL_CLIENT_SECRET", "s3cr3t")
    assert "s3cr3t" not in repr(ValidateEntitySettings())  # pyright: ignore[reportCallIssue]


@pytest.mark.covers("aurelius_atlas_validate_entity.settings.ValidateEntitySettings.tls", rules=["VE-05"])
def test__a_missing_required_setting_names_itself(environment: pytest.MonkeyPatch) -> None:
    """Without the issuer there is no app: the settings name the missing variable."""
    environment.delenv("AURELIUS_ATLAS_VALIDATE_ENTITY_AUTH_SERVER_URL")
    with pytest.raises(ValidationError, match="auth_server_url"):
        ValidateEntitySettings()  # pyright: ignore[reportCallIssue]


@pytest.mark.covers("aurelius_atlas_validate_entity.settings.ValidateEntitySettings.tls", rules=["VE-05"])
def test__tls_is_configured_by_a_pair(environment: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """One half of the certificate pair is a settings error; the pair yields the tuple."""
    certificate, key = tmp_path / "c.pem", tmp_path / "k.pem"
    certificate.write_text("c\n")
    key.write_text("k\n")
    environment.setenv("AURELIUS_ATLAS_VALIDATE_ENTITY_TLS_CERT_FILE", str(certificate))
    with pytest.raises(ValidationError, match="TLS_CERT_FILE"):
        ValidateEntitySettings()  # pyright: ignore[reportCallIssue]
    environment.setenv("AURELIUS_ATLAS_VALIDATE_ENTITY_TLS_KEY_FILE", str(key))
    assert ValidateEntitySettings().tls == (certificate, key)  # pyright: ignore[reportCallIssue]


@pytest.mark.covers("aurelius_atlas_validate_entity.settings.ValidateEntitySettings.tls", rules=["VE-05"])
def test__no_tls_means_plain_http(environment: pytest.MonkeyPatch) -> None:
    """With no certificate configured, tls is None."""
    _ = environment  # The issuer URL it sets: the required setting.
    assert ValidateEntitySettings().tls is None  # pyright: ignore[reportCallIssue]
