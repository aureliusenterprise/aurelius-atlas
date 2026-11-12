"""E2E: the scanner against a real broker, Registry, and server (KSC-07, KSC-09, KSC-10).

The suite drives the job in-process — the scanner is a batch CLI, not a service — on the
stack of ``e2e/docker-compose.yaml``: a real Atlas server on the dev store, and the suite's
own real broker and Schema Registry the scan reads (DD-541, KSC-10: the door walks a live
broker, no fakes). Every scan speaks as the scanner's own service client (KSC-09): the write
rides its client-credentials token and the audit names it, so this is the spec's end-to-end
proof that the identity answers read AND write in the real catalogue. Each scenario namespaces
its topics and System to one ``zz<run>`` word, scans with a ``zz<run>*`` pattern so a foreign
topic is never registered, deletes its topics and subjects at the end, and hard-deletes the
entities it wrote (DD-223); nothing here restarts the shared store.
"""

import asyncio
import json
import re
import time
from collections.abc import Awaitable, Callable
from typing import Any

import pytest
from aurelius_atlas_kafka_scanner.cluster import BrokerUnreachableError, KafkaCluster
from aurelius_atlas_kafka_scanner.graph import dataset_qualified_name, join_qualified, qualified_component
from aurelius_atlas_kafka_scanner.registry import SchemaRegistry
from aurelius_atlas_kafka_scanner.scan import ScanDoor, ScanReport, run_scan
from aurelius_atlas_kafka_scanner.settings import ScannerSettings
from aurelius_atlas_model.audit import EntityAuditActionV2
from aurelius_atlas_model.instance import AtlasEntitiesWithExtInfo, AtlasEntity, EntityMutationResponse
from aurelius_atlas_server_client import AtlasClient
from conftest import Seeded

ORDER_AVRO = json.dumps(
    {
        "type": "record",
        "name": "Order",
        "fields": [
            {"name": "id", "type": "string"},
            {
                "name": "address",
                "type": {
                    "type": "record",
                    "name": "Address",
                    "fields": [{"name": "city", "type": "string"}],
                },
            },
        ],
    }
)
"""An Avro value schema with a nested record: the subject read of KSC-04/KSC-06."""


def _wire_value(schema_id: int) -> bytes:
    """A record value in the Confluent wire format: magic byte, id, then payload bytes."""
    return b"\x00" + schema_id.to_bytes(4, "big") + b"not-avro-payload"


def _attributes(entity: AtlasEntity) -> dict[str, Any]:
    """The wire attributes of a read-back entity (the model's map is optional)."""
    return dict(entity.attributes or {})


class _RecordingDoor(ScanDoor):
    """The scanner's write door, with what it wrote handed to cleanup (DD-223's self-clean).

    The scan's one bulk write is the cleanup surface: the store's guid assignments name the
    real entities, and the cleanup fixture deletes them at the test's end — whatever the
    scenario asserts after the write.
    """

    def __init__(self, scanner: AtlasClient, cleanup: Seeded) -> None:
        self._scanner = scanner
        self._cleanup = cleanup

    async def create_or_update_bulk(self, entities: AtlasEntitiesWithExtInfo) -> EntityMutationResponse:
        """``POST /entity/bulk`` through the scanner's own client, remembering the guid map."""
        response = await self._scanner.entity.create_or_update_bulk(entities)
        self._cleanup.record(list(entities.entities or []), dict(response.guid_assignments or {}))
        return response


async def _found(writer: AtlasClient, type_name: str, qualified_name: str) -> AtlasEntity | None:
    """The stored entity by its unique qualified name, or None when nothing answers."""
    found = await writer.entity.entities_by_unique_attributes(type_name, [{"qualifiedName": qualified_name}])
    entities = found.entities or []
    return entities[0] if entities else None


async def _wait_for(writer: AtlasClient, type_name: str, qualified_name: str) -> AtlasEntity:
    """The stored entity, once the near-real-time search answers it (the webapp suite's race)."""
    deadline = time.monotonic() + 30
    while time.monotonic() < deadline:
        entity = await _found(writer, type_name, qualified_name)
        if entity is not None:
            return entity
        await asyncio.sleep(1)
    msg = f"the store never answered {type_name} {qualified_name}"
    raise TimeoutError(msg)


