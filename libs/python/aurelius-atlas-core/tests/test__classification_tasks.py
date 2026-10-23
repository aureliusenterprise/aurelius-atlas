"""Propagation tasks (TSK-02 to TSK-08) on the in-memory documents.

Lineage: ``p1`` reads ``a`` and writes ``b``, ``p2`` reads ``b`` and writes ``c``. The tasks recorded and what they
do are read from ``EntityGraphMapper`` (``addClassifications``, ``updateClassifications``, ``deleteClassification``,
``propagateClassification``, ``deleteClassificationPropagation``), ``DeleteHandlerV1`` (``addTagPropagation``,
``deleteAllClassifications``, ``createAndQueueTask``), ``AtlasRelationshipStoreV2#updateTagPropagations``,
``TaskExecutor`` and ``AbstractTask`` of Apache Atlas 2.4.0.
"""

from typing import Any

import pytest
from aurelius_atlas_core.entity_classifications import EntityClassifications
from aurelius_atlas_core.entity_retriever import EntityRetriever
from aurelius_atlas_core.entity_store import EntityStore, TaskChange
from aurelius_atlas_core.entity_writer import EntityWriter
from aurelius_atlas_core.relationship_store import RelationshipStore
from aurelius_atlas_core.stored_task import StoredTask
from aurelius_atlas_core.task_management import TaskManagement
from aurelius_atlas_core.testing.entity_samples import sample_registry
from aurelius_atlas_core.testing.memory import MemoryEntityDocuments
from aurelius_atlas_model.errors import AtlasError, AtlasErrorCode
from aurelius_atlas_model.instance import AtlasClassification, AtlasEntitiesWithExtInfo, AtlasRelationship
from aurelius_atlas_model.tasks import TaskStatus

P = "aurelius_atlas_core.tag_propagation.TagPropagation"
C = "aurelius_atlas_core.entity_classifications.EntityClassifications"
T = "aurelius_atlas_core.task_management.TaskManagement"
K = "aurelius_atlas_core.classification_tasks.ClassificationTasks"
ADD = "CLASSIFICATION_PROPAGATION_ADD"
DELETE = "CLASSIFICATION_PROPAGATION_DELETE"
UPDATE = "CLASSIFICATION_PROPAGATION_RELATIONSHIP_UPDATE"


@pytest.fixture
def store() -> EntityStore:
    """A store of the sample, write and classification types."""
    return EntityStore(sample_registry(classifications=True), MemoryEntityDocuments())


GUIDS: dict[str, str] = {}
FLOWS: dict[str, str] = {}


@pytest.fixture(autouse=True)
def _guids() -> None:
    GUIDS.clear()
    FLOWS.clear()


def ref(name: str) -> dict[str, Any]:
    """An object id of a ``p_data`` entity by name: its GUID, or its request GUID ``-name``."""
    return {"guid": GUIDS.get(name, f"-{name}"), "typeName": "p_data"}


def data(name: str, *classifications: dict[str, Any]) -> dict[str, Any]:
    """A ``p_data`` entity named ``name``."""
    return {
        "typeName": "p_data",
        "guid": f"-{name}",
        "attributes": {"qualifiedName": name},
        "classifications": list(classifications),
    }


def process(name: str, reads: list[str], writes: list[str]) -> dict[str, Any]:
    """A ``p_process`` reading and writing ``p_data`` entities by name."""
    return {
        "typeName": "p_process",
        "guid": f"-{name}",
        "attributes": {"qualifiedName": name},
        "relationshipAttributes": {"inputs": [ref(r) for r in reads], "outputs": [ref(w) for w in writes]},
    }


async def create(store: EntityStore, *entities: dict[str, Any], tasks: bool = False) -> None:
    """Create the entities; their GUIDs in ``GUIDS`` by name."""
    created = await EntityWriter(store, tasks=tasks).create_or_update(
        AtlasEntitiesWithExtInfo.model_validate({"entities": list(entities)})
    )
    GUIDS.update({key.removeprefix("-"): value for key, value in (created.guid_assignments or {}).items()})


async def chain(store: EntityStore) -> None:
    """``a -> p1 -> b -> p2 -> c`` and ``p3`` apart; the relationships in ``FLOWS`` as ``a.p1``, …."""
    await create(store, data("a"), data("b"), data("c"), process("p1", ["a"], ["b"]), process("p2", ["b"], ["c"]))
    await create(store, process("p3", [], []))
    by_guid = {guid: key for key, guid in GUIDS.items()}
    for name in ("p1", "p2"):
        found = await store.get(GUIDS[name])
        assert found is not None
        for relationship in (await store.get_relationships(found.entity.relationship_guids or [])).values():
            ends = relationship.relationship.ends()
            FLOWS[f"{by_guid[ends[0]]}.{by_guid[ends[1]]}"] = relationship.relationship.guid


