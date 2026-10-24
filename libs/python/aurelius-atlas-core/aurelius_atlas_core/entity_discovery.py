"""``EntityDiscovery``: the entities a write request names, and what each of its references is (EWR-02 to EWR-07).

``AtlasEntityGraphDiscoveryV2`` with its ``EntityGraphDiscoveryContext`` and the two resolvers
(``IDBasedEntityResolver``, ``UniqAttrBasedEntityResolver``): the request's entities are walked on their values as
given, their references recorded, then resolved against the store.
"""

import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from typing import Any

from aurelius_atlas_model.errors import AtlasError, AtlasErrorCode, java_string
from aurelius_atlas_model.instance import AtlasEntity, AtlasEntityExtInfo, AtlasObjectId, AtlasStruct
from aurelius_atlas_model.typedef import TypeCategory
from aurelius_atlas_typesystem.array_type import ArrayType
from aurelius_atlas_typesystem.atlas_type import AtlasType, resolved
from aurelius_atlas_typesystem.builtin.object_id_type import is_assigned_guid
from aurelius_atlas_typesystem.entity_type import EntityType
from aurelius_atlas_typesystem.map_type import MapType
from aurelius_atlas_typesystem.struct_type import StructType, struct_attributes
from aurelius_atlas_typesystem.values import relationship_type_of

from aurelius_atlas_core.entity_documents import VersionedEntity
from aurelius_atlas_core.entity_store import EntityStore

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
    resolved_guids: dict[str | None, str] = field(default_factory=dict)
    resolved_by_unique: list[tuple[AtlasObjectId, str]] = field(default_factory=list)
    local_guids: set[str | None] = field(default_factory=set)
    stored: dict[str, VersionedEntity] = field(default_factory=dict)

    def add_resolved_by_unique(self, object_id: AtlasObjectId, guid: str) -> None:
        """Record that ``object_id`` names the entity with ``guid``."""
        self.resolved_by_unique.append((_plain(object_id), guid))

    def resolved_object_id(self, object_id: AtlasObjectId, sub_types: Sequence[str]) -> str | None:
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
    """Walks a request's entities and resolves their references against ``store`` (EWR-03 to EWR-05)."""

    def __init__(self, store: EntityStore, stream: EntityStream) -> None:
        self._store = store
        self.stream = stream
        self.context = DiscoveryContext()

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
            found = context.stored.get(guid) if guid is not None and is_assigned_guid(guid) else None
            if found is None:
                entity = self.stream.get_by_guid(guid)
                if entity is not None:
                    found = await self._store.find_by_unique_attributes(
                        self.entity_type(entity.type_name), entity.attributes or {}
                    )
                elif not is_assigned_guid(guid):
                    raise AtlasError(AtlasErrorCode.REFERENCED_ENTITY_NOT_FOUND, guid)
            if found is not None:
                context.stored[found.entity.guid] = found
                context.resolved_guids[guid] = found.entity.guid
            elif is_assigned_guid(guid):
                raise AtlasError(AtlasErrorCode.REFERENCED_ENTITY_NOT_FOUND, guid)
            else:
                context.local_guids.add(guid)

    async def _resolve_unique_attributes(self) -> None:
        """``UniqAttrBasedEntityResolver``: the stored entity of the type or a sub type holding the values."""
        for object_id in self.context.referenced_by_unique:
            entity_type = self.entity_type(object_id.type_name)
            found = await self._store.find_by_unique_attributes(entity_type, object_id.unique_attributes or {})
            if found is None:
                raise AtlasError(AtlasErrorCode.REFERENCED_ENTITY_NOT_FOUND, object_id)
            self.context.stored[found.entity.guid] = found
            self.context.add_resolved_by_unique(object_id, found.entity.guid)


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
