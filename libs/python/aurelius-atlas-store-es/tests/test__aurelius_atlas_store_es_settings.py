from pathlib import Path

import pytest
from aurelius_atlas_store_es import StoreSettings
from aurelius_atlas_store_es.settings import HTTPS_ONLY_ERROR
from pydantic import ValidationError


@pytest.mark.covers(
    "aurelius_atlas_store_es.StoreSettings.host_urls",
    "aurelius_atlas_store_es.StoreSettings.ca_certs_path",
    rules=["STO-01"],
)
def test__store_settings_are_built_from_explicit_values(ca_file: Path, password: str) -> None:
    """The settings object carries everything the store needs."""
    settings = StoreSettings.model_validate(
        {
            "hosts": ["https://es-1:9200", "https://es-2:9200/"],
            "username": "atlas",
            "password": password,
            "ca_certs": ca_file,
            "request_timeout": 3.5,
        },
    )

    assert settings.host_urls == ["https://es-1:9200", "https://es-2:9200"]
    assert settings.username == "atlas"
    assert settings.password.get_secret_value() == password
    assert settings.ca_certs_path == ca_file
    assert settings.request_timeout == 3.5


@pytest.mark.covers(rules=["STO-01"])
def test__store_settings_ignore_the_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    """Environment variables never fill in settings."""
    for name in ("HOSTS", "PASSWORD", "CA_CERTS", "ELASTICSEARCH_HOSTS", "ELASTIC_PASSWORD"):
        monkeypatch.setenv(name, "from-the-environment")

    with pytest.raises(ValidationError) as caught:
        StoreSettings.model_validate({})

    assert {error["loc"][0] for error in caught.value.errors()} == {"hosts", "password", "ca_certs"}


@pytest.mark.covers(rules=["STO-02"])
def test__store_settings_reject_plain_http(ca_file: Path, password: str) -> None:
    """Connections are HTTPS only."""
    with pytest.raises(ValidationError, match=HTTPS_ONLY_ERROR):
        StoreSettings.model_validate({"hosts": ["http://localhost:9200"], "password": password, "ca_certs": ca_file})


@pytest.mark.covers(rules=["STO-02"])
def test__store_settings_have_no_switch_to_skip_certificate_verification() -> None:
    """No field can turn certificate verification off."""
    assert not any("verify" in name or "insecure" in name for name in StoreSettings.model_fields)


@pytest.mark.covers(rules=["STO-02"])
def test__store_settings_require_an_existing_ca_file(tmp_path: Path, password: str) -> None:
    """Verification needs a CA file that exists."""
    with pytest.raises(ValidationError):
        StoreSettings.model_validate(
            {"hosts": ["https://localhost:9200"], "password": password, "ca_certs": tmp_path / "missing.pem"},
        )


@pytest.mark.covers(rules=["STO-08"])
def test__store_settings_hide_the_password(settings: StoreSettings, password: str) -> None:
    """The password is not part of the settings' repr or string form."""
    assert password not in repr(settings)
    assert password not in str(settings)
