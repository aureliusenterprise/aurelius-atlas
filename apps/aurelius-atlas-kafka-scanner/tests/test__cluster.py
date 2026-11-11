"""The broker door: the internal filter, the patterns, the config, and the dead-broker failure (KSC-01, KSC-02, KSC-10).

The door's socket side is proved against the real broker in ``e2e/``; here the rules that are
pure functions get their own pairs, and the failure path runs against a fake admin client that
raises what ``kafka-python-ng`` raises when no bootstrap server answers.
"""

import re

import pytest
from aurelius_atlas_kafka_scanner.cluster import (
    BrokerUnreachableError,
    KafkaCluster,
    common_config,
    compile_patterns,
    is_internal,
    matches_any,
)
from kafka.errors import KafkaError

BOOTSTRAP = "broker-a:9092,broker-b:9092"
SILENT = "no broker answered the metadata request"


@pytest.mark.covers("aurelius_atlas_kafka_scanner.cluster.is_internal", rules=["KSC-02"])
@pytest.mark.parametrize(
    ("name", "internal"),
    [
        ("__consumer_offsets", True),
        ("_schemas", True),
        ("connect-configs", True),
        ("connect-offsets", True),
        ("connect-status", True),
        ("orders", False),
        ("order-events", False),
        ("internal-notes", False),
        ("my-collections", False),
    ],
)
def test_the_internal_filter_refuses_bookkeeping_only(name: str, internal: bool) -> None:  # noqa: FBT001 - the parametrized answer
    """Underscore-prefixed and state-suffixed names are bookkeeping; a data name never matches (KSC-02)."""
    assert is_internal(name) is internal


@pytest.mark.covers("aurelius_atlas_kafka_scanner.cluster.compile_patterns", rules=["KSC-02"])
def test_patterns_are_case_insensitive_full_matches() -> None:
    """A pattern matches a whole name, case-insensitively; ``*`` stands for any run (KSC-02)."""
    patterns = compile_patterns("orders, EVENTS-*")
    assert matches_any("Orders", patterns)
    assert matches_any("events-user-1", patterns)
    assert not matches_any("orders-archive", patterns)
    assert not matches_any("payments", patterns)


@pytest.mark.covers("aurelius_atlas_kafka_scanner.cluster.compile_patterns", rules=["KSC-02"])
def test_the_default_pattern_admits_everything_and_blanks_drop() -> None:
    """The default ``*`` admits every external name; an empty piece between commas is dropped (KSC-02)."""
    patterns = compile_patterns(" , * , ")
    assert len(patterns) == 1
    assert matches_any("anything-at-all", patterns)
    assert not matches_any("anything", [])  # no patterns admit nothing


@pytest.mark.covers("aurelius_atlas_kafka_scanner.cluster.matches_any", rules=["KSC-02"])
def test_a_wildcard_pattern_escapes_regex_text() -> None:
    """A dot in a pattern is literal text, not a regex wildcard (KSC-02)."""
    patterns = compile_patterns("orders.v2")
    assert matches_any("orders.v2", patterns)
    assert not matches_any("ordersXv2", patterns)


@pytest.mark.covers("aurelius_atlas_kafka_scanner.cluster.common_config", rules=["KSC-10"])
def test_the_ca_setting_reaches_the_client_config() -> None:
    """With CA_FILE set, the config verifies a TLS broker's hostname against it (KSC-10)."""
    plain = common_config(BOOTSTRAP, None, 10_000)
    assert "ssl_cafile" not in plain
    assert plain == {"bootstrap_servers": BOOTSTRAP, "request_timeout_ms": 10_000}
    secure = common_config(BOOTSTRAP, "/certs/ca.pem", 5_000)
    assert secure.get("ssl_cafile") == "/certs/ca.pem"
    assert secure.get("ssl_check_hostname") is True


class _RaisingAdmin:
    """An admin client whose every call fails the way a silent broker's does."""

    def describe_topics(self) -> list[dict[str, object]]:
        raise KafkaError(SILENT)

    def describe_cluster(self) -> dict[str, object]:
        raise KafkaError(SILENT)


@pytest.mark.covers("aurelius_atlas_kafka_scanner.cluster.KafkaCluster.external_topics", rules=["KSC-01", "KSC-02"])
def test_a_silent_broker_fails_the_run_naming_its_bootstrap_list(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """KSC-01/KSC-02: no metadata in the timeout is a run failure, and its message names the list.

    The legacy job hung in exactly this spot; the message is the apology it never printed.
    """
    monkeypatch.setattr(
        "aurelius_atlas_kafka_scanner.cluster.KafkaAdminClient",
        lambda **_config: _RaisingAdmin(),
    )
    door = KafkaCluster(BOOTSTRAP, admin_request_timeout_ms=1_000)
    with pytest.raises(BrokerUnreachableError, match=re.escape(BOOTSTRAP)):
        door.external_topics()
    with pytest.raises(BrokerUnreachableError, match="1000 ms"):
        door.cluster_id()


class _AnsweringAdmin:
    """An admin client over a small fake cluster: two data topics and one internal."""

    def describe_topics(self) -> list[dict[str, object]]:
        return [
            {"topic": "orders", "partitions": [{"partition": 0}, {"partition": 1}]},
            {"topic": "__consumer_offsets", "partitions": [{"partition": 0}]},
            {"topic": "payments", "partitions": [{"partition": 0}]},
        ]

    def describe_cluster(self) -> dict[str, object]:
        return {"cluster_id": "Ur6ciV-TSa2kMg", "controller": 1}


@pytest.mark.covers("aurelius_atlas_kafka_scanner.cluster.KafkaCluster.external_topics", rules=["KSC-02"])
def test_the_topic_list_is_external_and_sorted(monkeypatch: pytest.MonkeyPatch) -> None:
    """The door hands the scan the external names, sorted — the internal one never reaches it (KSC-02)."""
    monkeypatch.setattr(
        "aurelius_atlas_kafka_scanner.cluster.KafkaAdminClient",
        lambda **_config: _AnsweringAdmin(),
    )
    door = KafkaCluster(BOOTSTRAP)
    assert door.external_topics() == ["orders", "payments"]


@pytest.mark.covers("aurelius_atlas_kafka_scanner.cluster.KafkaCluster.cluster_id", rules=["KSC-03"])
def test_the_cluster_id_arrives_trimmed_or_none(monkeypatch: pytest.MonkeyPatch) -> None:
    """The broker's own name for itself, as KSC-03 hangs the Collection under it."""
    monkeypatch.setattr(
        "aurelius_atlas_kafka_scanner.cluster.KafkaAdminClient",
        lambda **_config: _AnsweringAdmin(),
    )
    door = KafkaCluster(BOOTSTRAP)
    assert door.cluster_id() == "Ur6ciV-TSa2kMg"


class _EmptyAdmin(_AnsweringAdmin):
    def describe_cluster(self) -> dict[str, object]:
        return {"cluster_id": None, "controller": 1}


@pytest.mark.covers("aurelius_atlas_kafka_scanner.cluster.KafkaCluster.cluster_id", rules=["KSC-03"])
def test_a_broker_answering_no_cluster_id_reads_as_none(monkeypatch: pytest.MonkeyPatch) -> None:
    """A broker that answers no id is the KSC-03 fallback case; the door answers None, not a guess."""
    monkeypatch.setattr(
        "aurelius_atlas_kafka_scanner.cluster.KafkaAdminClient",
        lambda **_config: _EmptyAdmin(),
    )
    door = KafkaCluster(BOOTSTRAP)
    assert door.cluster_id() is None
