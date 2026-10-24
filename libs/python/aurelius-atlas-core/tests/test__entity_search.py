"""Entity search (SRC-03 to SRC-10, DD-088, DD-089) on the in-memory documents.

The rules are read from ``SearchContext``, ``EntitySearchProcessor``, ``SearchProcessor`` and
``SearchPredicateUtil`` and ``EntityDiscoveryService.searchWithParameters`` of Apache Atlas 2.4.0.
"""

import itertools
from datetime import UTC, datetime
from typing import Any

import pytest
from aurelius_atlas_core.discovery_service import EntityDiscoveryService, normalized
from aurelius_atlas_core.entity_search_processor import date_range
from aurelius_atlas_core.entity_store import EntityStore
from aurelius_atlas_core.entity_writer import EntityWriter
from aurelius_atlas_core.search_context import decode_marker, encode_marker
from aurelius_atlas_core.search_fields import field_name, search_fields, search_value
from aurelius_atlas_core.testing.entity_samples import sample_registry
from aurelius_atlas_core.testing.memory import MemoryEntityDocuments
from aurelius_atlas_model.discovery import SearchParameters
from aurelius_atlas_model.errors import AtlasError, AtlasErrorCode
from aurelius_atlas_model.instance import AtlasEntitiesWithExtInfo

S = "aurelius_atlas_core.discovery_service.EntityDiscoveryService.search_with_parameters"
DAY = 86_400_000


@pytest.fixture
async def store() -> EntityStore:
    """Items ``i1`` to ``i3`` and tables ``t1``, ``t2`` of a database ``d``; the clock ticks a second a reading."""
    ticks = itertools.count(1_700_000_000)
    found = EntityStore(sample_registry(writes=True), MemoryEntityDocuments(), clock=lambda: next(ticks))
    items = [
        item("i1", count=1, flag=True, when=1000, label="alpha", tags=["x", "y"]),
        item("i2", count=2, flag=False, when=2000, label="Alpha beta", tags=["y"]),
        item("i3", count=3, label="gamma"),
    ]
    for entity in items:
        await write(found, entity)
    await write(found, {"typeName": "s_database", "guid": "-d", "attributes": {"qualifiedName": "d", "title": "D"}})
    await write(
        found,
        table(
            "t1", sizes=[1, 2], color="RED", db={"typeName": "s_database", "uniqueAttributes": {"qualifiedName": "d"}}
        ),
        table("t2", sizes=[5], color="BLUE"),
    )
    return found


def item(name: str, **attributes: Any) -> dict[str, Any]:  # noqa: ANN401 - Atlas JSON
    """A ``w_item`` named ``name``."""
    return {"typeName": "w_item", "guid": f"-{name}", "attributes": {"qualifiedName": name, **attributes}}


def table(name: str, **attributes: Any) -> dict[str, Any]:  # noqa: ANN401 - Atlas JSON
    """An ``s_table`` named ``name``."""
    return {
        "typeName": "s_table",
        "guid": f"-{name}",
        "attributes": {"qualifiedName": name, "name": name, **attributes},
    }


async def write(store: EntityStore, *entities: dict[str, Any]) -> None:
    """Create the entities in one request."""
    await EntityWriter(store).create_or_update(AtlasEntitiesWithExtInfo.model_validate({"entities": list(entities)}))


async def search(store: EntityStore, **body: Any) -> dict[str, Any]:  # noqa: ANN401 - Atlas JSON
    """The answer to a search, as JSON."""
    return (await EntityDiscoveryService(store).search_with_parameters(SearchParameters.model_validate(body))).to_json()


async def names(store: EntityStore, **body: Any) -> list[str]:  # noqa: ANN401 - Atlas JSON
    """The qualified names a search finds, in order."""
    return [entity["attributes"]["qualifiedName"] for entity in (await search(store, **body)).get("entities", [])]


def where(name: str, operator: str, value: str | None = None) -> dict[str, Any]:
    """An entity filter on one attribute."""
    return {"attributeName": name, "operator": operator, "attributeValue": value}


