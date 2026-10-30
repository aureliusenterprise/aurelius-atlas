from pathlib import Path
from typing import Any

import pytest
from aurelius_atlas_server import ServerSettings, __main__


@pytest.mark.covers("aurelius_atlas_server.__main__.uvicorn_options", rules=["SRV-03", "SRV-06", "SRV-10"])
def test__uvicorn_options_always_serve_https(settings: ServerSettings, tls_pair: tuple[Path, Path]) -> None:
    """The TLS pair is in the options unconditionally — the settings cannot construct without it (DD-234).

    ``forwarded_allow_ips`` rides along: uvicorn trusts only the loopback by default, so the proxy hop
    has to be declared for ``X-Forwarded-For`` to be read at all (SRV-10).
    """
    certificate, key = tls_pair

    assert __main__.uvicorn_options(settings) == {
        "host": "localhost",
        "port": 21000,
        "log_level": "info",
        "ssl_certfile": str(certificate),
        "ssl_keyfile": str(key),
        "forwarded_allow_ips": "127.0.0.1",
    }


@pytest.mark.covers("aurelius_atlas_server.__main__.uvicorn_options", rules=["SRV-10"])
def test__uvicorn_trusts_the_configured_proxy_networks(settings: ServerSettings) -> None:
    """The dev/e2e arrangement names the proxy's network, and uvicorn is told (SRV-10, DD-238)."""
    options = __main__.uvicorn_options(settings.model_copy(update={"forwarded_allow_ips": "172.20.0.0/16"}))

    assert options["forwarded_allow_ips"] == "172.20.0.0/16"


@pytest.mark.covers("aurelius_atlas_server.__main__.run", rules=["SRV-01", "SRV-06"])
def test__run_serves_the_app_built_from_the_environment(
    monkeypatch: pytest.MonkeyPatch, ca_file: Path, tls_pair: tuple[Path, Path], fake_es: object
) -> None:
    """``run`` reads the settings from the environment and hands the app to uvicorn."""
    _ = fake_es
    certificate, key = tls_pair
    monkeypatch.setenv("AURELIUS_ATLAS_SERVER_ELASTICSEARCH_HOSTS", '["https://es:9200"]')
    monkeypatch.setenv("AURELIUS_ATLAS_SERVER_ELASTICSEARCH_PASSWORD", "secret")
    monkeypatch.setenv("AURELIUS_ATLAS_SERVER_ELASTICSEARCH_CA_CERTS", str(ca_file))
    monkeypatch.setenv("AURELIUS_ATLAS_SERVER_TLS_CERT_FILE", str(certificate))
    monkeypatch.setenv("AURELIUS_ATLAS_SERVER_TLS_KEY_FILE", str(key))
    monkeypatch.setenv("AURELIUS_ATLAS_SERVER_PORT", "21443")
    calls: list[dict[str, Any]] = []
    monkeypatch.setattr(__main__.uvicorn, "run", lambda app, **options: calls.append({"app": app, **options}))

    __main__.run()

    (call,) = calls
    assert call["port"] == 21443
    assert call["ssl_certfile"] == str(certificate)
    assert call["app"].title == "aurelius-atlas-server"
