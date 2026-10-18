"""What Atlas keeps of a type definition, and so answers with afterwards (TDS-03, TDS-05 to TDS-07).

Atlas's def stores write a definition to a graph vertex and build every response from the vertex again
(``toEntityDef(vertex)``, …). Attributes go through the legacy form of ``toJsonFromAttribute`` and
``toAttributeDefFromJson``; these functions apply the same round trip without the graph (DD-028).
"""

from datetime import datetime
from uuid import uuid4

from aurelius_atlas_model.errors import java_string
from aurelius_atlas_model.typedef import (
    CONSTRAINT_PARAM_ATTRIBUTE,
    CONSTRAINT_TYPE_INVERSE_REF,
    CONSTRAINT_TYPE_OWNED_REF,
    AtlasAttributeDef,
    AtlasBaseTypeDef,
    AtlasBusinessMetadataDef,
    AtlasClassificationDef,
    AtlasConstraintDef,
    AtlasEntityDef,
    AtlasEnumDef,
    AtlasEnumElementDef,
    AtlasRelationshipDef,
    AtlasRelationshipEndDef,
    AtlasStructDef,
    Cardinality,
    PropagateTags,
    RelationshipCategory,
    TypeCategory,
)
from aurelius_atlas_typesystem.types import AtlasAttribute, StructType

JAVA_INT_MAX = 2_147_483_647
"""``Integer.MAX_VALUE``: the upper bound Atlas stores for an unbounded list or set."""

LEGACY_KIND = {
    TypeCategory.ENUM: "ENUM",
    TypeCategory.STRUCT: "STRUCT",
    TypeCategory.CLASSIFICATION: "TRAIT",
    TypeCategory.ENTITY: "CLASS",
    TypeCategory.RELATIONSHIP: "RELATIONSHIP",
    TypeCategory.BUSINESS_METADATA: "BUSINESS_METADATA",
}
"""The legacy ``DataTypes.TypeCategory`` names Atlas's ``TYPE_MATCH_FAILED`` messages use (TDS-02)."""


def stored_attribute(attribute: AtlasAttribute) -> AtlasAttributeDef:
    """An attribute after ``toJsonFromAttribute`` and ``toAttributeDefFromJson`` (TDS-05)."""
    definition = attribute.attribute_def
    if definition.cardinality is Cardinality.SINGLE:
        lower = 0 if definition.is_optional else 1
        upper = 1
    else:
        lower = 0 if definition.is_optional else max(definition.values_min_count, 1)
        upper = JAVA_INT_MAX if definition.values_max_count < 2 else definition.values_max_count  # noqa: PLR2004 - Java's bound
    if upper < 2:  # noqa: PLR2004 - Java's bound
        cardinality, max_count = Cardinality.SINGLE, 1
    else:
        cardinality = Cardinality.SET if definition.cardinality is Cardinality.SET else Cardinality.LIST
        max_count = upper
    constraints: list[AtlasConstraintDef] = []
    if attribute.is_owned_ref:
        constraints.append(AtlasConstraintDef(type=CONSTRAINT_TYPE_OWNED_REF))
    if attribute.inverse_ref_attribute_name and attribute.inverse_ref_attribute_name.strip():
        constraints.append(
            AtlasConstraintDef(
                type=CONSTRAINT_TYPE_INVERSE_REF,
                params={CONSTRAINT_PARAM_ATTRIBUTE: attribute.inverse_ref_attribute_name},
            )
        )
    return AtlasAttributeDef(
        name=definition.name,
        type_name=definition.type_name,
        is_unique=definition.is_unique,
        is_indexable=definition.is_indexable,
        include_in_notification=definition.include_in_notification,
        default_value=definition.default_value,
        description=definition.description,
        options=definition.options,
        display_name=definition.display_name,
        constraints=constraints,
        is_optional=lower == 0,
        values_min_count=lower,
        cardinality=cardinality,
        values_max_count=max_count,
        search_weight=definition.search_weight,
        index_type=definition.index_type,
    )


def stamp_created(typedef: AtlasBaseTypeDef, now: datetime, user: str | None) -> None:
    """``createTypeVertex``: fill in what a new definition lacks (TDS-03); changes ``typedef``, as Java does."""
    if not (typedef.type_version or "").strip():
        typedef.type_version = "1.0"
    if typedef.version is None:
        typedef.version = 1
    if not (typedef.guid or "").strip():
        typedef.guid = str(uuid4())
    if typedef.create_time is None:
        typedef.create_time = now
    if typedef.update_time is None:
        typedef.update_time = now
    typedef.created_by = user
    typedef.updated_by = user
    if not (typedef.description or "").strip():
        typedef.description = typedef.name


