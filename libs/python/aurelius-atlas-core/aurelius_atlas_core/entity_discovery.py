"""``EntityDiscovery``: the entities a write request names, and what each of its references is (EWR-02 to EWR-07).

``AtlasEntityGraphDiscoveryV2`` with its ``EntityGraphDiscoveryContext`` and the two resolvers
(``IDBasedEntityResolver``, ``UniqAttrBasedEntityResolver``): the request's entities are walked on their values as
given, their references recorded, then resolved against the store.
"""

import re
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field
from typing import Any, NamedTuple

from aurelius_atlas_model.errors import AtlasError, AtlasErrorCode, java_string
from aurelius_atlas_model.instance import (
    AtlasEntity,
    AtlasEntityExtInfo,
    AtlasObjectId,
    AtlasStruct,
    RelationshipStatus,
)
from aurelius_atlas_model.typedef import TypeCategory
from aurelius_atlas_typesystem.array_type import ArrayType
from aurelius_atlas_typesystem.atlas_type import AtlasType, resolved
from aurelius_atlas_typesystem.builtin.object_id_type import is_assigned_guid
from aurelius_atlas_typesystem.entity_type import EntityType
from aurelius_atlas_typesystem.map_type import MapType
from aurelius_atlas_typesystem.struct_type import StructType, struct_attributes
from aurelius_atlas_typesystem.values import relationship_type_of

from aurelius_atlas_core.entity_documents import VersionedEntity
from aurelius_atlas_core.entity_store import WriteStore
from aurelius_atlas_core.graph_helper import (
    edge_for_label,
    held_parent_edges,
    other_end,
    parent_end,
    parent_family,
    parent_side_children,
)
from aurelius_atlas_core.guids import AssignedGuid, as_assigned_guid
from aurelius_atlas_core.stored_relationship import StoredRelationship

CUSTOM_ATTRIBUTE_KEY_MAX_LENGTH = 50
"""``atlas.custom.attribute.key.max.length``'s default."""

LABEL_MAX_LENGTH = 50
"""``atlas.entity.label.max.length``'s default."""

NAME_PATTERN = re.compile("^[⺀-⿕㆐-㆟㐀-䶿一-鿌豈-節a-zA-Z0-9_-]*$")
"""The characters a custom attribute key and a label may have (``CUSTOM_ATTRIBUTE_KEY_REGEX``, ``LABEL_REGEX``)."""

NO_ENTITIES = "no entities to create/update."
NULL_ENTITY = "found null entity"

_PRIMITIVES = {TypeCategory.PRIMITIVE, TypeCategory.ENUM}


def is_valid_guid(guid: str | None) -> bool:
    """``AtlasTypeUtil.isValidGuid``: assigned, or unassigned (non-empty and starting with ``-``)."""
    return bool(guid)


def is_valid_object_id(object_id: AtlasObjectId) -> bool:
    """``AtlasTypeUtil.isValid``: a valid GUID, or a type name with unique attributes."""
    return is_valid_guid(object_id.guid) or (bool(object_id.type_name) and bool(object_id.unique_attributes))


@dataclass
class EntityStream:
    """``AtlasEntityStream``: the request's entities in order, and every entity it holds by GUID."""

    entities: Sequence[AtlasEntity | None]
    ext_info: AtlasEntityExtInfo

    def get_by_guid(self, guid: str | None) -> AtlasEntity | None:
        """The request's entity with ``guid``, a main or a referred one."""
        found = self.ext_info.get_entity(guid)
        if found is None:
            found = next((entity for entity in self.entities if entity is not None and entity.guid == guid), None)
        return found


@dataclass
class DiscoveryContext:
    """``EntityGraphDiscoveryContext``: what the walk recorded and what each record resolved to."""

    referenced_guids: list[str | None] = field(default_factory=list)
    referenced_by_unique: list[AtlasObjectId] = field(default_factory=list)
    resolved_guids: dict[str | None, AssignedGuid] = field(default_factory=dict)
    """What each GUID a request names resolves to: an assigned GUID, never a placeholder (DV-162)."""
    resolved_by_unique: list[tuple[AtlasObjectId, AssignedGuid]] = field(default_factory=list)
    local_guids: set[str | None] = field(default_factory=set)
    stored: dict[str, VersionedEntity] = field(default_factory=dict)

    def add_resolved_by_unique(self, object_id: AtlasObjectId, guid: AssignedGuid) -> None:
        """Record that ``object_id`` names the entity with ``guid``."""
        self.resolved_by_unique.append((_plain(object_id), guid))

    def resolved_object_id(self, object_id: AtlasObjectId, sub_types: Sequence[str]) -> AssignedGuid | None:
        """``getResolvedEntityVertex(AtlasObjectId)``: its entity, also when recorded for one of ``sub_types``."""
        wanted = _plain(object_id)
        candidates = [wanted] + [
            AtlasObjectId(guid=wanted.guid, type_name=name, unique_attributes=wanted.unique_attributes)
            for name in sub_types
        ]
        for candidate in candidates:
            found = next((guid for known, guid in self.resolved_by_unique if known == candidate), None)
            if found is not None:
                return found
        return None


