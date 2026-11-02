"""``AtlasServerService`` and ``AtlasServerDTO``: the servers exports and imports name, and their entities' marks.

The catalogues are ``AtlasServer`` entities; the entities they replicated name them (REP-01, REP-04).
"""

from typing import Any

from aurelius_atlas_model.errors import AtlasError
from aurelius_atlas_model.impexp import AtlasServer
from aurelius_atlas_model.instance import AtlasEntity, AtlasEntityWithExtInfo

from aurelius_atlas_core.authorization import ALLOW_ALL, Authorizer
from aurelius_atlas_core.data_access import DataAccess
from aurelius_atlas_core.entity_retriever import EntityRetriever
from aurelius_atlas_core.entity_store import EntityChange, EntityStore

SERVER_TYPE = "AtlasServer"


class AtlasServerDTO:
    """``AtlasServerDTO``: a server as its entity, found by its full name."""

    type_name = SERVER_TYPE

    def from_entity(self, found: AtlasEntityWithExtInfo) -> AtlasServer:
        """``from``: the name, full name, display name, additional info and URLs."""
        entity = found.entity or AtlasEntity()
        return AtlasServer(
            guid=str(entity.guid),
            name=entity.get_attribute("name"),
            full_name=entity.get_attribute("fullName"),
            display_name=entity.get_attribute("displayName"),
            additional_info=entity.get_attribute("additionalInfo"),
            urls=entity.get_attribute("urls"),
        )

    def to_entities(self, obj: AtlasServer) -> list[AtlasEntity]:
        """``toEntity``: the server's entity."""
        attributes = {
            "name": obj.name,
            "displayName": obj.display_name,
            "fullName": obj.full_name,
            "additionalInfo": obj.additional_info,
            "urls": obj.urls,
        }
        return [AtlasEntity(type_name=SERVER_TYPE, guid=obj.guid, attributes=attributes)]

    def unique_attributes(self, obj: AtlasServer) -> dict[str, Any]:
        """``getUniqueAttributes``: ``fullName``."""
        return {"fullName": obj.full_name}


class AtlasServerService:
    """``AtlasServerService`` over the entities of ``store``, written as ``user``, read and written as ``authorizer``
    allows (DD-307).
    """  # noqa: D205 - one sentence

    def __init__(self, store: EntityStore, *, user: str | None = None, authorizer: Authorizer = ALLOW_ALL) -> None:
        self._store = store
        self._authorizer = authorizer
        self._data_access = DataAccess(store, {AtlasServer: AtlasServerDTO()}, user=user, authorizer=authorizer)

    async def get(self, server: AtlasServer) -> AtlasServer:
        """``get``: the stored server of the full name (REP-01).

        Raises:
            AtlasError: ``INSTANCE_BY_UNIQUE_ATTRIBUTE_NOT_FOUND`` for none.
        """
        return await self._data_access.load(server)

    async def get_create_atlas_server(self, name: str, full_name: str) -> AtlasServer:
        """``getCreateAtlasServer``: the stored server of the full name, saved first when there is none."""
        default = AtlasServer(name=name, display_name=name, full_name=full_name)
        try:
            return await self.get(default)
        except AtlasError:
            return await self.save(default)

    async def save(self, server: AtlasServer) -> AtlasServer:
        """``save``: the server saved and read back; the server as given when the save fails."""
        try:
            return await self._data_access.save(server)
        except AtlasError:
            return server

    async def update_entities_with_server(self, server: AtlasServer, guids: list[str], attribute: str) -> None:
        """``updateEntitiesWithServer``: the server added once to the attribute of each entity and each it owns
        that has it, as a soft reference written straight to the entity (REP-04).
        """  # noqa: D205 - one sentence
        if server.guid.startswith("-"):
            return
        value = f"{SERVER_TYPE}:{server.guid}"
        retriever = EntityRetriever(self._store)
        for guid in guids:
            try:
                found = await retriever.entity_with_ext_info(guid)
            except AtlasError:
                continue
            for entity in [found.entity, *(found.referred_entities or {}).values()]:
                if entity is not None and entity.has_attribute(attribute):
                    await self._add(str(entity.guid), attribute, value)

    async def _add(self, guid: str, name: str, value: str) -> None:
        found = await self._store.get(guid)
        entity_type = None if found is None else self._store.registry.entity_type(found.entity.type_name)
        attribute = None if entity_type is None else entity_type.attribute(name)
        if found is None or attribute is None:
            return
        listed = list(found.entity.attributes.get(attribute.qualified_name) or [])
        if value in listed:
            return
        attributes = {**found.entity.attributes, attribute.qualified_name: [*listed, value]}
        await self._store.write(
            [EntityChange(found.entity.model_copy(update={"attributes": attributes}), found.version)]
        )
