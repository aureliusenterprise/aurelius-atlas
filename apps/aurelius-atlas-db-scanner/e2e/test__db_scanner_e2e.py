"""E2E: the scanner against a real database and a real server (DBS-02, DBS-03, DBS-07..10).

The suite drives the job in-process — the scanner is a batch CLI, not a service — on the
stack of ``e2e/docker-compose.yaml``: a real Atlas server on the dev store, and the suite's
own Postgres (DD-507), seeded through this file's fixture. Every scan speaks as the
scanner's own service client (DBS-10): the write rides its client-credentials token and the
audit names it, so this is the spec's end-to-end proof that the identity answers read AND
write in the real catalogue. Each scenario namespaces its schemas and System to one
``zz<run>`` word, scans with a ``zz<run>*`` pattern (a foreign schema is never registered —
DBS-04's patterns on a live dialect), drops its schemas and hard-deletes its entities at the
end (DD-223); nothing here restarts the store.
"""

import asyncio
import time
from typing import Any

import pytest
from aurelius_atlas_db_scanner.__main__ import EXIT_FAILURE, run
from aurelius_atlas_db_scanner.database import SqlDatabase
from aurelius_atlas_db_scanner.graph import dataset_qualified_name, join_qualified, qualified_component
from aurelius_atlas_db_scanner.scan import ScanDoor, ScanReport, run_scan
from aurelius_atlas_db_scanner.settings import ENV_PREFIX, ScannerSettings
from aurelius_atlas_model.audit import EntityAuditActionV2
from aurelius_atlas_model.instance import AtlasEntitiesWithExtInfo, AtlasEntity, EntityMutationResponse
from aurelius_atlas_server_client import AtlasClient
from conftest import Seeded

DEAD_DSN = "postgresql+psycopg://atlas:sup3r-s3cret@127.0.0.1:1/scan-dead"
"""A DSN on a port nothing answers, with a password to prove the scrubbing in the failure."""


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
) -> ScanReport:
    """One scan on the real doors: the database and the scanner's catalogue client.

    The door is the app's own class — this is DBS-01's proof that the walk runs on a real
    dialect with no fakes between the job and the database. The door closes on the way out.
    """
    door = SqlDatabase(settings.dsn.get_secret_value(), connect_timeout_seconds=settings.connect_timeout_seconds)
    door.open()
    try:
        return await run_scan(door, _RecordingDoor(scanner, cleanup), settings)
    finally:
        door.close()


def _run_settings(scanner_settings: ScannerSettings, run: str) -> ScannerSettings:
    """The session settings for one run: its own System name and a pattern admitting only it."""
    return scanner_settings.model_copy(update={"system_name": f"zz{run} Database", "schemas": f"zz{run}*"})


def _system_qn(run: str) -> str:
    """The System's qualified name for one run token (DBS-03)."""
    return qualified_component(f"zz{run} Database")


def _dataset_qn(run: str, schema: str, table: str) -> str:
    """The dataset qualified name the scan must have written for one table (DBS-03)."""
    return dataset_qualified_name(_system_qn(run), "default", schema, table)


