"""One scan: the steps, the notices, the one bulk write (13.3, DBS-02..05, DBS-09, DBS-11).

The scan is a straight walk of the door: the schemas (DBS-04), the patterns that admit them,
each schema's tables (DBS-05), one reflect per table, the tree (DBS-03, DBS-06..08), and one
bulk request holding it all (DBS-09). A table whose reflection fails keeps a field-less
dataset and a notice (DBS-05) and the run completes; only a run-level failure — the database
silent (DBS-02), the write refused — leaves :func:`run_scan` by exception.

The door is the app's own Protocol, so a test hands the walk a fake and exercises every rule
with no sockets. The catalogue door is the real :class:`AtlasClient`, because the scan's one
write is its contract with the store (DBS-09) and the client is thin on purpose (DBS-10).
"""

from dataclasses import dataclass, field
from typing import Protocol

from aurelius_atlas_model.instance import AtlasEntitiesWithExtInfo, AtlasEntity, EntityMutationResponse

from aurelius_atlas_db_scanner.database import DatabaseDoor, TableReflectionError, compile_patterns, matches_any
from aurelius_atlas_db_scanner.graph import Graph, build_graph, entity_line, table_display_name
from aurelius_atlas_db_scanner.reflect import TableInfo
from aurelius_atlas_db_scanner.settings import ScannerSettings


class ScanDoor(Protocol):
    """The catalogue door the scan writes through: one bulk request per run (DBS-09, DBS-10).

    ``AtlasClient.entity`` answers it — the same call the webapp suite's seed idiom makes; a
    test hands a fake and reads the entities back from it.
    """

    async def create_or_update_bulk(self, entities: AtlasEntitiesWithExtInfo) -> EntityMutationResponse:
        """``POST /entity/bulk``: the whole tree, one request (DBS-09, KSC-07)."""
        ...


@dataclass
class ScanReport:
    """What one scan did, as the CLI prints it (DBS-02, DBS-11)."""

    entities: list[AtlasEntity] = field(default_factory=list)
    """The tree the run built — the entities written, or the ones a dry run would write."""

    notices: list[str] = field(default_factory=list)
    """Every notice the run gathered, in scan order (DBS-05, DBS-08, DBS-11)."""

    schemas_found: int = 0
    """The schemas the patterns admitted before any table read (DBS-04)."""

    tables_found: int = 0
    """The tables the patterns admitted across those schemas (DBS-05)."""

    tables_written: int = 0
    """The datasets the run registered — every admitted table, field-less ones included (DBS-05, DBS-07)."""

    tables_fieldless: int = 0
    """The tables that landed without columns, each with its notice (DBS-05)."""


async def run_scan(  # noqa: PLR0913 - the two doors, the settings, and the run's own switches
    door: DatabaseDoor,
    client: ScanDoor,
    settings: ScannerSettings,
    *,
    schema_filter: list[str] | None = None,
    table_filter: list[str] | None = None,
    dry_run: bool = False,
) -> ScanReport:
    """Run one scan over the database and write the tree once (DBS-02..09, DBS-11).

    The walk never writes on a dry run but builds the whole tree anyway — the dry run prints
    what it would store, one line per entity (DBS-11). A missing ``--table``/``--schema`` name
    is a notice, not a failure (DBS-11); a database the door cannot reach fails the run before
    any of this (DBS-02, in :meth:`DatabaseDoor.open`).

    Args:
        door: The database door; already open. Its schemas and tables open the walk.
        client: The catalogue door the one bulk write goes through (DBS-09, DBS-10).
        settings: The scan's configuration; its patterns, System, and nameless-schema name steer it.
        schema_filter: ``--schema`` names; when given, only these patterns limit the schemas (DBS-11).
        table_filter: ``--table`` names; when given, only these patterns limit the tables (DBS-11).
        dry_run: Read everything, write nothing; the report still holds the full tree (DBS-11).

    Returns:
        The :class:`ScanReport`: the tree, the notices, the counts.

    Raises:
        DatabaseUnreachableError: re-raised by the caller's open — the walk itself never connects.
        Exception: a refused write — the store said no, which the scan cannot answer (DBS-02).
    """
    report = ScanReport()
    schemas = _admitted_schemas(door, settings, schema_filter)
    _notice_missing(schemas, schema_filter, "schema", report)
    report.schemas_found = len(schemas)

    tables: list[TableInfo] = []
    for schema in schemas:
        admitted = _admitted_tables(door, settings, schema, table_filter)
        tables.extend(_reflect_or_notice(door, schema, table, report) for table in admitted)
    report.tables_found = len(tables)
    _notice_missing_tables(tables, table_filter, report)
    report.tables_written = len(tables)

    graph: Graph = build_graph(
        system_name=settings.system_name,
        schema_name=settings.schema_name,
        schemas=schemas,
        tables=tables,
    )
    report.notices.extend(graph.notices)
    report.entities = graph.entities
    if not dry_run and report.entities:
        await client.create_or_update_bulk(AtlasEntitiesWithExtInfo(entities=report.entities))
    return report