async def _scan(
    scanner: AtlasClient,
    settings: ScannerSettings,
    cleanup: Seeded,
    *,
    dry_run: bool = False,
) -> ScanReport:
    """One scan on the real doors: the broker, the Registry, and the scanner's catalogue client.

    The doors are the app's own classes — this is KSC-10's proof, so no fake stands between the
    job and the broker. Each door is closed on the way out, whatever the scan answered.
    """
    cluster = KafkaCluster(
        settings.bootstrap_servers,
        ca_file=settings.ca_file,
        admin_request_timeout_ms=settings.admin_request_timeout_ms,
        security_protocol=settings.security_protocol,
        sasl_mechanism=settings.sasl_mechanism,
        sasl_username=settings.sasl_username,
        sasl_password=settings.sasl_password.get_secret_value() if settings.sasl_password else None,
    )
    registry = SchemaRegistry(str(settings.schema_registry_url), ca_file=None)
    try:
        return await run_scan(
            cluster,
            registry,
            _RecordingDoor(scanner, cleanup),
            settings,
            dry_run=dry_run,
        )
    finally:
        await registry.close()
        cluster.close()


def _run_settings(scanner_settings: ScannerSettings, run: str) -> ScannerSettings:
    """The session settings for one run: its own System name and a pattern admitting only it."""
    return scanner_settings.model_copy(
        update={"system_name": f"zz{run} Broker", "topics": f"zz{run}*"},
    )


def _qualified(cluster_id: str | None, run: str, topic: str) -> str:
    """The dataset qualified name the scan must have written for one topic (KSC-03)."""
    system_qualified = qualified_component(f"zz{run} Broker")
    return dataset_qualified_name(system_qualified, cluster_id, topic)


def _collection_qualified(cluster_id: str | None, run: str) -> str:
    """The collection qualified name (KSC-03): system, then the cluster component."""
    system_qualified = qualified_component(f"zz{run} Broker")
    return join_qualified(system_qualified, qualified_component(cluster_id or "default-cluster"))


@pytest.fixture
def run_cluster_id(scanner_settings: ScannerSettings) -> str | None:
    """The suite broker's cluster id, as the scan's own door reads it (KSC-03)."""
    cluster = KafkaCluster(scanner_settings.bootstrap_servers)
    try:
        return cluster.cluster_id()
    finally:
        cluster.close()


@pytest.mark.critical
@pytest.mark.covers(
    "aurelius_atlas_kafka_scanner.scan.run_scan",
    "aurelius_atlas_kafka_scanner.cluster.KafkaCluster.external_topics",
    "aurelius_atlas_kafka_scanner.cluster.KafkaCluster.cluster_id",
    "aurelius_atlas_kafka_scanner.graph.build_graph",
    "aurelius_atlas_kafka_scanner.__main__.build_client",
    rules=["KSC-09", "KSC-02", "KSC-03", "KSC-10"],
)
async def test__the_scanners_own_token_writes_the_tree_and_the_audit_names_it(
    scanner: AtlasClient,
    writer: AtlasClient,
    scanner_settings: ScannerSettings,
    scanner_claims: dict[str, Any],
    topics: Callable[[str], str],
    register: Callable[[str, str, str], Awaitable[int]],
    cleanup: Seeded,
    run_token: str,
    run_cluster_id: str | None,
) -> None:
    """The scan as its own service identity over the real broker (KSC-09, KSC-02, KSC-10).

    Two run-namespaced topics on the suite broker, one with a registered Avro subject; the scan
    admits both through the ``zz<run>*`` pattern (a foreign topic is never registered — KSC-02's
    patterns on a live broker), writes the tree with one bulk request, and the store holds the
    System, the Collection, both Datasets, and the fields. The dataset's create event names the
    scanner's service account, not the seeding writer and not an anonymous caller.
    """
    orders = topics("orders")
    payments = topics("payments")
    await register(f"{orders}-value", "AVRO", ORDER_AVRO)

    settings = _run_settings(scanner_settings, run_token)
    report = await _scan(scanner, settings, cleanup)
    assert report.topics_written == 2
    # The orders topic reads its subject; payments has none and no records, so it is the
    # fieldless case (KSC-05) — still written as a dataset, which the checks below confirm.
    assert report.topics_fieldless == 1

    system_qn = qualified_component(f"zz{run_token} Broker")
    collection_qn = _collection_qualified(run_cluster_id, run_token)
    orders_qn = _qualified(run_cluster_id, run_token, orders)
    payments_qn = _qualified(run_cluster_id, run_token, payments)

    system = await _wait_for(writer, "m4i_system", system_qn)
    assert _attributes(system)["name"] == f"zz{run_token} Broker"
    collection = await _wait_for(writer, "m4i_collection", collection_qn)
    orders_entity = await _wait_for(writer, "m4i_dataset", orders_qn)
    await _wait_for(writer, "m4i_dataset", payments_qn)

    city_qn = join_qualified(orders_qn, "address", "city")
    city = await _wait_for(writer, "m4i_field", city_qn)
    assert _attributes(city)["fieldType"] == "string"
    id_qn = join_qualified(orders_qn, "id")
    id_field = await _wait_for(writer, "m4i_field", id_qn)
    assert _attributes(id_field)["fieldType"] == "string"

    events = await writer.entity.audit_events(str(orders_entity.guid))
    created = [event for event in events if event.action is EntityAuditActionV2.ENTITY_CREATE]
    assert created, f"the dataset has no create event: {events}"
    expected = scanner_claims.get("preferred_username") or scanner_claims["sub"]
    assert {event.user for event in created} == {str(expected)}
    collection_events = await writer.entity.audit_events(str(collection.guid))
    assert {e.user for e in collection_events if e.action is EntityAuditActionV2.ENTITY_CREATE} == {str(expected)}