class EntityDiscovery:
    """Walks a request's entities and resolves their references against ``store`` (EWR-03 to EWR-05).

    ``importing`` keeps a GUID an import names that is nowhere yet as one to come (IMP-03).
    """

    def __init__(self, store: WriteStore, stream: EntityStream, *, importing: bool = False) -> None:
        self._store = store
        self.stream = stream
        self.context = DiscoveryContext()
        self._importing = importing

    async def discover(self) -> DiscoveryContext:
        """``discoverEntities``: walk the entities, then resolve every reference (EWR-04, EWR-05).

        Raises:
            AtlasError: ``INVALID_PARAMETERS``, ``TYPE_NAME_INVALID``, ``INVALID_OBJECT_ID``,
                ``INVALID_STRUCT_VALUE`` or ``REFERENCED_ENTITY_NOT_FOUND``.
        """
        if not self.stream.entities:
            raise AtlasError(AtlasErrorCode.INVALID_PARAMETERS, NO_ENTITIES)
        walked: set[str | None] = set()
        for entity in self.stream.entities:
            if entity is None:
                raise AtlasError(AtlasErrorCode.INVALID_PARAMETERS, NULL_ENTITY)
            process_dynamic_attributes(entity, self.entity_type(entity.type_name))
            self._walk(entity)
            walked.add(entity.guid)
        index = 0
        while index < len(self.context.referenced_guids):
            guid = self.context.referenced_guids[index]
            index += 1
            entity = None if guid in walked else self.stream.get_by_guid(guid)
            if entity is not None:
                self._walk(entity)
                walked.add(entity.guid)
        await self._resolve_guids()
        await self._resolve_unique_attributes()
        return self.context

    def entity_type(self, type_name: str | None) -> EntityType:
        """The entity type named.

        Raises:
            AtlasError: ``TYPE_NAME_INVALID`` (``ENTITY``, the name) when there is none.
        """
        entity_type = self._store.registry.entity_type(str(type_name))
        if entity_type is None:
            raise AtlasError(AtlasErrorCode.TYPE_NAME_INVALID, TypeCategory.ENTITY.value, type_name)
        return entity_type

    def validate_and_normalize(self, entity: AtlasEntity, *, for_update: bool) -> None:
        """``validateAndNormalize`` and ``…ForUpdate``: check the entity, then normalise it in place (EWR-07).

        Raises:
            AtlasError: ``INVALID_OBJECT_ID``, ``TYPE_NAME_INVALID``, the custom attribute and label errors, or
                ``INSTANCE_CRUD_INVALID_PARAMS`` with the type's messages.
        """
        if not is_valid_guid(entity.guid):
            raise AtlasError(AtlasErrorCode.INVALID_OBJECT_ID, f"invalid guid {java_string(entity.guid)}")
        entity_type = self.entity_type(entity.type_name)
        validate_custom_attributes(entity)
        validate_labels(entity.labels)
        messages: list[str] = []
        if for_update:
            entity_type.validate_value_for_update(entity, str(entity.type_name), messages)
        else:
            entity_type.validate_value(entity, str(entity.type_name), messages)
        if messages:
            raise AtlasError(AtlasErrorCode.INSTANCE_CRUD_INVALID_PARAMS, messages)
        if for_update:
            entity_type.get_normalized_value_for_update(entity)
        else:
            entity_type.get_normalized_value(entity)

    async def validate_parent_safe(self, entity: AtlasEntity, entity_type: EntityType, guid: str) -> None:
        """Each parent-side candidate the entity names: refused when it is held (RPS-01, RPS-03, DD-755).

        A candidate a stored edge holds to another parent is released when the same request also updates that
        parent to drop the candidate, so a deliberate move in one request is not refused (RPS-02).

        Raises:
            AtlasError: ``INSTANCE_CRUD_INVALID_PARAMS`` with one message per held candidate.
        """
        keeps = self._request_parent_keeps()
        held = await held_parent_sides(
            self._store,
            self.stream,
            entity,
            entity_type,
            guid,
            resolve=self._resolve_guid,
            released=lambda child_attribute, parent_guid, candidate: self._released(
                keeps, child_attribute, parent_guid, candidate
            ),
        )
        if held:
            messages = [held_parent_message(found) for found in held]
            raise AtlasError(AtlasErrorCode.INSTANCE_CRUD_INVALID_PARAMS, messages)

    def _resolve_guid(self, guid: str) -> str:
        """The assigned GUID a request's placeholder became, or ``guid`` when it names an assigned one (DV-162)."""
        found = self.context.resolved_guids.get(guid)
        return str(found) if found is not None else guid

    def _released(
        self, keeps: dict[tuple[str, str], set[str]], child_attribute: str, parent_guid: str, candidate: str
    ) -> bool:
        """Whether the request drops ``candidate`` from ``parent_guid``'s list of ``child_attribute`` (RPS-02)."""
        kept = keeps.get((parent_guid, child_attribute))
        return kept is not None and candidate not in kept

    def _request_parent_keeps(self) -> dict[tuple[str, str], set[str]]:
        """Each parent side the request writes, with the candidates it keeps: ``(parent GUID, child attribute)``.

        A parent-side `SET` an entity names replaces the parent's whole child list, so a candidate missing from
        it is dropped there (RPS-02). Candidates named by placeholder are resolved, so a move made in one
        request -- the child added under the new parent and dropped from the old one -- is read as deliberate.
        """
        keeps: dict[tuple[str, str], set[str]] = {}
        for entity in self.stream.entities:
            keeps.update(self._parent_keeps_of(entity))
        return keeps

    def _parent_keeps_of(self, entity: AtlasEntity | None) -> dict[tuple[str, str], set[str]]:
        """The parent sides one request entity writes, with the candidates each keeps (RPS-02)."""
        registry = self._store.registry
        entity_type = None if entity is None else registry.entity_type(str(entity.type_name))
        if entity is None or entity_type is None:
            return {}
        parent_guid = self._resolve_guid(str(entity.guid))
        keeps: dict[tuple[str, str], set[str]] = {}
        for parent_attribute, child_attribute in parent_side_children(registry, entity_type).items():
            if entity.has_relationship_attribute(parent_attribute):
                value = entity.get_relationship_attribute(parent_attribute)
                keeps[(parent_guid, child_attribute)] = self._kept_candidates(value)
        return keeps

    def _kept_candidates(self, value: object) -> set[str]:
        """The candidate GUIDs a parent-side value names, each resolved through the request's placeholders (RPS-02)."""
        items = value if isinstance(value, list | tuple | set) else []
        kept: set[str] = set()
        for item in items:
            object_id = object_id_of(item)
            if object_id is not None and object_id.guid is not None:
                kept.add(self._resolve_guid(str(object_id.guid)))
        return kept

    async def validate_parent_groups(
        self,
        entity: AtlasEntity,
        entity_type: EntityType,
        stored: VersionedEntity | None,
    ) -> None:
        """The parent groups of the entity's type: one filled member each (PME-07, PME-08, PME-09, DV-183).

        An attribute is filled when the request names it with a value, or the stored entity holds an active
        edge on it, read as the retriever reads it (PME-03). Apache Atlas has no such check.

        Raises:
            AtlasError: ``INSTANCE_CRUD_INVALID_PARAMS`` with one message per group that has two filled
                members.
        """
        groups = entity_type.parent_groups()
        if not groups:
            return
        edges = await self._held_edges(stored)
        guid = stored.entity.guid if stored is not None else str(entity.guid)
        messages: list[str] = []
        for group, names in sorted(groups.items()):
            filled = sorted(name for name in names if self._is_filled(entity, entity_type, name, guid, edges))
            if len(filled) > 1:
                messages.append(
                    f"{entity.type_name}: {' and '.join(filled)} cannot both hold a parent of group {group}"
                )
        if messages:
            raise AtlasError(AtlasErrorCode.INSTANCE_CRUD_INVALID_PARAMS, messages)

    @staticmethod
    def _is_filled(
        entity: AtlasEntity,
        entity_type: EntityType,
        name: str,
        guid: str,
        edges: list[StoredRelationship],
    ) -> bool:
        """Whether attribute ``name`` is filled (PME-03).

        A value in the request fills it. A null in the request clears it, as the mapper clears its edge, so it
        stays unfilled while the stored edge is still active. When the request names neither, the stored
        active edge fills it.
        """
        if entity.has_relationship_attribute(name):
            return entity.get_relationship_attribute(name) is not None
        if entity.has_attribute(name):
            return entity.get_attribute(name) is not None
        end = parent_end(entity_type.relationship_attribute(name))
        if end is None:
            return False
        held = edge_for_label(guid, edges, *end)
        return held is not None and held.state is RelationshipStatus.ACTIVE

    async def _held_edges(self, stored: VersionedEntity | None) -> list[StoredRelationship]:
        """The stored entity's relationships, read once for the check (PME-08)."""
        if stored is None or not stored.entity.relationship_guids:
            return []
        found = await self._store.get_relationships(stored.entity.relationship_guids)
        return [found[guid].relationship for guid in stored.entity.relationship_guids if guid in found]

    def _walk(self, entity: AtlasEntity) -> None:
        """``walkEntityGraph``: record the entity's GUID, then visit its relationship and other attributes."""
        entity_type = self.entity_type(entity.type_name)
        self._record_guid(entity.guid)
        visited: set[str] = set()
        for name in entity_type.relationship_attributes:
            if entity.has_relationship_attribute(name):
                value = entity.get_relationship_attribute(name)
            elif entity.has_attribute(name):
                value = entity.get_attribute(name)
            else:
                continue
            attribute = entity_type.relationship_attribute(name, relationship_type_of(value))
            if attribute is not None:
                self._visit(attribute.attribute_type, value)
            visited.add(name)
        for name, attribute in entity_type.all_attributes.items():
            if entity.has_attribute(name) and name not in visited:
                self._visit(attribute.attribute_type, entity.get_attribute(name))

    def _visit(self, type_: AtlasType, value: object) -> None:
        """``visitAttribute``: record the references in a value of ``type_``."""
        if value is None or type_.category in _PRIMITIVES:
            return
        if isinstance(type_, ArrayType):
            self._visit_collection(resolved(type_.element_type), value)
        elif isinstance(type_, MapType):
            self._visit_map(resolved(type_.key_type), resolved(type_.value_type), value)
        elif isinstance(type_, StructType):
            self._visit_struct(type_, value)
        elif type_.category is TypeCategory.OBJECT_ID_TYPE:
            self._visit_reference(value)
        else:  # pragma: no cover - attribute types are of the kinds above
            raise AtlasError(AtlasErrorCode.TYPE_CATEGORY_INVALID, type_.category.value)

    def _visit_collection(self, element: AtlasType, value: object) -> None:
        """``visitCollectionReferences``: each element of a collection; other values hold none."""
        if element.category not in _PRIMITIVES and isinstance(value, list | tuple | set):
            for item in value:
                self._visit(element, item)

    def _visit_map(self, key: AtlasType, item_type: AtlasType, value: object) -> None:
        """``visitMapReferences``: each key and value of a map, unless both are primitive."""
        if (key.category in _PRIMITIVES and item_type.category in _PRIMITIVES) or not isinstance(value, Mapping):
            return
        for item_key, item in value.items():
            self._visit(key, item_key)
            self._visit(item_type, item)

    def _visit_struct(self, struct_type: StructType, value: object) -> None:
        if isinstance(value, AtlasStruct):
            struct = value
        elif isinstance(value, Mapping):
            struct = AtlasStruct(type_name=struct_type.type_name, attributes=dict(struct_attributes(value)))
        else:
            raise AtlasError(AtlasErrorCode.INVALID_STRUCT_VALUE, value)
        for name, attribute in struct_type.all_attributes.items():
            self._visit(attribute.attribute_type, struct.get_attribute(str(name)))

    def _visit_reference(self, value: object) -> None:
        """``visitReference``: an object id, or a map read as one, that names an entity."""
        if isinstance(value, AtlasObjectId):
            object_id = value
        elif isinstance(value, Mapping):
            object_id = AtlasObjectId.from_map(value)
        else:
            raise AtlasError(AtlasErrorCode.INVALID_OBJECT_ID, value)
        if not is_valid_object_id(object_id):
            raise AtlasError(AtlasErrorCode.INVALID_OBJECT_ID, object_id)
        if is_valid_guid(object_id.guid):
            self._record_guid(object_id.guid)
        elif object_id not in self.context.referenced_by_unique:
            self.context.referenced_by_unique.append(object_id)

    def _record_guid(self, guid: str | None) -> None:
        if guid not in self.context.referenced_guids:
            self.context.referenced_guids.append(guid)

    async def _resolve_guids(self) -> None:
        """``IDBasedEntityResolver``: stored by GUID, else the request's entity by its unique values (EWR-05)."""
        context = self.context
        assigned = [guid for guid in context.referenced_guids if guid is not None and is_assigned_guid(guid)]
        context.stored.update(await self._store.get_many(assigned))
        for guid in context.referenced_guids:
            await self._resolve_guid_one(guid)

    async def _resolve_guid_one(self, guid: str | None) -> None:
        """One referenced GUID: its stored entity by GUID or unique values, or it joins the request's own (EWR-05).

        Raises:
            AtlasError: ``REFERENCED_ENTITY_NOT_FOUND`` for a reference that names no entity.
        """
        context = self.context
        found = context.stored.get(guid) if guid is not None and is_assigned_guid(guid) else None
        if found is None:
            found = await self._resolve_by_values(guid)
        if found is not None:
            context.stored[found.entity.guid] = found
            context.resolved_guids[guid] = as_assigned_guid(found.entity.guid)
        elif is_assigned_guid(guid) and not self._importing:
            raise AtlasError(AtlasErrorCode.REFERENCED_ENTITY_NOT_FOUND, guid)
        else:
            context.local_guids.add(guid)

    async def _resolve_by_values(self, guid: str | None) -> VersionedEntity | None:
        """The stored entity of a GUID the store does not have, by the request entity's unique values (EWR-05).

        Raises:
            AtlasError: ``REFERENCED_ENTITY_NOT_FOUND`` for a valueless reference outside an import.
        """
        entity = self.stream.get_by_guid(guid)
        if self._importing and is_assigned_guid(guid):
            return None  # an import keeps its GUIDs: its entity is not looked up by its values (IMP-03)
        if entity is not None:
            return await self._store.find_by_unique_attributes(
                self.entity_type(entity.type_name), entity.attributes or {}
            )
        if not is_assigned_guid(guid):
            raise AtlasError(AtlasErrorCode.REFERENCED_ENTITY_NOT_FOUND, guid)
        return None

    async def _resolve_unique_attributes(self) -> None:
        """``UniqAttrBasedEntityResolver``: the stored entity of the type or a sub type holding the values."""
        for object_id in self.context.referenced_by_unique:
            entity_type = self.entity_type(object_id.type_name)
            found = await self._store.find_by_unique_attributes(entity_type, object_id.unique_attributes or {})
            if found is None:
                raise AtlasError(AtlasErrorCode.REFERENCED_ENTITY_NOT_FOUND, object_id)
            self.context.stored[found.entity.guid] = found
            self.context.add_resolved_by_unique(object_id, as_assigned_guid(found.entity.guid))


