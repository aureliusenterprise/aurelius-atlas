"""One scan: the steps, the notices, the one bulk write (13.1, KSC-01, KSC-04..08).

The scan is a straight walk of the doors: the broker's topics (KSC-02), the patterns that admit
them, one schema read per topic (KSC-04, KSC-05), the tree (KSC-03, KSC-06), and one bulk request
holding it all (KSC-07). A topic whose fields cannot be read is data with a notice and a field-less
dataset (KSC-05), not a failure; only a run-level failure — the broker silent (KSC-01), the write
refused — leaves :func:`run_scan` by exception.

The doors are the app's own Protocols, so a test hands the walk fakes and exercises every rule
with no sockets. The catalogue door is the real :class:`AtlasClient`, because the scan's one write
is its contract with the store (KSC-07) and the client is thin on purpose (KSC-09).
"""

from dataclasses import dataclass, field
from typing import Protocol

from aurelius_atlas_model.instance import AtlasEntitiesWithExtInfo, AtlasEntity, EntityMutationResponse

from aurelius_atlas_kafka_scanner.cluster import ClusterDoor, compile_patterns, matches_any
from aurelius_atlas_kafka_scanner.fields import FieldSpec, parse_avro, parse_json_schema, parse_payload, schema_id_of
from aurelius_atlas_kafka_scanner.graph import TopicTree, build_graph, entity_line
from aurelius_atlas_kafka_scanner.registry import RegistryDoor, SubjectSchema
from aurelius_atlas_kafka_scanner.settings import ScannerSettings

SCHEMA_SUBJECT_SUFFIX = "-value"
"""The Registry subject of a topic's value schema, as Confluent's schemas name it (KSC-04)."""

USABLE_SCHEMA_TYPES = frozenset({"AVRO", "JSON"})
"""The two Registry schema types the parsers read (KSC-04); anything else moves the topic to the sniff."""


class ScanDoor(Protocol):
    """The catalogue door the scan writes through: one bulk request per run (KSC-07, KSC-09).

    ``AtlasClient.entity`` answers it — the same call the webapp suite's seed idiom makes; a test
    hands a fake and reads the entities back from it.
    """

    async def create_or_update_bulk(self, entities: AtlasEntitiesWithExtInfo) -> EntityMutationResponse:
        """``POST /entity/bulk``: the whole tree, one request (KSC-07)."""
        ...


@dataclass
class ScanReport:
    """What one scan did, as the CLI prints it (KSC-01, KSC-08)."""

    entities: list[AtlasEntity] = field(default_factory=list)
    """The tree the run built — the entities written, or the ones a dry run would write."""

    notices: list[str] = field(default_factory=list)
    """Every notice the run gathered, in scan order (KSC-05, KSC-08)."""

    topics_found: int = 0
    """The external topics the patterns admitted before any read (KSC-02)."""

    topics_written: int = 0
    """The datasets the run registered — every admitted topic, field-less ones included (KSC-05)."""

    topics_fieldless: int = 0
    """The topics that landed without fields, each with its notice (KSC-05)."""


async def run_scan(  # noqa: PLR0913 - the three doors and the settings are the scan's own parts
    cluster: ClusterDoor,
    registry: RegistryDoor,
    client: ScanDoor,
    settings: ScannerSettings,
    *,
    topic_filter: list[str] | None = None,
    dry_run: bool = False,
) -> ScanReport:
    """Run one scan over the broker and write the tree once (KSC-01..08).

    Args:
        cluster: The broker door; its topics and cluster id open the scan (KSC-02, KSC-03).
        registry: The Schema Registry door, ``None``-answering when the settings name none (KSC-04).
        client: The catalogue door the one bulk write goes through (KSC-07, KSC-09).
        settings: The scan's configuration; its ``topics`` and ``system_name`` steer the walk.
        topic_filter: ``--topic`` names; when given, only these patterns are scanned (KSC-08).
        dry_run: Read everything, write nothing; the report still holds the full tree (KSC-08).

    Returns:
        The :class:`ScanReport`: the tree, the notices, the counts.

    Raises:
        BrokerUnreachable: the broker answered no metadata — a run-level failure (KSC-01, KSC-02).
        Exception: a refused write — the store said no, which the scan cannot answer (KSC-01).
    """
    report = ScanReport()
    external = cluster.external_topics()
    patterns = compile_patterns(",".join(topic_filter) if topic_filter else settings.topics)
    topics = [topic for topic in external if matches_any(topic, patterns)]
    report.topics_found = len(topics)
    for named in topic_filter or []:
        if not any(matches_any(topic, compile_patterns(named)) for topic in external):
            report.notices.append(f"{named}: the broker holds no topic matching it")  # a notice, not a failure (KSC-08)

    trees: list[TopicTree] = []
    for topic in topics:
        fields, notice = await _read_fields(registry, cluster, topic)
        if notice is not None:
            report.notices.append(notice)
            report.topics_fieldless += 1
        trees.append(TopicTree(topic, fields))
        report.topics_written += 1

    report.entities = build_graph(
        system_name=settings.system_name,
        cluster_id=cluster.cluster_id(),
        trees=trees,
    )
    if not dry_run and report.entities:
        await client.create_or_update_bulk(AtlasEntitiesWithExtInfo(entities=report.entities))
    return report


