"""An import holds the tasks it records until it ends (IMT-01 to IMT-03, DD-361), on the in-memory documents.

A classified table and its database are exported from one catalogue and imported into another with tasks enabled;
the workers' turns are taken between the import's writes, where the race of DD-361 happened.
"""

import json
from typing import Any

import pytest
from aurelius_atlas_core import task_hold
from aurelius_atlas_core.entity_classifications import EntityClassifications
from aurelius_atlas_core.entity_store import EntityStore, EntityVersionConflictError, TaskChange
from aurelius_atlas_core.entity_writer import EntityWriter
from aurelius_atlas_core.export_service import ExportService
from aurelius_atlas_core.import_service import ImportService
from aurelius_atlas_core.model_loader import BUILTIN_MODELS_DIR
from aurelius_atlas_core.stored_task import StoredTask
from aurelius_atlas_core.task_hold import TaskHold, held
from aurelius_atlas_core.task_management import TaskManagement
from aurelius_atlas_core.testing.memory import MemoryEntityDocuments, MemoryTypedefDocument
from aurelius_atlas_core.typedef_store import TypedefStore
from aurelius_atlas_core.zip_sink import ZipSink
from aurelius_atlas_model.errors import AtlasError, AtlasErrorCode
from aurelius_atlas_model.impexp import AtlasExportRequest, AtlasImportRequest
from aurelius_atlas_model.instance import AtlasEntitiesWithExtInfo, AtlasEntityWithExtInfo, EntityMutationResponse
from aurelius_atlas_model.typedef import AtlasTypesDef
from aurelius_atlas_typesystem.registry import TypeRegistry

H = "aurelius_atlas_core.task_hold"
BASE = json.loads((BUILTIN_MODELS_DIR / "0000-Area0" / "0010-base_model.json").read_text(encoding="utf-8"))
TYPES = {
    "classificationDefs": [{"name": "PII"}],
    "entityDefs": [{"name": "hold_db", "superTypes": ["Asset"]}, {"name": "hold_table", "superTypes": ["DataSet"]}],
    "relationshipDefs": [
        {
            "name": "hold_table_db",
            "relationshipCategory": "ASSOCIATION",
            "propagateTags": "ONE_TO_TWO",
            "endDef1": {"type": "hold_table", "name": "db", "cardinality": "SINGLE"},
            "endDef2": {"type": "hold_db", "name": "tables", "cardinality": "SET"},
        }
    ],
}


class Clock:
    """A clock the test moves, in seconds as ``time.time``."""

    def __init__(self) -> None:
        self.now = 1_000.0

    def __call__(self) -> float:
        """The time now."""
        return self.now


async def catalogue(*models: dict[str, Any], clock: Clock | None = None) -> tuple[EntityStore, TypedefStore]:
    """An entity store and its typedef store, of these models."""
    types = TypedefStore(TypeRegistry(), MemoryTypedefDocument())
    await types.load()
    for model in models:
        await types.create_types_def(AtlasTypesDef.model_validate(model))
    return EntityStore(types.registry, MemoryEntityDocuments(), clock=clock or Clock()), types


@pytest.fixture
async def exported() -> tuple[bytes, dict[str, str]]:
    """The ZIP of an export of a table classified ``PII``, which propagates to its database, and their GUIDs."""
    store, _ = await catalogue(BASE, TYPES)
    entities = [
        {"typeName": "hold_db", "guid": "-1", "attributes": {"qualifiedName": "d", "name": "d"}},
        {
            "typeName": "hold_table",
            "guid": "-2",
            "attributes": {"qualifiedName": "t", "name": "t"},
            "classifications": [{"typeName": "PII", "propagate": True}],
            "relationshipAttributes": {"db": {"typeName": "hold_db", "guid": "-1"}},
        },
    ]
    created = await EntityWriter(store).create_or_update(
        AtlasEntitiesWithExtInfo.model_validate({"entities": entities})
    )
    guids = {"db": (created.guid_assignments or {})["-1"], "table": (created.guid_assignments or {})["-2"]}
    sink = ZipSink()
    request = AtlasExportRequest.model_validate({"itemsToExport": [{"guid": guids["table"]}]})
    await ExportService(store).run(sink, request, "exporter", "h", "ip")
    return sink.close(), guids


