"""MCP-16: the settings arrive as ``AURELIUS_ATLAS_MCP_``-prefixed environment variables."""

from typing import Any

import pytest
from aurelius_atlas_mcp.globals import LIVENESS_PATH  # imports the package, so the module path resolves
from aurelius_atlas_mcp.settings import (
    DEFAULT_PORT,
    DEFAULT_SERVER_URL,
    DEFAULT_VALIDATE_ENTITY_URL,
    DEFAULT_WRITE_ROLE,
    DEFAULT_WRITE_ROLE_CLIENT,
    TLS_PAIR_ERROR,
    McpSettings,
)


def _settings(**overrides: Any) -> McpSettings:  # noqa: ANN401 - the settings' own values
    """The settings with the fake issuer and any overrides (the env stays clean per conftest)."""
    values: dict[str, Any] = {"auth_server_url": "http://issuer.test"}
    values.update(overrides)
    return McpSettings(**values)


@pytest.mark.covers(rules=["MCP-16"])
def test__settings_read_the_prefixed_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    """Every setting is an environment variable under the app's own prefix, and only that prefix."""
    monkeypatch.setenv("AURELIUS_ATLAS_MCP_PORT", "23000")
    monkeypatch.setenv("AURELIUS_ATLAS_MCP_LOG_LEVEL", "debug")
    monkeypatch.setenv("AURELIUS_ATLAS_MCP_AUTH_SERVER_URL", "http://issuer.test")
    monkeypatch.setenv("AURELIUS_ATLAS_MCP_SERVER_BASE_URL", "http://catalogue.test")
    monkeypatch.setenv("AURELIUS_ATLAS_MCP_UNSHADOWED_KEY", "ignored")  # extra=ignore: other keys pass by
    # A value without the prefix must not set the setting (root AGENTS.md's shadowing rule).
    monkeypatch.setenv("PORT", "1")
    settings = McpSettings()  # pyright: ignore[reportCallIssue] - read from the environment
    assert settings.port == 23000
    assert settings.log_level == "debug"
    assert str(settings.server_base_url) == "http://catalogue.test/"


@pytest.mark.covers(rules=["MCP-16"])
def test__settings_require_the_auth_issuer() -> None:
    """The auth block is required: the app cannot run without knowing who issues tokens (MCP-02)."""
    with pytest.raises(ValueError, match="auth_server_url"):
        McpSettings(_env_file=None)  # pyright: ignore[reportCallIssue] - the missing-field probe reads the environment


@pytest.mark.covers(rules=["MCP-16"])
def test__settings_default_to_the_dev_services() -> None:
    """The defaults are the dev services: the port of the band, the dev server, the dev verdicts API."""
    settings = _settings()
    assert settings.port == DEFAULT_PORT
    assert str(settings.server_base_url) == f"{DEFAULT_SERVER_URL}/"
    assert str(settings.validate_entity_base_url) == f"{DEFAULT_VALIDATE_ENTITY_URL}/"
    assert settings.write_role == DEFAULT_WRITE_ROLE
    assert settings.write_role_client == DEFAULT_WRITE_ROLE_CLIENT
    assert settings.auth_audience == "aurelius"


@pytest.mark.covers("aurelius_atlas_mcp.settings.McpSettings.tls", rules=["MCP-16"])
def test__tls_needs_the_pair(tmp_path: Any) -> None:  # noqa: ANN401 - pytest's tmp path
    """TLS is configured by a pair, never by one half of it."""
    certificate = tmp_path / "cert.pem"
    key = tmp_path / "key.pem"
    certificate.write_bytes(b"cert")
    key.write_bytes(b"key")
    with pytest.raises(ValueError, match=TLS_PAIR_ERROR):
        _settings(tls_cert_file=certificate)
    paired = _settings(tls_cert_file=certificate, tls_key_file=key)
    assert paired.tls == (certificate, key)
    assert _settings().tls is None


@pytest.mark.covers(rules=["MCP-15"])
def test__liveness_path_is_the_open_health_route() -> None:
    """The liveness path is the app's own, not FastMCP's internal one."""
    assert LIVENESS_PATH == "/liveness"
