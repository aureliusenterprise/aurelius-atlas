"""Free text (FTX-01 to FTX-05, DD-092) on the in-memory documents.

The rules are read from ``EntityDiscoveryService.searchWithParameters`` and ``searchUsingFullTextQuery``,
``FreeTextSearchProcessor``, ``SolrIndexHelper``, ``FullTextMapperV2.getClassificationTextForEntity`` and
``AtlasStructType.AtlasAttribute.hastokenizeChar`` of Apache Atlas 2.4.0.
"""

from typing import Any

import pytest
from aurelius_atlas_core.discovery_service import EntityDiscoveryService
from aurelius_atlas_core.entity_classifications import EntityClassifications
from aurelius_atlas_core.entity_store import EntityStore
from aurelius_atlas_core.entity_writer import EntityWriter
from aurelius_atlas_core.free_text import basic_query, has_tokenize_char, text_matches, weighted_fields
from aurelius_atlas_core.search_fields import classifications_text
from aurelius_atlas_core.testing.entity_samples import sample_registry
from aurelius_atlas_core.testing.memory import MemoryEntityDocuments
from aurelius_atlas_model.discovery import SearchParameters
from aurelius_atlas_model.instance import AtlasClassification, AtlasEntitiesWithExtInfo
from aurelius_atlas_model.typedef import AtlasTypesDef

F = "aurelius_atlas_core.free_text"
D = "aurelius_atlas_core.discovery_service.EntityDiscoveryService"
GUIDS: dict[str, str] = {}

WEIGHTED_TYPES = {
    "entityDefs": [
        {"name": "__internal"},
        {
            "name": "f_secret",
            "superTypes": ["__internal"],
            "attributeDefs": [{"name": "hidden", "typeName": "string", "isOptional": True, "cardinality": "SINGLE"}],
        },
        {
            "name": "f_doc",
            "superTypes": ["s_ref"],
            "attributeDefs": [
                {"name": "title", "typeName": "string", "isOptional": True, "cardinality": "SINGLE", "searchWeight": 9},
                {"name": "body", "typeName": "string", "isOptional": True, "cardinality": "SINGLE", "searchWeight": 11},
                {"name": "pages", "typeName": "int", "isOptional": True, "cardinality": "SINGLE", "searchWeight": 5},
            ],
        },
    ]
}


@pytest.fixture
async def store() -> EntityStore:
    """Documents ``d1`` to ``d3``, ``d3`` deleted; ``c_pii`` (level 7) on ``d2``."""
    registry = sample_registry(classifications=True)
    with registry.update() as transient:
        transient.add_types(AtlasTypesDef.model_validate(WEIGHTED_TYPES))
    found = EntityStore(registry, MemoryEntityDocuments())
    documents = [
        doc("d1", title="Sales report", body="quarterly numbers"),
        doc("d2", title="Customer list", body="sales contacts"),
        doc("d3", title="Old sales", body="archive"),
    ]
    created = await EntityWriter(found).create_or_update(
        AtlasEntitiesWithExtInfo.model_validate({"entities": documents})
    )
    GUIDS.clear()
    GUIDS.update({key.removeprefix("-"): value for key, value in (created.guid_assignments or {}).items()})
    tag = AtlasClassification.model_validate({"typeName": "c_pii", "attributes": {"level": 7}})
    await EntityClassifications(found).add_classifications(GUIDS["d2"], [tag])
    await EntityWriter(found).delete_by_id(GUIDS["d3"])
    return found


def doc(name: str, **attributes: Any) -> dict[str, Any]:  # noqa: ANN401 - Atlas JSON
    """An ``f_doc`` named ``name``."""
    return {"typeName": "f_doc", "guid": f"-{name}", "attributes": {"qualifiedName": name, "name": name, **attributes}}


async def search(store: EntityStore, **body: Any) -> dict[str, Any]:  # noqa: ANN401 - Atlas JSON
    """The answer to a search, as JSON."""
    return (await EntityDiscoveryService(store).search_with_parameters(SearchParameters.model_validate(body))).to_json()


async def names(store: EntityStore, **body: Any) -> list[str]:  # noqa: ANN401 - Atlas JSON
    """The qualified names a search finds, in order."""
    return [entity["attributes"]["qualifiedName"] for entity in (await search(store, **body)).get("entities", [])]


