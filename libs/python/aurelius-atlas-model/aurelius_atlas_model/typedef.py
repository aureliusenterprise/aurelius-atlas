"""Atlas type definitions as Pydantic models that read and write Atlas's REST JSON (DD-020).

Ported from ``org.apache.atlas.model.typedef`` of Apache Atlas 2.4.0. Field names are snake_case in Python and
the Java getter names in JSON (TDM-01). The normalisations the Java setters and constructors apply run as
validators, so they hold for request bodies and for models built in code alike.
"""

from collections.abc import Callable, Iterable
from datetime import UTC, datetime, timedelta
from enum import StrEnum
from typing import Annotated, Any, ClassVar, Self

from pydantic import (
    AfterValidator,
    BaseModel,
    BeforeValidator,
    ConfigDict,
    Field,
    PlainSerializer,
    computed_field,
)
from pydantic.alias_generators import to_camel

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


_EPOCH = datetime(1970, 1, 1, tzinfo=UTC)
_MILLISECOND = timedelta(milliseconds=1)


def _read_epoch_millis(value: object) -> object:
    """Read a number or a string of digits as epoch milliseconds; leave other values to Pydantic (DD-022)."""
    if isinstance(value, bool):
        return value
    if isinstance(value, int | float):
        return _EPOCH + value * _MILLISECOND
    if isinstance(value, str) and value.isdigit():
        return _EPOCH + int(value) * _MILLISECOND
    return value


def _as_utc(value: datetime) -> datetime:
    """Read a date-time without a zone as UTC, as Jackson's ``StdDateFormat`` does."""
    return value.replace(tzinfo=UTC) if value.tzinfo is None else value


def _write_epoch_millis(value: datetime) -> int:
    return (value - _EPOCH) // _MILLISECOND


type Timestamp = Annotated[
    datetime,
    BeforeValidator(_read_epoch_millis),
    AfterValidator(_as_utc),
    PlainSerializer(_write_epoch_millis, return_type=int, when_used="json"),
]
"""A ``java.util.Date``: an aware datetime, written as epoch milliseconds (TDM-05)."""


def _null_as(default: object) -> Callable[[object], object]:
    def read(value: object) -> object:
        return default if value is None else value

    return read


type JavaBool = Annotated[bool, BeforeValidator(_null_as(default=False))]
"""A Java ``boolean``: an explicit null reads as false (TDM-10)."""

type JavaInt = Annotated[int, BeforeValidator(_null_as(default=0))]
"""A Java ``int``: an explicit null reads as 0 (TDM-10)."""


def _empty_when_null(value: object) -> object:
    return [] if value is None else value


def _unique(names: list[str]) -> list[str]:
    """Keep each name once, in first-seen order (TDM-09, DD-021)."""
    return list(dict.fromkeys(names))


def _unique_or_null(names: list[str] | None) -> list[str] | None:
    return None if names is None else _unique(names)


def _null_when_empty[T](values: list[T] | None) -> list[T] | None:
    return values or None


type NameSet = Annotated[list[str], BeforeValidator(_empty_when_null), AfterValidator(_unique)]
"""A Java ``Set<String>`` that is never null (TDM-06, TDM-09)."""

type OptionalNameSet = Annotated[list[str] | None, AfterValidator(_unique_or_null)]
"""A Java ``Set<String>`` that may be null (TDM-09)."""


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


class AtlasModel(BaseModel):
    """The JSON conventions of every Atlas model (TDM-01 to TDM-03, TDM-15, DD-020)."""

    model_config = ConfigDict(
        alias_generator=to_camel,
        validate_by_alias=True,
        validate_by_name=True,
        validate_assignment=True,
        extra="ignore",
        coerce_numbers_to_str=True,
    )

    def to_json(self) -> dict[str, Any]:
        """The JSON Atlas writes for this model: Java names, null fields left out, empty ones kept (TDM-02)."""
        return self.model_dump(mode="json", by_alias=True, exclude_none=True)


class AtlasConstraintDef(AtlasModel):
    """A constraint on an attribute, such as ``ownedRef`` or ``inverseRef``."""

    type: str | None = None
    params: dict[str, Any] | None = None

    def is_constraint_type(self, name: str | None) -> bool:
        """Whether this constraint is of type ``name``, compared without case."""
        return _equal_ignoring_case(name, self.type)

    def get_param(self, name: str) -> Any:  # noqa: ANN401 - Atlas's params are untyped JSON values
        """The value of parameter ``name``, or None."""
        return None if self.params is None else self.params.get(name)


class AtlasAttributeDef(AtlasModel):
    """An attribute of a struct, classification, entity, relationship or business metadata type (TDM-10)."""

    name: str | None = None
    type_name: str | None = None
    is_optional: JavaBool = False
    cardinality: Cardinality | None = Cardinality.SINGLE
    values_min_count: JavaInt = COUNT_NOT_SET
    values_max_count: JavaInt = COUNT_NOT_SET
    is_unique: JavaBool = False
    is_indexable: JavaBool = False
    include_in_notification: JavaBool = False
    default_value: str | None = None
    description: str | None = None
    search_weight: JavaInt = DEFAULT_SEARCH_WEIGHT
    index_type: IndexType | None = None
    constraints: Annotated[list[AtlasConstraintDef] | None, AfterValidator(_null_when_empty)] = None
    options: dict[str, str] | None = None
    display_name: str | None = None

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
    list[AtlasAttributeDef], BeforeValidator(_empty_when_null), AfterValidator(_keep_last_attributes)
]
"""``attributeDefs``: never null, one definition per name (TDM-06, TDM-07)."""


