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


@pytest.mark.covers(rules=["KSC-08", "KSC-10"])
def test_the_command_line_sets_the_flags_it_names(monkeypatch: pytest.MonkeyPatch) -> None:
    """The settings model is the CLI (DD-470): the flags it names, over the environment.

    --dry-run, repeatable --topic, and a flag for any key — a flag beats the environment's value.
    """
    monkeypatch.setenv(f"{ENV_PREFIX}CLIENT_SECRET", "from-the-environment")
    monkeypatch.setenv(f"{ENV_PREFIX}SYSTEM_NAME", "From Env")
    monkeypatch.setenv(f"{ENV_PREFIX}SASL_PASSWORD", "from-env")
    job = ScannerSettings(
        _cli_parse_args=[  # pyright: ignore[reportCallIssue] - the CLI source reads the argv it is handed
            "--dry-run",
            "--topic",
            "orders",
            "--topic",
            "events-*",
            "--system-name",
            "From Flags",
            "--security-protocol",
            "SASL_PLAINTEXT",
            "--sasl-mechanism",
            "SCRAM-SHA-512",
            "--sasl-username",
            "scanner",
        ]
    )
    assert job.dry_run is True
    assert job.topic == ["orders", "events-*"]
    assert job.system_name == "From Flags"  # the flag beats the environment
    assert job.security_protocol == "SASL_PLAINTEXT"
    assert job.sasl_mechanism == "SCRAM-SHA-512"
    assert job.sasl_username == "scanner"
    assert job.client_secret.get_secret_value() == "from-the-environment"  # the secret stays the environment's


@pytest.mark.covers(rules=["KSC-08"])
def test_a_flag_free_build_reads_the_environment_only(monkeypatch: pytest.MonkeyPatch) -> None:
    """Built without argv (as a test process is), the settings never parse the process's own arguments."""
    monkeypatch.setenv(f"{ENV_PREFIX}SYSTEM_NAME", "Quietly")
    job = ScannerSettings(client_secret="s")  # pyright: ignore[reportArgumentType] - pydantic coerces the str  # noqa: S106 - a test secret
    assert job.system_name == "Quietly"
    assert job.dry_run is False
    assert job.topic is None


@pytest.mark.covers(rules=["KSC-08", "KSC-10"])
def test_the_help_names_the_operators_knobs_and_never_a_secret(capsys: pytest.CaptureFixture[str]) -> None:
    """--help advertises the flags an operator turns; the secret fields are suppressed from it (DD-470)."""
    with pytest.raises(SystemExit):
        ScannerSettings(_cli_parse_args=["--help"])  # pyright: ignore[reportCallIssue] - argparse exits after printing
    help_text = capsys.readouterr().out
    assert "--dry-run" in help_text
    assert "--topic" in help_text
    assert "--sasl-username" in help_text
    assert "--client-secret" not in help_text
    assert "--sasl-password" not in help_text


@pytest.mark.covers(rules=["KSC-10"])
def test_a_sasl_protocol_names_a_mechanism(settings: Settings) -> None:
    """SASL_SSL without a mechanism, or a mechanism on a plain transport, is a configuration error (KSC-10)."""
    with pytest.raises(ValidationError, match=r"names no.*SASL_MECHANISM"):
        settings(security_protocol="SASL_SSL")
    with pytest.raises(ValidationError, match="rides a SASL_ SECURITY_PROTOCOL"):
        settings(sasl_mechanism="PLAIN")


@pytest.mark.covers(rules=["KSC-10"])
def test_the_password_mechanisms_carry_a_principal_and_secret(settings: Settings) -> None:
    """SCRAM without its credentials is refused; with them the ladder stands (KSC-10)."""
    with pytest.raises(ValidationError, match=r"needs.*SASL_USERNAME and _PASSWORD"):
        settings(security_protocol="SASL_PLAINTEXT", sasl_mechanism="SCRAM-SHA-256")
    job = settings(
        security_protocol="SASL_PLAINTEXT",
        sasl_mechanism="SCRAM-SHA-256",
        sasl_username="scanner",
        sasl_password="s3cret",  # noqa: S106 - a test secret
    )
    assert job.sasl_username == "scanner"


@pytest.mark.covers(rules=["KSC-10"])
def test_oauthbearer_carries_the_issuer_trio(settings: Settings) -> None:
    """The bearer mechanism needs the issuer trio; half of it is a configuration error (KSC-10)."""
    with pytest.raises(ValidationError, match=r"OAUTHBEARER needs.*SASL_OAUTH_TOKEN_URL"):
        settings(security_protocol="SASL_SSL", sasl_mechanism="OAUTHBEARER", sasl_oauth_client_id="scanner")
    job = settings(
        security_protocol="SASL_SSL",
        sasl_mechanism="OAUTHBEARER",
        sasl_oauth_token_url=MINT,
        sasl_oauth_client_id="scanner",
        sasl_oauth_client_secret="broker-secret",  # noqa: S106 - a test secret
    )
    assert str(job.sasl_oauth_token_url) == MINT
