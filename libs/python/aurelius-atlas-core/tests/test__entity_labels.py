"""Labels (LBL-02 to LBL-05, AUZ-16) on the in-memory documents.

Read from ``setLabels``, ``addLabels`` and ``removeLabels`` of Apache Atlas 2.4.0's ``AtlasEntityStoreV2`` and
``EntityGraphMapper``, ``AtlasEntityChangeNotifier#onLabelsUpdatedFromEntity`` and ``EntityAuditListenerV2``'s
``onLabelsAdded`` and ``onLabelsDeleted``.
"""

import itertools
from typing import Any

import pytest
from aurelius_atlas_core.authorization import AtlasPrivilege, Granted
from aurelius_atlas_core.entity_audit_listener import EntityAuditListener
from aurelius_atlas_core.entity_change_notifier import EntityChangeNotifier
from aurelius_atlas_core.entity_labels import EntityLabels
from aurelius_atlas_core.entity_store import EntityStore
from aurelius_atlas_core.entity_writer import EntityWriter
from aurelius_atlas_core.testing.entity_samples import sample_registry
from aurelius_atlas_core.testing.memory import InMemoryEntityAuditRepository, MemoryEntityDocuments
from aurelius_atlas_model.audit import EntityAuditActionV2
from aurelius_atlas_model.errors import AtlasError, AtlasErrorCode
from aurelius_atlas_model.instance import AtlasEntitiesWithExtInfo

E = "aurelius_atlas_core.entity_labels.EntityLabels"
L = "aurelius_atlas_core.entity_audit_listener.EntityAuditListener"
ADD, DELETE = EntityAuditActionV2.LABEL_ADD, EntityAuditActionV2.LABEL_DELETE


@pytest.fixture
def audits() -> InMemoryEntityAuditRepository:
    """The events recorded."""
    return InMemoryEntityAuditRepository()


@pytest.fixture
def store() -> EntityStore:
    """A store of the sample types whose clock ticks one millisecond per reading, from 1000."""
    ticks = itertools.count(1000)
    return EntityStore(sample_registry(), MemoryEntityDocuments(), clock=lambda: next(ticks) / 1000)


def notifier(store: EntityStore, audits: InMemoryEntityAuditRepository) -> EntityChangeNotifier:
    """A notifier recording audit events."""
    return EntityChangeNotifier(store, [EntityAuditListener(audits, store.now)])


def labels(store: EntityStore, audits: InMemoryEntityAuditRepository, **more: Any) -> EntityLabels:  # noqa: ANN401
    """Label changes as ``u``, audited."""
    return EntityLabels(store, user="u", notifier=notifier(store, audits), **more)


async def table(store: EntityStore, audits: InMemoryEntityAuditRepository, *given: str) -> str:
    """The GUID of a new ``s_table`` of these labels, created as ``c``."""
    entity = {"typeName": "s_table", "guid": "-1", "attributes": {"qualifiedName": "t"}, "labels": list(given)}
    writer = EntityWriter(store, user="c", notifier=notifier(store, audits))
    created = await writer.create_or_update(AtlasEntitiesWithExtInfo.model_validate({"entities": [entity]}))
    return (created.guid_assignments or {})["-1"]


async def stored(store: EntityStore, guid: str) -> tuple[list[str] | None, int, str | None]:
    """The entity's labels, modification time and modifying user as stored."""
    found = await store.get(guid)
    assert found is not None
    return found.entity.labels, found.entity.update_time, found.entity.updated_by


def events(audits: InMemoryEntityAuditRepository) -> list[tuple[EntityAuditActionV2 | None, str | None]]:
    """The label events recorded, in order."""
    return [(event.action, event.details) for event in audits.events if event.action in {ADD, DELETE}]


async def failure(call: Any) -> tuple[AtlasErrorCode, str]:  # noqa: ANN401 - a coroutine
    """The error code and message the call fails with."""
    with pytest.raises(AtlasError) as raised:
        await call
    return raised.value.code, raised.value.message


@pytest.mark.covers(f"{E}.set_labels", rules=["LBL-02", "LBL-05"])
async def test__setting_labels_replaces_them(store: EntityStore, audits: InMemoryEntityAuditRepository) -> None:
    """The removed told first, then the added; the entity is written even when its labels stay."""
    guid = await table(store, audits, "a", "b")
    service = labels(store, audits)
    audits.events.clear()

    await service.set_labels(guid, ["b", "c", "c"])
    after_set = await stored(store, guid)
    await service.set_labels(guid, ["b", "c"])
    after_same = await stored(store, guid)
    await service.set_labels(guid, None)

    assert after_set[0] == ["b", "c"]
    assert after_set[2] == "u"
    assert after_same[1] > after_set[1]
    assert (await stored(store, guid))[0] is None
    assert events(audits) == [(DELETE, "Deleted labels: a"), (ADD, "Added labels: c"), (DELETE, "Deleted labels: b c")]


@pytest.mark.covers(f"{E}.add_labels", rules=["LBL-03", "LBL-05"])
async def test__adding_labels_adds_those_not_there(store: EntityStore, audits: InMemoryEntityAuditRepository) -> None:
    """Only the new ones are added and told; nothing is written when there are none."""
    guid = await table(store, audits, "a")
    service = labels(store, audits)
    audits.events.clear()

    await service.add_labels(guid, ["a", "b", "c"])
    before = await stored(store, guid)
    await service.add_labels(guid, ["c"])

    assert before[0] == ["a", "b", "c"]
    assert await stored(store, guid) == before
    assert events(audits) == [(ADD, "Added labels: b c")]


