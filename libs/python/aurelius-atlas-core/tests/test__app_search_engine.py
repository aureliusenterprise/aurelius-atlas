"""The ``atlas-dev`` engine over the entity index (ASE-03 to ASE-11, DD-523 to DD-525), on the fake client.

Small sets of entity documents written for one test show each rule; the sample catalogue, imported and indexed
once, answers the webapp's search page as ``atlas-dev`` did.
"""

import asyncio
import json
from collections import Counter
from functools import cache
from pathlib import Path
from typing import Any

import pytest
from aurelius_atlas_core.app_search_document import own_document
from aurelius_atlas_core.app_search_engine import FIELDS, AppSearchEngine, AppSearchError, parse, query_body
from aurelius_atlas_core.app_search_indexer import AppSearchIndexer
from aurelius_atlas_core.entity_documents import ElasticsearchEntityDocuments
from aurelius_atlas_core.entity_store import EntityStore
from aurelius_atlas_core.entity_writer import EntityWriter
from aurelius_atlas_core.import_service import ImportService
from aurelius_atlas_core.model_loader import BUILTIN_MODELS_DIR, M4I_MODELS_DIR, ModelLoader
from aurelius_atlas_core.stored_entity import StoredEntity
from aurelius_atlas_core.testing.memory import MemoryTypedefDocument
from aurelius_atlas_core.typedef_store import TypedefStore
from aurelius_atlas_model.impexp import AtlasImportRequest
from aurelius_atlas_model.instance import EntityStatus
from aurelius_atlas_store_es.testing.fake import FakeClient
from aurelius_atlas_typesystem.registry import TypeRegistry

E = "aurelius_atlas_core.app_search_engine"
X = f"{E}.AppSearchEngine.search"
FIXTURES = Path(__file__).parent / "fixtures"
SAMPLE = Path(__file__).parents[4] / "data" / "atlas-sample" / "sample_data.zip"

ENTITY_SEARCH_FIELDS = {
    name: {"raw": {}}
    for name in (
        "typename",
        "breadcrumbguid",
        "breadcrumbname",
        "breadcrumbtype",
        "deriveddataentity",
        "deriveddataset",
        "derivedsystem",
        "guid",
        "derivedperson",
        "id",
        "name",
        "derivedcollection",
        "deriveddatadomain",
        "deriveddataattribute",
        "derivedfield",
        "dqscore_overall",
        "dqscorecnt_overall",
        "supertypenames",
    )
} | {"definition": {"raw": {}, "snippet": {"size": 100, "fallback": True}}}
"""The search page's result fields (``entity-search.service.ts``), the score fields shortened to one pair."""

ENTITY_SEARCH_FACETS = {
    name: {"type": "value", "size": 100}
    for name in (
        "supertypenames",
        "deriveddataentity",
        "deriveddataset",
        "derivedsystem",
        "derivedperson",
        "deriveddatadomain",
        "derivedcollection",
        "sourcetype",
    )
}
"""The search page's facets (``entity-search.service.ts``)."""


def stored(guid: str, type_name: str = "m4i_data_entity", **fields: Any) -> StoredEntity:  # noqa: ANN401
    """An entity named ``guid`` upper-cased, with its App Search document and ``fields`` of it."""
    entity = StoredEntity(
        guid=guid,
        type_name=type_name,
        attributes={"Referenceable.qualifiedName": guid, "Asset.name": guid.upper()} | fields.pop("attributes", {}),
    )
    return entity.model_copy(update={"app_search": own_document(entity).model_copy(update=fields)})


async def engine_of(*entities: StoredEntity) -> AppSearchEngine:
    """An engine over the entities, written to a fake store."""
    documents = ElasticsearchEntityDocuments(FakeClient())  # type: ignore[arg-type]
    await documents.prepare()
    await documents.write([(entity, None) for entity in entities])
    return AppSearchEngine(documents)


def guids(answer: dict[str, Any]) -> list[str]:
    """The results' ids in order."""
    return [result["id"]["raw"] for result in answer["results"]]


