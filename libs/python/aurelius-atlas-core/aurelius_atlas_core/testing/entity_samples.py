"""Types and stored entities to read back in tests of the entity reads (DD-049, DD-051).

``table`` has an attribute of every kind the reads map: dates, enums, structs, arrays and maps, plain, owned and
soft references, and a relationship attribute (``home``).
"""

from typing import Any

from aurelius_atlas_model.instance import AtlasEntity
from aurelius_atlas_model.typedef import AtlasTypesDef
from aurelius_atlas_typesystem.registry import TypeRegistry

from aurelius_atlas_core.stored_entity import StoredEntity

OWNED = [{"type": "ownedRef"}]
SOFT = {"isSoftReference": "true"}


def _attribute(name: str, type_name: str, **more: Any) -> dict[str, Any]:  # noqa: ANN401 - typedef JSON
    return {"name": name, "typeName": type_name, "isOptional": True, "cardinality": "SINGLE", **more}


SAMPLE_TYPES: dict[str, Any] = {
    "enumDefs": [
        {"name": "s_color", "elementDefs": [{"value": "RED", "ordinal": 0}, {"value": "BLUE", "ordinal": 1}]},
    ],
    "structDefs": [
        {
            "name": "s_place",
            "attributeDefs": [_attribute("x", "int"), _attribute("label", "string"), _attribute("at", "s_column")],
        },
    ],
    "entityDefs": [
        {
            "name": "s_ref",
            "attributeDefs": [
                _attribute("qualifiedName", "string", isUnique=True, isIndexable=True),
                _attribute("name", "string"),
            ],
        },
        {
            "name": "s_database",
            "superTypes": ["s_ref"],
            "options": {"displayTextAttribute": "title"},
            "attributeDefs": [_attribute("title", "string")],
        },
        {
            "name": "s_column",
            "superTypes": ["s_ref"],
            "options": {"schemaAttributes": '["position"]'},
            "attributeDefs": [_attribute("position", "int"), _attribute("comment", "string")],
        },
        {
            "name": "s_table",
            "superTypes": ["s_ref"],
            "attributeDefs": [
                _attribute("created", "date"),
                _attribute("color", "s_color"),
                _attribute("place", "s_place"),
                _attribute("places", "array<s_place>", cardinality="LIST"),
                _attribute("sizes", "array<int>", cardinality="LIST"),
                _attribute("props", "map<string,string>"),
                _attribute("db", "s_database"),
                _attribute("columns", "array<s_column>", cardinality="LIST", constraints=OWNED),
                _attribute("byName", "map<string,s_column>", constraints=OWNED),
                _attribute("primary", "s_column", options=SOFT),
                _attribute("spare", "array<s_column>", cardinality="LIST", options=SOFT, constraints=OWNED),
            ],
        },
    ],
    "relationshipDefs": [
        {
            "name": "s_table_home",
            "relationshipCategory": "ASSOCIATION",
            "endDef1": {"type": "s_table", "name": "home", "cardinality": "SINGLE"},
            "endDef2": {"type": "s_database", "name": "tables", "cardinality": "SET"},
        },
    ],
}
"""The sample types as Atlas JSON, to register directly or create over REST."""


def sample_types() -> AtlasTypesDef:
    """``SAMPLE_TYPES`` as definitions."""
    return AtlasTypesDef.model_validate(SAMPLE_TYPES)


def sample_registry() -> TypeRegistry:
    """A registry of the sample types."""
    registry = TypeRegistry()
    with registry.update() as transient:
        transient.add_types(sample_types())
    return registry


def sample_entity(
    registry: TypeRegistry,
    type_name: str,
    guid: str,
    attributes: dict[str, Any] | None = None,
    **system: Any,  # noqa: ANN401 - StoredEntity fields
) -> StoredEntity:
    """An entity as stored, created at time 1000: ``attributes`` by name, already in their stored form (DD-049)."""
    entity_type = registry.entity_type(type_name)
    if entity_type is None:
        raise ValueError(type_name)
    stored = StoredEntity.of(
        AtlasEntity(type_name=type_name, attributes=attributes or {}), entity_type, guid=guid, now=1000, user=None
    )
    return stored.model_copy(update=system)