def _admitted_schemas(
    door: DatabaseDoor,
    settings: ScannerSettings,
    schema_filter: list[str] | None,
) -> list[str | None]:
    """The schemas to scan (DBS-04): the door minus the system set, matched by the patterns in force."""
    patterns = compile_patterns(",".join(schema_filter) if schema_filter else settings.schemas)
    return door.schema_names(patterns)


def _admitted_tables(
    door: DatabaseDoor,
    settings: ScannerSettings,
    schema: str | None,
    table_filter: list[str] | None,
) -> list[str]:
    """One schema's tables that the patterns in force admit (DBS-05)."""
    patterns = compile_patterns(",".join(table_filter) if table_filter else settings.tables)
    return door.table_names(schema, patterns)


def _reflect_or_notice(door: DatabaseDoor, schema: str | None, table: str, report: ScanReport) -> TableInfo:
    """One table's metadata, or the field-less info its failure leaves (DBS-05).

    A reflection the inspector refuses keeps a dataset with no columns — the field-less case,
    as the Kafka scanner's KSC-05 — and a notice naming the table and the failure reason. The
    run completes; a broken table is data, not a run-level failure (DBS-02).
    """
    name = table_display_name(schema, table)
    try:
        info = door.reflect(schema, table)
    except TableReflectionError as cause:
        report.notices.append(f"{name}: the reflection failed ({cause}) — no columns registered")
        report.tables_fieldless += 1
        return TableInfo(schema=schema, name=table)
    if not info.columns:
        report.notices.append(f"{name}: the table answers no columns — registered without fields")
        report.tables_fieldless += 1
    return info


def _notice_missing(
    admitted: list[str | None],
    requested: list[str] | None,
    kind: str,
    report: ScanReport,
) -> None:
    """A ``--schema`` the admitted set does not hold is a notice, not a failure (DBS-11)."""
    for named in requested or []:
        patterns = compile_patterns(named)
        if not any(matches_any(name or "", patterns) for name in admitted):
            report.notices.append(f"{named}: the database holds no {kind} matching it")


def _notice_missing_tables(tables: list[TableInfo], requested: list[str] | None, report: ScanReport) -> None:
    """A ``--table`` the scan admitted no name for is a notice, not a failure (DBS-11)."""
    for named in requested or []:
        patterns = compile_patterns(named)
        if not any(matches_any(table.name, patterns) for table in tables):
            report.notices.append(f"{named}: the database holds no table matching it")


def scan_line(report: ScanReport, *, dry_run: bool) -> str:
    """The CLI's closing line: what the run did, in one sentence (DBS-02, DBS-11)."""
    verb = "would register" if dry_run else "registered"
    return (
        f"{verb} {report.tables_written} tables from {report.schemas_found} schemas "
        f"({report.tables_found} admitted, {report.tables_fieldless} field-less, "
        f"{len(report.entities)} entities)"
    )


def dry_run_lines(report: ScanReport) -> list[str]:
    """The dry-run's one line per entity the run would write (DBS-11)."""
    return [entity_line(entity) for entity in report.entities]