@pytest.mark.covers(
    "aurelius_atlas_core.search_fields.search_fields",
    "aurelius_atlas_core.search_fields.field_name",
    "aurelius_atlas_core.search_fields.kind_of",
    "aurelius_atlas_core.search_fields.labels_value",
    "aurelius_atlas_core.search_fields.search_value",
    rules=["SRC-05"],
)
async def test__an_entity_carries_typed_search_fields_named_after_the_defining_type(store: EntityStore) -> None:
    """Strings and enums keywords, numbers and dates longs, booleans; references and maps have none (DD-088)."""
    found = await store.find_by_unique_attributes(store.registry.entity_type("s_table"), {"qualifiedName": "t1"})  # type: ignore[arg-type]
    assert found is not None
    fields = found.entity.search or {}
    table_type = store.registry.entity_type("s_table")
    assert table_type is not None
    labelled = found.entity.model_copy(
        update={"labels": ["a", "b"], "custom_attributes": {"k": "v"}, "is_incomplete": True}
    )

    assert {
        name: fields[name] for name in ("keyword.s_ref.qualifiedName", "keyword.s_table.color", "long.s_table.sizes")
    } == {
        "keyword.s_ref.qualifiedName": "t1",
        "keyword.s_table.color": "RED",
        "long.s_table.sizes": [1, 2],
    }
    assert fields["keyword.__typeName"] == "s_table"
    assert fields["keyword.__state"] == "ACTIVE"
    assert isinstance(fields["long.__timestamp"], int)
    assert field_name(table_type.attribute("db")) is None  # type: ignore[arg-type]
    extra = search_fields(labelled, table_type)
    assert (extra["keyword.__labels"], extra["keyword.__customAttributes"], extra["long.__isIncomplete"]) == (
        "|a|b|",
        '{"k":"v"}',
        1,
    )
    assert [search_value(kind, value) for kind, value in (("long", "x"), ("boolean", "TRUE"), ("double", "1.5"))] == [
        None,
        True,
        1.5,
    ]
    assert search_value("long", datetime.fromtimestamp(1, UTC)) == 1000
    assert search_value("keyword", 5) == "5"


@pytest.mark.covers(
    S,
    "aurelius_atlas_core.search_context.SearchContext.all_entities",
    "aurelius_atlas_core.entity_store.EntityStore.search",
    rules=["SRC-03"],
)
async def test__types_are_named_with_their_sub_types_or_every_entity(store: EntityStore) -> None:
    """A super type finds its sub types' entities, unless switched off; unknown names are dropped; all of them."""
    assert len(await names(store, typeName="s_ref")) == 6
    assert await names(store, typeName="s_ref", includeSubTypes=False) == []
    assert sorted(await names(store, typeName="w_item,nope")) == ["i1", "i2", "i3"]
    assert (await search(store, typeName="_ALL_ENTITY_TYPES"))["approximateCount"] == 6
    with pytest.raises(AtlasError) as unknown:
        await search(store, typeName="nope,neither")

    assert (unknown.value.code, unknown.value.message) == (
        AtlasErrorCode.UNKNOWN_TYPENAME,
        "nope,neither: Unknown/invalid typename",
    )


@pytest.mark.covers("aurelius_atlas_core.search_context.SearchContext.first_type", rules=["SRC-04"])
async def test__filtered_sorted_and_requested_attributes_must_be_the_types(store: EntityStore) -> None:
    """Each type must have a filter's attribute and the sort; requested ones, the first type."""
    cases = [
        {"typeName": "w_item,s_table", "entityFilters": where("count", "=", "1")},
        {"typeName": "_ALL_ENTITY_TYPES", "sortBy": "name"},
        {"typeName": "w_item", "attributes": ["sizes"]},
    ]
    errors = []
    for body in cases:
        with pytest.raises(AtlasError) as failed:
            await search(store, **body)
        errors.append(failed.value.message)

    assert errors == [
        "Attribute count not found for type s_table",
        "Attribute name not found for type _ALL_ENTITY_TYPES",
        "Attribute sizes not found for type w_item",
    ]
    assert await names(store, typeName="_ALL_ENTITY_TYPES", entityFilters=where("__guid", "notNull"), limit=1) != []


