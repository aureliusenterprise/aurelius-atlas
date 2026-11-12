"""The tree: the shape, the names, the processes, the temporary guids (DBS-03, DBS-07..09).

Tables are built as the reflection returns them, so each rule of DBS-03, DBS-07, DBS-08 and
DBS-09 reads off the entities the builder answers — in write order, with the ends riding
through the request-local guids the store resolves (EWR-11).
"""

from collections.abc import Sequence

import pytest
from aurelius_atlas_db_scanner.graph import (
    COLLECTION_TYPE,
    DATASET_TYPE,
    FIELD_TYPE,
    PROCESS_TYPE,
    SYSTEM_TYPE,
    build_graph,
    entity_line,
    qualified_component,
)
from aurelius_atlas_db_scanner.reflect import ColumnInfo, ForeignKeyInfo, TableInfo
from aurelius_atlas_model.instance import AtlasEntity

SYSTEM = "Warehouse DB"
"""The configured System name: DBS-03's SYSTEM_NAME, with a space to sanitize."""

DEFAULTS = "default"
"""The Collection name for the nameless default schema (DBS-03's SCHEMA_NAME)."""


def _table(
    schema: str | None,
    name: str,
    *,
    columns: Sequence[str] = (),
    primary_key: Sequence[str] = (),
    foreign_keys: Sequence[ForeignKeyInfo] = (),
    definition: str | None = None,
) -> TableInfo:
    """A reflected table, columns as bare names with a rendered type."""
    return TableInfo(
        schema=schema,
        name=name,
        definition=definition,
        primary_key=tuple(primary_key),
        columns=tuple(
            ColumnInfo(name=column, field_type="VARCHAR" if column.endswith("name") else "INTEGER")
            for column in columns
        ),
        foreign_keys=tuple(foreign_keys),
    )


def _by_type(entities: Sequence[AtlasEntity], type_name: str) -> list[AtlasEntity]:
    return [entity for entity in entities if entity.type_name == type_name]


def _attributes(entity: AtlasEntity) -> dict[str, str]:
    return dict(entity.attributes or {})


@pytest.mark.covers("aurelius_atlas_db_scanner.graph.qualified_component", rules=["DBS-03"])
def test_a_component_follows_the_legacy_sanitizing_rule() -> None:
    """Lowercase, ``&`` and ``-`` removed, whitespace to ``-`` — in that order (KSC-03's rule)."""
    assert qualified_component("Warehouse DB") == "warehouse-db"
    assert qualified_component("Sales & Marketing") == "sales-marketing"
    assert qualified_component("Q1-Report") == "q1report"


@pytest.mark.covers("aurelius_atlas_db_scanner.graph.build_graph", rules=["DBS-03"])
def test_the_tree_hangs_system_collections_datasets_fields_with_the_legacy_names() -> None:
    """DBS-03: one System, one Collection per schema, one Dataset per table, one Field per column.

    Each qualified under its parent with ``--``.
    """
    graph = build_graph(
        system_name=SYSTEM,
        schema_name=DEFAULTS,
        schemas=["sales"],
        tables=[_table("sales", "orders", columns=["id", "shop_name"])],
    )
    system, collection, dataset = (
        _by_type(graph.entities, SYSTEM_TYPE)[0],
        _by_type(graph.entities, COLLECTION_TYPE)[0],
        _by_type(graph.entities, DATASET_TYPE)[0],
    )
    assert _attributes(system)["qualifiedName"] == "warehouse-db"
    assert _attributes(collection)["qualifiedName"] == "warehouse-db--sales"
    assert _attributes(dataset)["qualifiedName"] == "warehouse-db--sales--orders"
    fields = _by_type(graph.entities, FIELD_TYPE)
    assert [_attributes(field)["qualifiedName"] for field in fields] == [
        "warehouse-db--sales--orders--id",
        "warehouse-db--sales--orders--shop_name",
    ]
    assert [_attributes(field)["fieldType"] for field in fields] == ["INTEGER", "VARCHAR"]
    assert [entity.type_name for entity in graph.entities] == [
        SYSTEM_TYPE,
        COLLECTION_TYPE,
        DATASET_TYPE,
        FIELD_TYPE,
        FIELD_TYPE,
    ]


@pytest.mark.covers("aurelius_atlas_db_scanner.graph.build_graph", rules=["DBS-03"])
def test_the_nameless_default_schema_hangs_under_the_configured_name() -> None:
    """DBS-03: a nameless schema's Collection answers SCHEMA_NAME, and the qualified names use it."""
    graph = build_graph(
        system_name=SYSTEM,
        schema_name="public",
        schemas=[None],
        tables=[_table(None, "orders", columns=["id"])],
    )
    collection = _by_type(graph.entities, COLLECTION_TYPE)[0]
    dataset = _by_type(graph.entities, DATASET_TYPE)[0]
    assert _attributes(collection)["name"] == "public"
    assert _attributes(collection)["qualifiedName"] == "warehouse-db--public"
    assert _attributes(dataset)["qualifiedName"] == "warehouse-db--public--orders"


