from unittest.mock import MagicMock, Mock, patch

import pytest
from aurelius_atlas_fastapi_example.__main__ import run, tls_options


def test__tls_options_returns_server_tls_material() -> None:
    """TLS options are returned when both a certificate and a key are configured."""
    options = tls_options("/certs/server.pem", "/certs/server-key.pem")

    assert options == {"ssl_certfile": "/certs/server.pem", "ssl_keyfile": "/certs/server-key.pem"}


def test__tls_options_empty_without_material() -> None:
    """Without any certificate material the server stays plain HTTP."""
    assert tls_options("", "") == {}


@pytest.mark.parametrize(
    ("cert_file", "key_file"),
    [
        ("/certs/server.pem", ""),
        ("", "/certs/server-key.pem"),
    ],
)
def test__tls_options_rejects_partial_material(cert_file: str, key_file: str) -> None:
    """Configuring only one of certificate/key is a misconfiguration, not plaintext fallback."""
    with pytest.raises(ValueError, match="must both be set"):
        tls_options(cert_file, key_file)


def test__run_starts_uvicorn_with_tls(monkeypatch: pytest.MonkeyPatch, settings_server_tls: Mock) -> None:
    """run() passes host, port, and TLS options through to uvicorn."""
    monkeypatch.setattr("aurelius_atlas_fastapi_example.__main__.get_settings", lambda: settings_server_tls)

    with patch("uvicorn.run") as uv_run:
        run()

    uv_run.assert_called_once()
    args, kwargs = uv_run.call_args
    assert kwargs["factory"] is True
    assert kwargs["host"] == "127.0.0.1"
    assert kwargs["port"] == 8000
    assert kwargs["ssl_certfile"] == "/certs/server.pem"
    assert kwargs["ssl_keyfile"] == "/certs/server-key.pem"
    assert callable(args[0])


def test__run_starts_plain_http_without_tls(monkeypatch: pytest.MonkeyPatch, settings_plaintext: Mock) -> None:
    """run() omits TLS options when no certificate material is configured."""
    monkeypatch.setattr("aurelius_atlas_fastapi_example.__main__.get_settings", lambda: settings_plaintext)

    with patch("uvicorn.run") as uv_run:
        run()

    kwargs = uv_run.call_args.kwargs
    assert "ssl_certfile" not in kwargs
    assert "ssl_keyfile" not in kwargs


def test__run_builds_app_factory_from_settings(monkeypatch: pytest.MonkeyPatch, settings_plaintext: Mock) -> None:
    """The app factory passed to uvicorn constructs the application from settings."""
    monkeypatch.setattr("aurelius_atlas_fastapi_example.__main__.get_settings", lambda: settings_plaintext)

    with patch("uvicorn.run") as uv_run:
        run()

    factory = uv_run.call_args.args[0]
    with patch("aurelius_atlas_fastapi_example.__main__.main", return_value=MagicMock()) as main:
        factory()

    main.assert_called_once_with(settings_plaintext)
