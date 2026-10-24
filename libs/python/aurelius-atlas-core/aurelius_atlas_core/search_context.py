"""``SearchContext``: a basic search's types, checked attributes and marker (SRC-03, SRC-04, SRC-08).

Atlas's ``SearchContext`` with its ``MarkerUtil``, for the entity search of 4.1a (DD-087).
"""

import base64
import binascii
import hashlib
from collections.abc import Iterator

from aurelius_atlas_model import codec
from aurelius_atlas_model.discovery import FilterCriteria, SearchParameters
from aurelius_atlas_model.errors import AtlasError, AtlasErrorCode
from aurelius_atlas_typesystem.classification_type import CLASSIFICATION_ROOT
from aurelius_atlas_typesystem.entity_type import ENTITY_ROOT, EntityType
from aurelius_atlas_typesystem.registry import TypeRegistry

ALL_ENTITY_TYPES = "_ALL_ENTITY_TYPES"
TYPENAME_DELIMITER = ","
MARKER_START = "*"
MARKER_END = -1
MARKER_DELIMITER = ":"
MARKER_WITH_OFFSET = "Marker can be used only if offset=0."
INVALID_MARKER = "Invalid marker!"
NOT_SUPPORTED = "Search by {name} is not supported yet"

_NOT_YET = (("classification", "classification"), ("query", "query"), ("term_name", "termName"))
"""The parameters 4.1b, 4.2 and 5.2 add (DV-46)."""

_HASHED = (
    "query",
    "typeName",
    "classification",
    "termName",
    "includeSubTypes",
    "includeSubClassifications",
    "excludeDeletedEntities",
    "includeClassificationAttributes",
    "excludeHeaderAttributes",
    "limit",
    "offset",
    "entityFilters",
    "tagFilters",
    "attributes",
    "sortBy",
    "sortOrder",
)
"""The fields ``SearchParameters.hashCode`` hashes, which a marker is bound to (DV-45)."""


class SearchContext:
    """The entity types of a search, its attributes checked against them, and the offset its marker names.

    Raises:
        AtlasError: ``UNKNOWN_TYPENAME``, ``UNKNOWN_ATTRIBUTE``, or ``BAD_REQUEST`` for a marker, or a parameter
            not supported yet (DV-46).
    """

    def __init__(self, parameters: SearchParameters, registry: TypeRegistry) -> None:
        self.parameters = parameters
        for field, name in _NOT_YET:
            if getattr(parameters, field):
                raise AtlasError(AtlasErrorCode.BAD_REQUEST, NOT_SUPPORTED.format(name=name))
        self.entity_types = _entity_types(parameters.type_name, registry)
        """The types given, in their order; ``ENTITY_ROOT`` alone for every entity (SRC-03)."""
        for entity_type in self.entity_types:
            for name in [*_filter_attributes(parameters.entity_filters), parameters.sort_by]:
                _check_attribute(entity_type, name)
        self.marker = None if not parameters.marker else decode_marker(parameters)
        self.has_relationship_attributes = self._check_requested_attributes()
        self.type_names = self._type_names(include_sub_types=parameters.include_sub_types)
        self.entity_attributes = [
            name
            for name in dict.fromkeys(_filter_attributes(parameters.entity_filters))
            if not _is_system_attribute(name)
        ]
        """The attributes entity filters name, other than system attributes, answered with the entities (SRC-09)."""

    @property
    def all_entities(self) -> bool:
        """Whether the search is for every entity (``_ALL_ENTITY_TYPES``)."""
        return self.entity_types == [ENTITY_ROOT]

    @property
    def first_type(self) -> EntityType | None:
        """The first type given, the one sorting and requested attributes are of."""
        return self.entity_types[0] if self.entity_types else None

    def exclude_header_attributes(self) -> bool:
        """Whether the answer is a table of the requested attributes rather than headers (SRC-10)."""
        return (
            bool(self.entity_types)
            and self.parameters.exclude_header_attributes
            and bool(self.parameters.attributes)
            and not self.has_relationship_attributes
        )

    def _check_requested_attributes(self) -> bool:
        """Each requested attribute is one of the first type's; whether the last one checked is a relationship's."""
        has_relationship = False
        first = self.first_type
        if first is None:
            return has_relationship
        for name in self.parameters.attributes or []:
            attribute = first.attribute(name)
            if attribute is None:
                attribute = first.relationship_attribute(name)
                has_relationship = attribute is not None
            if attribute is None:
                raise AtlasError(AtlasErrorCode.UNKNOWN_ATTRIBUTE, name, _type_name(first))
        return has_relationship

    def _type_names(self, *, include_sub_types: bool) -> frozenset[str] | None:
        if self.all_entities or not self.entity_types:
            return None
        names: dict[str, None] = {}
        for entity_type in self.entity_types:
            found = entity_type.type_and_all_sub_types if include_sub_types else [entity_type.type_name]
            names.update(dict.fromkeys(str(name) for name in found))
        return frozenset(names)


