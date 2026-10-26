"""Quick search and suggestions (QSR-02 to QSR-04, SUG-01, SUG-02, DD-093, DD-094) on the in-memory documents.

The rules are read from ``EntityDiscoveryService.quickSearch``, ``SearchAggregatorImpl``,
``SuggestionsProviderImpl`` and ``AtlasJanusGraphIndexClient`` of Apache Atlas 2.4.0.
"""

from typing import Any

import pytest
from aurelius_atlas_core.discovery_service import EntityDiscoveryService
from aurelius_atlas_core.entity_store import EntityStore
from aurelius_atlas_core.entity_writer import EntityWriter
from aurelius_atlas_core.free_text import field_terms, suggestion_fields, top_terms
from aurelius_atlas_core.search_aggregator import SearchAggregator
from aurelius_atlas_core.search_query import facet_counts
from aurelius_atlas_core.suggestions_provider import SuggestionsProvider, index_field
from aurelius_atlas_core.testing.entity_samples import sample_registry
from aurelius_atlas_core.testing.memory import MemoryEntityDocuments
from aurelius_atlas_model.discovery import QuickSearchParameters
from aurelius_atlas_model.instance import AtlasEntitiesWithExtInfo
from aurelius_atlas_model.typedef import AtlasTypesDef
from aurelius_atlas_typesystem.registry import TypeRegistry

D = "aurelius_atlas_core.discovery_service.EntityDiscoveryService.quick_search"
A = "aurelius_atlas_core.search_aggregator.SearchAggregator"
P = "aurelius_atlas_core.suggestions_provider"


def _string(name: str, **more: Any) -> dict[str, Any]:  # noqa: ANN401 - typedef JSON
    return {"name": name, "typeName": "string", "isOptional": True, "cardinality": "SINGLE", **more}


ASSET_TYPES = {
    "entityDefs": [
        {
            "name": "Asset",
            "serviceType": "atlas_core",
            "attributeDefs": [
                _string("qualifiedName", isUnique=True, isIndexable=True, searchWeight=10),
                _string("name", searchWeight=10),
                _string("owner", indexType="STRING"),
                {"name": "size", "typeName": "int", "isOptional": True, "cardinality": "SINGLE"},
            ],
        },
        {"name": "q_table", "superTypes": ["Asset"], "serviceType": "q_db"},
        {"name": "q_view", "superTypes": ["q_table"], "serviceType": "q_db"},
        {"name": "q_file", "superTypes": ["Asset"], "serviceType": "q_fs"},
        {"name": "q_spare", "superTypes": ["Asset"], "serviceType": "q_spare"},
        {"name": "q_plain", "superTypes": ["Asset"]},
    ]
}


def registry_with_assets() -> TypeRegistry:
    """The sample types and ``Asset`` with sub types of three service types and one of none."""
    registry = sample_registry()
    with registry.update() as transient:
        transient.add_types(AtlasTypesDef.model_validate(ASSET_TYPES))
    return registry


@pytest.fixture
async def store() -> EntityStore:
    """Tables ``plum one``, ``plum two`` (``bob``), a view ``plums``, a file ``apple``, a ``plain`` entity."""
    found = EntityStore(registry_with_assets(), MemoryEntityDocuments())

    def asset(type_name: str, name: str, owner: str | None = "ann") -> dict[str, Any]:
        attributes = {"qualifiedName": f"{name}@q", "name": name, "owner": owner}
        return {"typeName": type_name, "guid": f"-{name}", "attributes": attributes}

    entities = [
        asset("q_table", "plum one"),
        asset("q_table", "plum two", "bob"),
        asset("q_view", "plums"),
        asset("q_file", "apple"),
        asset("q_plain", "plain plum", None),
    ]
    await EntityWriter(found).create_or_update(AtlasEntitiesWithExtInfo.model_validate({"entities": entities}))
    return found


async def quick(store: EntityStore, **body: Any) -> dict[str, Any]:  # noqa: ANN401 - Atlas JSON
    """The answer to a quick search, as JSON."""
    found = await EntityDiscoveryService(store).quick_search(QuickSearchParameters.model_validate(body))
    return found.to_json()


def names(result: dict[str, Any]) -> list[str]:
    """The names of the entities found, in order."""
    return [entity["attributes"]["name"] for entity in result["searchResults"].get("entities", [])]


@pytest.mark.covers(D, rules=["QSR-02"])
async def test__a_quick_search_is_a_basic_search_of_the_query_as_a_prefix(store: EntityStore) -> None:
    """``*`` appended to a plain query only; sub types only when asked; sorted and paged as basic search."""
    plain = await quick(store, query="plum")
    spaced = await quick(store, query="plum two")
    tables = await quick(store, typeName="q_table", sortBy="name", sortOrder="DESCENDING")
    with_views = await quick(store, typeName="q_table", includeSubTypes=True, limit=2, sortBy="name")

    assert plain["searchResults"]["queryText"] == "plum*"
    assert plain["searchResults"]["searchParameters"]["includeSubTypes"] is False
    assert sorted(names(plain)) == ["plain plum", "plum one", "plum two", "plums"]
    assert spaced["searchResults"]["queryText"] == "plum two"
    assert sorted(names(spaced)) == ["plain plum", "plum one", "plum two"]
    assert names(tables) == ["plum two", "plum one"]
    assert names(with_views) == ["plum one", "plum two"]
    assert with_views["searchResults"]["approximateCount"] == 3