@pytest.mark.covers(f"{E}.remove_labels", rules=["LBL-04", "LBL-05"])
async def test__removing_labels_removes_those_there(store: EntityStore, audits: InMemoryEntityAuditRepository) -> None:
    """Only those the entity has are removed and told; nothing is written when it has none of them."""
    guid = await table(store, audits, "a", "b", "c")
    service = labels(store, audits)
    audits.events.clear()

    await service.remove_labels(guid, ["c", "x", "a"])
    before = await stored(store, guid)
    await service.remove_labels(guid, ["x"])
    await service.remove_labels(guid, ["b"])

    assert before[0] == ["b"]
    assert (await stored(store, guid))[0] is None
    assert events(audits) == [(DELETE, "Deleted labels: a c"), (DELETE, "Deleted labels: b")]


@pytest.mark.covers(f"{E}.set_labels", f"{E}.add_labels", f"{E}.remove_labels", rules=["LBL-02", "LBL-03", "LBL-04"])
async def test__labels_are_checked_before_they_change(
    store: EntityStore, audits: InMemoryEntityAuditRepository
) -> None:
    """A missing GUID or labels, an unknown entity and an invalid label fail; nothing is written."""
    guid = await table(store, audits, "a")
    service = labels(store, audits)

    assert await failure(service.add_labels("", ["a"])) == (
        AtlasErrorCode.INVALID_PARAMETERS,
        "invalid parameters: guid is null/empty",
    )
    assert await failure(service.set_labels("", ["a"])) == (
        AtlasErrorCode.INVALID_PARAMETERS,
        "invalid parameters: guid is null/empty",
    )
    for empty in (None, []):
        assert await failure(service.add_labels(guid, empty)) == (
            AtlasErrorCode.INVALID_PARAMETERS,
            "invalid parameters: labels is null/empty",
        )
        assert (await failure(service.remove_labels(guid, empty)))[0] is AtlasErrorCode.INVALID_PARAMETERS
    assert (await failure(service.set_labels("nope", ["a"])))[0] is AtlasErrorCode.INSTANCE_GUID_NOT_FOUND
    assert (await failure(service.add_labels(guid, ["a b"])))[0] is AtlasErrorCode.INVALID_LABEL_CHARACTERS
    assert (await failure(service.set_labels(guid, ["x" * 51])))[0] is AtlasErrorCode.INVALID_LABEL_LENGTH
    assert (await failure(service.remove_labels(guid, ["a!"])))[0] is AtlasErrorCode.INVALID_LABEL_CHARACTERS
    assert (await stored(store, guid))[0] == ["a"]


@pytest.mark.covers(
    "aurelius_atlas_core.entity_writer.EntityWriter.create_or_update",
    f"{L}.on_labels_added",
    f"{L}.on_labels_deleted",
    "aurelius_atlas_core.entity_change_notifier.EntityChangeNotifier.on_labels_updated",
    "aurelius_atlas_core.entity_change_notifier.EntityChangeListener.on_labels_added",
    "aurelius_atlas_core.entity_change_notifier.EntityChangeListener.on_labels_deleted",
    rules=["LBL-05"],
)
async def test__an_entity_created_with_labels_records_them_first(
    store: EntityStore, audits: InMemoryEntityAuditRepository
) -> None:
    """``LABEL_ADD`` before ``ENTITY_CREATE``, as the creating user; none for an entity without labels."""
    guid = await table(store, audits, "a", "b")
    entity = {"typeName": "s_table", "guid": "-2", "attributes": {"qualifiedName": "u"}}
    await EntityWriter(store).create_or_update(AtlasEntitiesWithExtInfo.model_validate({"entities": [entity]}))

    assert [(event.entity_id, event.action, event.details, event.user) for event in audits.events[:1]] == [
        (guid, ADD, "Added labels: a b", "c")
    ]
    assert audits.events[1].action is EntityAuditActionV2.ENTITY_CREATE
    assert len(audits.events) == 2


@pytest.mark.covers(f"{E}.set_labels", f"{E}.add_labels", f"{E}.remove_labels", rules=["AUZ-16"])
async def test__each_label_is_checked_with_its_privilege(
    store: EntityStore, audits: InMemoryEntityAuditRepository
) -> None:
    """``add label``, ``remove label`` and ``add/update label`` per label; nothing is written when refused."""
    guid = await table(store, audits, "a")
    adder = labels(store, audits, authorizer=Granted("r", frozenset({AtlasPrivilege.ENTITY_ADD_LABEL})))
    remover = labels(store, audits, authorizer=Granted("r", frozenset({AtlasPrivilege.ENTITY_REMOVE_LABEL})))
    refused = "r is not authorized to perform "

    assert await failure(adder.set_labels(guid, ["b"])) == (
        AtlasErrorCode.UNAUTHORIZED_ACCESS,
        f"{refused}remove label: guid={guid}, label=a",
    )
    assert (await failure(remover.set_labels(guid, ["b"])))[1] == f"{refused}add label: guid={guid}, label=b"
    assert (await failure(remover.add_labels(guid, ["a"])))[1] == f"{refused}add/update label: guid={guid}, label=a"
    assert (await failure(adder.remove_labels(guid, ["z"])))[1] == f"{refused}remove label: guid={guid}, label=z"
    assert (await stored(store, guid))[0] == ["a"]
    await adder.set_labels(guid, ["a", "b"])
    assert (await stored(store, guid))[0] == ["a", "b"]