@pytest.mark.covers(
    "aurelius_atlas_core.entity_search_processor.EntitySearchProcessor.query",
    "aurelius_atlas_core.search_query.matches",
    "aurelius_atlas_core.search_query.selects",
    rules=["SRC-05"],
)
@pytest.mark.parametrize(
    ("criterion", "expected"),
    [
        (where("count", ">", "1"), ["i2", "i3"]),
        (where("count", "<=", "2"), ["i1", "i2"]),
        (where("count", "lt", "2"), ["i1"]),
        (where("count", ">=", "3"), ["i3"]),
        (where("count", "=", "2"), ["i2"]),
        (where("when", "neq", "1000"), ["i2", "i3"]),
        (where("flag", "=", "TRUE"), ["i1"]),
        (where("flag", "<", "true"), []),
        (where("label", "startsWith", "Alpha"), ["i2"]),
        (where("label", "endsWith", "ma"), ["i3"]),
        (where("label", "contains", "lph"), ["i1", "i2"]),
        (where("label", "like", "lph"), ["i1", "i2"]),
        (where("label", "not_contains", "lph"), ["i3"]),
        (where("label", ">", "B"), ["i1", "i3"]),
        (where("tags", "contains", "y"), ["i1", "i2"]),
        (where("tags", "not_contains", "x"), ["i2", "i3"]),
        (where("tags", "=", "x"), []),
        (where("count", "contains", "1"), []),
        (where("tags", "isNull"), ["i3"]),
        (where("when", "notNull"), ["i1", "i2", "i3"]),
        (where("when", "=", "0"), ["i3"]),
        (where("tags", "notEmpty"), ["i1", "i2"]),
        (where("label", "in", "alpha"), []),
        (where("label", "containsAny", "alpha"), ["i1", "i2", "i3"]),
        (where("label", "nope", "alpha"), ["i1", "i2", "i3"]),
        (where("count", "=", ""), []),
        (where("when", "timerange", "500,1500"), ["i1"]),
        (where("label", "timerange", "1,2"), []),
    ],
)
async def test__each_operator_tests_values_as_atlas_predicates_do(
    store: EntityStore, criterion: dict[str, Any], expected: list[str]
) -> None:
    """``SearchPredicateUtil``: comparisons by type, case-sensitive strings, arrays by element, presence."""
    assert sorted(await names(store, typeName="w_item", entityFilters=criterion)) == expected


@pytest.mark.covers("aurelius_atlas_core.entity_search_processor.EntitySearchProcessor.query", rules=["SRC-05"])
async def test__conditions_combine_criteria_and_drop_those_without_a_predicate(store: EntityStore) -> None:
    """``AND`` and ``OR`` nest; a criterion of ``CONTAINS_ANY`` is left out, not counted as true."""
    either = {"condition": "OR", "criterion": [where("count", "=", "1"), where("label", "=", "gamma")]}
    both = {"condition": "AND", "criterion": [either, where("flag", "=", "true")]}
    dropped = {"condition": "OR", "criterion": [where("label", "containsAny", "q"), where("count", "=", "2")]}
    empty = {"condition": "AND", "criterion": [where("label", "containsAny", "q")]}

    assert sorted(await names(store, typeName="w_item", entityFilters=either)) == ["i1", "i3"]
    assert await names(store, typeName="w_item", entityFilters=both) == ["i1"]
    assert await names(store, typeName="w_item", entityFilters=dropped) == ["i2"]
    assert len(await names(store, typeName="w_item", entityFilters=empty)) == 3
    assert sorted(await names(store, typeName="w_item,s_table", entityFilters=where("name", "=", "t2"))) == ["t2"]


@pytest.mark.covers("aurelius_atlas_core.entity_search_processor.date_range", rules=["SRC-06"])
def test__named_time_ranges_are_computed_as_process_date_range_does() -> None:
    """In UTC (DV-44), from midnight, ending the millisecond before the next range; ``THIS_QUARTER`` as Atlas has it."""
    now = datetime(2026, 5, 15, 13, 30, tzinfo=UTC)

    def span(name: str) -> tuple[str, str]:
        found = date_range(name, now)
        assert found is not None
        return tuple(datetime.fromtimestamp(ms / 1000, UTC).replace(tzinfo=None).isoformat() for ms in found)  # type: ignore[return-value]

    assert span("TODAY") == ("2026-05-15T00:00:00", "2026-05-15T23:59:59.999000")
    assert span("LAST_7_DAYS")[0] == "2026-05-09T00:00:00"
    assert span("LAST_MONTH") == ("2026-04-01T00:00:00", "2026-04-30T23:59:59.999000")
    assert span("THIS_QUARTER") == ("2026-04-01T00:00:00", "2026-06-30T23:59:59.999000")
    assert span("LAST_QUARTER") == ("2026-01-01T00:00:00", "2026-03-31T23:59:59.999000")
    assert span("LAST_YEAR") == ("2025-01-01T00:00:00", "2025-12-31T23:59:59.999000")
    assert span("LAST_12_MONTHS")[0] == "2025-05-01T00:00:00"
    assert [span(name)[0] for name in ("YESTERDAY", "LAST_30_DAYS", "THIS_MONTH", "THIS_YEAR")] == [
        "2026-05-14T00:00:00",
        "2026-04-16T00:00:00",
        "2026-05-01T00:00:00",
        "2026-01-01T00:00:00",
    ]
    assert [span(name)[0] for name in ("LAST_3_MONTHS", "LAST_6_MONTHS")] == [
        "2026-02-01T00:00:00",
        "2025-11-01T00:00:00",
    ]
    assert date_range("SOMETIME", now) is None


