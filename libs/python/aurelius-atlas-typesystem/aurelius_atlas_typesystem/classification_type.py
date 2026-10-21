"""``AtlasClassificationType``: a classification, its hierarchy and its entity types (THY-06 to THY-08)."""

import re
from datetime import UTC, datetime, tzinfo
from typing import TYPE_CHECKING

from aurelius_atlas_model.errors import AtlasError, AtlasErrorCode
from aurelius_atlas_model.instance import AtlasClassification, AtlasStruct, TimeBoundary
from aurelius_atlas_model.typedef import (
    ATLAS_TYPE_DATE,
    ATLAS_TYPE_STRING,
    AtlasAttributeDef,
    AtlasClassificationDef,
)

from aurelius_atlas_typesystem.attribute import AtlasAttribute
from aurelius_atlas_typesystem.entity_type import entity_types_and_all_sub_types
from aurelius_atlas_typesystem.hierarchy_type import HierarchyType
from aurelius_atlas_typesystem.java import is_valid_time_zone, time_zone
from aurelius_atlas_typesystem.struct_type import StructValue
from aurelius_atlas_typesystem.type_names import CLASSIFICATION_ROOT_NAME

if TYPE_CHECKING:
    from aurelius_atlas_typesystem.entity_type import EntityType
    from aurelius_atlas_typesystem.registry import TypeRegistry

_TIME_BOUNDARY = re.compile(r"\s*([0-9]+)/\s*([0-9]+)/\s*([0-9]+) \s*([0-9]+):\s*([0-9]+):\s*([0-9]+)")
"""``TimeBoundary.TIME_FORMAT``, ``yyyy/MM/dd HH:mm:ss``, as a strict ``SimpleDateFormat`` reads it."""


class ClassificationType(HierarchyType):
    """A classification type: its hierarchy and the entity types it applies to (THY-01 to THY-05, THY-07)."""

    def __init__(self, classification_def: AtlasClassificationDef) -> None:
        super().__init__(classification_def)
        self.classification_def = classification_def
        self.entity_types: list[str] = []

    def _declared_super_types(self) -> list[str]:
        return self.classification_def.super_types

    def _same_kind(self, registry: TypeRegistry, name: str) -> HierarchyType | None:
        return registry.classification_type(name)

    def _system_attribute(self, name: str) -> AtlasAttribute | None:
        return CLASSIFICATION_ROOT.all_attributes.get(name)

    def can_apply_to_entity_type(self, entity_type: EntityType) -> bool:
        """Whether the classification may be applied to ``entity_type`` (THY-07)."""
        return not self.entity_types or entity_type.type_name in self.entity_types

    def _resolve_references(self, registry: TypeRegistry) -> None:
        super()._resolve_references(registry)
        self.entity_types = []

    def _resolve_references_phase3(self, registry: TypeRegistry) -> None:
        super()._resolve_references_phase3(registry)
        allowed_by_supers: list[str] | None = None
        own = self.classification_def.entity_types
        for super_name in self.all_super_types:
            super_def = registry.typedef_by_name(super_name)
            names = super_def.entity_types if isinstance(super_def, AtlasClassificationDef) else []
            if not names:
                continue
            expanded = entity_types_and_all_sub_types(names, registry)
            allowed_by_supers = (
                expanded if allowed_by_supers is None else [name for name in allowed_by_supers if name in expanded]
            )
            if not allowed_by_supers:
                break
        if allowed_by_supers is None:
            self.entity_types = entity_types_and_all_sub_types(own, registry)
        elif not allowed_by_supers:
            raise AtlasError(AtlasErrorCode.CLASSIFICATIONDEF_PARENTS_ENTITYTYPES_DISJOINT, self.type_name)
        elif not own:
            self.entity_types = allowed_by_supers
        else:
            self.entity_types = entity_types_and_all_sub_types(own, registry)
            if not set(self.entity_types) <= set(allowed_by_supers):
                raise AtlasError(AtlasErrorCode.CLASSIFICATIONDEF_ENTITYTYPES_NOT_PARENTS_SUBSET, self.type_name, own)
        self.classification_def.sub_types = list(self.sub_types)

    def _classification_supers(self) -> list[ClassificationType]:
        return [super_type for super_type in self.super_types if isinstance(super_type, ClassificationType)]

    def create_default_value(self) -> AtlasClassification:
        """A classification of this type with the defaults of its own and inherited mandatory attributes."""
        classification = AtlasClassification(type_name=self.classification_def.name)
        self.populate_default_values(classification)
        return classification

    def is_valid_value(self, value: object) -> bool:
        """Valid for each super type, with valid validity periods, then for its own attributes (EVL-07)."""
        if value is None:
            return True
        if not all(super_type.is_valid_value(value) for super_type in self._classification_supers()):
            return False
        return validate_time_boundaries(value, None) and super().is_valid_value(value)

    def is_valid_value_for_update(self, value: object) -> bool:
        """As ``is_valid_value``, for update (EVL-03, EVL-07)."""
        if value is None:
            return True
        if not all(super_type.is_valid_value_for_update(value) for super_type in self._classification_supers()):
            return False
        return validate_time_boundaries(value, None) and super().is_valid_value_for_update(value)

    def validate_value(self, value: object, name: str, messages: list[str]) -> bool:
        """Validate for each super type, the validity periods, then the own attributes (EVL-07)."""
        if value is None:
            return True
        valid = True
        for super_type in self._classification_supers():
            valid = super_type.validate_value(value, name, messages) and valid
        valid = validate_time_boundaries(value, messages) and valid
        return super().validate_value(value, name, messages) and valid

    def validate_value_for_update(self, value: object, name: str, messages: list[str]) -> bool:
        """As ``validate_value``, for update (EVL-03, EVL-07)."""
        if value is None:
            return True
        valid = True
        for super_type in self._classification_supers():
            valid = super_type.validate_value_for_update(value, name, messages) and valid
        valid = validate_time_boundaries(value, messages) and valid
        return super().validate_value_for_update(value, name, messages) and valid

    def are_equal_values(self, left: object, right: object, guid_assignments: dict[str, str] | None) -> bool:
        """Equal for each super type and for this type (EVL-06)."""
        return all(
            super_type.are_equal_values(left, right, guid_assignments) for super_type in self._classification_supers()
        ) and super().are_equal_values(left, right, guid_assignments)

    def normalize_attribute_values(self, value: StructValue) -> None:
        """Normalise for each super type, then this type's own attributes (EVL-04)."""
        for super_type in self._classification_supers():
            super_type.normalize_attribute_values(value)
        super().normalize_attribute_values(value)

    def normalize_attribute_values_for_update(self, value: StructValue) -> None:
        """As ``normalize_attribute_values``, for update (EVL-03)."""
        for super_type in self._classification_supers():
            super_type.normalize_attribute_values_for_update(value)
        super().normalize_attribute_values_for_update(value)

    def populate_default_values(self, struct: AtlasStruct) -> None:
        """Defaults for each super type's mandatory attributes, then this type's (EVL-05)."""
        for super_type in self._classification_supers():
            super_type.populate_default_values(struct)
        super().populate_default_values(struct)


