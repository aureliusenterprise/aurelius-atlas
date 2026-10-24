"""Atlas type definitions as Pydantic models that read and write Atlas's REST JSON (DD-020).

Ported from ``org.apache.atlas.model.typedef`` of Apache Atlas 2.4.0. Field names are snake_case in Python and
the Java getter names in JSON (TDM-01). The normalisations the Java setters and constructors apply run as
validators, so they hold for request bodies and for models built in code alike.

The TDM-nn rule each class and field ports is cited in the increment spec, not in
class docstrings or field descriptions: those are public and end up in the OpenAPI
schema, where decision ids mean nothing to a client.
"""

from collections.abc import Callable, Iterable
from enum import StrEnum
from typing import Annotated, Any, ClassVar, Self

from pydantic import (
    AfterValidator,
    BeforeValidator,
    Field,
    computed_field,
)

from aurelius_atlas_model.base import (
    AtlasModel,
    JavaBool,
    JavaInt,
    NameSet,
    OptionalNameSet,
    Timestamp,
    empty_when_null,
    null_when_empty,
)

ATLAS_TYPE_BOOLEAN = "boolean"
ATLAS_TYPE_BYTE = "byte"
ATLAS_TYPE_SHORT = "short"
ATLAS_TYPE_INT = "int"
ATLAS_TYPE_LONG = "long"
ATLAS_TYPE_FLOAT = "float"
ATLAS_TYPE_DOUBLE = "double"
ATLAS_TYPE_BIGINTEGER = "biginteger"
ATLAS_TYPE_BIGDECIMAL = "bigdecimal"
ATLAS_TYPE_STRING = "string"
ATLAS_TYPE_DATE = "date"
ATLAS_TYPE_OBJECT_ID = "objectid"

ATLAS_TYPE_PROCESS = "Process"
ATLAS_TYPE_DATASET = "DataSet"
ATLAS_TYPE_ASSET = "Asset"
ATLAS_TYPE_INFRASTRUCTURE = "Infrastructure"

ATLAS_PRIMITIVE_TYPES = (
    ATLAS_TYPE_BOOLEAN,
    ATLAS_TYPE_BYTE,
    ATLAS_TYPE_SHORT,
    ATLAS_TYPE_INT,
    ATLAS_TYPE_LONG,
    ATLAS_TYPE_FLOAT,
    ATLAS_TYPE_DOUBLE,
    ATLAS_TYPE_BIGINTEGER,
    ATLAS_TYPE_BIGDECIMAL,
    ATLAS_TYPE_STRING,
)
"""Atlas's primitive type names (TDM-19)."""

ATLAS_RELATIONSHIP_ATTRIBUTE_TYPES = (*ATLAS_PRIMITIVE_TYPES, ATLAS_TYPE_DATE)
"""The type names a relationship attribute may have: the primitives and ``date`` (TDM-19)."""

ATLAS_BUILTIN_TYPES = (*ATLAS_PRIMITIVE_TYPES, ATLAS_TYPE_DATE, ATLAS_TYPE_OBJECT_ID)
"""Atlas's built-in type names (TDM-19)."""

TYPEDEF_OPTION_SUPPORTS_SCHEMA = "supportsSchema"
TYPEDEF_OPTION_SUPPORTS_PROFILE = "supportsProfile"
SERVICE_TYPE_ATLAS_CORE = "atlas_core"

ATTRDEF_OPTION_SOFT_REFERENCE = "isSoftReference"
ATTRDEF_OPTION_APPEND_ON_PARTIAL_UPDATE = "isAppendOnPartialUpdate"
DEFAULT_SEARCH_WEIGHT = -1
COUNT_NOT_SET = -1

CONSTRAINT_TYPE_OWNED_REF = "ownedRef"
CONSTRAINT_TYPE_INVERSE_REF = "inverseRef"
CONSTRAINT_PARAM_ATTRIBUTE = "attribute"

OPTION_DISPLAY_TEXT_ATTRIBUTE = "displayTextAttribute"
ATTR_OPTION_APPLICABLE_ENTITY_TYPES = "applicableEntityTypes"
ATTR_MAX_STRING_LENGTH = "maxStrLength"
ATTR_VALID_PATTERN = "validPattern"


