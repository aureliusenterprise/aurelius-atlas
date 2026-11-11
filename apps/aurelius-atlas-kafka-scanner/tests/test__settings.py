"""The settings: prefix, defaults, and the two validators (KSC-02, KSC-03, KSC-09, KSC-10)."""

from collections.abc import Callable

import pytest
from aurelius_atlas_kafka_scanner.settings import (
    DEFAULT_BOOTSTRAP_SERVERS,
    DEFAULT_SYSTEM_NAME,
    DEFAULT_TOPIC_PATTERN,
    ENV_PREFIX,
    ScannerSettings,
)
from pydantic import ValidationError

MINT = "https://keycloak.localhost:8443/realms/master/protocol/openid-connect/token"

Settings = Callable[..., ScannerSettings]
"""The settings fixture's type: the builder the conftest hands every test."""


@pytest.mark.covers(rules=["KSC-03", "KSC-09", "KSC-10"])
def test_defaults_are_the_dev_stack(settings: Settings) -> None:
    """The unset job aims at the dev server, issuer, and broker, and scans every external topic."""
    job = settings()
    assert str(job.server_url).startswith("https://localhost:21000")
    assert str(job.token_url) == MINT
    assert job.client_id == "aurelius-atlas-kafka-scanner"
    assert job.bootstrap_servers == DEFAULT_BOOTSTRAP_SERVERS
    assert job.system_name == DEFAULT_SYSTEM_NAME
    assert job.topics == DEFAULT_TOPIC_PATTERN
    assert job.schema_registry_url is None
    assert job.sniff_messages == 100


@pytest.mark.covers(rules=["KSC-02", "KSC-03"])
def test_environment_sets_the_prefixed_names(monkeypatch: pytest.MonkeyPatch, settings: Settings) -> None:
    """The settings read the project's own prefix — other projects' variables never set them."""
    monkeypatch.setenv(f"{ENV_PREFIX}SYSTEM_NAME", "Ops Cluster")
    monkeypatch.setenv(f"{ENV_PREFIX}TOPICS", "orders, events-*")
    monkeypatch.setenv(f"{ENV_PREFIX}BOOTSTRAP_SERVERS", "kafka:9093")
    job = settings()
    assert job.system_name == "Ops Cluster"
    assert job.topics == "orders, events-*"
    assert job.bootstrap_servers == "kafka:9093"


@pytest.mark.covers(rules=["KSC-09"])
def test_a_secretless_job_does_not_configure() -> None:
    """There is no default secret: a scan without an identity has no settings (KSC-09)."""
    with pytest.raises(ValidationError, match="client_secret"):
        ScannerSettings()  # pyright: ignore[reportCallIssue] - the point is the missing field


@pytest.mark.covers(rules=["KSC-02"])
def test_empty_topic_patterns_are_refused(settings: Settings) -> None:
    """A TOPICS of nothing but commas would silently admit nothing — refused, not defaulted."""
    with pytest.raises(ValidationError, match="names no pattern"):
        settings(topics=",  ,")


@pytest.mark.covers(rules=["KSC-10"])
def test_the_telemetry_trio_stands_together(monkeypatch: pytest.MonkeyPatch, settings: Settings) -> None:
    """Half an OTLP trio is a configuration error, the quality scanner's rule (DD-196)."""
    with pytest.raises(ValidationError, match="stand together"):
        settings(otel_endpoint="https://otel:4318")
    monkeypatch.setenv(f"{ENV_PREFIX}OTEL_TOKEN_URL", MINT)
    monkeypatch.setenv(f"{ENV_PREFIX}OTEL_CLIENT_ID", "otel-ingest-client")
    job = settings(otel_endpoint="https://otel:4318")
    assert job.otel_client_id == "otel-ingest-client"
    assert str(job.otel_token_url) == MINT
