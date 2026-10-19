"""The typedef store: type definitions kept in Elasticsearch and served from the registry (TDS-01 to TDS-13).

Ported from ``AtlasTypeDefGraphStore`` and its def stores (``Atlas*DefStoreV2``) of Apache Atlas 2.4.0. A change
is tried on the registry's transient copy, checked as Atlas's def stores check it, written as one document
(DD-028) and only then committed to the registry (TDS-10). The document also holds the record of each typedef
patch, written with the patch's change (DD-031).
"""

import asyncio
import json
import re
import time
from collections.abc import Awaitable, Callable, Iterable
from dataclasses import dataclass, field
from datetime import UTC, datetime

from aurelius_atlas_model.errors import AtlasError, AtlasErrorCode
from aurelius_atlas_model.patches import TYPEDEF_PATCH_TYPE, AtlasPatch, PatchStatus
from aurelius_atlas_model.typedef import (
    ATLAS_BUILTIN_TYPES,
    ATTR_OPTION_APPLICABLE_ENTITY_TYPES,
    CONSTRAINT_TYPE_OWNED_REF,
    AtlasAttributeDef,
    AtlasBaseTypeDef,
    AtlasBusinessMetadataDef,
    AtlasClassificationDef,
    AtlasEntityDef,
    AtlasEnumDef,
    AtlasRelationshipDef,
    AtlasRelationshipEndDef,
    AtlasStructDef,
    AtlasTypesDef,
    TypeCategory,
)
from aurelius_atlas_typesystem.registry import TransientTypeRegistry, TypeRegistry
from aurelius_atlas_typesystem.types import RelationshipType, StructType

from aurelius_atlas_core.stored_form import (
    LEGACY_KIND,
    java_end_string,
    stamp_created,
    stamp_updated,
    stored_typedef,
)
from aurelius_atlas_core.typedef_document import (
    DocumentVersion,
    StoredTypedefs,
    TypedefDocument,
    VersionConflictError,
)

DEFAULT_REFRESH_SECONDS = 5.0
"""How long a process answers from its registry before it checks for another process's change (DD-029)."""

_NAME = re.compile(r"(__)?[a-zA-Z][a-zA-Z0-9_ ]*")
_KINDS = (
    TypeCategory.ENUM,
    TypeCategory.STRUCT,
    TypeCategory.CLASSIFICATION,
    TypeCategory.ENTITY,
    TypeCategory.RELATIONSHIP,
    TypeCategory.BUSINESS_METADATA,
)
_NOT_FOUND = {AtlasErrorCode.TYPE_NAME_NOT_FOUND, AtlasErrorCode.TYPE_GUID_NOT_FOUND}
_LIST_FIELD = {
    TypeCategory.ENUM: "enum_defs",
    TypeCategory.STRUCT: "struct_defs",
    TypeCategory.CLASSIFICATION: "classification_defs",
    TypeCategory.ENTITY: "entity_defs",
    TypeCategory.RELATIONSHIP: "relationship_defs",
    TypeCategory.BUSINESS_METADATA: "business_metadata_defs",
}

ADD_MANDATORY_ATTRIBUTE = "ADD_MANDATORY_ATTRIBUTE"
"""The patch action under which an update may add mandatory attributes (``TYPEDEF_PATCH_ADD_MANDATORY_ATTRIBUTE``)."""

_DONE = {PatchStatus.APPLIED, PatchStatus.SKIPPED}

type TypeUsage = Callable[[str], Awaitable[bool]]
"""Whether entities, classifications or relationships of a type exist (DD-030)."""


async def never_in_use(_type_name: str) -> bool:
    """The type usage until the entity store exists (2.2): no type is in use (DD-030)."""
    return False


def is_valid_name(name: str | None) -> bool:
    """A letter, then letters, digits, spaces or ``_``; optionally after ``__`` (``isValidName``, TDS-02)."""
    return name is not None and _NAME.fullmatch(name) is not None


def referenced_type_names(type_name: str | None) -> list[str]:
    """The type names inside ``array<…>`` and ``map<…,…>`` (``AtlasTypeUtil.getReferencedTypeNames``, TDS-04)."""
    if not type_name:
        return []
    if type_name.startswith("array<") and type_name.endswith(">"):
        return referenced_type_names(type_name.removeprefix("array<").removesuffix(">"))
    if type_name.startswith("map<") and type_name.endswith(">"):
        key, _, value = type_name.removeprefix("map<").removesuffix(">").partition(",")
        return referenced_type_names(key) + referenced_type_names(value)
    return [type_name]


def _of_kind(types_def: AtlasTypesDef, kind: TypeCategory) -> list[AtlasBaseTypeDef]:
    return list(getattr(types_def, _LIST_FIELD[kind]) or [])


def types_def_of(typedefs: Iterable[AtlasBaseTypeDef]) -> AtlasTypesDef:
    """An ``AtlasTypesDef`` holding ``typedefs``, each in the list of its kind."""
    result = AtlasTypesDef()
    for typedef in typedefs:
        match typedef:
            case AtlasEnumDef():
                result.enum_defs = [*(result.enum_defs or []), typedef]
            case AtlasClassificationDef():
                result.classification_defs = [*(result.classification_defs or []), typedef]
            case AtlasEntityDef():
                result.entity_defs = [*(result.entity_defs or []), typedef]
            case AtlasRelationshipDef():
                result.relationship_defs = [*(result.relationship_defs or []), typedef]
            case AtlasBusinessMetadataDef():
                result.business_metadata_defs = [*(result.business_metadata_defs or []), typedef]
            case AtlasStructDef():
                result.struct_defs = [*(result.struct_defs or []), typedef]
            case _:  # pragma: no cover - every typedef class is matched above
                raise TypeError(typedef)
    return result


