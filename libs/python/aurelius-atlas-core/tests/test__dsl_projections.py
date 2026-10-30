"""DSL projections and traversals (DSP-01 to DSP-09) on the in-memory documents.

Read from ``SelectClauseComposer``, ``SelectClauseProjections``, ``GremlinQueryComposer`` (``process``,
``addGroupBy``, ``introduceType``, ``addWhere``) and ``TraversalBasedExecutor`` of Apache Atlas 2.4.0; the queries
are those of its ``DSLQueriesTest`` (``basicProvider``, ``minMaxCountProvider``, ``errorQueriesProvider``) on
types shaped as its ``BasicTestSetup``'s.
"""

from typing import Any

import pytest
from aurelius_atlas_core.discovery_service import EntityDiscoveryService
from aurelius_atlas_core.dsl_query_executor import MAX_STEP_ENTITIES
from aurelius_atlas_core.entity_classifications import EntityClassifications
from aurelius_atlas_core.entity_store import EntityStore
from aurelius_atlas_core.entity_writer import EntityWriter
from aurelius_atlas_core.select_clause_projections import get_sublist_for_group_by
from aurelius_atlas_core.testing.memory import MemoryEntityDocuments
from aurelius_atlas_dsl.atlas_dsl import QueryMetadata, parse
from aurelius_atlas_model.errors import AtlasError, AtlasErrorCode
from aurelius_atlas_model.instance import AtlasClassification, AtlasEntitiesWithExtInfo
from aurelius_atlas_model.typedef import AtlasTypesDef
from aurelius_atlas_typesystem.registry import TypeRegistry

X = "aurelius_atlas_core.dsl_query_executor.DslQueryExecutor.execute"
C = "aurelius_atlas_core.dsl_query_composer.DslQueryComposer.compose"
P = "aurelius_atlas_core.select_clause_projections"
S = "aurelius_atlas_core.select_clause_composer.SelectClauseComposer"
GUIDS: dict[str, str] = {}


def _attribute(name: str, type_name: str = "string", **more: Any) -> dict[str, Any]:  # noqa: ANN401 - Atlas JSON
    return {"name": name, "typeName": type_name, "isOptional": True, "cardinality": "SINGLE", **more}


def _end(type_name: str, name: str, cardinality: str = "SINGLE") -> dict[str, Any]:
    return {"type": type_name, "name": name, "cardinality": cardinality}


TYPES = {
    "classificationDefs": [
        {"name": "Dimension", "attributeDefs": [_attribute("tagAttr1")]},
        {"name": "Fine", "superTypes": ["Dimension"]},
    ],
    "entityDefs": [
        {
            "name": "Asset",
            "attributeDefs": [_attribute("qualifiedName", isUnique=True), _attribute("name"), _attribute("owner")],
        },
        {"name": "hive_db", "superTypes": ["Asset"]},
        {"name": "hive_storagedesc", "superTypes": ["Asset"], "attributeDefs": [_attribute("location")]},
        {
            "name": "hive_table",
            "superTypes": ["Asset"],
            "attributeDefs": [_attribute("sd", "hive_storagedesc"), _attribute("retention", "int")],
        },
        {"name": "hive_column", "superTypes": ["Asset"], "attributeDefs": [_attribute("dataType")]},
        {"name": "Person", "superTypes": ["Asset"], "attributeDefs": [_attribute("age", "float")]},
    ],
    "relationshipDefs": [
        {
            "name": "hive_table_db",
            "relationshipCategory": "ASSOCIATION",
            "endDef1": _end("hive_table", "db"),
            "endDef2": _end("hive_db", "tables", "SET"),
        },
        {
            "name": "hive_table_columns",
            "relationshipCategory": "COMPOSITION",
            "endDef1": {**_end("hive_table", "columns", "SET"), "isContainer": True},
            "endDef2": _end("hive_column", "table"),
        },
    ],
}


