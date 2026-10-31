"""``EntityRetriever``: entities, headers and object ids built from stored entities (ERD-02 to ERD-09).

The read side of ``EntityGraphRetriever`` and ``AtlasEntityStoreV2``: what Atlas maps from a vertex and its edges,
here from an entity document, the documents its references name and its relationships (DD-049, DD-064).
"""

from collections.abc import Iterable, Mapping, Sequence
from typing import Any

from aurelius_atlas_model.errors import AtlasError, AtlasErrorCode, java_string
from aurelius_atlas_model.instance import (
    AtlasClassification,
    AtlasEntitiesWithExtInfo,
    AtlasEntity,
    AtlasEntityExtInfo,
    AtlasEntityHeader,
    AtlasEntityWithExtInfo,
    AtlasObjectId,
    AtlasRelatedObjectId,
    AtlasStruct,
    AtlasTermAssignmentHeader,
    AtlasTermAssignmentStatus,
    EntityStatus,
    RelationshipStatus,
)
from aurelius_atlas_model.typedef import AtlasRelationshipEndDef, Cardinality, TypeCategory
from aurelius_atlas_typesystem.array_type import ArrayType
from aurelius_atlas_typesystem.atlas_type import AtlasType, resolved
from aurelius_atlas_typesystem.attribute import AtlasAttribute
from aurelius_atlas_typesystem.entity_type import EntityType
from aurelius_atlas_typesystem.map_type import MapType
from aurelius_atlas_typesystem.relationship_type import RelationshipType
from pydantic.alias_generators import to_camel

from aurelius_atlas_core.entity_store import EntityStore
from aurelius_atlas_core.graph_helper import (
    collection_elements,
    edge_for_label,
    edges_for_label,
    other_end,
    relationship_type_name,
)
from aurelius_atlas_core.stored_classification import StoredClassification
from aurelius_atlas_core.stored_entity import StoredEntity
from aurelius_atlas_core.stored_relationship import StoredRelationship

SOFT_REFERENCE_SEPARATOR = ":"
"""``typeName:guid``, how Atlas holds a soft reference (DD-049)."""

DISPLAY_TEXT_FALLBACKS = ("name", "displayName", "qualifiedName")
"""The attributes ``getDisplayText`` tries, in order, after the type's display text attribute."""