def _all(types_def: AtlasTypesDef) -> list[AtlasBaseTypeDef]:
    return [typedef for kind in _KINDS for typedef in _of_kind(types_def, kind)]


def _without_derived(typedef: AtlasBaseTypeDef) -> AtlasBaseTypeDef:
    """The definition without what the registry derives (sub types, relationship and business attributes)."""
    update: dict[str, None] = {}
    if isinstance(typedef, AtlasClassificationDef | AtlasEntityDef):
        update["sub_types"] = None
    if isinstance(typedef, AtlasEntityDef):
        update["relationship_attribute_defs"] = None
        update["business_attribute_defs"] = None
    return typedef.model_copy(update=update, deep=True) if update else typedef


def rectify(types_def: AtlasTypesDef) -> AtlasTypesDef:
    """Repair what older stores allowed, as ``rectifyTypeErrorsIfAny`` does on load (TDS-12).

    A second struct, classification or entity definition with the same name is dropped, and an ``ownedRef``
    constraint on an attribute that refers to no entity type is removed.
    """
    entity_names = {entity.name for entity in types_def.entity_defs or []}
    result = types_def.model_copy(deep=True)
    for kind in (TypeCategory.STRUCT, TypeCategory.CLASSIFICATION, TypeCategory.ENTITY):
        kept: list[AtlasBaseTypeDef] = []
        names: set[str | None] = set()
        for typedef in _of_kind(result, kind):
            if isinstance(typedef, AtlasStructDef):
                for attribute in typedef.attribute_defs:
                    owned = [c for c in attribute.constraints or [] if c.is_constraint_type(CONSTRAINT_TYPE_OWNED_REF)]
                    if owned and not entity_names & set(referenced_type_names(attribute.type_name)):
                        attribute.constraints = [c for c in attribute.constraints or [] if c not in owned]
            if typedef.name not in names:
                names.add(typedef.name)
                kept.append(typedef)
        setattr(result, _LIST_FIELD[kind], kept)
    return result


def java_compare(left: str, right: str) -> int:
    """Compare as Java's ``String.compareTo`` does: by UTF-16 code unit (MDL-01, MDL-02)."""
    left_units, right_units = left.encode("utf-16-be"), right.encode("utf-16-be")
    return (left_units > right_units) - (left_units < right_units)


def is_newer_version(new: str | None, old: str | None) -> bool:
    """``ObjectUtils.compare(new, old) > 0``: compared as strings, an absent version less than any (MDL-02)."""
    if new is None:
        return False
    return old is None or java_compare(new, old) > 0


def types_to_create(types_def: AtlasTypesDef, registry: TypeRegistry) -> AtlasTypesDef:
    """The definitions whose name is not registered, as any kind or built-in (``getTypesToCreate``, MDL-02)."""
    return types_def_of(typedef for typedef in _all(types_def) if not registry.is_registered(typedef.name))


def types_to_update(types_def: AtlasTypesDef, registry: TypeRegistry, *, check_type_version: bool) -> AtlasTypesDef:
    """The definitions registered as the same kind, when newer (``getTypesToUpdate``, MDL-02).

    With ``check_type_version``, only those whose ``typeVersion`` is greater than the registered one. Each keeps
    the registered attributes, or an enum the registered elements, that it lacks.
    """
    result: list[AtlasBaseTypeDef] = []
    for kind in _KINDS:
        for new in _of_kind(types_def, kind):
            old = registry.typedef_by_name(new.name)
            if old is None or old.category is not kind:
                continue
            if check_type_version and not is_newer_version(new.type_version, old.type_version):
                continue
            result.append(_keeping_registered(new.model_copy(deep=True), old))
    return types_def_of(result)


def _keeping_registered(update: AtlasBaseTypeDef, old: AtlasBaseTypeDef) -> AtlasBaseTypeDef:
    """``updateTypeAttributes`` and the enum's elements: what ``old`` has and ``update`` lacks is appended."""
    if isinstance(update, AtlasEnumDef) and isinstance(old, AtlasEnumDef):
        for element in old.element_defs:
            if not update.has_element(element.value):
                update.add_element(element)
    elif isinstance(update, AtlasStructDef) and isinstance(old, AtlasStructDef):
        for attribute in old.attribute_defs:
            if not update.has_attribute(attribute.name):
                update.add_attribute(attribute)
    return update


@dataclass
class PatchChange:
    """What a typedef patch decided (MDL-07): its status, and the definitions it updates, if any.

    ``patching`` names the action when the update runs "in type patching" (``RequestContext.isInTypePatching``):
    attributes may then be removed, a relationship's category may change and its ends may swap, and under
    ``ADD_MANDATORY_ATTRIBUTE`` mandatory attributes may be added (MDL-10, MDL-11).
    """

    status: PatchStatus
    update: AtlasTypesDef | None = None
    patching: str | None = None


