"""Atlas's built-in models and their typedef patches, loaded at start-up (MDL-01 to MDL-15).

Ported from ``AtlasTypeDefStoreInitializer`` of Apache Atlas 2.4.0. Each model file and each patch is one change of
the typedef store, decided on the newest stored definitions (DD-033); a patch's record is written with its change
(DD-031).
"""

import asyncio
import functools
import logging
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from aurelius_atlas_model.errors import AtlasError, AtlasErrorCode, java_string
from aurelius_atlas_model.patches import AtlasPatch, PatchStatus
from aurelius_atlas_model.typedef import (
    AtlasAttributeDef,
    AtlasBaseTypeDef,
    AtlasClassificationDef,
    AtlasEntityDef,
    AtlasEnumDef,
    AtlasEnumElementDef,
    AtlasModel,
    AtlasRelationshipDef,
    AtlasStructDef,
    AtlasTypesDef,
    IndexType,
    RelationshipCategory,
    TypeCategory,
)
from aurelius_atlas_typesystem.registry import TypeRegistry
from pydantic import Field

from aurelius_atlas_core.typedef_store import (
    ADD_MANDATORY_ATTRIBUTE,
    PatchChange,
    TypedefStore,
    java_compare,
    types_def_of,
)

LOGGER = logging.getLogger(__name__)

RACE_ATTEMPTS = 10
"""How often a model file or patch is tried while another process keeps writing first (MDL-15, DD-036)."""

BUILTIN_MODELS_DIR = Path(__file__).parent / "models"
"""``addons/models`` of Apache Atlas 2.4.0, unchanged (DD-032)."""

PATCHES_FOLDER_NAME = "patches"
"""The sub-directory of a models directory that holds its patches."""

REMOVE_LEGACY_REF_ATTRIBUTES = "REMOVE_LEGACY_REF_ATTRIBUTES"
"""The patch action under which an update may remove attributes and swap a relationship's ends (MDL-11)."""

_MIN_SEARCH_WEIGHT, _MAX_SEARCH_WEIGHT = 1, 10


class PatchDataError(ValueError):
    """Patch data that Atlas does not check, and fails on with a runtime exception (MDL-06, MDL-13)."""


class TypedefPatch(AtlasModel):
    """One typedef patch of a models-directory patch file (MDL-05).

    The fields a patch uses depend on its ``action``; the patch handlers read
    the ones their action needs.
    """

    id: str | None = Field(default=None, description="The unique id of the patch.")

    description: str | None = Field(default=None, description="A description of the patch.")

    action: str | None = Field(
        default=None,
        description="The action the patch performs, e.g. ``ADD_ATTRIBUTE`` or ``REMOVE_LEGACY_REF_ATTRIBUTES``.",
    )

    type_name: str | None = Field(default=None, description="The name of the type the patch changes.")

    apply_to_version: str | None = Field(
        default=None,
        description="The type version the patch applies to; a patch applies when the stored "
        "version equals it or starts below it.",
    )

    update_to_version: str | None = Field(
        default=None,
        description="The type version the type gets when the patch is applied.",
    )

    params: dict[str, Any] | None = Field(
        default=None,
        description="Parameters of the action, e.g. ``ownedAttribute``/``inverseAttribute`` for a ref-attribute patch.",
    )

    attribute_defs: list[AtlasAttributeDef] | None = Field(
        default=None,
        description="The attributes the patch adds to or changes on the type.",
    )

    element_defs: list[AtlasEnumElementDef] | None = Field(
        default=None,
        description="The enum values the patch adds to the type.",
    )

    type_def_options: dict[str, str] | None = Field(
        default=None,
        description="The type options the patch sets on the type.",
    )

    service_type: str | None = Field(default=None, description="The service type of the patched type.")

    attribute_name: str | None = Field(
        default=None,
        description="The name of a single attribute the patch acts on.",
    )

    super_types: list[str] | None = Field(
        default=None,
        description="The super types the patch adds to the type.",
    )

    def record(self) -> AtlasPatch:
        """The patch's record, before its status is known."""
        return AtlasPatch(id=self.id, description=self.description, action=self.action)


class TypedefPatches(AtlasModel):
    """A patch file: the patches of a models directory (MDL-05)."""

    patches: list[TypedefPatch] | None = Field(
        default=None,
        description="The patches of the file, in the order they are applied.",
    )


