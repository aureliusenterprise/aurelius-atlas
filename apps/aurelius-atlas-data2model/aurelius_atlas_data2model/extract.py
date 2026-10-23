"""The extraction engine: rows plus rules, in ar3 shape out (DTM-02..DTM-09; DD-109).

The legacy chain ran this on ``m4i-analytics`` DataFrames; the port is plain Python
over the parsed :class:`~aurelius_atlas_data2model.rules.ExtractionRequest` (DD-109).
Each function states the legacy behaviour it reproduces and cites the rule it keeps.
"""

from __future__ import annotations

import json
import math
from collections import defaultdict
from dataclasses import dataclass
from typing import Any

from aurelius_atlas_data2model.rules import ElementRule, ExtractionRequest, RelationRule, ViewRule
from aurelius_atlas_data2model.types import (
    ELEMENT_TYPE_LAYERS,
    LAYOUT_NAMES,
    NODE_HEIGHT,
    NODE_WIDTH,
    RELATIONSHIP_SHORTHANDS,
)

MODEL_NAME = "Generated model"
"""The model name the legacy extractor hard-codes (``ArchimateModel('Generated model')``)."""

SCRIPT_NAME = "Model Extractor API"
"""The ``created_by`` provenance the legacy extractor stamps on every metadata entry."""

ROW_SPACING = 95
"""Vertical distance between node tops in the native layout: node height 55 + a 40 gap (DV-15)."""

RANK_SPACING = 320
"""Horizontal distance between ranks in the native layout: node width 120 + a 200 gap (DV-15)."""

_INVERTED_TAGS = frozenset({"ar3_Access", "ar3_Specialization"})
"""The relationship tags whose direction the legacy layouts inverted (``_prepare_model``)."""


@dataclass(frozen=True)
class _Node:
    """A model node: an id, an Archimate element type tag, and a name (DTM-02)."""

    id: str
    type: str
    name: str


@dataclass(frozen=True)
class _Edge:
    """A model edge: an id, an ar3 relationship tag, its direction, and type attributes (DTM-04)."""

    id: str
    type: str
    attributes: dict[str, str]
    source: str
    target: str


def _is_null(value: object) -> bool:
    """Whether a row cell is the legacy's null: JSON null, or a float NaN.

    A strict JSON body cannot carry NaN, and FastAPI parses strictly (a ``NaN`` token
    is a 400), so ``None`` is the whole of it in practice; NaN covers a hand-built
    request in tests.
    """
    return value is None or (isinstance(value, float) and math.isnan(value))


def _legacy_str(value: object) -> str:
    """Stringify a cell the way the legacy's ``'%s' % value`` over pandas cells did.

    A pandas NaN renders as ``'nan'``; the JSON body carries nulls as ``None`` (DTM-02),
    which renders the same way here.
    """
    return "nan" if _is_null(value) else str(value)


def _columns(rows: list[dict[str, Any]]) -> set[str]:
    """The data's columns: the union of the rows' keys, as the legacy DataFrame built them."""
    return {key for row in rows for key in row}


def _dedupe_last(items: list[tuple[str, Any]]) -> list[Any]:
    """Keep the last item per key, at the kept item's position (DTM-05).

    The legacy model-level ``drop_duplicates(subset=['id'], keep='last')`` keeps the
    last occurrence, at the position of the *last* occurrence.
    """
    last_index: dict[str, int] = {}
    for index, (key, _) in enumerate(items):
        last_index[key] = index
    keep = set(last_index.values())
    return [item for index, (_, item) in enumerate(items) if index in keep]


def _parse_element_rows(rows: list[dict[str, Any]], rule: ElementRule) -> list[dict[str, Any]]:
    """The rows an element rule sees: its column present, the id non-null, first row per id (DTM-02).

    The legacy ``_parse_concept_definition`` drops a rule whose ``id_key`` is not a
    column, filters null ids (``data[data[key] == data[key]]``), and keeps the first
    row per id (``drop_duplicates`` default ``keep='first'``).
    """
    if rule.id_key not in _columns(rows):
        return []
    seen: set[str] = set()
    selected: list[dict[str, Any]] = []
    for row in rows:
        value = row.get(rule.id_key)
        if _is_null(value):
            continue
        key = _legacy_str(value)
        if key in seen:
            continue
        seen.add(key)
        selected.append(row)
    return selected


