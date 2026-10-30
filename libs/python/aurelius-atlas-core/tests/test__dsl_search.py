"""DSL search of entities (DSE-02 to DSE-15) on the in-memory documents.

Read from ``EntityDiscoveryService.searchUsingDslQuery`` and ``getDslQueryUsingTypeNameClassification``,
``TraversalBasedExecutor``, ``DSLVisitor``, ``GremlinQueryComposer``, ``GremlinClause``, ``IdentifierHelper``,
``RegistryBasedLookup`` and ``GremlinClauseToTraversalTranslator`` of Apache Atlas 2.4.0. The queries are those of
its ``GremlinQueryComposerTest`` and ``DSLQueriesTest`` where they show a rule, on types shaped as theirs.
"""

from typing import Any

import pytest
from aurelius_atlas_core import search_query as sq
from aurelius_atlas_core.discovery_service import EntityDiscoveryService
from aurelius_atlas_core.dsl_query_composer import DslQueryComposer
from aurelius_atlas_core.dsl_query_executor import translatable
from aurelius_atlas_core.entity_classifications import EntityClassifications
from aurelius_atlas_core.entity_store import EntityStore
from aurelius_atlas_core.entity_writer import EntityWriter
from aurelius_atlas_core.testing.memory import MemoryEntityDocuments
from aurelius_atlas_dsl.atlas_dsl import QueryMetadata, parse
from aurelius_atlas_model.errors import AtlasError, AtlasErrorCode
from aurelius_atlas_model.instance import AtlasClassification, AtlasEntitiesWithExtInfo
from aurelius_atlas_model.typedef import AtlasTypesDef
from aurelius_atlas_typesystem.registry import TypeRegistry

D = "aurelius_atlas_core.discovery_service.EntityDiscoveryService"
C = "aurelius_atlas_core.dsl_query_composer.DslQueryComposer.compose"
X = "aurelius_atlas_core.dsl_query_executor"
GUIDS: dict[str, str] = {}


def _attribute(name: str, type_name: str = "string", **more: Any) -> dict[str, Any]:  # noqa: ANN401 - Atlas JSON
    return {"name": name, "typeName": type_name, "isOptional": True, "cardinality": "SINGLE", **more}


TYPES = {
    "enumDefs": [
        {"name": "TableKind", "elementDefs": [{"value": "MANAGED", "ordinal": 0}, {"value": "VIEW", "ordinal": 1}]}
    ],
    "classificationDefs": [
        {"name": "Dimension", "attributeDefs": [_attribute("tagAttr1")]},
        {"name": "PII"},
        {"name": "Fact"},
    ],
    "entityDefs": [
        {
            "name": "Asset",
            "attributeDefs": [
                _attribute("qualifiedName", isUnique=True),
                _attribute("name"),
                _attribute("owner"),
                _attribute("description"),
            ],
        },
        {"name": "DB", "superTypes": ["Asset"], "attributeDefs": [_attribute("createTime", "date")]},
        {
            "name": "Table",
            "superTypes": ["Asset"],
            "attributeDefs": [
                _attribute("createTime", "date"),
                _attribute("partitionSize", "float"),
                _attribute("retention", "long"),
                _attribute("isFile", "boolean"),
                _attribute("tableType", indexType="STRING"),
                _attribute("kind", "TableKind"),
                {**_attribute("tags", "array<string>"), "cardinality": "SET"},
                _attribute("parameters", "map<string,string>"),
                _attribute("db", "DB"),
            ],
        },
        {"name": "View", "superTypes": ["Table"]},
    ],
}

TABLES = [
    {
        "qualifiedName": "sales_fact",
        "name": "sales_fact",
        "owner": "Joe",
        "description": "sales fact table",
        "createTime": "2014-12-11T02:35:58.440Z",
        "partitionSize": 2048.0,
        "retention": 10,
        "isFile": True,
        "tableType": "Managed table",
        "kind": "MANAGED",
        "tags": ["finance", "daily"],
    },
    {
        "qualifiedName": "time_dim",
        "name": "time_dim",
        "owner": "Jane BI",
        "description": "dimension table",
        "createTime": "2014-01-01T00:00:00.000Z",
        "partitionSize": 10.0,
        "isFile": False,
        "tableType": "External",
        "kind": "VIEW",
    },
    {"qualifiedName": "customer_dim", "name": "customer_dim", "owner": "Joe BI", "retention": 3, "tags": ["crm"]},
    {"qualifiedName": "log_fact", "name": "log_fact", "tableType": "*Tab_x*"},
]