@dataclass
class ModelLoad:
    """What loading a models directory did: the files that failed, the patch files stopped, each patch's status."""

    failed_files: list[Path] = field(default_factory=list)
    stopped_patch_files: list[Path] = field(default_factory=list)
    patches: dict[str, PatchStatus | None] = field(default_factory=dict)


def sorted_entries(directory: Path) -> list[Path]:
    """The entries of ``directory`` by name, compared as ``File.compareTo`` does on Unix (MDL-01)."""
    return sorted(directory.iterdir(), key=functools.cmp_to_key(lambda a, b: java_compare(a.name, b.name)))


def is_patch_applicable(patch: TypedefPatch, typedef: AtlasBaseTypeDef) -> bool:
    """``isPatchApplicable``: no ``typeVersion``, or ``applyToVersion`` ignoring case, or below it (MDL-07)."""
    current = typedef.type_version
    return (
        current is None
        or (patch.apply_to_version is not None and current.lower() == patch.apply_to_version.lower())
        or current.startswith(f"{java_string(patch.apply_to_version)}.")
    )


type PatchHandler = Callable[[TypedefPatch, TypeRegistry], PatchChange]


def _required[T](value: T | None, name: str) -> T:
    """A patch field Java dereferences without a check; missing, it fails with a runtime exception (MDL-06)."""
    if value is None:
        message = f"the patch has no {name}"
        raise PatchDataError(message)
    return value


def _typedef(patch: TypedefPatch, registry: TypeRegistry) -> AtlasBaseTypeDef:
    typedef = registry.typedef_by_name(patch.type_name)
    if typedef is None:
        raise AtlasError(AtlasErrorCode.PATCH_FOR_UNKNOWN_TYPE, patch.action, patch.type_name)
    return typedef.model_copy(deep=True)


def _not_applicable(patch: TypedefPatch, typedef: AtlasBaseTypeDef) -> AtlasError:
    return AtlasError(AtlasErrorCode.PATCH_NOT_APPLICABLE_FOR_TYPE, patch.action, type(typedef).__name__)


def _applied(patch: TypedefPatch, *typedefs: AtlasBaseTypeDef, patching: str | None = None) -> PatchChange:
    typedefs[0].type_version = patch.update_to_version
    return PatchChange(PatchStatus.APPLIED, types_def_of(typedefs), patching)


def _skipped(patch: TypedefPatch) -> PatchChange:
    LOGGER.info(
        "patch skipped: typeName=%s; applyToVersion=%s; updateToVersion=%s",
        patch.type_name,
        patch.apply_to_version,
        patch.update_to_version,
    )
    return PatchChange(PatchStatus.SKIPPED)


def update_enum_def(patch: TypedefPatch, registry: TypeRegistry) -> PatchChange:
    """``UPDATE_ENUMDEF``: add the elements to an enum (MDL-08)."""
    typedef = _typedef(patch, registry)
    if not is_patch_applicable(patch, typedef):
        return _skipped(patch)
    if type(typedef) is not AtlasEnumDef:
        raise _not_applicable(patch, typedef)
    for element in _required(patch.element_defs, "elementDefs"):
        typedef.add_element(element)
    return _applied(patch, typedef)


def _add_attributes(
    patch: TypedefPatch, registry: TypeRegistry, kinds: tuple[type[AtlasStructDef], ...]
) -> PatchChange:
    typedef = _typedef(patch, registry)
    if not is_patch_applicable(patch, typedef):
        return _skipped(patch)
    if type(typedef) not in kinds or not isinstance(typedef, AtlasStructDef):
        raise _not_applicable(patch, typedef)
    for attribute in _required(patch.attribute_defs, "attributeDefs"):
        typedef.add_attribute(attribute)
    return _applied(patch, typedef)


def add_attribute(patch: TypedefPatch, registry: TypeRegistry) -> PatchChange:
    """``ADD_ATTRIBUTE``: add attributes to an entity, classification, struct or relationship (MDL-09)."""
    return _add_attributes(
        patch, registry, (AtlasEntityDef, AtlasClassificationDef, AtlasStructDef, AtlasRelationshipDef)
    )


def update_attribute(patch: TypedefPatch, registry: TypeRegistry) -> PatchChange:
    """``UPDATE_ATTRIBUTE``: replace or add attributes of an entity, classification or struct (MDL-09)."""
    return _add_attributes(patch, registry, (AtlasEntityDef, AtlasClassificationDef, AtlasStructDef))