def _entity(
    type_name: str,
    name: str,
    relationships: dict[str, Any] | None = None,
    **attributes: Any,  # noqa: ANN401 - Atlas JSON
) -> dict[str, Any]:
    found: dict[str, Any] = {
        "typeName": type_name,
        "guid": f"-{name}",
        "attributes": {"qualifiedName": name, **attributes, "name": name},
    }
    if relationships:
        found["relationshipAttributes"] = relationships
    return found


def _ref(type_name: str, name: str) -> dict[str, str]:
    return {"typeName": type_name, "guid": f"-{name}"}


@pytest.fixture
async def store() -> EntityStore:
    """Three databases; tables in them with columns and a storage description; four people; ``time_dim`` is a
    ``Dimension`` of ``tagAttr1`` ``timeValue``, ``report_view`` a ``Fine`` (a sub type) of ``v2``.
    """  # noqa: D205 - one sentence
    registry = TypeRegistry()
    with registry.update() as transient:
        transient.add_types(AtlasTypesDef.model_validate(TYPES))
    found = EntityStore(registry, MemoryEntityDocuments())
    entities = [
        _entity("hive_db", "Sales", owner="John ETL"),
        _entity("hive_db", "Reporting", owner="Jane BI"),
        _entity("hive_db", "Logging", owner="Tim ETL"),
        _entity("hive_storagedesc", "sd1", location="/hdfs/sales"),
        _entity(
            "hive_table",
            "sales_fact",
            {"db": _ref("hive_db", "Sales")},
            owner="Joe",
            retention=3,
            sd=_ref("hive_storagedesc", "sd1"),
        ),
        _entity("hive_table", "time_dim", {"db": _ref("hive_db", "Sales")}, owner="Jane BI", retention=7),
        _entity("hive_table", "log_fact", {"db": _ref("hive_db", "Logging")}, owner="Tim ETL"),
        _entity("hive_table", "report_view", {"db": _ref("hive_db", "Reporting")}, owner="Jane BI"),
        _entity("hive_column", "time_id", {"table": _ref("hive_table", "sales_fact")}, dataType="int"),
        _entity("hive_column", "customer_id", {"table": _ref("hive_table", "sales_fact")}, dataType="int"),
        _entity("hive_column", "day", {"table": _ref("hive_table", "time_dim")}, dataType="string"),
        _entity("Person", "Julius", age=50.0),
        _entity("Person", "Max", age=20.0),
        _entity("Person", "Jane", age=16.0),
        _entity("Person", "Baby", age=0.0),
    ]
    created = await EntityWriter(found).create_or_update(
        AtlasEntitiesWithExtInfo.model_validate({"entities": entities})
    )
    GUIDS.clear()
    GUIDS.update({key.removeprefix("-"): value for key, value in (created.guid_assignments or {}).items()})
    classifications = EntityClassifications(found)
    for name, tag, value in (("time_dim", "Dimension", "timeValue"), ("report_view", "Fine", "v2")):
        classification = AtlasClassification(type_name=tag, attributes={"tagAttr1": value}, propagate=False)
        await classifications.add_classifications(GUIDS[name], [classification])
    return found


async def dsl(store: EntityStore, query: str, *, limit: int = 0, offset: int = 0) -> dict[str, Any]:
    """The answer to a DSL query, as JSON."""
    return (await EntityDiscoveryService(store).search_using_dsl_query(query, limit, offset)).to_json()


async def names(store: EntityStore, query: str) -> list[str]:
    """The names of the entities a DSL query finds, sorted."""
    return sorted(entity["attributes"]["name"] for entity in (await dsl(store, query)).get("entities", []))


async def table(store: EntityStore, query: str, **page: int) -> tuple[list[str], list[list[Any]]]:
    """The labels and the rows of a DSL query's ``attributes``."""
    found = await dsl(store, query, **page)
    assert "queryType" not in found
    return found["attributes"]["name"], found["attributes"]["values"]


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