@pytest.mark.critical
@pytest.mark.covers(
    "aurelius_atlas_kafka_scanner.scan.run_scan",
    "aurelius_atlas_kafka_scanner.graph.build_graph",
    rules=["KSC-07"],
)
async def test__a_second_scan_updates_the_same_entities_in_place(
    scanner: AtlasClient,
    writer: AtlasClient,
    scanner_settings: ScannerSettings,
    topics: Callable[[str], str],
    cleanup: Seeded,
    run_token: str,
    run_cluster_id: str | None,
) -> None:
    """A re-scan is idempotent on the real store (KSC-07): the same guid, no duplicates.

    The dataset resolves by its unique qualified name: the second run updates the first's
    entity in place (EWR-11's resolve, EWR-08's skip of the unchanged tree), and the store
    still answers exactly one dataset for the name.
    """
    orders = topics("orders")
    settings = _run_settings(scanner_settings, run_token)

    await _scan(scanner, settings, cleanup)
    qn = _qualified(run_cluster_id, run_token, orders)
    entity = await _wait_for(writer, "m4i_dataset", qn)
    first_guid = str(entity.guid)

    await _scan(scanner, settings, cleanup)
    again = await _found(writer, "m4i_dataset", qn)
    assert again is not None
    assert str(again.guid) == first_guid, "the re-scan duplicated or replaced the dataset"


@pytest.mark.critical
@pytest.mark.covers(
    "aurelius_atlas_kafka_scanner.scan.run_scan",
    "aurelius_atlas_kafka_scanner.cluster.KafkaCluster.newest_record",
    "aurelius_atlas_kafka_scanner.registry.SchemaRegistry.latest",
    "aurelius_atlas_kafka_scanner.registry.SchemaRegistry.by_id",
    "aurelius_atlas_kafka_scanner.fields.parse_avro",
    "aurelius_atlas_kafka_scanner.fields.parse_payload",
    rules=["KSC-04", "KSC-05"],
)
async def test__the_subject_the_wire_id_and_the_inference_each_answer_a_topic(
    scanner: AtlasClient,
    writer: AtlasClient,
    scanner_settings: ScannerSettings,
    topics: Callable[[str], str],
    produce: Callable[[str, bytes], None],
    register: Callable[[str, str, str], Awaitable[int]],
    cleanup: Seeded,
    run_token: str,
    run_cluster_id: str | None,
) -> None:
    """Three live doors for three topics (KSC-04, KSC-05): subject, sniff, inference.

    ``subject`` reads its latest Avro from the Registry; ``wire`` has no subject but its record
    names a schema id the Registry answers (the magic-byte sniff); ``json`` has neither and its
    JSON record infers its own shape. Each dataset lands with the fields the door answered.
    """
    subject_topic = topics("subject")
    wire_topic = topics("wire")
    json_topic = topics("json")
    schema_id = await register(f"{subject_topic}-value", "AVRO", ORDER_AVRO)
    unused_id = await register(f"{wire_topic}-unused", "AVRO", ORDER_AVRO)
    assert unused_id > 0
    produce(wire_topic, _wire_value(schema_id))
    produce(json_topic, json.dumps({"level": "warn", "count": 3}).encode())

    settings = _run_settings(scanner_settings, run_token)
    report = await _scan(scanner, settings, cleanup)
    assert report.topics_written == 3
    assert report.notices == []

    subject_qn = _qualified(run_cluster_id, run_token, subject_topic)
    wire_qn = _qualified(run_cluster_id, run_token, wire_topic)
    json_qn = _qualified(run_cluster_id, run_token, json_topic)
    for name, field, type_name in (
        (subject_qn, "id", "string"),
        (wire_qn, "id", "string"),
        (json_qn, "level", "string"),
        (json_qn, "count", "integer"),
    ):
        entity = await _wait_for(writer, "m4i_field", join_qualified(name, field))
        assert _attributes(entity)["fieldType"] == type_name