@pytest.mark.covers("aurelius_atlas_core.entity_search_processor.EntitySearchProcessor.query", rules=["SRC-06"])
async def test__system_attributes_match_as_atlas_keeps_them(store: EntityStore) -> None:
    """``__isIncomplete`` false is no value; labels match an element; times by named range; a bad value fails."""
    first = await store.find_by_unique_attributes(store.registry.entity_type("w_item"), {"qualifiedName": "i1"})  # type: ignore[arg-type]
    assert first is not None
    await store.write([_changed(first, labels=["red", "blue"], custom_attributes={"k": "v"})])
    item_type = {"typeName": "w_item"}

    assert len(await names(store, **item_type, entityFilters=where("__isIncomplete", "=", "false"))) == 3
    assert await names(store, **item_type, entityFilters=where("__isIncomplete", "!=", "0")) == []
    assert await names(store, **item_type, entityFilters=where("__isIncomplete", "notNull")) == []
    assert await names(store, **item_type, entityFilters=where("__labels", "=", "red")) == ["i1"]
    assert await names(store, **item_type, entityFilters=where("__labels", "startsWith", "blu")) == ["i1"]
    assert await names(store, **item_type, entityFilters=where("__labels", "endsWith", "ed")) == ["i1"]
    assert len(await names(store, **item_type, entityFilters=where("__labels", "!=", "red"))) == 2
    assert await names(store, **item_type, entityFilters=where("__customAttributes", "contains", "k=v")) == ["i1"]
    assert len(await names(store, **item_type, entityFilters=where("__timestamp", "timerange", "TODAY"))) == 3
    with pytest.raises(AtlasError) as invalid:
        await search(store, **item_type, entityFilters=where("count", "=", "many"))
    with pytest.raises(AtlasError) as range_:
        await search(store, **item_type, entityFilters=where("when", "timerange", "1"))

    assert (invalid.value.code, invalid.value.message) == (
        AtlasErrorCode.BAD_REQUEST,
        "Invalid value many for attribute count",
    )
    assert range_.value.code is AtlasErrorCode.BAD_REQUEST


def _changed(found: Any, **update: Any) -> Any:  # noqa: ANN401 - an entity change
    from aurelius_atlas_core.entity_store import EntityChange  # noqa: PLC0415

    return EntityChange(found.entity.model_copy(update=update), found.version)


@pytest.mark.covers(f"{S}", "aurelius_atlas_core.discovery_service.normalized", rules=["SRC-07"])
async def test__entities_are_sorted_paged_and_restricted_to_active_ones(store: EntityStore) -> None:
    """By ``sortBy`` either way, missing last; by creation without; limit and offset normalised and shown."""
    t1 = await store.find_by_unique_attributes(store.registry.entity_type("s_table"), {"qualifiedName": "t1"})  # type: ignore[arg-type]
    assert t1 is not None
    await EntityWriter(store).delete_by_id(t1.entity.guid)
    answer = await search(store, typeName="w_item", limit=-3, offset=-1)

    assert await names(store, typeName="w_item", sortBy="when", sortOrder="DESCENDING") == ["i2", "i1", "i3"]
    assert await names(store, typeName="w_item", sortBy="when") == ["i3", "i1", "i2"]
    assert await names(store, typeName="w_item", sortBy="tags") == ["i1", "i2", "i3"]
    assert await names(store, typeName="w_item") == ["i1", "i2", "i3"]
    assert await names(store, typeName="w_item", limit=1, offset=1) == ["i2"]
    assert (answer["searchParameters"]["limit"], answer["searchParameters"]["offset"]) == (100, 0)
    assert normalized(10_001, 3) == (100, 3)
    assert await names(store, typeName="s_table", excludeDeletedEntities=True) == ["t2"]
    assert sorted(await names(store, typeName="s_table")) == ["t1", "t2"]


