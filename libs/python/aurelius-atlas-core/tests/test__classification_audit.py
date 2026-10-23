"""Classification audit (CAU-01 to CAU-07) on the in-memory documents and repository.

Lineage: ``p1`` reads ``a`` and writes ``b``. The events are read from ``EntityGraphMapper``
(``addClassifications``, ``updateClassifications``, ``deleteClassification``, ``propagateClassification``,
``deleteClassificationPropagation``), ``AtlasEntityChangeNotifier`` (``notifyPropagatedEntities``),
``DeleteHandlerV1`` and ``EntityAuditListenerV2`` of Apache Atlas 2.4.0.
"""

import itertools
from typing import Any

import pytest
from aurelius_atlas_core.classification_associator import ClassificationRetriever
from aurelius_atlas_core.delete_type import DeleteType
from aurelius_atlas_core.entity_audit_listener import EntityAuditListener
from aurelius_atlas_core.entity_change_notifier import EntityChangeNotifier
from aurelius_atlas_core.entity_classifications import EntityClassifications
from aurelius_atlas_core.entity_store import EntityStore
from aurelius_atlas_core.entity_writer import EntityWriter
from aurelius_atlas_core.relationship_store import RelationshipStore
from aurelius_atlas_core.task_management import TaskManagement
from aurelius_atlas_core.testing.entity_samples import sample_registry
from aurelius_atlas_core.testing.memory import InMemoryEntityAuditRepository, MemoryEntityDocuments
from aurelius_atlas_model import codec
from aurelius_atlas_model.instance import AtlasClassification, AtlasEntitiesWithExtInfo, AtlasRelationship

N = "aurelius_atlas_core.entity_change_notifier.EntityChangeNotifier"
L = "aurelius_atlas_core.entity_audit_listener.EntityAuditListener"
C = "aurelius_atlas_core.entity_classifications.EntityClassifications"
ADD, PADD = "CLASSIFICATION_ADD", "PROPAGATED_CLASSIFICATION_ADD"
UPDATE, PUPDATE = "CLASSIFICATION_UPDATE", "PROPAGATED_CLASSIFICATION_UPDATE"
DELETE, PDELETE = "CLASSIFICATION_DELETE", "PROPAGATED_CLASSIFICATION_DELETE"


@pytest.fixture
def audits() -> InMemoryEntityAuditRepository:
    """The events recorded."""
    return InMemoryEntityAuditRepository()


@pytest.fixture
def store() -> EntityStore:
    """A store of the classification types whose clock ticks one millisecond per reading."""
    ticks = itertools.count(1000)
    return EntityStore(sample_registry(classifications=True), MemoryEntityDocuments(), clock=lambda: next(ticks) / 1000)


@pytest.fixture
def notifier(store: EntityStore, audits: InMemoryEntityAuditRepository) -> EntityChangeNotifier:
    """A notifier recording audit events."""
    return EntityChangeNotifier(store, [EntityAuditListener(audits, store.now)])


GUIDS: dict[str, str] = {}


@pytest.fixture(autouse=True)
def _guids() -> None:
    GUIDS.clear()


def data(name: str, *classifications: dict[str, Any]) -> dict[str, Any]:
    """A ``p_data`` entity named ``name``."""
    return {
        "typeName": "p_data",
        "guid": GUIDS.get(name, f"-{name}"),
        "attributes": {"qualifiedName": name},
        "classifications": list(classifications),
    }


def process(name: str, reads: list[str], writes: list[str]) -> dict[str, Any]:
    """A ``p_process`` reading and writing ``p_data`` entities by name."""

    def ref(other: str) -> dict[str, Any]:
        return {"guid": GUIDS.get(other, f"-{other}"), "typeName": "p_data"}

    return {
        "typeName": "p_process",
        "guid": GUIDS.get(name, f"-{name}"),
        "attributes": {"qualifiedName": name},
        "relationshipAttributes": {"inputs": [ref(r) for r in reads], "outputs": [ref(w) for w in writes]},
    }


