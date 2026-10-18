"""The type registry and its transient copy (``AtlasTypeRegistry``, TRG-01 to TRG-09, DD-024).

Readers use a ``TypeRegistry``. Writers take a ``TransientTypeRegistry`` from ``lock_for_update``, change it,
and release it with or without committing; until the commit, readers see the registry as it was.
"""

import threading
from collections.abc import Iterable, Iterator
from contextlib import contextmanager
from typing import Self

from aurelius_atlas_model.errors import AtlasError, AtlasErrorCode
from aurelius_atlas_model.typedef import (
    ATLAS_TYPE_BIGDECIMAL,
    ATLAS_TYPE_BIGINTEGER,
    ATLAS_TYPE_BOOLEAN,
    ATLAS_TYPE_BYTE,
    ATLAS_TYPE_DATE,
    ATLAS_TYPE_DOUBLE,
    ATLAS_TYPE_FLOAT,
    ATLAS_TYPE_INT,
    ATLAS_TYPE_LONG,
    ATLAS_TYPE_SHORT,
    ATLAS_TYPE_STRING,
    AtlasBaseTypeDef,
    AtlasTypesDef,
    TypeCategory,
)

from aurelius_atlas_typesystem.types import (
    CLASSIFICATION_ROOT,
    ENTITY_ROOT,
    ArrayType,
    AtlasType,
    BuiltInType,
    BusinessMetadataType,
    ClassificationType,
    EntityType,
    EnumType,
    MapType,
    ObjectIdType,
    RelationshipType,
    StructType,
    type_of,
)

DEFAULT_LOCK_TIMEOUT_SECONDS = 15.0
"""Atlas's ``atlas.server.type.update.lock.max.wait.time.seconds`` default."""

_BUILT_IN_TYPE_NAMES = (
    ATLAS_TYPE_BOOLEAN,
    ATLAS_TYPE_BYTE,
    ATLAS_TYPE_SHORT,
    ATLAS_TYPE_INT,
    ATLAS_TYPE_LONG,
    ATLAS_TYPE_FLOAT,
    ATLAS_TYPE_DOUBLE,
    ATLAS_TYPE_BIGINTEGER,
    ATLAS_TYPE_BIGDECIMAL,
    ATLAS_TYPE_DATE,
    ATLAS_TYPE_STRING,
)

_KINDS = (
    TypeCategory.ENUM,
    TypeCategory.STRUCT,
    TypeCategory.CLASSIFICATION,
    TypeCategory.ENTITY,
    TypeCategory.RELATIONSHIP,
    TypeCategory.BUSINESS_METADATA,
)
"""The categories of definitions, in the order Atlas walks them."""


class _Definitions:
    """Every definition and type, by name and GUID (``TypeCache`` and ``TypeDefCache``)."""

    def __init__(self) -> None:
        self.types_by_name: dict[str, AtlasType] = {name: BuiltInType(name) for name in _BUILT_IN_TYPE_NAMES}
        self.types_by_name[ObjectIdType().type_name or ""] = ObjectIdType()
        self.types_by_guid: dict[str, AtlasType] = {}
        self.service_types: set[str] = {"atlas_core"}
        self.defs_by_name: dict[TypeCategory, dict[str, AtlasBaseTypeDef]] = {kind: {} for kind in _KINDS}
        self.defs_by_guid: dict[TypeCategory, dict[str, AtlasBaseTypeDef]] = {kind: {} for kind in _KINDS}
        self.kind_types: dict[TypeCategory, dict[str, AtlasType]] = {kind: {} for kind in _KINDS}

    def add(self, typedef: AtlasBaseTypeDef) -> None:
        kind = typedef.category
        type_ = type_of(typedef)
        if typedef.guid:
            self.defs_by_guid[kind][typedef.guid] = typedef
            self.types_by_guid[typedef.guid] = type_
        if typedef.name:
            self.defs_by_name[kind][typedef.name] = typedef
            self.kind_types[kind][typedef.name] = type_
            self.types_by_name[typedef.name] = type_
        if type_.service_type:
            self.service_types.add(type_.service_type)

    def remove_by_name(self, kind: TypeCategory, name: str | None) -> None:
        if name is None:
            return
        typedef = self.defs_by_name[kind].pop(name, None)
        self.kind_types[kind].pop(name, None)
        self.types_by_name.pop(name, None)
        if typedef is not None and typedef.guid is not None:
            self.defs_by_guid[kind].pop(typedef.guid, None)
            self.types_by_guid.pop(typedef.guid, None)

    def remove_by_guid(self, kind: TypeCategory, guid: str) -> None:
        typedef = self.defs_by_guid[kind].pop(guid, None)
        self.types_by_guid.pop(guid, None)
        if typedef is not None and typedef.name is not None:
            self.defs_by_name[kind].pop(typedef.name, None)
            self.kind_types[kind].pop(typedef.name, None)
            self.types_by_name.pop(typedef.name, None)

    def typedef_by_name(self, name: str | None) -> AtlasBaseTypeDef | None:
        return next((defs[name] for defs in self.defs_by_name.values() if name in defs), None)

    def typedef_by_guid(self, guid: str | None) -> AtlasBaseTypeDef | None:
        return next((defs[guid] for defs in self.defs_by_guid.values() if guid in defs), None)


