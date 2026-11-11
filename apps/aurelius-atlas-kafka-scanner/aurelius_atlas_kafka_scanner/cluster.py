"""The broker door: the topic list, the cluster id, and a topic's newest records (13.1, KSC-01, KSC-02, KSC-05, KSC-10).

The door speaks any of the four security protocols to the bootstrap list (KSC-10) — PLAINTEXT,
SSL, and SASL over either, with ``PLAIN``, ``SCRAM-SHA-256/512``, or ``OAUTHBEARER`` — and answers
three questions: which external topics the broker holds (KSC-02), what the broker calls its
cluster (KSC-03), and what the newest record of one topic looks like (KSC-05). A broker that
answers no metadata inside the timeout fails the run with its bootstrap list in the message
(KSC-01, KSC-02): the legacy job hung in exactly this spot, and its README carried an apology.

The sniff reads through ``assign`` at the log end with no consumer group (DD-468): a metadata
scan must not leave a group and committed offsets on the broker as a side effect.
"""

import re
from dataclasses import dataclass
from typing import TYPE_CHECKING, NotRequired, Protocol, TypedDict

from kafka.admin import KafkaAdminClient
from kafka.consumer import KafkaConsumer
from kafka.errors import KafkaError
from kafka.net.sasl.oauth import AbstractTokenProvider
from kafka.structs import TopicPartition

if TYPE_CHECKING:
    from aurelius_atlas_otel import ClientCredentialsTokenSource

    from aurelius_atlas_kafka_scanner.settings import SaslMechanism, SecurityProtocol

INTERNAL_PREFIX = "_"
"""The internal-topic convention every Kafka bookkeeping name shares (KSC-02)."""

INTERNAL_SUFFIXES: tuple[str, ...] = ("-offsets", "-status", "-configs")
"""The bookkeeping endings Connect and MirrorMaker give their state topics (KSC-02, DD-467):
``connect-configs``, ``connect-offsets``, ``mm2-offsets.*`` (the last matched as a prefix-style
ending fails it — see :func:`is_internal`, which keeps the legacy rule honest)."""

WILDCARD = "*"
"""The one wildcard a topic pattern holds (KSC-02)."""


class BrokerUnreachableError(RuntimeError):
    """The broker door's run-level failure (KSC-01, KSC-02): no bootstrap server answered metadata."""


@dataclass(frozen=True)
class Sniffed:
    """One record a topic's sniff answered: its key and value bytes (KSC-05)."""

    key: bytes | None
    value: bytes


class ClusterDoor(Protocol):
    """What the scan asks the broker: the topics, the cluster's name, one record's shape (KSC-02..05)."""

    def external_topics(self) -> list[str]:
        """The broker's external topic names, sorted (KSC-02)."""
        ...

    def cluster_id(self) -> str | None:
        """The broker's cluster id, or ``None`` when it answers none (KSC-03)."""
        ...

    def newest_record(self, topic: str) -> Sniffed | None:
        """The topic's newest record within the sniff bound, or ``None`` when it answers none (KSC-05)."""
        ...

    def close(self) -> None:
        """Release the broker's connections."""
        ...


def is_internal(name: str) -> bool:
    """Whether a topic is bookkeeping rather than data (KSC-02, DD-467).

    A name starting ``_`` is the broker's own (``__consumer_offsets``); a name ending in one of
    :data:`INTERNAL_SUFFIXES` is a connector's or a converter's state. The legacy filter joined
    the two tests with ``or`` in a way that let every non-underscore name through; this one
    refuses both families, whichever test catches the name.
    """
    if name.startswith(INTERNAL_PREFIX):
        return True
    return any(name.endswith(suffix) for suffix in INTERNAL_SUFFIXES)


def compile_patterns(topics: str) -> list[re.Pattern[str]]:
    """The topic patterns of the settings, compiled for a case-insensitive full match (KSC-02).

    Each comma-separated pattern may hold ``*``, which stands for any run of characters; the rest
    of a pattern is literal text. An empty pattern between commas is dropped.
    """
    compiled: list[re.Pattern[str]] = []
    for raw in topics.split(","):
        pattern = raw.strip()
        if not pattern:
            continue
        body = "".join(".*" if part == WILDCARD else re.escape(part) for part in re.split(r"(\*)", pattern))
        compiled.append(re.compile(f"^{body}$", re.IGNORECASE))
    return compiled


def matches_any(name: str, patterns: list[re.Pattern[str]]) -> bool:
    """Whether a topic name matches any of ``patterns`` (KSC-02). An empty list matches nothing."""
    return any(pattern.match(name) for pattern in patterns)