async def names(store: EntityStore, name: str) -> list[str | None]:
    """The classification type names entity ``name`` lists."""
    return [c.type_name for c in await EntityClassifications(store).get_classifications(GUIDS[name])]


async def pending(store: EntityStore, name: str) -> list[str]:
    """The ``pendingTasks`` of entity ``name`` as it reads."""
    entity = (await EntityRetriever(store).entity_with_ext_info(GUIDS[name])).entity
    return [] if entity is None else entity.pending_tasks or []


def tag(type_name: str = "c_pii", **more: Any) -> AtlasClassification:  # noqa: ANN401 - Atlas JSON
    """A classification as a request gives it."""
    return AtlasClassification.model_validate({"typeName": type_name, **more})


async def tasks(store: EntityStore) -> list[tuple[str | None, dict[str, Any]]]:
    """Each task's type and parameters, oldest first."""
    return [(task.type, task.parameters or {}) for task in await TaskManagement(store).get_all()]


@pytest.mark.covers(
    f"{P}.queue",
    f"{P}.propagate",
    f"{P}.tasks",
    f"{P}.deferred",
    f"{P}.unqueue",
    f"{C}.add_classifications",
    f"{T}.run_pending",
    f"{K}.run",
    "aurelius_atlas_core.entity_store.EntityStore.list_tasks",
    "aurelius_atlas_core.stored_task.StoredTask.to_task",
    rules=["TSK-02", "TSK-04", "TSK-05", "TSK-07"],
)
async def test__an_added_classification_propagates_once_its_task_runs(store: EntityStore) -> None:
    """``c_pii`` on ``a`` is on ``a`` at once; an ``ADD`` task, listed by ``a``, takes it downstream."""
    await chain(store)
    woken: list[bool] = []
    store.task_listeners.append(lambda: woken.append(True))

    await EntityClassifications(store, user="jo", tasks=True).add_classifications(GUIDS["a"], [tag()])
    instance = (await store.get(GUIDS["a"]) or pytest.fail("no a")).entity.classification_guids or []
    recorded = (await TaskManagement(store).get_all())[0]
    before = (await names(store, "a"), await names(store, "c"), await pending(store, "a"))
    ran = await TaskManagement(store).run_pending()

    assert before == (["c_pii"], [], [recorded.guid])
    assert (recorded.type, recorded.status, recorded.created_by, recorded.attempt_count) == (
        ADD,
        TaskStatus.PENDING,
        "jo",
        0,
    )
    assert recorded.parameters == {
        "entityGuid": GUIDS["a"],
        "classificationVertexId": instance[0],
        "classificationName": "c_pii",
        "relationshipGuid": None,
    }
    assert woken == [True]
    assert ran == 1
    assert [await names(store, n) for n in ("p1", "b", "p2", "c")] == [["c_pii"]] * 4
    assert await pending(store, "a") == []
    assert await TaskManagement(store).get_all() == []


@pytest.mark.covers(
    f"{P}.withdraw",
    f"{C}.update_classifications",
    f"{C}.delete_classification",
    rules=["TSK-02", "TSK-04"],
)
async def test__propagate_off_and_on_and_a_delete_record_tasks(store: EntityStore) -> None:
    """``propagate`` false records ``DELETE``, true ``ADD``, a delete ``DELETE``; each moves it when it runs."""
    await chain(store)
    classifier = EntityClassifications(store, tasks=True)
    manager = TaskManagement(store)
    await classifier.add_classifications(GUIDS["a"], [tag()])
    await manager.run_pending()

    await classifier.update_classifications(GUIDS["a"], [tag(propagate=False)])
    off = ([t for t, _ in await tasks(store)], await names(store, "c"))
    await manager.run_pending()
    run_off = await names(store, "c")
    await classifier.update_classifications(GUIDS["a"], [tag(propagate=True)])
    on = [t for t, _ in await tasks(store)]
    await manager.run_pending()
    run_on = await names(store, "c")
    await classifier.delete_classification(GUIDS["a"], "c_pii")
    deleted = ([t for t, _ in await tasks(store)], await names(store, "a"), await names(store, "c"))
    await manager.run_pending()

    assert off == ([DELETE], ["c_pii"])
    assert (run_off, on, run_on) == ([], [ADD], ["c_pii"])
    assert deleted == ([DELETE], [], ["c_pii"])
    assert await names(store, "c") == []
    assert not await store.type_in_use("c_pii")


