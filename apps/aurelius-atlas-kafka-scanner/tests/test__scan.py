"""The scan: the walk of the doors, the notices, the one write, the dry run (KSC-01, KSC-04..08).

The broker and Registry doors are fakes — every branch of the ladder (subject, sniff, inference,
field-less) is data here. The one bulk write is checked as a call count and a payload shape; its
server-side idempotency belongs to ``e2e/``.
"""

from collections.abc import Callable

import pytest
from aurelius_atlas_kafka_scanner.cluster import BrokerUnreachableError, Sniffed
from aurelius_atlas_kafka_scanner.registry import SubjectSchema
from aurelius_atlas_kafka_scanner.scan import dry_run_lines, run_scan, scan_line
from aurelius_atlas_kafka_scanner.settings import ScannerSettings
from aurelius_atlas_model.instance import AtlasEntitiesWithExtInfo, EntityMutationResponse

AVRO_ORDER = '{"type": "record", "name": "Order", "fields": [{"name": "id", "type": "string"}]}'
DEAD_BROKER = "the broker answered no metadata: localhost:29092"

Settings = Callable[..., ScannerSettings]
"""The settings fixture's type: the builder the conftest hands every test."""


class FakeCluster:
    """A broker door over a name-to-record map; the internal filter and sorting are the door's own job."""

    def __init__(
        self,
        topics: list[str],
        records: dict[str, Sniffed | None] | None = None,
        *,
        cluster_id: str | None = "abc123",
    ) -> None:
        self._topics = topics
        self._records = records or {}
        self._cluster_id = cluster_id

    def external_topics(self) -> list[str]:
        """The given names, sorted — what the real door's KSC-02 filter hands the scan."""
        return sorted(self._topics)

    def cluster_id(self) -> str | None:
        """The given id (KSC-03)."""
        return self._cluster_id

    def newest_record(self, topic: str) -> Sniffed | None:
        """The topic's prepared record, or ``None`` (KSC-05)."""
        return self._records.get(topic)

    def close(self) -> None:
        """Nothing to release."""
        return


class DeadBroker(FakeCluster):
    """A door over a broker that answers no metadata (KSC-01)."""

    def __init__(self) -> None:
        super().__init__([])

    def external_topics(self) -> list[str]:
        """The run-level failure, naming the bootstrap list as KSC-02 requires."""
        raise BrokerUnreachableError(DEAD_BROKER)


class FakeRegistry:
    """A Registry door over a subject map and an id map; anything else answers ``None`` (KSC-04)."""

    def __init__(
        self,
        subjects: dict[str, SubjectSchema] | None = None,
        ids: dict[int, SubjectSchema] | None = None,
    ) -> None:
        self._subjects = subjects or {}
        self._ids = ids or {}

    async def latest(self, subject: str) -> SubjectSchema | None:
        """The prepared subject, or ``None`` for "no such subject" (KSC-04)."""
        return self._subjects.get(subject)

    async def by_id(self, schema_id: int) -> SubjectSchema | None:
        """The prepared id, or ``None`` (KSC-05)."""
        return self._ids.get(schema_id)


class FakeCatalogue:
    """The catalogue door: counts the bulk writes and keeps what came through."""

    def __init__(self) -> None:
        self.calls: list[AtlasEntitiesWithExtInfo] = []

    async def create_or_update_bulk(self, entities: AtlasEntitiesWithExtInfo) -> EntityMutationResponse:
        """One bulk write: kept for the assertions, answered empty (KSC-07)."""
        self.calls.append(entities)
        return EntityMutationResponse()


def _avro_subject() -> SubjectSchema:
    return SubjectSchema(schema_type="AVRO", schema_str=AVRO_ORDER)


@pytest.mark.covers("aurelius_atlas_kafka_scanner.scan.run_scan", rules=["KSC-01", "KSC-04", "KSC-07"])
async def test_a_scan_reads_the_subject_and_writes_the_tree_once(settings: Settings) -> None:
    """A registered subject is parsed and the whole tree leaves in one bulk request (KSC-04, KSC-07)."""
    cluster = FakeCluster(["orders"], cluster_id="abc123")
    registry = FakeRegistry({"orders-value": _avro_subject()})
    catalogue = FakeCatalogue()
    report = await run_scan(cluster, registry, catalogue, settings())
    assert len(catalogue.calls) == 1
    written = catalogue.calls[0].entities
    assert written is not None
    assert [e.type_name for e in written] == ["m4i_system", "m4i_collection", "m4i_dataset", "m4i_field"]
    assert report.topics_found == 1
    assert report.topics_written == 1
    assert report.topics_fieldless == 0
    assert report.notices == []


@pytest.mark.covers("aurelius_atlas_kafka_scanner.scan.run_scan", rules=["KSC-02"])
async def test_the_topic_patterns_admit_only_matching_names(settings: Settings) -> None:
    """The settings' patterns steer the scan; the broker's whole list is the door's (KSC-02)."""
    cluster = FakeCluster(["orders", "payments", "events-user"])
    registry = FakeRegistry({"orders-value": _avro_subject(), "events-user-value": _avro_subject()})
    report = await run_scan(cluster, registry, FakeCatalogue(), settings(topics="orders, events-*"))
    assert report.topics_found == 2
    names = sorted((e.attributes or {})["name"] for e in report.entities if e.type_name == "m4i_dataset")
    assert names == ["events-user", "orders"]


@pytest.mark.covers("aurelius_atlas_kafka_scanner.scan.run_scan", rules=["KSC-01", "KSC-02"])
async def test_a_silent_broker_raises_out_of_the_scan(settings: Settings) -> None:
    """A broker that answers no metadata is the run-level failure KSC-01 names, not a zero-topic scan."""
    with pytest.raises(BrokerUnreachableError):
        await run_scan(DeadBroker(), FakeRegistry(), FakeCatalogue(), settings())


