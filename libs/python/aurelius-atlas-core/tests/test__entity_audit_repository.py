"""``ElasticsearchEntityAuditRepository`` (AUD-05, AUD-08, DD-082, DD-083) on the fake client."""

from typing import cast

import pytest
from aurelius_atlas_core import entity_audit_repository
from aurelius_atlas_core.entity_audit_repository import ElasticsearchEntityAuditRepository, EntityAuditRepository
from aurelius_atlas_core.testing.memory import InMemoryEntityAuditRepository
from aurelius_atlas_model.audit import EntityAuditActionV2, EntityAuditEventV2
from aurelius_atlas_model.instance import AtlasEntity
from aurelius_atlas_store_es.testing.fake import FakeClient
from elasticsearch import AsyncElasticsearch

E = "aurelius_atlas_core.entity_audit_repository.ElasticsearchEntityAuditRepository"


def event(entity_id: str, n: int, action: EntityAuditActionV2) -> EntityAuditEventV2:
    """An event of ``entity_id`` at ``n``, with an entity definition that is not kept."""
    return EntityAuditEventV2(
        entity_id=entity_id,
        timestamp=n,
        action=action,
        details="d",
        event_key=f"{entity_id}:{n}:0:{n}",
        entity=AtlasEntity(guid=entity_id, type_name="t"),
    )