QUALIFIED_NAME = "qualifiedName"
TERM_ASSIGNMENT = "AtlasGlossarySemanticAssignment"
"""The relationship type of a term's assignment to an entity (``TERM_ASSIGNMENT_LABEL``, GTA-05)."""

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

    async def header(self, guid: str, *, classifications: bool = True) -> AtlasEntityHeader:
        """The header of the entity with ``guid``, with its classifications (ERD-07, CLS-02, ``getHeaderById``).

        Without ``classifications``, as ``toAtlasEntityHeader`` answers it (EWR-13).

        Raises:
            AtlasError: ``INSTANCE_GUID_NOT_FOUND`` when no entity has the GUID.
        """
        reading = self._reading(AtlasEntityExtInfo())
        stored = await self._found(guid)
        header = await reading.header(stored)
        if classifications:
            header.classifications = await reading.classifications(stored)
        return header

    async def header_with_attributes(self, stored: StoredEntity, attributes: Iterable[str]) -> AtlasEntityHeader:
        """``toAtlasEntityHeader(vertex, attributes)``: the header, and the attributes named that have a value (SRC-09).

        A name the type has no attribute of is read without its type prefix, also as a relationship attribute.
        """
        reading = self._reading(AtlasEntityExtInfo())
        header = await reading.header(stored)
        entity_type = self._store.registry.entity_type(stored.type_name)
        for given in attributes:
            name, attribute = given, None if entity_type is None else entity_type.attribute(given)
            if attribute is None and entity_type is not None:
                name = given.rsplit(".", 1)[-1]
                if header.has_attribute(name):
                    continue
                attribute = entity_type.attribute(name) or entity_type.relationship_attribute(name)
            value = None if attribute is None else await reading._vertex_attribute(stored, attribute)  # noqa: SLF001
            if value is not None:
                header.set_attribute(name, value)
        return header

    async def classifications(self, guid: str) -> list[AtlasClassification]:
        """``getAllClassifications``: the classifications of the entity with ``guid``, in order (CLS-02, CLS-03).

        Raises:
            AtlasError: ``INSTANCE_GUID_NOT_FOUND`` when no entity has the GUID.
        """
        return await self._reading(AtlasEntityExtInfo()).classifications(await self._found(guid))

    async def classification_of(self, stored: StoredClassification) -> AtlasClassification:
        """``toAtlasClassification``: a stored instance as Atlas answers it, every attribute of its type (CLS-02)."""
        return await self._reading(AtlasEntityExtInfo())._classification(stored)  # noqa: SLF001 - same module

    async def object_id_of(self, stored: StoredEntity) -> AtlasObjectId | None:
        """The entity as a relationship's end: GUID, type and unique values, none when it has none (REL-06).

        ``getEntityUniqueAttribute`` answers null rather than an empty map.
        """
        object_id = await self._reading(AtlasEntityExtInfo()).object_id(stored)
        if object_id is not None and not object_id.unique_attributes:
            object_id.unique_attributes = None
        return object_id

    async def entity_attribute(self, stored: StoredEntity, attribute: AtlasAttribute) -> Any:  # noqa: ANN401 - Atlas JSON
        """``getEntityAttribute``: the stored value of ``attribute`` as a read answers it, without referred entities.

        What ``AtlasEntityComparator`` compares a request's value with (EWR-08).
        """
        return await self._reading(AtlasEntityExtInfo())._vertex_attribute(stored, attribute)  # noqa: SLF001 - same module

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
        self._edges: dict[str, list[StoredRelationship]] = {}
        self._classified: dict[str, list[AtlasClassification]] = {}

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
            entity.set_attribute(name, await self._entity_attribute(stored, attribute, ext_info=True))
        if self._relationships:
            for name in entity_type.relationship_attributes:
                await self._relationship_attribute(stored, entity_type, name, entity)
        entity.classifications = await self.classifications(stored) or None
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
        entity.classifications = await self.classifications(stored) or None
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
            classification_names=[str(found.type_name) for found in await self.classifications(stored)],
            is_incomplete=stored.is_incomplete,
            labels=stored.labels or [],
        )
        header.meanings = await self.meanings(stored)
        header.meaning_names = [meaning.display_text for meaning in header.meanings if meaning.display_text is not None]
        for name, attribute in entity_type.header_attributes.items():
            value = await self._vertex_attribute(stored, attribute)
            header.set_attribute(name, "" if value is None else value)
        display_text = await self._display_text(stored, entity_type)
        if display_text is not None:
            header.display_text = java_string(display_text)
        return header

    async def meanings(self, stored: StoredEntity) -> list[AtlasTermAssignmentHeader]:
        """``mapAssignedTerms``: the terms assigned to the entity, by assignments in any state (GTA-05).

        An assignment's status that is no ``AtlasTermAssignmentStatus`` is left out (DV-103).
        """
        assignments = [
            found
            for found in await self._relationships_of(stored)
            if found.type_name == TERM_ASSIGNMENT and found.end2_guid == stored.guid
        ]
        await self._load(found.end1_guid for found in assignments)
        meanings = []
        for found in assignments:
            term = self._stored.get(found.end1_guid)
            attributes = {} if term is None else term.attributes
            header = AtlasTermAssignmentHeader(
                term_guid=found.end1_guid,
                relation_guid=found.guid,
                display_text=_text(attributes.get("AtlasGlossaryTerm.name")),
                qualified_name=_text(attributes.get("AtlasGlossaryTerm.qualifiedName")),
            )
            values = found.attributes
            for name in ("description", "expression", "created_by", "steward", "source"):
                value = values.get(to_camel(name))
                if isinstance(value, str):
                    setattr(header, name, value)
            if isinstance(values.get("confidence"), int):
                header.confidence = values["confidence"]
            if values.get("status") in AtlasTermAssignmentStatus.__members__:
                header.status = AtlasTermAssignmentStatus(values["status"])
            meanings.append(header)
        return meanings

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

    async def classifications(self, stored: StoredEntity) -> list[AtlasClassification]:
        """``mapClassifications``: the entity's classifications, in the order it lists them (CLS-02, DD-070).

        Read once per entity and response; each has every attribute of its type, null when it has no value.
        """
        if stored.guid not in self._classified:
            listed = stored.classification_guids or []
            found = await self._store.get_classifications(listed)
            self._classified[stored.guid] = [
                await self._classification(found[guid].classification) for guid in listed if guid in found
            ]
        return [found.model_copy(deep=True) for found in self._classified[stored.guid]]

    async def _classification(self, stored: StoredClassification) -> AtlasClassification:
        """``toAtlasClassification``: the system fields and every attribute of the classification's type."""
        classification = stored.to_classification()
        classification_type = self._store.registry.classification_type(stored.type_name)
        if classification_type is not None:
            for name, attribute in classification_type.all_attributes.items():
                classification.set_attribute(
                    name, await self._attribute(attribute, stored.attributes.get(str(name)), ext_info=False)
                )
        return classification

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
        return await self._entity_attribute(stored, attribute, ext_info=False)

    async def _display_text(self, stored: StoredEntity, entity_type: EntityType) -> Any:  # noqa: ANN401 - Atlas JSON
        """``getDisplayText``: the display text attribute's value, else the first fallback with one (ERD-07)."""
        for name in (entity_type.display_text_attribute, *DISPLAY_TEXT_FALLBACKS):
            attribute = entity_type.attribute(name)
            value = None if attribute is None else await self._vertex_attribute(stored, attribute)
            if value is not None:
                return value
        return None

    async def _entity_attribute(self, stored: StoredEntity, attribute: AtlasAttribute, *, ext_info: bool) -> Any:  # noqa: ANN401 - Atlas JSON
        """``mapVertexToAttribute`` of an entity: a relationship end through its relationships (REL-18)."""
        if attribute.relationship_name is not None:
            return await self._relationship_end(stored, attribute, ext_info=ext_info)
        return await self._attribute(attribute, stored.attributes.get(attribute.qualified_name), ext_info=ext_info)

    async def _relationships_of(self, stored: StoredEntity) -> list[StoredRelationship]:
        """The entity's relationships, in the order it lists them, read once per response (DD-061)."""
        if stored.guid not in self._edges:
            listed = stored.relationship_guids or []
            found = await self._store.get_relationships(listed)
            self._edges[stored.guid] = [found[guid].relationship for guid in listed if guid in found]
        return self._edges[stored.guid]

    async def _relationship_end(self, stored: StoredEntity, attribute: AtlasAttribute, *, ext_info: bool) -> Any:  # noqa: ANN401 - Atlas JSON
        """``mapVertexToObjectId`` and ``mapVertexToArray`` over relationships: the other ends (REL-18)."""
        relationships = await self._relationships_of(stored)
        owned = ext_info and attribute.is_owned_ref
        if attribute.attribute_type.category in _REFERENCES:
            edge = edge_for_label(
                stored.guid, relationships, attribute.relationship_edge_label, attribute.relationship_edge_direction
            )
            return None if edge is None else await self._reference(other_end(edge, stored.guid), owned=owned)
        if not isinstance(attribute.attribute_type, ArrayType):  # pragma: no cover - an end is a reference or array
            return None
        guids = [other_end(edge, stored.guid) for edge in collection_elements(stored.guid, relationships, attribute)]
        await self._load(guids)
        items = [await self._reference(guid, owned=owned) for guid in guids]
        return [item for item in items if item is not None]

    async def _relationship_attribute(
        self, stored: StoredEntity, entity_type: EntityType, name: str, entity: AtlasEntity
    ) -> None:
        """``mapVertexToRelationshipAttribute``: related object ids, and a legacy end not otherwise read (REL-17).

        Raises:
            AtlasError: ``RELATIONSHIPDEF_INVALID`` when the attribute has no relationship type or end.
        """
        relationships = await self._relationships_of(stored)
        type_name = relationship_type_name(stored.guid, relationships, entity_type, name)
        relationship_type = None if type_name is None else self._store.registry.relationship_type(type_name)
        if relationship_type is None:  # pragma: no cover - a relationship attribute has a relationship type
            raise AtlasError(AtlasErrorCode.RELATIONSHIPDEF_INVALID, "relationshipDef is null")
        attribute = entity_type.relationship_attribute(name, type_name)
        end = _end_of(relationship_type, entity_type, name)
        if attribute is None or end is None:  # pragma: no cover - the registry added the attribute for this end
            raise AtlasError(AtlasErrorCode.RELATIONSHIPDEF_INVALID, relationship_type.type_name)
        label, direction = attribute.relationship_edge_label, attribute.relationship_edge_direction
        if end.cardinality in (Cardinality.LIST, Cardinality.SET):
            edges = edges_for_label(stored.guid, relationships, label, direction)
            await self._load(other_end(edge, stored.guid) for edge in edges)
            related = [await self._related(stored, edge, owned=attribute.is_owned_ref) for edge in edges]
            value: Any = [item for item in related if item is not None]
        else:
            edge = edge_for_label(stored.guid, relationships, label, direction)
            value = None if edge is None else await self._related(stored, edge, owned=attribute.is_owned_ref)
        if entity.relationship_attributes is None:
            entity.relationship_attributes = {}
        entity.relationship_attributes[name] = value
        if end.is_legacy_attribute and not entity.has_attribute(name):
            entity.set_attribute(name, _legacy(value))

    async def _related(
        self, stored: StoredEntity, edge: StoredRelationship, *, owned: bool
    ) -> AtlasRelatedObjectId | None:
        """``mapVertexToRelatedObjectId``: the other end, with its status and display text, and the relationship."""
        other = await self._get(other_end(edge, stored.guid))
        if other is None:
            return None
        relationship_type = self._store.registry.relationship_type(edge.type_name)
        names = [] if relationship_type is None else [str(name) for name in relationship_type.all_attributes]
        related = AtlasRelatedObjectId(
            guid=other.guid,
            type_name=other.type_name,
            entity_status=other.state,
            relationship_type=edge.type_name,
            relationship_guid=edge.guid,
            relationship_status=edge.state,
            relationship_attributes=AtlasStruct(
                type_name=edge.type_name, attributes={name: edge.attributes.get(name) for name in names} or None
            ),
        )
        entity_type = self._store.registry.entity_type(other.type_name)
        if entity_type is not None:
            display_text = await self._display_text(other, entity_type)
            if display_text is not None:
                related.display_text = java_string(display_text)
            qualified_name = entity_type.attribute(QUALIFIED_NAME)
            value = None if qualified_name is None else await self._vertex_attribute(other, qualified_name)
            if value is not None:
                related.qualified_name = java_string(value)
        if owned:
            await (self.min_entity(other) if self._min_ext_info else self.entity(other))
        return related

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


