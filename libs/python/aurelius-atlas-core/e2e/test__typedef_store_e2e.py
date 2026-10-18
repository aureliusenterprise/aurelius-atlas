"""The typedef store on the dev Elasticsearch, two processes sharing one document (TDS-10 to TDS-13)."""

import json
from pathlib import Path

import pytest
from aurelius_atlas_core.typedef_document import ElasticsearchTypedefDocument
from aurelius_atlas_core.typedef_store import TypedefStore
from aurelius_atlas_model.errors import AtlasError, AtlasErrorCode
from aurelius_atlas_model.typedef import AtlasEntityDef, AtlasTypesDef, TypeCategory
from aurelius_atlas_store_es import ElasticsearchStore
from aurelius_atlas_typesystem.registry import TypeRegistry

FIXTURES = Path(__file__).parents[1] / "tests" / "fixtures"

# The async fixtures run on the module loop (asyncio_default_fixture_loop_scope); so must async tests.
pytestmark = pytest.mark.asyncio(loop_scope="module")


async def loaded_store(dev_store: ElasticsearchStore, alias: str, refresh_seconds: float = 0.0) -> TypedefStore:
    """A store, as one server process has it, loaded from ``alias``."""
    store = TypedefStore(
        TypeRegistry(), ElasticsearchTypedefDocument(dev_store.client, alias), refresh_seconds=refresh_seconds
    )
    await store.load()
    return store


@pytest.mark.covers(rules=["TDS-10", "TDS-12"])
async def test__the_base_model_survives_a_restart(dev_store: ElasticsearchStore, typedef_index: str) -> None:
    """Created definitions are in Elasticsearch; a new process loads them all."""
    first = await loaded_store(dev_store, typedef_index)
    await first.create_types_def(
        AtlasTypesDef.model_validate(json.loads((FIXTURES / "0010-base_model.json").read_text()))
    )

    restarted = await loaded_store(dev_store, typedef_index)

    assert len(restarted.registry.typedef_names(TypeCategory.ENTITY)) == 15
    process = restarted.registry.entity_type("Process")
    assert process is not None
    assert process.relationship_attribute("inputs") is not None


@pytest.mark.covers(rules=["TDS-11", "TDS-13"])
async def test__two_processes_see_each_others_changes(dev_store: ElasticsearchStore, typedef_index: str) -> None:
    """DD-029: the second writer reloads first; the reader reloads on refresh."""
    one = await loaded_store(dev_store, typedef_index)
    two = await loaded_store(dev_store, typedef_index)

    await one.create_types_def(AtlasTypesDef(entity_defs=[AtlasEntityDef(name="fromOne")]))
    await two.create_types_def(AtlasTypesDef(entity_defs=[AtlasEntityDef(name="fromTwo")]))
    assert await one.refresh()

    assert sorted(one.registry.typedef_names(TypeCategory.ENTITY)) == ["fromOne", "fromTwo"]
    assert sorted(two.registry.typedef_names(TypeCategory.ENTITY)) == ["fromOne", "fromTwo"]


@pytest.mark.covers(rules=["TDS-10"])
async def test__a_rejected_change_leaves_elasticsearch_unchanged(
    dev_store: ElasticsearchStore, typedef_index: str
) -> None:
    """A request with one bad definition stores none of them."""
    store = await loaded_store(dev_store, typedef_index)
    await store.create_types_def(AtlasTypesDef(entity_defs=[AtlasEntityDef(name="kept")]))

    with pytest.raises(AtlasError) as raised:
        await store.create_types_def(
            AtlasTypesDef(entity_defs=[AtlasEntityDef(name="new"), AtlasEntityDef(name="kept")])
        )
    restarted = await loaded_store(dev_store, typedef_index)

    assert raised.value.code is AtlasErrorCode.TYPE_ALREADY_EXISTS
    assert restarted.registry.typedef_names(TypeCategory.ENTITY) == ["kept"]