def _node(row: dict[str, Any], rule: ElementRule) -> _Node:
    """The node a row yields through an element rule (DTM-02)."""
    name = ""
    if rule.concept_name_key and rule.concept_name_key in row:
        value = row[rule.concept_name_key]
        name = rule.concept_name_prefix + ("" if _is_null(value) else str(value))
    return _Node(
        id=rule.id_prefix + _legacy_str(row.get(rule.id_key)),
        type=rule.concept_type,
        name=name,
    )


def _metadata(row: dict[str, Any], rule: ElementRule | RelationRule | ViewRule, id_value: object) -> dict[str, Any]:
    """The ``{id, data}`` metadata entry a row yields through a rule (DTM-03)."""
    data: dict[str, Any] = {
        "created_by": SCRIPT_NAME,
        "m4i_id_prefix": rule.id_prefix,
        "m4i_original_id": _legacy_str(id_value),
    }
    for entry in rule.mapping:
        value = row.get(entry.value) if isinstance(row, dict) else None
        if entry.value in row and not _is_null(value):
            data[entry.key] = value
    return {"id": rule.id_prefix + _legacy_str(id_value), "data": data}


def _relation_rows(
    rows: list[dict[str, Any]], rule: RelationRule, elements: dict[str, ElementRule]
) -> list[dict[str, Any]]:
    """The rows a relation rule sees: source and target non-null, first row per relation id (DTM-04).

    ``fmt_relation`` resolved the rule's ``source``/``target`` references into the
    referenced element rules' ``id_key``/``id_prefix``; the reference resolution
    happened at parse time (DTM-11), the endpoint keys here.
    """
    source_key = elements[rule.source].id_key
    target_key = elements[rule.target].id_key
    seen: set[str] = set()
    selected: list[dict[str, Any]] = []
    for row in rows:
        source, target = row.get(source_key), row.get(target_key)
        if _is_null(source) or _is_null(target):
            continue
        key = _legacy_str(row.get(rule.id_key))
        if key in seen:
            continue
        seen.add(key)
        selected.append(row)
    return selected


def _edge(row: dict[str, Any], rule: RelationRule, elements: dict[str, ElementRule]) -> _Edge:
    """The edge a row yields through a relation rule (DTM-04)."""
    tag, attributes = RELATIONSHIP_SHORTHANDS[rule.relationship_type]
    source_rule = elements[rule.source]
    target_rule = elements[rule.target]
    return _Edge(
        id=rule.id_prefix + _legacy_str(row.get(rule.id_key)),
        type=tag,
        attributes=dict(attributes),
        source=source_rule.id_prefix + _legacy_str(row.get(source_rule.id_key)),
        target=target_rule.id_prefix + _legacy_str(row.get(target_rule.id_key)),
    )


def _view_node_ids(rows: list[dict[str, Any]], rule: ViewRule, elements: dict[str, ElementRule]) -> list[str] | None:
    """The node ids a view rule collects (DTM-07): per ``view_nodes`` rule, first row per id.

    The legacy scans each node rule's column (non-null, first per value) in rule
    order; an empty collection is the legacy's ``None`` — the whole model. Preset
    node coordinates (``x``/``x_key`` in a view node rule) are ignored: the layout
    is native (DV-15).
    """
    ids: list[str] = []
    for node_rule in rule.view_nodes:
        element = elements[node_rule.rule]
        if element.id_key not in _columns(rows):
            continue
        seen: set[str] = set()
        for row in rows:
            value = row.get(element.id_key)
            if _is_null(value):
                continue
            key = element.id_prefix + _legacy_str(value)
            if key in seen:
                continue
            seen.add(key)
            ids.append(key)
    return ids or None


def _view_edge_ids(
    rows: list[dict[str, Any]], rule: ViewRule, relations: dict[str, RelationRule], edge_ids: set[str]
) -> list[str] | None:
    """The edge ids a view rule selects (DTM-07): each edge rule's column, model edges only.

    An empty selection is the legacy's ``None`` — every model edge between the view
    nodes.
    """
    ids: list[str] = []
    for edge_rule in rule.view_edges:
        relation = relations[edge_rule.rule]
        if relation.id_key not in _columns(rows):
            continue
        for row in rows:
            value = row.get(relation.id_key)
            if _is_null(value):
                continue
            key = relation.id_prefix + _legacy_str(value)
            if key in edge_ids and key not in ids:
                ids.append(key)
    return ids or None


