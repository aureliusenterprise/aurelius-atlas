"""``RelationshipStore``: relationship instances as ``AtlasRelationshipStoreV2`` keeps them (REL-04 to REL-08).

A relationship is a document of its own, and both its ends list its GUID (DD-061); creating, changing and deleting
one writes those documents together, all or nothing (DD-062), and runs again once after a lost race (DD-052).
"""

from collections.abc import Awaitable, Callable
from typing import Any

from aurelius_atlas_model import codec
from aurelius_atlas_model.errors import AtlasError, AtlasErrorCode, java_string
from aurelius_atlas_model.instance import (
    AtlasObjectId,
    AtlasRelationship,
    AtlasRelationshipWithExtInfo,
    RelationshipStatus,
)
from aurelius_atlas_model.typedef import PropagateTags
from aurelius_atlas_typesystem.builtin.object_id_type import is_assigned_guid
from aurelius_atlas_typesystem.entity_type import EntityType
from aurelius_atlas_typesystem.relationship_type import RelationshipType

from aurelius_atlas_core.delete_type import DeleteType
from aurelius_atlas_core.entity_documents import VersionedEntity, VersionedRelationship
from aurelius_atlas_core.entity_retriever import EntityRetriever
from aurelius_atlas_core.entity_store import (
    EntityChange,
    EntityStore,
    EntityVersionConflictError,
    EntityWriteError,
    RelationshipChange,
    UniqueValueTakenError,
)
from aurelius_atlas_core.stored_entity import StoredEntity
from aurelius_atlas_core.stored_relationship import StoredRelationship

ATTEMPTS = 2
"""A request that loses a race is run once more (DD-052)."""

UNKNOWN_TYPE = "unknown relationship type'{name}'"
EMPTY_GUID = " empty/null guid"

_SWAPPED = {PropagateTags.ONE_TO_TWO: PropagateTags.TWO_TO_ONE, PropagateTags.TWO_TO_ONE: PropagateTags.ONE_TO_TWO}