@dataclass
class _Stored:
    """The stored definitions by name, in the order they were stored, and the patch records by id."""

    by_name: dict[str, AtlasBaseTypeDef] = field(default_factory=dict)
    patches: dict[str, AtlasPatch] = field(default_factory=dict)

    @classmethod
    def of(cls, stored: StoredTypedefs) -> _Stored:
        return cls(
            {str(typedef.name): typedef for typedef in _all(stored.types_def)},
            {str(patch.id): patch for patch in stored.patches if patch.id},
        )

    def copy(self) -> _Stored:
        return _Stored(dict(self.by_name), dict(self.patches))

    def record(self, patch: AtlasPatch, status: PatchStatus, now: datetime) -> None:
        """Record how ``patch`` ended, keeping an existing record's created time (``register``, MDL-06)."""
        millis = int(now.timestamp() * 1000)
        existing = self.patches.get(str(patch.id))
        self.patches[str(patch.id)] = patch.model_copy(
            update={
                "type": TYPEDEF_PATCH_TYPE,
                "status": status,
                "created_time": existing.created_time if existing is not None else millis,
                "updated_time": millis,
            }
        )

    def find(self, kind: TypeCategory, guid: str | None, name: str | None) -> AtlasBaseTypeDef | None:
        """The stored definition of ``kind`` with ``guid`` when it is not blank, else named ``name``."""
        if guid and guid.strip():
            return next((d for d in self.by_name.values() if d.guid == guid and d.category is kind), None)
        found = self.by_name.get(str(name))
        return found if found is not None and found.category is kind else None

    def as_document(self) -> StoredTypedefs:
        return StoredTypedefs(
            types_def_of(_without_derived(typedef) for typedef in self.by_name.values()), list(self.patches.values())
        )


@dataclass
class _Outcome[T]:
    """A change's result, what to write (None: nothing) and whether to commit the transient registry."""

    result: T
    stored: _Stored | None
    commit: bool = True


def _add_resolving(transient: TransientTypeRegistry, types_def: AtlasTypesDef) -> None:
    """``tryTypeCreation``: add and resolve; a type not found is a bad request (TDS-01, MDL-03)."""
    try:
        transient.add_types(types_def)
    except AtlasError as error:
        if error.code in _NOT_FOUND:
            raise AtlasError(AtlasErrorCode.BAD_REQUEST, error.message) from error
        raise


