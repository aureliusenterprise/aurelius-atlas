"""``SelectClauseProjections``: a ``select``'s rows over the entities found (DSP-01 to DSP-03, DSP-05).

Each entity gives a row: its primitive attributes' values, the header of the entity for an item that refers to
entities, and the aggregates of all the entities given; a row equal to an earlier one is left out, as Atlas's
``HashSet`` leaves it out, the others kept in the order of the entities (DV-97).
"""

from collections.abc import Sequence
from decimal import Decimal
from typing import Any

from aurelius_atlas_dsl.atlas_dsl import QueryMetadata
from aurelius_atlas_model import codec
from aurelius_atlas_model.base import AtlasModel
from aurelius_atlas_typesystem.attribute import AtlasAttribute

from aurelius_atlas_core.entity_retriever import EntityRetriever
from aurelius_atlas_core.search_fields import vertex_property
from aurelius_atlas_core.select_clause_composer import Aggregator, SelectClauseComposer
from aurelius_atlas_core.stored_entity import StoredEntity


async def projection_rows(
    found: Sequence[StoredEntity], select: SelectClauseComposer, retriever: EntityRetriever
) -> list[list[Any]]:
    """``getProjectionRows``: the distinct rows of the entities, in their order (DSP-01 to DSP-03).

    Args:
        found: The entities the rows are of; aggregates are over all of them.
        select: The items.
        retriever: Reads the header of an entity an item refers to.

    Returns:
        A row per entity, those equal to an earlier one left out.
    """
    aggregates = {
        index: _aggregate(aggregator, found, select.attributes[index])
        for index, aggregator in enumerate(select.aggregators)
        if aggregator is not Aggregator.NONE
    }
    rows: list[list[Any]] = []
    seen: set[bytes] = set()
    for stored in found:
        row: list[Any] = []
        for index in range(len(select.labels)):
            if index in aggregates:
                row.append(aggregates[index])
            elif index in select.primitive:
                row.append(vertex_property(stored, select.attributes[index]))
            else:
                header = await retriever.header_with_attributes(stored, [])
                header.classifications = await retriever.classifications(stored.guid)
                row.append(header)
        key = codec.dumps([item.to_json() if isinstance(item, AtlasModel) else item for item in row])
        if key not in seen:
            seen.add(key)
            rows.append(row)
    return rows


def get_sublist_for_group_by(rows: list[list[Any]], metadata: QueryMetadata) -> list[list[Any]]:
    """``getSublistForGroupBy``: the rows from ``offset - 1`` (0 at least), ``limit`` of them (DSP-05)."""
    start = max(metadata.resolved_offset - 1, 0)
    end = start + metadata.resolved_limit
    if start >= len(rows):
        start = end = 0
    return rows[start : min(end, len(rows))]


def _aggregate(aggregator: Aggregator, found: Sequence[StoredEntity], attribute: AtlasAttribute | None) -> Any:  # noqa: ANN401 - a value
    """``count``, ``computeSum``, ``computeMax`` and ``computeMin`` over every entity (DSP-03)."""
    if aggregator is Aggregator.COUNT:
        return len(found)
    values = [vertex_property(stored, attribute, None) for stored in found]
    if aggregator is Aggregator.SUM:
        return float(sum(float(value) for value in values if _is_number(value)))
    chosen = values[0]
    for value in values[1:]:
        order = _compare(value, chosen)
        if (aggregator is Aggregator.MAX and order > 0) or (aggregator is Aggregator.MIN and order < 0):
            chosen = value
    return chosen


def _compare(left: object, right: object) -> int:
    """``VertexPropertyComparator``: no value least; values of one kind by their order; of two kinds equal."""
    if left is None or right is None:
        return 0 if left is right else -1 if left is None else 1
    if isinstance(left, str) and isinstance(right, str):
        return (left > right) - (left < right)
    if _is_number(left) and _is_number(right) and _kind(left) == _kind(right):
        return (left > right) - (left < right)  # type: ignore[operator]
    return 0


def _is_number(value: object) -> bool:
    return isinstance(value, (int, float, Decimal)) and not isinstance(value, bool)


def _kind(value: object) -> type:
    """Java's boxed class of a number: integers apart from decimals."""
    return int if isinstance(value, int) else float