def process_dynamic_attributes(entity: AtlasEntity, entity_type: EntityType) -> None:
    """``processDynamicAttributes``: set each dynamic attribute from its template, in order (EWR-03, DD-054)."""
    for attribute in entity_type.dyn_eval_attributes:
        parts: list[str] = []
        for token in entity_type.parsed_templates.get(str(attribute.name), []):
            text = token.eval(entity)
            if text is None:
                break
            parts.append(text)
        else:
            entity.set_attribute(str(attribute.name), "".join(parts))


def validate_custom_attributes(entity: AtlasEntity) -> None:
    """``validateCustomAttributes``: keys of at most 50 letters, digits, ``_`` and ``-`` (EWR-07).

    Values are not checked: Atlas checks them only for keys without its special prefix, and with the default
    empty prefix every key has it.

    Raises:
        AtlasError: ``INVALID_CUSTOM_ATTRIBUTE_KEY_LENGTH`` or ``INVALID_CUSTOM_ATTRIBUTE_KEY_CHARACTERS``.
    """
    for key in entity.custom_attributes or {}:
        if len(key) > CUSTOM_ATTRIBUTE_KEY_MAX_LENGTH:
            raise AtlasError(AtlasErrorCode.INVALID_CUSTOM_ATTRIBUTE_KEY_LENGTH, key)
        if not NAME_PATTERN.match(key):
            raise AtlasError(AtlasErrorCode.INVALID_CUSTOM_ATTRIBUTE_KEY_CHARACTERS, key)