class RelationshipStore:
    """Relationships between entities of ``store``, written as ``user``; ``delete_type`` is the default (EDL-04)."""

    def __init__(
        self, store: EntityStore, *, user: str | None = None, delete_type: DeleteType = DeleteType.SOFT
    ) -> None:
        self._store = store
        self._user = user
        self._delete_type = DeleteType.SOFT if delete_type is DeleteType.DEFAULT else delete_type

    async def create(self, relationship: AtlasRelationship) -> AtlasRelationship:
        """``create``: a new relationship between two entities, unless one with its label joins them (REL-04, REL-05).

        Raises:
            AtlasError: ``INVALID_VALUE``, ``RELATIONSHIP_END_IS_NULL``, ``INVALID_RELATIONSHIP_END_TYPE``,
                ``INVALID_PROPAGATION_TYPE``, ``RELATIONSHIP_CRUD_INVALID_PARAMS`` or ``RELATIONSHIP_ALREADY_EXISTS``.
        """
        return await self._run(lambda: self._create(relationship.model_copy(deep=True)))

    async def update(self, relationship: AtlasRelationship) -> AtlasRelationship:
        """``update``: the given tag propagation and attributes; type and ends may not change (REL-07).

        Raises:
            AtlasError: ``RELATIONSHIP_GUID_NOT_FOUND``, ``RELATIONSHIP_UPDATE_TYPE_CHANGE_NOT_ALLOWED``,
                ``RELATIONSHIP_UPDATE_END_CHANGE_NOT_ALLOWED``, or what ``create`` checks.
        """
        return await self._run(lambda: self._update(relationship.model_copy(deep=True)))

    async def get_by_id(self, guid: str) -> AtlasRelationship:
        """``getById``: the relationship with ``guid``, in any state (REL-06).

        Raises:
            AtlasError: ``RELATIONSHIP_GUID_NOT_FOUND``.
        """
        return await self._answer((await self._found(guid)).relationship)

    async def get_ext_info_by_id(self, guid: str) -> AtlasRelationshipWithExtInfo:
        """``getExtInfoById``: the relationship and the headers of its ends (REL-06).

        Raises:
            AtlasError: ``RELATIONSHIP_GUID_NOT_FOUND``.
        """
        stored = (await self._found(guid)).relationship
        result = AtlasRelationshipWithExtInfo(relationship=await self._answer(stored))
        retriever = EntityRetriever(self._store)
        for end in stored.ends():
            if not result.referred_entities_contains(end):
                result.add_referred_entity(end, await retriever.header(end, classifications=False))
        return result

    async def delete_by_id(self, guid: str, delete_type: DeleteType = DeleteType.DEFAULT) -> None:
        """``deleteById``: soft-delete the relationship, or remove it and drop it from its ends (REL-08).

        Raises:
            AtlasError: ``RELATIONSHIP_CRUD_INVALID_PARAMS`` for no GUID, ``RELATIONSHIP_GUID_NOT_FOUND``,
                ``RELATIONSHIP_ALREADY_DELETED``.
        """
        if not guid:
            raise AtlasError(AtlasErrorCode.RELATIONSHIP_CRUD_INVALID_PARAMS, EMPTY_GUID)
        hard = (self._delete_type if delete_type is DeleteType.DEFAULT else delete_type) is DeleteType.HARD

        async def delete() -> None:
            found = await self._found(guid)
            stored = found.relationship
            if stored.state is RelationshipStatus.DELETED:
                raise AtlasError(AtlasErrorCode.RELATIONSHIP_ALREADY_DELETED, guid)
            if not hard:
                deleted = stored.model_copy(
                    update={
                        "state": RelationshipStatus.DELETED,
                        "update_time": self._store.now(),
                        "updated_by": self._user,
                    }
                )
                await self._store.write([], [RelationshipChange(deleted, found.version)])
                return
            ends = await self._store.get_many(list(stored.ends()))
            changes = [EntityChange(end.entity.unlisting({guid}), end.version) for end in ends.values()]
            await self._store.write(changes, [RelationshipChange(stored, found.version, remove=True)])

        await self._run(delete)

    async def _run[T](self, attempt: Callable[[], Awaitable[T]]) -> T:
        """Run once more after a lost race; a second loss or a failed write is ``INTERNAL_ERROR`` (DD-052)."""
        for number in range(1, ATTEMPTS + 1):
            try:
                return await attempt()
            except EntityVersionConflictError as conflict:
                if number == ATTEMPTS:
                    raise AtlasError(AtlasErrorCode.INTERNAL_ERROR, str(conflict)) from conflict
            except (UniqueValueTakenError, EntityWriteError) as failure:
                raise AtlasError(AtlasErrorCode.INTERNAL_ERROR, str(failure)) from failure
        raise AssertionError  # pragma: no cover - the loop returns or raises

    async def _create(self, relationship: AtlasRelationship) -> AtlasRelationship:
        end1 = await self._end(relationship.end1)
        end2 = await self._end(relationship.end2)
        relationship_type, end1, end2 = self._validate(end1, end2, relationship)
        label = _edge_label(relationship_type, end1.entity, end2.entity)
        listed = await self._store.get_relationships(end1.entity.relationship_guids or [])
        for found in listed.values():
            existing = found.relationship
            if (existing.end1_guid, existing.end2_guid, existing.label) == (end1.entity.guid, end2.entity.guid, label):
                raise AtlasError(
                    AtlasErrorCode.RELATIONSHIP_ALREADY_EXISTS,
                    relationship.type_name,
                    end1.entity.guid,
                    end2.entity.guid,
                )
        now = self._store.now()
        stored = StoredRelationship(
            guid=given if (given := relationship.guid) and is_assigned_guid(given) else self._store.new_guid(),
            type_name=str(relationship_type.type_name),
            label=label,
            end1_guid=end1.entity.guid,
            end2_guid=end2.entity.guid,
            propagate_tags=_tag_propagation(relationship_type, end1.entity, end2.entity),
            create_time=now,
            update_time=now,
            created_by=self._user,
            updated_by=self._user,
            version=relationship.version or 0,
            provenance_type=relationship.provenance_type,
            home_id=relationship.home_id,
            attributes={
                name: _stored(relationship.get_attribute(name))
                for name in relationship_type.all_attributes
                if relationship.get_attribute(name) is not None
            },
        )
        ends = {end1.entity.guid: end1, end2.entity.guid: end2}
        changes = [EntityChange(end.entity.listing(stored.guid), end.version) for end in ends.values()]
        await self._store.write(changes, [RelationshipChange(stored)])
        return await self._answer(stored)

    async def _update(self, relationship: AtlasRelationship) -> AtlasRelationship:
        guid = relationship.guid
        if not guid:
            raise AtlasError(AtlasErrorCode.RELATIONSHIP_GUID_NOT_FOUND, guid)
        found = await self._found(guid)
        stored = found.relationship
        if relationship.type_name and relationship.type_name.lower() != stored.type_name.lower():
            raise AtlasError(
                AtlasErrorCode.RELATIONSHIP_UPDATE_TYPE_CHANGE_NOT_ALLOWED,
                guid,
                stored.type_name,
                relationship.type_name,
            )
        for given, current in ((relationship.end1, stored.end1_guid), (relationship.end2, stored.end2_guid)):
            await self._check_end_unchanged(given, current, stored)
        ends = await self._store.get_many(list(stored.ends()))
        unnamed = not relationship.type_name
        if unnamed:
            relationship.type_name = stored.type_name
        relationship_type, _, _ = self._validate(ends.get(stored.end1_guid), ends.get(stored.end2_guid), relationship)
        if unnamed:
            relationship.type_name = None
        update: dict[str, Any] = {"attributes": _updated_attributes(relationship_type, relationship, stored)}
        if relationship.propagate_tags is not None:
            update["propagate_tags"] = relationship.propagate_tags  # DV-29: none given keeps the stored one
        changed = stored.model_copy(update=update)
        await self._store.write([], [RelationshipChange(changed, found.version)])
        return await self._answer(changed)

    async def _check_end_unchanged(self, given: AtlasObjectId | None, current: str, stored: StoredRelationship) -> None:
        """An end may not change; one given by unique attributes alone always fails, as Atlas compares GUIDs."""
        if given is None:
            return
        updated = given.guid
        if updated is None:
            found = await self._end(given)
            updated = None if found is None else found.entity.guid
        if updated is not None and (given.guid or "").lower() != current.lower():
            raise AtlasError(
                AtlasErrorCode.RELATIONSHIP_UPDATE_END_CHANGE_NOT_ALLOWED,
                stored.type_name,
                stored.guid,
                current,
                given.guid,
            )

    def _validate(
        self, end1: VersionedEntity | None, end2: VersionedEntity | None, relationship: AtlasRelationship
    ) -> tuple[RelationshipType, VersionedEntity, VersionedEntity]:
        """``validateRelationship``: type, ends, end types, tag propagation, then the type's value checks.

        Answers the type and both ends, found.
        """
        name = relationship.type_name
        relationship_type = self._store.registry.relationship_type(name)
        if relationship_type is None:
            raise AtlasError(AtlasErrorCode.INVALID_VALUE, UNKNOWN_TYPE.format(name=java_string(name)))
        end1_type, end2_type = _types(relationship_type)
        if end1 is None:
            raise AtlasError(AtlasErrorCode.RELATIONSHIP_END_IS_NULL, end1_type.type_name)
        if end2 is None:
            raise AtlasError(AtlasErrorCode.RELATIONSHIP_END_IS_NULL, end2_type.type_name)
        name1, name2 = end1.entity.type_name, end2.entity.type_name
        if _of_type(end1_type, name1):
            valid = _of_type(end2_type, name2)
        else:
            valid = _of_type(end2_type, name1) and _of_type(end1_type, name2)
        if not valid:
            raise AtlasError(AtlasErrorCode.INVALID_RELATIONSHIP_END_TYPE, name, end2_type.type_name, name1)
        type_propagation = relationship_type.relationship_def.propagate_tags or PropagateTags.NONE
        propagation = relationship.propagate_tags or PropagateTags.NONE
        if (
            propagation is not PropagateTags.NONE
            and type_propagation is not PropagateTags.BOTH
            and propagation is not type_propagation
        ):
            raise AtlasError(AtlasErrorCode.INVALID_PROPAGATION_TYPE, propagation.value, name, type_propagation.value)
        messages: list[str] = []
        relationship_type.validate_value(relationship, str(name), messages)
        if messages:
            raise AtlasError(AtlasErrorCode.RELATIONSHIP_CRUD_INVALID_PARAMS, messages)
        relationship_type.get_normalized_value(relationship)
        return relationship_type, end1, end2

    async def _end(self, end: AtlasObjectId | None) -> VersionedEntity | None:
        """``getVertexFromEndPoint``: by GUID in any state, else the ``ACTIVE`` holder of the unique values."""
        if end is None:
            return None
        if end.guid:
            return await self._store.get(end.guid)
        entity_type = self._store.registry.entity_type(end.type_name) if end.type_name else None
        if entity_type is None or not end.unique_attributes:
            return None
        return await self._store.find_by_unique_attributes(entity_type, end.unique_attributes)

    async def _found(self, guid: str) -> VersionedRelationship:
        found = (await self._store.get_relationships([guid])).get(guid)
        if found is None:
            raise AtlasError(AtlasErrorCode.RELATIONSHIP_GUID_NOT_FOUND, guid)
        return found

    async def _answer(self, stored: StoredRelationship) -> AtlasRelationship:
        """``mapEdgeToAtlasRelationship``: the ends as object ids with their unique values (REL-06)."""
        ends = await self._store.get_many(list(stored.ends()))
        retriever = EntityRetriever(self._store)
        object_ids = []
        for guid in stored.ends():
            found = ends.get(guid)
            object_id = None if found is None else await retriever.object_id_of(found.entity)
            object_ids.append(object_id or AtlasObjectId(guid=guid))
        relationship_type = self._store.registry.relationship_type(stored.type_name)
        names = [] if relationship_type is None else [str(name) for name in relationship_type.all_attributes]
        return stored.to_relationship(object_ids[0], object_ids[1], names)