@pytest.mark.covers(
    "aurelius_atlas_db_scanner.scan.run_scan",
    "aurelius_atlas_db_scanner.database.SqlDatabase.schema_names",
    "aurelius_atlas_db_scanner.database.SqlDatabase.reflect",
    "aurelius_atlas_db_scanner.graph.build_graph",
    "aurelius_atlas_db_scanner.__main__.build_client",
    rules=["DBS-01", "DBS-03", "DBS-04", "DBS-06", "DBS-07", "DBS-08", "DBS-10"],
)
async def test__the_scanners_own_token_writes_the_tree_and_the_audit_names_it(
    scanner: AtlasClient,
    writer: AtlasClient,
    scanner_settings: ScannerSettings,
    scanner_claims: dict[str, Any],
    seeded_database: dict[str, str],
    cleanup: Seeded,
    run_token: str,
) -> None:
    """The scan as its own service identity over a real Postgres (DBS-01, DBS-03, DBS-08, DBS-10).

    Two run-namespaced schemas with five tables: a commented table and column, a simple
    foreign key, a composite one across the schemas, a self key, and a zero-column table. The
    scan admits them through the ``zz<run>*`` pattern (the other suites' and the dialect's own
    schemas are never registered — DBS-04 on a live dialect), writes the tree with one bulk
    request, and the store holds each piece with the names, definitions, and process ends the
    rules promise. The dataset's create event names the scanner's service account.
    """
    schema_a, schema_b = seeded_database["schema_a"], seeded_database["schema_b"]
    settings = _run_settings(scanner_settings, run_token)
    report = await _scan(scanner, settings, cleanup)

    assert report.schemas_found == 2
    assert (report.tables_found, report.tables_written) == (5, 5)
    assert report.tables_fieldless == 1
    assert report.notices == [f"{schema_a}.empty: the table answers no columns — registered without fields"]

    system = await _wait_for(writer, "m4i_system", _system_qn(run_token))
    assert _attributes(system)["name"] == f"zz{run_token} Database"
    await _wait_for(writer, "m4i_collection", join_qualified(_system_qn(run_token), qualified_component(schema_a)))
    orders_qn = _dataset_qn(run_token, schema_a, "orders")
    orders = await _wait_for(writer, "m4i_dataset", orders_qn)
    assert _attributes(orders)["definition"] == "One row per customer order"

    shop_name = await _wait_for(writer, "m4i_field", join_qualified(orders_qn, "shop_name"))
    assert _attributes(shop_name)["fieldType"] == "TEXT"
    assert _attributes(shop_name)["definition"] == "Where the order was placed"
    id_field = await _wait_for(writer, "m4i_field", join_qualified(orders_qn, "id"))
    assert _attributes(id_field)["definition"] == "Primary key"

    line_qn = _dataset_qn(run_token, schema_a, "line")
    process = await _wait_for(writer, "m4i_generic_process", join_qualified(line_qn, "order_id"))
    assert _attributes(process)["name"] == f"{schema_a}.line.order_id"
    composite = await _found(writer, "m4i_generic_process", join_qualified(line_qn, "shop_code"))
    assert composite is not None, "the composite key's first pair is missing"
    assert await _found(writer, "m4i_generic_process", join_qualified(line_qn, "shop_region")) is not None
    employee_qn = _dataset_qn(run_token, schema_b, "employee")
    self_key = await _wait_for(writer, "m4i_generic_process", join_qualified(employee_qn, "manager_id"))
    assert self_key.relationship_attributes is not None
    # The store enriches each endpoint with its own relationship facts (guid, type), so the
    # DBS-08 fact is the entity the ends name: the same dataset guid and qualifiedName on both.
    inputs = self_key.relationship_attributes["inputs"]
    outputs = self_key.relationship_attributes["outputs"]
    assert [(end["guid"], end["qualifiedName"]) for end in inputs] == [
        (end["guid"], end["qualifiedName"]) for end in outputs
    ]

    events = await writer.entity.audit_events(str(orders.guid))
    created = [event for event in events if event.action is EntityAuditActionV2.ENTITY_CREATE]
    assert created, f"the dataset has no create event: {events}"
    expected = scanner_claims.get("preferred_username") or scanner_claims["sub"]
    assert {event.user for event in created} == {str(expected)}


@pytest.mark.covers(
    "aurelius_atlas_db_scanner.scan.run_scan",
    "aurelius_atlas_db_scanner.graph.build_graph",
    rules=["DBS-09"],
)
async def test__a_second_scan_updates_the_same_entities_in_place(
    scanner: AtlasClient,
    writer: AtlasClient,
    scanner_settings: ScannerSettings,
    seeded_database: dict[str, str],
    cleanup: Seeded,
    run_token: str,
) -> None:
    """A re-scan is idempotent on the real store (DBS-09): the same guid, no duplicates.

    The dataset resolves by its unique qualified name: the second run updates the first's
    entity in place (EWR-11's resolve, EWR-08's skip of the unchanged tree), and the store
    still answers exactly one dataset for the name.
    """
    schema_a = seeded_database["schema_a"]
    settings = _run_settings(scanner_settings, run_token)

    await _scan(scanner, settings, cleanup)
    qn = _dataset_qn(run_token, schema_a, "orders")
    entity = await _wait_for(writer, "m4i_dataset", qn)
    first_guid = str(entity.guid)

    await _scan(scanner, settings, cleanup)
    found = await writer.entity.entities_by_unique_attributes("m4i_dataset", [{"qualifiedName": qn}])
    entities = found.entities or []
    assert len(entities) == 1, f"the re-scan duplicated the dataset: {entities}"
    assert str(entities[0].guid) == first_guid, "the re-scan replaced the dataset"


@pytest.mark.covers("aurelius_atlas_db_scanner.__main__.run", rules=["DBS-02", "DBS-10"])
def test__a_refused_connect_exits_one_naming_host_not_password(
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
    run_token: str,
) -> None:
    """DBS-02 through the CLI: a dead database is exit 1, host named, password scrubbed.

    The DSN rides the environment as it does in production (DD-506: never a flag); the
    failure message is the door's, rendered with SQLAlchemy's own scrubbing — the refused
    DSN's password appears nowhere the job reports. The identity the run carries is the real
    one from the project environment, so only the database is missing.
    """
    monkeypatch.setenv(f"{ENV_PREFIX}DSN", DEAD_DSN)
    code = run(["--system-name", f"zz{run_token} Dead", "--connect-timeout-seconds", "1"])
    assert code == EXIT_FAILURE
    assert "127.0.0.1:1" in caplog.text
    assert "sup3r-s3cret" not in caplog.text