def _end_of(relationship_type: RelationshipType, entity_type: EntityType, name: str) -> AtlasRelationshipEndDef | None:
    """The end of ``relationship_type`` whose type is or is a super type of ``entity_type`` and is named ``name``."""
    definition = relationship_type.relationship_def
    for end, end_type in (
        (definition.end_def1, relationship_type.end1_type),
        (definition.end_def2, relationship_type.end2_type),
    ):
        if (
            end is not None
            and end_type is not None
            and end.name == name
            and (end_type.type_name == entity_type.type_name or end_type.is_super_type_of(str(entity_type.type_name)))
        ):
            return end
    return None


def _legacy(value: object) -> Any:  # noqa: ANN401 - Atlas JSON
    """``toLegacyAttribute``: object ids without the relationship; a deleted one to an active entity left out."""
    if isinstance(value, AtlasRelatedObjectId):
        if value.relationship_status is RelationshipStatus.DELETED and value.entity_status is EntityStatus.ACTIVE:
            return None
        return AtlasObjectId(guid=value.guid, type_name=value.type_name, unique_attributes=value.unique_attributes)
    if isinstance(value, list):
        return [found for item in value if (found := _legacy(item)) is not None]
    return value


def _references_of(values: Mapping[str, Any], attributes: Iterable[AtlasAttribute], *, qualified: bool) -> list[str]:
    """The GUIDs of the plain references among these values, to read in one request."""
    guids: list[str] = []
    for attribute in attributes:
        value = values.get(attribute.qualified_name if qualified else str(attribute.name))
        if value is None or attribute.attribute_def.is_soft_referenced() or attribute.relationship_name is not None:
            continue
        type_ = attribute.attribute_type
        contained = _contained(type_)
        if type_.category in _REFERENCES:
            guids.append(str(value))
        elif contained is not None and contained.category in _REFERENCES:
            items = value.values() if isinstance(value, Mapping) else value if isinstance(value, list) else []
            guids += [str(item) for item in items if item is not None]
    return guids


def _text(value: object) -> str | None:
    return value if isinstance(value, str) else None
