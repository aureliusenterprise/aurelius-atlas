"""Types and stored entities to read back in tests of the entity reads and writes (DD-049, DD-051).

``table`` has an attribute of every kind the reads map: dates, enums, structs, arrays and maps, plain, owned and
soft references, and a relationship attribute (``home``). ``WRITE_TYPES`` add what only writes treat apart:
defaults, sets, appending on partial update, a dynamic attribute, a legacy relationship end, and a relationship
type with attributes and tag propagation.
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


APPEND = {"isAppendOnPartialUpdate": "true"}

WRITE_TYPES: dict[str, Any] = {
    "entityDefs": [
        {
            "name": "w_item",
            "superTypes": ["s_ref"],
            "options": {"dynAttribute:name": "item-{qualifiedName}"},
            "attributeDefs": [
                _attribute("count", "int"),
                _attribute("flag", "boolean"),
                _attribute("when", "date"),
                _attribute("label", "string", defaultValue="none"),
                _attribute("tags", "array<string>", cardinality="SET", options=APPEND),
                _attribute("notes", "map<string,string>", options=APPEND),
                _attribute("peers", "array<s_column>", cardinality="SET"),
                _attribute("holder", "s_database"),
            ],
        },
    ],
    "relationshipDefs": [
        {
            "name": "w_item_holder",
            "relationshipCategory": "ASSOCIATION",
            "endDef1": {"type": "w_item", "name": "holder", "cardinality": "SINGLE", "isLegacyAttribute": True},
            "endDef2": {"type": "s_database", "name": "items", "cardinality": "SET"},
        },
        {
            "name": "w_link",
            "relationshipCategory": "ASSOCIATION",
            "propagateTags": "ONE_TO_TWO",
            "endDef1": {"type": "w_item", "name": "links", "cardinality": "SET"},
            "endDef2": {"type": "s_column", "name": "linkedBy", "cardinality": "SET"},
            "attributeDefs": [_attribute("weight", "int"), _attribute("note", "string", defaultValue="n")],
        },
    ],
}
"""Types only writes need, on top of ``SAMPLE_TYPES``, as Atlas JSON."""


RELATIONSHIP_TYPES: dict[str, Any] = {
    "entityDefs": [
        {
            "name": "r_node",
            "superTypes": ["s_ref"],
            "options": {"appendRelationshipsOnPartialUpdate": '["friends"]'},
            "attributeDefs": [
                _attribute("keeper", "s_database"),
                _attribute("members", "array<s_column>", cardinality="SET", options=APPEND),
                _attribute("owns", "array<s_column>", cardinality="SET", options=APPEND, constraints=OWNED),
                _attribute("lead", "r_tag", constraints=[{"type": "inverseRef", "params": {"attribute": "follower"}}]),
            ],
        },
        {"name": "r_part", "superTypes": ["s_ref"]},
        {
            "name": "r_pin",
            "superTypes": ["s_ref"],
            "attributeDefs": [{**_attribute("pinned", "s_column"), "isOptional": False}],
        },
        {
            "name": "r_tag",
            "superTypes": ["s_ref"],
            "attributeDefs": [
                _attribute("follower", "r_node", constraints=[{"type": "inverseRef", "params": {"attribute": "lead"}}]),
            ],
        },
    ],
    "relationshipDefs": [
        {
            "name": "r_tree",
            "relationshipCategory": "COMPOSITION",
            "endDef1": {"type": "r_node", "name": "parts", "cardinality": "SET", "isContainer": True},
            "endDef2": {"type": "r_part", "name": "whole", "cardinality": "SINGLE"},
        },
        {
            "name": "r_peer",
            "relationshipCategory": "ASSOCIATION",
            "endDef1": {"type": "r_node", "name": "friends", "cardinality": "SET"},
            "endDef2": {"type": "r_node", "name": "friends", "cardinality": "SET"},
        },
        {
            "name": "r_keeper",
            "relationshipCategory": "ASSOCIATION",
            "endDef1": {"type": "s_database", "name": "kept", "cardinality": "SET"},
            "endDef2": {"type": "r_node", "name": "keeper", "cardinality": "SINGLE", "isLegacyAttribute": True},
        },
        {
            "name": "r_members",
            "relationshipCategory": "ASSOCIATION",
            "endDef1": {"type": "r_node", "name": "members", "cardinality": "SET", "isLegacyAttribute": True},
            "endDef2": {"type": "s_column", "name": "memberOf", "cardinality": "SET"},
        },
        {
            "name": "r_badge",
            "relationshipCategory": "ASSOCIATION",
            "relationshipLabel": "badge",
            "endDef1": {"type": "r_node", "name": "badge", "cardinality": "SINGLE"},
            "endDef2": {"type": "s_column", "name": "badgeOf", "cardinality": "SINGLE", "isLegacyAttribute": True},
        },
        {
            "name": "r_lead",
            "relationshipCategory": "ASSOCIATION",
            "endDef1": {"type": "r_node", "name": "lead", "cardinality": "SINGLE", "isLegacyAttribute": True},
            "endDef2": {"type": "r_tag", "name": "follower", "cardinality": "SINGLE", "isLegacyAttribute": True},
        },
    ],
}
"""Types for relationship attributes (REL-11 to REL-19), on top of the others, as Atlas JSON.

