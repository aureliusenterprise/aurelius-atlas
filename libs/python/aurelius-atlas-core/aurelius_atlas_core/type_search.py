"""Searching the registered type definitions with a filter of query parameters (TYR-05 to TYR-08).

Ported from ``TypesREST.getSearchFilter``, ``SearchFilter`` and ``FilterUtil`` of Apache Atlas 2.4.0, and
``AtlasTypeDefGraphStore.searchTypesDef``.
"""

import functools
from collections.abc import Iterable
from dataclasses import dataclass, field

from aurelius_atlas_model.typedef import AtlasBaseTypeDef, AtlasTypeDefHeader, AtlasTypesDef, TypeCategory
from aurelius_atlas_typesystem.registry import TypeRegistry
from aurelius_atlas_typesystem.types import AtlasType, ClassificationType, EntityType

from aurelius_atlas_core.typedef_store import java_compare, types_def_of

PARAM_TYPE = "type"
PARAM_NAME = "name"
PARAM_SUPERTYPE = "supertype"
PARAM_SERVICETYPE = "servicetype"
PARAM_NOT_SUPERTYPE = "notsupertype"
PARAM_NOT_SERVICETYPE = "notservicetype"
PARAM_NOT_NAME = "notname"
"""The filter's parameter names (``SearchFilter.PARAM_*``), compared with case."""

EXCLUDE_INTERNAL = "excludeInternalTypesAndReferences"
"""The parameter that hides ``__internal`` and its sub types, compared without case (TYR-07)."""

TYPE_NAME_INTERNAL = "__internal"
"""The super type of Atlas's internal entity types (``Constants.TYPE_NAME_INTERNAL``)."""

_KINDS = (
    TypeCategory.ENUM,
    TypeCategory.STRUCT,
    TypeCategory.CLASSIFICATION,
    TypeCategory.ENTITY,
    TypeCategory.RELATIONSHIP,
    TypeCategory.BUSINESS_METADATA,
)
_TYPE_PARAM_KINDS = {
    "CLASS": TypeCategory.ENTITY,
    "ENTITY": TypeCategory.ENTITY,
    "TRAIT": TypeCategory.CLASSIFICATION,
    "CLASSIFICATION": TypeCategory.CLASSIFICATION,
    "STRUCT": TypeCategory.STRUCT,
    "ENUM": TypeCategory.ENUM,
    "RELATIONSHIP": TypeCategory.RELATIONSHIP,
    "BUSINESS_METADATA": TypeCategory.BUSINESS_METADATA,
}


@dataclass(frozen=True)
class TypeSearchFilter:
    """The parameters of a type search, each with its values in order (``SearchFilter``)."""

    params: dict[str, list[str]] = field(default_factory=dict)

    @classmethod
    def from_query(cls, items: Iterable[tuple[str, str]]) -> TypeSearchFilter:
        """The filter of a request's query parameters (``getSearchFilter``, TYR-06, TYR-07).

        Each parameter counts with its first value, in the order the parameters first appear;
        ``excludeInternalTypesAndReferences=true`` adds ``notname`` and ``notsupertype`` ``__internal``.
        """
        first: dict[str, str] = {}
        for key, value in items:
            first.setdefault(key, value)
        params: dict[str, list[str]] = {}
        for key, value in first.items():
            if key.lower() == EXCLUDE_INTERNAL.lower() and value.lower() == "true":
                params.setdefault(PARAM_NOT_NAME, []).append(TYPE_NAME_INTERNAL)
                params.setdefault(PARAM_NOT_SUPERTYPE, []).append(TYPE_NAME_INTERNAL)
            else:
                params.setdefault(key, []).append(value)
        return cls(params)

    def param(self, name: str) -> str | None:
        """The first value of parameter ``name`` (``getParam``)."""
        values = self.params.get(name)
        return values[0] if values else None

    def matches(self, type_: AtlasType) -> bool:
        """Whether the filter keeps ``type_`` (``FilterUtil.getPredicateFromSearchFilter``, TYR-06)."""
        checks: list[bool] = []
        if _not_blank(kind := self.param(PARAM_TYPE)):
            checks.append(_TYPE_PARAM_KINDS.get(str(kind).upper()) is type_.category)
        if _not_blank(name := self.param(PARAM_NAME)):
            checks.append(type_.type_name == name)
        if _not_blank(service_type := self.param(PARAM_SERVICETYPE)):
            checks.append(type_.service_type == service_type)
        if _not_blank(super_type := self.param(PARAM_SUPERTYPE)):
            checks.append(_has_super_type(type_, str(super_type)))
        if _not_blank(not_super_type := self.param(PARAM_NOT_SUPERTYPE)):
            checks.append(not _has_super_type(type_, str(not_super_type)))
        if _not_blank(not_service_type := self.param(PARAM_NOT_SERVICETYPE)):
            checks.append(type_.service_type != not_service_type)
        checks.extend(type_.type_name != not_name for not_name in self.params.get(PARAM_NOT_NAME, []))
        return all(checks)


def _not_blank(value: str | None) -> bool:
    return value is not None and value.strip() != ""


def _has_super_type(type_: AtlasType, name: str) -> bool:
    return isinstance(type_, EntityType | ClassificationType) and name in type_.all_super_types


def _compare_names(left: AtlasBaseTypeDef, right: AtlasBaseTypeDef) -> int:
    return java_compare(str(left.name), str(right.name))


_BY_NAME = functools.cmp_to_key(_compare_names)


def search_types_def(registry: TypeRegistry, search_filter: TypeSearchFilter) -> AtlasTypesDef:
    """The registered definitions the filter keeps, each kind sorted by name (``searchTypesDef``, TYR-05, DD-034)."""
    kept: list[AtlasBaseTypeDef] = []
    for kind in _KINDS:
        typedefs = [
            typedef for typedef in registry.typedefs(kind) if search_filter.matches(registry.get_type(typedef.name))
        ]
        kept.extend(sorted(typedefs, key=_BY_NAME))
    return types_def_of(kept)


def type_def_headers(types_def: AtlasTypesDef) -> list[AtlasTypeDefHeader]:
    """The header of each definition, enums first (``AtlasTypeUtil.toTypeDefHeader``, TYR-08)."""
    lists = (
        types_def.enum_defs,
        types_def.struct_defs,
        types_def.classification_defs,
        types_def.entity_defs,
        types_def.relationship_defs,
        types_def.business_metadata_defs,
    )
    return [AtlasTypeDefHeader.of(typedef) for typedefs in lists for typedef in typedefs or []]
