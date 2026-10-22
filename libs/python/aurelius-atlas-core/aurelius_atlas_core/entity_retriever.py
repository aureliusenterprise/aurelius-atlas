"""``EntityRetriever``: entities, headers and object ids built from stored entities (ERD-02 to ERD-09).

The read side of ``EntityGraphRetriever`` and ``AtlasEntityStoreV2``: what Atlas maps from a vertex and its edges,
here from an entity document and the documents its references name (DD-049, DD-050).
"""

from collections.abc import Iterable, Mapping, Sequence
from typing import Any

from aurelius_atlas_model.errors import AtlasError, AtlasErrorCode, java_string
from aurelius_atlas_model.instance import (
    AtlasEntitiesWithExtInfo,
    AtlasEntity,
    AtlasEntityExtInfo,
    AtlasEntityHeader,
    AtlasEntityWithExtInfo,
    AtlasObjectId,
    AtlasStruct,
)
from aurelius_atlas_model.typedef import Cardinality, TypeCategory
from aurelius_atlas_typesystem.array_type import ArrayType
from aurelius_atlas_typesystem.atlas_type import AtlasType, resolved
from aurelius_atlas_typesystem.attribute import AtlasAttribute
from aurelius_atlas_typesystem.entity_type import EntityType
from aurelius_atlas_typesystem.map_type import MapType

from aurelius_atlas_core.entity_store import EntityStore
from aurelius_atlas_core.stored_entity import StoredEntity

SOFT_REFERENCE_SEPARATOR = ":"
"""``typeName:guid``, how Atlas holds a soft reference (DD-049)."""

DISPLAY_TEXT_FALLBACKS = ("name", "displayName", "qualifiedName")
"""The attributes ``getDisplayText`` tries, in order, after the type's display text attribute."""

_REFERENCES = {TypeCategory.OBJECT_ID_TYPE, TypeCategory.ENTITY}


class EntityRetriever:
    """Reads entities of ``store`` as Atlas answers them; one instance per request's options."""

    def __init__(self, store: EntityStore, *, min_ext_info: bool = False, ignore_relationships: bool = False) -> None:
        self._store = store
        self._min_ext_info = min_ext_info
        self._ignore_relationships = ignore_relationships

    async def entity_with_ext_info(self, guid: str) -> AtlasEntityWithExtInfo:
        """The entity with ``guid``, in any state, and the entities it owns (ERD-02, ``getById``).

        Raises:
            AtlasError: ``INSTANCE_GUID_NOT_FOUND`` when no entity has the GUID.
        """
        return await self._with_ext_info(await self._found(guid))

    async def entities_with_ext_info(self, guids: Sequence[str]) -> AtlasEntitiesWithExtInfo:
        """The entities with these GUIDs, in order, sharing their referred entities (ERD-02, ``getByIds``).

        Raises:
            AtlasError: ``INSTANCE_GUID_NOT_FOUND`` naming the first GUID no entity has.
        """
        found = await self._store.get_many(guids)
        missing = next((guid for guid in guids if guid not in found), None)
        if missing is not None:
            raise AtlasError(AtlasErrorCode.INSTANCE_GUID_NOT_FOUND, missing)
        result = AtlasEntitiesWithExtInfo()
        reading = _Reading(self._store, result, min_ext_info=self._min_ext_info, relationships=self._relationships)
        for guid in guids:
            result.add_entity(await reading.entity(found[guid].entity))
        result.compact()
        return result

    async def entity_by_unique_attributes(
        self, entity_type: EntityType, values: Mapping[str, Any]
    ) -> AtlasEntityWithExtInfo:
        """The ``ACTIVE`` entity of the type holding the unique values (ERD-09, ``getByUniqueAttributes``).

        Raises:
            AtlasError: ``INSTANCE_BY_UNIQUE_ATTRIBUTE_NOT_FOUND`` when none holds them.
        """
        return await self._with_ext_info(await self._found_by_unique_attributes(entity_type, values))

    async def entities_by_unique_attributes(
        self, entity_type: EntityType, value_sets: Sequence[Mapping[str, Any]]
    ) -> AtlasEntitiesWithExtInfo:
        """The entity each set of unique values finds; sets that find none are left out (ERD-09)."""
        result = AtlasEntitiesWithExtInfo()
        reading = _Reading(self._store, result, min_ext_info=self._min_ext_info, relationships=self._relationships)
        for values in value_sets:
            found = await self._store.find_by_unique_attributes(entity_type, values)
            if found is not None:
                result.add_entity(await reading.entity(found.entity))
        result.compact()
        return result

    async def header(self, guid: str) -> AtlasEntityHeader:
        """The header of the entity with ``guid``, with its (empty) classifications (ERD-07, ``getHeaderById``).

        Raises:
            AtlasError: ``INSTANCE_GUID_NOT_FOUND`` when no entity has the GUID.
        """
        header = await self._reading(AtlasEntityExtInfo()).header(await self._found(guid))
        header.classifications = []
        return header

    async def header_by_unique_attributes(
        self, entity_type: EntityType, values: Mapping[str, Any]
    ) -> AtlasEntityHeader:
        """The header of the entity holding the unique values (ERD-07, ``getEntityHeaderByUniqueAttributes``).

        Raises:
            AtlasError: ``INSTANCE_BY_UNIQUE_ATTRIBUTE_NOT_FOUND`` when none holds them.
        """
        found = await self._found_by_unique_attributes(entity_type, values)
        return await self._reading(AtlasEntityExtInfo()).header(found)

    @property
    def _relationships(self) -> bool:
        return not self._ignore_relationships

    def _reading(self, ext_info: AtlasEntityExtInfo) -> _Reading:
        return _Reading(self._store, ext_info, min_ext_info=self._min_ext_info, relationships=self._relationships)

    async def _found(self, guid: str) -> StoredEntity:
        found = await self._store.get(guid)
        if found is None:
            raise AtlasError(AtlasErrorCode.INSTANCE_GUID_NOT_FOUND, guid)
        return found.entity

    async def _found_by_unique_attributes(self, entity_type: EntityType, values: Mapping[str, Any]) -> StoredEntity:
        found = await self._store.find_by_unique_attributes(entity_type, values)
        if found is None:
            raise AtlasError(
                AtlasErrorCode.INSTANCE_BY_UNIQUE_ATTRIBUTE_NOT_FOUND, entity_type.type_name, java_string(dict(values))
            )
        return found.entity

    async def _with_ext_info(self, stored: StoredEntity) -> AtlasEntityWithExtInfo:
        result = AtlasEntityWithExtInfo()
        result.entity = await self._reading(result).entity(stored)
        result.compact()
        return result