def array_type_name(element_type_name: str) -> str:
    """The name of the array type of ``element_type_name``: ``array<T>`` (TDM-19)."""
    return f"array<{element_type_name}>"


def map_type_name(key_type_name: str, value_type_name: str) -> str:
    """The name of the map type from ``key_type_name`` to ``value_type_name``: ``map<K,V>`` (TDM-19)."""
    return f"map<{key_type_name},{value_type_name}>"


class TypeCategory(StrEnum):
    """The kinds of Atlas types (``org.apache.atlas.model.TypeCategory``)."""

    PRIMITIVE = "PRIMITIVE"
    OBJECT_ID_TYPE = "OBJECT_ID_TYPE"
    ENUM = "ENUM"
    STRUCT = "STRUCT"
    CLASSIFICATION = "CLASSIFICATION"
    ENTITY = "ENTITY"
    ARRAY = "ARRAY"
    MAP = "MAP"
    RELATIONSHIP = "RELATIONSHIP"
    BUSINESS_METADATA = "BUSINESS_METADATA"


class Cardinality(StrEnum):
    """How many values an attribute or relationship end holds."""

    SINGLE = "SINGLE"
    LIST = "LIST"
    SET = "SET"


class IndexType(StrEnum):
    """How an attribute is indexed."""

    DEFAULT = "DEFAULT"
    STRING = "STRING"


class RelationshipCategory(StrEnum):
    """How the two ends of a relationship depend on each other."""

    ASSOCIATION = "ASSOCIATION"
    AGGREGATION = "AGGREGATION"
    COMPOSITION = "COMPOSITION"


class PropagateTags(StrEnum):
    """The direction in which classifications propagate over a relationship."""

    NONE = "NONE"
    ONE_TO_TWO = "ONE_TO_TWO"
    TWO_TO_ONE = "TWO_TO_ONE"
    BOTH = "BOTH"


def _keep_last_by[T](values: list[T], key: Callable[[T], str | None]) -> list[T]:
    """Keep the last of the values with the same key, compared without case, at its own position.

    Values without a key are dropped (TDM-07, TDM-08).
    """
    kept: list[T] = []
    seen: set[str] = set()
    for value in reversed(values):
        name = key(value)
        if name is not None and name.lower() not in seen:
            seen.add(name.lower())
            kept.append(value)
    kept.reverse()
    return kept


def _equal_ignoring_case(left: str | None, right: str | None) -> bool:
    """``StringUtils.equalsIgnoreCase``: two nulls are equal, a null and a string are not."""
    if left is None or right is None:
        return left is right
    return left.lower() == right.lower()


class AtlasConstraintDef(AtlasModel):
    """A constraint on an attribute, such as ``ownedRef`` or ``inverseRef``."""

    type: str | None = Field(default=None, description="The constraint type name, e.g. ``ownedRef``.")

    params: dict[str, Any] | None = Field(
        default=None,
        description="The constraint's parameters, e.g. ``attribute`` for a ref constraint.",
    )

    def is_constraint_type(self, name: str | None) -> bool:
        """Whether this constraint is of type ``name``, compared without case."""
        return _equal_ignoring_case(name, self.type)

    def get_param(self, name: str) -> Any:  # noqa: ANN401 - Atlas's params are untyped JSON values
        """The value of parameter ``name``, or None."""
        return None if self.params is None else self.params.get(name)


