"""Entity audit against the dev Elasticsearch (AUD-02, AUD-05, AUD-08, DD-082, DD-083).

Events are written in one bulk request after the change and read back newest first by their event key.
"""

import pytest
from aurelius_atlas_core.entity_audit_listener import EntityAuditListener
from aurelius_atlas_core.entity_audit_repository import ElasticsearchEntityAuditRepository, list_events_sorted
from aurelius_atlas_core.entity_change_notifier import EntityChangeNotifier
from aurelius_atlas_core.entity_documents import ElasticsearchEntityDocuments
from aurelius_atlas_core.entity_store import EntityStore
from aurelius_atlas_core.entity_writer import EntityWriter
from aurelius_atlas_core.testing.entity_samples import sample_registry
from aurelius_atlas_model.audit import EntityAuditActionV2
from aurelius_atlas_model.instance import AtlasEntitiesWithExtInfo
from aurelius_atlas_store_es import ElasticsearchStore

# The async fixtures run on the module loop (asyncio_default_fixture_loop_scope); so must async tests.
pytestmark = pytest.mark.asyncio(loop_scope="module")


@pytest.mark.covers(
    "aurelius_atlas_core.entity_audit_repository.ElasticsearchEntityAuditRepository.list_events",
    "aurelius_atlas_core.entity_audit_repository.ElasticsearchEntityAuditRepository.put_events",
    rules=["AUD-02", "AUD-05", "AUD-07", "AUD-08"],
)
async def test__a_tables_events_are_recorded_and_read_newest_first(
    dev_store: ElasticsearchStore, entity_prefix: str
) -> None:
    """Create, two updates and a delete: newest key first, from a start key, by action, sorted by time."""
    store = EntityStore(sample_registry(), ElasticsearchEntityDocuments(dev_store.client, prefix=entity_prefix))
    await store.prepare()
    audits = ElasticsearchEntityAuditRepository(dev_store.client, prefix=entity_prefix)
    await audits.prepare()
    writer = EntityWriter(store, notifier=EntityChangeNotifier(store, [EntityAuditListener(audits, store.now)]))

    def table(guid: str, name: str | None = None) -> AtlasEntitiesWithExtInfo:
        attributes = {"qualifiedName": "t@au", **({} if name is None else {"name": name})}
        return AtlasEntitiesWithExtInfo.model_validate(
            {"entities": [{"typeName": "s_table", "guid": guid, "attributes": attributes}]}
        )

    guid = ((await writer.create_or_update(table("-1"))).guid_assignments or {})["-1"]
    for name in ("one", "two"):
        await writer.create_or_update(table(guid, name))
    await writer.delete_by_id(guid)

    events = await audits.list_events(guid, None, None, -1)
    rest = await audits.list_events(guid, None, events[1].event_key, 10)
    created = await audits.list_events(guid, EntityAuditActionV2.ENTITY_CREATE, None, 10)
    oldest = await list_events_sorted(audits, guid, None, "timestamp", descending=False, offset=0, limit=2)

    assert [e.action for e in events] == ["ENTITY_DELETE", "ENTITY_UPDATE", "ENTITY_UPDATE", "ENTITY_CREATE"]
    assert [e.event_key for e in rest] == [e.event_key for e in events[1:]]
    assert [e.action for e in created] == ["ENTITY_CREATE"]
    assert [e.action for e in oldest] == ["ENTITY_CREATE", "ENTITY_UPDATE"]