def _types(relationship_type: RelationshipType) -> tuple[EntityType, EntityType]:
    end1_type, end2_type = relationship_type.end1_type, relationship_type.end2_type
    if end1_type is None or end2_type is None:  # pragma: no cover - a registered relationship type has both
        raise AtlasError(AtlasErrorCode.INVALID_VALUE, UNKNOWN_TYPE.format(name=relationship_type.type_name))
    return end1_type, end2_type


def _of_type(entity_type: EntityType, type_name: str) -> bool:
    """``isTypeOrSuperTypeOf``."""
    return type_name == entity_type.type_name or entity_type.is_super_type_of(type_name)


def _type_and_super_types(store_entity: StoredEntity) -> set[str]:
    return {store_entity.type_name, *store_entity.super_type_names}


def _edge_label(relationship_type: RelationshipType, from_entity: StoredEntity, to_entity: StoredEntity) -> str | None:
    """``getRelationshipEdgeLabel``: the label of the relationship attribute of the end ``from_entity`` is."""
    end1_def, end2_def = relationship_type.relationship_def.end_def1, relationship_type.relationship_def.end_def2
    end1_type, end2_type = _types(relationship_type)
    from_types, to_types = _type_and_super_types(from_entity), _type_and_super_types(to_entity)
    attribute = None
    if end1_def is not None and end2_def is not None:
        if end1_def.type in from_types and end2_def.type in to_types:
            attribute = end1_type.relationship_attribute(str(end1_def.name), str(relationship_type.type_name))
        elif end2_def.type in from_types and end1_def.type in to_types:
            attribute = end2_type.relationship_attribute(str(end2_def.name), str(relationship_type.type_name))
    return relationship_type.relationship_label if attribute is None else attribute.relationship_edge_label