@pytest.mark.critical
@pytest.mark.covers(
    "aurelius_atlas_kafka_scanner.scan.run_scan",
    rules=["KSC-05", "KSC-08"],
)
async def test__a_fieldless_topic_lands_as_a_dataset_with_a_notice(
    scanner: AtlasClient,
    writer: AtlasClient,
    scanner_settings: ScannerSettings,
    topics: Callable[[str], str],
    cleanup: Seeded,
    run_token: str,
    run_cluster_id: str | None,
) -> None:
    """A topic with no subject and no record is data with a notice, not a failure (KSC-05).

    The scan still registers the dataset — field-less — and the report carries one notice naming
    the topic; the run exits as a completed scan (KSC-01).
    """
    empty = topics("empty")
    settings = _run_settings(scanner_settings, run_token)
    report = await _scan(scanner, settings, cleanup)
    assert report.topics_written == 1
    assert report.topics_fieldless == 1
    assert len(report.notices) == 1
    assert empty in report.notices[0]

    qn = _qualified(run_cluster_id, run_token, empty)
    dataset = await _wait_for(writer, "m4i_dataset", qn)
    assert _attributes(dataset)["name"] == empty


@pytest.mark.critical
@pytest.mark.covers(
    "aurelius_atlas_kafka_scanner.scan.run_scan",
    "aurelius_atlas_kafka_scanner.scan.dry_run_lines",
    rules=["KSC-08"],
)
async def test__a_dry_run_writes_nothing(
    scanner: AtlasClient,
    writer: AtlasClient,
    scanner_settings: ScannerSettings,
    topics: Callable[[str], str],
    cleanup: Seeded,
    run_token: str,
    run_cluster_id: str | None,
) -> None:
    """``--dry-run`` reads the real broker and writes nothing (KSC-08).

    The report holds the full tree — the topic pattern admitted the run's topic — but the
    store answers no dataset for the name the scan would have written.
    """
    orders = topics("orders")
    settings = _run_settings(scanner_settings, run_token)
    report = await _scan(scanner, settings, cleanup, dry_run=True)
    assert report.entities
    assert report.topics_written == 1

    qn = _qualified(run_cluster_id, run_token, orders)
    assert await _found(writer, "m4i_dataset", qn) is None


@pytest.mark.critical
@pytest.mark.covers(
    "aurelius_atlas_kafka_scanner.scan.run_scan",
    "aurelius_atlas_kafka_scanner.cluster.KafkaCluster.external_topics",
    "aurelius_atlas_kafka_scanner.cluster.KafkaCluster.newest_record",
    "aurelius_atlas_kafka_scanner.cluster.broker_config",
    rules=["KSC-10"],
)
async def test__a_scan_over_scram_reads_the_same_broker(
    scanner: AtlasClient,
    topics: Callable[[str], str],
    produce: Callable[[str, bytes], None],
    cleanup: Seeded,
    run_token: str,
    sasl_settings: ScannerSettings,
) -> None:
    """The SASL listener answers the whole read the plain one does (KSC-10): SCRAM in, scan out.

    A dry run over the broker's SASL_PLAINTEXT listener: the door authenticates with the
    SCRAM-SHA-512 principal, the metadata read and the record sniff both ride that connection,
    and the run-namespaced pattern admits exactly the run's topics — the ladder's read leg on
    a live broker, no fake between the job and the listener. Nothing is written (KSC-08).
    """
    orders = topics("orders")
    produce(orders, json.dumps({"sku": "abc"}).encode())
    settings = sasl_settings.model_copy(update={"topics": f"zz{run_token}*"})
    report = await _scan(scanner, settings, cleanup, dry_run=True)
    assert report.topics_written == 1
    assert report.topics_fieldless == 0  # the sniff read the record over the SASL connection
    assert report.entities


@pytest.mark.critical
@pytest.mark.covers(
    "aurelius_atlas_kafka_scanner.cluster.KafkaCluster.external_topics",
    rules=["KSC-01", "KSC-10"],
)
def test__a_wrong_secret_fails_the_run_naming_the_bootstrap_list(
    sasl_settings: ScannerSettings,
) -> None:
    """A refused credential is a dead broker as far as the run cares (KSC-01, KSC-10): exit-path failure.

    The door cannot separate a listener that refuses it from one that never answers: the same
    BrokerUnreachableError, naming the bootstrap list, is what the CLI answers with exit 1.
    """
    cluster = KafkaCluster(
        sasl_settings.bootstrap_servers,
        security_protocol="SASL_PLAINTEXT",
        sasl_mechanism="SCRAM-SHA-512",
        sasl_username=sasl_settings.sasl_username or "",
        sasl_password="not-the-secret",  # noqa: S106 - a deliberately wrong dev secret
        admin_request_timeout_ms=5_000,
    )
    try:
        with pytest.raises(BrokerUnreachableError, match=re.escape(sasl_settings.bootstrap_servers)):
            cluster.external_topics()
    finally:
        cluster.close()