@pytest.mark.covers(X, C, f"{P}.projection_rows", f"{S}.of", rules=["DSP-01", "DSP-02"])
async def test__a_select_answers_rows_of_the_entities_found(store: EntityStore) -> None:
    """``hive_db where name = "Reporting" select name, owner``: labels as written, ``as`` names, a row each."""
    labels, rows = await table(store, 'hive_db where (name = "Reporting") select name as _col_0, owner as _col_1')
    assert (labels, rows) == (["_col_0", "_col_1"], [["Reporting", "Jane BI"]])
    labels, rows = await table(store, "hive_table where owner = 'Jane BI' select hive_table.owner")
    assert (labels, rows) == (["hive_table.owner"], [["Jane BI"]])


@pytest.mark.covers(
    X, f"{P}.projection_rows", "aurelius_atlas_core.search_fields.vertex_property", rules=["DSP-01", "DSP-02"]
)
async def test__rows_hold_values_or_nothing_and_none_found_has_no_attributes(store: EntityStore) -> None:
    """A missing value is ``""``; equal rows are one; nothing found answers the query without ``attributes``."""
    _, rows = await table(store, "hive_table where name = 'log_fact' select name, retention")
    assert rows == [["log_fact", 0]]
    _, rows = await table(store, "Person where name = 'Max' select name, owner")
    assert rows == [["Max", ""]]
    _, rows = await table(store, "hive_table where owner = 'Jane BI' select owner")
    assert rows == [["Jane BI"]]
    nothing = await dsl(store, "hive_table where name = 'none' select name")
    assert (nothing["queryType"], "attributes" in nothing, "entities" in nothing) == ("DSL", False, False)


@pytest.mark.covers(X, C, rules=["DSP-02"])
async def test__a_select_of_the_type_or_a_referred_attribute_answers_entities(store: EntityStore) -> None:
    """``hive_db as d select d`` the databases; ``hive_table select db`` the databases referred to."""
    assert await names(store, "hive_db as d select d") == ["Logging", "Reporting", "Sales"]
    assert await names(store, "hive_table where owner = 'Jane BI' select db") == ["Reporting", "Sales"]
    assert await names(store, "hive_column select table") == ["sales_fact", "time_dim"]


@pytest.mark.covers(X, f"{P}.projection_rows", rules=["DSP-02"])
async def test__a_select_of_a_referred_attribute_s_attribute_holds_headers(store: EntityStore) -> None:
    """``select db.name``: the traversal executor reads only primitive items' values; the referred entity's header."""
    labels, rows = await table(store, "hive_table where name = 'log_fact' select db.name")
    assert labels == ["db.name"]
    ((header,),) = rows
    assert (header["typeName"], header["guid"], header["attributes"]["name"]) == (
        "hive_db",
        GUIDS["Logging"],
        "Logging",
    )


@pytest.mark.covers(X, f"{P}.projection_rows", f"{S}.has_aggregators", rules=["DSP-03"])
async def test__aggregates_are_of_every_entity_found(store: EntityStore) -> None:
    """``minMaxCountProvider``: ``count()``, ``max``, ``min`` of names in case; of people's ages, a double sum."""
    assert await table(store, "from hive_db select max(name), min(name)") == (
        ["max(name)", "min(name)"],
        [["Sales", "Logging"]],
    )
    assert await table(store, "from hive_db select count() ") == (["count()"], [[3]])
    labels, rows = await table(
        store, "from Person select count() as 'count', max(Person.age) as 'max', min(Person.age) as 'min'"
    )
    assert (labels, rows) == (["'count'", "'max'", "'min'"], [[4, 50.0, 0.0]])
    assert await table(store, "from Person select count() as 'count', sum(Person.age) as 'sum'") == (
        ["'count'", "'sum'"],
        [[4, 86.0]],
    )
    assert await table(store, "from Person select count() limit 1") == (["count()"], [[4]])


@pytest.mark.covers(X, f"{P}.projection_rows", rules=["DSP-03"])
async def test__min_is_null_when_an_entity_has_no_value(store: EntityStore) -> None:
    """``VertexPropertyComparator``: no value is least; ``owner`` is missing on the people."""
    assert await table(store, "Asset where name = 'Max' or name = 'Sales' select min(owner), max(owner)") == (
        ["min(owner)", "max(owner)"],
        [[None, "John ETL"]],
    )