def refused(body: object) -> list[str]:
    """The messages of the refusal of ``body``."""
    with pytest.raises(AppSearchError) as refusal:
        parse(body)
    assert refusal.value.status == 400
    return refusal.value.messages


@pytest.mark.covers(f"{E}._fields", rules=["ASE-03", "LAS-07"])
def test__the_engine_s_fields_are_atlas_dev_s() -> None:
    """Every field of the legacy documents, and no other; LAS-07's constants and the scores' empty values."""
    legacy = json.loads(FIXTURES.joinpath("legacy-app-search-atlas-dev.json").read_text())

    assert set(FIELDS) == set(legacy[0])
    assert FIELDS["entityname"].constant is None
    assert FIELDS["classificationstext"].constant == []
    assert FIELDS["businessruleid"].constant == 0.0
    assert all(FIELDS[f"dqscore_{d}"].constant == 0.0 for d in ("overall", "accuracy", "validity"))


@pytest.mark.covers(X, rules=["ASE-03", "ASE-10", "ASE-11"])
async def test__a_document_answers_its_entity_s_fields_stored_fields_and_constants() -> None:
    """Every field as raw when none is asked for; ``id`` and ``_meta``; meta as App Search's."""
    engine = await engine_of(stored("e", deriveddatasetguid=["s"], deriveddataset=["S"]))

    answer = await engine.search({})

    (result,) = answer["results"]
    assert set(result) == {*FIELDS, "_meta"}
    assert result["id"] == result["guid"] == {"raw": "e"}
    assert (result["typename"]["raw"], result["supertypenames"]["raw"]) == ("m4i_data_entity", ["m4i_data_entity"])
    assert (result["name"]["raw"], result["deriveddataset"]["raw"]) == ("E", ["S"])
    assert (result["entityname"]["raw"], result["dqscore_overall"]["raw"], result["qualityguid_validity"]["raw"]) == (
        None,
        0.0,
        [],
    )
    assert result["_meta"] == {"id": "e", "engine": "atlas-dev", "score": 0.0}
    meta = answer["meta"]
    assert {key: meta[key] for key in ("alerts", "warnings", "precision", "engine")} == {
        "alerts": [],
        "warnings": [],
        "precision": 2,
        "engine": {"name": "atlas-dev", "type": "default"},
    }
    assert meta["page"] == {"current": 1, "total_pages": 1, "total_results": 1, "size": 10}
    assert len(meta["request_id"]) == 32
    assert answer["facets"] == {}


@pytest.mark.covers(X, rules=["ASE-03"])
async def test__stale_documents_are_answered_and_deleted_or_unindexed_entities_are_not() -> None:
    """A stale document with its old fields; a deleted entity's document and an entity without one are not (DD-524)."""
    fresh = stored("fresh")
    stale = stored("stale").model_copy(update={"attributes": {"Asset.name": "Renamed"}})
    deleted = stored("deleted").model_copy(update={"state": EntityStatus.DELETED})
    bare = StoredEntity(guid="bare", type_name="m4i_data_entity")
    engine = await engine_of(fresh, stale, deleted, bare)

    answer = await engine.search({"result_fields": {"name": {"raw": {}}}})

    assert guids(answer) == ["fresh", "stale"]
    assert answer["results"][1]["name"] == {"raw": "STALE"}


@pytest.mark.covers(X, rules=["ASE-05"])
@pytest.mark.covers(f"{E}.query_body", rules=["ASE-05"])
async def test__a_query_s_words_match_the_text_fields_more_matches_first() -> None:
    """Any word matches; the document matching in more fields ranks first; ``search_fields`` narrows and weighs."""
    engine = await engine_of(
        stored("a", definition="Customer orders"),
        stored("b", definition="Orders", deriveddataset=["Customer master"]),
        stored("c", definition="Invoices"),
    )

    found = await engine.search({"query": "customer orders"})
    narrowed = await engine.search({"query": "customer", "search_fields": {"deriveddataset": {"weight": 3}}})
    body = query_body(parse({"query": "x", "search_fields": {"name": {"weight": 2}, "guid": {}}}))

    assert guids(found) == ["b", "a"]
    assert guids(narrowed) == ["b"]
    assert body["query"]["bool"]["must"][0]["simple_query_string"]["fields"] == ["appSearch.name.text^2", "guid"]
    assert guids(await engine.search({"query": "   "})) == ["a", "b", "c"]