def validate_labels(labels: Sequence[str] | set[str] | None) -> None:
    """``validateLabels``: labels of at most 50 letters, digits, ``_`` and ``-`` (EWR-07).

    Raises:
        AtlasError: ``INVALID_LABEL_LENGTH`` or ``INVALID_LABEL_CHARACTERS``.
    """
    for label in labels or []:
        if len(label) > LABEL_MAX_LENGTH:
            raise AtlasError(AtlasErrorCode.INVALID_LABEL_LENGTH, label, str(LABEL_MAX_LENGTH))
        if not NAME_PATTERN.match(label):
            raise AtlasError(AtlasErrorCode.INVALID_LABEL_CHARACTERS, label)


def _plain(object_id: AtlasObjectId) -> AtlasObjectId:
    """An object id as ``AtlasObjectId``, as Java compares a related object id it looks up."""
    if type(object_id) is AtlasObjectId:
        return object_id
    return AtlasObjectId(
        guid=object_id.guid, type_name=object_id.type_name, unique_attributes=object_id.unique_attributes
    )


def object_id_of(value: Any) -> AtlasObjectId | None:  # noqa: ANN401 - a reference as given
    """``getObjectId``: the object id a reference value is, or None for null.

    Raises:
        AtlasError: ``INVALID_OBJECT_ID`` for a value that is no valid object id.
    """
    if value is None:
        return None
    if isinstance(value, AtlasObjectId):
        return value
    if isinstance(value, Mapping):
        found = AtlasObjectId.from_map(value)
        if is_valid_object_id(found):
            return found
    raise AtlasError(AtlasErrorCode.INVALID_OBJECT_ID, value)