async def create(writer: EntityWriter, *entities: dict[str, Any]) -> None:
    """Create the entities; their GUIDs in ``GUIDS`` by name."""
    created = await writer.create_or_update(AtlasEntitiesWithExtInfo.model_validate({"entities": list(entities)}))
    GUIDS.update({key.removeprefix("-"): value for key, value in (created.guid_assignments or {}).items()})


async def lineage(store: EntityStore) -> None:
    """``a -> p1 -> b`` and ``p3`` apart, created without audit."""
    await create(EntityWriter(store), data("a"), data("b"), process("p1", ["a"], ["b"]), process("p3", [], []))


async def events(audits: InMemoryEntityAuditRepository, name: str) -> list[tuple[str | None, str]]:
    """Entity ``name``'s classification events, oldest first: action and details."""
    found = await audits.list_events(GUIDS[name], None, None, -1)
    return [(e.action, e.details or "") for e in reversed(found) if "CLASSIFICATION" in str(e.action)]


async def actions(audits: InMemoryEntityAuditRepository, name: str) -> list[str | None]:
    """Entity ``name``'s actions, oldest first."""
    return [e.action for e in reversed(await audits.list_events(GUIDS[name], None, None, -1))]


def tag(type_name: str = "c_pii", **more: Any) -> AtlasClassification:  # noqa: ANN401 - Atlas JSON
    """A classification as a request gives it."""
    return AtlasClassification.model_validate({"typeName": type_name, **more})


@pytest.mark.covers(
    f"{N}.on_classifications_added",
    f"{L}.on_classifications_added",
    f"{C}.add_classifications",
    rules=["CAU-01", "CAU-02"],
)
async def test__an_added_classification_is_recorded_on_its_entity_and_where_it_propagated(
    store: EntityStore, audits: InMemoryEntityAuditRepository, notifier: EntityChangeNotifier
) -> None:
    """``a`` an add with the classification's JSON, ``p1`` and ``b`` a propagated add; ``p3`` nothing."""
    await lineage(store)

    await EntityClassifications(store, user="jo", notifier=notifier).add_classifications(
        GUIDS["a"], [tag(attributes={"level": 2})]
    )
    (action, details), *_ = await events(audits, "a")
    added = codec.loads(details.removeprefix("Added classification: "))

    assert action == ADD
    assert (added["typeName"], added["entityGuid"], added["attributes"]["level"]) == ("c_pii", GUIDS["a"], 2)
    assert [a for a, _ in await events(audits, "p1")] == [PADD]
    assert (await events(audits, "b"))[0][1].startswith('Added propagated classification: {"typeName":"c_pii"')
    assert await events(audits, "p3") == []
    assert {e.user for e in audits.events} == {"jo"}


@pytest.mark.covers(
    f"{N}.on_classifications_updated",
    f"{L}.on_classifications_updated",
    f"{C}.update_classifications",
    rules=["CAU-01", "CAU-03"],
)
async def test__an_update_is_recorded_on_the_entities_it_reaches_and_propagate_moves_it(
    store: EntityStore, audits: InMemoryEntityAuditRepository, notifier: EntityChangeNotifier
) -> None:
    """Attributes: an update on ``a``, propagated updates; ``propagate`` off: deletes; on again: adds."""
    await lineage(store)
    classifier = EntityClassifications(store, notifier=notifier)
    await classifier.add_classifications(GUIDS["a"], [tag()])

    await classifier.update_classifications(GUIDS["a"], [tag(attributes={"level": 5})])
    await classifier.update_classifications(GUIDS["a"], [tag(propagate=False)])
    await classifier.update_classifications(GUIDS["a"], [tag(propagate=True)])

    assert [a for a, _ in await events(audits, "a")] == [ADD, UPDATE, UPDATE, UPDATE]
    assert [a for a, _ in await events(audits, "b")] == [PADD, PUPDATE, PDELETE, PADD]
    assert (await events(audits, "b"))[2][1] == "Deleted propagated classification: c_pii"
    assert (await events(audits, "b"))[1][1].startswith("Updated propagated classification: {")
    assert (await events(audits, "a"))[1][1].startswith("Updated classification: {")