@pytest.fixture
async def store() -> EntityStore:
    """Two databases; tables ``sales_fact`` (``Fact``), ``time_dim`` (``Dimension``), ``customer_dim`` (``PII``),
    ``log_fact``; the view ``sales_view``; the database ``Old`` deleted.
    """  # noqa: D205 - one sentence
    registry = TypeRegistry()
    with registry.update() as transient:
        transient.add_types(AtlasTypesDef.model_validate(TYPES))
    found = EntityStore(registry, MemoryEntityDocuments())
    entities = [
        _entity("DB", "Sales", owner="John ETL", createTime="2014-12-11T00:00:00.000Z"),
        _entity("DB", "Reporting", owner="Jane BI"),
        _entity("DB", "Old", owner="Tim ETL"),
        *[
            _entity("Table", **{key: value for key, value in table.items() if key != "qualifiedName"})
            for table in TABLES
        ],
        _entity("View", "sales_view", owner="Joe"),
    ]
    created = await EntityWriter(found).create_or_update(
        AtlasEntitiesWithExtInfo.model_validate({"entities": entities})
    )
    GUIDS.clear()
    GUIDS.update({key.removeprefix("-"): value for key, value in (created.guid_assignments or {}).items()})
    classifications = EntityClassifications(found)
    for name, tag in (("sales_fact", "Fact"), ("time_dim", "Dimension"), ("customer_dim", "PII")):
        await classifications.add_classifications(GUIDS[name], [AtlasClassification(type_name=tag)])
    await EntityWriter(found).delete_by_id(GUIDS["Old"])
    return found


def _entity(type_name: str, name: str = "", **attributes: Any) -> dict[str, Any]:  # noqa: ANN401 - Atlas JSON
    return {
        "typeName": type_name,
        "guid": f"-{name}",
        "attributes": {"qualifiedName": name, **attributes, "name": name},
    }


async def dsl(
    store: EntityStore,
    query: str | None,
    *,
    type_name: str | None = None,
    classification: str | None = None,
    limit: int = 0,
    offset: int = 0,
) -> dict[str, Any]:
    """The answer to ``searchUsingDSL``, as JSON."""
    service = EntityDiscoveryService(store)
    query_str = service.get_dsl_query_using_type_name_classification(query, type_name, classification)
    return (await service.search_using_dsl_query(query_str, limit, offset)).to_json()


async def names(store: EntityStore, query: str | None, *, ordered: bool = False, **params: Any) -> list[str]:  # noqa: ANN401 - parameters
    """The names a DSL query finds: in order when ``ordered``, else sorted (entities written together are unordered)."""
    found = [entity["attributes"]["name"] for entity in (await dsl(store, query, **params)).get("entities", [])]
    return found if ordered else sorted(found)


async def failure(store: EntityStore, query: str) -> str:
    """The reason a DSL query fails with ``INVALID_DSL_QUERY``."""
    with pytest.raises(AtlasError) as raised:
        await dsl(store, query)
    assert raised.value.code is AtlasErrorCode.INVALID_DSL_QUERY
    return (
        str(raised.value)
        .split(" | Reason: ", 1)[1]
        .removesuffix(". Please refer to Atlas DSL grammar for more information")
    )


ALL_TABLES = ["sales_fact", "time_dim", "customer_dim", "log_fact", "sales_view"]