class AtlasAttributeDef(AtlasModel):
    """An attribute of a struct, classification, entity, relationship or business metadata type.

    A null cardinality, an explicit null boolean, and an empty constraint list are
    normalised on read, as the Java setters do.
    """

    name: str | None = Field(default=None, description="The attribute name, unique within its type.")

    type_name: str | None = Field(
        default=None,
        description="The attribute's type: a primitive or built-in name, an array/map type name, "
        "or the name of a defined type.",
    )

    is_optional: JavaBool = Field(default=False, description="Whether an entity may omit the attribute.")

    cardinality: Cardinality | None = Field(
        default=Cardinality.SINGLE,
        description="How many values the attribute holds: SINGLE, LIST, or SET. A null reads as SINGLE.",
    )

    values_min_count: JavaInt = Field(
        default=COUNT_NOT_SET,
        description="The least number of values a LIST/SET attribute must hold; -1 means unset.",
    )

    values_max_count: JavaInt = Field(
        default=COUNT_NOT_SET,
        description="The most number of values a LIST/SET attribute may hold; -1 means unlimited.",
    )

    is_unique: JavaBool = Field(
        default=False,
        description="Whether the attribute's value is unique across the entities of its type.",
    )

    is_indexable: JavaBool = Field(default=False, description="Whether the attribute is searchable.")

    include_in_notification: JavaBool = Field(
        default=False,
        description="Whether the attribute's value is carried in change notifications.",
    )

    default_value: str | None = Field(
        default=None,
        description="The value an entity gets for the attribute when it omits one.",
    )

    description: str | None = Field(default=None, description="A description of the attribute.")

    search_weight: JavaInt = Field(
        default=DEFAULT_SEARCH_WEIGHT,
        description="The attribute's weight in search scoring, 1 to 10; -1 means unset.",
    )

    index_type: IndexType | None = Field(
        default=None,
        description="How a string attribute is indexed: DEFAULT or STRING.",
    )

    constraints: Annotated[list[AtlasConstraintDef] | None, AfterValidator(null_when_empty)] = Field(
        default=None,
        description="The constraints on the attribute, e.g. ``ownedRef``/``inverseRef`` pairs. "
        "An empty list is written back as null.",
    )

    options: dict[str, str] | None = Field(
        default=None,
        description="Extension options of the attribute, e.g. ``maxStrLength``, ``validPattern``, ``isSoftReference``.",
    )

    display_name: str | None = Field(
        default=None,
        description="The name shown for the attribute in UIs; the name itself when unset.",
    )

    def get_option(self, name: str) -> str | None:
        """The value of option ``name``, or None."""
        return None if self.options is None else self.options.get(name)

    def set_option(self, name: str, value: str) -> None:
        """Set option ``name`` to ``value``."""
        self.options = {**(self.options or {}), name: value}

    def is_soft_referenced(self) -> bool:
        """Whether the ``isSoftReference`` option is true."""
        return (self.get_option(ATTRDEF_OPTION_SOFT_REFERENCE) or "").lower() == "true"

    def is_append_on_partial_update(self) -> bool:
        """Whether the ``isAppendOnPartialUpdate`` option is true."""
        return (self.get_option(ATTRDEF_OPTION_APPEND_ON_PARTIAL_UPDATE) or "").lower() == "true"

    def add_constraint(self, constraint: AtlasConstraintDef) -> None:
        """Append a constraint."""
        self.constraints = [*(self.constraints or []), constraint]


def _attribute_name(attribute: AtlasAttributeDef) -> str | None:
    return attribute.name


def _keep_last_attributes(attributes: list[AtlasAttributeDef]) -> list[AtlasAttributeDef]:
    return _keep_last_by(attributes, _attribute_name)


type AttributeDefs = Annotated[
    list[AtlasAttributeDef], BeforeValidator(empty_when_null), AfterValidator(_keep_last_attributes)
]
"""``attributeDefs``: never null, one definition per name (TDM-06, TDM-07)."""


def find_attribute(attributes: Iterable[AtlasAttributeDef], name: str | None) -> AtlasAttributeDef | None:
    """The first attribute definition named ``name``, compared without case, or None (TDM-16)."""
    return next((attribute for attribute in attributes if _equal_ignoring_case(attribute.name, name)), None)