async def _read_fields(
    registry: RegistryDoor,
    cluster: ClusterDoor,
    topic: str,
) -> tuple[tuple[FieldSpec, ...], str | None]:
    """One topic's field tree and the notice it earned (KSC-04, KSC-05).

    The Registry's latest ``<topic>-value`` subject first (KSC-04); its answer parsed by its type.
    A subject absent, of an unreadable type, or unreadable itself falls to the sniff (KSC-05): a
    wire record names its schema id in the Registry — through KSC-04's parsers again — and a JSON
    record infers its own shape. Both doors empty is the field-less case, and the notice names
    the door that was silent.
    """
    subject = f"{topic}{SCHEMA_SUBJECT_SUFFIX}"
    usable, wrong_type = await _usable_subject(registry, subject)
    if usable is not None:
        fields, error = _parse_schema(usable)
        if error is None:
            return fields, None
        return await _sniff(
            registry,
            cluster,
            topic,
            f"the Registry's {usable.schema_type} schema for {subject} could not be read ({error})",
        )
    if wrong_type is not None:
        return await _sniff(registry, cluster, topic, wrong_type)
    return await _sniff(registry, cluster, topic, None)


async def _sniff(
    registry: RegistryDoor,
    cluster: ClusterDoor,
    topic: str,
    registry_reason: str | None,
) -> tuple[tuple[FieldSpec, ...], str | None]:
    """The topic's fields from its own newest record (KSC-05).

    ``registry_reason`` says why the Registry door was skipped, and earns the notice when the
    sniff answers nothing.
    """
    record = cluster.newest_record(topic)
    if record is None or not record.value:
        reason = registry_reason or "the Registry holds no subject and the topic holds no record"
        return (), f"{topic}: {reason} — no fields registered"
    if (schema_id := schema_id_of(record.value)) is not None:
        by_id, id_reason = await _usable_schema_by_id(registry, schema_id)
        if by_id is None:
            return (), f"{topic}: {id_reason or f'its messages name schema {schema_id}, the Registry holds no answer'}"
        fields, error = _parse_schema(by_id)
        if error is None:
            return fields, None
        return (), f"{topic}: the wire schema {schema_id} could not be read ({error})"
    fields, error = _parse_payload(record.value)
    if error is None:
        return fields, None
    return (), f"{topic}: its newest message is neither a wire schema nor a JSON object — no fields registered"


async def _usable_subject(registry: RegistryDoor, subject: str) -> tuple[SubjectSchema | None, str | None]:
    """The subject's latest schema when the parsers can read its type (KSC-04), else the reason not."""
    schema = await registry.latest(subject)
    if schema is None:
        return None, None
    if schema.schema_type not in USABLE_SCHEMA_TYPES:
        return None, f"the Registry holds {subject} as {schema.schema_type}, not AVRO or JSON"
    return schema, None


async def _usable_schema_by_id(registry: RegistryDoor, schema_id: int) -> tuple[SubjectSchema | None, str | None]:
    """The wire schema the record names, when its type is readable (KSC-05)."""
    schema = await registry.by_id(schema_id)
    if schema is None:
        return None, None
    if schema.schema_type not in USABLE_SCHEMA_TYPES:
        return None, f"the Registry's schema {schema_id} is {schema.schema_type}, not AVRO or JSON"
    return schema, None


def _parse_schema(schema: SubjectSchema) -> tuple[tuple[FieldSpec, ...], str | None]:
    """A Registry schema's fields by its type (KSC-04), or the cause the parser answered."""
    parse = parse_avro if schema.schema_type == "AVRO" else parse_json_schema
    try:
        return tuple(parse(schema.schema_str)), None
    except Exception as cause:  # noqa: BLE001 - any parser failure is the topic's notice, not a crash (KSC-04)
        return (), str(cause)


def _parse_payload(value: bytes) -> tuple[tuple[FieldSpec, ...], str | None]:
    """A sniffed record's inferred fields (KSC-05), or the cause it is not a JSON object."""
    try:
        return tuple(parse_payload(value.decode())), None
    except Exception as cause:  # noqa: BLE001 - an unreadable record is the field-less notice (KSC-05)
        return (), str(cause)


def scan_line(report: ScanReport, *, dry_run: bool) -> str:
    """The CLI's closing line: what the run did, in one sentence (KSC-01, KSC-08)."""
    verb = "would register" if dry_run else "registered"
    return (
        f"{verb} {report.topics_written} topics "
        f"({report.topics_found} on the broker, {report.topics_fieldless} field-less, "
        f"{len(report.entities)} entities)"
    )


def dry_run_lines(report: ScanReport) -> list[str]:
    """The dry-run's one line per entity the run would write (KSC-08)."""
    return [entity_line(entity) for entity in report.entities]
