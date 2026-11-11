"""The app's settings, read once at start from the environment (13.1, KSC-02, KSC-03, KSC-09, KSC-10)."""

from typing import Literal, Self

from pydantic import HttpUrl, SecretStr, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

ENV_PREFIX = "AURELIUS_ATLAS_KAFKA_SCANNER_"
"""Every setting is an environment variable with this prefix, so other projects' variables never set it."""

DEFAULT_CLIENT_ID = "aurelius-atlas-kafka-scanner"
"""The Keycloak client the job signs in as (KSC-09, DD-458's pattern): its own service identity."""

DEFAULT_SERVER_URL = "https://localhost:21000"
"""The dev Atlas server: what ``nx serve`` of the server publishes, where the scan runs in dev."""

DEFAULT_MINT_URL = "https://keycloak.localhost:8443/realms/master/protocol/openid-connect/token"
"""The dev issuer's token endpoint: the TLS :8443 listener every producer mints at (DD-113)."""

DEFAULT_BOOTSTRAP_SERVERS = "localhost:29092"
"""The dev broker: the PLAINTEXT listener ``dev/kafka`` publishes, loopback-pinned (DD-469)."""

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


class ScannerSettings(BaseSettings):
    """Where the broker and its Registry are, who the job signs in as, what it scans, and what bounds it."""

    model_config = SettingsConfigDict(env_prefix=ENV_PREFIX, frozen=True, extra="ignore")

    log_level: LogLevel = "info"
    """The lowest level of log record the job emits."""

    server_url: HttpUrl = DEFAULT_SERVER_URL  # pyright: ignore[reportAssignmentType] - pydantic validates the URL text
    """The Atlas metadata API the job writes the tree to (KSC-09)."""

    token_url: HttpUrl = DEFAULT_MINT_URL  # pyright: ignore[reportAssignmentType] - pydantic validates the URL text
    """The issuer's token endpoint the job's client credentials are sent to (KSC-09)."""

    client_id: str = DEFAULT_CLIENT_ID
    """The confidential client the job signs in as (KSC-09, DD-458's pattern)."""

    client_secret: SecretStr
    """The secret of ``client_id``; there is no default — a scan without an identity does not run."""

    ca_file: str | None = None
    """PEM CA verifying the server's, the issuer's, the broker's and the Registry's TLS; unset uses
    the system trust store (KSC-10)."""

    bootstrap_servers: str = DEFAULT_BOOTSTRAP_SERVERS
    """The broker's bootstrap list, comma-separated as Kafka writes it (KSC-10). The door fails the
    run naming this list when none of it answers (KSC-02)."""

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

    otel_client_secret: SecretStr | None = None
    """The secret of ``otel_client_id``."""

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
