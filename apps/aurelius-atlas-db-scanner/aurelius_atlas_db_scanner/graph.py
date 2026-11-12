"""The tree: table list to catalogue entities, the qualified names, the FKs (13.3, DBS-03, DBS-08, DBS-09).

The tree hangs the way the spec says (DBS-03, DD-504): the configured System, one Collection
per scanned schema, one Dataset per table under its schema's Collection, and one Field per
column. The qualified names follow the legacy rule exactly — the component lowercased, ``&``
and ``-`` removed, whitespace runs replaced by ``-``, the parts joined by ``--`` — as the
Kafka scanner applies it (KSC-03), so a table registered by one scanner lines up with the
same name everywhere.

Each foreign-key column pair becomes one ``m4i_generic_process`` (DBS-08, DD-505): the
referring dataset on ``inputs``, the referred dataset on ``outputs``, qualified one level
below the table. Every entity carries a request-local temporary guid and the ends ride
``relationshipAttributes`` through those guids (KSC-07, DD-466); the store resolves ends by
guid or unique qualified name (EWR-11), so a re-scan updates in place and an unchanged tree
is skipped whole (DBS-09, EWR-08).
"""

import re
from collections.abc import Sequence
from dataclasses import dataclass, field

from aurelius_atlas_model.instance import AtlasEntity, next_internal_id

from aurelius_atlas_db_scanner.reflect import TableInfo

SYSTEM_TYPE = "m4i_system"
COLLECTION_TYPE = "m4i_collection"
DATASET_TYPE = "m4i_dataset"
FIELD_TYPE = "m4i_field"
PROCESS_TYPE = "m4i_generic_process"
"""The m4i types of the tree (1.5b's model, loaded by DD-362)."""

DELIMITER = "--"
"""The legacy qualified-name delimiter, joining the sanitized components (KSC-03)."""

ILLEGAL_CHARACTERS = re.compile("[&-]+")
"""The characters the legacy rule removes from a component: the two it lists, ``&`` and ``-``."""

WHITE_SPACE = re.compile(r"\s+")
"""Whitespace runs the legacy rule replaces with a single ``-`` (KSC-03)."""


def qualified_component(name: str) -> str:
    """One qualified-name component, by the legacy rule (KSC-03).

    Lowercase first, then ``&`` and ``-`` are removed, then whitespace becomes ``-`` — that
    order, because a hyphen the whitespace rule introduces must survive the removal.
    """
    without_illegal = ILLEGAL_CHARACTERS.sub("", name.lower())
    return WHITE_SPACE.sub("-", without_illegal)


def join_qualified(*components: str) -> str:
    """The components joined by ``--``, empty ones dropped — the legacy concatenation (KSC-03).

    Each component arrives already sanitized, or already a qualified name of deeper parts; it is
    never sanitized a second time, because the second pass would eat the delimiter's own hyphens.
    """
    return DELIMITER.join(component for component in components if component)


def collection_name(schema: str | None, default_name: str) -> str:
    """The Collection's name for one schema (DBS-03): its own, or the default for the nameless."""
    return schema if schema is not None else default_name


def collection_qualified_name(system_qualified_name: str, name: str) -> str:
    """The qualified name of one schema's Collection (DBS-03): ``<system>--<schema>``."""
    return join_qualified(system_qualified_name, qualified_component(name))


def dataset_qualified_name(system_qualified_name: str, default_name: str, schema: str | None, table: str) -> str:
    """The qualified name of one table's Dataset (DBS-03): ``<system>--<schema>--<table>``."""
    collection = collection_qualified_name(system_qualified_name, collection_name(schema, default_name))
    return join_qualified(collection, qualified_component(table))


def table_display_name(schema: str | None, table: str) -> str:
    """``<schema>.<table>``, the nameless schema omitted: a table as a notice names it."""
    return ".".join(part for part in (schema, table) if part)