@pytest.mark.covers("aurelius_atlas_kafka_scanner.scan.run_scan", rules=["KSC-04", "KSC-05"])
async def test_a_subject_of_an_unreadable_type_moves_the_topic_to_the_sniff(settings: Settings) -> None:
    """A PROTOBUF subject is not parsed (KSC-04); the newest record's wire id reaches the Registry again (KSC-05)."""
    registry = FakeRegistry(
        {"orders-value": SubjectSchema(schema_type="PROTOBUF", schema_str="syntax")},
        ids={7: _avro_subject()},
    )
    cluster = FakeCluster(["orders"], records={"orders": Sniffed(None, b"\x00\x00\x00\x00\x07rest")})
    report = await run_scan(cluster, registry, FakeCatalogue(), settings())
    field_types = {(e.attributes or {})["fieldType"] for e in report.entities if e.type_name == "m4i_field"}
    assert field_types == {"string"}
    assert report.topics_fieldless == 0


@pytest.mark.covers("aurelius_atlas_kafka_scanner.scan.run_scan", rules=["KSC-05"])
async def test_a_schemaless_topic_infers_its_fields_from_a_json_record(settings: Settings) -> None:
    """No subject, no magic byte, a JSON object: the inference names the fields (KSC-05)."""
    cluster = FakeCluster(["logs"], records={"logs": Sniffed(None, b'{"level": "warn", "count": 3}')})
    report = await run_scan(cluster, FakeRegistry(), FakeCatalogue(), settings())
    fields = {
        (e.attributes or {})["name"]: (e.attributes or {})["fieldType"]
        for e in report.entities
        if e.type_name == "m4i_field"
    }
    assert fields == {"level": "string", "count": "integer"}
    assert report.notices == []


@pytest.mark.covers("aurelius_atlas_kafka_scanner.scan.run_scan", rules=["KSC-01", "KSC-05"])
async def test_a_topic_nothing_can_read_lands_field_less_with_a_notice(settings: Settings) -> None:
    """The field-less case: a dataset still registers, the run still exits whole (KSC-01, KSC-05)."""
    cluster = FakeCluster(["mystery"], records={"mystery": None})
    catalogue = FakeCatalogue()
    report = await run_scan(cluster, FakeRegistry(), catalogue, settings())
    assert report.topics_written == 1
    assert report.topics_fieldless == 1
    assert len(report.notices) == 1
    assert "mystery" in report.notices[0]
    written = catalogue.calls[0].entities
    assert written is not None
    assert [e.type_name for e in written if e.type_name == "m4i_dataset"] == ["m4i_dataset"]


@pytest.mark.covers("aurelius_atlas_kafka_scanner.scan.run_scan", rules=["KSC-05"])
async def test_a_wire_record_naming_an_absent_schema_gets_the_named_notice(settings: Settings) -> None:
    """The magic byte names an id the Registry does not hold: field-less, and the notice names the id (KSC-05)."""
    cluster = FakeCluster(["orders"], records={"orders": Sniffed(None, b"\x00\x00\x00\x00\x2a")})
    report = await run_scan(cluster, FakeRegistry(), FakeCatalogue(), settings())
    assert report.topics_fieldless == 1
    assert "42" in report.notices[0]


@pytest.mark.covers("aurelius_atlas_kafka_scanner.scan.run_scan", rules=["KSC-08"])
async def test_the_topic_filter_limits_the_scan_and_a_missing_name_is_a_notice(settings: Settings) -> None:
    """--topic matches like TOPICS; a name the broker lacks is a notice, never a failure (KSC-08)."""
    cluster = FakeCluster(["orders", "payments"], cluster_id=None)
    registry = FakeRegistry({"orders-value": _avro_subject()})
    report = await run_scan(cluster, registry, FakeCatalogue(), settings(), topic_filter=["orders", "gone*"])
    assert report.topics_written == 1
    assert any("gone*" in notice for notice in report.notices)


@pytest.mark.covers("aurelius_atlas_kafka_scanner.scan.run_scan", rules=["KSC-08"])
async def test_a_dry_run_reads_everything_and_writes_nothing(settings: Settings) -> None:
    """The dry run's tree is the real tree, printed — the catalogue door never hears of it (KSC-08)."""
    cluster = FakeCluster(["orders"], records={"ghost": None}, cluster_id=None)
    registry = FakeRegistry({"orders-value": _avro_subject()})
    catalogue = FakeCatalogue()
    report = await run_scan(cluster, registry, catalogue, settings(), dry_run=True)
    assert catalogue.calls == []
    assert len(report.entities) == 4
    lines = dry_run_lines(report)
    assert lines[0] == "m4i_system kafka-broker"
    assert lines[2] == "m4i_dataset kafka-broker--defaultcluster--orders"


@pytest.mark.covers("aurelius_atlas_kafka_scanner.scan.scan_line", rules=["KSC-01", "KSC-08"])
async def test_the_closing_line_counts_the_run_in_one_sentence(settings: Settings) -> None:
    """The CLI's last line carries the counts: found, written, field-less, entities."""
    cluster = FakeCluster(["orders", "mystery"], records={"mystery": None})
    registry = FakeRegistry({"orders-value": _avro_subject()})
    report = await run_scan(cluster, registry, FakeCatalogue(), settings())
    line = scan_line(report, dry_run=False)
    assert line.startswith("registered 2 topics")
    assert "1 field-less" in line