@pytest.mark.covers(f"{D}.get_dsl_query_using_type_name_classification", rules=["DSE-02"])
@pytest.mark.parametrize(
    ("query", "type_name", "classification", "expected"),
    [
        ("where name = 'x'", "Table", None, "`Table` where name = 'x'"),
        ("", "`Table`", None, "`Table` "),
        (None, "Table", "PII", "`Table`  isa PII"),
        ("where name = 'x'", "Table", "PII", "`Table` where name = 'x'"),
        ("Table", None, None, "Table"),
    ],
)
def test__the_query_names_the_type_and_classification(
    query: str | None, type_name: str | None, classification: str | None, expected: str
) -> None:
    """``typeName`` in backticks before the query, ``isa`` the classification only without a query."""
    found = EntityDiscoveryService.get_dsl_query_using_type_name_classification(query, type_name, classification)
    assert found == expected


@pytest.mark.covers(f"{D}.search_using_dsl_query", f"{X}.DslQueryExecutor.execute", rules=["DSE-02", "DSE-13"])
async def test__the_answer_is_a_dsl_result_of_entity_headers(store: EntityStore) -> None:
    """``queryType`` ``DSL``, the query as ``queryText``, each entity's header with its classifications."""
    found = await dsl(store, "where name = 'time_dim'", type_name="Table")
    assert found["queryType"] == "DSL"
    assert found["queryText"] == "`Table` where name = 'time_dim'"
    (header,) = found["entities"]
    assert header["typeName"] == "Table"
    assert header["guid"] == GUIDS["time_dim"]
    assert header["classificationNames"] == ["Dimension"]
    assert [tag["typeName"] for tag in header["classifications"]] == ["Dimension"]


@pytest.mark.covers(f"{X}.DslQueryExecutor.execute", rules=["DSE-13"])
async def test__nothing_found_answers_no_entities(store: EntityStore) -> None:
    """``processVertices`` adds no entity: the answer has no ``entities``."""
    found = await dsl(store, "Table where name = 'nothing'")
    assert "entities" not in found


@pytest.mark.covers(f"{X}.translatable", rules=["DSE-03"])
@pytest.mark.parametrize(
    ("query", "expected"),
    [
        ("Table", "Table limit 25 offset 5"),
        ("Table limit 2", "Table limit 2"),
        ("Table where name = 'offsetting'", "Table where name = 'offsetting'"),
    ],
)
def test__limit_and_offset_are_appended_unless_named(query: str, expected: str) -> None:
    """``getStringWithLimitOffset`` looks for the words anywhere in the text."""
    assert translatable(query, 25, 5) == expected


@pytest.mark.covers(f"{D}.search_using_dsl_query", f"{C}", rules=["DSE-01", "DSE-03"])
async def test__paging_by_request_or_by_query(store: EntityStore) -> None:
    """The request's limit and offset, normalised; the query's own win over them."""
    assert await names(store, "Table orderby name", ordered=True, limit=2, offset=1) == ["log_fact", "sales_fact"]
    assert await names(store, "Table orderby name limit 1 offset 3", ordered=True, limit=2) == ["sales_view"]
    assert len(await names(store, "Table", limit=-5)) == len(ALL_TABLES)
    assert await names(store, "Table where name = 'offset'") == []


@pytest.mark.covers(f"{X}.DslQueryExecutor.execute", rules=["DSE-03"])
async def test__a_query_that_does_not_parse_names_the_text_parsed(store: EntityStore) -> None:
    """The appended limit and offset are part of the query the error names."""
    with pytest.raises(AtlasError) as raised:
        await dsl(store, "Table where")
    assert str(raised.value).startswith("Invalid DSL query: Table where limit 100 offset 0 | Reason: ")


@pytest.mark.covers(C, rules=["DSE-04"])
@pytest.mark.parametrize(
    ("query", "expected"),
    [
        ("Table", ALL_TABLES),
        ("View", ["sales_view"]),
        ("`Table`", ALL_TABLES),
        ("DB", ["Sales", "Reporting", "Old"]),
        ("from DB", ["Sales", "Reporting", "Old"]),
        ("Dimension", ["time_dim"]),
        ("_CLASSIFIED", ["sales_fact", "time_dim", "customer_dim"]),
        ("_NOT_CLASSIFIED", ["Sales", "Reporting", "Old", "log_fact", "sales_view"]),
        ("_ALL_ENTITY_TYPES", ["Sales", "Reporting", "Old", *ALL_TABLES]),
        ("Table PII", ["customer_dim"]),
        ("Table DB", []),
    ],
)
async def test__sources_find_types_and_classifications(store: EntityStore, query: str, expected: list[str]) -> None:
    """Sub types too, every state, classifications attached; further sources narrow (``DSLQueriesTest``)."""
    assert await names(store, query) == sorted(expected)