class TypeRegistry:
    """The resolved types of the server (``AtlasTypeRegistry``)."""

    def __init__(self, lock_timeout: float = DEFAULT_LOCK_TIMEOUT_SECONDS) -> None:
        self._data = _Definitions()
        self._lock = threading.RLock()
        self._lock_timeout = lock_timeout
        self._under_update: TransientTypeRegistry | None = None
        self._holds = 0
        ENTITY_ROOT._resolve_references(self)  # noqa: SLF001 - every registry resolves the root types, as Java's does
        CLASSIFICATION_ROOT._resolve_references(self)  # noqa: SLF001

    def is_registered(self, type_name: str | None) -> bool:
        """Whether ``type_name`` is a registered type; built array and map names are not (TRG-04)."""
        return type_name in self._data.types_by_name

    def get_type(self, type_name: str | None) -> AtlasType:
        """The type named ``type_name``, building ``array<T>`` and ``map<K,V>`` types on demand (TRG-02, TRG-03).

        Raises:
            AtlasError: ``TYPE_NAME_NOT_FOUND`` when the name, or an element, key or value name, is unknown.
        """
        if type_name is not None and (registered := self._data.types_by_name.get(type_name)) is not None:
            return registered
        built: AtlasType
        if type_name is not None and type_name.startswith("array<") and type_name.endswith(">"):
            built = ArrayType(type_name.removeprefix("array<").removesuffix(">"))
        elif type_name is not None and type_name.startswith("map<") and type_name.endswith(">"):
            key, _, value = type_name.removeprefix("map<").removesuffix(">").partition(",")
            built = MapType(key, value)
        else:
            raise AtlasError(AtlasErrorCode.TYPE_NAME_NOT_FOUND, type_name)
        built._resolve_references(self)  # noqa: SLF001 - a type resolves against its registry
        return built

    def get_type_by_guid(self, guid: str | None) -> AtlasType:
        """The type whose definition has ``guid`` (TRG-03).

        Raises:
            AtlasError: ``TYPE_GUID_NOT_FOUND`` when no definition has it.
        """
        type_ = None if guid is None else self._data.types_by_guid.get(guid)
        if type_ is None:
            raise AtlasError(AtlasErrorCode.TYPE_GUID_NOT_FOUND, guid)
        return type_

    def all_type_names(self) -> list[str]:
        """Every registered type name, built-in ones included (TRG-04)."""
        return list(self._data.types_by_name)

    def all_types(self) -> list[AtlasType]:
        """Every registered type (TRG-04)."""
        return list(self._data.types_by_name.values())

    def all_service_types(self) -> set[str]:
        """The service types of every registered type (TRG-04)."""
        return set(self._data.service_types)

    def typedef_by_name(self, name: str | None) -> AtlasBaseTypeDef | None:
        """The definition named ``name``, of any kind (TRG-04)."""
        return self._data.typedef_by_name(name)

    def typedef_by_guid(self, guid: str | None) -> AtlasBaseTypeDef | None:
        """The definition with ``guid``, of any kind (TRG-04)."""
        return self._data.typedef_by_guid(guid)

    def typedefs(self, kind: TypeCategory) -> list[AtlasBaseTypeDef]:
        """The definitions of one kind, such as every ``ENTITY`` definition (TRG-04)."""
        return list(self._data.defs_by_name[kind].values())

    def typedef_names(self, kind: TypeCategory) -> list[str]:
        """The names of the definitions of one kind (TRG-04)."""
        return list(self._data.defs_by_name[kind])

    def types(self, kind: TypeCategory) -> list[AtlasType]:
        """The types of one kind (TRG-04)."""
        return list(self._data.kind_types[kind].values())

    def enum_type(self, name: str | None) -> EnumType | None:
        """The enum type named ``name``, or None (TRG-04)."""
        return _of_kind(self._kind_type(TypeCategory.ENUM, name), EnumType)

    def struct_type(self, name: str | None) -> StructType | None:
        """The struct type named ``name``, or None (TRG-04)."""
        return _of_kind(self._kind_type(TypeCategory.STRUCT, name), StructType)

    def classification_type(self, name: str | None) -> ClassificationType | None:
        """The classification type named ``name``, or None (TRG-04)."""
        return _of_kind(self._kind_type(TypeCategory.CLASSIFICATION, name), ClassificationType)

    def entity_type(self, name: str | None) -> EntityType | None:
        """The entity type named ``name``, or None (TRG-04)."""
        return _of_kind(self._kind_type(TypeCategory.ENTITY, name), EntityType)

    def relationship_type(self, name: str | None) -> RelationshipType | None:
        """The relationship type named ``name``, or None (TRG-04)."""
        return _of_kind(self._kind_type(TypeCategory.RELATIONSHIP, name), RelationshipType)

    def business_metadata_type(self, name: str | None) -> BusinessMetadataType | None:
        """The business metadata type named ``name``, or None (TRG-04)."""
        return _of_kind(self._kind_type(TypeCategory.BUSINESS_METADATA, name), BusinessMetadataType)

    def _kind_type(self, kind: TypeCategory, name: str | None) -> AtlasType | None:
        return None if name is None else self._data.kind_types[kind].get(name)

    def lock_for_update(self, timeout: float | None = None) -> TransientTypeRegistry:
        """Take the update lock and a transient copy of this registry to change (TRG-05).

        The lock is re-entrant: a thread that holds it gets the same copy again.

        Raises:
            AtlasError: ``FAILED_TO_OBTAIN_TYPE_UPDATE_LOCK`` when the lock is not free within the timeout.
        """
        if not self._lock.acquire(timeout=self._lock_timeout if timeout is None else timeout):
            raise AtlasError(AtlasErrorCode.FAILED_TO_OBTAIN_TYPE_UPDATE_LOCK)
        self._holds += 1
        if self._under_update is None:
            self._under_update = TransientTypeRegistry.copy_of(self)
        return self._under_update

    def release(self, transient: TransientTypeRegistry, *, commit: bool) -> None:
        """Release the update lock; on the last release, make the copy's types the registry's when ``commit``.

        A copy that is not the one handed out is not committed (TRG-05).
        """
        try:
            if self._holds == 1:
                if commit and transient is self._under_update:
                    self._data = transient._data  # noqa: SLF001 - the copy hands its types over
                self._under_update = None
            self._holds -= 1
        finally:
            self._lock.release()

    @contextmanager
    def update(self, timeout: float | None = None) -> Iterator[TransientTypeRegistry]:
        """Change the registry: commit when the block ends normally, discard when it raises (TRG-05, TRG-09)."""
        transient = self.lock_for_update(timeout)
        try:
            yield transient
        except BaseException:
            self.release(transient, commit=False)
            raise
        self.release(transient, commit=True)


