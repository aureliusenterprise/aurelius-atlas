"""Unit tests for the app's settings (DTM-10, DD-197)."""

from __future__ import annotations

from pathlib import Path

import pytest
from aurelius_atlas_data2model.settings import DEFAULT_PORT, Data2ModelSettings
from pydantic import ValidationError


@pytest.fixture
def environment(monkeypatch: pytest.MonkeyPatch) -> pytest.MonkeyPatch:
    """The required settings as environment variables."""
    monkeypatch.setenv("AURELIUS_ATLAS_DATA2MODEL_AUTH_SERVER_URL", "http://keycloak.localhost:8080")
    return monkeypatch


@pytest.mark.covers("aurelius_atlas_data2model.settings.Data2ModelSettings.tls", rules=["DTM-10"])
def test__settings_are_read_from_prefixed_variables(environment: pytest.MonkeyPatch) -> None:
    """Prefixed variables set the settings; the port defaults to 21001; the audience is the app's client id."""
    environment.setenv("PORT", "8000")

    settings = Data2ModelSettings()  # pyright: ignore[reportCallIssue] - read from the environment

    assert settings.port == DEFAULT_PORT == 21001
    assert str(settings.auth_server_url) == "http://keycloak.localhost:8080/"
    assert settings.auth_realm == "master"
    assert settings.auth_audience == "aurelius-atlas-data2model"
    assert settings.otel_client_id == "otel-data2model"
    assert settings.otel_endpoint == "https://localhost:4319"
    # The ingest secret's value never appears in the repr (DD-196).
    environment.setenv("AURELIUS_ATLAS_DATA2MODEL_OTEL_CLIENT_SECRET", "s3cr3t")
    assert "s3cr3t" not in repr(Data2ModelSettings())  # pyright: ignore[reportCallIssue]


@pytest.mark.covers("aurelius_atlas_data2model.settings.Data2ModelSettings.tls", rules=["DTM-10"])
def test__a_missing_auth_server_url_names_itself(monkeypatch: pytest.MonkeyPatch) -> None:
    """Without an issuer there is no app: the settings name the missing variable."""
    monkeypatch.delenv("AURELIUS_ATLAS_DATA2MODEL_AUTH_SERVER_URL", raising=False)
    with pytest.raises(ValidationError, match="auth_server_url"):
        Data2ModelSettings()  # pyright: ignore[reportCallIssue]


@pytest.mark.covers("aurelius_atlas_data2model.settings.Data2ModelSettings.tls", rules=["DTM-10"])
def test__tls_is_configured_by_a_pair(environment: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """One half of the certificate pair is a settings error; the pair yields the tuple."""
    certificate, key = tmp_path / "c.pem", tmp_path / "k.pem"
    certificate.write_text("c\n")
    key.write_text("k\n")
    environment.setenv("AURELIUS_ATLAS_DATA2MODEL_TLS_CERT_FILE", str(certificate))
    with pytest.raises(ValidationError, match="TLS_CERT_FILE"):
        Data2ModelSettings()  # pyright: ignore[reportCallIssue]
    environment.setenv("AURELIUS_ATLAS_DATA2MODEL_TLS_KEY_FILE", str(key))
    assert Data2ModelSettings().tls == (certificate, key)  # pyright: ignore[reportCallIssue]


@pytest.mark.covers("aurelius_atlas_data2model.settings.Data2ModelSettings.tls", rules=["DTM-10"])
def test__no_tls_means_plain_http(environment: pytest.MonkeyPatch) -> None:
    """With no certificate configured, tls is None."""
    _ = environment  # The issuer URL it sets: the only required setting.
    assert Data2ModelSettings().tls is None  # pyright: ignore[reportCallIssue]