def process_display_name(schema: str | None, table: str, column: str) -> str:
    """The Process' display name (DBS-08): ``<schema>.<table>.<column>``, the nameless omitted."""
    return ".".join(part for part in (schema, table, column) if part)


def process_qualified_name(
    system_qualified_name: str,
    default_name: str,
    schema: str | None,
    table: str,
    column: str,
) -> str:
    """The Process' qualified name (DBS-08): ``<system>--<schema>--<table>--<column>``.

    One level below the table (DD-505): the column rides as the last component, and the
    nameless default schema drops out of the join like any empty component (KSC-03).
    """
    table_qualified = dataset_qualified_name(system_qualified_name, default_name, schema, table)
    return join_qualified(table_qualified, qualified_component(column))


@dataclass
class Graph:
    """What the builder made: the entities for one bulk request, and the drops (DBS-08, DBS-09)."""

    entities: list[AtlasEntity] = field(default_factory=list)
    """System, Collections, Datasets, Fields, Processes — the whole tree, one bulk request."""

    notices: list[str] = field(default_factory=list)
    """Every dropped edge, in scan order: an end must name two registered datasets (DBS-08)."""


def build_graph(
    *,
    system_name: str,
    schema_name: str,
    schemas: Sequence[str | None],
    tables: Sequence[TableInfo],
) -> Graph:
    """The whole scan's entities, in one list for one bulk request (DBS-03, DBS-08, DBS-09).

    The System holds every scanned schema's Collection — a schema whose tables the patterns
    filtered out keeps an empty Collection, because the scan read it (DBS-03) — and each
    Collection holds its tables as Datasets; each Dataset holds its columns as Fields. Each
    foreign-key column pair becomes a Process between two datasets (DBS-08); an edge whose
    referred table sits outside the admitted set, or whose referred column resolved to
    nothing, is dropped with a notice naming both sides.

    Args:
        system_name: The System entity's name (DBS-03's ``SYSTEM_NAME``).
        schema_name: The Collection name for the nameless default schema (DBS-03).
        schemas: Every schema the scan admitted, in scan order — including any that yielded no
            table — so each gets its Collection.
        tables: One :class:`~aurelius-atlas-db-scanner.reflect.TableInfo` per reflected table,
            in scan order. A field-less table still becomes a dataset (DBS-05, DBS-07).

    Returns:
        The :class:`Graph`: entities in write order (system, collections, datasets, fields,
        processes), and the notices for every dropped edge.
    """
    notices: list[str] = []
    system_guid = next_internal_id()
    system_qualified = qualified_component(system_name)

    collection_guids: dict[str | None, str] = {}
    collection_qualified: dict[str | None, str] = {}
    collections: list[AtlasEntity] = []
    for schema in schemas:
        name = collection_name(schema, schema_name)
        guid = next_internal_id()
        collection_guids[schema] = guid
        collection_qualified[schema] = collection_qualified_name(system_qualified, name)
        collections.append(
            AtlasEntity(
                guid=guid,
                type_name=COLLECTION_TYPE,
                attributes={"name": name, "qualifiedName": collection_qualified[schema]},
                relationship_attributes={
                    "systems": [{"guid": system_guid, "typeName": SYSTEM_TYPE}],
                },
            )
        )

    dataset_guids: dict[tuple[str | None, str], str] = {}
    for table in tables:
        dataset_guids[(table.schema, table.name)] = next_internal_id()

    datasets: list[AtlasEntity] = []
    fields: list[AtlasEntity] = []
    for table in tables:
        guid = dataset_guids[(table.schema, table.name)]
        qualified = dataset_qualified_name(system_qualified, schema_name, table.schema, table.name)
        field_refs: list[dict[str, str]] = []
        for column in table.columns:
            field_guid = next_internal_id()
            field_refs.append({"guid": field_guid, "typeName": FIELD_TYPE})
            attributes: dict[str, str] = {
                "name": column.name,
                "qualifiedName": join_qualified(qualified, qualified_component(column.name)),
                "fieldType": column.field_type,
            }
            if column.definition is not None:
                attributes["definition"] = column.definition
            fields.append(
                AtlasEntity(
                    guid=field_guid,
                    type_name=FIELD_TYPE,
                    attributes=attributes,
                    relationship_attributes={"datasets": [{"guid": guid, "typeName": DATASET_TYPE}]},
                )
            )
        attributes = {"name": table.name, "qualifiedName": qualified}
        if table.definition is not None:
            attributes["definition"] = table.definition
        datasets.append(
            AtlasEntity(
                guid=guid,
                type_name=DATASET_TYPE,
                attributes=attributes,
                relationship_attributes={
                    "collections": [{"guid": collection_guids[table.schema], "typeName": COLLECTION_TYPE}],
                    "fields": field_refs,
                },
            )
        )

    processes = _build_processes(system_qualified, schema_name, tables, dataset_guids, notices)

    system = AtlasEntity(
        guid=system_guid,
        type_name=SYSTEM_TYPE,
        attributes={"name": system_name, "qualifiedName": system_qualified},
        relationship_attributes={
            "collections": [{"guid": guid, "typeName": COLLECTION_TYPE} for guid in collection_guids.values()],
        },
    )
    return Graph([system, *collections, *datasets, *fields, *processes], notices)


