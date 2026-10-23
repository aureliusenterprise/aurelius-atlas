"""Entity audit (AUD-02 to AUD-05, AUD-07, AUD-08) on the in-memory repository.

The events and their details are read from ``AtlasEntityChangeNotifier`` (``onEntitiesMutated``,
``pruneResponse``), ``EntityAuditListenerV2`` and ``HBaseBasedAuditRepository`` of Apache Atlas 2.4.0, the
listings from its test ``AuditRepositoryTestBase``.
"""

import itertools
from typing import Any

import pytest
from aurelius_atlas_core import entity_audit_listener
from aurelius_atlas_core.entity_audit_listener import EntityAuditListener, audit_detail
from aurelius_atlas_core.entity_audit_repository import list_events_sorted, sort_events
from aurelius_atlas_core.entity_change_notifier import (
    EntityChangeListener,
    EntityChangeNotifier,
    entity_of_header,
    prune_response,
)
from aurelius_atlas_core.entity_store import EntityStore
from aurelius_atlas_core.entity_writer import EntityWriter
from aurelius_atlas_core.testing.entity_samples import sample_registry
from aurelius_atlas_core.testing.memory import InMemoryEntityAuditRepository, MemoryEntityDocuments
from aurelius_atlas_model import codec
from aurelius_atlas_model.audit import EntityAuditActionV2, EntityAuditEventV2
from aurelius_atlas_model.instance import (
    AtlasEntitiesWithExtInfo,
    AtlasEntity,
    AtlasEntityHeader,
    EntityMutationResponse,
    EntityOperation,
)

N = "aurelius_atlas_core.entity_change_notifier"
L = "aurelius_atlas_core.entity_audit_listener"
R = "aurelius_atlas_core.entity_audit_repository"
CREATE, UPDATE = EntityAuditActionV2.ENTITY_CREATE, EntityAuditActionV2.ENTITY_UPDATE
DELETE, PURGE = EntityAuditActionV2.ENTITY_DELETE, EntityAuditActionV2.ENTITY_PURGE


@pytest.fixture
def audits() -> InMemoryEntityAuditRepository:
    """The events recorded."""
    return InMemoryEntityAuditRepository()


@pytest.fixture
def store() -> EntityStore:
    """A store of the sample types whose clock ticks one millisecond per reading, from 1000."""
    ticks = itertools.count(1000)
    return EntityStore(sample_registry(), MemoryEntityDocuments(), clock=lambda: next(ticks) / 1000)


def writer(store: EntityStore, audits: InMemoryEntityAuditRepository, **more: Any) -> EntityWriter:  # noqa: ANN401
    """A writer whose notifier records audit events."""
    notifier = EntityChangeNotifier(store, [EntityAuditListener(audits, store.now)])
    return EntityWriter(store, notifier=notifier, **more)


def table(guid: str, qualified_name: str, **attributes: Any) -> dict[str, Any]:  # noqa: ANN401 - Atlas JSON
    """An ``s_table``."""
    return {"typeName": "s_table", "guid": guid, "attributes": {"qualifiedName": qualified_name, **attributes}}


def body(*entities: dict[str, Any]) -> AtlasEntitiesWithExtInfo:
    """A bulk request."""
    return AtlasEntitiesWithExtInfo.model_validate({"entities": list(entities)})


def details_json(event: EntityAuditEventV2) -> dict[str, Any]:
    """The JSON part of the event's details."""
    details = event.details or ""
    return codec.loads(details[details.index("{") :])


@pytest.mark.covers(
    f"{N}.EntityChangeNotifier.on_entities_mutated",
    f"{L}.EntityAuditListener.on_entities_added",
    f"{L}.EntityAuditListener.on_entities_updated",
    f"{L}.EntityAuditListener.on_entities_deleted",
    f"{L}.EntityAuditListener.on_entities_purged",
    f"{N}.entity_of_header",
    "aurelius_atlas_core.entity_writer.EntityWriter.create_or_update",
    "aurelius_atlas_core.entity_writer.EntityWriter.delete_by_id",
    "aurelius_atlas_core.entity_writer.EntityWriter.purge_by_ids",
    rules=["AUD-02", "AUD-03", "AUD-05"],
)
async def test__a_create_an_update_a_delete_and_a_purge_are_recorded(
    store: EntityStore, audits: InMemoryEntityAuditRepository
) -> None:
    """Each with its action and details, newest first; the entity JSON as read, without relationship attributes."""
    write = writer(store, audits, user="jo")
    created = await write.create_or_update(body(table("-1", "t@cl")))
    guid = (created.guid_assignments or {})["-1"]
    await write.create_or_update(body(table(guid, "t@cl", name="renamed")))
    await write.delete_by_id(guid)
    await write.purge_by_ids([guid])

    events = await audits.list_events(guid, None, None, -1)

    assert [event.action for event in events] == [PURGE, DELETE, UPDATE, CREATE]
    purged, deleted, updated, made = events
    assert (made.details or "").startswith("Created: {")
    assert details_json(made)["attributes"]["qualifiedName"] == "t@cl"
    assert "relationshipAttributes" not in details_json(made)
    assert details_json(updated)["attributes"]["name"] == "renamed"
    assert (updated.details or "").startswith("Updated: ")
    assert deleted.details == "Deleted entity"
    assert (purged.details or "").startswith("Purged: ")
    assert {key: details_json(purged)[key] for key in ("guid", "typeName", "status", "proxy", "provenanceType")} == {
        "guid": guid,
        "typeName": "s_table",
        "status": "DELETED",
        "proxy": False,
        "provenanceType": 0,
    }
    assert all(event.user == "jo" and event.entity is None for event in events)
    assert all((event.event_key or "").startswith(f"{guid}:{event.timestamp}:0:") for event in events)
    assert [event.timestamp for event in events] == sorted((event.timestamp for event in events), reverse=True)


