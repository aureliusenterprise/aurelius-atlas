"""``ClassificationAssociator`` (CLA-01 to CLA-04) on the in-memory documents.

The expected changes and summaries are read from ``ClassificationAssociator.Updater`` and ``ListOps`` of Apache Atlas
2.4.0 and its test ``ClassificationAssociatorTest``.
"""

import json
from typing import Any

import pytest
from aurelius_atlas_core.classification_associator import ClassificationAssociator
from aurelius_atlas_core.entity_classifications import EntityClassifications
from aurelius_atlas_core.entity_store import EntityStore
from aurelius_atlas_core.entity_writer import EntityWriter
from aurelius_atlas_core.testing.entity_samples import sample_registry
from aurelius_atlas_core.testing.memory import MemoryEntityDocuments
from aurelius_atlas_model.instance import AtlasClassification, AtlasEntitiesWithExtInfo, AtlasEntityHeaders

A = "aurelius_atlas_core.classification_associator.ClassificationAssociator"


@pytest.fixture
async def store() -> EntityStore:
    """A store of the sample and classification types with tables ``t@cl`` (``c_pii``, ``c_tabular``) and ``u@cl``."""
    found = EntityStore(sample_registry(classifications=True), MemoryEntityDocuments())
    created = await EntityWriter(found).create_or_update(
        AtlasEntitiesWithExtInfo.model_validate(
            {
                "entities": [
                    {"typeName": "s_table", "guid": "-1", "attributes": {"qualifiedName": "t@cl"}},
                    {"typeName": "s_table", "guid": "-2", "attributes": {"qualifiedName": "u@cl"}},
                ]
            }
        )
    )
    guid = (created.guid_assignments or {})["-1"]
    await EntityClassifications(found).add_classifications(
        guid, [AtlasClassification(type_name="c_pii"), AtlasClassification(type_name="c_tabular")]
    )
    return found


def headers(*items: dict[str, Any]) -> AtlasEntityHeaders:
    """``guidHeaderMap`` of these headers, by their own ``guid``."""
    return AtlasEntityHeaders.model_validate(
        {"guidHeaderMap": {item.get("guid", str(n)): item for n, item in enumerate(items)}}
    )


async def names(store: EntityStore, qualified_name: str) -> list[str | None]:
    """The classification type names of the table with the qualified name."""
    table = store.registry.entity_type("s_table")
    assert table is not None
    found = await store.find_by_unique_attributes(table, {"qualifiedName": qualified_name})
    assert found is not None
    return [c.type_name for c in await EntityClassifications(store).get_classifications(found.entity.guid)]


@pytest.mark.covers(f"{A}.set_classifications", rules=["CLA-01", "CLA-02", "CLA-03", "CLA-04"])
async def test__an_entitys_classifications_become_its_headers_deletes_then_updates_then_adds(
    store: EntityStore,
) -> None:
    """``c_tabular`` goes, ``c_pii`` is updated, ``c_secret`` added; one summary line per step."""
    table = store.registry.entity_type("s_table")
    assert table is not None
    found = await store.find_by_unique_attributes(table, {"qualifiedName": "t@cl"})
    assert found is not None
    guid = found.entity.guid
    request = headers(
        {
            "guid": "remote",
            "typeName": "s_table",
            "attributes": {"qualifiedName": "t@cl"},
            "classifications": [
                {"typeName": "c_pii", "attributes": {"level": 5}},
                {"typeName": "c_secret"},
                {"typeName": "c_owned", "entityGuid": "elsewhere"},
            ],
        }
    )

    summary = await ClassificationAssociator(store).set_classifications(request.guid_header_map)
    updated = await EntityClassifications(store).get_classification(guid, "c_pii")

    assert json.loads(summary) == [
        f"Delete:{guid}:s_table:qualifiedName -> c_tabular:(Done)",
        f"Update:{guid}:s_table:qualifiedName -> c_pii:(Done)",
        f"Add:{guid}:s_table:qualifiedName -> c_secret:(Done)",
    ]
    assert await names(store, "t@cl") == ["c_pii", "c_secret"]
    assert (updated.attributes or {})["level"] == 5


@pytest.mark.covers(f"{A}.set_classifications", rules=["CLA-01", "CLA-02", "CLA-03", "CLA-04"])
async def test__unknown_types_and_entities_are_skipped_and_failing_steps_partial(store: EntityStore) -> None:
    """A failed request marks its step ``(Partial)`` and the others go on; nothing to change adds no line."""
    request = headers(
        {"guid": "a", "typeName": "nope", "attributes": {}},
        {"guid": "b", "typeName": "s_table", "attributes": {"qualifiedName": "x@cl"}},
        {"guid": "c", "typeName": "s_table"},
        {"guid": "d", "typeName": "s_table", "attributes": {"qualifiedName": "u@cl"}},
        {
            "guid": "e",
            "typeName": "s_column",
            "attributes": {"qualifiedName": "u@cl"},
            "classifications": [{"typeName": "c_tabular"}],
        },
        {"typeName": "s_table", "attributes": {"qualifiedName": "u@cl"}, "classifications": [{"typeName": "c_owned"}]},
    )

    summary = json.loads(await ClassificationAssociator(store).set_classifications(request.guid_header_map))

    assert summary[:4] == [
        "nope: (Skipped)",
        "Entity:s_table:qualifiedName:[Not found]:(Skipped)",
        "Entity:s_table:qualifiedName:[Not found]:(Skipped)",
        "Entity:s_column:qualifiedName:[Not found]:(Skipped)",
    ]
    assert summary[4].endswith(":s_table:qualifiedName -> c_owned:(Partial)")
    assert len(summary) == 5
    assert await ClassificationAssociator(store).set_classifications(None) == "[]"
