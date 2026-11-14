"""The search door of the view family over the entity index (AVR-02..09, AVR-11, AVR-13).

Every test opens the door over a fake store holding the entities it names, typed by the data dictionary's
models, and asks it in the door's own shapes (DD-584). The last test sets the door over the sample catalogue:
its counts are 14.4's, plus the entities the engine never derived and the door opens on (AVR-11, DD-586).
"""

import asyncio
from typing import Any

import pytest
from aurelius_atlas_core.app_search_document import own_document
from aurelius_atlas_core.app_search_engine import AppSearchEngine
from aurelius_atlas_core.entity_documents import ElasticsearchEntityDocuments
from aurelius_atlas_core.search_fields import search_fields
from aurelius_atlas_core.stored_entity import (
    StoredDimensionTotals,
    StoredEntity,
    StoredQualityTotals,
)
from aurelius_atlas_core.view_search import ViewSearchEngine, door_fields, query_fields
from aurelius_atlas_model.errors import AtlasError, AtlasErrorCode
from aurelius_atlas_model.instance import EntityStatus
from aurelius_atlas_store_es.testing.fake import FakeClient
from aurelius_atlas_typesystem.registry import TypeRegistry
from test__app_search_engine import indexed_sample, legacy_counts
from test__app_search_quality import m4i_types

V = "aurelius_atlas_core.view_search"
X = f"{V}.ViewSearchEngine.search"

SCORED = StoredQualityTotals(overall=StoredDimensionTotals(total=4, count=4, score=0.75))
"""A score roll-up of four results averaging three-quarters."""

_FIELDS = ("state", "labels", "quality_totals", "governed", "createTime", "updateTime", "createdBy", "updatedBy")
"""The values ``hold`` gives to the entity itself rather than to its attributes."""


@pytest.fixture
def m4i() -> TypeRegistry:
    """Atlas's and the data dictionary's types (ADR 058), the door's registry."""
    return asyncio.run(m4i_types()).registry


def hold(m4i: TypeRegistry, guid: str, type_name: str = "m4i_data_entity", **values: Any) -> StoredEntity:  # noqa: ANN401
    """A stored entity of ``type_name`` named ``guid``.

    ``values`` are attribute values by name and ``_FIELDS`` of the entity itself; a current document is
    added when ``document`` holds updates for one (AVS-04, DD-518).
    """
    entity_type = m4i.entity_type(type_name)
    assert entity_type is not None
    document = values.pop("document", None)
    values.setdefault("qualifiedName", guid)
    values.setdefault("name", guid.upper())
    held: dict[str, Any] = {}
    attributes: dict[str, Any] = {}
    for name, value in values.items():
        if name in _FIELDS:
            held[name] = value
        elif (defining := entity_type.attribute(name)) is not None:
            attributes[defining.qualified_name] = value
    entity = StoredEntity(guid=guid, type_name=type_name, attributes=attributes, **held)
    entity = entity.model_copy(update={"search": search_fields(entity, entity_type)})
    if document is not None:
        entity = entity.model_copy(update={"app_search": own_document(entity).model_copy(update=document)})
    return entity


async def opened(*entities: StoredEntity, m4i: TypeRegistry) -> ViewSearchEngine:
    """The door over a fake store holding ``entities``."""
    documents = ElasticsearchEntityDocuments(FakeClient())  # type: ignore[arg-type]
    await documents.prepare()
    await documents.write([(entity, None) for entity in entities])
    return ViewSearchEngine(documents, m4i)


async def held(door: ViewSearchEngine, body: object) -> list[str]:
    """The GUIDs of a request's cards, in the answer's order."""
    return [card["guid"] for card in (await door.search(body))["cards"]]


async def refused(door: ViewSearchEngine, body: object) -> list[str]:
    """The messages of the door's refusal of ``body`` (AVR-13)."""
    with pytest.raises(AtlasError) as raised:
        await door.search(body)
    assert raised.value.code is AtlasErrorCode.VIEW_REFUSED
    return raised.value.messages or [raised.value.message]