class TypedefStore:
    """Type definitions kept in a ``TypedefDocument``, served from a ``TypeRegistry`` (``AtlasTypeDefGraphStore``)."""

    def __init__(  # noqa: PLR0913 - the store's collaborators and clocks
        self,
        registry: TypeRegistry,
        document: TypedefDocument,
        *,
        usage: TypeUsage = never_in_use,
        refresh_seconds: float = DEFAULT_REFRESH_SECONDS,
        clock: Callable[[], float] = time.monotonic,
        now: Callable[[], datetime] = lambda: datetime.now(UTC),
    ) -> None:
        self.registry = registry
        self._document = document
        self._usage = usage
        self._refresh_seconds = refresh_seconds
        self._clock = clock
        self._now = now
        self._lock = asyncio.Lock()
        self._stored = _Stored()
        self._version: DocumentVersion | None = None
        self._checked_at: float | None = None

    async def load(self) -> None:
        """Prepare the document and load every stored definition into the registry (``init``, TDS-12)."""
        await self._document.prepare()
        async with self._lock:
            await self._load()

    async def _load(self) -> None:
        stored, version = await self._document.read()
        repaired = rectify(stored.types_def if stored is not None else AtlasTypesDef())
        with self.registry.update() as transient:
            transient.clear()
            transient.add_types(repaired)
        self._stored = _Stored.of(StoredTypedefs(repaired, stored.patches if stored is not None else []))
        self._version = version
        self._checked_at = self._clock()

    async def refresh(self, *, force: bool = False) -> bool:
        """Reload when another process changed the definitions; checked at most every refresh interval (TDS-13).

        Returns:
            Whether the registry was reloaded.
        """
        if not force and self._checked_at is not None and self._clock() - self._checked_at < self._refresh_seconds:
            return False
        async with self._lock:
            return await self._reload_if_changed()

    async def _reload_if_changed(self) -> bool:
        self._checked_at = self._clock()
        if await self._document.version() == self._version:
            return False
        await self._load()
        return True

    async def _change[T](self, apply: Callable[[TransientTypeRegistry], Awaitable[_Outcome[T]]]) -> T:
        """Apply a change on the transient registry, write it, then commit it (TDS-10, TDS-11).

        ``apply`` is called again after a conflict, on the reloaded definitions (DD-029, DD-033). It may leave the
        document unwritten, or the registry uncommitted, as its outcome says.
        """
        async with self._lock:
            await self._reload_if_changed()
            for attempt in (1, 2):
                transient = self.registry.lock_for_update()
                try:
                    outcome = await apply(transient)
                    if outcome.stored is not None:
                        self._version = await self._document.write(outcome.stored.as_document(), self._version)
                except VersionConflictError as conflict:
                    self.registry.release(transient, commit=False)
                    if attempt == 2:  # noqa: PLR2004 - the retry of DD-029
                        raise AtlasError(AtlasErrorCode.FAILED_TO_OBTAIN_TYPE_UPDATE_LOCK) from conflict
                    await self._load()
                    continue
                except BaseException:
                    self.registry.release(transient, commit=False)
                    raise
                self.registry.release(transient, commit=outcome.commit)
                if outcome.stored is not None:
                    self._stored = outcome.stored
                return outcome.result
        raise AssertionError  # pragma: no cover - the loop returns or raises

    async def create_types_def(self, types_def: AtlasTypesDef, user: str | None = None) -> AtlasTypesDef:
        """Create the definitions, all or none (``createTypesDef``, TDS-01 to TDS-06, TDS-10).

        Returns:
            The created definitions, as stored.

        Raises:
            AtlasError: A definition is invalid, exists already or refers to an unknown type.
        """

        async def apply(transient: TransientTypeRegistry) -> _Outcome[AtlasTypesDef]:
            _add_resolving(transient, types_def)
            stored = self._stored.copy()
            created = _Creation(transient, stored, self._now(), user).run(types_def)
            transient.update_types(created)
            return _Outcome(created, stored)

        return await self._change(apply)

    async def update_types_def(self, types_def: AtlasTypesDef, user: str | None = None) -> AtlasTypesDef:
        """Update the definitions found by GUID, else name (``updateTypesDef``, TDS-07, TDS-08, TDS-10).

        Returns:
            The updated definitions, as stored.

        Raises:
            AtlasError: A definition is not found, or changes what may not change.
        """

        async def apply(transient: TransientTypeRegistry) -> _Outcome[AtlasTypesDef]:
            stored = self._stored.copy()
            return _Outcome(self._update(transient, stored, types_def, user), stored)

        return await self._change(apply)

    def _update(
        self,
        transient: TransientTypeRegistry,
        stored: _Stored,
        types_def: AtlasTypesDef,
        user: str | None,
        patching: str | None = None,
    ) -> AtlasTypesDef:
        try:
            transient.update_types(types_def)
        except AtlasError as error:
            if error.code is AtlasErrorCode.TYPE_NAME_NOT_FOUND:
                raise AtlasError(AtlasErrorCode.BAD_REQUEST, error.message) from error
            raise
        updated = _Update(transient, stored, self._now(), user, patching).run(types_def)
        transient.update_types(updated)
        return updated

    async def create_update_types_def(
        self, types_def: AtlasTypesDef, *, check_type_version: bool = False, user: str | None = None
    ) -> AtlasTypesDef:
        """Create the definitions not registered and update the registered ones, all or none (MDL-02, MDL-03).

        ``createUpdateTypesDef``: what to create and update is decided on the newest stored definitions, and again
        after a conflict (DD-033). With ``check_type_version``, as at start-up, only definitions with a greater
        ``typeVersion`` are updated. Nothing is written when there is nothing to create or update.

        Returns:
            The created and updated definitions, as stored.

        Raises:
            AtlasError: A definition is invalid or refers to an unknown type.
        """

        async def apply(transient: TransientTypeRegistry) -> _Outcome[AtlasTypesDef]:
            to_create = types_to_create(types_def, self.registry)
            to_update = types_to_update(types_def, self.registry, check_type_version=check_type_version)
            if to_create.is_empty() and to_update.is_empty():
                return _Outcome(AtlasTypesDef(), None, commit=False)
            transient.update_types_without_resolving(to_update)
            _add_resolving(transient, to_create)
            stored = self._stored.copy()
            now = self._now()
            created = _all(_Creation(transient, stored, now, user).run(to_create))
            updated = _all(_Update(transient, stored, now, user).run(to_update))
            result = types_def_of([*created, *updated])
            transient.update_types(result)
            return _Outcome(result, stored)

        return await self._change(apply)

    async def apply_patch(self, patch: AtlasPatch, decide: Callable[[TypeRegistry], PatchChange]) -> PatchStatus | None:
        """Apply a typedef patch unless its record says it is done, and record how it ended (MDL-05, MDL-06).

        ``decide`` looks at the registry and says what the patch does; an ``AtlasError`` from it, or from the update
        it asks for, makes the patch ``FAILED``, and leaves the definitions as they were. Any other error is
        raised. The patch's record is written with its change (DD-031); a patch without an id is not recorded.

        Returns:
            How the patch ended, or None when its record says it was applied or skipped before.
        """

        async def apply(transient: TransientTypeRegistry) -> _Outcome[PatchStatus | None]:
            recorded = self._stored.patches.get(str(patch.id)) if patch.id else None
            if recorded is not None and recorded.status in _DONE:
                return _Outcome(None, None, commit=False)
            stored = self._stored.copy()
            try:
                change = decide(self.registry)
                if change.update is not None:
                    self._update(transient, stored, change.update, None, change.patching)
                status, changed = change.status, change.update is not None
            except AtlasError:
                stored, status, changed = self._stored.copy(), PatchStatus.FAILED, False
            if patch.id:
                stored.record(patch, status, self._now())
            elif not changed:
                return _Outcome(status, None, commit=False)
            return _Outcome(status, stored, commit=changed)

        return await self._change(apply)

    async def delete_types_def(self, types_def: AtlasTypesDef) -> None:
        """Delete the definitions found by GUID, else name, unless something refers to them (TDS-09, TDS-10).

        Raises:
            AtlasError: A definition is not found, is in use or is referred to.
        """

        async def apply(transient: TransientTypeRegistry) -> _Outcome[None]:
            stored = self._stored.copy()
            await _Deletion(stored, self._usage).run(types_def)
            transient.remove_types(types_def)
            return _Outcome(None, stored)

        await self._change(apply)

    async def delete_type_by_name(self, name: str) -> None:
        """Delete the definition named ``name`` (``deleteTypeByName``, TDS-09).

        Raises:
            AtlasError: ``TYPE_NAME_INVALID`` for a blank name, ``TYPE_NAME_NOT_FOUND`` for an unknown one and
                ``SYSTEM_TYPE`` for a built-in, array or map type.
        """
        await self.delete_types_def(types_def_of([self.get_by_name(name)]))

    def get_by_name(self, name: str) -> AtlasBaseTypeDef:
        """The registered definition named ``name``, of any kind (``getByName``, TYR-01).

        Raises:
            AtlasError: ``TYPE_NAME_INVALID`` for a blank name, ``TYPE_NAME_NOT_FOUND`` for an unknown one and
                ``SYSTEM_TYPE`` for a built-in, array or map type.
        """
        if not name.strip():
            raise AtlasError(AtlasErrorCode.TYPE_NAME_INVALID, "", name)
        type_ = self.registry.get_type(name)
        typedef = self.registry.typedef_by_name(name)
        if typedef is None:
            raise AtlasError(AtlasErrorCode.SYSTEM_TYPE, type_.category.name)
        return typedef

    def get_by_guid(self, guid: str) -> AtlasBaseTypeDef:
        """The registered definition with ``guid``, of any kind (``getByGuid``, TYR-02).

        Raises:
            AtlasError: ``TYPE_GUID_NOT_FOUND`` for a blank or unknown GUID.
        """
        if not guid.strip():
            raise AtlasError(AtlasErrorCode.TYPE_GUID_NOT_FOUND, guid)
        self.registry.get_type_by_guid(guid)
        typedef = self.registry.typedef_by_guid(guid)
        if typedef is None:  # pragma: no cover - every type with a GUID has a definition
            raise AtlasError(AtlasErrorCode.TYPE_GUID_NOT_FOUND, guid)
        return typedef

    def get_def_by_name(self, kind: TypeCategory, name: str) -> AtlasBaseTypeDef:
        """The registered definition of ``kind`` named ``name`` (``get{Kind}DefByName``, TYR-03).

        Raises:
            AtlasError: ``TYPE_NAME_NOT_FOUND`` when no definition of ``kind`` has the name.
        """
        typedef = self.registry.typedef_by_name(name)
        if typedef is None or typedef.category is not kind:
            raise AtlasError(AtlasErrorCode.TYPE_NAME_NOT_FOUND, name)
        return typedef

    def get_def_by_guid(self, kind: TypeCategory, guid: str) -> AtlasBaseTypeDef:
        """The registered definition of ``kind`` with ``guid`` (``get{Kind}DefByGuid``, TYR-03).

        Raises:
            AtlasError: ``TYPE_GUID_NOT_FOUND`` when no definition of ``kind`` has the GUID.
        """
        typedef = self.registry.typedef_by_guid(guid)
        if typedef is None or typedef.category is not kind:
            raise AtlasError(AtlasErrorCode.TYPE_GUID_NOT_FOUND, guid)
        return typedef