@pytest.mark.covers(
    C,
    f"{S}.is_aggregator_with_argument",
    f"{S}.has_multiple_referred_types",
    f"{S}.has_mixed_attributes",
    rules=["DSP-04"],
)
@pytest.mark.parametrize(
    ("query", "reason"),
    [
        ("hive_table select xxx", "Unable to find qualified name for xxx"),
        (
            "hive_table select min(db), name",
            "DSL Semantic Error - Select clause has aggregation on referred attributes hive_table.db",
        ),
        ("hive_table select db, columns", "Unable to find qualified name for columns"),
        ("hive_column select table, db", "DSL Semantic Error - Select clause has multiple referred attributes 2"),
        ("hive_table select owner, db", "DSL Semantic Error - Select clause has simple and referred attributes"),
        (
            "hive_table select name as hive_table",
            "DSL Semantic Error - Duplicate alias found: {0} for type {1} already present.",
        ),
    ],
)
async def test__a_select_fails_as_atlas_checks_it(store: EntityStore, query: str, reason: str) -> None:
    """``errorQueriesProvider``: items no attribute names, aggregates of references, referred items mixed."""
    assert await failure(store, query) == reason


@pytest.mark.covers(X, C, f"{P}.get_sublist_for_group_by", rules=["DSP-05"])
async def test__groupby_gives_each_group_s_rows(store: EntityStore) -> None:
    """``minMaxCountProvider``: a row per group, groups by value; a count and a min per group."""
    assert await table(store, "from hive_db groupby (owner) select count() ") == (["count()"], [[1], [1], [1]])
    assert await table(store, "from hive_table groupby (owner) select owner, count()") == (
        ["owner", "count()"],
        [["Jane BI", 2], ["Joe", 1], ["Tim ETL", 1]],
    )
    assert await table(store, "from hive_table groupby (owner) select owner, min(name) orderby owner desc") == (
        ["owner", "min(name)"],
        [["Jane BI", "report_view"], ["Joe", "sales_fact"], ["Tim ETL", "log_fact"]],
    )
    assert await table(
        store, "from Asset where __typeName != 'Person' groupby (__typeName) select __typeName, count()"
    ) == (
        ["__typeName", "count()"],
        [["hive_column", 3], ["hive_db", 3], ["hive_storagedesc", 1], ["hive_table", 4]],
    )


@pytest.mark.covers(X, f"{P}.get_sublist_for_group_by", rules=["DSP-05"])
async def test__groupby_rows_are_paged_from_offset_minus_one(store: EntityStore) -> None:
    """``getSublistForGroupBy`` starts at ``offset - 1``: offset 2 skips one row, offset 1 none."""
    query = "from hive_table groupby (owner) select owner"
    assert (await table(store, query, limit=2, offset=2))[1] == [["Joe"], ["Tim ETL"]]
    assert (await table(store, query, limit=2, offset=1))[1] == [["Jane BI"], ["Joe"]]
    assert (await table(store, query, limit=2, offset=9))[1] == []
    tree = parse("t limit 3 offset 0")
    assert get_sublist_for_group_by([[1], [2]], QueryMetadata.of(tree)) == [[1], [2]]


@pytest.mark.covers(X, C, rules=["DSP-05"])
async def test__groupby_without_select_answers_every_group_s_entities(store: EntityStore) -> None:
    """Entities without a value are left out; a non-primitive attribute fails."""
    assert await names(store, "hive_table groupby (retention)") == ["log_fact", "report_view", "sales_fact", "time_dim"]
    assert await names(store, "Asset groupby (owner)") == [
        "Logging",
        "Reporting",
        "Sales",
        "log_fact",
        "report_view",
        "sales_fact",
        "time_dim",
    ]
    assert await failure(store, "hive_table groupby (db)") == (
        "DSL Semantic Error - Select clause has aggregation on referred attributes db"
    )