@pytest.mark.covers(X, rules=["AVR-04"])
async def test__query_words_match_the_analysed_names_and_the_other_fields_whole(m4i: TypeRegistry) -> None:
    """A query matches the names as words and the other fields whole.

    Words go over the name, qualified name and definition, however many types store them; elsewhere a word
    matches a whole stored value; an empty query matches every document (AVR-04, DD-525).
    """
    door = await opened(
        hold(m4i, "a-1", "Asset", name="Legacy Orders"),
        hold(m4i, "d-1", definition="Finance orders of records"),
        m4i=m4i,
    )

    assert sorted(await held(door, {})) == ["a-1", "d-1"]
    assert sorted(await held(door, {"query": "orders"})) == ["a-1", "d-1"]
    assert await held(door, {"query": "records"}) == ["d-1"]
    assert await held(door, {"query": "legacy"}) == ["a-1"]
    assert await held(door, {"query": "m4i_data_entity"}) == ["d-1"]
    assert await held(door, {"query": "data"}) == []


@pytest.mark.covers(X, f"{V}.door_fields", rules=["AVR-03"])
async def test__filters_take_values_lists_ranges_and_nested_objects(m4i: TypeRegistry) -> None:
    """A filter takes values, lists, ranges, or nested objects.

    One type or a list of them; a ``{from, to}`` over a quality sub-field, missing as zero (DD-530);
    ``all``, ``any`` and ``none`` nested (AVR-03).
    """
    door = await opened(
        hold(m4i, "a-1", "Asset", name="Legacy Orders"),
        hold(m4i, "d-1"),
        hold(m4i, "q-1", quality_totals=SCORED),
        m4i=m4i,
    )

    assert await held(door, {"filters": {"typeName": "m4i_data_entity"}}) == ["d-1", "q-1"]
    assert sorted(await held(door, {"filters": {"typeName": ["Asset", "m4i_data_entity"]}})) == ["a-1", "d-1", "q-1"]
    assert await held(door, {"filters": {"quality.overall.score": {"from": 0.5}}}) == ["q-1"]
    assert await held(door, {"filters": {"quality.overall.score": {"from": 0.0, "to": 0.5}}}) == ["a-1", "d-1"]
    nested = {"filters": {"all": [{"typeName": "m4i_data_entity"}, {"any": [{"name": "D-1"}, {"name": "NOPE"}]}]}}
    assert await held(door, nested) == ["d-1"]
    assert await held(door, {"filters": {"none": [{"typeName": "m4i_data_entity"}]}}) == ["a-1"]


@pytest.mark.covers(X, f"{V}.door_fields", rules=["AVR-05"])
async def test__facets_count_the_matching_values_most_first_empty_left_out(m4i: TypeRegistry) -> None:
    """A facet counts the matching values, most first, empty left out.

    Each asked field's ``{value, count}`` entries; ``size`` caps them; a boolean counts its ``false``;
    a quality score sub-field is one such name (AVR-05, DD-587).
    """
    door = await opened(
        hold(m4i, "a-1", "Asset", name="Legacy Orders"),
        hold(m4i, "d-1", labels=["important"]),
        hold(m4i, "q-1", quality_totals=SCORED, labels=["important"]),
        m4i=m4i,
    )

    answer = await door.search({"facets": ["labels", "typeName", "governed"], "limit": 1})
    assert list(answer["facets"]) == ["labels", "typeName", "governed"]
    assert answer["facets"]["labels"] == [{"value": "important", "count": 2}]
    assert answer["facets"]["typeName"] == [
        {"value": "m4i_data_entity", "count": 2},
        {"value": "Asset", "count": 1},
    ]
    assert answer["facets"]["governed"] == [{"value": False, "count": 3}]
    scored = await door.search({"facets": {"quality.overall.score": {"size": 5}}, "limit": 1})
    assert scored["facets"]["quality.overall.score"] == [
        {"value": 0.0, "count": 2},
        {"value": 0.75, "count": 1},
    ]
    capped = await door.search({"facets": {"labels": {"size": 1}}, "limit": 1})
    assert capped["facets"]["labels"] == [{"value": "important", "count": 2}]