class HeldParent(NamedTuple):
    """A candidate held on a save (RPS-01): which candidate, by which child attribute, and which parent.

    The edge's GUID is None for a candidate this request creates, whose edges do not exist yet.
    """

    candidate_type: str
    candidate_guid: str
    child_attribute: str
    parent_type: str
    parent_guid: str
    edge_guid: str | None = None


def held_parent_message(held: HeldParent) -> str:
    """The refusal of one held candidate: its child attribute and the parent it already holds (RPS-03)."""
    return (
        f"{held.candidate_type} {held.candidate_guid}: {held.child_attribute} holds parent "
        f"{held.parent_type} {held.parent_guid}, pass unsafeReparent to move it"
    )


async def held_parent_sides(  # noqa: PLR0913, PLR0917 - the save's parts; each needed once
    store: WriteStore,
    stream: EntityStream,
    entity: AtlasEntity,
    entity_type: EntityType,
    guid: str,
    resolve: Callable[[str], str] | None = None,
    released: Callable[[str, str, str], bool] | None = None,
) -> list[HeldParent]:
    """Each parent-side candidate of the entity that already holds another parent (RPS-01, RPS-02, DD-755).

    A parent side is a `SET` whose opposite end is a `SINGLE` child end (HCA-01). Neither write door ever
    cleared the child's edge of another relationship on such a save, so the child ended under two parents:
    Apache Atlas has no check, and neither had Aurelius. A candidate this request creates is read on the
    parents it declares; a stored one on its active edges. The parent the save names never holds the
    candidate (RPS-02). ``resolve`` answers the assigned GUID a request's placeholder became, so a candidate
    created in this same request naming the written parent by its placeholder is not a reparent.
    Apache Atlas has no such check.
    """
    registry = store.registry
    held: list[HeldParent] = []
    for name, child_attribute in parent_side_children(registry, entity_type).items():
        value = entity.get_relationship_attribute(name) if entity.has_relationship_attribute(name) else None
        items = value if isinstance(value, list | tuple | set) else []
        for item in items:
            object_id = object_id_of(item)
            if object_id is None or object_id.guid is None:
                continue  # a unique-attribute reference: the writer resolves it, and checks what it names
            declared = stream.get_by_guid(object_id.guid)
            if declared is not None:
                held += await _declared_parents_held(store, stream, declared, child_attribute, guid, resolve)
            elif is_assigned_guid(object_id.guid):
                held += await held_parents_of(store, str(object_id.guid), child_attribute, guid, released)
    return held