@pytest.mark.covers(C, rules=["DSE-05"])
async def test__an_unknown_source_fails(store: EntityStore) -> None:
    """``registerActive``: a name that is no entity or classification type (``PIII``, ``TableTTT``)."""
    assert await failure(store, "PIII") == "DSL Semantic Error - PIII type not found"
    assert await failure(store, "TableKind") == "DSL Semantic Error - TableKind type not found"


@pytest.mark.covers(C, rules=["DSE-05"])
async def test__aliases_name_the_active_type(store: EntityStore) -> None:
    """``Table as t where t.name = ...``; ``t`` is the type; a second alias fails, its message unfilled."""
    assert await names(store, "Table as t where t.name = 'time_dim'") == ["time_dim"]
    assert await names(store, "Table as t where t.__state = 'ACTIVE' and t has description") == [
        "sales_fact",
        "time_dim",
    ]
    assert await failure(store, "Table as Table") == (
        "DSL Semantic Error - Duplicate alias found: {0} for type {1} already present."
    )
    assert await names(store, "Table Table") == sorted(ALL_TABLES)


@pytest.mark.covers(C, rules=["DSE-06", "DSE-07"])
@pytest.mark.parametrize(
    ("query", "expected"),
    [
        ('Table where name = "sales_fact"', ["sales_fact"]),
        ("Table where name = sales_fact", ["sales_fact"]),
        ("Table where Asset.name = 'time_dim'", ["time_dim"]),
        ("Table where owner != 'Joe'", ["time_dim", "customer_dim", "log_fact"]),
        ("Table where partitionSize = 2048", ["sales_fact"]),
        ("Table where partitionSize > 100 or partitionSize = 10", ["sales_fact", "time_dim"]),
        ("Table where retention >= 10", ["sales_fact"]),
        ("Table where retention != 10", ["time_dim", "customer_dim", "log_fact", "sales_view"]),
        ("Table where isFile = true", ["sales_fact"]),
        ("Table where isFile = FALSE", ["time_dim", "customer_dim", "log_fact", "sales_view"]),
        ("Table where kind = 'VIEW'", ["time_dim"]),
        ("Table where name < 'log'", ["customer_dim"]),
        ("Table where tags = 'crm'", ["customer_dim"]),
        ("Table where __guid = 'none'", []),
        ("DB where __state = 'DELETED'", ["Old"]),
        ("Table where parameters = 'x'", []),
        ("Table where retention = 'ten'", []),
    ],
)
async def test__comparisons_read_the_value_as_the_attributes_type(
    store: EntityStore, query: str, expected: list[str]
) -> None:
    """Strings, numbers (DV-90), booleans, enums, arrays, system attributes; ``!=`` of a string holds without a
    value, of a number only with one (``GremlinQueryComposerTest`` numericAttributes, systemAttributes).
    """  # noqa: D205 - one sentence
    assert await names(store, query) == sorted(expected)


@pytest.mark.covers(C, rules=["DSE-06"])
@pytest.mark.parametrize(
    ("query", "expected"),
    [
        ('Table where createTime = "2014-12-11T02:35:58.440Z"', ["sales_fact"]),
        ('Table where createTime >= "2014-12-11"', ["sales_fact"]),
        (
            'Table where createTime < "2014-12-11T02:35:58.440Zignored"',
            ["time_dim", "customer_dim", "log_fact", "sales_view"],
        ),
        ('Table where createTime = "2013-12-32T00:00:00.000Z"', ["time_dim"]),
        ('Table where createTime = "2013-14-01T00:00:00.000Z"', []),
        ('DB where createTime = "2014-12-11"', ["Sales"]),
    ],
)
async def test__dates_are_read_as_simple_date_format_reads_them(
    store: EntityStore, query: str, expected: list[str]
) -> None:
    """ISO 8601 with milliseconds, else a date, in UTC; lenient: the 13th month and the 32nd day roll over."""
    assert await names(store, query) == sorted(expected)


