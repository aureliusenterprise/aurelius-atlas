"""``SearchDocuments``: the one search the engines run, on a narrow contract (QRY-05, DD-770).

The engines are typed against the protocol, not the concrete class, so a spec hands them a small fake for the one
method they call — the pattern ``FakeEmbedder`` uses — and the Elasticsearch documents satisfy the protocol as
they are. The in-memory store answers the basic and terms searches it always answered, and deliberately does not
satisfy this contract: an App Search search there would be a third query engine (DD-770).
"""

import asyncio
from typing import Any, cast

import pytest
from aurelius_atlas_core.app_search_engine import AppSearchEngine
from aurelius_atlas_core.entity_documents import ENTITY_DOCUMENTS, ElasticsearchEntityDocuments, SearchDocuments
from aurelius_atlas_core.search_fields import search_fields
from aurelius_atlas_core.search_query import SearchQuery
from aurelius_atlas_core.stored_entity import StoredEntity
from aurelius_atlas_core.testing.memory import MemoryEntityDocuments
from aurelius_atlas_core.view_search import ViewSearchEngine
from aurelius_atlas_store_es.testing.fake import FakeClient
from aurelius_atlas_typesystem.registry import TypeRegistry
from elasticsearch import AsyncElasticsearch
from test__app_search_quality import m4i_types

E = "aurelius_atlas_core.entity_documents.SearchDocuments.search_app_search"


@pytest.fixture
def m4i() -> TypeRegistry:
    """Atlas's and the data dictionary's types (ADR 058), the door's registry."""
    return asyncio.run(m4i_types()).registry


class OnlySearch:
    """A ``SearchDocuments`` answering one canned response, and recording the search it was handed."""

    def __init__(self, response: dict[str, Any] | None = None) -> None:
        """The contract, answering ``response`` for every search; empty hits by default."""
        self.calls: list[dict[str, Any]] = []
        self._response = response or {"hits": {"total": {"value": 0}, "hits": []}}

    async def search_app_search(self, **kwargs: Any) -> dict[str, Any]:  # noqa: ANN401 - the search's body
        """Record what the engine built, and answer the canned response."""
        self.calls.append(kwargs)
        return self._response


def response_of(*sources: dict[str, Any]) -> dict[str, Any]:
    """A search response of these ``_source`` documents, in order."""
    return {
        "hits": {
            "total": {"value": len(sources)},
            "hits": [{"_source": source, "_score": 1.0} for source in sources],
        },
        "aggregations": {},
    }


@pytest.mark.covers(E, rules=["QRY-05"])
async def test__the_engine_runs_on_the_contract_alone() -> None:
    """A purpose-built fake, no Elasticsearch: the engine hands its whole search down and answers it."""
    documents = OnlySearch(response_of({"guid": "a", "typeName": "m4i_data_entity"}))
    answer = await AppSearchEngine(documents).search({"result_fields": {"guid": {"raw": {}}}})
    assert [result["id"]["raw"] for result in answer["results"]] == ["a"]
    assert answer["meta"]["page"]["total_results"] == 1
    asked = documents.calls[0]
    assert asked["index"] == ENTITY_DOCUMENTS
    assert set(asked) == {"query", "knn", "sort", "aggs", "from_", "size", "index"}


@pytest.mark.covers(E, rules=["QRY-05"])
async def test__the_door_runs_on_the_contract_alone(m4i: TypeRegistry) -> None:
    """The same for the view door: its cards are the response's stored entities."""
    entity = StoredEntity(guid="a", type_name="m4i_data_entity", attributes={"Asset.name": "Sales"})
    documents = OnlySearch(response_of(entity.to_json()))
    answer = await ViewSearchEngine(documents, m4i).search({})
    assert [card["guid"] for card in answer["cards"]] == ["a"]
    assert answer["total"] == 1


@pytest.mark.covers(
    "aurelius_atlas_core.entity_documents.ElasticsearchEntityDocuments.search_app_search", rules=["QRY-05"]
)
async def test__the_elasticsearch_documents_satisfy_the_contract() -> None:
    """The concrete store satisfies the protocol unchanged (DD-770)."""
    documents = ElasticsearchEntityDocuments(cast("AsyncElasticsearch", FakeClient()))
    assert isinstance(documents, SearchDocuments)
    assert isinstance(OnlySearch(), SearchDocuments)


@pytest.mark.covers(
    "aurelius_atlas_core.testing.memory.MemoryEntityDocuments.search",
    "aurelius_atlas_core.testing.memory.MemoryEntityDocuments.terms",
    rules=["QRY-05"],
)
async def test__the_memory_store_answers_its_two_searches_and_not_the_engine_one(m4i: TypeRegistry) -> None:
    """The in-memory store answers the basic and terms searches, and stays off the App Search contract (DD-770)."""
    store = MemoryEntityDocuments()
    entity_type = m4i.entity_type("m4i_data_entity")
    assert entity_type is not None
    name = entity_type.attribute("name")
    assert name is not None
    entity = StoredEntity(guid="a", type_name="m4i_data_entity", attributes={name.qualified_name: "Sales"})
    entity = entity.model_copy(update={"search": search_fields(entity, entity_type)})
    await store.write([(entity, None)])
    hits = await store.search(SearchQuery(type_names=None))
    assert [found.guid for found in hits.entities] == ["a"]
    field = f"keyword.{name.qualified_name}"
    assert (await store.terms([field], "sa"))[field] == [("sales", 1)]
    # No App Search search: the door would need a third query engine here (DD-770).
    assert not isinstance(store, SearchDocuments)