def validate_time_boundaries(value: object, messages: list[str] | None) -> bool:
    """``validateTimeBoundaries``: each validity period of a classification is valid (EVL-07).

    A map has none: Java reads it with ``AtlasClassification(Map)``, which takes no validity periods. Each message is
    added once.
    """
    if not isinstance(value, AtlasClassification):
        return True
    valid = True
    for period in value.validity_periods or []:
        if period is not None:
            valid = _validate_time_boundary(period, messages) and valid
    return valid


def _validate_time_boundary(period: TimeBoundary, messages: list[str] | None) -> bool:
    valid = True
    zone: tzinfo = UTC
    if period.time_zone:
        if not is_valid_time_zone(period.time_zone):
            valid = _report(messages, AtlasErrorCode.INVALID_TIMEBOUNDRY_TIMEZONE, period.time_zone)
        zone = time_zone(period.time_zone) or UTC
    start = parse_time_boundary(period.start_time, zone) if period.start_time else None
    if period.start_time and start is None:
        valid = _report(messages, AtlasErrorCode.INVALID_TIMEBOUNDRY_START_TIME, period.start_time)
    end = parse_time_boundary(period.end_time, zone) if period.end_time else None
    if period.end_time and end is None:
        valid = _report(messages, AtlasErrorCode.INVALID_TIMEBOUNDRY_END_TIME, period.end_time)
    if start is not None and end is not None and end < start:
        valid = _report(messages, AtlasErrorCode.INVALID_TIMEBOUNDRY_DATERANGE, period.start_time, period.end_time)
    return valid


def _report(messages: list[str] | None, code: AtlasErrorCode, *params: object) -> bool:
    """``addValidationMessageIfNotPresent``; always False, the period being invalid."""
    message = code.message(*params)
    if messages is not None and message not in messages:
        messages.append(message)
    return False


def parse_time_boundary(text: str, zone: tzinfo) -> datetime | None:
    """``DateValidator.validate(text, "yyyy/MM/dd HH:mm:ss", zone)``: strict, the whole text, else None.

    Each number may be preceded by whitespace, as ``SimpleDateFormat`` skips it before a field.
    """
    match = _TIME_BOUNDARY.fullmatch(text)
    if match is None:
        return None
    year, month, day, hour, minute, second = (int(field) for field in match.groups())
    try:
        return datetime(year, month, day, hour, minute, second, tzinfo=zone)
    except ValueError:
        return None


def _root_classification_def() -> AtlasClassificationDef:
    """``initRootClassificationType``: the system attributes of every classification (THY-05)."""
    attributes = [
        ("__typeName", ATLAS_TYPE_STRING),
        ("__timestamp", ATLAS_TYPE_DATE),
        ("__modificationTimestamp", ATLAS_TYPE_DATE),
        ("__modifiedBy", ATLAS_TYPE_STRING),
        ("__createdBy", ATLAS_TYPE_STRING),
        ("__entityStatus", ATLAS_TYPE_STRING),
    ]
    return AtlasClassificationDef(
        name=CLASSIFICATION_ROOT_NAME,
        description="Root classification for system attributes",
        type_version="1.0",
        attribute_defs=[
            AtlasAttributeDef(name=name, type_name=type_name, is_indexable=True) for name, type_name in attributes
        ],
    )


CLASSIFICATION_ROOT = ClassificationType(_root_classification_def())
"""``__CLASSIFICATION_ROOT``; not registered, resolved by every registry (THY-05)."""