def _ranks(node_ids: list[str], edges: list[_Edge]) -> dict[str, int]:
    """Each node's rank: the longest path from an edge source, cycles bounded (DV-15).

    The legacy graphviz layout ranked with dot; the inversion the legacy layouts
    applied (``_prepare_model``) applies to the ranking edges here: writes and
    specializations rank against their direction.
    """

    def ranking_edges() -> list[tuple[str, str]]:
        pairs = []
        for edge in edges:
            inverted = edge.type in _INVERTED_TAGS and (
                edge.type == "ar3_Specialization" or edge.attributes.get("accessType") == "Write"
            )
            pairs.append((edge.target, edge.source) if inverted else (edge.source, edge.target))
        return [(source, target) for source, target in pairs if source in set(node_ids) and target in set(node_ids)]

    rank = dict.fromkeys(node_ids, 0)
    incoming: dict[str, list[str]] = defaultdict(list)
    for source, target in ranking_edges():
        incoming[target].append(source)
    for _ in range(len(node_ids) + 1):
        changed = False
        for node, sources in incoming.items():
            if sources and (candidate := max(rank[source] for source in sources) + 1) > rank[node]:
                rank[node] = candidate
                changed = True
        if not changed:
            break
    return rank


def _coordinates(node_ids: list[str], edges: list[_Edge], layout: str) -> dict[str, tuple[int, int]]:
    """The native deterministic layout (DTM-08, DV-15).

    ``archimate_process`` ranks left to right (graphviz ``rankdir=LR``);
    ``archimate_hierarchical`` ranks bottom to top (``rankdir=BT``). Nodes stack by
    :data:`ROW_SPACING` within a rank, centred; ranks sit :data:`RANK_SPACING` apart.
    """
    ranks = _ranks(node_ids, edges)
    by_rank: dict[int, list[str]] = defaultdict(list)
    for node_id in node_ids:
        by_rank[ranks[node_id]].append(node_id)
    coordinates: dict[str, tuple[int, int]] = {}
    for rank, members in by_rank.items():
        centre = (len(members) - 1) / 2
        for index, node_id in enumerate(members):
            stack = (index - centre) * ROW_SPACING
            if layout == "archimate_process":
                coordinates[node_id] = (round(rank * RANK_SPACING), round(stack))
            else:
                coordinates[node_id] = (round(stack), round(-rank * RANK_SPACING))
    return coordinates


def _view_diagram(
    view_id: str,
    name: str,
    nodes: list[_Node],
    edges: list[_Edge],
    layout: str,
) -> dict[str, Any]:
    """The ar3 view: nodes placed by the layout, connections over them (DTM-07..DTM-09).

    ``generate_view`` numbered the placements and connections with a running index,
    ``'{view}-{ref}--{i}'``; the model's ids are the ``@elementRef``/``@relationshipRef``.
    """
    node_ids = [node.id for node in nodes]
    coordinates = _coordinates(node_ids, edges, layout)
    ar3_nodes = []
    for index, node in enumerate(nodes):
        x, y = coordinates[node.id]
        junction = node.type in {"ar3_Junction", "ar3_AndJunction", "ar3_OrJunction"}
        ar3_nodes.append(
            {
                "@identifier": f"{view_id}-{node.id}--{index}",
                "@x": x,
                "@y": y,
                "@w": 14 if junction else NODE_WIDTH,
                "@h": 14 if junction else NODE_HEIGHT,
                "@elementRef": node.id,
                "@xsi_type": "ar3_Element",
            }
        )
    placement = {node["@elementRef"]: node["@identifier"] for node in ar3_nodes}
    ar3_connections = []
    for index, edge in enumerate(edges):
        ar3_connections.append(
            {
                "@identifier": f"{view_id}-{edge.id}--{index}",
                "@source": placement[edge.source],
                "@target": placement[edge.target],
                "@relationshipRef": edge.id,
                "@xsi_type": "ar3_Relationship",
            }
        )
    return {
        "@identifier": view_id,
        "@xsi_type": "ar3_Diagram",
        "ar3_node": ar3_nodes,
        "ar3_connection": ar3_connections,
        "ar3_name": [{"@xml_lang": "en", "value": str(name)}],
    }


