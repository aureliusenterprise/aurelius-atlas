from pathlib import Path

import pytest
from aurelius_atlas_core.model_loader import BUILTIN_MODELS_DIR
from aurelius_atlas_server.settings import DEFAULT_PORT, ServerSettings
from pydantic import ValidationError


@pytest.fixture
def environment(monkeypatch: pytest.MonkeyPatch, ca_file: Path) -> pytest.MonkeyPatch:
    """The required settings as environment variables."""
    monkeypatch.setenv("AURELIUS_ATLAS_SERVER_ELASTICSEARCH_HOSTS", '["https://es:9200"]')
    monkeypatch.setenv("AURELIUS_ATLAS_SERVER_ELASTICSEARCH_PASSWORD", "sup3rs3cr3t")
    monkeypatch.setenv("AURELIUS_ATLAS_SERVER_ELASTICSEARCH_CA_CERTS", str(ca_file))
    return monkeypatch


@pytest.mark.covers(
    "aurelius_atlas_server.settings.ServerSettings.store_settings", rules=["SRV-01", "SRV-03", "MDL-16"]
)
def test__settings_are_read_from_prefixed_variables(environment: pytest.MonkeyPatch, ca_file: Path) -> None:
    """Prefixed variables set the settings; unprefixed ones of other projects do not; the port defaults to 21000."""
    environment.setenv("PORT", "8000")
    environment.setenv("AURELIUS_ATLAS_SERVER_AUTH_CLIENT_SECRET", "rp-secret")

    settings = ServerSettings()  # pyright: ignore[reportCallIssue] - read from the environment
    store = settings.store_settings()

    assert settings.port == DEFAULT_PORT == 21000
    assert settings.models_dir == BUILTIN_MODELS_DIR
    assert store.host_urls == ["https://es:9200"]
    assert store.password.get_secret_value() == "sup3rs3cr3t"
    assert store.ca_certs_path == ca_file
    assert "sup3rs3cr3t" not in repr(settings)
    assert "rp-secret" not in repr(settings)


@pytest.mark.covers("aurelius_atlas_server.settings.ServerSettings.store_settings", rules=["SRV-01"])
@pytest.mark.parametrize(
    ("name", "value", "problem"),
    [
        ("AURELIUS_ATLAS_SERVER_ELASTICSEARCH_PASSWORD", None, "elasticsearch_password"),
        ("AURELIUS_ATLAS_SERVER_PORT", "70000", "port"),
        ("AURELIUS_ATLAS_SERVER_ELASTICSEARCH_CA_CERTS", "/does/not/exist.pem", "elasticsearch_ca_certs"),
    ],
)
def test__a_missing_or_invalid_setting_names_itself(
    environment: pytest.MonkeyPatch, name: str, value: str | None, problem: str
) -> None:
    """Start-up stops with an error that names the setting."""
    if value is None:
        environment.delenv(name)
    else:
        environment.setenv(name, value)

    with pytest.raises(ValidationError, match=problem):
        ServerSettings()  # pyright: ignore[reportCallIssue] - read from the environment


@pytest.mark.covers("aurelius_atlas_server.settings.ServerSettings.tls", rules=["SRV-03"])
def test__tls_needs_both_certificate_and_key(environment: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """Certificate and key together enable HTTPS; one without the other is an error."""
    certificate, key = tmp_path / "server.pem", tmp_path / "server-key.pem"
    certificate.write_text("cert\n")
    key.write_text("key\n")

    assert ServerSettings().tls is None  # pyright: ignore[reportCallIssue]

    environment.setenv("AURELIUS_ATLAS_SERVER_TLS_CERT_FILE", str(certificate))
    with pytest.raises(ValidationError, match="must both be set"):
        ServerSettings()  # pyright: ignore[reportCallIssue]

    environment.setenv("AURELIUS_ATLAS_SERVER_TLS_KEY_FILE", str(key))
    assert ServerSettings().tls == (certificate, key)  # pyright: ignore[reportCallIssue]


@pytest.mark.covers("aurelius_atlas_server.settings.ServerSettings.auth_enabled", rules=["AUTH-01"])
def test__authentication_is_on_with_an_issuer_and_needs_its_trio(environment: pytest.MonkeyPatch) -> None:
    """No issuer means no authentication; an issuer without its secret or redirect URI is an error."""
    assert ServerSettings().auth_enabled is False  # pyright: ignore[reportCallIssue]

    environment.setenv("AURELIUS_ATLAS_SERVER_AUTH_ISSUER", "https://keycloak.localhost:8443/realms/master")
    with pytest.raises(ValidationError, match="AUTH_CLIENT_SECRET"):
        ServerSettings()  # pyright: ignore[reportCallIssue]

    environment.setenv("AURELIUS_ATLAS_SERVER_AUTH_CLIENT_SECRET", "rp-secret")
    environment.setenv("AURELIUS_ATLAS_SERVER_AUTH_REDIRECT_URI", "https://localhost:8444/api/atlas/auth/callback")
    settings = ServerSettings()  # pyright: ignore[reportCallIssue]
    assert settings.auth_enabled is True
    assert settings.auth_client_id == "aurelius-atlas"