def find_attribute(attributes: Iterable[AtlasAttributeDef], name: str | None) -> AtlasAttributeDef | None:
    """The first attribute definition named ``name``, compared without case, or None (TDM-16)."""
    return next((attribute for attribute in attributes if _equal_ignoring_case(attribute.name, name)), None)


class AtlasBaseTypeDef(AtlasModel):
    """What every type definition has: identity, audit fields, name and options."""

    CATEGORY: ClassVar[TypeCategory]

    guid: str | None = None
    created_by: str | None = None
    updated_by: str | None = None
    create_time: Timestamp | None = None
    update_time: Timestamp | None = None
    version: int | None = None
    name: str | None = None
    description: str | None = None
    type_version: str | None = None
    service_type: str | None = None
    options: dict[str, str] | None = None

    @computed_field
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

    value: str | None = None
    description: str | None = None
    ordinal: int | None = None


def _element_value(element: AtlasEnumElementDef) -> str | None:
    return element.value


def _keep_last_elements(elements: list[AtlasEnumElementDef]) -> list[AtlasEnumElementDef]:
    return _keep_last_by(elements, _element_value)


class AtlasEnumDef(AtlasBaseTypeDef):
    """An enum type."""

    CATEGORY: ClassVar[TypeCategory] = TypeCategory.ENUM

    element_defs: Annotated[
        list[AtlasEnumElementDef], BeforeValidator(_empty_when_null), AfterValidator(_keep_last_elements)
    ] = Field(default_factory=list)
    default_value: str | None = None

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

    attribute_defs: AttributeDefs = Field(default_factory=list)

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

    super_types: NameSet = Field(default_factory=list)
    entity_types: NameSet = Field(default_factory=list)
    sub_types: OptionalNameSet = None
    """Derived from the super types of all classifications; ignored on create and update."""

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

    relationship_type_name: str | None = None
    is_legacy_attribute: JavaBool = False


class AtlasEntityDef(AtlasStructDef):
    """An entity type."""

    CATEGORY: ClassVar[TypeCategory] = TypeCategory.ENTITY

    super_types: NameSet = Field(default_factory=list)
    sub_types: OptionalNameSet = None
    """Derived from the super types of all entity types; ignored on create and update."""
    relationship_attribute_defs: list[AtlasRelationshipAttributeDef] | None = None
    """Derived from the relationship types that refer to this one; ignored on create and update."""
    business_attribute_defs: dict[str, list[AtlasAttributeDef]] | None = None
    """Derived from the business metadata types that apply to this one; ignored on create and update."""

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
    """One end of a relationship type: the entity type there and the attribute it gets (TDM-12)."""

    type: str | None = None
    name: str | None = None
    is_container: JavaBool = False
    cardinality: Cardinality | None = Cardinality.SINGLE
    is_legacy_attribute: JavaBool = False
    description: str | None = None


class AtlasRelationshipDef(AtlasStructDef):
    """A relationship type between two entity types (TDM-12)."""

    CATEGORY: ClassVar[TypeCategory] = TypeCategory.RELATIONSHIP

    relationship_category: RelationshipCategory | None = None
    relationship_label: str | None = None
    propagate_tags: PropagateTags | None = None
    end_def1: AtlasRelationshipEndDef | None = None
    end_def2: AtlasRelationshipEndDef | None = None


class AtlasBusinessMetadataDef(AtlasStructDef):
    """A business metadata type: attributes that apply to the entity types its options name."""

    CATEGORY: ClassVar[TypeCategory] = TypeCategory.BUSINESS_METADATA


class AtlasTypeDefHeader(AtlasModel):
    """The identity of a type definition, as ``/v2/types/typedefs/headers`` lists it."""

    guid: str | None = None
    name: str | None = None
    service_type: str | None = None
    category: TypeCategory | None = None

    @classmethod
    def of(cls, typedef: AtlasBaseTypeDef) -> Self:
        """The header of ``typedef`` (TDM-18)."""
        return cls(guid=typedef.guid, name=typedef.name, service_type=typedef.service_type, category=typedef.category)


def _has_name(typedefs: list[Any] | None, name: str) -> bool:
    return any(typedef.name == name for typedef in typedefs or ())


class AtlasTypesDef(AtlasModel):
    """Type definitions of every kind: the body of ``/v2/types/typedefs`` (TDM-13)."""

    enum_defs: list[AtlasEnumDef] | None = Field(default_factory=list)
    struct_defs: list[AtlasStructDef] | None = Field(default_factory=list)
    classification_defs: list[AtlasClassificationDef] | None = Field(default_factory=list)
    entity_defs: list[AtlasEntityDef] | None = Field(default_factory=list)
    relationship_defs: list[AtlasRelationshipDef] | None = Field(default_factory=list)
    business_metadata_defs: list[AtlasBusinessMetadataDef] | None = Field(default_factory=list)

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