@pytest.mark.covers(D, f"{A}.aggregated_metrics", "aurelius_atlas_core.search_query.facet_counts", rules=["QSR-03"])
async def test__facets_count_every_entity_found_by_type_state_and_owner(store: EntityStore) -> None:
    """Unpaged, most first then by value, no zero counts; arrays by element, missing values left out."""
    found = await quick(store, query="plum", limit=1)
    metrics = found["aggregationMetrics"]

    assert len(names(found)) == 1
    assert metrics["__typeName"] == [
        {"name": "q_table", "count": 2},
        {"name": "q_plain", "count": 1},
        {"name": "q_view", "count": 1},
    ]
    assert metrics["__state"] == [{"name": "ACTIVE", "count": 4}]
    assert metrics["Asset.owner"] == [{"name": "ann", "count": 2}, {"name": "bob", "count": 1}]
    assert facet_counts([{"f": ["x", "y"]}, {"f": "x"}, {}], ["f", "g"]) == {"f": [("x", 2), ("y", 1)], "g": []}


@pytest.mark.covers(f"{A}.aggregated_metrics", rules=["QSR-04"])
async def test__service_types_add_up_the_type_counts(store: EntityStore) -> None:
    """Tables and views are ``q_db``; types without a service type and service types counted none are left out."""
    every = (await quick(store, query="plum* apple"))["aggregationMetrics"]
    nothing = (await quick(store, query="nothing"))["aggregationMetrics"]
    aggregator = SearchAggregator(sample_registry())

    assert every["ServiceType"] == [{"name": "q_db", "count": 3}, {"name": "q_fs", "count": 1}]
    assert "ServiceType" not in nothing
    assert nothing["__typeName"] == []
    assert list(aggregator.fields) == ["__typeName", "__state"]
    assert aggregator.aggregated_metrics({}) == {"__typeName": [], "__state": [], "Asset.owner": []}


@pytest.mark.covers(
    f"{P}.SuggestionsProvider.suggestions",
    "aurelius_atlas_core.free_text.suggestion_fields",
    "aurelius_atlas_core.free_text.field_terms",
    "aurelius_atlas_core.free_text.top_terms",
    "aurelius_atlas_core.entity_store.EntityStore.terms",
    rules=["SUG-01"],
)
async def test__suggestions_are_the_most_frequent_words_of_the_heaviest_fields(store: EntityStore) -> None:
    """Words of the fields weighted 8 or more beginning with the prefix, case-sensitively, summed over fields."""
    provider = SuggestionsProvider(store)

    plum = (await provider.suggestions("plum", None)).to_json()
    every = (await provider.suggestions(None, None)).to_json()
    upper = (await provider.suggestions("PLUM", None)).to_json()

    assert suggestion_fields(store.registry)[:2] == ["keyword.__classificationsText", "keyword.__labels"]
    assert "keyword.Asset.owner" not in suggestion_fields(store.registry)
    assert plum == {"prefixString": "plum", "suggestions": ["plum", "plums"]}
    assert len(every["suggestions"]) == 5
    assert every["suggestions"][:2] == ["plum", "q"]
    assert upper["suggestions"] == []
    assert field_terms([{"f": "A b"}, {"f": ["a", "c"]}], "f", "") == [("a", 2), ("b", 1), ("c", 1)]
    assert top_terms({"f": [("a", 1), ("b", 2)], "g": [("a", 2)]}) == ["a", "b"]


@pytest.mark.covers(f"{P}.index_field", rules=["SUG-02"])
async def test__a_field_name_reads_that_field_alone(store: EntityStore) -> None:
    """A system attribute or ``<type>.<attribute>`` the type defines; others ignored; numbers suggest nothing."""
    provider = SuggestionsProvider(store)

    owner = (await provider.suggestions("a", "Asset.owner")).to_json()
    state = (await provider.suggestions("A", "__state")).to_json()
    size = (await provider.suggestions("", "Asset.size")).to_json()
    inherited = (await provider.suggestions("plum", "q_table.name")).to_json()

    assert owner == {"prefixString": "a", "fieldName": "Asset.owner", "suggestions": ["ann"]}
    assert state["suggestions"] == []
    assert size["suggestions"] == []
    assert inherited["suggestions"][0] == "plum"
    assert index_field(store.registry, "__typeName") == "keyword.__typeName"
    assert index_field(store.registry, "Asset.name") == "keyword.Asset.name"
    assert index_field(store.registry, "q_table.name") is None
    assert index_field(store.registry, "nope.name") is None
    assert index_field(store.registry, "s_table.db") is None