def _validate_name(typedef: AtlasBaseTypeDef) -> None:
    if not is_valid_name(typedef.name):
        raise AtlasError(AtlasErrorCode.TYPE_NAME_INVALID_FORMAT, typedef.name, typedef.category.name)
    if isinstance(typedef, AtlasBusinessMetadataDef):
        for attribute in typedef.attribute_defs:
            if not is_valid_name(attribute.name):
                raise AtlasError(AtlasErrorCode.ATTRIBUTE_NAME_INVALID_CHARS, attribute.name)


def _check_attributes(typedef: AtlasBaseTypeDef) -> None:
    for attribute in typedef.attribute_defs if isinstance(typedef, AtlasStructDef) else []:
        if not attribute.name:
            # Java's check; unreachable, the registry's resolution rejects this first.
            raise AtlasError(AtlasErrorCode.MISSING_MANDATORY_ATTRIBUTE, typedef.name, "name")  # pragma: no cover
        if not attribute.type_name:
            # Java's check; unreachable, the registry's resolution rejects this first.
            raise AtlasError(AtlasErrorCode.MISSING_MANDATORY_ATTRIBUTE, typedef.name, "typeName")  # pragma: no cover


def _check_enum(typedef: AtlasEnumDef) -> None:
    if not typedef.element_defs:
        raise AtlasError(AtlasErrorCode.MISSING_MANDATORY_ATTRIBUTE, typedef.name, "values")
    for element in typedef.element_defs:
        if not element.value or element.ordinal is None:
            raise AtlasError(AtlasErrorCode.MISSING_MANDATORY_ATTRIBUTE, typedef.name, "elementValue")


def _resolved_type(transient: TransientTypeRegistry, typedef: AtlasBaseTypeDef) -> StructType | None:
    type_ = transient.get_type(typedef.name)
    return type_ if isinstance(type_, StructType) else None