@pytest.mark.covers(f"{N}.EntityChangeNotifier.on_entities_mutated", rules=["AUD-02", "AUD-05"])
async def test__a_request_records_its_entities_in_order_each_keyed_by_its_place(
    store: EntityStore, audits: InMemoryEntityAuditRepository
) -> None:
    """Two created tables in one request: indices 0 and 1; a request that changes nothing records nothing."""
    created = await writer(store, audits).create_or_update(body(table("-1", "a@cl"), table("-2", "b@cl")))
    guids = [(created.guid_assignments or {})[key] for key in ("-1", "-2")]
    await writer(store, audits).create_or_update(body(table(guids[0], "a@cl")))

    first = await audits.list_events(guids[0], None, None, -1)
    second = await audits.list_events(guids[1], None, None, -1)

    assert [event.action for event in first] == [CREATE]
    assert (first[0].event_key or "").split(":")[2] == "0"
    assert (second[0].event_key or "").split(":")[2] == "1"
    assert await EntityChangeNotifier(store, []).on_entities_mutated(created, user=None) is None


@pytest.mark.covers(f"{N}.prune_response", rules=["AUD-02"])
def test__a_response_lists_each_entity_under_the_kind_that_counts() -> None:
    """``DELETED`` ones leave the changed lists; purged, deleted, created and updated ones the earlier lists."""

    def header(guid: str, status: str = "ACTIVE") -> AtlasEntityHeader:
        return AtlasEntityHeader.model_validate({"guid": guid, "typeName": "t", "status": status})

    response = EntityMutationResponse(
        mutated_entities={
            EntityOperation.CREATE: [header("c"), header("gone", "DELETED"), header("d")],
            EntityOperation.UPDATE: [header("u"), header("c"), header("d"), header("p")],
            EntityOperation.PARTIAL_UPDATE: [header("u"), header("x")],
            EntityOperation.DELETE: [header("d"), header("p")],
            EntityOperation.PURGE: [header("p")],
        }
    )

    prune_response(response)

    assert {
        operation.value: [header.guid for header in headers]
        for operation, headers in (response.mutated_entities or {}).items()
    } == {"CREATE": ["c"], "UPDATE": ["u"], "PARTIAL_UPDATE": ["x"], "DELETE": ["d"], "PURGE": ["p"]}
    prune_response(EntityMutationResponse())


@pytest.mark.covers(f"{N}.EntityChangeNotifier.on_entities_mutated", rules=["AUD-02"])
async def test__entities_of_unknown_types_or_gone_are_left_out(
    store: EntityStore, audits: InMemoryEntityAuditRepository
) -> None:
    """A header of no entity type, and an updated entity that cannot be read, record nothing."""
    response = EntityMutationResponse(
        mutated_entities={
            EntityOperation.UPDATE: [AtlasEntityHeader(guid="nope", type_name="s_table")],
            EntityOperation.DELETE: [AtlasEntityHeader(guid="x", type_name="unknown")],
        }
    )

    await EntityChangeNotifier(store, [EntityAuditListener(audits, store.now)]).on_entities_mutated(response, user=None)

    assert audits.events == []


@pytest.mark.covers(f"{L}.EntityAuditListener.on_entities_updated", rules=["AUD-03"])
async def test__an_updated_shell_entity_is_recorded_as_created(audits: InMemoryEntityAuditRepository) -> None:
    """Incomplete, with the same create and update time: ``ENTITY_CREATE``, ``Created: ``."""
    listener = EntityAuditListener(audits, lambda: 5)
    shell = AtlasEntity.model_validate(
        {"guid": "s", "typeName": "t", "isIncomplete": True, "createTime": 1, "updateTime": 1}
    )
    later = shell.model_copy(update={"guid": "l", "update_time": None})

    await listener.on_entities_updated([shell, later], user=None)

    assert [(event.entity_id, event.action) for event in audits.events] == [("s", CREATE), ("l", UPDATE)]
    assert (audits.events[0].details or "").startswith("Created: ")


