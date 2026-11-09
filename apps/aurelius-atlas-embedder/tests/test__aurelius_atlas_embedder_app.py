"""Unit tests for the composition root, the settings and the entry point (EMB-07, EMB-08, EMB-09)."""

from pathlib import Path
from typing import Any

import pytest
from aurelius_atlas_embedder import __main__
from aurelius_atlas_embedder.app import create_app
from aurelius_atlas_embedder.model import Model, ModelLoadError
from aurelius_atlas_embedder.settings import EmbedderSettings
from fastapi.testclient import TestClient
from pydantic import ValidationError


@pytest.mark.covers("aurelius_atlas_embedder.app.create_app", rules=["EMB-07"])
def test__the_model_loads_at_start_up_and_is_released_at_shutdown(settings: EmbedderSettings, model: Model) -> None:
    """The loader runs once, with the app's settings, before the app serves."""
    calls: list[EmbedderSettings] = []

    def loader(given: EmbedderSettings) -> Model:
        calls.append(given)
        return model

    app = create_app(settings, loader=loader)
    with TestClient(app) as client:
        assert app.state.model is model
        assert client.get("/readiness").status_code == 204
    assert calls == [settings]
    assert app.state.model is None


@pytest.mark.covers("aurelius_atlas_embedder.app.create_app", rules=["EMB-08"])
def test__a_model_that_cannot_load_stops_the_start(settings: EmbedderSettings) -> None:
    """The load's error ends the start-up: the app never serves without its model."""

    def loader(_settings: EmbedderSettings) -> Model:
        message = "no model"
        raise ModelLoadError(message)

    with pytest.raises(ModelLoadError, match="no model"), TestClient(create_app(settings, loader=loader)):
        pass


@pytest.mark.covers("aurelius_atlas_embedder.settings.EmbedderSettings.tls", rules=["EMB-09"])
def test__the_settings_read_their_prefix_and_default_to_the_shipped_model(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Every setting is ``AURELIUS_ATLAS_EMBEDDER_``-prefixed; the defaults are the image's model and port."""
    monkeypatch.setenv("AURELIUS_ATLAS_EMBEDDER_MODEL_DIR", str(tmp_path))
    monkeypatch.setenv("AURELIUS_ATLAS_EMBEDDER_THREADS", "2")
    monkeypatch.setenv("MODEL_DIR", "/elsewhere")

    settings = EmbedderSettings()  # pyright: ignore[reportCallIssue] - read from the environment

    assert settings.model_dir == tmp_path
    assert settings.threads == 2
    assert settings.port == 21004
    assert settings.model_id == "intfloat/multilingual-e5-small"
    assert settings.model_revision == "614241f622f53c4eeff9890bdc4f31cfecc418b3"
    assert settings.max_tokens == 512
    assert settings.tls is None


@pytest.mark.covers("aurelius_atlas_embedder.settings.EmbedderSettings.tls", rules=["EMB-09"])
def test__tls_is_a_pair_never_one_half(tmp_path: Path) -> None:
    """Both files give the pair; one alone is refused."""
    certificate, key = tmp_path / "c.pem", tmp_path / "k.pem"
    certificate.write_text("c\n")
    key.write_text("k\n")

    assert EmbedderSettings(model_dir=tmp_path, tls_cert_file=certificate, tls_key_file=key).tls == (certificate, key)
    with pytest.raises(ValidationError, match="must both be set"):
        EmbedderSettings(model_dir=tmp_path, tls_cert_file=certificate)


@pytest.mark.covers("aurelius_atlas_embedder.settings.EmbedderSettings.tls", rules=["EMB-08"])
def test__a_model_directory_that_does_not_exist_is_refused(tmp_path: Path) -> None:
    """The model's directory must exist before the app reads it."""
    with pytest.raises(ValidationError, match="model_dir"):
        EmbedderSettings(model_dir=tmp_path / "missing")


@pytest.mark.covers("aurelius_atlas_embedder.__main__.uvicorn_options", rules=["EMB-09"])
def test__uvicorn_options_serve_https_only_with_a_certificate(settings: EmbedderSettings, tmp_path: Path) -> None:
    """Without TLS the options have no certificate; with it, both files."""
    certificate, key = tmp_path / "c.pem", tmp_path / "k.pem"
    certificate.write_text("c\n")
    key.write_text("k\n")
    with_tls = settings.model_copy(update={"tls_cert_file": certificate, "tls_key_file": key})

    assert __main__.uvicorn_options(settings) == {"host": "localhost", "port": 21004, "log_level": "info"}
    assert __main__.uvicorn_options(with_tls) == {
        "host": "localhost",
        "port": 21004,
        "log_level": "info",
        "ssl_certfile": str(certificate),
        "ssl_keyfile": str(key),
    }


@pytest.mark.covers("aurelius_atlas_embedder.__main__.run", rules=["EMB-09"])
def test__run_serves_the_app_built_from_the_environment(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """``run`` reads the settings from the environment and hands the app to uvicorn."""
    monkeypatch.setenv("AURELIUS_ATLAS_EMBEDDER_MODEL_DIR", str(tmp_path))
    monkeypatch.setenv("AURELIUS_ATLAS_EMBEDDER_PORT", "22004")
    calls: list[dict[str, Any]] = []
    monkeypatch.setattr(__main__.uvicorn, "run", lambda app, **options: calls.append({"app": app, **options}))

    __main__.run()

    assert len(calls) == 1
    assert calls[0]["port"] == 22004
    assert calls[0]["app"].title == "aurelius-atlas-embedder"