@pytest.mark.covers(X, rules=["ASE-06"])
async def test__filters_match_values_ranges_and_nested_all_any_and_none() -> None:
    """The relationship editor's nested filter, a list of values, a top-level field, constants decided at once."""
    engine = await engine_of(
        stored("a", sourcetype="Business"),
        stored("b", "m4i_dataset", sourcetype="Technical"),
        stored("c", "m4i_dataset", sourcetype="Technical"),
    )

    async def found(filters: object) -> list[str]:
        return guids(await engine.search({"filters": filters}))

    assert await found({"all": [{"all": [{"supertypenames": ["m4i_dataset"]}], "none": [{"guid": ["b"]}]}]}) == ["c"]
    assert await found({"sourcetype": "Business"}) == ["a"]
    assert await found({"any": [{"guid": ["a"]}, {"guid": ["c"]}]}) == ["a", "c"]
    assert await found({"guid": ["a", "b"], "typename": ["m4i_dataset"]}) == ["b"]
    assert await found({"all": [{"deriveddataownerguid": ["a"]}]}) == []
    assert await found({"dqscore_overall": {"from": 0, "to": 1}}) == ["a", "b", "c"]
    assert await found({"dqscore_overall": {"from": 0.5}}) == []
    assert await found({"none": [{"businessruleid": [0]}]}) == []
    assert await found({"any": []}) == []


@pytest.mark.covers(f"{E}.parse", rules=["ASE-04", "ASE-06", "ASE-07", "ASE-08", "ASE-09", "ASE-10"])
def test__a_request_app_search_refuses_is_answered_with_each_problem() -> None:
    """One message per problem, all of them; other keys are ignored (DD-527)."""
    assert refused([]) == ["The request body must be a JSON object"]
    messages = refused(
        {
            "query": 1,
            "filters": {"unknown": ["x"], "guid": [1], "name": {"from": 1}},
            "facets": {"name": {"type": "range"}, "guid": {"type": "value", "size": 251}},
            "sort": [{"name": "up"}, {"nope": "asc"}],
            "page": {"current": 101, "size": 0},
            "result_fields": {"dqscore_overall": {"snippet": {"size": 10}}},
            "search_fields": {"dqscore_overall": {}},
            "group": {"field": "name"},
        }
    )

    assert messages == [
        "Query must be a string",
        "Filters contains an unknown field: unknown",
        "Filter value for guid must be a string",
        "Filter for name must be a value or a list of values: it is a text field",
        "Range facets are not supported: name",
        "Facet size for guid must be between 1 and 250",
        "Sort direction for name must be asc or desc",
        "Sort contains an unknown field: nope",
        "Page current must be between 1 and 100",
        "Page size must be between 1 and 1000",
        "Snippets are only for text fields: dqscore_overall",
        "Snippet size for dqscore_overall must be at least 20 and at most 1000",
        "Search fields must be text fields: dqscore_overall",
    ]
    assert parse({"precision": 5, "boosts": {}, "analytics": {"tags": ["x"]}}).query == ""