@dataclass
class _Creation:
    """``addToGraphStore``: enums first, then every other kind's pre-create, then their create."""

    transient: TransientTypeRegistry
    stored: _Stored
    now: datetime
    user: str | None

    def run(self, types_def: AtlasTypesDef) -> AtlasTypesDef:
        created: list[AtlasBaseTypeDef] = []
        for enum in _of_kind(types_def, TypeCategory.ENUM):
            self._pre_create(enum)
            if isinstance(enum, AtlasEnumDef):
                _check_enum(enum)
            created.append(self._store(enum))
        others = [typedef for kind in _KINDS[1:] for typedef in _of_kind(types_def, kind)]
        for typedef in others:
            self._pre_create(typedef)
            _check_attributes(typedef)
        for typedef in others:
            self._create(typedef)
            created.append(self._store(typedef))
        return types_def_of(created)

    def _pre_create(self, typedef: AtlasBaseTypeDef) -> None:
        _validate_name(typedef)
        if self.transient.get_type(typedef.name).category is not typedef.category:
            raise AtlasError(AtlasErrorCode.TYPE_MATCH_FAILED, typedef.name, LEGACY_KIND[typedef.category])
        if str(typedef.name) in self.stored.by_name:
            raise AtlasError(AtlasErrorCode.TYPE_ALREADY_EXISTS, typedef.name)
        stamp_created(typedef, self.now, self.user)
        self.stored.by_name[str(typedef.name)] = typedef

    def _create(self, typedef: AtlasBaseTypeDef) -> None:
        if type(typedef) is AtlasStructDef and not typedef.attribute_defs:
            raise AtlasError(AtlasErrorCode.BAD_REQUEST, "Missing attributes for structdef")
        _check_references(typedef, self.stored)
        if isinstance(typedef, AtlasClassificationDef):
            _check_entity_types(typedef, self.stored)

    def _store(self, typedef: AtlasBaseTypeDef) -> AtlasBaseTypeDef:
        result = stored_typedef(typedef, _resolved_type(self.transient, typedef))
        self.stored.by_name[str(typedef.name)] = result
        return result


def _check_references(typedef: AtlasBaseTypeDef, stored: _Stored) -> None:
    """``addReferencesForAttribute``: every non-built-in type an attribute names is stored (TDS-04)."""
    if isinstance(typedef, AtlasBusinessMetadataDef | AtlasRelationshipDef) or not isinstance(typedef, AtlasStructDef):
        return
    for attribute in typedef.attribute_defs:
        for name in referenced_type_names(attribute.type_name):
            if name not in ATLAS_BUILTIN_TYPES and name not in stored.by_name:
                # Java's check; unreachable, the registry's resolution rejects this first.
                raise AtlasError(AtlasErrorCode.UNKNOWN_TYPE, name, typedef.name, attribute.name)  # pragma: no cover


def _check_entity_types(typedef: AtlasClassificationDef, stored: _Stored) -> None:
    for name in typedef.entity_types:
        found = stored.by_name.get(name)
        if found is None or found.category is not TypeCategory.ENTITY:
            # Java's check; unreachable, the registry's resolution rejects this first.
            raise AtlasError(
                AtlasErrorCode.CLASSIFICATIONDEF_INVALID_ENTITYTYPES, typedef.name, name
            )  # pragma: no cover


@dataclass
class _Update:
    """``updateGraphStore``: each definition's update, in Atlas's order of kinds."""

    transient: TransientTypeRegistry
    stored: _Stored
    now: datetime
    user: str | None
    patching: str | None = None

    def run(self, types_def: AtlasTypesDef) -> AtlasTypesDef:
        return types_def_of(self._update(typedef) for typedef in _all(types_def))

    def _update(self, typedef: AtlasBaseTypeDef) -> AtlasBaseTypeDef:
        _validate_name(typedef)
        by_guid = bool(typedef.guid and typedef.guid.strip())
        current = self.stored.find(typedef.category, typedef.guid, typedef.name)
        resolved = self.transient.get_type_by_guid(typedef.guid) if by_guid else self.transient.get_type(typedef.name)
        if resolved.category is not typedef.category:
            # Java's check; unreachable, the registry's resolution rejects this first.
            raise AtlasError(
                AtlasErrorCode.TYPE_MATCH_FAILED, typedef.name, LEGACY_KIND[typedef.category]
            )  # pragma: no cover
        if current is None:
            if by_guid:
                raise AtlasError(AtlasErrorCode.TYPE_GUID_NOT_FOUND, typedef.guid)
            raise AtlasError(AtlasErrorCode.TYPE_NAME_NOT_FOUND, typedef.name)
        skipped: set[str] = set()
        if isinstance(typedef, AtlasEnumDef):
            _check_enum(typedef)
        else:
            if isinstance(typedef, AtlasRelationshipDef) and isinstance(current, AtlasRelationshipDef):
                _check_relationship_update(typedef, current, patching=self.patching is not None)
            if isinstance(typedef, AtlasBusinessMetadataDef) and isinstance(current, AtlasBusinessMetadataDef):
                _check_applicable_entity_types(typedef, current)
            skipped = self._check_struct_update(typedef, current)
            if isinstance(typedef, AtlasClassificationDef | AtlasEntityDef):
                _check_super_types(typedef, current)
            if isinstance(typedef, AtlasClassificationDef) and isinstance(current, AtlasClassificationDef):
                _check_entity_types_update(typedef, current, self.stored)
        stamp_updated(typedef, current, self.now, self.user)
        if skipped and isinstance(typedef, AtlasStructDef):
            typedef = typedef.model_copy(
                update={"attribute_defs": [a for a in typedef.attribute_defs if a.name not in skipped]}
            )
        result = stored_typedef(typedef, _resolved_type(self.transient, typedef))
        del self.stored.by_name[str(current.name)]
        self.stored.by_name[str(result.name)] = result
        return result

    def _check_struct_update(self, typedef: AtlasBaseTypeDef, current: AtlasBaseTypeDef) -> set[str]:
        """``updateVertexPreUpdate``: no attribute removed or retyped, no mandatory one added (TDS-08).

        Returns:
            The new attributes that are a legacy end of a relationship, which are not stored as attributes.
        """
        if not isinstance(typedef, AtlasStructDef) or not isinstance(current, AtlasStructDef):
            return set()  # pragma: no cover - enums are checked before
        names = [attribute.name for attribute in typedef.attribute_defs]
        for attribute in current.attribute_defs:
            if attribute.name not in names and self.patching is None:
                raise AtlasError(AtlasErrorCode.ATTRIBUTE_DELETION_NOT_SUPPORTED, typedef.name, attribute.name)
        skipped: set[str] = set()
        for attribute in typedef.attribute_defs:
            existing = current.get_attribute(attribute.name)
            if existing is None and _is_legacy_relationship_end(self.transient, typedef.name, attribute.name):
                skipped.add(str(attribute.name))
                continue
            _check_updated_attribute(typedef, attribute, existing, mandatory=self.patching == ADD_MANDATORY_ATTRIBUTE)
        return skipped