@pytest.mark.covers(
    f"{N}.on_classifications_deleted",
    f"{L}.on_classifications_deleted",
    f"{C}.delete_classification",
    rules=["CAU-01", "CAU-04"],
)
async def test__a_deleted_classification_is_recorded_where_it_was_then_on_its_entity(
    store: EntityStore, audits: InMemoryEntityAuditRepository, notifier: EntityChangeNotifier
) -> None:
    """Deletes on ``p1`` and ``b`` and ``a``; removing a propagated one of a deleted entity records nothing."""
    await lineage(store)
    classifier = EntityClassifications(store, notifier=notifier)
    await classifier.add_classifications(GUIDS["a"], [tag(), tag("c_secret", propagate=False)])

    await classifier.delete_classification(GUIDS["a"], "c_secret")
    await classifier.delete_classification(GUIDS["a"], "c_pii")
    await classifier.add_classifications(GUIDS["a"], [tag()])
    await EntityWriter(store).delete_by_id(GUIDS["a"])
    await classifier.delete_classification(GUIDS["b"], "c_pii", GUIDS["a"])

    assert await events(audits, "a") == [
        (ADD, (await events(audits, "a"))[0][1]),
        (ADD, (await events(audits, "a"))[1][1]),
        (DELETE, "Deleted classification: c_secret"),
        (DELETE, "Deleted classification: c_pii"),
        (ADD, (await events(audits, "a"))[4][1]),
    ]
    assert [a for a, _ in await events(audits, "b")] == [PADD, PDELETE, PADD]


@pytest.mark.covers(
    f"{N}.notify_propagated_entities",
    "aurelius_atlas_core.entity_writer.EntityWriter.create_or_update",
    "aurelius_atlas_core.relationship_store.RelationshipStore.create",
    "aurelius_atlas_core.relationship_store.RelationshipStore.update",
    "aurelius_atlas_core.relationship_store.RelationshipStore.delete_by_id",
    "aurelius_atlas_core.tag_propagation.TagPropagation.add",
    "aurelius_atlas_core.tag_propagation.TagPropagation.remove",
    rules=["CAU-02", "CAU-05"],
)
async def test__relationships_and_entity_writes_record_what_they_propagated(
    store: EntityStore, audits: InMemoryEntityAuditRepository, notifier: EntityChangeNotifier
) -> None:
    """A new relationship, its update and hard delete; a create with a classification is recorded before it."""
    await lineage(store)
    await EntityClassifications(store).add_classifications(GUIDS["a"], [tag(removePropagationsOnEntityDelete=True)])
    relationships = RelationshipStore(store, notifier=notifier)

    created = await relationships.create(
        AtlasRelationship.model_validate(
            {"typeName": "p_input", "end1": {"guid": GUIDS["b"]}, "end2": {"guid": GUIDS["p3"]}}
        )
    )
    await relationships.update(AtlasRelationship.model_validate({"guid": created.guid, "propagateTags": "NONE"}))
    await relationships.update(AtlasRelationship.model_validate({"guid": created.guid, "propagateTags": "ONE_TO_TWO"}))
    await RelationshipStore(store, delete_type=DeleteType.HARD, notifier=notifier).delete_by_id(str(created.guid))
    await create(EntityWriter(store, notifier=notifier), data("e", {"typeName": "c_secret"}), process("p4", ["e"], []))

    assert [a for a, _ in await events(audits, "p3")] == [PADD, PDELETE, PADD, PDELETE]
    assert await actions(audits, "e") == [ADD, "ENTITY_CREATE"]
    assert await actions(audits, "p4") == [PADD, "ENTITY_CREATE", PADD]


