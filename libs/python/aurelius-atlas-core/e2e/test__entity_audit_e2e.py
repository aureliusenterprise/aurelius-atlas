"""Entity audit against the dev Elasticsearch (AUD-02, AUD-05, AUD-08, DD-082, DD-083).

Events are written in one bulk request after the change and read back newest first by their event key.
"""

import pytest
from aurelius_atlas_core.classification_associator import ClassificationRetriever
from aurelius_atlas_core.entity_audit_listener import EntityAuditListener
from aurelius_atlas_core.entity_audit_repository import (
    ElasticsearchEntityAuditRepository,
    delete_events_v2,
    list_events_sorted,
)
from aurelius_atlas_core.entity_change_notifier import EntityChangeNotifier
from aurelius_atlas_core.entity_classifications import EntityClassifications
from aurelius_atlas_core.entity_documents import ElasticsearchEntityDocuments
from aurelius_atlas_core.entity_store import EntityStore
from aurelius_atlas_core.entity_writer import EntityWriter
from aurelius_atlas_core.testing.entity_samples import sample_registry
from aurelius_atlas_model.audit import EntityAuditActionV2
from aurelius_atlas_model.audit_reduction import AtlasAuditAgingType
from aurelius_atlas_model.instance import AtlasClassification, AtlasEntitiesWithExtInfo
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


@pytest.mark.covers(
    "aurelius_atlas_core.entity_audit_repository.ElasticsearchEntityAuditRepository.entities_with_tag_changes",
    "aurelius_atlas_core.classification_associator.ClassificationRetriever.get",
    rules=["CAU-02", "CAU-05", "CAU-07"],
)
async def test__classification_events_are_recorded_and_their_entities_found(
    dev_store: ElasticsearchStore, entity_prefix: str
) -> None:
    """An add on the input and a propagated add on the output; only the input counts as changed."""
    store = EntityStore(
        sample_registry(classifications=True), ElasticsearchEntityDocuments(dev_store.client, prefix=entity_prefix)
    )
    await store.prepare()
    audits = ElasticsearchEntityAuditRepository(dev_store.client, prefix=entity_prefix)
    await audits.prepare()
    notifier = EntityChangeNotifier(store, [EntityAuditListener(audits, store.now)])
    process = {
        "typeName": "p_process",
        "guid": "-3",
        "attributes": {"qualifiedName": "p@ca"},
        "relationshipAttributes": {"inputs": [{"guid": "-1"}], "outputs": [{"guid": "-2"}]},
    }
    created = await EntityWriter(store).create_or_update(
        AtlasEntitiesWithExtInfo.model_validate(
            {
                "entities": [
                    {"typeName": "p_data", "guid": "-1", "attributes": {"qualifiedName": "a@ca"}},
                    {"typeName": "p_data", "guid": "-2", "attributes": {"qualifiedName": "b@ca"}},
                    process,
                ]
            }
        )
    )
    guids = created.guid_assignments or {}
    start = store.now()

    await EntityClassifications(store, notifier=notifier).add_classifications(
        guids["-1"], [AtlasClassification(type_name="c_pii")]
    )
    changed = await ClassificationRetriever(store, audits).get(start, store.now())

    assert [e.action for e in await audits.list_events(guids["-1"], None, None, -1)] == ["CLASSIFICATION_ADD"]
    assert [e.action for e in await audits.list_events(guids["-2"], None, None, -1)] == [
        "PROPAGATED_CLASSIFICATION_ADD"
    ]
    assert list(changed.guid_header_map or {}) == [guids["-1"]]


@pytest.mark.covers(
    "aurelius_atlas_core.entity_audit_repository.ElasticsearchEntityAuditRepository.delete_events",
    "aurelius_atlas_core.entity_audit_repository.delete_events_v2",
    rules=["AGE-04"],
)
async def test__an_aging_deletes_a_tables_older_updates(dev_store: ElasticsearchStore, entity_prefix: str) -> None:
    """A default aging keeping one: the creation stays, the newest update stays, the older one goes."""
    store = EntityStore(sample_registry(), ElasticsearchEntityDocuments(dev_store.client, prefix=entity_prefix))
    await store.prepare()
    audits = ElasticsearchEntityAuditRepository(dev_store.client, prefix=entity_prefix)
    await audits.prepare()
    writer = EntityWriter(store, notifier=EntityChangeNotifier(store, [EntityAuditListener(audits, store.now)]))
    body = {"entities": [{"typeName": "s_table", "guid": "-1", "attributes": {"qualifiedName": "t@age"}}]}
    guid = ((await writer.create_or_update(AtlasEntitiesWithExtInfo.model_validate(body))).guid_assignments or {})["-1"]
    for name in ("one", "two"):
        entity = {"typeName": "s_table", "guid": guid, "attributes": {"qualifiedName": "t@age", "name": name}}
        await writer.create_or_update(AtlasEntitiesWithExtInfo.model_validate({"entities": [entity]}))

    removed = await delete_events_v2(
        audits,
        guid,
        [],
        1,
        0,
        create_events_ageout_allowed=False,
        aging_type=AtlasAuditAgingType.DEFAULT,
        now=store.now(),
    )
    left = await audits.list_events(guid, None, None, -1)

    assert [e.action for e in removed] == ["ENTITY_UPDATE"]
    assert [e.action for e in left] == ["ENTITY_UPDATE", "ENTITY_CREATE"]