def add_mandatory_attribute(patch: TypedefPatch, registry: TypeRegistry) -> PatchChange:
    """``ADD_MANDATORY_ATTRIBUTE``: add mandatory primitive attributes that have a default value (MDL-10)."""
    typedef = _typedef(patch, registry)
    if not is_patch_applicable(patch, typedef):
        return _skipped(patch)
    if not isinstance(typedef, AtlasStructDef):
        message = f"{type(typedef).__name__} cannot be cast to AtlasStructDef"
        raise PatchDataError(message)
    to_add = [
        attribute
        for attribute in _required(patch.attribute_defs, "attributeDefs")
        if registry.get_type(attribute.type_name).category is TypeCategory.PRIMITIVE
        and not typedef.has_attribute(attribute.name)
        and not attribute.is_optional
        and attribute.default_value
        and not attribute.is_unique
    ]
    if not to_add:
        LOGGER.info(
            "patch skipped: typeName=%s; mandatory attributes are not valid in patch %s", patch.type_name, patch.id
        )
        return PatchChange(PatchStatus.SKIPPED)
    if type(typedef) not in (AtlasEntityDef, AtlasClassificationDef, AtlasStructDef):
        raise _not_applicable(patch, typedef)
    for attribute in to_add:
        typedef.add_attribute(attribute)
    return _applied(patch, typedef, patching=ADD_MANDATORY_ATTRIBUTE)


def remove_legacy_ref_attributes(patch: TypedefPatch, registry: TypeRegistry) -> PatchChange:
    """``REMOVE_LEGACY_REF_ATTRIBUTES``: move a relationship's legacy attributes to the relationship (MDL-11)."""
    typedef = _typedef(patch, registry)
    if not is_patch_applicable(patch, typedef):
        return _skipped(patch)
    if not isinstance(typedef, AtlasRelationshipDef):
        return PatchChange(PatchStatus.UNKNOWN)
    end1, end2 = _required(typedef.end_def1, "end1"), _required(typedef.end_def2, "end2")
    params = patch.params or {}
    category = params.get("relationshipCategory")
    label = _relationship_label(patch, typedef, registry)
    if str(params.get("swapEnds")).lower() == "true":
        typedef.end_def1, typedef.end_def2 = end2, end1
    typedef.relationship_label = label
    if category is not None:
        try:
            typedef.relationship_category = RelationshipCategory(java_string(category))
        except ValueError as error:
            raise PatchDataError(str(error)) from error
    ends = [_required(typedef.end_def1, "end1"), _required(typedef.end_def2, "end2")]
    entities: list[AtlasBaseTypeDef] = []
    for end in ends:
        entity = registry.entity_type(end.type)
        if entity is None:
            # A resolved relationship ends on entity types; Java would fail with a NullPointerException.
            message = f"no entity type {end.type}"  # pragma: no cover
            raise PatchDataError(message)  # pragma: no cover
        entity_def = entity.entity_def.model_copy(deep=True)
        entity_def.remove_attribute(end.name)
        entities.append(entity_def)
    return _applied(patch, typedef, *entities, patching=REMOVE_LEGACY_REF_ATTRIBUTES)


def _relationship_label(patch: TypedefPatch, typedef: AtlasRelationshipDef, registry: TypeRegistry) -> str | None:
    """The patch's label unless empty, else ``__`` and the one legacy end's attribute, else the current label."""
    label = (patch.params or {}).get("relationshipLabel")
    if label is not None and java_string(label):
        return java_string(label)
    end1, end2 = _required(typedef.end_def1, "end1"), _required(typedef.end_def2, "end2")
    if end1.is_legacy_attribute and end2.is_legacy_attribute:
        raise AtlasError(AtlasErrorCode.PATCH_MISSING_RELATIONSHIP_LABEL, patch.action, patch.type_name)
    if end1.is_legacy_attribute or end2.is_legacy_attribute:
        legacy = end1 if end1.is_legacy_attribute else end2
        return f"__{_legacy_attribute(registry, legacy.type, legacy.name)}"
    return typedef.relationship_label


def _legacy_attribute(registry: TypeRegistry, type_name: str | None, name: str | None) -> str:
    entity = registry.entity_type(type_name)
    attribute = None if entity is None else entity.attribute(name)
    if attribute is None:
        message = f"no attribute {type_name}.{name}"
        raise PatchDataError(message)
    return attribute.qualified_name


def update_typedef_options(patch: TypedefPatch, registry: TypeRegistry) -> PatchChange:
    """``UPDATE_TYPEDEF_OPTIONS``: merge options into a type's options (MDL-12)."""
    typedef = _typedef(patch, registry)
    if not patch.type_def_options:
        raise AtlasError(AtlasErrorCode.PATCH_INVALID_DATA, patch.action, patch.type_name)
    if not is_patch_applicable(patch, typedef):
        return _skipped(patch)
    typedef.options = {**(typedef.options or {}), **patch.type_def_options}
    return _applied(patch, typedef)


