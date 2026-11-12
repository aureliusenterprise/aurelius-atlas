"""The app's settings, read once at start from the environment and the command line (13.1, KSC-02, KSC-03, KSC-08..10).

One model carries every setting and the run's two flags (KSC-08): environment variables under
:data:`ENV_PREFIX` first, command-line arguments over them, both through pydantic-settings' CLI
source — there is no second argument parser to keep in step with the fields (DD-470). Secrets
are environment settings like the rest, and the CLI does not advertise a flag for them
(:data:`~pydantic_settings.CliSuppress`): ``--help`` names the knobs an operator is meant to
turn, and a secret is not one of them.
"""

from typing import Literal, Self

from pydantic import Field, HttpUrl, SecretStr, field_validator, model_validator
from pydantic_settings import (
    BaseSettings,
    CliSettingsSource,
    CliSuppress,
    CliToggleFlag,
    PydanticBaseSettingsSource,
    SettingsConfigDict,
)

ENV_PREFIX = "AURELIUS_ATLAS_KAFKA_SCANNER_"
"""Every setting is an environment variable with this prefix, so other projects' variables never set it."""

DEFAULT_CLIENT_ID = "aurelius-atlas-kafka-scanner"
"""The Keycloak client the job signs in as (KSC-09, DD-458's pattern): its own service identity."""

DEFAULT_SERVER_URL = "https://localhost:21000"
"""The dev Atlas server: what ``nx serve`` of the server publishes, where the scan runs in dev."""

DEFAULT_MINT_URL = "https://keycloak.localhost:8443/realms/master/protocol/openid-connect/token"
"""The dev issuer's token endpoint: the TLS :8443 listener every producer mints at (DD-113)."""

DEFAULT_BOOTSTRAP_SERVERS = "localhost:29092"
"""The broker of the e2e stack: its PLAINTEXT host listener, published loopback-pinned on this
port (DD-469's port, moved into the app's own stack by DD-533). A deployment names its own
cluster with ``BOOTSTRAP_SERVERS``."""

DEFAULT_SYSTEM_NAME = "Kafka Broker"
"""The System the tree hangs under, when the operator names none (KSC-03)."""

DEFAULT_TOPIC_PATTERN = "*"
"""The topic filter that admits every external topic (KSC-02)."""

DEFAULT_SNIFF_MESSAGES = 100
"""The newest records one topic's sniff reads at most (KSC-05): the field shape of a schemaless topic."""

DEFAULT_POLL_TIMEOUT_SECONDS = 5.0
"""How long one poll of one topic waits (KSC-05). The legacy job polled five seconds per topic;
this job seeks to the log end first, so the timeout bounds a quiet topic's read, not a busy one's."""

DEFAULT_ADMIN_REQUEST_TIMEOUT_MS = 10_000
"""How long the broker door waits for metadata before the run fails (KSC-01, KSC-02): the legacy
job waited forever, and its README called that a hang."""

DEFAULT_REGISTRY_TIMEOUT_SECONDS = 10.0
"""How long one Schema Registry request waits (KSC-04, KSC-05)."""

type LogLevel = Literal["trace", "debug", "info", "warning", "error"]
"""Levels the app's logging accepts."""

type SecurityProtocol = Literal["PLAINTEXT", "SSL", "SASL_PLAINTEXT", "SASL_SSL"]
"""The four transports the broker door speaks (KSC-10), spelled as Kafka spells them."""

type SaslMechanism = Literal["PLAIN", "SCRAM-SHA-256", "SCRAM-SHA-512", "OAUTHBEARER"]
"""The SASL mechanisms the door carries (KSC-10). ``GSSAPI`` is deliberately out: it needs a
Kerberos client the image does not ship, and no Aurelius deployment asks for it (DD-469)."""


