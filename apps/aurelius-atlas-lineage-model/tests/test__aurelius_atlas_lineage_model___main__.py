"""Unit tests for ``python -m aurelius_atlas_lineage_model`` (the serve entry point)."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
from aurelius_atlas_lineage_model import __main__
from aurelius_atlas_lineage_model.settings import LineageModelSettings


@pytest.mark.covers("aurelius_atlas_lineage_model.__main__.uvicorn_options", rules=["LM-10"])
def test__uvicorn_options_serve_https_only_with_a_certificate(settings: LineageModelSettings, tmp_path: Path) -> None:
    """Without TLS the options have no certificate; with it, both files."""
    certificate, key = tmp_path / "c.pem", tmp_path / "k.pem"
    certificate.write_text("c\n")
    key.write_text("k\n")
    with_tls = settings.model_copy(update={"tls_cert_file": certificate, "tls_key_file": key})

    assert __main__.uvicorn_options(settings) == {"host": "localhost", "port": 21002, "log_level": "info"}
    assert __main__.uvicorn_options(with_tls) == {
        "host": "localhost",
        "port": 21002,
        "log_level": "info",
        "ssl_certfile": str(certificate),
        "ssl_keyfile": str(key),
    }


@pytest.mark.covers("aurelius_atlas_lineage_model.__main__.run", rules=["LM-10"])
def test__run_serves_the_app_built_from_the_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    """``run`` reads the settings from the environment and hands the app to uvicorn."""
    monkeypatch.setenv("AURELIUS_ATLAS_LINEAGE_MODEL_AUTH_SERVER_URL", "http://keycloak.localhost:8080")
    monkeypatch.setenv("AURELIUS_ATLAS_LINEAGE_MODEL_ATLAS_BASE_URL", "https://localhost:21000")
    monkeypatch.setenv("AURELIUS_ATLAS_LINEAGE_MODEL_DATA2MODEL_URL", "https://localhost:21001")
    monkeypatch.setenv("AURELIUS_ATLAS_LINEAGE_MODEL_PORT", "22002")
    calls: list[dict[str, Any]] = []
    monkeypatch.setattr(__main__.uvicorn, "run", lambda app, **options: calls.append({"app": app, **options}))

    __main__.run()

    assert len(calls) == 1
    assert calls[0]["port"] == 22002
    assert calls[0]["app"].title == "aurelius-atlas-lineage-model"
