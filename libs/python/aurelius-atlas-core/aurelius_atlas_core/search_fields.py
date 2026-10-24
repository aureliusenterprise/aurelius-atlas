"""The search fields of an entity: its searchable values, typed and keyed as Atlas keys vertex properties (DD-088).

An attribute's field is ``<kind>.<qualified name>``: the qualified name is Atlas's vertex property key
(``hive_table.name``, ``Referenceable.qualifiedName``, ``__guid``), the kind the Elasticsearch type its Atlas type
is mapped to. The system attributes of the entity root are taken from the entity's own fields.
"""

from collections.abc import Callable, Mapping
from datetime import datetime
from typing import Any

from aurelius_atlas_model import codec
from aurelius_atlas_model.typedef import (
    ATLAS_TYPE_BIGDECIMAL,
    ATLAS_TYPE_BIGINTEGER,
    ATLAS_TYPE_BOOLEAN,
    ATLAS_TYPE_BYTE,
    ATLAS_TYPE_DATE,
    ATLAS_TYPE_DOUBLE,
    ATLAS_TYPE_FLOAT,
    ATLAS_TYPE_INT,
    ATLAS_TYPE_LONG,
    ATLAS_TYPE_SHORT,
    ATLAS_TYPE_STRING,
)
from aurelius_atlas_typesystem.array_type import ArrayType
from aurelius_atlas_typesystem.atlas_type import AtlasType, resolved
from aurelius_atlas_typesystem.attribute import AtlasAttribute
from aurelius_atlas_typesystem.entity_type import ENTITY_ROOT, EntityType
from aurelius_atlas_typesystem.enum_type import EnumType

from aurelius_atlas_core.stored_entity import StoredEntity

KEYWORD, LONG, DOUBLE, BOOLEAN = "keyword", "long", "double", "boolean"
KINDS = (KEYWORD, LONG, DOUBLE, BOOLEAN)
"""The Elasticsearch types of search fields, each the first part of its fields' names."""

_KIND_OF: dict[str, str] = {
    ATLAS_TYPE_STRING: KEYWORD,
    ATLAS_TYPE_BYTE: LONG,
    ATLAS_TYPE_SHORT: LONG,
    ATLAS_TYPE_INT: LONG,
    ATLAS_TYPE_LONG: LONG,
    ATLAS_TYPE_DATE: LONG,
    ATLAS_TYPE_FLOAT: DOUBLE,
    ATLAS_TYPE_DOUBLE: DOUBLE,
    ATLAS_TYPE_BIGINTEGER: DOUBLE,
    ATLAS_TYPE_BIGDECIMAL: DOUBLE,
    ATLAS_TYPE_BOOLEAN: BOOLEAN,
}

LABEL_DELIMITER = "|"
"""``CLASSIFICATION_NAME_DELIMITER``: Atlas keeps labels as ``|a|b|``."""

INCOMPLETE_ENTITY_VALUE = 1
"""``INCOMPLETE_ENTITY_VALUE``: ``__isIncomplete`` of a shell entity; a complete one has none."""


def kind_of(attribute_type: AtlasType) -> str | None:
    """The kind of an attribute type's search field: primitives, enums and arrays of them; None for others."""
    if isinstance(attribute_type, ArrayType):
        element = resolved(attribute_type.element_type)
        return None if isinstance(element, ArrayType) else kind_of(element)
    if isinstance(attribute_type, EnumType):
        return KEYWORD
    return _KIND_OF.get(str(attribute_type.type_name))


def field_name(attribute: AtlasAttribute) -> str | None:
    """``<kind>.<qualified name>``: the search field of an attribute, or None when it has none (DD-088)."""
    kind = kind_of(attribute.attribute_type)
    return None if kind is None else f"{kind}.{attribute.qualified_name}"


def labels_value(labels: list[str] | None) -> str | None:
    """``getLabelString``: ``|a|b|``, or None for no labels."""
    return LABEL_DELIMITER + LABEL_DELIMITER.join(labels) + LABEL_DELIMITER if labels else None


_SYSTEM: dict[str, Callable[[StoredEntity], Any]] = {
    "__guid": lambda entity: entity.guid,
    "__typeName": lambda entity: entity.type_name,
    "__state": lambda entity: entity.state.value,
    "__createdBy": lambda entity: entity.created_by,
    "__modifiedBy": lambda entity: entity.updated_by,
    "__timestamp": lambda entity: entity.create_time,
    "__modificationTimestamp": lambda entity: entity.update_time,
    "__isIncomplete": lambda entity: INCOMPLETE_ENTITY_VALUE if entity.is_incomplete else None,
    "__labels": lambda entity: labels_value(entity.labels),
    "__customAttributes": lambda entity: (
        codec.dumps(entity.custom_attributes).decode() if entity.custom_attributes else None
    ),
    "__pendingTasks": lambda entity: entity.pending_tasks,
}
"""The system attributes an entity has a value of, read from its own fields."""


def search_fields(entity: StoredEntity, entity_type: EntityType) -> dict[str, Any]:
    """The entity's search fields: its attributes' values and its system attributes', those without one left out."""
    fields: dict[str, Any] = {}
    for name, read in _SYSTEM.items():
        _put(fields, ENTITY_ROOT.all_attributes[name], read(entity))
    for attribute in entity_type.all_attributes.values():
        _put(fields, attribute, entity.attributes.get(attribute.qualified_name))
    return fields


def _put(fields: dict[str, Any], attribute: AtlasAttribute, value: Any) -> None:  # noqa: ANN401 - Atlas values
    name = field_name(attribute)
    if name is None or value is None:
        return
    kind = name.partition(".")[0]
    if isinstance(value, list):
        values = [found for item in value if (found := search_value(kind, item)) is not None]
        if values:
            fields[name] = values
    elif not isinstance(value, Mapping):
        found = search_value(kind, value)
        if found is not None:
            fields[name] = found


def search_value(kind: str, value: Any) -> Any:  # noqa: ANN401 - Atlas values
    """A value as its kind's field holds it: dates as epoch milliseconds; None for one that is not of the kind."""
    try:
        if kind == KEYWORD:
            return value if isinstance(value, str) else codec.dumps(value).decode().strip('"')
        if kind == BOOLEAN:
            return value if isinstance(value, bool) else str(value).lower() == "true"
        if kind == LONG:
            if isinstance(value, datetime):
                return int(value.timestamp() * 1000)
            return int(value)
        return float(value)
    except TypeError, ValueError:
        return None
