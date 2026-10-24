"""Unit tests for the app's settings (LM-10, DD-108)."""

from __future__ import annotations

from pathlib import Path

import pytest
from aurelius_atlas_lineage_model.settings import DEFAULT_PORT, LineageModelSettings
from pydantic import ValidationError


@pytest.fixture
def environment(monkeypatch: pytest.MonkeyPatch) -> pytest.MonkeyPatch:
    """The required settings as environment variables."""
    monkeypatch.setenv("AURELIUS_ATLAS_LINEAGE_MODEL_AUTH_SERVER_URL", "http://keycloak.localhost:8080")
    monkeypatch.setenv("AURELIUS_ATLAS_LINEAGE_MODEL_ATLAS_BASE_URL", "https://localhost:21000")
    monkeypatch.setenv("AURELIUS_ATLAS_LINEAGE_MODEL_DATA2MODEL_URL", "https://localhost:21001")
    return monkeypatch


@pytest.mark.covers("aurelius_atlas_lineage_model.settings.LineageModelSettings.tls", rules=["LM-10"])
def test__the_settings_are_read_from_prefixed_variables(environment: pytest.MonkeyPatch) -> None:
    """Prefixed variables set the settings; the port defaults to 21002; the upstreams are settings."""
    environment.setenv("PORT", "8000")

    settings = LineageModelSettings()  # pyright: ignore[reportCallIssue] - read from the environment

    assert settings.port == DEFAULT_PORT == 21002
    assert str(settings.auth_server_url) == "http://keycloak.localhost:8080/"
    assert str(settings.atlas_base_url) == "https://localhost:21000/"
    assert str(settings.data2model_url) == "https://localhost:21001/"
    assert settings.auth_realm == "master"
    assert settings.auth_audience == "aurelius-atlas-lineage-model"
    assert settings.otel_client_id == "otel-lineage-model"
    assert settings.otel_endpoint == "https://localhost:4319"
    # The ingest secret's value never appears in the repr (DD-107).
    environment.setenv("AURELIUS_ATLAS_LINEAGE_MODEL_OTEL_CLIENT_SECRET", "s3cr3t")
    assert "s3cr3t" not in repr(LineageModelSettings())  # pyright: ignore[reportCallIssue]


@pytest.mark.covers("aurelius_atlas_lineage_model.settings.LineageModelSettings.tls", rules=["LM-10"])
@pytest.mark.parametrize(
    "name",
    [
        "AURELIUS_ATLAS_LINEAGE_MODEL_AUTH_SERVER_URL",
        "AURELIUS_ATLAS_LINEAGE_MODEL_ATLAS_BASE_URL",
        "AURELIUS_ATLAS_LINEAGE_MODEL_DATA2MODEL_URL",
    ],
)
def test__a_missing_required_setting_names_itself(environment: pytest.MonkeyPatch, name: str) -> None:
    """Without the issuer or an upstream there is no app: the settings name the missing variable."""
    environment.delenv(name)
    field = name.removeprefix("AURELIUS_ATLAS_LINEAGE_MODEL_").lower()
    with pytest.raises(ValidationError, match=field):
        LineageModelSettings()  # pyright: ignore[reportCallIssue]


@pytest.mark.covers("aurelius_atlas_lineage_model.settings.LineageModelSettings.tls", rules=["LM-10"])
def test__tls_is_configured_by_a_pair(environment: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """One half of the certificate pair is a settings error; the pair yields the tuple."""
    certificate, key = tmp_path / "c.pem", tmp_path / "k.pem"
    certificate.write_text("c\n")
    key.write_text("k\n")
    environment.setenv("AURELIUS_ATLAS_LINEAGE_MODEL_TLS_CERT_FILE", str(certificate))
    with pytest.raises(ValidationError, match="TLS_CERT_FILE"):
        LineageModelSettings()  # pyright: ignore[reportCallIssue]
    environment.setenv("AURELIUS_ATLAS_LINEAGE_MODEL_TLS_KEY_FILE", str(key))
    assert LineageModelSettings().tls == (certificate, key)  # pyright: ignore[reportCallIssue]


@pytest.mark.covers("aurelius_atlas_lineage_model.settings.LineageModelSettings.tls", rules=["LM-10"])
def test__no_tls_means_plain_http(environment: pytest.MonkeyPatch) -> None:
    """With no certificate configured, tls is None."""
    _ = environment  # The issuer and upstream URLs it sets: the required settings.
    assert LineageModelSettings().tls is None  # pyright: ignore[reportCallIssue]