@pytest.mark.covers(f"{C}.delete_classification", rules=["TSK-03"])
async def test__a_classification_with_a_pending_task_cannot_be_deleted(store: EntityStore) -> None:
    """While ``a``'s ``ADD`` waits, deleting ``c_pii`` fails; once it ran, the delete goes ahead."""
    await chain(store)
    classifier = EntityClassifications(store, tasks=True)
    await classifier.add_classifications(GUIDS["a"], [tag()])
    instance = ((await store.get(GUIDS["a"]) or pytest.fail("no a")).entity.classification_guids or [])[0]

    with pytest.raises(AtlasError) as waiting:
        await classifier.delete_classification(GUIDS["a"], "c_pii")
    await TaskManagement(store).run_pending()
    await classifier.delete_classification(GUIDS["a"], "c_pii")

    assert (waiting.value.code, waiting.value.message) == (
        AtlasErrorCode.DELETE_TAG_PROPAGATION_NOT_ALLOWED,
        (
            "Classification delete is not allowed; Add/Update classification propagation is in progress for "
            f"classification: {instance} and entity: {GUIDS['a']}. Please try again"
        ),
    )
    assert await names(store, "a") == []


@pytest.mark.covers(
    f"{P}.relationship_created", "aurelius_atlas_core.entity_writer.EntityWriter.create_or_update", rules=["TSK-02"]
)
async def test__a_new_relationship_and_a_new_classified_entity_record_add_tasks(store: EntityStore) -> None:
    """``c`` read by ``p3`` records an ``ADD`` on ``p3`` with the relationship; ``e`` created classified, on ``e``."""
    await chain(store)
    await EntityClassifications(store).add_classifications(GUIDS["a"], [tag()])

    created = await RelationshipStore(store, tasks=True).create(
        AtlasRelationship.model_validate(
            {"typeName": "p_input", "end1": {"guid": GUIDS["c"]}, "end2": {"guid": GUIDS["p3"]}}
        )
    )
    await create(store, data("e", {"typeName": "c_secret"}), process("p4", ["e"], []), tasks=True)
    recorded = await tasks(store)
    before = await names(store, "p3"), await names(store, "p4")
    await TaskManagement(store).run_pending()

    assert [(t, p["entityGuid"], p["relationshipGuid"]) for t, p in recorded] == [
        (ADD, GUIDS["p3"], created.guid),
        (ADD, GUIDS["e"], None),
    ]
    assert before == ([], [])
    assert (await names(store, "p3"), await names(store, "p4")) == (["c_pii"], ["c_secret"])


@pytest.mark.covers(
    f"{P}.defer_update", "aurelius_atlas_core.relationship_store.RelationshipStore.update", rules=["TSK-02"]
)
async def test__a_relationship_update_changes_propagation_when_its_task_runs(store: EntityStore) -> None:
    """``a.p1`` set to ``NONE`` keeps ``ONE_TO_TWO`` and the propagation until its task runs."""
    await chain(store)
    await EntityClassifications(store).add_classifications(GUIDS["a"], [tag()])
    relationships = RelationshipStore(store, tasks=True)

    answered = await relationships.update(
        AtlasRelationship.model_validate({"guid": FLOWS["a.p1"], "propagateTags": "NONE"})
    )
    recorded = await tasks(store)
    guids = [task.guid for task in await TaskManagement(store).get_all()]
    listed = (await store.get_relationships([FLOWS["a.p1"]]))[FLOWS["a.p1"]].relationship.pending_tasks
    before = await names(store, "c")
    await TaskManagement(store).run_pending()
    after = await relationships.get_by_id(FLOWS["a.p1"])

    assert answered.propagate_tags == "ONE_TO_TWO"
    assert [(t, p["relationshipEdgeId"]) for t, p in recorded] == [(UPDATE, FLOWS["a.p1"])]
    assert '"propagateTags":"NONE"' in recorded[0][1]["relationshipObject"]
    assert listed == guids
    assert before == ["c_pii"]
    assert after.propagate_tags == "NONE"
    assert await names(store, "c") == []
    assert (await store.get_relationships([FLOWS["a.p1"]]))[FLOWS["a.p1"]].relationship.pending_tasks is None


@pytest.mark.covers("aurelius_atlas_core.delete_handler.DeleteHandler.delete_entities", rules=["TSK-02", "TSK-04"])
async def test__an_entity_deleted_with_a_classification_that_removes_propagations_records_a_delete(
    store: EntityStore,
) -> None:
    """Deleting ``a`` with ``c_secret`` keeps it downstream until the ``DELETE`` task runs; ``a`` keeps it listed."""
    await chain(store)
    await EntityClassifications(store).add_classifications(
        GUIDS["a"], [tag("c_secret", removePropagationsOnEntityDelete=True)]
    )

    await EntityWriter(store, tasks=True).delete_by_id(GUIDS["a"])
    recorded = [t for t, _ in await tasks(store)]
    before = (await names(store, "c"), await pending(store, "a"))
    await TaskManagement(store).run_pending()

    assert (recorded, before[0], len(before[1])) == ([DELETE], ["c_secret"], 1)
    assert await names(store, "c") == []
    assert await names(store, "a") == ["c_secret"]
    assert await pending(store, "a") == []