class _Reading:
    """One response being built: the entities it has read, and those it holds in ``ext_info`` by GUID."""

    def __init__(
        self, store: EntityStore, ext_info: AtlasEntityExtInfo, *, min_ext_info: bool, relationships: bool
    ) -> None:
        self._store = store
        self._ext_info = ext_info
        self._min_ext_info = min_ext_info
        self._relationships = relationships
        self._stored: dict[str, StoredEntity | None] = {}

    async def entity(self, stored: StoredEntity) -> AtlasEntity:
        """``mapVertexToAtlasEntity``: every attribute, relationship attributes unless ignored (ERD-03 to ERD-06)."""
        known = self._ext_info.get_entity(stored.guid)
        if known is not None:
            return known
        entity_type = self._entity_type(stored)
        entity = stored.to_entity(entity_type)
        entity.attributes = {}
        self._ext_info.add_referred_entity_as(stored.guid, entity)
        self._stored[stored.guid] = stored
        await self._load(_references_of(stored.attributes, entity_type.all_attributes.values(), qualified=True))
        for name, attribute in entity_type.all_attributes.items():
            value = stored.attributes.get(attribute.qualified_name)
            entity.set_attribute(name, await self._attribute(attribute, value, ext_info=True))
        if self._relationships:
            for name in entity_type.relationship_attributes:
                attribute = entity_type.relationship_attribute(name)
                single = attribute is None or attribute.attribute_def.cardinality is Cardinality.SINGLE
                if entity.relationship_attributes is None:
                    entity.relationship_attributes = {}
                entity.relationship_attributes[name] = None if single else []
        return entity

    async def min_entity(self, stored: StoredEntity) -> AtlasEntity:
        """``mapVertexToAtlasEntityMin``: system properties and the minimal-info attributes with a value (ERD-05)."""
        known = self._ext_info.get_entity(stored.guid)
        if known is not None:
            return known
        entity_type = self._entity_type(stored)
        entity = stored.to_entity(entity_type)
        entity.attributes = None
        self._ext_info.add_referred_entity_as(stored.guid, entity)
        for name, attribute in entity_type.min_info_attributes.items():
            value = await self._vertex_attribute(stored, attribute)
            if value is not None:
                entity.set_attribute(name, value)
        return entity

    async def header(self, stored: StoredEntity) -> AtlasEntityHeader:
        """``mapVertexToAtlasEntityHeader``: header attributes, ``""`` for none, and the display text (ERD-07)."""
        entity_type = self._entity_type(stored)
        header = AtlasEntityHeader(
            type_name=stored.type_name,
            guid=stored.guid,
            status=stored.state,
            classification_names=[],
            is_incomplete=stored.is_incomplete,
            labels=stored.labels or [],
            meanings=[],
            meaning_names=[],
        )
        for name, attribute in entity_type.header_attributes.items():
            value = await self._vertex_attribute(stored, attribute)
            header.set_attribute(name, "" if value is None else value)
        for name in (entity_type.display_text_attribute, *DISPLAY_TEXT_FALLBACKS):
            attribute = entity_type.attribute(name)
            value = None if attribute is None else await self._vertex_attribute(stored, attribute)
            if value is not None:
                header.display_text = java_string(value)
                break
        return header

    async def object_id(self, stored: StoredEntity) -> AtlasObjectId | None:
        """``toAtlasObjectId``: GUID, type name and the unique attribute values that are not null (ERD-05)."""
        entity_type = self._store.registry.entity_type(stored.type_name)
        if entity_type is None:
            return None
        unique: dict[str, Any] = {}
        for name, attribute in entity_type.unique_attributes.items():
            value = await self._vertex_attribute(stored, attribute)
            if value is not None:
                unique[name] = value
        return AtlasObjectId(guid=stored.guid, type_name=stored.type_name, unique_attributes=unique)

    def _entity_type(self, stored: StoredEntity) -> EntityType:
        entity_type = self._store.registry.entity_type(stored.type_name)
        if entity_type is None:
            raise AtlasError(AtlasErrorCode.TYPE_NAME_NOT_FOUND, stored.type_name)
        return entity_type

    async def _load(self, guids: Iterable[str]) -> None:
        """Read the entities with these GUIDs not read yet, in one request."""
        missing = [guid for guid in dict.fromkeys(guids) if guid not in self._stored]
        if missing:
            found = await self._store.get_many(missing)
            for guid in missing:
                self._stored[guid] = found[guid].entity if guid in found else None

    async def _get(self, guid: str) -> StoredEntity | None:
        await self._load([guid])
        return self._stored[guid]

    async def _vertex_attribute(self, stored: StoredEntity, attribute: AtlasAttribute) -> Any:  # noqa: ANN401 - Atlas JSON
        """``getVertexAttribute``: the value without referred entities."""
        return await self._attribute(attribute, stored.attributes.get(attribute.qualified_name), ext_info=False)

    async def _attribute(self, attribute: AtlasAttribute, value: object, *, ext_info: bool) -> Any:  # noqa: ANN401 - Atlas JSON
        """``mapVertexToAttribute``: an owned reference adds its entity to the response when ``ext_info`` (ERD-04)."""
        owned = ext_info and attribute.is_owned_ref
        if attribute.attribute_def.is_soft_referenced():
            return await self._soft_references(value, owned=owned)
        return await self._value(attribute.attribute_type, value, owned=owned, ext_info=ext_info)

    async def _value(self, type_: AtlasType, value: object, *, owned: bool, ext_info: bool) -> Any:  # noqa: ANN401 - Atlas JSON
        if value is None:
            return None
        if type_.category in _REFERENCES:
            return await self._reference(str(value), owned=owned)
        if type_.category is TypeCategory.STRUCT and isinstance(value, Mapping):
            return await self._struct(value, ext_info=ext_info)
        contained = _contained(type_)
        if contained is None or not _is_reference(contained):
            return value
        return await self._collection(type_, contained, value, owned=owned, ext_info=ext_info)

    async def _collection(
        self, type_: AtlasType, contained: AtlasType, value: object, *, owned: bool, ext_info: bool
    ) -> Any:  # noqa: ANN401 - Atlas JSON
        """``mapVertexToArray`` and ``mapVertexToMap`` of references and structs: null elements are left out."""
        if isinstance(type_, ArrayType) and isinstance(value, list):
            items = [await self._value(contained, item, owned=owned, ext_info=ext_info) for item in value]
            return [item for item in items if item is not None]
        if isinstance(value, Mapping) and value:
            entries = {
                str(key): await self._value(contained, item, owned=owned, ext_info=ext_info)
                for key, item in value.items()
            }
            return {key: item for key, item in entries.items() if item is not None}
        return None

    async def _reference(self, guid: str, *, owned: bool) -> AtlasObjectId | None:
        """``mapVertexToObjectId``: an owned entity is added to the response and named by GUID and type alone."""
        stored = await self._get(guid)
        if stored is None:
            return None
        if owned:
            entity = await (self.min_entity(stored) if self._min_ext_info else self.entity(stored))
            return AtlasObjectId(guid=entity.guid, type_name=entity.type_name)
        return await self.object_id(stored)

    async def _struct(self, value: Mapping[str, Any], *, ext_info: bool) -> AtlasStruct:
        """``mapVertexToStruct``: every attribute of the struct's type (DD-049)."""
        type_name = str(value.get("typeName"))
        struct = AtlasStruct(type_name=type_name)
        struct_type = self._store.registry.struct_type(type_name)
        stored = value.get("attributes")
        stored = stored if isinstance(stored, Mapping) else {}
        if struct_type is not None:
            await self._load(_references_of(stored, struct_type.all_attributes.values(), qualified=False))
            for name, attribute in struct_type.all_attributes.items():
                struct.set_attribute(name, await self._attribute(attribute, stored.get(name), ext_info=ext_info))
        return struct

    async def _soft_references(self, value: object, *, owned: bool) -> Any:  # noqa: ANN401 - Atlas JSON
        """``mapVertexTo{ObjectId,Array,Map}ForSoftRef``: ``typeName:guid`` values; empty collections as stored."""
        if isinstance(value, list):
            if not value:
                return value
            items = [await self._soft_reference(java_string(item), owned=owned) for item in value]
            return [item for item in items if item is not None]
        if isinstance(value, Mapping):
            if not value:
                return value
            entries = {
                str(key): await self._soft_reference(java_string(item), owned=owned) for key, item in value.items()
            }
            return {key: item for key, item in entries.items() if item is not None}
        return await self._soft_reference(value, owned=owned) if isinstance(value, str) and value else None

    async def _soft_reference(self, value: str, *, owned: bool) -> AtlasObjectId | None:
        """``getAtlasObjectIdFromSoftRefFormat``: an owned entity found is added and named by its unique values."""
        parts = [part for part in value.split(SOFT_REFERENCE_SEPARATOR) if part]
        if len(parts) < 2:  # noqa: PLR2004 - type name and GUID
            return None
        object_id = AtlasObjectId(guid=parts[1], type_name=parts[0])
        stored = await self._get(parts[1]) if owned else None
        if stored is None:
            return object_id
        entity = await (self.min_entity(stored) if self._min_ext_info else self.entity(stored))
        entity_type = self._store.registry.entity_type(entity.type_name)
        unique = {
            name: entity.get_attribute(name)
            for name in ([] if entity_type is None else entity_type.unique_attributes)
            if entity.get_attribute(name) is not None
        }
        return AtlasObjectId(guid=entity.guid, type_name=entity.type_name, unique_attributes=unique)


def _contained(type_: AtlasType) -> AtlasType | None:
    if isinstance(type_, ArrayType):
        return resolved(type_.element_type)
    if isinstance(type_, MapType):
        return resolved(type_.value_type)
    return None


def _is_reference(type_: AtlasType) -> bool:
    return type_.category in _REFERENCES or type_.category is TypeCategory.STRUCT


def _references_of(values: Mapping[str, Any], attributes: Iterable[AtlasAttribute], *, qualified: bool) -> list[str]:
    """The GUIDs of the plain references among these values, to read in one request."""
    guids: list[str] = []
    for attribute in attributes:
        value = values.get(attribute.qualified_name if qualified else str(attribute.name))
        if value is None or attribute.attribute_def.is_soft_referenced():
            continue
        type_ = attribute.attribute_type
        contained = _contained(type_)
        if type_.category in _REFERENCES:
            guids.append(str(value))
        elif contained is not None and contained.category in _REFERENCES:
            items = value.values() if isinstance(value, Mapping) else value if isinstance(value, list) else []
            guids += [str(item) for item in items if item is not None]
    return guids