def _check_updated_attribute(
    typedef: AtlasStructDef, attribute: AtlasAttributeDef, existing: AtlasAttributeDef | None, *, mandatory: bool
) -> None:
    if existing is None and not attribute.is_optional and not mandatory:
        raise AtlasError(AtlasErrorCode.CANNOT_ADD_MANDATORY_ATTRIBUTE, typedef.name, attribute.name)
    if not attribute.name:
        # Java's check; unreachable, the registry's resolution rejects this first.
        raise AtlasError(AtlasErrorCode.MISSING_MANDATORY_ATTRIBUTE, typedef.name, "name")  # pragma: no cover
    if not attribute.type_name:
        # Java's check; unreachable, the registry's resolution rejects this first.
        raise AtlasError(AtlasErrorCode.MISSING_MANDATORY_ATTRIBUTE, typedef.name, "typeName")  # pragma: no cover
    if existing is not None and attribute.type_name != existing.type_name:
        raise AtlasError(AtlasErrorCode.BAD_REQUEST, "Data type update for attribute is not supported")


def _is_legacy_relationship_end(transient: TransientTypeRegistry, type_name: str | None, name: str | None) -> bool:
    """``AtlasTypeUtil.findRelationshipWithLegacyRelationshipEnd``."""
    for relationship in transient.types(TypeCategory.RELATIONSHIP):
        if isinstance(relationship, RelationshipType):
            for end in (relationship.relationship_def.end_def1, relationship.relationship_def.end_def2):
                if end is not None and end.type == type_name and end.name == name and end.is_legacy_attribute:
                    return True
    return False


def _check_relationship_update(
    typedef: AtlasRelationshipDef, current: AtlasRelationshipDef, *, patching: bool = False
) -> None:
    """``preUpdateCheck``: a relationship's name, category and ends stay (TDS-08).

    While patching, the category may change and the ends may swap (MDL-11).
    """
    if current.name != typedef.name:
        raise AtlasError(AtlasErrorCode.RELATIONSHIPDEF_INVALID_NAME_UPDATE, typedef.guid, current.name, typedef.name)
    if current.relationship_category != typedef.relationship_category and not patching:
        raise AtlasError(
            AtlasErrorCode.RELATIONSHIPDEF_INVALID_CATEGORY_UPDATE,
            typedef.name,
            None if typedef.relationship_category is None else typedef.relationship_category.value,
            None if current.relationship_category is None else current.relationship_category.value,
        )
    new_end1, new_end2 = typedef.end_def1, typedef.end_def2
    if not _same_end(current.end_def1, new_end1):
        if not (patching and _same_end(current.end_def1, new_end2)):
            raise AtlasError(
                AtlasErrorCode.RELATIONSHIPDEF_INVALID_END1_UPDATE,
                typedef.name,
                java_end_string(new_end1),
                java_end_string(current.end_def1),
            )
        new_end2 = new_end1
    if not _same_end(current.end_def2, new_end2):
        raise AtlasError(
            AtlasErrorCode.RELATIONSHIPDEF_INVALID_END2_UPDATE,
            typedef.name,
            java_end_string(new_end2),
            java_end_string(current.end_def2),
        )


def _same_end(current: AtlasRelationshipEndDef | None, new: AtlasRelationshipEndDef | None) -> bool:
    if current is None or new is None:
        return current is new  # pragma: no cover - the resolution needs both ends
    return (current.type, current.name, current.is_container, current.cardinality) == (
        new.type,
        new.name,
        new.is_container,
        new.cardinality,
    )


def _check_applicable_entity_types(typedef: AtlasBusinessMetadataDef, current: AtlasBusinessMetadataDef) -> None:
    """A business metadata attribute keeps its applicable entity types (TDS-08)."""
    for attribute in typedef.attribute_defs:
        existing = current.get_attribute(attribute.name)
        before = _name_set(existing.get_option(ATTR_OPTION_APPLICABLE_ENTITY_TYPES)) if existing else None
        if before is not None and not before <= (
            _name_set(attribute.get_option(ATTR_OPTION_APPLICABLE_ENTITY_TYPES)) or set()
        ):
            raise AtlasError(
                AtlasErrorCode.APPLICABLE_ENTITY_TYPES_DELETION_NOT_SUPPORTED, attribute.name, typedef.name
            )