class AtlasBaseTypeDef(AtlasModel):
    """What every type definition has: identity, audit fields, name and options."""

    CATEGORY: ClassVar[TypeCategory]

    guid: str | None = Field(default=None, description="The server-assigned guid of the type definition.")

    created_by: str | None = Field(default=None, description="The user who created the type.")

    updated_by: str | None = Field(default=None, description="The user who last updated the type.")

    create_time: Timestamp | None = Field(
        default=None,
        description="When the type was created, in epoch milliseconds.",
    )

    update_time: Timestamp | None = Field(
        default=None,
        description="When the type was last updated, in epoch milliseconds.",
    )

    version: int | None = Field(default=None, description="The version of the type definition.")

    name: str | None = Field(default=None, description="The unique name of the type.")

    description: str | None = Field(default=None, description="A description of the type.")

    type_version: str | None = Field(
        default=None,
        description="The version string of the type, used by typedef patches.",
    )

    service_type: str | None = Field(
        default=None,
        description="The service the type belongs to; built-in types use ``atlas_core``.",
    )

    options: dict[str, str] | None = Field(
        default=None,
        description="Extension options of the type, e.g. ``applicableEntityTypes``.",
    )

    @computed_field(description="The kind of this type definition, fixed by its type: never read from input.")
    @property
    def category(self) -> TypeCategory:
        """The kind of this type definition, fixed by its class; never read from input (TDM-04)."""
        return self.CATEGORY

    def get_option(self, name: str) -> str | None:
        """The value of option ``name``, or None."""
        return None if self.options is None else self.options.get(name)

    def set_option(self, name: str, value: str) -> None:
        """Set option ``name`` to ``value``."""
        self.options = {**(self.options or {}), name: value}


class AtlasEnumElementDef(AtlasModel):
    """One value of an enum type."""

    value: str | None = Field(default=None, description="The enum value, unique within its type.")

    description: str | None = Field(default=None, description="A description of the enum value.")

    ordinal: int | None = Field(default=None, description="The position of the value in the enum.")


def _element_value(element: AtlasEnumElementDef) -> str | None:
    return element.value


def _keep_last_elements(elements: list[AtlasEnumElementDef]) -> list[AtlasEnumElementDef]:
    return _keep_last_by(elements, _element_value)


class AtlasEnumDef(AtlasBaseTypeDef):
    """An enum type."""

    CATEGORY: ClassVar[TypeCategory] = TypeCategory.ENUM

    element_defs: Annotated[
        list[AtlasEnumElementDef], BeforeValidator(empty_when_null), AfterValidator(_keep_last_elements)
    ] = Field(
        default_factory=list,
        description="The values of the enum; one element per value, the last given for a value wins.",
    )

    default_value: str | None = Field(
        default=None,
        description="The value an entity gets for a missing attribute of this enum type.",
    )

    def get_element(self, value: str | None) -> AtlasEnumElementDef | None:
        """The element with ``value``, compared without case, or None (TDM-16)."""
        return next((element for element in self.element_defs if _equal_ignoring_case(element.value, value)), None)

    def has_element(self, value: str | None) -> bool:
        """Whether an element has ``value``, compared without case (TDM-16)."""
        return self.get_element(value) is not None

    def add_element(self, element: AtlasEnumElementDef) -> None:
        """Add ``element`` at the end, replacing an element with the same value (TDM-16)."""
        kept = [existing for existing in self.element_defs if not _equal_ignoring_case(existing.value, element.value)]
        self.element_defs = [*kept, element]

    def remove_element(self, value: str | None) -> None:
        """Remove the elements with ``value``, compared without case (TDM-16)."""
        self.element_defs = [element for element in self.element_defs if not _equal_ignoring_case(element.value, value)]


class AtlasStructDef(AtlasBaseTypeDef):
    """A struct type, and the base of the types that have attributes."""

    CATEGORY: ClassVar[TypeCategory] = TypeCategory.STRUCT

    attribute_defs: AttributeDefs = Field(
        default_factory=list,
        description="The attributes of the type; one definition per name, the last given for a name wins.",
    )

    def get_attribute(self, name: str | None) -> AtlasAttributeDef | None:
        """The attribute definition named ``name``, compared without case, or None (TDM-16)."""
        return find_attribute(self.attribute_defs, name)

    def has_attribute(self, name: str | None) -> bool:
        """Whether an attribute definition is named ``name``, compared without case (TDM-16)."""
        return self.get_attribute(name) is not None

    def add_attribute(self, attribute: AtlasAttributeDef) -> None:
        """Add ``attribute`` at the end, replacing one with the same name (TDM-16)."""
        kept = [existing for existing in self.attribute_defs if not _equal_ignoring_case(existing.name, attribute.name)]
        self.attribute_defs = [*kept, attribute]

    def remove_attribute(self, name: str | None) -> None:
        """Remove the attribute definitions named ``name``, compared without case (TDM-16)."""
        self.attribute_defs = [
            attribute for attribute in self.attribute_defs if not _equal_ignoring_case(attribute.name, name)
        ]