@pytest.mark.covers(C, rules=["DSE-06"])
async def test__a_date_neither_format_reads_fails(store: EntityStore) -> None:
    """``INVALID_DSL_INVALID_DATE`` (``DSLQueriesTest`` errorQueries: ``createTime >= "2014-12"``)."""
    assert await failure(store, 'Table where createTime >= "2014-12"') == "DSL Semantic Error - Date format: 2014-12."


@pytest.mark.covers(C, rules=["DSE-06"])
async def test__an_attribute_the_type_does_not_have_fails(store: EntityStore) -> None:
    """The type of the unknown name, then its qualified name, are not found."""
    assert await failure(store, "Table where xxx = 1") == (
        "DSL Semantic Error - xxx type not found, DSL Semantic Error - Qualified name for xxx failed!"
    )


@pytest.mark.covers(C, rules=["DSE-07"])
@pytest.mark.parametrize(
    ("query", "string_like"),
    [
        ("Table where retention != 10", False),
        ("Table where isFile != true", False),
        ("Table where owner != 'Joe'", True),
    ],
)
def test__not_equal_holds_without_a_value_only_for_strings(store: EntityStore, query: str, string_like: bool) -> None:  # noqa: FBT001
    """``HAS_NOT_OPERATOR`` (no value or another) for strings; ``neq`` (another value) for the rest. Entities have
    defaults for numbers, dates and booleans, so the difference shows in the query composed.
    """  # noqa: D205 - one sentence
    tree = parse(f"{query} limit 10 offset 0")
    found = DslQueryComposer(store.registry, QueryMetadata.of(tree), 10, 0).compose(tree).filter
    assert isinstance(found, sq.Group)
    condition = found.criteria[1]
    if string_like:
        assert isinstance(condition, sq.Criterion)
        assert condition.test is sq.Test.NEQ
    else:
        assert isinstance(condition, sq.Group)
        assert [criterion.test for criterion in condition.criteria] == [sq.Test.NOT_NULL, sq.Test.NEQ]  # type: ignore[union-attr]


@pytest.mark.covers(C, rules=["DSE-07"])
@pytest.mark.parametrize(
    ("query", "expected"),
    [
        ("Table where name eq 'time_dim'", ["time_dim"]),
        ("Table where retention GT 5", ["sales_fact"]),
        ("Table where retention lte 3 and retention > 0", ["customer_dim"]),
        ("Table where name NEQ 'time_dim' and name neq 'log_fact'", ["sales_fact", "customer_dim", "sales_view"]),
    ],
)
async def test__operator_words_compare_as_their_symbols(store: EntityStore, query: str, expected: list[str]) -> None:
    """``eq``, ``lt``, ... in any case, which Atlas fails on (DV-89)."""
    assert await names(store, query) == sorted(expected)


@pytest.mark.covers(C, rules=["DSE-07"])
@pytest.mark.parametrize(
    ("query", "expected"),
    [
        ("Table where name = ['time_dim', 'log_fact']", ["time_dim", "log_fact"]),
        ("Table where name != ['time_dim']", ["time_dim"]),
        ('Table where retention = ["3", "10"]', ["sales_fact", "customer_dim"]),
        ("Table where tags = ['daily', 'none']", ["sales_fact"]),
    ],
)
async def test__a_value_array_holds_for_any_of_its_values(store: EntityStore, query: str, expected: list[str]) -> None:
    """``within``, whatever the operator; values read as the attribute's type (DV-91)."""
    assert await names(store, query) == sorted(expected)