def _name_set(value: str | None) -> set[str] | None:
    if value is None or not value.strip():
        return None
    try:
        parsed = json.loads(value)
    except ValueError:
        return None
    return {str(name) for name in parsed} if isinstance(parsed, list) else None


def _check_super_types(typedef: AtlasClassificationDef | AtlasEntityDef, current: AtlasBaseTypeDef) -> None:
    """``createSuperTypeEdges``: super types may be added, not removed (TDS-08)."""
    before = set(current.super_types) if isinstance(current, AtlasClassificationDef | AtlasEntityDef) else set()
    if not before <= set(typedef.super_types):
        raise AtlasError(AtlasErrorCode.SUPERTYPE_REMOVAL_NOT_SUPPORTED)


def _check_entity_types_update(
    typedef: AtlasClassificationDef, current: AtlasClassificationDef, stored: _Stored
) -> None:
    """``createEntityTypeEdges``: entity types may be added, or all removed, not some (TDS-08)."""
    if typedef.entity_types and not set(current.entity_types) <= set(typedef.entity_types):
        raise AtlasError(AtlasErrorCode.ENTITYTYPE_REMOVAL_NOT_SUPPORTED, typedef.name)
    _check_entity_types(typedef, stored)


@dataclass
class _Deletion:
    """``deleteTypesDef``, in Atlas's order; references between deleted definitions do not count (TDS-09).

    Relationships, structs, classifications and entities are pre-deleted, which drops their own edges, then
    deleted; then enums and business metadata are.
    """

    stored: _Stored
    usage: TypeUsage
    deleted: set[str] = field(default_factory=set)

    async def run(self, types_def: AtlasTypesDef) -> None:
        graph = (TypeCategory.RELATIONSHIP, TypeCategory.STRUCT, TypeCategory.CLASSIFICATION, TypeCategory.ENTITY)
        found = [
            (kind, await self._pre_delete(kind, typedef)) for kind in graph for typedef in _of_kind(types_def, kind)
        ]
        for _kind, typedef in found:
            self._delete(typedef)
        for kind in (TypeCategory.ENUM, TypeCategory.BUSINESS_METADATA):
            for typedef in _of_kind(types_def, kind):
                self._delete(await self._pre_delete(kind, typedef))

    async def _pre_delete(self, kind: TypeCategory, typedef: AtlasBaseTypeDef) -> AtlasBaseTypeDef:
        by_guid = bool(typedef.guid and typedef.guid.strip())
        found = self.stored.find(kind, typedef.guid, typedef.name)
        if found is None:
            if by_guid:
                raise AtlasError(AtlasErrorCode.TYPE_GUID_NOT_FOUND, typedef.guid)
            raise AtlasError(AtlasErrorCode.TYPE_NAME_NOT_FOUND, typedef.name)
        if kind is not TypeCategory.ENUM and await self.usage(str(found.name)):
            raise AtlasError(AtlasErrorCode.TYPE_HAS_REFERENCES, found.name)
        if kind is TypeCategory.ENTITY and self._referrers(found, relationships=True):
            raise AtlasError(AtlasErrorCode.TYPE_HAS_RELATIONSHIPS, found.name)
        self.deleted.add(str(found.name))
        return found

    def _delete(self, typedef: AtlasBaseTypeDef) -> None:
        if self._referrers(typedef, relationships=False):
            raise AtlasError(AtlasErrorCode.TYPE_HAS_REFERENCES, typedef.name)
        self.stored.by_name.pop(str(typedef.name), None)

    def _referrers(self, typedef: AtlasBaseTypeDef, *, relationships: bool) -> list[str]:
        """The stored definitions, not being deleted, with an edge to ``typedef``."""
        name = typedef.name
        return [
            str(other.name)
            for other in self.stored.by_name.values()
            if other.name not in self.deleted
            and other.name != name
            and name in _edges(other, relationships=relationships)
        ]


def _edges(typedef: AtlasBaseTypeDef, *, relationships: bool) -> set[str]:
    """The types a stored definition has graph edges to (``getOrCreateEdge``).

    With ``relationships``, a relationship's end types; otherwise also attribute types, super types and a
    classification's entity types.
    """
    if relationships:
        if isinstance(typedef, AtlasRelationshipDef):
            return {end.type for end in (typedef.end_def1, typedef.end_def2) if end is not None and end.type}
        return set()
    targets: set[str] = set()
    if isinstance(typedef, AtlasRelationshipDef):
        targets |= {end.type for end in (typedef.end_def1, typedef.end_def2) if end is not None and end.type}
    elif isinstance(typedef, AtlasStructDef) and not isinstance(typedef, AtlasBusinessMetadataDef):
        for attribute in typedef.attribute_defs:
            targets |= set(referenced_type_names(attribute.type_name))
    if isinstance(typedef, AtlasClassificationDef | AtlasEntityDef):
        targets |= set(typedef.super_types)
    if isinstance(typedef, AtlasClassificationDef):
        targets |= set(typedef.entity_types)
    return targets