def _with(names: list[str], name: str) -> list[str]:
    return names if name in names else [*names, name]


def _without(names: list[str], name: str) -> list[str]:
    return [existing for existing in names if existing != name]


class AtlasClassificationDef(AtlasStructDef):
    """A classification type: attributes, super types and the entity types it may be applied to."""

    CATEGORY: ClassVar[TypeCategory] = TypeCategory.CLASSIFICATION

    super_types: NameSet = Field(
        default_factory=list,
        description="The classifications this one extends.",
    )

    entity_types: NameSet = Field(
        default_factory=list,
        description="The entity types the classification may be applied to.",
    )

    sub_types: OptionalNameSet = Field(
        default=None,
        description="The classifications extending this one; derived by the server, ignored on create and update.",
    )

    def has_super_type(self, name: str) -> bool:
        """Whether ``name`` is a super type, compared exactly (TDM-16)."""
        return name in self.super_types

    def add_super_type(self, name: str) -> None:
        """Add the super type ``name`` (TDM-16)."""
        self.super_types = _with(self.super_types, name)

    def remove_super_type(self, name: str) -> None:
        """Remove the super type ``name`` (TDM-16)."""
        self.super_types = _without(self.super_types, name)

    def has_entity_type(self, name: str) -> bool:
        """Whether the classification may be applied to entity type ``name``, compared exactly (TDM-16)."""
        return name in self.entity_types

    def add_entity_type(self, name: str) -> None:
        """Allow the classification on entity type ``name`` (TDM-16)."""
        self.entity_types = _with(self.entity_types, name)

    def remove_entity_type(self, name: str) -> None:
        """No longer allow the classification on entity type ``name`` (TDM-16)."""
        self.entity_types = _without(self.entity_types, name)


class AtlasRelationshipAttributeDef(AtlasAttributeDef):
    """An entity attribute that a relationship type adds; read-only, derived from the relationship types."""

    relationship_type_name: str | None = Field(
        default=None,
        description="The name of the relationship type that adds this attribute.",
    )

    is_legacy_attribute: JavaBool = Field(
        default=False,
        description="Whether the attribute comes from a legacy relationship end definition.",
    )


class AtlasEntityDef(AtlasStructDef):
    """An entity type."""

    CATEGORY: ClassVar[TypeCategory] = TypeCategory.ENTITY

    super_types: NameSet = Field(
        default_factory=list,
        description="The entity types this one extends.",
    )

    sub_types: OptionalNameSet = Field(
        default=None,
        description="The entity types extending this one; derived by the server, ignored on create and update.",
    )

    relationship_attribute_defs: list[AtlasRelationshipAttributeDef] | None = Field(
        default=None,
        description="The attributes added by relationship types; derived by the server, ignored on create and update.",
    )

    business_attribute_defs: dict[str, list[AtlasAttributeDef]] | None = Field(
        default=None,
        description="The attributes of the business metadata types that apply to this one, keyed by "
        "business metadata type name; derived by the server, ignored on create and update.",
    )

    def has_super_type(self, name: str) -> bool:
        """Whether ``name`` is a super type, compared exactly (TDM-16)."""
        return name in self.super_types

    def add_super_type(self, name: str) -> None:
        """Add the super type ``name`` (TDM-16)."""
        self.super_types = _with(self.super_types, name)

    def remove_super_type(self, name: str) -> None:
        """Remove the super type ``name`` (TDM-16)."""
        self.super_types = _without(self.super_types, name)


class AtlasRelationshipEndDef(AtlasModel):
    """One end of a relationship type: the entity type there and the attribute it gets."""

    type: str | None = Field(
        default=None,
        description="The name of the entity type at this end of the relationship.",
    )

    name: str | None = Field(
        default=None,
        description="The name of the attribute this end adds to the entity type.",
    )

    is_container: JavaBool = Field(
        default=False,
        description="Whether the entity at this end owns the entities at the other end.",
    )

    cardinality: Cardinality | None = Field(
        default=Cardinality.SINGLE,
        description="How many entities sit at this end: SINGLE, LIST, or SET.",
    )

    is_legacy_attribute: JavaBool = Field(
        default=False,
        description="Whether the attribute this end defines already exists on the entity type.",
    )

    description: str | None = Field(default=None, description="A description of this end of the relationship.")


