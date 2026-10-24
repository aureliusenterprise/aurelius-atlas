"""Classification search (CSR-01 to CSR-05, DD-090) on the in-memory documents.

Lineage: ``p1`` reads ``a`` and writes ``b``; ``c_pii`` on ``a`` propagates to ``p1`` and ``b``. The rules are read
from ``SearchContext``, ``ClassificationSearchProcessor``, ``EntitySearchProcessor`` and ``buildTraitPredict`` of
Apache Atlas 2.4.0.
"""

from typing import Any

import pytest
from aurelius_atlas_core.discovery_service import EntityDiscoveryService
from aurelius_atlas_core.entity_classifications import EntityClassifications
from aurelius_atlas_core.entity_store import EntityStore
from aurelius_atlas_core.entity_writer import EntityWriter
from aurelius_atlas_core.search_fields import classification_fields
from aurelius_atlas_core.search_query import wildcard_pattern
from aurelius_atlas_core.testing.entity_samples import sample_registry
from aurelius_atlas_core.testing.memory import MemoryEntityDocuments
from aurelius_atlas_model.discovery import SearchParameters
from aurelius_atlas_model.errors import AtlasError, AtlasErrorCode
from aurelius_atlas_model.instance import AtlasClassification, AtlasEntitiesWithExtInfo

P = "aurelius_atlas_core.classification_search_processor.ClassificationSearchProcessor.criterion"
GUIDS: dict[str, str] = {}


@pytest.fixture
async def store() -> EntityStore:
    """``a -> p1 -> b`` and ``d`` apart; ``c_pii`` (level 5) on ``a``, ``c_secret`` (level 1) on ``d``."""
    found = EntityStore(sample_registry(classifications=True), MemoryEntityDocuments())

    def data(name: str) -> dict[str, Any]:
        return {"typeName": "p_data", "guid": f"-{name}", "attributes": {"qualifiedName": name}}

    process = {
        "typeName": "p_process",
        "guid": "-p1",
        "attributes": {"qualifiedName": "p1"},
        "relationshipAttributes": {"inputs": [{"guid": "-a"}], "outputs": [{"guid": "-b"}]},
    }
    created = await EntityWriter(found).create_or_update(
        AtlasEntitiesWithExtInfo.model_validate({"entities": [data("a"), data("b"), data("d"), process]})
    )
    GUIDS.clear()
    GUIDS.update({key.removeprefix("-"): value for key, value in (created.guid_assignments or {}).items()})
    classifier = EntityClassifications(found)
    await classifier.add_classifications(GUIDS["a"], [tag("c_pii", level=5)])
    await classifier.add_classifications(GUIDS["d"], [tag("c_secret", level=1)])
    return found


def tag(type_name: str, **attributes: Any) -> AtlasClassification:  # noqa: ANN401 - Atlas JSON
    """A classification with attribute values."""
    return AtlasClassification.model_validate({"typeName": type_name, "attributes": attributes})


async def search(store: EntityStore, **body: Any) -> dict[str, Any]:  # noqa: ANN401 - Atlas JSON
    """The answer to a search, as JSON."""
    return (await EntityDiscoveryService(store).search_with_parameters(SearchParameters.model_validate(body))).to_json()


async def names(store: EntityStore, **body: Any) -> list[str]:  # noqa: ANN401 - Atlas JSON
    """The qualified names a search finds, sorted."""
    return sorted(entity["attributes"]["qualifiedName"] for entity in (await search(store, **body)).get("entities", []))


def where(name: str, operator: str, value: str | None = None) -> dict[str, Any]:
    """A filter on one attribute."""
    return {"attributeName": name, "operator": operator, "attributeValue": value}


@pytest.mark.covers(P, "aurelius_atlas_core.search_context.SearchContext.all_entities", rules=["CSR-01", "CSR-02"])
async def test__entities_are_found_by_their_attached_and_propagated_classifications(store: EntityStore) -> None:
    """A type finds where it is attached or propagated; a super type its sub types' too, unless switched off."""
    assert await names(store, classification="c_pii") == ["a", "b", "d", "p1"]
    assert await names(store, classification="c_pii", includeSubClassifications=False) == ["a", "b", "p1"]
    assert await names(store, classification="c_secret,nope") == ["d"]
    assert await names(store, classification="c_pii", typeName="p_data") == ["a", "b", "d"]
    with pytest.raises(AtlasError) as unknown:
        await search(store, classification="nope,neither")

    assert (unknown.value.code, unknown.value.message) == (
        AtlasErrorCode.UNKNOWN_CLASSIFICATION,
        "nope,neither: Unknown/invalid classification",
    )