@pytest.mark.covers("aurelius_atlas_db_scanner.graph.build_graph", rules=["DBS-03"])
def test_a_schema_whose_tables_the_patterns_dropped_keeps_an_empty_collection() -> None:
    """DBS-03: the scan read the schema, so its Collection is registered even with no table."""
    graph = build_graph(system_name=SYSTEM, schema_name=DEFAULTS, schemas=["sales", "ops"], tables=[])
    collections = _by_type(graph.entities, COLLECTION_TYPE)
    assert sorted(_attributes(collection)["name"] for collection in collections) == ["ops", "sales"]
    assert _by_type(graph.entities, DATASET_TYPE) == []


@pytest.mark.covers("aurelius_atlas_db_scanner.graph.build_graph", rules=["DBS-07"])
def test_the_table_comment_becomes_the_dataset_definition_and_a_bare_table_still_lands() -> None:
    """DBS-07: the comment rides as the dataset's definition; a zero-column table is still a dataset."""
    graph = build_graph(
        system_name=SYSTEM,
        schema_name=DEFAULTS,
        schemas=[None],
        tables=[
            _table(None, "orders", definition="One row per customer order"),
            _table(None, "empty"),
        ],
    )
    datasets = {
        _attributes(dataset)["name"]: _attributes(dataset) for dataset in _by_type(graph.entities, DATASET_TYPE)
    }
    assert datasets["orders"]["definition"] == "One row per customer order"
    assert "definition" not in datasets["empty"]
    assert len(_by_type(graph.entities, DATASET_TYPE)) == 2


@pytest.mark.covers("aurelius_atlas_db_scanner.graph.build_graph", rules=["DBS-08"])
def test_each_foreign_key_column_pair_becomes_one_process() -> None:
    """DBS-08: the referring dataset is the input, the referred one the output, qualified one level down."""
    tables = [
        _table("sales", "orders", columns=["id"], primary_key=["id"]),
        _table(
            "sales",
            "line",
            columns=["order_id"],
            foreign_keys=[ForeignKeyInfo(("order_id",), "sales", "orders", ("id",))],
        ),
    ]
    graph = build_graph(system_name=SYSTEM, schema_name=DEFAULTS, schemas=["sales"], tables=tables)
    process = _by_type(graph.entities, PROCESS_TYPE)[0]
    assert _attributes(process)["name"] == "sales.line.order_id"
    assert _attributes(process)["qualifiedName"] == "warehouse-db--sales--line--order_id"
    assert process.relationship_attributes is not None
    assert [end["typeName"] for end in process.relationship_attributes["inputs"]] == [DATASET_TYPE]
    assert [end["typeName"] for end in process.relationship_attributes["outputs"]] == [DATASET_TYPE]
    guid_of = {_attributes(dataset)["name"]: dataset.guid for dataset in _by_type(graph.entities, DATASET_TYPE)}
    assert [end["guid"] for end in process.relationship_attributes["inputs"]] == [guid_of["line"]]
    assert [end["guid"] for end in process.relationship_attributes["outputs"]] == [guid_of["orders"]]


@pytest.mark.covers("aurelius_atlas_db_scanner.graph.build_graph", rules=["DBS-08"])
def test_a_composite_key_becomes_one_process_per_column_pair() -> None:
    """DBS-08: a two-column key registers two processes, each pairing its own column."""
    tables = [
        _table("shop", "shops", columns=["code", "region"], primary_key=["code", "region"]),
        _table(
            "shop",
            "line",
            columns=["shop_code", "shop_region"],
            foreign_keys=[ForeignKeyInfo(("shop_code", "shop_region"), "shop", "shops", ("code", "region"))],
        ),
    ]
    graph = build_graph(system_name=SYSTEM, schema_name=DEFAULTS, schemas=["shop"], tables=tables)
    processes = _by_type(graph.entities, PROCESS_TYPE)
    assert sorted(_attributes(process)["name"] for process in processes) == [
        "shop.line.shop_code",
        "shop.line.shop_region",
    ]


@pytest.mark.covers("aurelius_atlas_db_scanner.graph.build_graph", rules=["DBS-08"])
def test_a_self_referencing_key_names_one_dataset_on_both_ends() -> None:
    """DBS-08: the self key is an honest graph fact — one dataset, both ends."""
    tables = [
        _table(
            None,
            "employee",
            columns=["manager_id"],
            foreign_keys=[ForeignKeyInfo(("manager_id",), None, "employee", ("manager_id",))],
        )
    ]
    graph = build_graph(system_name=SYSTEM, schema_name=DEFAULTS, schemas=[None], tables=tables)
    process = _by_type(graph.entities, PROCESS_TYPE)[0]
    assert process.relationship_attributes is not None
    inputs = [end["guid"] for end in process.relationship_attributes["inputs"]]
    outputs = [end["guid"] for end in process.relationship_attributes["outputs"]]
    assert inputs == outputs