class ClientConfig(TypedDict):
    """The client config the doors pass to ``kafka-python``, typed as the library's own keys."""

    bootstrap_servers: str
    request_timeout_ms: int
    security_protocol: NotRequired[SecurityProtocol]
    ssl_cafile: NotRequired[str]
    ssl_check_hostname: NotRequired[bool]
    sasl_mechanism: NotRequired[SaslMechanism]
    sasl_plain_username: NotRequired[str]
    sasl_plain_password: NotRequired[str]
    sasl_oauth_token_provider: NotRequired[AbstractTokenProvider]


class BrokerAuthError(RuntimeError):
    """The broker door's auth failure (KSC-10): the issuer refused the token the broker needs."""


class OAuthTokenProvider(AbstractTokenProvider):
    """The OAUTHBEARER provider over the app's client-credentials mint (KSC-10, DD-469).

    ``kafka-python`` asks for a token when a connection authenticates and again as the token
    ages out; each ask reads the cached bearer of the shared
    :class:`~aurelius_atlas_otel.ClientCredentialsTokenSource`, which refreshes ahead of expiry.
    A refused mint raises: the scan does not speak anonymously to the broker either (KSC-01).
    """

    def __init__(self, source: ClientCredentialsTokenSource) -> None:
        """Wrap the mint whose bearer the broker accepts."""
        super().__init__()
        self._source = source

    def token(self) -> str:  # pyright: ignore[reportIncompatibleMethodOverride] - the library's ABC is untyped; its docstring promises a str
        """A current bearer, or the run-level refusal (KSC-01, KSC-10).

        The provider always answers a bearer or raises — it never lets the mechanism fall
        back to anonymous, which is why the return is a plain ``str`` where the base's
        untyped stub answers ``None``.
        """
        value = self._source.bearer()
        if value is None:
            msg = "the issuer refused the broker token: the scan will not speak anonymously to the broker"
            raise BrokerAuthError(msg)
        return value


def broker_config(  # noqa: PLR0913 - the transport and its credentials, one keyword each (KSC-10)
    bootstrap_servers: str,
    *,
    ca_file: str | None = None,
    request_timeout_ms: int = 10_000,
    security_protocol: SecurityProtocol = "PLAINTEXT",
    sasl_mechanism: SaslMechanism | None = None,
    sasl_username: str | None = None,
    sasl_password: str | None = None,
    oauth_source: ClientCredentialsTokenSource | None = None,
) -> ClientConfig:
    """The client config the admin and consumer doors share (KSC-10): the transport and its credentials.

    With ``ca_file`` set, the client verifies a TLS broker against that CA. A SASL mechanism
    rides the door's own seam (DD-469): ``PLAIN`` and the ``SCRAM-*`` mechanisms carry the
    username and its secret — the library spells SCRAM's credentials with its plain keys — and
    ``OAUTHBEARER`` carries the mint wrapped in the provider the library demands. The settings
    validator refuses every other combination before this runs (KSC-10). The timeout bounds
    the metadata read (KSC-02).
    """
    config: ClientConfig = {
        "bootstrap_servers": bootstrap_servers,
        "request_timeout_ms": request_timeout_ms,
        "security_protocol": security_protocol,
    }
    if ca_file is not None:
        config["ssl_cafile"] = ca_file
        config["ssl_check_hostname"] = True
    if sasl_mechanism == "OAUTHBEARER" and oauth_source is not None:
        config["sasl_mechanism"] = sasl_mechanism
        config["sasl_oauth_token_provider"] = OAuthTokenProvider(oauth_source)
    elif sasl_mechanism is not None and sasl_username is not None and sasl_password is not None:
        config["sasl_mechanism"] = sasl_mechanism
        config["sasl_plain_username"] = sasl_username
        config["sasl_plain_password"] = sasl_password
    return config