@pytest.mark.covers(
    f"{E}.prepare", f"{E}.put_events", f"{E}.list_events", rules=["AUD-01", "AUD-05", "AUD-08", "ENS-11", "IDX-01"]
)
async def test__events_are_written_in_one_bulk_request_and_listed_by_entity(
    fake: FakeClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Without their entity; by entity, action and start key, page by page; an alias created once.

    The append carries the refresh, the listings pay for none (ENS-11).
    """
    monkeypatch.setattr(entity_audit_repository, "AUDIT_PAGE", 1)
    repository = ElasticsearchEntityAuditRepository(cast("AsyncElasticsearch", fake), prefix="t")
    await repository.prepare()
    await repository.prepare()
    await repository.put_events([])
    create, update = EntityAuditActionV2.ENTITY_CREATE, EntityAuditActionV2.ENTITY_UPDATE
    await repository.put_events([event("a", 1, create), event("a", 2, update), event("b", 3, create)])

    every = await repository.list_events("a", None, None, -1)
    created = await repository.list_events("a", create, None, 5)
    bounded = await repository.list_events("a", None, "a:1:0:1", 5)

    assert repository.alias == "t-entity-audits"
    assert len(every) == 2
    assert {e.timestamp for e in every} == {1, 2}
    assert all(e.entity is None and e.type is None for e in every)
    assert [e.timestamp for e in created] == [1]
    assert [e.timestamp for e in bounded] == [1]
    assert len(await repository.list_events("a", None, None, 1)) == 1
    assert await repository.list_events("a", None, None, 0) == []
    assert set(fake.write_refreshes) == {("t-entity-audits", "true")}
    assert fake.refreshes == []


@pytest.mark.covers(f"{E}.prepare", rules=["IDX-02"])
async def test__prepare_survives_losing_the_create_to_another_server(fake: FakeClient) -> None:
    """Two servers booting on one store make the audit index: the loser takes the existing path (DD-508)."""
    fake.race_lost = "t-entity-audits-000001"

    await ElasticsearchEntityAuditRepository(cast("AsyncElasticsearch", fake), prefix="t").prepare()

    assert fake.aliases == {"t-entity-audits": "t-entity-audits-000001"}
    assert fake.index_settings["t-entity-audits-000001"]["index.auto_expand_replicas"] == "0-1"


@pytest.mark.covers(f"{E}.put_events", rules=["AUD-05"])
async def test__events_that_are_not_kept_fail_the_put(fake: FakeClient) -> None:
    """A bulk item that fails is an error."""
    repository = ElasticsearchEntityAuditRepository(cast("AsyncElasticsearch", fake), prefix="t")

    async def failing(**_: object) -> dict[str, object]:
        return {"errors": True, "items": []}

    fake.bulk = failing

    with pytest.raises(RuntimeError, match="t-entity-audits"):
        await repository.put_events([event("a", 1, EntityAuditActionV2.ENTITY_CREATE)])


@pytest.mark.covers(
    "aurelius_atlas_core.entity_audit_repository.EntityAuditRepository.prepare",
    "aurelius_atlas_core.entity_audit_repository.EntityAuditRepository.put_events",
    "aurelius_atlas_core.entity_audit_repository.EntityAuditRepository.list_events",
    "aurelius_atlas_core.entity_audit_repository.EntityAuditRepository.list_sorted",
    "aurelius_atlas_core.entity_audit_repository.EntityAuditRepository.entities_with_tag_changes",
    "aurelius_atlas_core.testing.memory.InMemoryEntityAuditRepository.prepare",
    "aurelius_atlas_core.testing.memory.InMemoryEntityAuditRepository.put_events",
    "aurelius_atlas_core.testing.memory.InMemoryEntityAuditRepository.list_sorted",
    rules=["AUD-08"],
)
async def test__both_implementations_are_audit_repositories(fake: FakeClient) -> None:
    """The server keeps events in Elasticsearch, tests in memory."""
    memory = InMemoryEntityAuditRepository()
    await memory.prepare()

    assert isinstance(ElasticsearchEntityAuditRepository(cast("AsyncElasticsearch", fake)), EntityAuditRepository)
    assert isinstance(memory, EntityAuditRepository)


@pytest.mark.covers(f"{E}.prepare", rules=["IDX-02"])
async def test__the_audit_index_expands_its_replicas_to_the_cluster() -> None:
    """At most one replica, none on a single node; an index made before gets the setting at the next start."""
    fake = FakeClient()
    await ElasticsearchEntityAuditRepository(cast("AsyncElasticsearch", fake), prefix="t").prepare()
    await fake.indices.create(index="o-entity-audits-000001", aliases={"o-entity-audits": {}})
    await ElasticsearchEntityAuditRepository(cast("AsyncElasticsearch", fake), prefix="o").prepare()

    assert fake.index_settings == {
        "t-entity-audits-000001": {"index.auto_expand_replicas": "0-1"},
        "o-entity-audits-000001": {"index.auto_expand_replicas": "0-1"},
    }


def audit_event(
    entity_id: str,
    timestamp: int,
    action: EntityAuditActionV2,
    user: str | None = "u",
    key: str | None = None,
) -> EntityAuditEventV2:
    """An event with a user and a key of its own, for the sorted listings (AUD-07)."""
    return EntityAuditEventV2(
        entity_id=entity_id,
        timestamp=timestamp,
        user=user,
        action=action,
        details="d",
        event_key=key or f"{entity_id}:{timestamp}:0:{timestamp}",
    )


# The events: mixed case and a missing user, equal timestamps at different keys, one of another entity.
MIXED: list[EntityAuditEventV2] = [
    audit_event("a", 1, EntityAuditActionV2.ENTITY_UPDATE, "user1", key="a:1:0:9"),
    audit_event("a", 2, EntityAuditActionV2.ENTITY_CREATE, "User3", key="a:2:0:9"),
    audit_event("a", 3, EntityAuditActionV2.ENTITY_DELETE, "user2", key="a:3:0:9"),
    audit_event("a", 1, EntityAuditActionV2.ENTITY_CREATE, "user1", key="a:1:0:8"),
    audit_event("a", 2, EntityAuditActionV2.ENTITY_UPDATE, None, key="a:2:0:8"),
    audit_event("b", 4, EntityAuditActionV2.ENTITY_CREATE, "user1", key="b:4:0:9"),
]


@pytest.mark.covers(
    f"{E}.list_sorted", "aurelius_atlas_core.testing.memory.InMemoryEntityAuditRepository.list_sorted", rules=["AUD-07"]
)
async def test__the_index_answers_the_sorted_listing_the_memory_one_gives(fake: FakeClient) -> None:
    """Every column, both directions, every offset and limit: the same windows from both repositories (AUD-07, DD-710).

    The fold of the user and the action is stored with the event, so the index sorts case-insensitively; equal
    timestamps break by event key descending newest key first, both directions, as Java's stable sort of the
    newest-key-first scan does.
    """
    repository = ElasticsearchEntityAuditRepository(cast("AsyncElasticsearch", fake), prefix="t")
    memory = InMemoryEntityAuditRepository()
    await repository.prepare()
    await repository.put_events(MIXED)
    await memory.put_events(MIXED)

    for sort_by in ["user", "action", "timestamp", None, "nope"]:
        for descending in [False, True]:
            for offset, limit in [(0, 100), (1, 2), (0, 0), (0, -1), (5, 3)]:
                indexed = await repository.list_sorted(
                    "a", None, sort_by, descending=descending, offset=offset, limit=limit
                )
                remembered = await memory.list_sorted(
                    "a", None, sort_by, descending=descending, offset=offset, limit=limit
                )
                assert [e.event_key for e in indexed] == [e.event_key for e in remembered], (
                    sort_by,
                    descending,
                    offset,
                    limit,
                )


@pytest.mark.covers(f"{E}.list_sorted", rules=["AUD-07"])
async def test__the_sorted_listing_holds_to_an_action_and_breaks_ties_by_event_key(
    fake: FakeClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Only the asked action; a page deep, so the key tail and ``search_after`` decide (AUD-07)."""
    monkeypatch.setattr(entity_audit_repository, "AUDIT_PAGE", 1)
    repository = ElasticsearchEntityAuditRepository(cast("AsyncElasticsearch", fake), prefix="t")
    await repository.prepare()
    create, update = EntityAuditActionV2.ENTITY_CREATE, EntityAuditActionV2.ENTITY_UPDATE
    await repository.put_events(
        [
            audit_event("a", 1, create, "same", key="a:1:0:9"),
            audit_event("a", 1, update, "same", key="a:1:0:8"),
            audit_event("a", 1, create, "same", key="a:1:0:7"),
        ]
    )

    by_timestamp = await repository.list_sorted("a", create, None, descending=False, offset=0, limit=0)
    newest_first = await repository.list_sorted("a", None, None, descending=True, offset=1, limit=1)

    assert [e.event_key for e in by_timestamp] == ["a:1:0:9", "a:1:0:7"]
    assert [e.event_key for e in newest_first] == ["a:1:0:8"]


@pytest.mark.covers(f"{E}.put_events", f"{E}.prepare", rules=["AUD-07", "DD-710"])
async def test__an_event_is_stored_with_its_folded_keys_and_an_old_one_gains_them(fake: FakeClient) -> None:
    """The fold is written with the event; a store made before it gains the fields and the fold at the next start."""
    repository = ElasticsearchEntityAuditRepository(cast("AsyncElasticsearch", fake), prefix="t")
    await repository.prepare()
    await repository.put_events([audit_event("a", 1, EntityAuditActionV2.ENTITY_DELETE, "MixedCase", key="a:1:0:9")])
    held = next(iter(fake.documents["t-entity-audits-000001"].values()))[0]

    create = {k: v for k, v in held.items() if k in {"user", "userKey", "action", "actionKey"}}
    old = {"entityId": "a", "auditId": "old", "timestamp": 2, "user": "MIXEDcase", "action": "ENTITY_CREATE"}
    await fake.index(index="t-entity-audits", id="old", document=old)
    await repository.prepare()
    backfilled = fake.documents["t-entity-audits-000001"]["old"][0]

    assert create == {
        "user": "MixedCase",
        "userKey": "mixedcase",
        "action": "ENTITY_DELETE",
        "actionKey": "entity_delete",
    }
    assert {k: backfilled[k] for k in ("user", "userKey", "action", "actionKey")} == {
        "user": "MIXEDcase",
        "userKey": "mixedcase",
        "action": "ENTITY_CREATE",
        "actionKey": "entity_create",
    }
    assert backfilled["entityId"] == "a"
    assert fake.mapping_updates[-1] == "t-entity-audits"


@pytest.fixture
def fake() -> FakeClient:
    """An empty fake client."""
    return FakeClient()


@pytest.mark.covers(f"{E}.entities_with_tag_changes", rules=["CAU-07", "ENS-11", "IDX-01"])
async def test__entities_with_classification_events_in_a_range_are_found(
    fake: FakeClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Their own classification events from the start, before the end; each entity once; page by page.

    The append carries the refresh, the read pays for none (ENS-11).
    """
    monkeypatch.setattr(entity_audit_repository, "AUDIT_PAGE", 1)
    repository = ElasticsearchEntityAuditRepository(cast("AsyncElasticsearch", fake), prefix="t")
    await repository.prepare()
    add, update = EntityAuditActionV2.CLASSIFICATION_ADD, EntityAuditActionV2.CLASSIFICATION_UPDATE
    await repository.put_events(
        [
            event("a", 1, add),
            event("a", 2, update),
            event("b", 3, EntityAuditActionV2.PROPAGATED_CLASSIFICATION_ADD),
            event("c", 4, EntityAuditActionV2.ENTITY_CREATE),
            event("d", 5, add),
        ]
    )

    assert sorted(await repository.entities_with_tag_changes(1, 6)) == ["a", "d"]
    assert await repository.entities_with_tag_changes(2, 5) == ["a"]
    assert set(fake.write_refreshes) == {("t-entity-audits", "true")}
    assert fake.refreshes == []
