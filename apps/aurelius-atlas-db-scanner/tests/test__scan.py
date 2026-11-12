"""One scan: the walk, the notices, the dry run, the filters, a dead database (DBS-02, DBS-05, DBS-11).

A fake database door answers the walk and a fake catalogue door catches the one bulk request,
so every rule of DBS-02, DBS-05 and DBS-11 runs offline. The dead-database case opens the real
door through the CLI against a port nothing answers on, because the exit code is what DBS-02
promises the operator.
"""

import re
from collections.abc import Callable, Sequence

import pytest
from aurelius_atlas_db_scanner.__main__ import EXIT_FAILURE, run
from aurelius_atlas_db_scanner.database import TableReflectionError, matches_any
from aurelius_atlas_db_scanner.reflect import ColumnInfo, ForeignKeyInfo, TableInfo
from aurelius_atlas_db_scanner.scan import dry_run_lines, run_scan, scan_line
from aurelius_atlas_db_scanner.settings import ENV_PREFIX, ScannerSettings
from aurelius_atlas_model.instance import AtlasEntitiesWithExtInfo, AtlasEntity, EntityMutationResponse

Settings = Callable[..., ScannerSettings]

SCRUB_CANARY = "sup3r-s3cret"
"""The stand-in password the door must never repeat: it proves the scrubbing (DBS-02, DD-506)."""

DEAD_DSN = f"postgresql+psycopg://atlas:{SCRUB_CANARY}@127.0.0.1:1/warehouse"
"""A Postgres DSN pointing at a port nothing answers on, with a password to prove scrubbing."""


class FakeDatabase:
    """The database door, answered from memory: the schemas, the tables, one reflection each."""

    def __init__(
        self, schemas: Sequence[str | None], tables: dict[str | None, Sequence[str]], *, fail: Sequence[str] = ()
    ) -> None:
        self._schemas = list(schemas)
        self._tables = tables
        self._fail = set(fail)

    def open(self) -> None:
        """The fake always answers a connect — DBS-02's silent case is the CLI test's."""

    def close(self) -> None:
        """Nothing to release."""

    def schema_names(self, patterns: list[re.Pattern[str]]) -> list[str | None]:
        """The fake's schemas that the patterns admit."""
        return [schema for schema in self._schemas if matches_any(schema or "", patterns)]

    def table_names(self, schema: str | None, patterns: list[re.Pattern[str]]) -> list[str]:
        """The fake's tables of one schema that the patterns admit."""
        return [table for table in self._tables.get(schema, []) if matches_any(table, patterns)]

    def reflect(self, schema: str | None, table: str) -> TableInfo:
        """A one-column table, the reflection failure the test asked for, or line's foreign key."""
        if table in self._fail:
            msg = "the inspector choked on this one"
            raise TableReflectionError(msg)
        foreign_keys = (ForeignKeyInfo(("id",), schema, "orders", ("id",)),) if table == "line" else ()
        return TableInfo(
            schema=schema, name=table, columns=(ColumnInfo(name="id", field_type="INTEGER"),), foreign_keys=foreign_keys
        )


class FakeCatalogue:
    """The catalogue door: catch the bulk requests, answer like the store."""

    def __init__(self) -> None:
        self.requests: list[AtlasEntitiesWithExtInfo] = []

    async def create_or_update_bulk(self, entities: AtlasEntitiesWithExtInfo) -> EntityMutationResponse:
        """Catch the one bulk request, answer like the store."""
        self.requests.append(entities)
        return EntityMutationResponse()


def _by_qualified(entities: Sequence[AtlasEntity], qualified: str, type_name: str) -> AtlasEntity:
    """One entity by its qualified name and type — the qualified name alone is shared across types."""
    return next(
        entity
        for entity in entities
        if (entity.attributes or {}).get("qualifiedName") == qualified and entity.type_name == type_name
    )


@pytest.mark.covers("aurelius_atlas_db_scanner.scan.run_scan", rules=["DBS-02", "DBS-09"])
async def test_a_completed_scan_walks_the_database_and_writes_once(settings: Settings) -> None:
    """DBS-02/DBS-09: the walk ends with one bulk request holding the whole tree, and counts to print."""
    database = FakeDatabase(["sales"], {"sales": ["orders", "line"]})
    catalogue = FakeCatalogue()
    report = await run_scan(database, catalogue, settings())
    assert len(catalogue.requests) == 1
    entities = catalogue.requests[0].entities or []
    assert len(entities) == 7  # system, collection, two datasets, two fields, one foreign-key process
    assert _by_qualified(entities, "test-database", "m4i_system") is not None
    assert _by_qualified(entities, "test-database--sales--line--id", "m4i_generic_process") is not None
    assert (report.schemas_found, report.tables_found, report.tables_written, report.tables_fieldless) == (1, 2, 2, 0)
    assert report.notices == []
    assert (
        scan_line(report, dry_run=False) == "registered 2 tables from 1 schemas (2 admitted, 0 field-less, 7 entities)"
    )