@pytest.mark.covers(f"{F}.has_tokenize_char", f"{F}.basic_query", rules=["FTX-01"])
def test__a_query_loses_its_stars_when_it_holds_a_tokenising_character() -> None:
    """``.``, ``:`` and ``'`` tokenise only next to a non-letter; any other non-word character and CJK always."""
    tokenising = ["a.1", "1:a", "a b", "a-b", "表", "ひ"]
    plain = ["abc_1", "a.b", "a:b", "it's", ".a", "a'", "カ", ""]

    assert [has_tokenize_char(value) for value in tokenising] == [True] * len(tokenising)
    assert [has_tokenize_char(value) for value in plain] == [False] * len(plain)
    assert [basic_query(query) for query in ("*sales*", "*a-b*", "**x y")] == ["*sales*", "a-b", "x y"]


@pytest.mark.covers(f"{F}.weighted_fields", f"{F}.text_matches", rules=["FTX-02"])
def test__the_searched_fields_are_weighted_string_attributes_and_system_fields() -> None:
    """``searchWeight`` 1 to 10, else 3; strings only; internal types left out; words match in any case."""
    registry = sample_registry()
    with registry.update() as transient:
        transient.add_types(AtlasTypesDef.model_validate(WEIGHTED_TYPES))
    weights = weighted_fields(registry)
    values = {"keyword.f_doc.title": "Sales Report", "keyword.f_doc.body": ["x", "salesman"], "keyword.__typeName": "f"}

    assert (weights["keyword.f_doc.title"], weights["keyword.f_doc.body"]) == (9, 3)
    assert (weights["keyword.__classificationsText"], weights["keyword.__typeName"]) == (10, 1)
    assert "long.f_doc.pages" not in weights
    assert "keyword.f_secret.hidden" not in weights
    assert text_matches("sales", values, weights) == 9
    assert text_matches("SALES* f", values, weights) == 9 + 3 + 1
    assert text_matches("nothing", values, weights) == 0


@pytest.mark.covers("aurelius_atlas_core.search_fields.classifications_text", rules=["FTX-03"])
async def test__classification_text_names_the_type_and_its_values(store: EntityStore) -> None:
    """The classified document is found by its classification's type name and attribute value."""
    d2 = await store.get(GUIDS["d2"])
    instances = await store.get_classifications(d2.entity.classification_guids or [] if d2 else [])

    assert classifications_text([found.classification for found in instances.values()]) == "c_pii 7 0"
    assert classifications_text([]) is None
    assert await names(store, query="c_pii") == ["d2"]
    assert await names(store, query="7") == ["d2"]


@pytest.mark.covers(f"{D}.search_with_parameters", rules=["FTX-04"])
async def test__a_basic_search_with_a_query_finds_the_best_match_first(store: EntityStore) -> None:
    """Weighted by field; with types, classifications and filters too; ``sortBy`` orders instead."""
    by_weight = await names(store, query="sales")
    active = await names(store, query="sales", excludeDeletedEntities=True)
    classified = await names(store, query="sales", classification="c_pii")
    sorted_ = await names(store, query="sales*", typeName="f_doc", sortBy="name", sortOrder="DESCENDING")
    filtered = await names(
        store,
        query="sales",
        typeName="f_doc",
        entityFilters={"attributeName": "name", "operator": "=", "attributeValue": "d2"},
    )
    stars = await search(store, query="*d1*")

    assert (set(by_weight[:2]), by_weight[2:]) == ({"d1", "d3"}, ["d2"])
    assert active[0] == "d1"
    assert sorted(active) == ["d1", "d2"]
    assert classified == ["d2"]
    assert sorted_ == ["d3", "d2", "d1"]
    assert filtered == ["d2"]
    assert stars["queryText"] == "*d1*"
    assert await names(store, query="nothing", typeName="f_doc") == []


@pytest.mark.covers(f"{D}.search_using_full_text", rules=["FTX-05"])
async def test__a_full_text_search_answers_headers_with_scores(store: EntityStore) -> None:
    """Best first, at most ``limit``, deleted ones left out but counted; ``offset`` unused (DV-49)."""
    service = EntityDiscoveryService(store)

    every = (await service.search_using_full_text("sales", exclude_deleted_entities=False, limit=0, offset=0)).to_json()
    active = (await service.search_using_full_text("sales", exclude_deleted_entities=True, limit=1, offset=5)).to_json()

    assert every["queryType"] == "FULL_TEXT"
    assert every["queryText"] == "sales"
    assert every["approximateCount"] == 3
    scores = [found["score"] for found in every["fullTextResult"]]
    assert scores == sorted(scores, reverse=True)
    assert scores[-1] == 3
    assert {found["entity"]["attributes"]["qualifiedName"] for found in every["fullTextResult"]} == {"d1", "d2", "d3"}
    assert [found["entity"]["attributes"]["qualifiedName"] for found in active["fullTextResult"]] == ["d1"]
    assert active["approximateCount"] == 3
    assert active["fullTextResult"][0]["entity"]["status"] == "ACTIVE"