def stamp_updated(typedef: AtlasBaseTypeDef, stored: AtlasBaseTypeDef, now: datetime, user: str | None) -> None:
    """``updateTypeVertex`` and ``markVertexUpdated``: keep what may not change, bump the version (TDS-07)."""
    typedef.name = stored.name
    typedef.guid = _non_blank(typedef.guid, stored.guid)
    typedef.description = _non_blank(typedef.description, stored.description)
    typedef.type_version = _non_blank(typedef.type_version, stored.type_version)
    typedef.service_type = typedef.service_type or stored.service_type
    typedef.created_by = stored.created_by
    typedef.create_time = stored.create_time
    typedef.updated_by = user
    typedef.update_time = now
    typedef.version = (stored.version or 0) + 1


def _non_blank(value: str | None, stored: str | None) -> str | None:
    return value if value is not None and value.strip() else stored


def stored_typedef(typedef: AtlasBaseTypeDef, type_: StructType | None) -> AtlasBaseTypeDef:
    """The definition as Atlas reads it back from its vertex (``to*Def(vertex)``, TDS-05, TDS-06).

    ``type_`` is the definition's resolved type, whose attributes are stored; None for an enum.
    """
    base = {
        "name": typedef.name,
        "description": typedef.description,
        "service_type": typedef.service_type,
        "type_version": typedef.type_version,
        "guid": typedef.guid,
        "created_by": typedef.created_by,
        "updated_by": typedef.updated_by,
        "create_time": typedef.create_time,
        "update_time": typedef.update_time,
        "version": typedef.version if typedef.version is not None else 0,
        "options": typedef.options,
    }
    if isinstance(typedef, AtlasEnumDef):
        return AtlasEnumDef(
            **base,
            element_defs=[
                AtlasEnumElementDef(
                    value=element.value,
                    ordinal=element.ordinal,
                    description=element.description if (element.description or "").strip() else None,
                )
                for element in typedef.element_defs
            ],
            default_value=typedef.default_value,
        )
    if not isinstance(typedef, AtlasStructDef) or type_ is None:  # pragma: no cover - every other kind is a struct
        raise TypeError(typedef)
    attributes = [
        stored_attribute(attribute)
        for definition in typedef.attribute_defs
        if (attribute := type_.attribute(definition.name)) is not None
    ]
    match typedef:
        case AtlasClassificationDef():
            return AtlasClassificationDef(
                **base,
                attribute_defs=attributes,
                super_types=list(typedef.super_types),
                entity_types=list(typedef.entity_types),
            )
        case AtlasEntityDef():
            return AtlasEntityDef(**base, attribute_defs=attributes, super_types=list(typedef.super_types))
        case AtlasRelationshipDef():
            return AtlasRelationshipDef(
                **base,
                attribute_defs=attributes,
                relationship_category=typedef.relationship_category or RelationshipCategory.ASSOCIATION,
                propagate_tags=typedef.propagate_tags or PropagateTags.NONE,
                relationship_label=typedef.relationship_label,
                end_def1=_copy_end(typedef.end_def1),
                end_def2=_copy_end(typedef.end_def2),
            )
        case AtlasBusinessMetadataDef():
            return AtlasBusinessMetadataDef(**base, attribute_defs=attributes)
        case _:
            return AtlasStructDef(**base, attribute_defs=attributes)


def _copy_end(end: AtlasRelationshipEndDef | None) -> AtlasRelationshipEndDef | None:
    return None if end is None else AtlasRelationshipEndDef.model_validate(end.to_json())


def java_end_string(end: AtlasRelationshipEndDef | None) -> str:
    """``AtlasRelationshipEndDef.toString``, as ``RELATIONSHIPDEF_INVALID_END*_UPDATE`` messages show it (TDS-08)."""
    if end is None:
        return "null"
    fields = (
        ("type=", end.type),
        ("name==>", end.name),
        ("description==>", end.description),
        ("isContainer==>", end.is_container),
        ("cardinality==>", None if end.cardinality is None else end.cardinality.value),
        ("isLegacyAttribute==>", end.is_legacy_attribute),
    )
    return "AtlasRelationshipEndDef{" + ", ".join(f"{name}'{java_string(value)}'" for name, value in fields) + "}"