@pytest.mark.covers(
    "aurelius_atlas_core.entity_writer.EntityWriter.delete_by_id",
    "aurelius_atlas_core.entity_change_notifier.RequestRecord.merge",
    rules=["CAU-05"],
)
async def test__a_delete_records_the_propagations_it_removed_but_not_on_deleted_entities(
    store: EntityStore, audits: InMemoryEntityAuditRepository, notifier: EntityChangeNotifier
) -> None:
    """Deleting ``a`` with a classification that removes propagations: deletes on ``p1`` and ``b``, none on ``a``."""
    await lineage(store)
    await EntityClassifications(store).add_classifications(GUIDS["a"], [tag(removePropagationsOnEntityDelete=True)])

    await EntityWriter(store, notifier=notifier).delete_by_id(GUIDS["a"])

    assert [a for a, _ in await events(audits, "b")] == [PDELETE]
    assert [a for a, _ in await events(audits, "p1")] == [PDELETE]
    assert await actions(audits, "a") == ["ENTITY_DELETE"]


@pytest.mark.covers(
    "aurelius_atlas_core.task_management.TaskManagement.run_pending",
    "aurelius_atlas_core.classification_tasks.ClassificationTasks.run",
    rules=["CAU-02", "CAU-06"],
)
async def test__tasks_record_what_they_propagate_and_remove(
    store: EntityStore, audits: InMemoryEntityAuditRepository, notifier: EntityChangeNotifier
) -> None:
    """With tasks the add is on ``a`` alone; the ``ADD`` task adds on ``p1`` and ``b``; ``DELETE`` deletes there."""
    await lineage(store)
    classifier = EntityClassifications(store, tasks=True, notifier=notifier)
    manager = TaskManagement(store, notifier=notifier)

    await classifier.add_classifications(GUIDS["a"], [tag()])
    before = await events(audits, "b")
    await manager.run_pending()
    await classifier.update_classifications(GUIDS["a"], [tag(propagate=False)])
    await manager.run_pending()
    relationship = next(iter((await store.get_relationships(await _listed(store, "p1"))).values())).relationship
    await RelationshipStore(store, tasks=True, notifier=notifier).update(
        AtlasRelationship.model_validate({"guid": relationship.guid, "propagateTags": "NONE"})
    )
    await manager.run_pending()

    assert before == []
    assert [a for a, _ in await events(audits, "a")] == [ADD, UPDATE]
    assert [a for a, _ in await events(audits, "b")] == [PADD, PDELETE]


async def _listed(store: EntityStore, name: str) -> list[str]:
    found = await store.get(GUIDS[name])
    return [] if found is None else list(found.entity.relationship_guids or [])


@pytest.mark.covers(
    "aurelius_atlas_core.classification_associator.ClassificationRetriever.get",
    "aurelius_atlas_core.testing.memory.InMemoryEntityAuditRepository.entities_with_tag_changes",
    rules=["CAU-07"],
)
async def test__entities_with_classification_events_in_a_time_range_are_listed(
    store: EntityStore, audits: InMemoryEntityAuditRepository, notifier: EntityChangeNotifier
) -> None:
    """Their own events count, propagated ones not; both ends included; purged entities left out."""
    await lineage(store)
    classifier = EntityClassifications(store, notifier=notifier)
    start = store.now()
    await classifier.add_classifications(GUIDS["a"], [tag()])
    await classifier.add_classifications(GUIDS["p3"], [tag("c_secret")])
    retriever = ClassificationRetriever(store, audits)
    times = sorted(e.timestamp for e in audits.events if e.action == ADD)

    every = await retriever.get(start, store.now())
    first = await retriever.get(times[0], times[0])
    await EntityWriter(store, delete_type=DeleteType.HARD).delete_by_id(GUIDS["p3"])
    after = await retriever.get(start, store.now())

    assert set(every.guid_header_map or {}) == {GUIDS["a"], GUIDS["p3"]}
    assert [c.type_name for c in (every.guid_header_map or {})[GUIDS["a"]].classifications or []] == ["c_pii"]
    assert set(first.guid_header_map or {}) == {GUIDS["a"]}
    assert set(after.guid_header_map or {}) == {GUIDS["a"]}
