"""The ``atlas-dev`` engine over the entity index (ASE-03 to ASE-11, DD-523 to DD-525), and the quality and
governance engines (ASQ-02 to ASQ-06, ASG-05), on the fake client.

Small sets of entity documents written for one test show each rule; the sample catalogue, imported and indexed
once, answers the webapp's search page as ``atlas-dev`` did.
"""  # noqa: D205 - one sentence

import asyncio
import json
from collections import Counter
from functools import cache
from pathlib import Path
from typing import Any

import pytest
from aurelius_atlas_core.app_search_document import StoredVerdict, own_document
from aurelius_atlas_core.app_search_engine import (
    ATLAS_DEV,
    ATLAS_DEV_GOV_QUALITY,
    ATLAS_DEV_QUALITY,
    FIELDS,
    GOV_QUALITY_FIELDS,
    QUALITY_FIELDS,
    AppSearchEngine,
    AppSearchError,
    Engine,
    Kind,
    parse,
    query_body,
)
from aurelius_atlas_core.app_search_indexer import AppSearchIndexer
from aurelius_atlas_core.entity_documents import ElasticsearchEntityDocuments
from aurelius_atlas_core.entity_store import EntityStore
from aurelius_atlas_core.entity_writer import EntityWriter
from aurelius_atlas_core.import_service import ImportService
from aurelius_atlas_core.model_loader import BUILTIN_MODELS_DIR, M4I_MODELS_DIR, ModelLoader
from aurelius_atlas_core.stored_entity import (
    StoredDimensionTotals,
    StoredEntity,
    StoredQualityResult,
    StoredQualityTotals,
)
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


async def engine_of(*entities: StoredEntity, engine: Engine = ATLAS_DEV) -> AppSearchEngine:
    """``engine`` over the entities, written to a fake store."""
    documents = ElasticsearchEntityDocuments(FakeClient())  # type: ignore[arg-type]
    await documents.prepare()
    await documents.write([(entity, None) for entity in entities])
    return AppSearchEngine(documents, engine)


def scored(guid: str, rule: str, dimension: str, score: float, *fields: str) -> StoredEntity:
    """A score entity holding its result: ``rule``'s, named ``Rule <rule>``, over ``fields``."""
    result = StoredQualityResult(
        qualityguid=rule,
        qualityqualifiedname=f"{rule}--q",
        name=f"Rule {rule}",
        expression=f"completeness('{rule}')",
        dataqualityruledimension=dimension,
        businessruleid=1.0,
        fieldguid=list(fields),
        fieldqualifiedname=[f"{field}--q" for field in fields],
        datadomainname="Domain",
        dqscore=score,
    )
    return StoredEntity(guid=guid, type_name="m4i_dq_score", attributes={}, quality_result=result)


def with_totals(entity: StoredEntity, total: float, count: float, rules: list[str]) -> StoredEntity:
    """The entity holding accuracy totals, the overall the same."""
    accuracy = StoredDimensionTotals(total=total, count=count, score=total / count, rules=rules)
    overall = accuracy.model_copy(update={"rules": []})
    return entity.model_copy(update={"quality_totals": StoredQualityTotals(accuracy=accuracy, overall=overall)})


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
    """Every field of the legacy documents, and no other; LAS-07's constants; the scores 0 without totals."""
    legacy = json.loads(FIXTURES.joinpath("legacy-app-search-atlas-dev.json").read_text())

    assert set(FIELDS) == set(legacy[0])
    assert FIELDS["entityname"].constant is None
    assert FIELDS["classificationstext"].constant == []
    assert FIELDS["businessruleid"].constant == 0.0
    assert all(FIELDS[f"dqscore_{d}"].value({}) == 0.0 for d in ("overall", "accuracy", "validity"))
    assert all(FIELDS[f"dqscorecnt_{d}"].missing == 0.0 for d in ("overall", "accuracy", "validity"))
    assert FIELDS["qualityguid_accuracy"].value({}) == []


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