class Turns:
    """The workers' turns, taken after each entity the import writes: what they ran, and the tasks then held."""

    def __init__(self, store: EntityStore, writer: EntityWriter, *, fail_at: int | None = None) -> None:
        self.ran: list[int] = []
        self.held: list[bool] = []
        self._store = store
        self._write = writer.create_or_update_for_import
        self._fail_at = fail_at
        writer.create_or_update_for_import = self._turn

    async def _turn(self, found: AtlasEntityWithExtInfo) -> EntityMutationResponse:
        response = await self._write(found)
        self.held += [task.held_by is not None for task, _ in await self._store.list_tasks(open_only=True)]
        self.ran.append(await TaskManagement(self._store).run_pending())
        if len(self.ran) == self._fail_at:
            raise AtlasError(AtlasErrorCode.INTERNAL_ERROR, "the import stops here")
        return response


async def classified(store: EntityStore, guid: str) -> list[str | None]:
    """The classification type names the entity lists, its own and propagated."""
    return [c.type_name for c in await EntityClassifications(store).get_classifications(guid)]


@pytest.mark.covers(
    "aurelius_atlas_core.import_service.ImportService.run",
    "aurelius_atlas_core.entity_writer.EntityWriter.hold_tasks",
    "aurelius_atlas_core.entity_writer.EntityWriter.defers_tasks",
    f"{H}.TaskHold.start",
    f"{H}.TaskHold.holds",
    f"{H}.TaskHold.release",
    f"{H}.held",
    rules=["IMT-01", "IMT-02"],
)
async def test__an_import_holds_its_tasks_until_it_ends(exported: tuple[bytes, dict[str, str]]) -> None:
    """No worker runs a task the import records while it runs; they are released and run once it ends."""
    content, guids = exported
    store, types = await catalogue(BASE)
    woken: list[None] = []
    store.task_listeners.append(lambda: woken.append(None))
    writer = EntityWriter(store, user="importer", tasks=True)
    turns = Turns(store, writer)

    found = await ImportService(store, types, writer).run(content, AtlasImportRequest(), "importer", "h", "ip")
    waiting = await store.list_tasks(open_only=True)

    assert found.operation_status.value == "SUCCESS"
    assert turns.ran == [0, 0]
    assert turns.held
    assert all(turns.held)
    assert waiting
    assert all(task.held_by is None and task.held_until is None for task, _ in waiting)
    assert woken
    assert await classified(store, guids["db"]) == []
    assert await TaskManagement(store).run_pending() == len(waiting)
    assert await classified(store, guids["db"]) == ["PII"]


@pytest.mark.covers("aurelius_atlas_core.import_service.ImportService.run", f"{H}.TaskHold.release", rules=["IMT-02"])
async def test__an_import_that_fails_releases_what_it_held(exported: tuple[bytes, dict[str, str]]) -> None:
    """The tasks of the entities written before the failure run as any other; the next import holds none."""
    content, guids = exported
    store, types = await catalogue(BASE)
    writer = EntityWriter(store, user="importer", tasks=True)
    Turns(store, writer, fail_at=2)

    with pytest.raises(AtlasError, match="the import stops here"):
        await ImportService(store, types, writer).run(content, AtlasImportRequest(), "importer", "h", "ip")
    waiting = await store.list_tasks(open_only=True)

    assert waiting
    assert all(task.held_by is None for task, _ in waiting)
    assert await TaskManagement(store).run_pending() == len(waiting)
    assert await classified(store, guids["db"]) == ["PII"]