@pytest.mark.covers("aurelius_atlas_db_scanner.graph.build_graph", rules=["DBS-08"])
def test_an_edge_to_a_table_outside_the_scan_is_dropped_with_a_notice() -> None:
    """DBS-08: a referred table the scan never registered cannot be a process end."""
    tables = [
        _table(
            "sales",
            "line",
            columns=["ghost_id"],
            foreign_keys=[ForeignKeyInfo(("ghost_id",), "archive", "ghosts", ("id",))],
        )
    ]
    graph = build_graph(system_name=SYSTEM, schema_name=DEFAULTS, schemas=["sales"], tables=tables)
    assert _by_type(graph.entities, PROCESS_TYPE) == []
    assert graph.notices == [
        (
            "sales.line (ghost_id): the referred table archive.ghosts is not in the"
            " scan — the foreign key is not registered"
        ),
    ]


@pytest.mark.covers("aurelius_atlas_db_scanner.graph.build_graph", rules=["DBS-08"])
def test_a_pair_that_resolves_to_no_referred_column_is_dropped_with_a_notice() -> None:
    """DBS-08: a None referred column — the reflection could not resolve it — names no end."""
    tables = [
        _table("sales", "orders", columns=["id"]),
        _table(
            "sales",
            "line",
            columns=["order_id"],
            foreign_keys=[ForeignKeyInfo(("order_id",), "sales", "orders", (None,))],
        ),
    ]
    graph = build_graph(system_name=SYSTEM, schema_name=DEFAULTS, schemas=["sales"], tables=tables)
    assert _by_type(graph.entities, PROCESS_TYPE) == []
    assert graph.notices == [
        (
            "sales.line.order_id: its foreign key names no referred column and the referred table"
            " answers no primary key there — not registered"
        )
    ]


@pytest.mark.covers("aurelius_atlas_db_scanner.graph.build_graph", rules=["DBS-09"])
def test_every_entity_carries_a_temporary_guid_and_the_ends_ride_through_them() -> None:
    """DBS-09: request-local guids (negative, unique per run) connect every end of the tree."""
    tables = [
        _table("sales", "orders", columns=["id"], primary_key=["id"]),
        _table(
            "sales",
            "line",
            columns=["order_id"],
            foreign_keys=[ForeignKeyInfo(("order_id",), "sales", "orders", ("id",))],
        ),
    ]
    graph = build_graph(system_name=SYSTEM, schema_name=DEFAULTS, schemas=["sales"], tables=tables)
    guids = [str(entity.guid) for entity in graph.entities]
    assert len(set(guids)) == len(guids)
    assert all(guid.startswith("-") for guid in guids)
    system, collection = graph.entities[0], graph.entities[1]
    assert collection.relationship_attributes is not None
    assert [end["guid"] for end in collection.relationship_attributes["systems"]] == [system.guid]
    system_collections = system.relationship_attributes
    assert system_collections is not None
    assert [end["guid"] for end in system_collections["collections"]] == [collection.guid]
    datasets = {_attributes(dataset)["name"]: dataset for dataset in _by_type(graph.entities, DATASET_TYPE)}
    orders, line = datasets["orders"], datasets["line"]
    assert line.relationship_attributes is not None
    assert [end["guid"] for end in line.relationship_attributes["collections"]] == [collection.guid]
    fields = _by_type(graph.entities, FIELD_TYPE)
    assert [end["guid"] for end in line.relationship_attributes["fields"]] == [
        field.guid for field in fields if _attributes(field)["name"] == "order_id"
    ]
    for field in fields:
        assert field.relationship_attributes is not None
        owner = orders if _attributes(field)["name"] == "id" else line
        assert [end["guid"] for end in field.relationship_attributes["datasets"]] == [owner.guid]
    process = _by_type(graph.entities, PROCESS_TYPE)[0]
    assert process.relationship_attributes is not None
    assert [end["guid"] for end in process.relationship_attributes["inputs"]] == [line.guid]
    assert [end["guid"] for end in process.relationship_attributes["outputs"]] == [orders.guid]


@pytest.mark.covers("aurelius_atlas_db_scanner.graph.entity_line", rules=["DBS-11"])
def test_the_dry_run_line_names_the_type_and_the_qualified_name() -> None:
    """DBS-11: one line per entity the run would write, type first."""
    graph = build_graph(system_name=SYSTEM, schema_name=DEFAULTS, schemas=[None], tables=[])
    assert entity_line(graph.entities[0]) == "m4i_system warehouse-db"