@pytest.mark.covers(f"{L}.audit_detail", rules=["AUD-04"])
def test__long_details_lose_the_attributes_then_all_but_the_system_fields(monkeypatch: pytest.MonkeyPatch) -> None:
    """Over the limit the attributes go; still over it, only GUID, type, times, users, status and version stay."""
    entity = AtlasEntity(guid="g", type_name="t", attributes={"blob": "x" * 200}, created_by="jo", version=3)
    monkeypatch.setattr(entity_audit_listener, "MAX_DETAILS_BYTES", 150)
    trimmed = codec.loads(audit_detail(entity, UPDATE).removeprefix("Updated: "))
    monkeypatch.setattr(entity_audit_listener, "MAX_DETAILS_BYTES", 10)
    shallow = codec.loads(audit_detail(entity, UPDATE).removeprefix("Updated: "))

    assert "attributes" not in trimmed
    assert trimmed["createdBy"] == "jo"
    assert shallow["guid"] == "g"
    assert (shallow["version"], shallow["createdBy"]) == (3, "jo")
    assert audit_detail(entity, EntityAuditActionV2.LABEL_ADD).startswith("Unknown: ")
    assert entity_of_header(AtlasEntityHeader(guid="h", type_name="t")).guid == "h"


def event(entity_id: str, timestamp: int, user: str | None, action: EntityAuditActionV2) -> EntityAuditEventV2:
    """An event keyed as Atlas keys them."""
    return EntityAuditEventV2(
        entity_id=entity_id,
        timestamp=timestamp,
        user=user,
        action=action,
        details=f"{action}",
        event_key=f"{entity_id}:{timestamp}:0:{timestamp}",
    )


@pytest.mark.covers("aurelius_atlas_core.testing.memory.InMemoryEntityAuditRepository.list_events", rules=["AUD-08"])
async def test__events_are_listed_newest_key_first_from_a_start_key(audits: InMemoryEntityAuditRepository) -> None:
    """``testListPaginationV2``: three of four, then from the third's key that one again; by action; counts."""
    await audits.put_events([event("a", 1000 + n, "u", CREATE if n == 0 else UPDATE) for n in range(4)])
    await audits.put_events([event("b", 2000, "u", CREATE)])

    first = await audits.list_events("a", None, None, 3)
    rest = await audits.list_events("a", None, first[2].event_key, 3)

    assert [e.timestamp for e in first] == [1003, 1002, 1001]
    assert [e.timestamp for e in rest] == [1001, 1000]
    assert [e.timestamp for e in await audits.list_events("a", CREATE, None, 10)] == [1000]
    assert len(await audits.list_events("a", None, None, -1)) == 4
    assert await audits.list_events("a", None, None, 0) == []
    assert await audits.list_events("a", None, None, -2) == []


@pytest.mark.covers(f"{R}.list_events_sorted", f"{R}.sort_events", rules=["AUD-07"])
async def test__events_are_sorted_by_a_column_then_paged(audits: InMemoryEntityAuditRepository) -> None:
    """``testSortListV2``: by timestamp, by user, by action; descending; offset and count as Atlas reads them."""
    await audits.put_events(
        [event("a", 1, "user1", UPDATE), event("a", 2, "User3", CREATE), event("a", 3, "user2", DELETE)]
    )

    def at(events: list[EntityAuditEventV2]) -> list[int]:
        return [e.timestamp for e in events]

    async def listed(sort_by: str | None, *, descending: bool = False, offset: int = 0, limit: int = 3) -> list[int]:
        return at(
            await list_events_sorted(audits, "a", None, sort_by, descending=descending, offset=offset, limit=limit)
        )

    assert await listed("timestamp", limit=2) == [1, 2]
    assert await listed("user") == [1, 3, 2]
    assert await listed("ACTION") == [2, 3, 1]
    assert await listed(None, descending=True) == [3, 2, 1]
    assert await listed("nope", offset=-1, limit=-5) == [1, 2, 3]
    assert await listed("timestamp", offset=1, limit=0) == [2, 3]
    assert await listed("timestamp", offset=5) == []
    assert at(sort_events([event("a", 2, None, CREATE), event("a", 1, "x", CREATE)], "user", descending=True)) == [1, 2]


@pytest.mark.covers(
    *(
        f"{N}.EntityChangeListener.{name}"
        for name in ("on_entities_added", "on_entities_updated", "on_entities_deleted", "on_entities_purged")
    ),
    rules=["AUD-02"],
)
def test__the_audit_listener_is_an_entity_change_listener(audits: InMemoryEntityAuditRepository) -> None:
    """The notifier takes any ``EntityChangeListener``; the audit listener is the one Aurelius Atlas has."""
    assert isinstance(EntityAuditListener(audits, lambda: 0), EntityChangeListener)