@pytest.mark.covers(X, rules=["AVR-06"])
async def test__sort_orders_by_a_field_or_score_with_ties_by_guid(m4i: TypeRegistry) -> None:
    """A sort orders by a field or score, ties by GUID.

    ``createTime`` both ways; by default score down, ties by GUID; ``name`` sorts when ``filters.typeName``
    names one type (AVR-06, DD-586).
    """
    door = await opened(
        hold(m4i, "t-1", createTime=100),
        hold(m4i, "t-2", createTime=100),
        hold(m4i, "t-3", createTime=50),
        m4i=m4i,
    )

    assert await held(door, {"sort": {"createTime": "desc"}}) == ["t-1", "t-2", "t-3"]
    assert await held(door, {"sort": [{"createTime": "asc"}]}) == ["t-3", "t-1", "t-2"]
    assert await held(door, {"sort": {"createTime": "desc"}, "limit": 2}) == ["t-1", "t-2"]
    assert await held(door, {}) == ["t-1", "t-2", "t-3"]

    typed = await opened(
        hold(m4i, "n-1", "m4i_data_domain", name="Beta"),
        hold(m4i, "n-2", "m4i_data_domain", name="Alpha"),
        m4i=m4i,
    )
    assert await held(typed, {"filters": {"typeName": "m4i_data_domain"}, "sort": {"name": "asc"}}) == ["n-2", "n-1"]


@pytest.mark.covers(X, rules=["AVR-07"])
async def test__limit_and_offset_cut_the_page_and_total_counts_every_hit(m4i: TypeRegistry) -> None:
    """Ten cards by default; ``limit`` and ``offset`` move the window; ``total`` is the whole count (AVR-07)."""
    door = await opened(*(hold(m4i, f"t-{number}") for number in range(1, 13)), m4i=m4i)

    answer = await door.search({"limit": 2, "offset": 2})
    assert answer["total"] == 12
    assert [card["guid"] for card in answer["cards"]] == ["t-11", "t-12"]
    assert len((await door.search({}))["cards"]) == 10
    assert (await door.search({"limit": 100, "offset": 12}))["cards"] == []


@pytest.mark.covers(X, f"{V}._card", rules=["AVR-08"])
async def test__the_answer_holds_cards_facets_and_a_total(m4i: TypeRegistry) -> None:
    """The answer holds cards, facets, and a total.

    A card is 16.1's: its own fields, the derived ones, the roll-up per dimension (AVR-08, AVS-01).
    """
    door = await opened(
        hold(m4i, "d-1", definition="Finance orders of records", labels=["important"], quality_totals=SCORED),
        m4i=m4i,
    )

    answer = await door.search({"facets": ["typeName"]})
    assert set(answer) == {"cards", "facets", "total"}
    assert answer["total"] == 1
    (card,) = answer["cards"]
    assert card["guid"] == card["qualifiedName"] == "d-1"
    assert card["name"] == card["displayText"] == "D-1"
    assert card["typeName"] == "m4i_data_entity"
    assert card["definition"] == "Finance orders of records"
    assert card["labels"] == ["important"]
    assert card["status"] == "ACTIVE"
    assert card["breadcrumb"] == []
    assert card["relations"] == []
    assert [entry["dimension"] for entry in card["quality"]] == [
        "accuracy",
        "completeness",
        "timeliness",
        "uniqueness",
        "validity",
        "overall",
    ]
    assert card["quality"][-1]["score"] == 0.75
    assert answer["facets"]["typeName"] == [{"value": "m4i_data_entity", "count": 1}]


@pytest.mark.covers(X, rules=["AVR-09"])
async def test__only_active_entities_are_in_the_door_marking_stale_documents(m4i: TypeRegistry) -> None:
    """A deleted entity is out; a stale document is answered with its mark and filters by it (AVR-09, AVS-06)."""
    door = await opened(
        hold(m4i, "d-1", document={}),
        hold(m4i, "s-1", document={"stale": True}),
        hold(m4i, "x-9", state=EntityStatus.DELETED),
        m4i=m4i,
    )

    assert sorted(await held(door, {})) == ["d-1", "s-1"]
    answer = await door.search({})
    assert {card["guid"]: card["stale"] for card in answer["cards"]} == {"d-1": False, "s-1": True}
    assert await held(door, {"filters": {"stale": True}}) == ["s-1"]
    assert await held(door, {"filters": {"stale": False}}) == ["d-1"]