@pytest.mark.covers(C, rules=["DSE-08"])
@pytest.mark.parametrize(
    ("query", "expected"),
    [
        ("Table where name like 'sales*'", ["sales_fact", "sales_view"]),
        ("Table where owner like 'jo*'", ["sales_fact", "customer_dim", "sales_view"]),
        ("Table where owner like 'B?'", ["time_dim", "customer_dim"]),
        ("Table where description like 'dimension'", ["time_dim"]),
        ("Table where owner like 'Joe BI'", ["customer_dim"]),
        ("Table where owner like 'joe BI'", []),
        ("Table where owner like '*BI'", ["time_dim", "customer_dim"]),
        ("Table where tableType like 'Managed'", []),
        ("Table where tableType like 'Managed*'", ["sales_fact"]),
        ('Table where tableType like "\\*Tab_*"', []),
        ("Table where retention like '1*'", []),
        ("Table where name like 'table[0-9'", []),
    ],
)
async def test__like_matches_the_whole_value_or_a_word(store: EntityStore, query: str, expected: list[str]) -> None:
    """Letters and digits only match a word in any case (DV-92); else, and for ``indexType`` ``STRING``, the whole
    value in case (``GremlinQueryComposerTest`` whereClauseTextContains).
    """  # noqa: D205 - one sentence
    assert await names(store, query) == sorted(expected)


@pytest.mark.covers(C, rules=["DSE-09"])
async def test__is_incomplete_tests_incompleteness(store: EntityStore) -> None:
    """Every entity here is complete: ``= 0``, ``= false`` and ``!= 1`` find them, ``= 1`` and ``= true`` none."""
    every = sorted(["Sales", "Reporting", "Old"])
    assert await names(store, "DB where __isIncomplete = 0") == every
    assert await names(store, "DB where __isIncomplete = false") == every
    assert await names(store, "DB where __isIncomplete != 1") == every
    assert await names(store, "DB where __isIncomplete = 1") == []
    assert await names(store, "DB where __isIncomplete = 'true'") == []
    assert await names(store, "DB where __isIncomplete != 0") == []
    assert await names(store, "DB where __isIncomplete = 2") == []


@pytest.mark.covers(C, rules=["DSE-10"])
@pytest.mark.parametrize(
    ("query", "expected"),
    [
        ("Table has description", ["sales_fact", "time_dim"]),
        ("Table has __state", ALL_TABLES),
        ("Table isa Dimension", ["time_dim"]),
        ("Table is 'Fact'", ["sales_fact"]),
        ("Table isa _CLASSIFIED", ["sales_fact", "time_dim", "customer_dim"]),
        ("Table isa _NOT_CLASSIFIED", ["log_fact", "sales_view"]),
        ("Table isa '_CLASSIFIED'", []),
        ("Table where Table isa PII", ["customer_dim"]),
        ("Table where DB isa PII", []),
        ("Table has name and name = 'sales_fact'", ["sales_fact"]),
        ("Table isa 'Dimension' and name = 'time_dim'", ["time_dim"]),
        ("Table as t where t has owner and t isa PII", ["customer_dim"]),
        ("isa_free", []),
    ],
)
async def test__has_and_isa(store: EntityStore, query: str, expected: list[str]) -> None:
    """``HAS_PROPERTY`` and ``TRAIT``; the subject of a lone ``isa`` is a source (``GremlinQueryComposerTest``
    keywordsInWhereClause).
    """  # noqa: D205 - one sentence
    if query == "isa_free":
        with pytest.raises(AtlasError):
            await names(store, query)
        return
    assert await names(store, query) == sorted(expected)


@pytest.mark.covers(C, rules=["DSE-10"])
async def test__has_and_isa_fail_on_what_they_cannot_test(store: EntityStore) -> None:
    """``Table has db``, ``Table has xxx``, ``Table isa Table`` (``GremlinQueryComposerTest`` invalidQueries2)."""
    assert await failure(store, "Table has db") == "DSL Semantic Error - Property needs to be a primitive type: db"
    assert await failure(store, "Table has xxx") == "DSL Semantic Error - Property needs to be a primitive type: xxx"
    assert await failure(store, "Table isa Table") == "DSL Semantic Error - Table classification not found"