``r_tree`` composes a node of parts (``parts`` is ``OUT`` and owned, ``whole`` ``IN`` and mandatory); ``r_peer``
relates nodes both ways (``BOTH``); ``r_keeper``'s legacy end is end 2 (``keeper`` is ``OUT``, ``kept`` ``IN``);
``members`` is a legacy array end that appends on a partial update; ``badgeOf`` is a legacy end ``s_column`` has
no attribute for (``badge`` is ``IN``); ``r_lead``'s ends, ``r_node.lead`` and
``r_tag.follower``, are legacy attributes, each the other's ``inverseRef``.
``friends`` keeps its relationships on any update (``appendRelationshipsOnPartialUpdate``). ``owns`` is a plain
owned array that appends on a partial update; ``r_pin.pinned`` is a mandatory plain reference (OWN-01, OWN-02).
"""


CLASSIFICATION_TYPES: dict[str, Any] = {
    "classificationDefs": [
        {
            "name": "c_pii",
            "attributeDefs": [
                _attribute("level", "int"),
                _attribute("note", "string"),
                _attribute("since", "date"),
            ],
        },
        {"name": "c_secret", "superTypes": ["c_pii"]},
        {"name": "c_tabular", "entityTypes": ["s_table"]},
        {"name": "c_owned", "attributeDefs": [{**_attribute("owner", "string"), "isOptional": False}]},
    ],
}
"""Classification types (CLS-01 to CLS-12), on top of the others: ``c_secret`` is a ``c_pii``, ``c_tabular`` may
classify tables only, ``c_owned`` has a mandatory attribute."""


def sample_types() -> AtlasTypesDef:
    """``SAMPLE_TYPES`` as definitions."""
    return AtlasTypesDef.model_validate(SAMPLE_TYPES)


def write_types() -> AtlasTypesDef:
    """``WRITE_TYPES`` as definitions."""
    return AtlasTypesDef.model_validate(WRITE_TYPES)


def sample_registry(
    *, writes: bool = False, relationships: bool = False, classifications: bool = False
) -> TypeRegistry:
    """A registry of the sample types; the write types, ``RELATIONSHIP_TYPES`` or ``CLASSIFICATION_TYPES`` as asked.

    Relationships and classifications bring the write types too.
    """
    registry = TypeRegistry()
    with registry.update() as transient:
        transient.add_types(sample_types())
        if writes or relationships or classifications:
            transient.add_types(write_types())
        if relationships:
            transient.add_types(AtlasTypesDef.model_validate(RELATIONSHIP_TYPES))
        if classifications:
            transient.add_types(AtlasTypesDef.model_validate(CLASSIFICATION_TYPES))
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


def sample_entities(registry: TypeRegistry) -> list[StoredEntity]:
    """Database ``d``, columns ``c1`` to ``c3`` and table ``t``, whose attributes reach them in every way they can.

    ``t`` owns ``c1`` and ``c2``, refers to ``d``, holds ``c3`` in a struct and as soft references, and refers to
    an entity that does not exist (``gone``, ``nowhere``).
    """
    return [
        sample_entity(registry, "s_database", "d", {"qualifiedName": "db@cl", "title": "DB"}),
        sample_entity(registry, "s_column", "c1", {"qualifiedName": "c1@cl", "position": 1}),
        sample_entity(registry, "s_column", "c2", {"qualifiedName": "c2@cl", "comment": "x"}),
        sample_entity(registry, "s_column", "c3", {"qualifiedName": "c3@cl"}),
        sample_entity(
            registry,
            "s_table",
            "t",
            {
                "qualifiedName": "t@cl",
                "name": "orders",
                "created": 1_700_000_000_000,
                "color": "BLUE",
                "place": {"typeName": "s_place", "attributes": {"x": 3, "at": "c3"}},
                "places": [{"typeName": "s_place", "attributes": {"label": "p"}}],
                "sizes": [1, 2],
                "props": {"k": "v"},
                "db": "d",
                "columns": ["c1", None, "gone"],
                "byName": {"second": "c2"},
                "primary": "s_column:c3",
                "spare": ["s_column:c3", "s_column:nowhere", "bad"],
            },
            labels=["gold"],
            home_id="home",
        ),
    ]
