"""Deletes against the dev Elasticsearch (EDL-06, EDL-07, EDL-09, EDL-10).

Referring entities are found by searching their references after a refresh (DD-057); hard deletes and purges
remove documents in the same bulk write as the changes (DD-056); preparing an existing index maps the field.
"""

from typing import Any

import pytest
from aurelius_atlas_core.delete_type import DeleteType
from aurelius_atlas_core.entity_documents import ElasticsearchEntityDocuments
from aurelius_atlas_core.entity_store import EntityStore
from aurelius_atlas_core.entity_writer import EntityWriter
from aurelius_atlas_core.testing.entity_samples import sample_registry
from aurelius_atlas_model.instance import AtlasEntitiesWithExtInfo, EntityStatus
from aurelius_atlas_store_es import ElasticsearchStore

# The async fixtures run on the module loop (asyncio_default_fixture_loop_scope); so must async tests.
pytestmark = pytest.mark.asyncio(loop_scope="module")

W = "aurelius_atlas_core.entity_writer.EntityWriter"


def entity(type_name: str, guid: str, **attributes: Any) -> dict[str, Any]:  # noqa: ANN401 - Atlas JSON
    """An entity as Atlas JSON."""
    return {"typeName": type_name, "guid": guid, "attributes": attributes}


@pytest.mark.covers(f"{W}.delete_by_id", f"{W}.purge_by_ids", rules=["EDL-06", "EDL-07", "EDL-09", "EDL-10"])
async def test__deletes_find_referrers_and_remove_documents_on_elasticsearch(
    dev_store: ElasticsearchStore, entity_prefix: str
) -> None:
    """A soft delete reports the referring table; a hard delete drops its reference; a purge removes the rest."""
    documents = ElasticsearchEntityDocuments(dev_store.client, prefix=entity_prefix)
    store = EntityStore(sample_registry(), documents)
    await store.prepare()
    await store.prepare()  # an existing index gets its fields mapped again, unchanged
    created = await EntityWriter(store).create_or_update(
        AtlasEntitiesWithExtInfo.model_validate(
            {
                "entities": [
                    entity("s_database", "-1", qualifiedName="db@cl"),
                    entity("s_database", "-2", qualifiedName="db2@cl"),
                    entity("s_table", "-3", qualifiedName="t@cl", db={"guid": "-1"}, columns=[{"guid": "-4"}]),
                    entity("s_column", "-4", qualifiedName="c@cl"),
                    entity("s_table", "-5", qualifiedName="u@cl", db={"guid": "-2"}),
                ]
            }
        )
    )
    guids = created.guid_assignments or {}

    soft = await EntityWriter(store).delete_by_id(guids["-1"])
    hard = await EntityWriter(store, delete_type=DeleteType.HARD).delete_by_id(guids["-2"])
    await EntityWriter(store).delete_by_id(guids["-3"])
    purged = await EntityWriter(store).purge_by_ids([guids["-1"], guids["-3"]])

    assert [header.guid for header in soft.get_updated_entities() or []] == [guids["-3"]]
    assert [header.guid for header in hard.get_updated_entities() or []] == [guids["-5"]]
    table = await store.get(guids["-5"])
    assert table is not None
    assert "s_table.db" not in table.entity.attributes
    assert table.entity.state is EntityStatus.ACTIVE
    assert {header.guid for header in purged.get_purged_entities() or []} == {guids["-1"], guids["-3"], guids["-4"]}
    assert await store.get_many([guids["-1"], guids["-2"], guids["-3"], guids["-4"]]) == {}