@pytest.mark.covers(f"{K}.run", rules=["TSK-04"])
async def test__a_task_whose_classification_is_gone_does_nothing(store: EntityStore) -> None:
    """An ``ADD`` and a ``DELETE`` of an instance that no longer exists, and an update of a gone relationship."""
    await chain(store)
    for n, (task_type, parameters) in enumerate(
        [
            (ADD, {"entityGuid": GUIDS["a"], "classificationVertexId": "gone"}),
            (ADD, {"entityGuid": "gone", "classificationVertexId": "gone"}),
            (DELETE, {"entityGuid": GUIDS["a"], "classificationVertexId": "gone"}),
            (UPDATE, {"relationshipEdgeId": "gone", "relationshipObject": "{}"}),
        ]
    ):
        await store.write([], [], [], [TaskChange(StoredTask(guid=f"t{n}", type=task_type, parameters=parameters))])

    assert await TaskManagement(store).run_pending() == 4
    assert await TaskManagement(store).get_all() == []


@pytest.mark.covers(f"{T}.run_pending", rules=["TSK-05"])
async def test__a_failing_task_is_tried_three_times_then_failed(store: EntityStore) -> None:
    """Each failure counts an attempt and keeps the message; the third makes it ``FAILED``, never run again."""
    await chain(store)
    await store.write(
        [], [], [], [TaskChange(StoredTask(guid="t", type="NOPE", parameters={"entityGuid": GUIDS["a"]}))]
    )
    manager = TaskManagement(store)

    states = []
    for _ in range(4):
        await manager.run_pending()
        found = (await manager.get_by_guids(["t"]))[0]
        states.append((found.status, found.attempt_count))

    assert states == [
        (TaskStatus.PENDING, 1),
        (TaskStatus.PENDING, 2),
        (TaskStatus.FAILED, 3),
        (TaskStatus.FAILED, 3),
    ]
    assert (await manager.get_by_guids(["t"]))[0].error_message == "unknown task type: NOPE"


@pytest.mark.covers(f"{T}.run_pending", rules=["TSK-04"])
async def test__a_task_claimed_by_another_runs_only_once_its_lease_passed(store: EntityStore) -> None:
    """``IN_PROGRESS`` with a lease ahead is left alone; one whose lease passed is claimed again (DD-080)."""
    now = store.now()
    for guid, until in (("held", now + 60_000), ("stale", now - 1)):
        await store.write(
            [],
            [],
            [],
            [
                TaskChange(
                    StoredTask(
                        guid=guid,
                        type=ADD,
                        status=TaskStatus.IN_PROGRESS,
                        claimed_until=until,
                        parameters={"entityGuid": "gone", "classificationVertexId": "gone"},
                    )
                )
            ],
        )

    assert await TaskManagement(store).run_pending() == 1
    assert [task.guid for task in await TaskManagement(store).get_all()] == ["held"]


@pytest.mark.covers(
    f"{T}.get_all",
    f"{T}.get_by_guids",
    f"{T}.delete_by_guids",
    "aurelius_atlas_core.entity_store.EntityStore.get_tasks",
    rules=["TSK-06"],
)
async def test__tasks_are_listed_by_guid_and_removed(store: EntityStore) -> None:
    """All oldest first; by GUIDs in their order, unknown ones left out; removed ones are gone."""
    for guid, created in (("y", 2), ("x", 1), ("z", 3)):
        await store.write([], [], [], [TaskChange(StoredTask(guid=guid, type=ADD, created_time=created))])
    manager = TaskManagement(store)

    every = [task.guid for task in await manager.get_all()]
    some = [task.guid for task in await manager.get_by_guids(["z", "nope", "x"])]
    await manager.delete_by_guids(["x", "nope"])
    await manager.delete_by_guids(["nope"])

    assert (every, some) == (["x", "y", "z"], ["z", "x"])
    assert [task.guid for task in await manager.get_all()] == ["y", "z"]


@pytest.mark.covers(f"{C}.add_classifications", rules=["TSK-08"])
async def test__without_tasks_propagation_happens_in_the_request(store: EntityStore) -> None:
    """Tasks disabled, ``c`` has ``c_pii`` at once and no task is recorded."""
    await chain(store)

    await EntityClassifications(store).add_classifications(GUIDS["a"], [tag()])

    assert await names(store, "c") == ["c_pii"]
    assert await TaskManagement(store).get_all() == []