def set_service_type(patch: TypedefPatch, registry: TypeRegistry) -> PatchChange:
    """``SET_SERVICE_TYPE``: set a type's service type; without one, the update keeps the stored one (MDL-12)."""
    typedef = _typedef(patch, registry)
    if not is_patch_applicable(patch, typedef):
        return _skipped(patch)
    typedef.service_type = patch.service_type
    return _applied(patch, typedef)


def update_attribute_metadata(patch: TypedefPatch, registry: TypeRegistry) -> PatchChange:
    """``UPDATE_ATTRIBUTE_METADATA``: set the search weight or index type of an attribute (MDL-13)."""
    typedef = _typedef(patch, registry)
    if not is_patch_applicable(patch, typedef):
        return _skipped(patch)
    if type(typedef) not in (AtlasEntityDef, AtlasStructDef) or not isinstance(typedef, AtlasStructDef):
        raise _not_applicable(patch, typedef)
    name = (patch.attribute_name or "").lower()
    for attribute in typedef.attribute_defs:
        if patch.attribute_name is not None and (attribute.name or "").lower() == name:
            _update_attribute_metadata(attribute, _required(patch.params, "params"))
    return _applied(patch, typedef)


def _update_attribute_metadata(attribute: AtlasAttributeDef, params: dict[str, Any]) -> None:
    for key, value in params.items():
        if key.lower() == "searchweight":
            if isinstance(value, bool) or not isinstance(value, int | float):
                message = f"searchWeight {value!r} of {attribute.name} is not a number"
                raise PatchDataError(message)
            weight = int(value)
            if weight != -1 and not _MIN_SEARCH_WEIGHT <= weight <= _MAX_SEARCH_WEIGHT:
                message = f"Invalid search weight '{weight}' was provided for property {attribute.name}."
                raise PatchDataError(message)
            attribute.search_weight = weight
        elif key.lower() == "indextype":
            if not isinstance(value, str):
                message = f"indexType {value!r} of {attribute.name} is not a string"
                raise PatchDataError(message)
            if value:
                try:
                    attribute.index_type = IndexType(value)
                except ValueError as error:
                    message = f"Value {value} provided for the attribute indexType is not valid."
                    raise PatchDataError(message) from error
        else:
            message = f"Received unknown property {key} for attribute {attribute.name}"
            raise PatchDataError(message)


def add_super_types(patch: TypedefPatch, registry: TypeRegistry) -> PatchChange:
    """``ADD_SUPER_TYPES``: add super types to an entity type (MDL-14)."""
    typedef = _typedef(patch, registry)
    if not patch.super_types:
        LOGGER.info("patch skipped: No superTypes provided to add for typeName=%s", patch.type_name)
        return PatchChange(PatchStatus.SKIPPED)
    if not is_patch_applicable(patch, typedef):
        return _skipped(patch)
    if type(typedef) is not AtlasEntityDef:
        raise _not_applicable(patch, typedef)
    for super_type in patch.super_types:
        typedef.add_super_type(super_type)
    return _applied(patch, typedef)


PATCH_HANDLERS: dict[str, PatchHandler] = {
    "UPDATE_ENUMDEF": update_enum_def,
    "ADD_ATTRIBUTE": add_attribute,
    "UPDATE_ATTRIBUTE": update_attribute,
    REMOVE_LEGACY_REF_ATTRIBUTES: remove_legacy_ref_attributes,
    "UPDATE_TYPEDEF_OPTIONS": update_typedef_options,
    "SET_SERVICE_TYPE": set_service_type,
    "UPDATE_ATTRIBUTE_METADATA": update_attribute_metadata,
    "ADD_SUPER_TYPES": add_super_types,
    ADD_MANDATORY_ATTRIBUTE: add_mandatory_attribute,
}
"""The patch actions of Atlas 2.4.0 (``applyTypePatches``, MDL-07 to MDL-14)."""


