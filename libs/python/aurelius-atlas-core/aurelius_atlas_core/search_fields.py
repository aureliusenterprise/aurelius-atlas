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
from aurelius_atlas_typesystem.classification_type import CLASSIFICATION_ROOT, ClassificationType
from aurelius_atlas_typesystem.entity_type import ENTITY_ROOT, EntityType
from aurelius_atlas_typesystem.enum_type import EnumType

from aurelius_atlas_core.stored_classification import StoredClassification
from aurelius_atlas_core.stored_entity import StoredEntity

KEYWORD, LONG, DOUBLE, BOOLEAN = "keyword", "long", "double", "boolean"
TEXT = "text"
"""The analysed sub-field of a keyword search field, which free text searches (DD-092)."""
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

TRAIT_NAMES = f"{KEYWORD}.__traitNames"
PROPAGATED_TRAIT_NAMES = f"{KEYWORD}.__propagatedTraitNames"
"""``__traitNames`` and ``__propagatedTraitNames``: the type names of an entity's attached and propagated
classifications, as Atlas keeps them on the vertex (DD-090)."""
CLASSIFICATION_GUIDS = f"{KEYWORD}.__classificationGuids"
"""The classification instances an entity lists, for tag filters (DD-090); no attribute names it."""


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


def search_fields(
    entity: StoredEntity,
    entity_type: EntityType,
    classifications: Mapping[str, StoredClassification] | None = None,
) -> dict[str, Any]:
    """The entity's search fields: its attributes' values, its system attributes' and its classifications' names,
    those without one left out; ``classifications`` holds the instances it lists (CSR-05, DD-090).
    """  # noqa: D205 - one sentence
    fields: dict[str, Any] = {}
    for name, read in _SYSTEM.items():
        _put(fields, ENTITY_ROOT.all_attributes[name], read(entity))
    for attribute in entity_type.all_attributes.values():
        _put(fields, attribute, entity.attributes.get(attribute.qualified_name))
    listed = [found for guid in entity.classification_guids or [] if (found := (classifications or {}).get(guid))]
    attached = [found.type_name for found in listed if found.entity_guid == entity.guid]
    propagated = [found.type_name for found in listed if found.entity_guid != entity.guid]
    _put(fields, ENTITY_ROOT.all_attributes["__classificationNames"], labels_value(attached))
    _put(fields, ENTITY_ROOT.all_attributes["__classificationsText"], classifications_text(listed))
    _put(fields, ENTITY_ROOT.all_attributes["__propagatedClassificationNames"], labels_value(propagated))
    for name, values in (
        (TRAIT_NAMES, attached),
        (PROPAGATED_TRAIT_NAMES, propagated),
        (CLASSIFICATION_GUIDS, entity.classification_guids),
    ):
        if values:
            fields[name] = list(values)
    return fields


def classifications_text(instances: list[StoredClassification]) -> str | None:
    """``getClassificationTextForEntity``: each classification's type name and attribute values (FTX-03)."""
    words: list[str] = []
    for instance in instances:
        words.append(instance.type_name)
        for value in instance.attributes.values():
            items = value if isinstance(value, list) else [value]
            words.extend(
                search_value(KEYWORD, item) for item in items if item is not None and not isinstance(item, Mapping)
            )
    return " ".join(words) if words else None


def classification_fields(instance: StoredClassification, classification_type: ClassificationType) -> dict[str, Any]:
    """The search fields of a classification instance, as tag filters test them: its attributes' values, its type
    name and its entity's status (CSR-03, DD-090).
    """  # noqa: D205 - one sentence
    fields: dict[str, Any] = {}
    _put(fields, CLASSIFICATION_ROOT.all_attributes["__typeName"], instance.type_name)
    status = instance.entity_status
    _put(fields, CLASSIFICATION_ROOT.all_attributes["__entityStatus"], None if status is None else status.value)
    for name, attribute in classification_type.all_attributes.items():
        _put(fields, attribute, instance.attributes.get(str(name)))
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