@pytest.mark.covers(C, rules=["DSE-11"])
@pytest.mark.parametrize(
    ("query", "expected"),
    [
        ("Table where name = 'time_dim' or name = 'log_fact' and owner = 'Joe'", []),
        ("Table where name = 'log_fact' and owner = 'Joe' or name = 'time_dim'", ["time_dim"]),
        ("Table where (name = 'log_fact' and owner = 'Joe') or name = 'time_dim'", ["time_dim"]),
        ("Table where name = 'time_dim' or (name = 'log_fact' and owner = 'Joe')", ["time_dim"]),
        ("Table where (name = 'time_dim')", ["time_dim"]),
        ("Table where ((name = 'time_dim'))", ["time_dim"]),
        ("Table qualifiedName = 'sales_fact' AND owner = 'Joe'", ["sales_fact"]),
        ("Table name = 'sales_fact'", ["sales_fact"]),
    ],
)
async def test__and_and_or_join_left_to_right(store: EntityStore, query: str, expected: list[str]) -> None:
    """``processExprRight``: no precedence; parentheses group; expressions after a source are conditions."""
    assert await names(store, query) == sorted(expected)


@pytest.mark.covers(C, rules=["DSE-11"])
async def test__an_expression_without_a_type_source(store: EntityStore) -> None:
    """Ignored, unless an ``isa`` or ``has`` names its subject; a query with no type finds every entity."""
    assert await names(store, "PII name = 'x'") == ["customer_dim"]
    assert await names(store, "Table has description") == ["sales_fact", "time_dim"]
    assert await names(store, "Table isa PII") == ["customer_dim"]


@pytest.mark.covers(C, rules=["DSE-12"])
async def test__orderby_sorts_and_leaves_out_entities_without_a_value(store: EntityStore) -> None:
    """``has(p).order().by(p)``; ``desc`` in any case; parentheses around the name ignored."""
    query = "Table where createTime > '2000-01-01' orderby createTime"
    assert await names(store, query, ordered=True) == ["time_dim", "sales_fact"]
    assert await names(store, "Table orderby (description) DESC", ordered=True) == ["sales_fact", "time_dim"]
    assert await names(store, "Table orderby name asc limit 2", ordered=True) == ["customer_dim", "log_fact"]


@pytest.mark.covers(C, rules=["DSE-12"])
async def test__orderby_a_non_primitive_fails(store: EntityStore) -> None:
    """``INVALID_DSL_ORDERBY`` (``DSLQueriesTest`` errorQueries: ``orderby(db.name)``)."""
    assert await failure(store, "Table orderby db") == "DSL Semantic Error - OrderBy attribute db is non-primitive"
    assert await failure(store, "Table orderby (db.name)") == (
        "DSL Semantic Error - OrderBy attribute db.name is non-primitive"
    )


@pytest.mark.covers(C, rules=["DSE-14"])
async def test__semantic_errors_are_joined_in_order(store: EntityStore) -> None:
    """Each error found, in order, joined by ``, ``."""
    assert await failure(store, "Table where xxx = 1 and name isa Nope") == (
        "DSL Semantic Error - xxx type not found, DSL Semantic Error - Qualified name for xxx failed!, "
        "DSL Semantic Error - Nope classification not found"
    )


@pytest.mark.covers(C, rules=["DSE-15"])
@pytest.mark.parametrize(
    ("query", "reason"),
    [
        ("Table hasTerm sales", "hasTerm is not supported"),
        ("Table where retention + 1 = 2", "a comparison takes a name and a value, not retention+1"),
        ("Table where retention = 1 * 2", "a comparison takes a name and a value, not 1*2"),
        ("Table where count()", "count() is not a condition"),
        ("Table where name", "name is not a condition"),
        ("Table isa (PII)", "isa takes a classification name, not an expression"),
        ("where name = 'x'", "a where clause needs a type or classification before it"),
        ("Table select name", "select is not supported yet"),
        ("Table groupby(owner)", "groupby is not supported yet"),
        ("Table where db.name = 'Sales'", "the referred attribute db is not supported yet"),
        ("Table, db", "the referred attribute db is not supported yet"),
        ("Table where Dimension.tagAttr1 = 'x'", "classification attributes are not supported yet"),
    ],
)
async def test__forms_not_searched_fail_with_a_reason(store: EntityStore, query: str, reason: str) -> None:
    """Declared (DV-95) and, until 4.4b, temporary (DV-96)."""
    assert await failure(store, query) == reason