@pytest.mark.covers(X, rules=["ASE-07"])
async def test__facets_count_the_matches_values_most_first_or_by_value() -> None:
    """Over the filtered documents; ``size``; by value; a list of facets; empty values left out; constants."""
    engine = await engine_of(
        stored("a", deriveddataset=["S1", "S2"], sourcetype=""),
        stored("b", deriveddataset=["S2"], sourcetype="Business"),
        stored("c", "m4i_dataset", deriveddataset=["S3"], sourcetype="Technical"),
    )

    answer = await engine.search(
        {
            "filters": {"typename": ["m4i_data_entity"]},
            "facets": {
                "deriveddataset": [{"type": "value", "size": 1}, {"type": "value", "sort": {"value": "desc"}}],
                "sourcetype": {"type": "value"},
                "dqscore_overall": {"type": "value"},
                "deriveddataownerguid": {"type": "value"},
            },
        }
    )

    facets = answer["facets"]
    assert list(facets) == ["deriveddataset", "sourcetype", "dqscore_overall", "deriveddataownerguid"]
    assert facets["deriveddataset"] == [
        {"type": "value", "data": [{"value": "S2", "count": 2}]},
        {"type": "value", "data": [{"value": "S2", "count": 2}, {"value": "S1", "count": 1}]},
    ]
    assert facets["sourcetype"] == [{"type": "value", "data": [{"value": "Business", "count": 1}]}]
    assert facets["dqscore_overall"] == [{"type": "value", "data": [{"value": 0.0, "count": 2}]}]
    assert facets["deriveddataownerguid"] == [{"type": "value", "data": []}]


@pytest.mark.covers(X, rules=["ASE-08"])
@pytest.mark.covers(f"{E}._sort_clauses", rules=["ASE-08"])
async def test__a_sort_orders_by_fields_or_score_arrays_by_their_ends_ties_by_id() -> None:
    """By name both ways; an array by its least ascending and greatest descending; a constant sorts nothing."""
    engine = await engine_of(
        stored("a", name="Beta", deriveddataset=["M", "Z"]),
        stored("b", name="Alpha", deriveddataset=["N"]),
        stored("c", name="Beta", deriveddataset=["A", "B"]),
    )

    assert guids(await engine.search({"sort": {"name": "asc"}})) == ["b", "a", "c"]
    assert guids(await engine.search({"sort": [{"name": "desc"}]})) == ["a", "c", "b"]
    assert guids(await engine.search({"sort": {"deriveddataset": "asc"}})) == ["c", "a", "b"]
    assert guids(await engine.search({"sort": {"deriveddataset": "desc"}})) == ["a", "b", "c"]
    assert guids(await engine.search({"sort": {"dqscore_overall": "desc"}})) == ["a", "b", "c"]
    assert query_body(parse({}))["sort"] == [{"_score": {"order": "desc"}}, {"guid": {"order": "asc"}}]


@pytest.mark.covers(X, rules=["ASE-09"])
@pytest.mark.covers(f"{E}.query_body", rules=["ASE-09"])
async def test__pages_answer_their_slice_and_the_totals_and_nothing_past_the_window() -> None:
    """Page 2 of size 2 of five; the pages rounded up; a page past the 10,000th result is empty."""
    engine = await engine_of(*(stored(f"e{index}") for index in range(5)))

    answer = await engine.search({"page": {"current": 2, "size": 2}})
    past = query_body(parse({"page": {"current": 11, "size": 1000}}))
    edge = query_body(parse({"page": {"current": 11, "size": 999}}))

    assert guids(answer) == ["e2", "e3"]
    assert answer["meta"]["page"] == {"current": 2, "total_pages": 3, "total_results": 5, "size": 2}
    assert (past["from_"], past["size"]) == (10_000, 0)
    assert (edge["from_"], edge["size"]) == (9990, 10)


@pytest.mark.covers(X, rules=["ASE-10"])
@pytest.mark.covers(f"{E}._snippet", rules=["ASE-10"])
async def test__results_hold_the_fields_asked_raw_cut_and_snippets_escaped_with_the_words_marked() -> None:
    """``raw.size`` cuts texts; a snippet marks the query's words, escaped; without a match only a fallback."""
    engine = await engine_of(stored("a", definition="Orders & <b>invoices</b> of a customer"))
    fields = {
        "name": {"raw": {"size": 20}},
        "definition": {"snippet": {"size": 20, "fallback": True}},
        "deriveddataset": {"raw": {}, "snippet": {"size": 20}},
    }

    matched = await engine.search({"query": "orders", "result_fields": fields})
    unmatched = await engine.search({"query": "customer", "result_fields": fields})
    cut = await engine.search({"result_fields": {"definition": {"raw": {"size": 20}}}})

    (result,) = matched["results"]
    assert set(result) == {"id", "name", "definition", "deriveddataset", "_meta"}
    assert result["definition"] == {"snippet": "<em>Orders</em> &amp; &lt;b&gt;invoices"}
    assert result["deriveddataset"] == {"raw": [], "snippet": None}
    assert unmatched["results"][0]["definition"] == {"snippet": "Orders &amp; &lt;b&gt;invoices"}
    assert cut["results"][0]["definition"] == {"raw": "Orders & <b>invoices"}
    assert result["_meta"]["score"] > 0