@pytest.mark.covers(X, C, rules=["DSP-06"])
@pytest.mark.parametrize(
    ("query", "expected"),
    [
        ("hive_table, columns", ["customer_id", "day", "time_id"]),
        ("hive_table where name = 'sales_fact', columns", ["customer_id", "time_id"]),
        ("hive_table where name = 'sales_fact' columns where dataType = 'int'", ["customer_id", "time_id"]),
        ("hive_table, sd", ["sd1"]),
        ("hive_column, table where owner = 'Jane BI'", ["time_dim"]),
        ("hive_table where name = 'log_fact', columns", []),
    ],
)
async def test__a_source_naming_a_reference_moves_to_the_entities_referred_to(
    store: EntityStore, query: str, expected: list[str]
) -> None:
    """Relationship ends and plain references alike; later conditions are of the entities moved to."""
    assert await names(store, query) == expected


@pytest.mark.covers(X, C, rules=["DSP-07"])
@pytest.mark.parametrize(
    ("query", "expected"),
    [
        ('hive_table where db.name = "Sales"', ["sales_fact", "time_dim"]),
        ('hive_table where (name = "sales_fact" and db.name = "Sales")', ["sales_fact"]),
        (
            'hive_table where (name = "time_dim" and db.name = "Sales") or (name = "log_fact" and db.name = "Sales")',
            ["time_dim"],
        ),
        ('hive_column where table.name = "sales_fact"', ["customer_id", "time_id"]),
        ('hive_table where columns.name = "day"', ["time_dim"]),
        ("hive_table where sd.location like '/hdfs/*'", ["sales_fact"]),
        ('hive_table where db.name = "None"', []),
    ],
)
async def test__a_condition_on_a_referred_entity(store: EntityStore, query: str, expected: list[str]) -> None:
    """``basicProvider``: ``db.name``, ``table.name``, ``columns.name``; references and relationships alike."""
    assert await names(store, query) == expected


@pytest.mark.covers(C, rules=["DSP-07"])
async def test__order_and_conditions_on_a_reference_itself_fail(store: EntityStore) -> None:
    """``errorQueriesProvider``: ``orderby(db.name)``, ``groupby(db.name)``; a reference compared directly."""
    assert await failure(store, "hive_table orderby (db.name)") == (
        "DSL Semantic Error - OrderBy attribute db.name is non-primitive"
    )
    assert await failure(store, "hive_table groupby (db.name)") == (
        "DSL Semantic Error - Select clause has aggregation on referred attributes db.name"
    )
    assert await failure(store, "hive_table where db = 'x'") == "DSL Semantic Error - Qualified name for db failed!"
    assert (
        await failure(store, "hive_table where db.xxx = 'x'")
        == "DSL Semantic Error - Qualified name for db.xxx failed!"
    )


@pytest.mark.covers(X, C, rules=["DSP-08"])
@pytest.mark.parametrize(
    ("query", "expected"),
    [
        ("hive_table where Dimension.tagAttr1 = 'timeValue'", ["time_dim"]),
        ("hive_table where Dimension.tagAttr1 = 'v2'", ["report_view"]),
        ("Dimension where Dimension.tagAttr1 like 'time*'", ["time_dim"]),
        ("hive_table where Dimension.tagAttr1 != 'none' and owner = 'Jane BI'", ["report_view", "time_dim"]),
        ("hive_table where Fine.tagAttr1 = 'timeValue'", []),
    ],
)
async def test__a_condition_on_a_classification_attribute(store: EntityStore, query: str, expected: list[str]) -> None:
    """Instances of the classification and its sub types; ``Dimension where tagAttr1 = ...`` needs the prefix."""
    assert await names(store, query) == expected


@pytest.mark.covers(C, rules=["DSP-08"])
async def test__a_classification_attribute_without_its_type_fails(store: EntityStore) -> None:
    """``errorQueriesProvider``: ``Dimension where tagAttr1 = 'tagValue'``."""
    assert await failure(store, "Dimension where tagAttr1 = 'tagValue'") == (
        "DSL Semantic Error - tagAttr1 type not found, DSL Semantic Error - Qualified name for tagAttr1 failed!"
    )


@pytest.mark.covers(X, rules=["DSP-09"])
def test__steps_read_at_most_ten_thousand_entities() -> None:
    """DSP-09, DV-98."""
    assert MAX_STEP_ENTITIES == 10_000