@pytest.mark.covers(
    "aurelius_atlas_core.search_context.encode_marker",
    "aurelius_atlas_core.search_context.decode_marker",
    "aurelius_atlas_core.entity_search_processor.EntitySearchProcessor.execute",
    rules=["SRC-08"],
)
async def test__a_marker_pages_through_the_entities(store: EntityStore) -> None:
    """``*`` starts; each page names the next; ``-1`` after the last; not with an offset, nor a foreign marker."""
    body = {"typeName": "w_item", "limit": 2}
    first = await search(store, **body, marker="*")
    second = await search(store, **body, marker=first["nextMarker"])
    errors = []
    for marker, offset in ((first["nextMarker"], 1), ("not-a-marker", 0), (first["nextMarker"].upper(), 0)):
        with pytest.raises(AtlasError) as failed:
            await search(store, **body, marker=marker, offset=offset)
        errors.append(failed.value.message)

    assert [e["attributes"]["qualifiedName"] for e in first["entities"]] == ["i1", "i2"]
    assert [e["attributes"]["qualifiedName"] for e in second["entities"]] == ["i3"]
    assert second["nextMarker"] == "-1"
    assert errors == ["Marker can be used only if offset=0.", "Invalid marker!", "Invalid marker!"]
    parameters = SearchParameters(type_name="w_item", limit=2, marker="*")
    assert decode_marker(parameters.model_copy(update={"marker": encode_marker(parameters, 4)})) == 4
    assert encode_marker(parameters, None) is None


@pytest.mark.covers(
    f"{S}",
    "aurelius_atlas_core.entity_retriever.EntityRetriever.header_with_attributes",
    "aurelius_atlas_core.search_context.SearchContext.exclude_header_attributes",
    rules=["SRC-09", "SRC-10"],
)
async def test__headers_carry_requested_and_filtered_attributes_and_referred_entities(store: EntityStore) -> None:
    """``db`` refers to the database, whose header is referred; the filter's ``sizes`` shows; or a table of values.

    A missing optional primitive is stored with its type's default, as an entity create stores it.
    """
    answer = await search(
        store,
        typeName="s_table",
        attributes=["db", "color"],
        entityFilters=where("sizes", "notEmpty"),
        includeClassificationAttributes=True,
    )
    table_ = await search(
        store, typeName="w_item", attributes=["label", "count", "__guid"], excludeHeaderAttributes=True
    )
    nothing = await search(store, typeName="w_item", entityFilters=where("count", ">", "9"))

    t1 = next(entity for entity in answer["entities"] if entity["attributes"]["qualifiedName"] == "t1")
    assert answer["queryType"] == "BASIC"
    assert (answer["approximateCount"], t1["attributes"]["sizes"], t1["attributes"]["color"]) == (2, [1, 2], "RED")
    assert t1["attributes"]["db"]["typeName"] == "s_database"
    assert t1["classifications"] == []
    assert [header["displayText"] for header in answer["referredEntities"].values()] == ["D"]
    assert table_["attributes"]["name"] == ["label", "count", "__guid"]
    assert [row[:2] for row in table_["attributes"]["values"]] == [["alpha", 1], ["Alpha beta", 2], ["gamma", 3]]
    assert "entities" not in table_
    assert ("entities" in nothing, nothing["approximateCount"]) == (False, 0)


@pytest.mark.covers(f"{S}", rules=["SRC-03"])
async def test__parameters_not_supported_yet_and_no_type_are_refused(store: EntityStore) -> None:
    """``classification``, ``query`` and ``termName`` until 4.1b, 4.2 and 5.2; no type at all (DV-46)."""
    messages = []
    for body in ({"typeName": "w_item", "classification": "c"}, {"query": "x"}, {"termName": "t"}, {}):
        with pytest.raises(AtlasError) as failed:
            await search(store, **body)
        messages.append((failed.value.code, failed.value.message))

    assert messages[:3] == [
        (AtlasErrorCode.BAD_REQUEST, "Search by classification is not supported yet"),
        (AtlasErrorCode.BAD_REQUEST, "Search by query is not supported yet"),
        (AtlasErrorCode.BAD_REQUEST, "Search by termName is not supported yet"),
    ]
    assert messages[3][0] is AtlasErrorCode.INVALID_SEARCH_PARAMS