async def _declared_parents_held(  # noqa: PLR0913, PLR0917 - the candidate's parts; each needed once
    store: WriteStore,
    stream: EntityStream,
    candidate: AtlasEntity,
    child_attribute: str,
    parent_guid: str,
    resolve: Callable[[str], str] | None = None,
) -> list[HeldParent]:
    """The parents a created candidate declares that are not the one being written (RPS-01).

    A created candidate's edges do not exist yet, so it is held by what the same request declares for it, on
    any family member including the written attribute: a candidate moved off its parent on that attribute is a
    reparent. A declaration naming the written parent -- by placeholder or assigned GUID -- is the edge the
    save writes, so it is not a reparent (RPS-02).
    """
    registry = store.registry
    candidate_type = registry.entity_type(str(candidate.type_name))
    if candidate_type is None:
        return []
    family = parent_family(registry, candidate_type, child_attribute)
    held: list[HeldParent] = []
    for name in candidate_type.relationship_attributes:
        attribute = candidate_type.relationship_attribute(name)
        if attribute is None or str(attribute.relationship_edge_label) not in family:
            continue
        value = (
            candidate.get_relationship_attribute(name)
            if candidate.has_relationship_attribute(name)
            else candidate.get_attribute(name)
        )
        for item in _as_many(value):
            parent = _reference_guid(item)
            if parent is not None and (resolve is None or resolve(parent)) != parent_guid:
                held.append(
                    HeldParent(
                        str(candidate.type_name),
                        str(candidate.guid),
                        str(name),
                        await _known_type_name(store, stream, parent),
                        parent,
                    )
                )
    return held


