from pathlib import Path

import pytest
from aurelius_atlas_core.model_loader import BUILTIN_MODELS_DIR
from aurelius_atlas_server.settings import DEFAULT_PORT, ServerSettings
from pydantic import ValidationError


@pytest.fixture
def environment(monkeypatch: pytest.MonkeyPatch, ca_file: Path, tls_pair: tuple[Path, Path]) -> pytest.MonkeyPatch:
    """The required settings as environment variables."""
    certificate, key = tls_pair
    monkeypatch.setenv("AURELIUS_ATLAS_SERVER_ELASTICSEARCH_HOSTS", '["https://es:9200"]')
    monkeypatch.setenv("AURELIUS_ATLAS_SERVER_ELASTICSEARCH_PASSWORD", "secret")
    monkeypatch.setenv("AURELIUS_ATLAS_SERVER_ELASTICSEARCH_CA_CERTS", str(ca_file))
    monkeypatch.setenv("AURELIUS_ATLAS_SERVER_TLS_CERT_FILE", str(certificate))
    monkeypatch.setenv("AURELIUS_ATLAS_SERVER_TLS_KEY_FILE", str(key))
    return monkeypatch


@pytest.mark.covers(
    "aurelius_atlas_server.settings.ServerSettings.store_settings", rules=["SRV-01", "SRV-03", "MDL-16"]
)
def test__settings_are_read_from_prefixed_variables(environment: pytest.MonkeyPatch, ca_file: Path) -> None:
    """Prefixed variables set the settings; unprefixed ones of other projects do not; the port defaults to 21000."""
    environment.setenv("PORT", "8000")

    settings = ServerSettings()  # pyright: ignore[reportCallIssue] - read from the environment
    store = settings.store_settings()

    assert settings.port == DEFAULT_PORT == 21000
    assert settings.models_dir == BUILTIN_MODELS_DIR
    assert store.host_urls == ["https://es:9200"]
    assert store.password.get_secret_value() == "secret"
    assert store.ca_certs_path == ca_file
    # The password's value never appears in the repr (SecretStr masks; the
    # quoted form is what a leaked value would look like — the bare token
    # would also match field names like otel_client_secret, DD-196).
    assert "'secret'" not in repr(settings)


@pytest.mark.covers("aurelius_atlas_server.settings.ServerSettings.store_settings", rules=["SRV-01"])
@pytest.mark.parametrize(
    ("name", "value", "problem"),
    [
        ("AURELIUS_ATLAS_SERVER_ELASTICSEARCH_PASSWORD", None, "elasticsearch_password"),
        ("AURELIUS_ATLAS_SERVER_PORT", "70000", "port"),
        ("AURELIUS_ATLAS_SERVER_ELASTICSEARCH_CA_CERTS", "/does/not/exist.pem", "elasticsearch_ca_certs"),
        ("AURELIUS_ATLAS_SERVER_TLS_CERT_FILE", None, "tls_cert_file"),
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


@pytest.mark.covers("aurelius_atlas_server.settings.ServerSettings.tls", rules=["SRV-03", "SRV-06"])
def test__tls_material_is_required(environment: pytest.MonkeyPatch, tls_pair: tuple[Path, Path]) -> None:
    """The server serves HTTPS only: certificate and key are required settings (SRV-06, DD-234).

    The pair from the environment fixture is the settings' ``tls``; dropping either names the
    missing setting at start-up — the same failure shape as the store password (SRV-01).
    """
    certificate, key = tls_pair

    assert ServerSettings().tls == (certificate, key)  # pyright: ignore[reportCallIssue]

    environment.delenv("AURELIUS_ATLAS_SERVER_TLS_CERT_FILE")
    with pytest.raises(ValidationError, match="tls_cert_file"):
        ServerSettings()  # pyright: ignore[reportCallIssue]

    environment.setenv("AURELIUS_ATLAS_SERVER_TLS_CERT_FILE", str(certificate))
    environment.delenv("AURELIUS_ATLAS_SERVER_TLS_KEY_FILE")
    with pytest.raises(ValidationError, match="tls_key_file"):
        ServerSettings()  # pyright: ignore[reportCallIssue]