def _name_of(rule: ViewRule, row: dict[str, Any] | None) -> str:
    """The view name: static from the rule, dynamic from the group's first row (DTM-06)."""
    if rule.view_name_type == "static":
        return rule.view_name_value
    if row is not None and rule.view_name_key in row and not _is_null(row[rule.view_name_key]):
        return rule.view_name_prefix + str(row[rule.view_name_key])
    return rule.view_name_prefix + "nan"


def extract(request: ExtractionRequest) -> dict[str, Any]:
    """Run the extraction: the legacy ``extract`` endpoint's body, pandas-free (DTM-01).

    :param request: the parsed ``POST /extract`` body
    :returns: ``{"metadata": [...], "model": "<ar3 JSON string>"}`` — the model is a
        JSON string inside the JSON body, as the legacy answer is
    """
    rows = request.data
    elements = {rule.id: rule for rule in request.rules.elements}
    relations = {rule.id: rule for rule in request.rules.relations}

    # Nodes and their metadata, per rule (DTM-02, DTM-03), model-deduplicated by id (DTM-05).
    node_rows = [(rule, row) for rule in request.rules.elements for row in _parse_element_rows(rows, rule)]
    nodes = _dedupe_last([(_node(row, rule).id, _node(row, rule)) for rule, row in node_rows])
    node_ids = {node.id for node in nodes}
    metadata: list[dict[str, Any]] = [_metadata(row, rule, row.get(rule.id_key)) for rule, row in node_rows]

    # Edges, filtered to the model nodes — their metadata kept either way (DTM-04, DTM-03).
    edges: list[_Edge] = []
    for rule in request.rules.relations:
        for row in _relation_rows(rows, rule, elements):
            edge = _edge(row, rule, elements)
            metadata.append(_metadata(row, rule, row.get(rule.id_key)))
            if edge.source in node_ids and edge.target in node_ids:
                edges.append(edge)
    edges = _dedupe_last([(edge.id, edge) for edge in edges])

    # Views, only for known layouts (DTM-06); each appends its metadata (DTM-03).
    diagrams: list[dict[str, Any]] = []
    organizations: list[dict[str, Any]] = [
        {"idRef": node.id, "level1": ELEMENT_TYPE_LAYERS[node.type].capitalize(), "level2": None} for node in nodes
    ] + [{"idRef": edge.id, "level1": "Relations", "level2": None} for edge in edges]
    edge_ids = {edge.id for edge in edges}
    for rule in request.rules.views:
        if rule.view_layout not in LAYOUT_NAMES:
            continue
        for view_id, group, first_row in _view_groups(rows, rule):
            metadata.append(_view_metadata(rule, view_id, first_row))
            selected_nodes = _view_select(nodes, _view_node_ids(group, rule, elements))
            selected_edges = _view_select_edges(edges, _view_edge_ids(group, rule, relations, edge_ids), selected_nodes)
            name = _name_of(rule, first_row)
            diagram = _view_diagram(view_id, name, selected_nodes, selected_edges, rule.view_layout)
            diagrams.append(diagram)
            path = ["Views", *rule.view_path]
            organization: dict[str, Any] = {"idRef": view_id}
            for depth, folder in enumerate(path):
                organization[f"level{depth + 1}"] = folder
            organization[f"level{len(path) + 1}"] = None
            organizations.append(organization)

    model = _ar3_model(nodes, edges, diagrams, organizations)
    return {"metadata": metadata, "model": json.dumps(model)}


def _view_groups(
    rows: list[dict[str, Any]], rule: ViewRule
) -> list[tuple[str, list[dict[str, Any]], dict[str, Any] | None]]:
    """The groups a view rule produces (DTM-06, DTM-07).

    A static view is one group of all rows; a dynamic view groups by ``id_key``,
    each group scanned on its own rows.

    Null group keys are skipped: the legacy ``data[data[key] == key]`` mask drops
    them from every group, so their own group held no rows and was skipped.
    """
    if rule.id_type == "static":
        return [(rule.id_value, rows, rows[0] if rows else None)]
    groups: list[tuple[str, list[dict[str, Any]], dict[str, Any] | None]] = []
    seen: set[str] = set()
    for row in rows:
        value = row.get(rule.id_key)
        if _is_null(value):
            continue
        key = rule.id_prefix + _legacy_str(value)
        if key in seen:
            continue
        seen.add(key)
        group = [candidate for candidate in rows if rule.id_prefix + _legacy_str(candidate.get(rule.id_key)) == key]
        groups.append((key, group, group[0]))
    return groups