@pytest.mark.covers(f"{H}.held", "aurelius_atlas_core.task_management.TaskManagement.run_pending", rules=["IMT-03"])
async def test__a_hold_that_passed_holds_no_more() -> None:
    """A task held is not claimed; once the hold has passed it is claimed and run as any other."""
    clock = Clock()
    store, _ = await catalogue(BASE, clock=clock)
    hold = TaskHold.start(store)
    task = StoredTask(guid="t", type="UNKNOWN", held_by=hold.id, held_until=hold.until)
    await store.write([], [], [], [TaskChange(task)])

    before = await TaskManagement(store).run_pending()
    untouched = (await store.get_tasks(["t"]))["t"][0]
    clock.now += task_hold.HOLD_MILLISECONDS / 1000 + 1
    after = await TaskManagement(store).run_pending()
    tried = (await store.get_tasks(["t"]))["t"][0]

    assert held(untouched, store.now() - task_hold.HOLD_MILLISECONDS)
    assert not held(untouched, store.now())
    assert (before, untouched.attempt_count) == (0, 0)
    assert (after, tried.attempt_count) == (0, 1)


@pytest.mark.covers(f"{H}.TaskHold.release", rules=["IMT-02"])
async def test__a_release_that_loses_a_race_releases_the_rest(monkeypatch: pytest.MonkeyPatch) -> None:
    """A batch whose write loses is released task by task; a task changed since it was listed is passed over."""
    store, _ = await catalogue(BASE)
    hold = TaskHold.start(store)
    other = TaskHold.start(store)
    tasks = [StoredTask(guid=f"t{n}", type="UNKNOWN", held_by=hold.id, held_until=hold.until) for n in range(3)]
    mine_not = StoredTask(guid="o", type="UNKNOWN", held_by=other.id, held_until=other.until)
    await store.write([], [], [], [TaskChange(task) for task in [*tasks, mine_not]])
    woken: list[None] = []
    store.task_listeners.append(lambda: woken.append(None))
    monkeypatch.setattr(task_hold, "RELEASE_BATCH", 2)
    write = store.write

    async def racing(*changes: Any, **kwargs: Any) -> None:  # noqa: ANN401 - EntityStore.write's arguments
        released = [change.task.guid for change in changes[3]]
        if len(released) > 1 or released == ["t1"]:
            raise EntityVersionConflictError(released[0])
        await write(*changes, **kwargs)

    monkeypatch.setattr(store, "write", racing)

    count = await hold.release(store)
    found = await store.get_tasks(["t0", "t1", "t2", "o"])

    assert count == 2
    assert [found[guid][0].held_by is None for guid in ("t0", "t1", "t2")] == [True, False, True]
    assert found["o"][0].held_by == other.id
    assert woken == [None]


@pytest.mark.covers(
    "aurelius_atlas_core.entity_classifications.EntityClassifications.delete_classification", rules=["IMT-04"]
)
async def test__an_import_may_delete_a_classification_whose_task_it_holds() -> None:
    """The task the import holds is no refusal for it; for another request it still is (TSK-03)."""
    store, _ = await catalogue(BASE, TYPES)
    hold = TaskHold.start(store)
    writer = EntityWriter(store, user="importer", tasks=True)
    writer.hold_tasks(hold)
    pii = [{"typeName": "PII", "propagate": True}]
    entities = [
        {"typeName": "hold_db", "guid": "-1", "attributes": {"qualifiedName": n, "name": n}, "classifications": pii}
        for n in ("mine", "theirs")
    ]
    entities[1]["guid"] = "-2"
    created = await writer.create_or_update(AtlasEntitiesWithExtInfo.model_validate({"entities": entities}))
    mine, theirs = ((created.guid_assignments or {})[key] for key in ("-1", "-2"))

    await EntityClassifications(store, tasks=True, hold=hold).delete_classification(mine, "PII")
    with pytest.raises(AtlasError) as refused:
        await EntityClassifications(store, tasks=True).delete_classification(theirs, "PII")

    assert await classified(store, mine) == []
    assert refused.value.code is AtlasErrorCode.DELETE_TAG_PROPAGATION_NOT_ALLOWED