def _of_kind[T: AtlasType](type_: AtlasType | None, kind: type[T]) -> T | None:
    return type_ if isinstance(type_, kind) else None


type _TypedefLists = Iterable[Iterable[AtlasBaseTypeDef] | None]


def _lists_of(types_def: AtlasTypesDef) -> _TypedefLists:
    return (
        types_def.enum_defs,
        types_def.struct_defs,
        types_def.classification_defs,
        types_def.entity_defs,
        types_def.relationship_defs,
        types_def.business_metadata_defs,
    )


class TransientTypeRegistry(TypeRegistry):
    """A copy of a registry that changes and resolves before it is committed (``AtlasTransientTypeRegistry``)."""

    def __init__(self) -> None:
        super().__init__()
        self.added: list[AtlasBaseTypeDef] = []
        self.updated: list[AtlasBaseTypeDef] = []
        self.deleted: list[AtlasBaseTypeDef] = []

    @classmethod
    def copy_of(cls, registry: TypeRegistry) -> Self:
        """A copy holding the registry's definitions as new, unresolved types (TRG-05)."""
        transient = cls()
        for kind in _KINDS:
            for typedef in registry.typedefs(kind):
                transient._data.add(typedef)
        return transient

    def clear(self) -> None:
        """Drop every definition, keeping the built-in types (``AtlasTransientTypeRegistry.clear``)."""
        self._data = _Definitions()

    def add_type(self, typedef: AtlasBaseTypeDef | None) -> None:
        """Add a definition, then resolve every type (TRG-06, TRG-09)."""
        if typedef is not None:
            self._add(typedef)
        self._resolve()

    def add_types(self, typedefs: Iterable[AtlasBaseTypeDef] | AtlasTypesDef | None) -> None:
        """Add definitions, then resolve every type (TRG-06, TRG-09)."""
        for typedef in self._flatten(typedefs):
            self._add(typedef)
        self._resolve()

    def update_type(self, typedef: AtlasBaseTypeDef | None) -> None:
        """Replace the definition with ``typedef``'s GUID, else its name, then resolve (TRG-07, TRG-09)."""
        if typedef is not None:
            self._update(typedef)
        self._resolve()

    def update_type_by_guid(self, guid: str | None, typedef: AtlasBaseTypeDef | None) -> None:
        """Replace the definition with ``guid`` by ``typedef``, then resolve (TRG-07, TRG-09)."""
        if guid is not None and typedef is not None:
            self._replace_by_guid(guid, typedef)
        self._resolve()

    def update_type_by_name(self, name: str | None, typedef: AtlasBaseTypeDef | None) -> None:
        """Replace the definition named ``name`` by ``typedef``, then resolve (TRG-07, TRG-09)."""
        if name is not None and typedef is not None:
            self._replace_by_name(name, typedef)
        self._resolve()

    def update_types(self, typedefs: Iterable[AtlasBaseTypeDef] | AtlasTypesDef | None) -> None:
        """Replace each definition by GUID, else by name, then resolve (TRG-07, TRG-09)."""
        for typedef in self._flatten(typedefs):
            self._update(typedef)
        self._resolve()

    def update_types_without_resolving(self, typedefs: Iterable[AtlasBaseTypeDef] | AtlasTypesDef | None) -> None:
        """Replace each definition by GUID, else by name, and leave resolving to the next change (MDL-03).

        ``updateTypesWithNoRefResolve``: ``createUpdateTypesDef`` replaces the updated definitions first, so
        that the definitions it then creates resolve against them.
        """
        for typedef in self._flatten(typedefs):
            self._update(typedef)

    def remove_types(self, types_def: AtlasTypesDef | None) -> None:
        """Remove each definition by its GUID when it has one, else by its name, then resolve (TRG-08, TRG-09)."""
        if types_def is not None and not types_def.is_empty():
            for typedef in self._flatten(types_def):
                if typedef.guid:
                    self._data.remove_by_guid(typedef.category, typedef.guid)
                else:
                    self._data.remove_by_name(typedef.category, typedef.name)
                self.deleted.append(typedef)
        self._resolve()

    def remove_type_by_guid(self, guid: str | None) -> None:
        """Remove the definition with ``guid``, then resolve (TRG-08, TRG-09)."""
        typedef = self.typedef_by_guid(guid)
        if typedef is not None and guid is not None:
            self._data.remove_by_guid(typedef.category, guid)
        self._resolve()
        if typedef is not None:
            self.deleted.append(typedef)

    def remove_type_by_name(self, name: str | None) -> None:
        """Remove the definition named ``name``, then resolve (TRG-08, TRG-09)."""
        typedef = self.typedef_by_name(name)
        if typedef is not None:
            self._data.remove_by_name(typedef.category, name)
        self._resolve()
        if typedef is not None:
            self.deleted.append(typedef)

    def _add(self, typedef: AtlasBaseTypeDef) -> None:
        self._data.add(typedef)
        self.added.append(typedef)

    def _update(self, typedef: AtlasBaseTypeDef) -> None:
        if typedef.guid and typedef.guid.strip():
            self._replace_by_guid(typedef.guid, typedef)
        elif typedef.name and typedef.name.strip():
            self._replace_by_name(typedef.name, typedef)

    def _replace_by_guid(self, guid: str, typedef: AtlasBaseTypeDef) -> None:
        self._data.remove_by_guid(typedef.category, guid)
        self._data.add(typedef)
        self.updated.append(typedef)

    def _replace_by_name(self, name: str, typedef: AtlasBaseTypeDef) -> None:
        self._data.remove_by_name(typedef.category, name)
        self._data.add(typedef)
        self.updated.append(typedef)

    @staticmethod
    def _flatten(typedefs: Iterable[AtlasBaseTypeDef] | AtlasTypesDef | None) -> list[AtlasBaseTypeDef]:
        if typedefs is None:
            return []
        if isinstance(typedefs, AtlasTypesDef):
            return [typedef for typedef_list in _lists_of(typedefs) for typedef in typedef_list or ()]
        return list(typedefs)

    def _resolve(self) -> None:
        types = list(self._data.types_by_name.values())
        for type_ in types:
            type_._resolve_references(self)  # noqa: SLF001 - the registry drives resolution
        for type_ in types:
            type_._resolve_references_phase2(self)  # noqa: SLF001
        for type_ in types:
            type_._resolve_references_phase3(self)  # noqa: SLF001