@pytest.mark.covers(f"{E}._quality_fields", rules=["ASQ-02", "ASQ-03", "LAS-11"])
def test__the_quality_engine_s_fields_are_atlas_dev_quality_s() -> None:
    """Every field of the legacy results, and no other; ``dqscore`` and ``businessruleid`` numbers, the rest text."""
    legacy_results = json.loads(FIXTURES.joinpath("legacy-app-search-atlas-dev-quality.json").read_text())

    assert set(QUALITY_FIELDS) == set(legacy_results[0])
    assert {name for name, field in QUALITY_FIELDS.items() if field.kind is Kind.NUMBER} == {
        "dqscore",
        "businessruleid",
    }
    assert all(field.constant is None and field.path is not None for field in QUALITY_FIELDS.values())


@pytest.mark.covers(X, rules=["ASQ-02", "ASQ-03"])
async def test__a_field_page_s_request_answers_the_field_s_results() -> None:
    """The field page's filter on ``fieldguid``, facet on the dimension and sorts; a word in a rule's name; the
    engine named; documents and deleted scores without a result left out.
    """  # noqa: D205 - one sentence
    engine = await engine_of(
        scored("s1", "r1", "Accuracy", 0.9, "f", "g"),
        scored("s2", "r2", "Validity", 0.5, "f"),
        scored("s3", "r3", "Validity", 0.7, "g"),
        scored("s4", "r4", "Validity", 0.1, "f").model_copy(update={"state": EntityStatus.DELETED}),
        stored("f", "m4i_field"),
        engine=ATLAS_DEV_QUALITY,
    )
    body = {
        "filters": {"all": [{"fieldguid": ["f"]}]},
        "facets": {"dataqualityruledimension": {"type": "value"}},
        "result_fields": {name: {"raw": {}} for name in ("guid", "name", "dqscore", "fieldguid", "businessruleid")},
    }

    by_score = await engine.search(body | {"sort": [{"dqscore": "desc"}]})
    by_name = await engine.search(body | {"sort": {"name": "desc"}})
    by_word = await engine.search({"query": "r3"})

    assert guids(by_score) == ["s1", "s2"]
    assert guids(by_name) == ["s2", "s1"]
    assert guids(by_word) == ["s3"]
    first = by_score["results"][0]
    assert first["guid"] == {"raw": "r1"}
    assert (first["name"], first["dqscore"], first["businessruleid"]) == (
        {"raw": "Rule r1"},
        {"raw": 0.9},
        {"raw": 1.0},
    )
    assert first["fieldguid"] == {"raw": ["f", "g"]}
    assert first["_meta"]["engine"] == by_score["meta"]["engine"]["name"] == "atlas-dev-quality"
    assert by_score["facets"]["dataqualityruledimension"] == [
        {"type": "value", "data": [{"value": "Accuracy", "count": 1}, {"value": "Validity", "count": 1}]}
    ]