class ScannerSettings(BaseSettings):
    """Where the broker and its Registry are, how the job authenticates, what it scans, and what bounds it."""

    model_config = SettingsConfigDict(
        env_prefix=ENV_PREFIX,
        frozen=True,
        extra="ignore",
        cli_prog_name="aurelius-atlas-kafka-scanner",
        cli_kebab_case=True,
        cli_hide_none_type=True,
        cli_avoid_json=True,
        cli_exit_on_error=False,
    )

    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls: type[BaseSettings],
        init_settings: PydanticBaseSettingsSource,
        env_settings: PydanticBaseSettingsSource,
        dotenv_settings: PydanticBaseSettingsSource,
        file_secret_settings: PydanticBaseSettingsSource,
    ) -> tuple[PydanticBaseSettingsSource, ...]:
        """Command line over environment over dotenv (DD-470): an explicit flag beats ambient config.

        The CLI source parses only what the caller hands it (``_cli_parse_args``): built without
        that, the settings read environment alone, so a test process never parses its own
        pytest arguments as scanner flags.
        """
        return (
            CliSettingsSource(settings_cls),
            init_settings,
            env_settings,
            dotenv_settings,
            file_secret_settings,
        )

    log_level: LogLevel = "info"
    """The lowest level of log record the job emits."""

    server_url: HttpUrl = DEFAULT_SERVER_URL  # pyright: ignore[reportAssignmentType] - pydantic validates the URL text
    """The Atlas metadata API the job writes the tree to (KSC-09)."""

    token_url: HttpUrl = DEFAULT_MINT_URL  # pyright: ignore[reportAssignmentType] - pydantic validates the URL text
    """The issuer's token endpoint the job's client credentials are sent to (KSC-09)."""

    client_id: str = DEFAULT_CLIENT_ID
    """The confidential client the job signs in as (KSC-09, DD-458's pattern)."""

    client_secret: CliSuppress[SecretStr]
    """The secret of ``client_id``; there is no default — a scan without an identity does not run.
    Suppressed from ``--help`` (DD-470): the documented interface stays the knobs, not the secrets."""

    dry_run: CliToggleFlag[bool] = Field(default=False, description="read everything and print the tree, write nothing")
    """``--dry-run`` / ``--no-dry-run`` (KSC-08): the whole read, no write."""

    topic: list[str] | None = Field(
        default=None, description="limit the scan to topics matching this pattern (repeatable)"
    )
    """``--topic`` repeated (KSC-08): the patterns that limit this run, matched like
    :attr:`topics` (KSC-02). Unset scans what :attr:`topics` admits."""

    ca_file: str | None = None
    """PEM CA verifying the server's, the issuer's, the broker's and the Registry's TLS; unset uses
    the system trust store (KSC-10)."""

    bootstrap_servers: str = DEFAULT_BOOTSTRAP_SERVERS
    """The broker's bootstrap list, comma-separated as Kafka writes it (KSC-10). The door fails the
    run naming this list when none of it answers (KSC-02)."""

    security_protocol: SecurityProtocol = "PLAINTEXT"
    """How the broker doors reach the bootstrap list (KSC-10): plain, TLS, or SASL over either.
    The stack's broker answers PLAINTEXT and SASL_PLAINTEXT; a customer cluster typically answers
    SASL_SSL with OAUTHBEARER (DD-469)."""

    sasl_mechanism: SaslMechanism | None = None
    """The SASL mechanism the broker's listener names (KSC-10); required with a SASL protocol,
    refused without one."""

    sasl_username: str | None = None
    """The SASL principal for ``PLAIN`` and the ``SCRAM-*`` mechanisms (KSC-10)."""

    sasl_password: CliSuppress[SecretStr | None] = None
    """The secret of ``sasl_username`` — suppressed from ``--help``, like the catalogue secret."""

    sasl_oauth_token_url: HttpUrl | None = None
    """The issuer the broker accepts tokens from; the head of the OAUTHBEARER trio (KSC-10)."""

    sasl_oauth_client_id: str | None = None
    """The client the job mints the broker token as, with ``sasl_oauth_token_url``."""

    sasl_oauth_client_secret: CliSuppress[SecretStr | None] = None
    """The secret of ``sasl_oauth_client_id`` — suppressed from ``--help``."""

    schema_registry_url: HttpUrl | None = None
    """The Schema Registry to ask for a topic's subject; unset means every topic is sniffed (KSC-04)."""

    system_name: str = DEFAULT_SYSTEM_NAME
    """The System entity's name: the catalogue's label for this cluster (KSC-03)."""

    topics: str = DEFAULT_TOPIC_PATTERN
    """A comma-separated list of topic-name patterns; ``*`` matches any run of characters and a
    name matching any pattern is scanned, case-insensitive (KSC-02)."""

    sniff_messages: int = DEFAULT_SNIFF_MESSAGES
    """The newest records one schemaless topic's sniff reads at most (KSC-05)."""

    poll_timeout_seconds: float = DEFAULT_POLL_TIMEOUT_SECONDS
    """How long one topic's sniff poll waits for a record (KSC-05)."""

    admin_request_timeout_ms: int = DEFAULT_ADMIN_REQUEST_TIMEOUT_MS
    """The broker door's metadata timeout (KSC-01, KSC-02)."""

    registry_timeout_seconds: float = DEFAULT_REGISTRY_TIMEOUT_SECONDS
    """The Registry door's request timeout (KSC-04, KSC-05)."""

    otel_token_url: HttpUrl | None = None
    """The issuer for the OTLP ingest token; unset with ``otel_endpoint`` keeps telemetry off."""

    otel_client_id: str | None = None
    """The OTLP ingest client id, with ``otel_token_url``."""

    otel_client_secret: CliSuppress[SecretStr | None] = None
    """The secret of ``otel_client_id`` — suppressed from ``--help``."""

    otel_endpoint: str | None = None
    """The OTLP endpoint telemetry is exported to; unset keeps telemetry off."""

    @field_validator("topics")
    @classmethod
    def _check_topics(cls, value: str) -> str:
        """The topic patterns must not be empty: an empty list would silently admit nothing (KSC-02)."""
        if not any(pattern.strip() for pattern in value.split(",")):
            msg = f"{ENV_PREFIX}TOPICS names no pattern: use '*' to admit every external topic"
            raise ValueError(msg)
        return value

    @model_validator(mode="after")
    def _check_telemetry_trio(self) -> Self:
        """The OTLP trio stands or falls together, as in the quality scanner (DD-196)."""
        trio = (self.otel_token_url, self.otel_client_id, self.otel_endpoint)
        if any(trio) and not all(trio):
            msg = f"{ENV_PREFIX}OTEL_ENDPOINT, _TOKEN_URL and _CLIENT_ID stand together"
            raise ValueError(msg)
        return self

    @model_validator(mode="after")
    def _check_broker_auth(self) -> Self:
        """The broker's auth settings stand as one ladder (KSC-10, DD-469).

        A SASL protocol names a mechanism; a mechanism rides a SASL protocol. ``PLAIN`` and the
        ``SCRAM-*`` mechanisms carry a username and its secret; ``OAUTHBEARER`` carries the
        issuer trio the job mints the broker token with. Plain or TLS brokers carry neither.
        """
        sasl = self.security_protocol.startswith("SASL_")
        if sasl and self.sasl_mechanism is None:
            msg = f"{ENV_PREFIX}SECURITY_PROTOCOL={self.security_protocol} names no {ENV_PREFIX}SASL_MECHANISM"
            raise ValueError(msg)
        if not sasl and self.sasl_mechanism is not None:
            msg = f"{ENV_PREFIX}SASL_MECHANISM rides a SASL_ SECURITY_PROTOCOL, not {self.security_protocol}"
            raise ValueError(msg)
        needs_creds = self.sasl_username is None or self.sasl_password is None
        if self.sasl_mechanism in ("PLAIN", "SCRAM-SHA-256", "SCRAM-SHA-512") and needs_creds:
            msg = f"{ENV_PREFIX}SASL_MECHANISM={self.sasl_mechanism} needs {ENV_PREFIX}SASL_USERNAME and _PASSWORD"
            raise ValueError(msg)
        if self.sasl_mechanism == "OAUTHBEARER":
            trio = (self.sasl_oauth_token_url, self.sasl_oauth_client_id, self.sasl_oauth_client_secret)
            if not all(trio):
                msg = (
                    f"{ENV_PREFIX}SASL_MECHANISM=OAUTHBEARER needs {ENV_PREFIX}SASL_OAUTH_TOKEN_URL,"
                    f" _CLIENT_ID and _CLIENT_SECRET"
                )
                raise ValueError(msg)
        return self
