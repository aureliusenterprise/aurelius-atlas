from pathlib import Path
from typing import Any

import pytest
from aurelius_atlas_server import ServerSettings, __main__


@pytest.mark.covers("aurelius_atlas_server.__main__.uvicorn_options", rules=["SRV-03"])
def test__uvicorn_options_serve_https_only_with_a_certificate(settings: ServerSettings, tmp_path: Path) -> None:
    """Without TLS the options have no certificate; with it, both files."""
    certificate, key = tmp_path / "c.pem", tmp_path / "k.pem"
    certificate.write_text("c\n")
    key.write_text("k\n")
    with_tls = settings.model_copy(update={"tls_cert_file": certificate, "tls_key_file": key})

    assert __main__.uvicorn_options(settings) == {"host": "localhost", "port": 21000, "log_level": "info"}
    assert __main__.uvicorn_options(with_tls) == {
        "host": "localhost",
        "port": 21000,
        "log_level": "info",
        "ssl_certfile": str(certificate),
        "ssl_keyfile": str(key),
    }


@pytest.mark.covers("aurelius_atlas_server.__main__.run", rules=["SRV-01"])
def test__run_serves_the_app_built_from_the_environment(
    monkeypatch: pytest.MonkeyPatch, ca_file: Path, fake_es: object
) -> None:
    """``run`` reads the settings from the environment and hands the app to uvicorn."""
    _ = fake_es
    monkeypatch.setenv("AURELIUS_ATLAS_SERVER_ELASTICSEARCH_HOSTS", '["https://es:9200"]')
    monkeypatch.setenv("AURELIUS_ATLAS_SERVER_ELASTICSEARCH_PASSWORD", "secret")
    monkeypatch.setenv("AURELIUS_ATLAS_SERVER_ELASTICSEARCH_CA_CERTS", str(ca_file))
    monkeypatch.setenv("AURELIUS_ATLAS_SERVER_PORT", "21443")
    calls: list[dict[str, Any]] = []
    monkeypatch.setattr(__main__.uvicorn, "run", lambda app, **options: calls.append({"app": app, **options}))

    __main__.run()

    (call,) = calls
    assert call["port"] == 21443
    assert call["app"].title == "aurelius-atlas-server"