@pytest.mark.covers("aurelius_atlas_db_scanner.scan.run_scan", rules=["DBS-05"])
async def test_a_failing_table_lands_as_a_fieldless_dataset_with_a_notice(settings: Settings) -> None:
    """DBS-05: a reflection that fails is a notice and a bare dataset — and the run still completes."""
    database = FakeDatabase([None], {None: ["orders", "broken"]}, fail=["broken"])
    catalogue = FakeCatalogue()
    report = await run_scan(database, catalogue, settings())
    assert report.notices == [
        "broken: the reflection failed (the inspector choked on this one) — no columns registered"
    ]
    assert (report.tables_written, report.tables_fieldless) == (2, 1)
    entities = catalogue.requests[0].entities or []
    broken = _by_qualified(entities, "test-database--default--broken", "m4i_dataset")
    assert broken.relationship_attributes is not None
    assert broken.relationship_attributes["fields"] == []


@pytest.mark.covers("aurelius_atlas_db_scanner.scan.run_scan", rules=["DBS-05"])
async def test_a_table_that_answers_no_columns_lands_fieldless_with_a_notice(settings: Settings) -> None:
    """DBS-05: a reflection that answers zero columns is the same field-less case, by another cause."""

    class Bare(FakeDatabase):
        def reflect(self, schema: str | None, table: str) -> TableInfo:
            return TableInfo(schema=schema, name=table)

    report = await run_scan(Bare([None], {None: ["empty"]}), FakeCatalogue(), settings())
    assert report.notices == ["empty: the table answers no columns — registered without fields"]
    assert report.tables_fieldless == 1


@pytest.mark.covers("aurelius_atlas_db_scanner.scan.run_scan", rules=["DBS-11"])
async def test_a_dry_run_builds_the_tree_and_writes_nothing(settings: Settings) -> None:
    """DBS-11: the dry run reads everything, writes nothing, and the report still holds the full tree."""
    catalogue = FakeCatalogue()
    report = await run_scan(FakeDatabase(["sales"], {"sales": ["orders"]}), catalogue, settings(), dry_run=True)
    assert catalogue.requests == []
    assert len(report.entities) == 4  # system, collection, dataset, field
    assert dry_run_lines(report) == [
        "m4i_system test-database",
        "m4i_collection test-database--sales",
        "m4i_dataset test-database--sales--orders",
        "m4i_field test-database--sales--orders--id",
    ]
    assert scan_line(report, dry_run=True).startswith("would register 1 tables")


@pytest.mark.covers("aurelius_atlas_db_scanner.scan.run_scan", rules=["DBS-11"])
async def test_the_cli_filters_beat_the_settings_patterns(settings: Settings) -> None:
    """DBS-11: --schema/--table limit this run; the settings' own patterns stand aside."""
    job = settings(schemas="ops", tables="nothing")
    database = FakeDatabase(["sales", "ops"], {"sales": ["orders"], "ops": ["audits"]})
    report = await run_scan(database, FakeCatalogue(), job, schema_filter=["sales"], table_filter=["orders"])
    assert (report.schemas_found, report.tables_found) == (1, 1)
    assert report.notices == []


@pytest.mark.covers("aurelius_atlas_db_scanner.scan.run_scan", rules=["DBS-11"])
async def test_a_named_schema_or_table_the_database_lacks_is_a_notice_not_a_failure(settings: Settings) -> None:
    """DBS-11: a --schema or --table the database does not hold is a notice, and the run completes."""
    database = FakeDatabase(["sales"], {"sales": ["orders"]})
    report = await run_scan(
        database,
        FakeCatalogue(),
        settings(),
        schema_filter=["sales", "ghost"],
        table_filter=["orders", "phantom"],
    )
    assert report.tables_written == 1
    assert sorted(report.notices) == [
        "ghost: the database holds no schema matching it",
        "phantom: the database holds no table matching it",
    ]


@pytest.mark.covers("aurelius_atlas_db_scanner.__main__.run", rules=["DBS-02"])
def test_a_database_that_answers_no_connect_exits_one_naming_host_not_password(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    """DBS-02: a silent database is a run-level failure — exit 1, host and database named, password scrubbed."""
    monkeypatch.setenv(f"{ENV_PREFIX}DSN", DEAD_DSN)
    monkeypatch.setenv(f"{ENV_PREFIX}CLIENT_SECRET", "anything")
    with caplog.at_level("DEBUG"):
        assert run(["--system-name", "Test Database", "--connect-timeout-seconds", "1"]) == EXIT_FAILURE
    printed = caplog.text
    assert "127.0.0.1:1" in printed
    assert "warehouse" in printed
    assert SCRUB_CANARY not in printed


@pytest.mark.covers("aurelius_atlas_db_scanner.__main__.run", rules=["DBS-02", "DBS-12"])
def test_a_settings_answer_without_a_dsn_exits_one_naming_the_key(capsys: pytest.CaptureFixture[str]) -> None:
    """DBS-12 through the CLI: no DSN, no scan — exit 1 and the message names the key (autouse env is clean)."""
    assert run(["--system-name", "Test Database"]) == EXIT_FAILURE
    assert "dsn" in capsys.readouterr().err.lower()
