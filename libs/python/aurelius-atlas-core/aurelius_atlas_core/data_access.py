"""``DataAccess``: model objects saved and loaded as the entities of internal types (DD-246, DD-252).

Each kind of object has a data transfer object that makes its entities and reads it back: the glossary's objects
(5.2), the user profile and its saved searches (4.5). An object is saved as its entity and those it refers to,
created or updated, and loaded by GUID, or by its unique attributes while it has no GUID of the store.
"""

from collections.abc import Iterable, Mapping, Sequence
from typing import Any, Protocol

from aurelius_atlas_model.errors import AtlasError, AtlasErrorCode
from aurelius_atlas_model.instance import AtlasEntitiesWithExtInfo, AtlasEntity, AtlasEntityWithExtInfo, EntityStatus

from aurelius_atlas_core.delete_type import DeleteType
from aurelius_atlas_core.entity_retriever import EntityRetriever
from aurelius_atlas_core.entity_store import EntityStore
from aurelius_atlas_core.entity_writer import EntityWriter


class ModelObject(Protocol):
    """``AtlasBaseModelObject``: an object with a GUID, negative until the store assigns one."""

    guid: str


class DataTransferObject[T: ModelObject](Protocol):
    """``DataTransferObject``: one kind of object as the entities of ``type_name``."""

    @property
    def type_name(self) -> str:
        """The entity type the object is stored as."""
        ...

    def from_entity(self, found: AtlasEntityWithExtInfo) -> T:
        """``from``: the object of an entity read with the entities it refers to."""
        ...

    def to_entities(self, obj: T) -> list[AtlasEntity]:
        """``toEntityWithExtInfo``: the object's entity first, then those it refers to."""
        ...

    def unique_attributes(self, obj: T) -> dict[str, Any]:
        """``getUniqueAttributes``: the attributes a new object is found by."""
        ...


type Registry = Mapping[type, DataTransferObject[Any]]
"""The data transfer objects by the class of the objects they carry (``DTORegistry``)."""


class DataAccess:
    """``DataAccess``: the objects ``dtos`` carry, as the entities of ``store``, written as ``user``."""

    def __init__(self, store: EntityStore, dtos: Registry, *, user: str | None = None) -> None:
        self._store = store
        self._dtos = dtos
        self._user = user

    async def save[T: ModelObject](self, obj: T) -> T:
        """``save``: create or update the object's entities, its new GUID taken, and load it back."""
        response = await EntityWriter(self._store, user=self._user).create_or_update(
            AtlasEntitiesWithExtInfo(entities=self._dto(obj).to_entities(obj))
        )
        assigned = (response.guid_assignments or {}).get(obj.guid)
        if response.get_created_entities() and assigned is not None and assigned != obj.guid:
            obj.guid = assigned
        return await self.load(obj)

    async def save_all[T: ModelObject](self, objects: Iterable[T]) -> list[T]:
        """``save`` of each, in order."""
        return [await self.save(obj) for obj in objects]

    async def load[T: ModelObject](self, obj: T) -> T:
        """``load``: by GUID, or by its unique attributes for a new object.

        Raises:
            AtlasError: ``INSTANCE_GUID_NOT_FOUND`` or ``INSTANCE_BY_UNIQUE_ATTRIBUTE_NOT_FOUND``, ``UNEXPECTED_TYPE``
                for another type, ``INSTANCE_GUID_DELETED`` for a deleted one.
        """
        dto = self._dto(obj)
        retriever = EntityRetriever(self._store)
        if obj.guid and not obj.guid.startswith("-"):
            found = await retriever.entity_with_ext_info(obj.guid)
        else:
            entity_type = self._store.registry.entity_type(dto.type_name)
            if entity_type is None:  # pragma: no cover - the base and glossary models are loaded with the server
                raise AtlasError(AtlasErrorCode.TYPE_NAME_NOT_FOUND, dto.type_name)
            found = await retriever.entity_by_unique_attributes(entity_type, dto.unique_attributes(obj))
        entity = found.entity
        if entity is None:  # pragma: no cover - a read answers the entity
            raise AtlasError(AtlasErrorCode.INSTANCE_GUID_NOT_FOUND, obj.guid)
        if entity.type_name != dto.type_name:
            raise AtlasError(AtlasErrorCode.UNEXPECTED_TYPE, dto.type_name, entity.type_name)
        if entity.status is EntityStatus.DELETED:
            raise AtlasError(AtlasErrorCode.INSTANCE_GUID_DELETED, obj.guid)
        return dto.from_entity(found)

    async def load_all[T: ModelObject](self, objects: Sequence[T]) -> list[T]:
        """``load`` of each, those failing to load left out."""
        found = []
        for obj in objects:
            try:
                found.append(await self.load(obj))
            except AtlasError:
                continue
        return found

    async def delete(self, guid: str) -> None:
        """``delete``: the entity, as the server deletes entities."""
        await EntityWriter(self._store, user=self._user).delete_by_id(guid, DeleteType.DEFAULT)

    def _dto[T: ModelObject](self, obj: T) -> DataTransferObject[T]:
        return self._dtos[type(obj)]