@pytest.mark.covers(P, "aurelius_atlas_core.search_query.wildcard_pattern", rules=["CSR-01", "CSR-02"])
@pytest.mark.parametrize(
    ("classification", "expected"),
    [
        ("_NOT_CLASSIFIED", []),
        ("_CLASSIFIED", ["a", "b", "d", "p1"]),
        ("*", ["a", "b", "d", "p1"]),
        ("_ALL_CLASSIFICATION_TYPES", ["a", "b", "d", "p1"]),
        ("C_SEC*", ["d"]),
        ("*pii,c_tabular", ["a", "b", "p1"]),
        ("c_pii,_NOT_CLASSIFIED", []),
    ],
)
async def test__special_and_wildcard_names_match_none_any_or_by_pattern(
    store: EntityStore, classification: str, expected: list[str]
) -> None:
    """``_NOT_CLASSIFIED`` wins over the others; a wildcard matches names ignoring case, without sub types."""
    await EntityWriter(store).create_or_update(
        AtlasEntitiesWithExtInfo.model_validate(
            {"entities": [{"typeName": "p_data", "guid": "-e", "attributes": {"qualifiedName": "e"}}]}
        )
    )
    found = await names(store, classification=classification)

    assert [name for name in found if name != "e"] == expected
    assert ("e" in found) is classification.endswith("_NOT_CLASSIFIED")
    assert wildcard_pattern("a*b").fullmatch("AxyB") is not None


@pytest.mark.covers(P, "aurelius_atlas_core.search_fields.classification_fields", rules=["CSR-03", "CSR-04"])
async def test__tag_filters_match_the_instances_an_entity_lists(store: EntityStore) -> None:
    """``level`` 5 finds where ``c_pii`` reaches; the system ``__entityStatus`` too; no count with tag filters."""
    high = await search(store, classification="c_pii", tagFilters=where("level", ">", "3"))
    low = await names(store, classification="c_pii", tagFilters=where("level", "<", "3"))
    active = await names(store, classification="*", tagFilters=where("__entityStatus", "=", "ACTIVE"))
    typed = await names(store, classification="c_pii", typeName="p_process", tagFilters=where("level", "=", "5"))
    nothing = await names(store, classification="c_pii", tagFilters=where("level", "=", "9"))

    assert sorted(entity["attributes"]["qualifiedName"] for entity in high["entities"]) == ["a", "b", "p1"]
    assert high["approximateCount"] == -1
    assert (low, active, typed, nothing) == (["d"], ["a", "b", "d", "p1"], ["p1"], [])
    a = await store.get(GUIDS["a"])
    assert a is not None
    instance = next(iter((await store.get_classifications(a.entity.classification_guids or [])).values()))
    pii = store.registry.classification_type("c_pii")
    assert pii is not None
    assert classification_fields(instance.classification, pii)["long.c_pii.level"] == 5


@pytest.mark.covers(P, rules=["CSR-03"])
async def test__tag_filters_name_attributes_of_every_type_and_no_wildcard(store: EntityStore) -> None:
    """An attribute ``c_tabular`` lacks, and tag filters with ``c_*``, fail."""
    failures = []
    for body in (
        {"classification": "c_pii,c_tabular", "tagFilters": where("level", "=", "1")},
        {"classification": "_ALL_CLASSIFICATION_TYPES", "tagFilters": where("level", "=", "1")},
        {"classification": "c_*", "tagFilters": where("level", "=", "1")},
    ):
        with pytest.raises(AtlasError) as failed:
            await search(store, **body)
        failures.append(failed.value.message)

    assert failures == [
        "Attribute level not found for type c_tabular",
        "Attribute level not found for type _ALL_CLASSIFICATION_TYPES",
        "TagFilters specified with wildcard tag name",
    ]


@pytest.mark.covers(
    "aurelius_atlas_core.search_fields.search_fields",
    "aurelius_atlas_core.entity_store.EntityStore.classifications_of_types",
    rules=["CSR-05"],
)
async def test__entities_carry_and_match_their_classification_names(store: EntityStore) -> None:
    """``a`` has ``|c_pii|`` attached, ``b`` propagated; entity filters match them as pipe-separated names."""
    a = await store.get(GUIDS["a"])
    b = await store.get(GUIDS["b"])
    assert a is not None
    assert b is not None
    on_a, on_b = a.entity.search or {}, b.entity.search or {}

    assert (on_a["keyword.__classificationNames"], on_a["keyword.__traitNames"]) == ("|c_pii|", ["c_pii"])
    assert (on_b["keyword.__propagatedClassificationNames"], on_b["keyword.__propagatedTraitNames"]) == (
        "|c_pii|",
        ["c_pii"],
    )
    assert "keyword.__classificationNames" not in on_b
    assert await names(store, typeName="p_data", entityFilters=where("__classificationNames", "=", "c_pii")) == ["a"]
    assert await names(
        store, typeName="p_data", entityFilters=where("__propagatedClassificationNames", "startsWith", "c_p")
    ) == ["b"]
    assert len(await store.classifications_of_types(None)) == 2