@pytest.mark.covers(X, f"{V}.door_fields", rules=["AVR-11"])
async def test__an_entity_of_any_type_without_a_document_is_in_the_door(m4i: TypeRegistry) -> None:
    """An entity of any type, document or none, is in the door.

    A plain ``Asset`` with no document matches an empty query and its own name, and answers empty derived
    fields with no mark; ``filters.typeName`` types it out (AVR-11, AVS-02, DD-586).
    """
    door = await opened(
        hold(m4i, "a-1", "Asset", name="Legacy Orders"),
        hold(m4i, "d-1"),
        m4i=m4i,
    )

    answer = await door.search({"query": "orders"})
    (card,) = answer["cards"]
    assert card["guid"] == "a-1"
    assert card["breadcrumb"] == []
    assert card["relations"] == []
    assert card["quality"] == []
    assert card["stale"] is False
    assert "governed" not in card
    assert await held(door, {"filters": {"typeName": "Asset"}}) == ["a-1"]


@pytest.mark.covers(f"{V}.parse", f"{V}._refuse", rules=["AVR-02", "AVR-05", "AVR-07", "AVR-13"])
async def test__a_request_the_door_refuses_is_answered_with_one_message_per_problem(m4i: TypeRegistry) -> None:
    """A request the door refuses names every problem.

    Unknown options, kinds and bounds; a facet of a number or of a field of no single value; each problem
    named once, all of them (AVR-02, AVR-05, AVR-07, AVR-13).
    """
    door = await opened(
        hold(m4i, "d-1", name="Beta"),
        hold(m4i, "n-1", "m4i_data_domain"),
        m4i=m4i,
    )

    assert await refused(door, []) == ["The request body must be a JSON object"]
    assert await refused(door, {"bogus": 1, "query": 7}) == [
        "The request holds an unknown option: bogus",
        "Query must be a string",
    ]
    assert await refused(door, {"limit": 0, "offset": 10_001}) == [
        "Limit must be between 1 and 100",
        "Offset must be between 0 and 10000",
    ]
    assert await refused(door, {"filters": {"nope": "x"}}) == ["Filters contains an unknown field: nope"]
    assert await refused(door, {"facets": ["createTime"]}) == [
        "Facet for createTime: number fields hold no values to count"
    ]
    assert await refused(door, {"facets": {"typeName": {"size": 251}}}) == [
        "Facet size for typeName must be between 1 and 250"
    ]
    assert await refused(door, {"sort": {"name": "asc"}}) == [
        "Sort by name needs one stored value: filters.typeName must name one type"
    ]
    assert await refused(door, {"facets": {"name": {}}}) == ["Facet for name: the field holds no single value to count"]
    assert await held(door, {"facets": {"name": {}}, "filters": {"typeName": "m4i_data_domain"}}) == ["n-1"]


@pytest.mark.covers(f"{V}.name_paths", f"{V}.door_fields", f"{V}.query_fields", rules=["AVR-03", "AVR-04"])
def test__one_type_narrows_what_every_type_holds_under_its_own_name(m4i: TypeRegistry) -> None:
    """One type narrows what every type holds under its own name.

    Un-narrowed, ``name`` holds every defining type's path; narrowed, one path and its analysed sub-field;
    the query reaches both, the exact fields whole (AVR-03, AVR-04, DD-586).
    """
    untyped = door_fields(m4i)
    typed = door_fields(m4i, "m4i_data_domain")

    assert untyped["name"].path is None
    assert "search.keyword.Asset.name" in (untyped["name"].paths or ())
    assert typed["name"].path == "search.keyword.m4i_data_domain.name"
    assert typed["name"].text == "search.keyword.m4i_data_domain.name.text"
    assert typed["definition"].path is None
    fields = query_fields(m4i)
    assert fields["typeName"] == 1.0
    assert fields["classificationNames"] == 1.0
    assert "search.keyword.Asset.name.text" in fields


@pytest.fixture(scope="module")
def sample_door() -> tuple[ViewSearchEngine, AppSearchEngine]:
    """The sample catalogue imported and indexed once: the door and 14.4's engine over it."""
    documents = asyncio.run(indexed_sample())
    registry = asyncio.run(m4i_types()).registry
    return ViewSearchEngine(documents, registry), AppSearchEngine(documents)