def _build_processes(
    system_qualified: str,
    schema_name: str,
    tables: Sequence[TableInfo],
    dataset_guids: dict[tuple[str | None, str], str],
    notices: list[str],
) -> list[AtlasEntity]:
    """The foreign-key column pairs, one Process each (DBS-08, DD-505).

    A key whose referred table is outside the admitted set — a filtered schema or table — and
    a pair whose referred column resolved to nothing are dropped with a notice, because a
    process end must name two registered datasets (EWR-11 has nothing to resolve to). A
    self-referencing key names the same dataset on both ends — a valid graph, an honest fact.
    """
    processes: list[AtlasEntity] = []
    for table in tables:
        for key in table.foreign_keys:
            referred_guid = dataset_guids.get((key.referred_schema, key.referred_table))
            if referred_guid is None:
                notices.append(
                    f"{table_display_name(table.schema, table.name)}"
                    f" ({', '.join(key.constrained_columns)}): the referred table"
                    f" {table_display_name(key.referred_schema, key.referred_table)}"
                    " is not in the scan — the foreign key is not registered"
                )
                continue
            if len(key.referred_columns) != len(key.constrained_columns):
                notices.append(
                    f"{process_display_name(table.schema, table.name, ', '.join(key.constrained_columns))}:"
                    " its foreign key names a different number of referred columns — not registered"
                )
                continue
            referring_guid = dataset_guids[(table.schema, table.name)]
            for column, referred_column in zip(key.constrained_columns, key.referred_columns, strict=True):
                if referred_column is None:
                    notices.append(
                        f"{process_display_name(table.schema, table.name, column)}: its foreign key names no"
                        " referred column and the referred table answers no primary key there — not registered"
                    )
                    continue
                processes.append(
                    AtlasEntity(
                        guid=next_internal_id(),
                        type_name=PROCESS_TYPE,
                        attributes={
                            "name": process_display_name(table.schema, table.name, column),
                            "qualifiedName": process_qualified_name(
                                system_qualified, schema_name, table.schema, table.name, column
                            ),
                        },
                        relationship_attributes={
                            "inputs": [{"guid": referring_guid, "typeName": DATASET_TYPE}],
                            "outputs": [{"guid": referred_guid, "typeName": DATASET_TYPE}],
                        },
                    )
                )
    return processes


def entity_line(entity: AtlasEntity) -> str:
    """The dry-run's one line per entity (DBS-11): its type and its qualified name."""
    attributes = entity.attributes or {}
    return f"{entity.type_name} {attributes.get('qualifiedName', '?')}"