class KafkaCluster:
    """The broker door over ``kafka-python`` (DD-465): an admin client and a group-less consumer.

    Args:
        bootstrap_servers: The broker's bootstrap list (KSC-10).
        ca_file: The PEM CA a TLS broker's certificate is verified against (KSC-10).
        admin_request_timeout_ms: How long metadata waits before the run fails (KSC-02).
        poll_timeout_seconds: How long one topic's sniff poll waits (KSC-05).
        sniff_messages: The newest records one sniff reads at most (KSC-05).
        security_protocol: The transport the broker's listener answers (KSC-10).
        sasl_mechanism: The SASL mechanism the listener names, with its credentials (KSC-10).
        sasl_username: The SASL principal for ``PLAIN`` and ``SCRAM-*``.
        sasl_password: The secret of ``sasl_username``.
        oauth_source: The mint whose bearer ``OAUTHBEARER`` rides.
    """

    def __init__(  # noqa: PLR0913 - the door's bounds and its auth, one keyword each (KSC-10)
        self,
        bootstrap_servers: str,
        *,
        ca_file: str | None = None,
        admin_request_timeout_ms: int = 10_000,
        poll_timeout_seconds: float = 5.0,
        sniff_messages: int = 100,
        security_protocol: SecurityProtocol = "PLAINTEXT",
        sasl_mechanism: SaslMechanism | None = None,
        sasl_username: str | None = None,
        sasl_password: str | None = None,
        oauth_source: ClientCredentialsTokenSource | None = None,
    ) -> None:
        self._bootstrap_servers = bootstrap_servers
        self._ca_file = ca_file
        self._timeout_ms = admin_request_timeout_ms
        self._poll_timeout = poll_timeout_seconds
        self._sniff_messages = sniff_messages
        self._security_protocol: SecurityProtocol = security_protocol
        self._sasl_mechanism: SaslMechanism | None = sasl_mechanism
        self._sasl_username = sasl_username
        self._sasl_password = sasl_password
        self._oauth_source = oauth_source
        self._admin: KafkaAdminClient | None = None
        self._consumer: KafkaConsumer | None = None

    def external_topics(self) -> list[str]:
        """The broker's external topics (KSC-02): every name the metadata answers that :func:`is_internal` refuses not.

        Raises:
            BrokerUnreachableError: the broker answered no metadata within the timeout (KSC-01, KSC-02).
        """
        names = (str(described["name"]) for described in self._describe())
        return sorted(name for name in names if not is_internal(name))

    def cluster_id(self) -> str | None:
        """The broker's cluster id, or ``None`` for a broker that answers none (KSC-03)."""
        try:
            cluster = self._admin_client().describe_cluster()
        except KafkaError as cause:
            raise self._unreachable() from cause
        value = cluster.get("cluster_id")
        return str(value) if value else None

    def newest_record(self, topic: str) -> Sniffed | None:
        """The newest record of ``topic`` within the sniff bound (KSC-05), or ``None`` when none answers.

        The consumer assigns every partition, seeks to the last ``sniff_messages`` offsets of each,
        and takes the first record that answers. The newest record is the last one the poll holds,
        so the read is one pass and the seek keeps it small on a busy topic.
        """
        partitions = [TopicPartition(topic, partition) for partition in self._partitions(topic)]
        if not partitions:
            return None
        consumer = self._consumer_client()
        try:
            consumer.assign(partitions)
            ends = consumer.end_offsets(partitions)
            for partition, end in ends.items():
                consumer.seek(partition, max(0, end - self._sniff_messages))
            newest: Sniffed | None = None
            deadline_polls = max(1, int(self._poll_timeout / 0.5))
            for _ in range(deadline_polls):
                batch = consumer.poll(timeout_ms=500)
                for records in batch.values():
                    for record in records:
                        newest = Sniffed(record.key, record.value)
                if newest is not None:
                    return newest
            return newest
        finally:
            consumer.unsubscribe()

    def close(self) -> None:
        """Close the admin client and the consumer, each once, swallowing their close races."""
        if self._admin is not None:
            self._admin.close()
            self._admin = None
        if self._consumer is not None:
            self._consumer.close()
            self._consumer = None

    def _describe(self) -> list[dict[str, object]]:
        """One metadata request's per-topic answers, raising the run failure on any error (KSC-02).

        ``describe_topics`` answers a list of ``{"name": ..., "partitions": [...]}`` records, one
        per topic; the door hands them through as they came.
        """
        try:
            return list(self._admin_client().describe_topics())
        except KafkaError as cause:
            raise self._unreachable() from cause

    def _partitions(self, topic: str) -> list[int]:
        """The partition ids of ``topic``, from the metadata (KSC-05)."""
        for described in self._describe():
            if described.get("name") == topic:
                partitions = described.get("partitions") or []
                if isinstance(partitions, list):
                    return [int(str(partition["partition_index"])) for partition in partitions]
        return []

    def _admin_client(self) -> KafkaAdminClient:
        """The admin client, built once on the shared config."""
        if self._admin is None:
            self._admin = KafkaAdminClient(**self._config())
        return self._admin

    def _consumer_client(self) -> KafkaConsumer:
        """The group-less sniff consumer, built once on the shared config (DD-468)."""
        if self._consumer is None:
            self._consumer = KafkaConsumer(
                **self._config(),
                enable_auto_commit=False,
                auto_offset_reset="latest",
            )
        return self._consumer

    def _config(self) -> ClientConfig:
        """The client config from the door's own settings (KSC-10)."""
        return broker_config(
            self._bootstrap_servers,
            ca_file=self._ca_file,
            request_timeout_ms=self._timeout_ms,
            security_protocol=self._security_protocol,
            sasl_mechanism=self._sasl_mechanism,
            sasl_username=self._sasl_username,
            sasl_password=self._sasl_password,
            oauth_source=self._oauth_source,
        )

    def _unreachable(self) -> BrokerUnreachableError:
        """The door's one failure message: it names the bootstrap list (KSC-02)."""
        return BrokerUnreachableError(
            f"the broker answered no metadata within {self._timeout_ms} ms: {self._bootstrap_servers}",
        )