def load_plan(models_dir: Path) -> list[tuple[Path, bool]]:
    """The model and patch files in the order they load, each with whether it is a patch file (MDL-01).

    ``loadBootstrapTypeDefs``:

    each sub-directory except ``patches`` in name order, then the directory itself; of each, its files in name order,
    then the files of its ``patches`` sub-directory. A directory without entries contributes nothing.
    """
    if not models_dir.is_dir():
        LOGGER.info("Types directory %s does not exist or not readable or has no typedef files", models_dir)
        return []
    folders = [entry for entry in sorted_entries(models_dir) if entry.is_dir() and entry.name != PATCHES_FOLDER_NAME]
    plan: list[tuple[Path, bool]] = []
    for folder in [*folders, models_dir]:
        entries = sorted_entries(folder)
        if not entries:
            LOGGER.info("Types directory %s does not exist or not readable or has no typedef files", folder.name)
            continue
        plan += [(entry, False) for entry in entries if entry.is_file()]
        patches_dir = folder / PATCHES_FOLDER_NAME
        if patches_dir.is_dir():
            plan += [(entry, True) for entry in sorted_entries(patches_dir) if entry.is_file()]
    return plan


class ModelLoader:
    """Loads a models directory into a typedef store (``AtlasTypeDefStoreInitializer.loadBootstrapTypeDefs``)."""

    def __init__(self, store: TypedefStore) -> None:
        self._store = store

    async def load(self, models_dir: Path) -> ModelLoad:
        """Load the model files and apply the patch files of ``models_dir``, in the order of ``load_plan`` (MDL-01).

        Returns:
            What failed, and how each patch ended.
        """
        result = ModelLoad()
        for path, is_patch_file in await asyncio.to_thread(load_plan, models_dir):
            if is_patch_file:
                await self._apply_patches(path, result)
            else:
                await self._load_file(path, result)
        return result

    async def _load_file(self, path: Path, result: ModelLoad) -> None:
        """Create and update the types of one model file; a failure skips the file (MDL-02 to MDL-04)."""
        try:
            types_def = AtlasTypesDef.model_validate_json(await asyncio.to_thread(path.read_bytes))
            if types_def.is_empty():
                LOGGER.info("No type in file %s", path)
                return
            changed = await _until_not_raced(
                lambda: self._store.create_update_types_def(types_def, check_type_version=True)
            )
        except Exception:
            LOGGER.exception("error while registering types in file %s", path)
            result.failed_files.append(path)
            return
        if changed.is_empty():
            LOGGER.info("No new type in file %s", path)
        else:
            LOGGER.info("Created/Updated types defined in file %s", path)

    async def _apply_patches(self, path: Path, result: ModelLoad) -> None:
        """Apply the patches of one file in order; an error other than an Atlas error ends the file (MDL-05, MDL-06)."""
        LOGGER.info("Applying patches in file %s", path)
        try:
            patches = TypedefPatches.model_validate_json(await asyncio.to_thread(path.read_bytes)).patches
            for patch in patches or []:
                handler = PATCH_HANDLERS.get(str(patch.action))
                if handler is None:
                    LOGGER.error("Unknown patch action %s in file %s. Ignored", patch.action, path)
                    continue
                status = await self._apply_patch(patch, handler, path)
                if patch.id:
                    result.patches[patch.id] = status
        except Exception:
            LOGGER.exception("Failed to apply patches in file %s. Ignored", path)
            result.stopped_patch_files.append(path)

    async def _apply_patch(self, patch: TypedefPatch, handler: PatchHandler, path: Path) -> PatchStatus | None:
        try:
            status = await _until_not_raced(
                lambda: self._store.apply_patch(patch.record(), lambda registry: handler(patch, registry))
            )
        except AtlasError:
            LOGGER.exception("Failed to apply %s (action: %s) in file: %s. Ignored.", patch.id, patch.action, path)
            return PatchStatus.FAILED
        if status is None:
            LOGGER.info("%s in file: %s already applied. Ignoring.", patch.id, path)
        else:
            LOGGER.info("%s (status: %s; action: %s) in file: %s", patch.id, status, patch.action, path)
        return status


async def _until_not_raced[T](change: Callable[[], Awaitable[T]]) -> T:
    """Make ``change`` again while the store gives up on it after losing to other processes (MDL-15, DD-036).

    Every lost race is another process's write, so processes starting together each get through.
    """
    for attempt in range(1, RACE_ATTEMPTS + 1):
        try:
            return await change()
        except AtlasError as error:
            if error.code is not AtlasErrorCode.FAILED_TO_OBTAIN_TYPE_UPDATE_LOCK or attempt == RACE_ATTEMPTS:
                raise
            LOGGER.info("Another process changed the types first (attempt %d); trying again", attempt)
    raise AssertionError  # pragma: no cover - the loop returns or raises