async def held_parents_of(
    store: WriteStore,
    candidate_guid: str,
    child_attribute: str,
    parent_guid: str,
    released: Callable[[str, str, str], bool] | None = None,
) -> list[HeldParent]:
    """The active family edges of a stored candidate to a parent other than the save's (RPS-01).

    Both doors ask this of one candidate: the wire path through ``held_parent_sides``, the view door's
    ``sections`` step directly, where the edge is created by the relationship store instead of the mapper. An
    active edge on any member of the family to another parent is a held child, including the written attribute:
    moving it is the reparent the check guards. ``released(child_attribute, parent_guid, candidate)`` answers
    whether the same request drops the candidate from that parent, releasing it (RPS-02).
    """
    found = await store.get(candidate_guid)
    if found is None or not found.entity.relationship_guids:
        return []
    entity_type = store.registry.entity_type(found.entity.type_name)
    if entity_type is None:
        return []
    family = parent_family(store.registry, entity_type, child_attribute)
    edges = await store.get_relationships(found.entity.relationship_guids)
    relationships = [edges[guid].relationship for guid in found.entity.relationship_guids if guid in edges]
    held: list[HeldParent] = []
    for relationship, attribute in held_parent_edges(candidate_guid, relationships, family, parent_guid):
        parent = other_end(relationship, candidate_guid)
        if released is not None and released(attribute, parent, candidate_guid):
            continue
        held.append(
            HeldParent(
                found.entity.type_name,
                candidate_guid,
                attribute,
                await _type_name(store, parent),
                parent,
                relationship.guid,
            )
        )
    return held


def _as_many(value: Any) -> list[Any]:  # noqa: ANN401 - a relationship value as given; read as one or more references
    """A relationship attribute's value as a list of references: many as itself, one as a single item, none as empty."""
    if isinstance(value, list | tuple | set):
        return list(value)
    return [] if value is None else [value]


def _reference_guid(value: Any) -> str | None:  # noqa: ANN401 - a reference as given
    """The GUID a reference value names, None when it names none or is no valid object id."""
    try:
        object_id = object_id_of(value)
    except AtlasError:
        return None
    return None if object_id is None or object_id.guid is None else str(object_id.guid)


async def _known_type_name(store: WriteStore, stream: EntityStream, guid: str) -> str:
    """The type name a same-request or stored GUID names, "entity" when it names neither yet."""
    entity = stream.get_by_guid(guid)
    if entity is not None:
        return str(entity.type_name)
    return await _type_name(store, guid)


async def _type_name(store: WriteStore, guid: str) -> str:
    """The type name of the stored entity, "entity" when there is none."""
    found = await store.get(guid)
    return "entity" if found is None else found.entity.type_name
