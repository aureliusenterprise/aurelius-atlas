"""What ``AtlasClassificationType`` and ``AtlasEntityType`` share: super and sub types (THY-01 to THY-05)."""

from typing import TYPE_CHECKING

from aurelius_atlas_model.errors import AtlasError, AtlasErrorCode
from aurelius_atlas_model.typedef import (
    AtlasStructDef,
)

if TYPE_CHECKING:
    from aurelius_atlas_typesystem.registry import TypeRegistry

from aurelius_atlas_typesystem.attribute import AtlasAttribute
from aurelius_atlas_typesystem.struct_type import StructType


class HierarchyType(StructType):
    """What entity and classification types share: super and sub types, inherited attributes (THY-01 to THY-04)."""

    def __init__(self, struct_def: AtlasStructDef) -> None:
        super().__init__(struct_def)
        self.super_types: list[HierarchyType] = []
        self.all_super_types: list[str] = []
        self.sub_types: list[str] = []
        self.all_sub_types: list[str] = []
        self.type_and_all_sub_types: list[str] = []
        self.type_and_all_super_types: list[str] = []

    def _declared_super_types(self) -> list[str]:
        raise NotImplementedError  # pragma: no cover - every kind overrides it

    def _same_kind(self, registry: TypeRegistry, name: str) -> HierarchyType | None:
        raise NotImplementedError  # pragma: no cover - every kind overrides it

    def is_super_type_of(self, other: StructType | str | None) -> bool:
        """Whether ``other`` is among this type's sub types, at any depth (THY-04)."""
        return name_of(other) in self.all_sub_types

    def is_sub_type_of(self, other: StructType | str | None) -> bool:
        """Whether ``other`` is among this type's super types, at any depth (THY-04)."""
        return name_of(other) in self.all_super_types

    def _resolve_references(self, registry: TypeRegistry) -> None:
        super()._resolve_references(registry)
        all_super_types: dict[str, None] = {}
        all_attributes: dict[str, AtlasAttribute] = {}
        self._collect_hierarchy(registry, all_super_types, all_attributes, {}, [])
        supers: list[HierarchyType] = []
        for name in self._declared_super_types():
            super_type = registry.get_type(name)
            if not isinstance(super_type, type(self)):
                raise AtlasError(AtlasErrorCode.INCOMPATIBLE_SUPERTYPE, name, self.type_name)
            supers.append(super_type)
        self.super_types = supers
        self.all_super_types = list(all_super_types)
        self.all_attributes = all_attributes
        self.unique_attributes = {
            name: attribute for name, attribute in all_attributes.items() if attribute.attribute_def.is_unique
        }
        self.sub_types = []
        self.all_sub_types = []
        self.type_and_all_sub_types = [str(self.type_name)]
        self.type_and_all_super_types = [*self.all_super_types, str(self.type_name)]

    def _collect_hierarchy(
        self,
        registry: TypeRegistry,
        all_super_types: dict[str, None],
        all_attributes: dict[str, AtlasAttribute],
        owners: dict[str, str],
        visited: list[str],
    ) -> None:
        """``collectTypeHierarchyInfo``: super types first, depth first, then this type's own attributes."""
        name = str(self.struct_def.name)
        if name in visited:
            raise AtlasError(AtlasErrorCode.CIRCULAR_REFERENCE, name, visited)
        declared = self._declared_super_types()
        if declared:
            visited.append(name)
            for super_name in declared:
                super_type = self._same_kind(registry, super_name)
                if super_type is not None:
                    super_type._collect_hierarchy(registry, all_super_types, all_attributes, owners, visited)  # noqa: SLF001
            visited.remove(name)
            all_super_types.update(dict.fromkeys(declared))
        for attribute_def in self.struct_def.attribute_defs:
            attribute_name = str(attribute_def.name)
            attribute_type = registry.get_type(attribute_def.type_name)
            if owners.get(attribute_name, name) != name:
                raise AtlasError(
                    AtlasErrorCode.ATTRIBUTE_NAME_ALREADY_EXISTS_IN_ANOTHER_PARENT_TYPE,
                    name,
                    attribute_name,
                    owners[attribute_name],
                )
            all_attributes[attribute_name] = AtlasAttribute(self, attribute_def, attribute_type)
            owners[attribute_name] = name

    def _resolve_references_phase2(self, registry: TypeRegistry) -> None:
        super()._resolve_references_phase2(registry)
        for super_type in self.super_types:
            super_type.sub_types = _with(super_type.sub_types, str(self.type_name))
        for super_name in self.all_super_types:
            super_type = self._same_kind(registry, super_name)
            if super_type is not None:
                super_type.all_sub_types = _with(super_type.all_sub_types, str(self.type_name))
                super_type.type_and_all_sub_types = _with(super_type.type_and_all_sub_types, str(self.type_name))


def name_of(other: StructType | str | None) -> str | None:
    """The name of a type, or the name itself."""
    return other.type_name if isinstance(other, StructType) else other


def _with(names: list[str], name: str) -> list[str]:
    return names if name in names else [*names, name]