_SAMPLE: dict[str, AppSearchEngine] = {}


@cache
def sample() -> AppSearchEngine:
    """The sample catalogue imported into the fake store and indexed once for the module."""

    async def build() -> AppSearchEngine:
        types = TypedefStore(TypeRegistry(), MemoryTypedefDocument())
        await types.load()
        for models_dir in (BUILTIN_MODELS_DIR, M4I_MODELS_DIR):
            await ModelLoader(types).load(models_dir)
        documents = ElasticsearchEntityDocuments(FakeClient())  # type: ignore[arg-type]
        store = EntityStore(types.registry, documents)
        await store.prepare()
        result = await ImportService(store, types, EntityWriter(store, user="importer")).run(
            SAMPLE.read_bytes(), AtlasImportRequest(), "importer", "h", "ip"
        )
        assert result.operation_status.value == "SUCCESS"
        await AppSearchIndexer(documents, types.registry).run_once()
        return AppSearchEngine(documents)

    return asyncio.run(build())


@cache
def legacy() -> list[dict[str, Any]]:
    """``atlas-dev``'s documents."""
    return json.loads(FIXTURES.joinpath("legacy-app-search-atlas-dev.json").read_text())


def legacy_counts(field: str) -> dict[str, int]:
    """The legacy documents' value counts of a field, empty values left out."""
    counts: Counter[str] = Counter()
    for document in legacy():
        values = document[field] if isinstance(document[field], list) else [document[field]]
        counts.update(value for value in set(values) if value not in ("", None))
    return dict(counts)


@pytest.mark.covers(X, rules=["ASE-03", "ASE-07", "ASE-09"])
def test__the_search_page_s_first_request_answers_the_sample_as_atlas_dev_did() -> None:
    """All 684 documents; the type and source type facets count what ``atlas-dev`` counted."""
    answer = asyncio.run(
        sample().search(
            {
                "query": "",
                "page": {"current": 1, "size": 5},
                "result_fields": ENTITY_SEARCH_FIELDS,
                "facets": ENTITY_SEARCH_FACETS,
            }
        )
    )

    assert answer["meta"]["page"] == {"current": 1, "total_pages": 137, "total_results": 684, "size": 5}
    assert len(answer["results"]) == 5
    for field in ("supertypenames", "sourcetype"):
        (facet,) = answer["facets"][field]
        assert {entry["value"]: entry["count"] for entry in facet["data"]} == legacy_counts(field)


@pytest.mark.covers(X, rules=["ASE-03", "ASE-06"])
def test__a_details_card_s_filter_finds_what_atlas_dev_held() -> None:
    """A data domain's entities: the documents of type ``m4i_data_entity`` whose domain is the domain (LAS-05)."""
    domain = next(document for document in legacy() if document["typename"] == "m4i_data_domain")
    expected = sorted(
        document["guid"]
        for document in legacy()
        if document["typename"] == "m4i_data_entity" and domain["guid"] in document["deriveddatadomainguid"]
    )

    answer = asyncio.run(
        sample().search(
            {
                "filters": {"all": [{"typename": ["m4i_data_entity"]}, {"deriveddatadomainguid": [domain["guid"]]}]},
                "page": {"size": 100},
                "result_fields": {"guid": {"raw": {}}},
            }
        )
    )

    assert expected
    assert guids(answer) == expected
