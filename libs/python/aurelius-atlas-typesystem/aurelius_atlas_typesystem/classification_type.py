"""``AtlasClassificationType``: a classification, its hierarchy and its entity types (THY-06 to THY-08)."""

from typing import TYPE_CHECKING

from aurelius_atlas_model.errors import AtlasError, AtlasErrorCode
from aurelius_atlas_model.typedef import (
    ATLAS_TYPE_DATE,
    ATLAS_TYPE_STRING,
    AtlasAttributeDef,
    AtlasClassificationDef,
)

if TYPE_CHECKING:
    from aurelius_atlas_typesystem.entity_type import EntityType
    from aurelius_atlas_typesystem.registry import TypeRegistry

from aurelius_atlas_typesystem.attribute import AtlasAttribute
from aurelius_atlas_typesystem.entity_type import entity_types_and_all_sub_types
from aurelius_atlas_typesystem.hierarchy_type import HierarchyType
from aurelius_atlas_typesystem.type_names import CLASSIFICATION_ROOT_NAME


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