class AtlasRelationshipDef(AtlasStructDef):
    """A relationship type between two entity types."""

    CATEGORY: ClassVar[TypeCategory] = TypeCategory.RELATIONSHIP

    relationship_category: RelationshipCategory | None = Field(
        default=None,
        description="How the two ends depend on each other: ASSOCIATION, AGGREGATION, or COMPOSITION.",
    )

    relationship_label: str | None = Field(
        default=None,
        description="The label of the relationship; the type name when unset.",
    )

    propagate_tags: PropagateTags | None = Field(
        default=None,
        description="The direction in which classifications propagate over the relationship.",
    )

    end_def1: AtlasRelationshipEndDef | None = Field(
        default=None,
        description="The first end of the relationship.",
    )

    end_def2: AtlasRelationshipEndDef | None = Field(
        default=None,
        description="The second end of the relationship.",
    )


class AtlasBusinessMetadataDef(AtlasStructDef):
    """A business metadata type: attributes that apply to the entity types its options name."""

    CATEGORY: ClassVar[TypeCategory] = TypeCategory.BUSINESS_METADATA


class AtlasTypeDefHeader(AtlasModel):
    """The identity of a type definition, as ``/v2/types/typedefs/headers`` lists it."""

    guid: str | None = Field(default=None, description="The guid of the type definition.")

    name: str | None = Field(default=None, description="The name of the type.")

    service_type: str | None = Field(default=None, description="The service the type belongs to.")

    category: TypeCategory | None = Field(default=None, description="The kind of the type.")

    @classmethod
    def of(cls, typedef: AtlasBaseTypeDef) -> Self:
        """The header of ``typedef`` (TDM-18)."""
        return cls(guid=typedef.guid, name=typedef.name, service_type=typedef.service_type, category=typedef.category)


def _has_name(typedefs: list[Any] | None, name: str) -> bool:
    return any(typedef.name == name for typedef in typedefs or ())


class AtlasTypesDef(AtlasModel):
    """Type definitions of every kind: the body of ``/v2/types/typedefs``."""

    enum_defs: list[AtlasEnumDef] | None = Field(
        default_factory=list,
        description="The enum types.",
    )

    struct_defs: list[AtlasStructDef] | None = Field(
        default_factory=list,
        description="The struct types.",
    )

    classification_defs: list[AtlasClassificationDef] | None = Field(
        default_factory=list,
        description="The classification types.",
    )

    entity_defs: list[AtlasEntityDef] | None = Field(
        default_factory=list,
        description="The entity types.",
    )

    relationship_defs: list[AtlasRelationshipDef] | None = Field(
        default_factory=list,
        description="The relationship types.",
    )

    business_metadata_defs: list[AtlasBusinessMetadataDef] | None = Field(
        default_factory=list,
        description="The business metadata types.",
    )

    def is_empty(self) -> bool:
        """Whether every list is empty or null (TDM-17)."""
        return not any(
            (
                self.enum_defs,
                self.struct_defs,
                self.classification_defs,
                self.entity_defs,
                self.relationship_defs,
                self.business_metadata_defs,
            )
        )

    def has_enum_def(self, name: str) -> bool:
        """Whether an enum definition is named ``name`` (TDM-17)."""
        return _has_name(self.enum_defs, name)

    def has_struct_def(self, name: str) -> bool:
        """Whether a struct definition is named ``name`` (TDM-17)."""
        return _has_name(self.struct_defs, name)

    def has_classification_def(self, name: str) -> bool:
        """Whether a classification definition is named ``name`` (TDM-17)."""
        return _has_name(self.classification_defs, name)

    def has_entity_def(self, name: str) -> bool:
        """Whether an entity definition is named ``name`` (TDM-17)."""
        return _has_name(self.entity_defs, name)

    def has_relationship_def(self, name: str) -> bool:
        """Whether a relationship definition is named ``name`` (TDM-17)."""
        return _has_name(self.relationship_defs, name)

    def has_business_metadata_def(self, name: str) -> bool:
        """Whether a business metadata definition is named ``name`` (TDM-17)."""
        return _has_name(self.business_metadata_defs, name)