@pytest.mark.covers(X, rules=["ASQ-04", "ASQ-06"])
@pytest.mark.covers(f"{E}._sort_clauses", rules=["ASQ-06"])
async def test__the_score_fields_read_filter_facet_and_sort_with_and_without_totals() -> None:
    """``a`` holds totals; ``b`` none, read, filtered, faceted and sorted as 0 (DD-530)."""
    engine = await engine_of(with_totals(stored("a"), 1.5, 2, ["r"]), stored("b"))

    async def found(body: dict[str, Any]) -> list[str]:
        return guids(await engine.search(body))

    answer = await engine.search({"sort": {"guid": "asc"}})
    a, b = answer["results"]
    assert (a["dqscore_accuracy"], a["dqscorecnt_accuracy"], a["dqscoresum_overall"]) == (
        {"raw": 0.75},
        {"raw": 2.0},
        {"raw": 1.5},
    )
    assert (a["qualityguid_accuracy"], a["qualityguid_validity"]) == ({"raw": ["r"]}, {"raw": []})
    assert (b["dqscore_accuracy"], b["dqscorecnt_overall"], b["qualityguid_accuracy"]) == (
        {"raw": 0.0},
        {"raw": 0.0},
        {"raw": []},
    )
    assert await found({"filters": {"dqscore_overall": [0]}}) == ["b"]
    assert await found({"filters": {"dqscore_overall": [0.75]}}) == ["a"]
    assert await found({"filters": {"dqscorecnt_overall": {"from": 1}}}) == ["a"]
    assert await found({"filters": {"dqscore_overall": {"to": 0.5}}}) == ["b"]
    assert await found({"filters": {"qualityguid_accuracy": ["r"]}}) == ["a"]
    assert await found({"sort": {"dqscore_overall": "desc"}}) == ["a", "b"]
    assert await found({"sort": {"dqscore_overall": "asc"}}) == ["b", "a"]
    facets = await engine.search({"facets": {"dqscorecnt_overall": {"type": "value", "sort": {"value": "asc"}}}})
    assert facets["facets"]["dqscorecnt_overall"] == [
        {"type": "value", "data": [{"value": 0.0, "count": 1}, {"value": 2.0, "count": 1}]}
    ]


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


async def indexed_sample() -> ElasticsearchEntityDocuments:
    """The sample catalogue imported into a new fake store, its documents indexed."""
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
    return documents


@cache
def sample() -> AppSearchEngine:
    """The sample catalogue imported into the fake store and indexed once for the module."""
    return AppSearchEngine(asyncio.run(indexed_sample()))


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


def verdict(entity: str, rule: str, compliant: str, **fields: str) -> StoredVerdict:
    """The verdict of ``rule`` on ``entity``, named ``Rule <rule>``, of the completeness dimension unless given."""
    pair = f"{entity}--{rule}"
    return StoredVerdict.model_validate(
        {
            "id": pair,
            "qualifiedname": pair,
            "guid": rule,
            "qualityqualifiedname": f"m4i_dataset--{rule}",
            "name": f"Rule {rule}",
            "expression": f"completeness('{rule}')",
            "dataqualitytype": "attribute",
            "dataqualityruledescription": f"About {rule}",
            "dataqualityruledimension": "completeness",
            "noncompliant_message": f"Misses {rule}",
            "usedattributes": [rule],
            "dataqualityruletypename": "m4i_dataset",
            "entity_guid": entity,
            "compliant": compliant,
            "result_id": "0",
            "business_rule_id": "1",
        }
        | fields
    )


async def gov_engine(*verdicts: StoredVerdict) -> AppSearchEngine:
    """``atlas-dev-gov-quality`` over the verdicts, written to a fake store."""
    documents = ElasticsearchEntityDocuments(FakeClient())  # type: ignore[arg-type]
    await documents.prepare()
    by_entity: dict[str, list[StoredVerdict]] = {}
    for found in verdicts:
        by_entity.setdefault(found.entity_guid, []).append(found)
    await documents.replace_verdicts(by_entity)
    return AppSearchEngine(documents, ATLAS_DEV_GOV_QUALITY)


@pytest.mark.covers(f"{E}._gov_quality_fields", rules=["ASG-03", "ASG-05", "LAS-13"])
def test__the_governance_engine_s_fields_are_the_legacy_schema_s() -> None:
    """Every field of the legacy verdicts and the schema's two never filled, all text."""
    legacy_verdicts = json.loads(FIXTURES.joinpath("legacy-app-search-atlas-dev-gov-quality.json").read_text())

    assert set(GOV_QUALITY_FIELDS) == {*legacy_verdicts[0], "result", "doc_guid"}
    assert all(field.kind is Kind.TEXT for field in GOV_QUALITY_FIELDS.values())
    assert GOV_QUALITY_FIELDS["result"].constant is GOV_QUALITY_FIELDS["doc_guid"].constant is None