def _view_metadata(rule: ViewRule, view_id: str, first_row: dict[str, Any] | None) -> dict[str, Any]:
    """The view's metadata entry (DTM-03): ``m4i_id_type``, and ``m4i_path`` when the rule has a path."""
    original_id = rule.id_value if rule.id_type == "static" else _legacy_str((first_row or {}).get(rule.id_key))
    data: dict[str, Any] = {
        "created_by": SCRIPT_NAME,
        "m4i_id_type": rule.id_type,
        "m4i_id_prefix": "" if rule.id_type == "static" else rule.id_prefix,
        "m4i_original_id": _legacy_str(original_id),
    }
    if rule.view_path:
        data["m4i_path"] = "/".join(["Views", *rule.view_path])
    return {"id": view_id, "data": data}


def _view_select(nodes: list[_Node], selected: list[str] | None) -> list[_Node]:
    """The model nodes a view holds (DTM-07): the selection, in model order; ``None`` is all."""
    if selected is None:
        return nodes
    wanted = set(selected)
    return [node for node in nodes if node.id in wanted]


def _view_select_edges(edges: list[_Edge], selected: list[str] | None, nodes: list[_Node]) -> list[_Edge]:
    """The model edges a view holds (DTM-07): between its nodes, then the selection; ``None`` is all."""
    node_ids = {node.id for node in nodes}
    inside = [edge for edge in edges if edge.source in node_ids and edge.target in node_ids]
    if selected is None:
        return inside
    wanted = set(selected)
    return [edge for edge in inside if edge.id in wanted]


def _ar3_element(node: _Node) -> dict[str, Any]:
    """One ``ar3_element`` (``to_JSON.format_element``)."""
    return {
        "@identifier": node.id,
        "@xsi_type": node.type,
        "ar3_name": [{"@xml_lang": "en", "value": str(node.name)}],
    }


def _ar3_relationship(edge: _Edge) -> dict[str, Any]:
    """One ``ar3_relationship`` (``to_JSON.format_relationship``), type attributes included."""
    result: dict[str, Any] = {
        "@identifier": edge.id,
        "@target": edge.target,
        "@source": edge.source,
        "@xsi_type": edge.type,
        "ar3_name": [{"@xml_lang": "en", "value": ""}],
    }
    result |= {f"@{key}": value for key, value in edge.attributes.items()}
    return result


def _ar3_organizations(organizations: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """The ``ar3_organizations`` folder tree (``to_JSON.format_organizations``).

    The levels are the union of the organization rows' ``levelN`` columns — the
    legacy DataFrame's columns — sorted; a row without a level reads as the legacy's
    NaN: falsy, which ends its descent at that depth.
    """
    root: dict[str, Any] = {"ar3_item": []}
    levels = sorted({key for organization in organizations for key in organization if key.startswith("level")})

    def folder_at(parent: dict[str, Any], label: str) -> dict[str, Any]:
        for item in parent["ar3_item"]:
            if item.get("ar3_label") == [{"@xml_lang": "en", "value": str(label)}]:
                return item
        item: dict[str, Any] = {"ar3_label": [{"@xml_lang": "en", "value": str(label)}], "ar3_item": []}
        parent["ar3_item"].append(item)
        return item

    for organization in organizations:
        parent = root
        for depth, level in enumerate(levels):
            name = organization.get(level)
            if not name or depth == len(levels) - 1:
                break
            parent = folder_at(parent, str(name))
        parent["ar3_item"].append({"@identifierRef": organization["idRef"]})
    return [root]


def _ar3_model(
    nodes: list[_Node], edges: list[_Edge], diagrams: list[dict[str, Any]], organizations: list[dict[str, Any]]
) -> dict[str, Any]:
    """The ``ar3_model`` document (``to_JSON``), the shape the webapp's parser reads (DTM-09)."""
    return {
        "ar3_model": {
            "@identifier": MODEL_NAME,
            "ar3_name": [{"@xml_lang": "en", "value": MODEL_NAME}],
            "ar3_elements": {"ar3_element": [_ar3_element(node) for node in nodes]},
            "ar3_relationships": {"ar3_relationship": [_ar3_relationship(edge) for edge in edges]},
            "ar3_views": {"ar3_diagrams": {"ar3_view": diagrams}},
            "ar3_organizations": _ar3_organizations(organizations),
        }
    }
