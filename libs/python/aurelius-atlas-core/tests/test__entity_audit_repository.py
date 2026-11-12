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
    "aurelius_atlas_core.entity_audit_repository.EntityAuditRepository.entities_with_tag_changes",
    "aurelius_atlas_core.testing.memory.InMemoryEntityAuditRepository.prepare",
    "aurelius_atlas_core.testing.memory.InMemoryEntityAuditRepository.put_events",
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