@pytest.mark.covers(X, f"{V}.door_fields", rules=["AVR-05", "AVR-08", "AVR-11"])
def test__the_sample_answers_what_14_4_answered_plus_the_entities_it_left_out(
    sample_door: tuple[ViewSearchEngine, AppSearchEngine],
) -> None:
    """The door answers what 14.4 answered, plus what it left out.

    The engine's 684 documents plus the active source entities it never derived; each type's facet count
    is what ``atlas-dev`` counted for the same sample (AVR-11, DD-586).
    """
    door, engine = sample_door
    answer = asyncio.run(door.search({"facets": {"typeName": {"size": 250}}, "limit": 1}))
    held_by_engine = asyncio.run(engine.search({"query": "", "facets": {"typename": {"type": "value", "size": 250}}}))

    counted = {entry["value"]: entry["count"] for entry in answer["facets"]["typeName"]}
    expected = legacy_counts("typename")
    assert answer["total"] == 687
    assert held_by_engine["meta"]["page"]["total_results"] == 684
    for value, count in expected.items():
        assert counted[value] == count
    assert set(counted) - set(expected) == {"m4i_source"}


@pytest.mark.covers(X, f"{V}.door_fields", f"{V}._service_types", rules=["VSR-01"])
async def test__owner_counts_the_owners_and_service_type_sums_the_types_by_service(m4i: TypeRegistry) -> None:
    """``owner`` counts Asset's owners; ``serviceType`` sums the type counts by service type.

    Each is asked as any other facet; the roll-up counts every matched entity's type and not the page of
    cards, most first, ties by name, a service type counted none left out; ``size`` caps each (VSR-01,
    DD-093, DD-599).
    """
    door = await opened(
        hold(m4i, "a-1", "Asset", owner="alice"),
        hold(m4i, "g-1", "DataSet", owner="bob"),
        hold(m4i, "w-1", "aws_s3_bucket"),
        hold(m4i, "h-1", "hive_table"),
        m4i=m4i,
    )

    assert (await door.search({"facets": ["owner"]}))["facets"]["owner"] == [
        {"value": "alice", "count": 1},
        {"value": "bob", "count": 1},
    ]
    roll_up = await door.search({"facets": ["serviceType"], "limit": 1})
    assert roll_up["facets"]["serviceType"] == [
        {"value": "atlas_core", "count": 2},
        {"value": "aws", "count": 1},
        {"value": "hive", "count": 1},
    ]
    short = await door.search({"facets": {"typeName": {"size": 1}, "serviceType": {"size": 2}}})
    assert len(short["facets"]["typeName"]) == 1
    assert short["facets"]["serviceType"] == [{"value": "atlas_core", "count": 2}, {"value": "aws", "count": 1}]


@pytest.mark.covers(X, f"{V}._facets", rules=["VSR-01"])
async def test__the_two_facet_names_are_always_accepted_and_answer_empty_where_there_is_nothing(
    m4i: TypeRegistry,
) -> None:
    """The two names are always accepted and answer empty where the registry or the entities hold nothing.

    A registry without Asset's owner attribute knows the name and counts no one, as DD-093 does; only the
    asked size is ever refused, as with any facet (VSR-01, DD-599).
    """
    door = await opened(hold(m4i, "d-1"), m4i=m4i)
    assert (await door.search({"facets": ["owner", "serviceType"]}))["facets"]["owner"] == []

    documents = ElasticsearchEntityDocuments(FakeClient())  # type: ignore[arg-type]
    await documents.prepare()
    bare = await ViewSearchEngine(documents, TypeRegistry()).search({"facets": ["owner", "serviceType"]})
    assert bare == {"cards": [], "facets": {"owner": [], "serviceType": []}, "total": 0}

    assert await refused(door, {"facets": {"serviceType": {"size": 0}}}) == [
        "Facet size for serviceType must be between 1 and 250"
    ]
    assert await refused(door, {"facets": {"owner": {"size": 251}}}) == [
        "Facet size for owner must be between 1 and 250"
    ]


@pytest.mark.covers(X, rules=["VSR-02"])
async def test__the_new_facet_names_leave_every_other_answer_as_it_was(m4i: TypeRegistry) -> None:
    """The two new names change no card, no total and no other facet, and unknown names stay refused.

    The same query asked with or without them answers the same cards; a name near them is still no field
    of the door (VSR-02).
    """
    door = await opened(hold(m4i, "a-1", "Asset", owner="alice"), hold(m4i, "d-1"), m4i=m4i)

    plain = await door.search({})
    asked = await door.search({"facets": ["owner", "serviceType"]})
    assert asked["cards"] == plain["cards"]
    assert asked["total"] == plain["total"]
    assert list(asked["facets"]) == ["owner", "serviceType"]
    assert await refused(door, {"facets": ["ownern"]}) == ["Facets contains an unknown field: ownern"]