def _tag_propagation(
    relationship_type: RelationshipType, from_entity: StoredEntity, to_entity: StoredEntity
) -> PropagateTags:
    """``getRelationshipTagPropagation``: the type's, swapped when end 1 is of the type's end 2 type (REL-05)."""
    definition = relationship_type.relationship_def
    propagation = definition.propagate_tags or PropagateTags.NONE
    end1_def, end2_def = definition.end_def1, definition.end_def2
    if (
        end1_def is not None
        and end2_def is not None
        and end2_def.type in _type_and_super_types(from_entity)
        and end1_def.type in _type_and_super_types(to_entity)
    ):
        return _SWAPPED.get(propagation, propagation)
    return propagation


def _updated_attributes(
    relationship_type: RelationshipType, relationship: AtlasRelationship, stored: StoredRelationship
) -> dict[str, Any]:
    """``updateRelationship``: each given attribute, else a non-empty default; others stay (REL-07)."""
    attributes = dict(stored.attributes)
    for name, attribute in relationship_type.all_attributes.items():
        if relationship.has_attribute(name):
            value = relationship.get_attribute(name)
            if value is None:
                attributes.pop(name, None)
            else:
                attributes[name] = _stored(value)
        elif attribute.attribute_def.default_value:
            default = attribute.attribute_type.create_default_value_of(attribute.attribute_def.default_value)
            if default is not None:
                attributes[name] = _stored(default)
    return attributes


def _stored(value: object) -> Any:  # noqa: ANN401 - a stored value
    """A value as stored: the codec's JSON of it, a date as epoch milliseconds (DD-049)."""
    return codec.loads(codec.dumps(value))