def _entity_types(type_name: str | None, registry: TypeRegistry) -> list[EntityType]:
    """``getEntityTypes``: the known types of a comma-separated list; ``_ALL_ENTITY_TYPES`` wins (SRC-03).

    Raises:
        AtlasError: ``UNKNOWN_TYPENAME`` when none is known.
    """
    if not type_name:
        return []
    found: dict[str, EntityType] = {}
    for name in type_name.split(TYPENAME_DELIMITER):
        entity_type = ENTITY_ROOT if name == ALL_ENTITY_TYPES else registry.entity_type(name)
        if entity_type is not None:
            found.setdefault(name, entity_type)
    if not found:
        raise AtlasError(AtlasErrorCode.UNKNOWN_TYPENAME, type_name)
    return [ENTITY_ROOT] if ALL_ENTITY_TYPES in found else list(found.values())


def _filter_attributes(criteria: FilterCriteria | None) -> Iterator[str]:
    """The attribute names of a filter, as ``validateAttributes`` and ``processSearchAttributes`` walk it."""
    if criteria is None:
        return
    if criteria.condition is not None and criteria.criterion:
        for child in criteria.criterion:
            yield from _filter_attributes(child)
    elif criteria.attribute_name:
        yield criteria.attribute_name


def _check_attribute(entity_type: EntityType, name: str | None) -> None:
    """``validateAttributes``: a name the type has no attribute of fails (SRC-04)."""
    if name and entity_type.attribute_type(name) is None:
        raise AtlasError(AtlasErrorCode.UNKNOWN_ATTRIBUTE, name, _type_name(entity_type))


def _type_name(entity_type: EntityType | None) -> str:
    return ALL_ENTITY_TYPES if entity_type is ENTITY_ROOT or entity_type is None else str(entity_type.type_name)


def _is_system_attribute(name: str) -> bool:
    """``isSystemAttribute``: one of the entity or the classification root."""
    return name in ENTITY_ROOT.all_attributes or name in CLASSIFICATION_ROOT.all_attributes


def _hash(parameters: SearchParameters) -> int:
    """The hash a marker is bound to: of the fields ``hashCode`` hashes (DV-45)."""
    written = parameters.to_json()
    text = codec.dumps({name: written.get(name) for name in _HASHED})
    return int.from_bytes(hashlib.sha256(text).digest()[:4], "big", signed=True)


def encode_marker(parameters: SearchParameters, next_offset: int | None) -> str | None:
    """``getNextEncMarker``: base64 of ``<hash>:<offset>``, or ``-1`` after the last page (SRC-08)."""
    if next_offset is None:
        return None
    if next_offset == MARKER_END:
        return str(MARKER_END)
    value = f"{_hash(parameters)}{MARKER_DELIMITER}{next_offset}"
    return base64.b64encode(value.encode()).decode()


def decode_marker(parameters: SearchParameters) -> int:
    """``decodeMarker``: the offset a marker names; ``*`` is the start (SRC-08).

    Raises:
        AtlasError: ``BAD_REQUEST`` with an offset above 0, or for a marker not of these parameters.
    """
    if parameters.offset > 0:
        raise AtlasError(AtlasErrorCode.BAD_REQUEST, MARKER_WITH_OFFSET)
    if parameters.marker == MARKER_START:
        return 0
    try:
        hashed, offset = base64.b64decode(str(parameters.marker), validate=True).decode().split(MARKER_DELIMITER)
        if int(hashed) == _hash(parameters) and int(offset) >= 0:
            return int(offset)
    except ValueError, binascii.Error, UnicodeDecodeError:
        pass
    raise AtlasError(AtlasErrorCode.BAD_REQUEST, INVALID_MARKER)