@pytest.mark.covers(X, rules=["ASG-05"])
async def test__the_details_page_s_requests_answer_the_entity_s_verdicts() -> None:
    """The cards: a page of 9 by ``entity_guid``, faceted on dimension and type, sorted by each option; the list:
    its missed rules with their messages; a word of a rule's name; ``id`` the pair.
    """  # noqa: D205 - one sentence
    engine = await gov_engine(
        verdict("e", "named", "1"),
        verdict("e", "owned", "0", dataqualitytype="relationship"),
        verdict("e", "defined", "0"),
        verdict("other", "named", "0"),
    )
    cards = {
        "query": "",
        "facets": {
            "dataqualityruledimension": {"type": "value", "size": 100},
            "dataqualitytype": {"type": "value", "size": 100},
        },
        "page": {"current": 1, "size": 9},
        "filters": {"all": [{"entity_guid": ["e"]}]},
    }
    listed = {
        "result_fields": {name: {"raw": {}} for name in ("entity_guid", "guid", "compliant", "noncompliant_message")},
        "facets": {"guid": {"type": "value", "size": 100}},
        "page": {"current": 1, "size": 100},
        "query": "",
        "filters": {"all": [{"entity_guid": ["e"]}, {"compliant": ["0"]}]},
    }

    by_name = await engine.search(cards | {"sort": {"name": "asc"}})
    by_compliant = await engine.search(cards | {"sort": [{"compliant": "desc"}, {"name": "desc"}]})
    missed = await engine.search(listed | {"sort": {"name": "asc"}})
    by_word = await engine.search({"query": "owned"})

    assert guids(by_name) == ["e--defined", "e--named", "e--owned"]
    assert guids(by_compliant) == ["e--named", "e--owned", "e--defined"]
    assert by_name["facets"] == {
        "dataqualityruledimension": [{"type": "value", "data": [{"value": "completeness", "count": 3}]}],
        "dataqualitytype": [
            {"type": "value", "data": [{"value": "attribute", "count": 2}, {"value": "relationship", "count": 1}]}
        ],
    }
    assert [(found["guid"]["raw"], found["noncompliant_message"]["raw"]) for found in missed["results"]] == [
        ("defined", "Misses defined"),
        ("owned", "Misses owned"),
    ]
    assert guids(by_word) == ["e--owned"]
    assert by_name["results"][0]["_meta"] | {"score": 0} == {
        "id": "e--defined",
        "engine": "atlas-dev-gov-quality",
        "score": 0,
    }


@pytest.mark.covers(X, rules=["ASG-05"])
async def test__a_rule_page_s_requests_answer_the_entities_that_meet_and_miss_it() -> None:
    """The rule's verdicts by ``guid`` and ``compliant``, ``entity_guid`` read, pages of 1,000; their totals."""
    engine = await gov_engine(
        *(verdict(f"m{index}", "named", "1") for index in range(3)),
        verdict("x", "named", "0"),
        verdict("m0", "owned", "0"),
    )

    def tab(compliant: str) -> dict[str, Any]:
        return {
            "facets": {"guid": {"type": "value", "size": 250}},
            "page": {"current": 1, "size": 1000},
            "query": "",
            "result_fields": {"entity_guid": {"raw": {}}},
            "filters": {"all": [{"compliant": [compliant]}, {"guid": ["named"]}]},
        }

    met, missed = await engine.search(tab("1")), await engine.search(tab("0"))

    assert sorted(found["entity_guid"]["raw"] for found in met["results"]) == ["m0", "m1", "m2"]
    assert [found["entity_guid"]["raw"] for found in missed["results"]] == ["x"]
    assert (met["meta"]["page"]["total_results"], missed["meta"]["page"]["total_results"]) == (3, 1)
    assert met["facets"]["guid"] == [{"type": "value", "data": [{"value": "named", "count": 3}]}]
