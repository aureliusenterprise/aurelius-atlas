"""``StoredEntity``: an entity as stored, its system properties and its attribute values (ENS-03, DD-043).

What ``EntityGraphMapper`` and ``GraphHelper`` keep on an entity's vertex: the GUID, type and super type names,
state, times, users, version and the attribute values, here under their qualified names.
"""

from datetime import UTC, datetime, timedelta
from typing import Any, Self

from aurelius_atlas_model.base import AtlasModel
from aurelius_atlas_model.instance import AtlasEntity, EntityStatus
from aurelius_atlas_model.typedef import TypeCategory
from aurelius_atlas_typesystem.array_type import ArrayType
from aurelius_atlas_typesystem.atlas_type import resolved
from aurelius_atlas_typesystem.entity_type import EntityType
from aurelius_atlas_typesystem.map_type import MapType
from pydantic import Field

from aurelius_atlas_core.unique_key import UniqueKey

_EPOCH = datetime(1970, 1, 1, tzinfo=UTC)
_MILLISECOND = timedelta(milliseconds=1)


class StoredEntity(AtlasModel):
    """One document of the entity index; ``write_id`` names the write that last wrote it (DD-046)."""

    guid: str
    type_name: str
    super_type_names: list[str] = Field(default_factory=list)
    state: EntityStatus = EntityStatus.ACTIVE
    create_time: int = 0
    update_time: int = 0
    created_by: str | None = None
    updated_by: str | None = None
    version: int = 0
    is_incomplete: bool = False
    is_proxy: bool | None = None
    provenance_type: int = 0
    home_id: str | None = None
    labels: list[str] | None = None
    custom_attributes: dict[str, str] | None = None
    attributes: dict[str, Any] = Field(default_factory=dict)
    references: list[str] | None = None
    relationship_guids: list[str] | None = None
    write_id: str | None = None

    @classmethod
    def of(cls, entity: AtlasEntity, entity_type: EntityType, *, guid: str, now: int, user: str | None) -> Self:
        """A new entity as stored (``createVertexWithGuid``): ``ACTIVE``, both times ``now``, ``version`` its own.

        Attributes the type does not have are left out; the others are stored under their qualified names.
        """
        return cls(
            guid=guid,
            type_name=str(entity_type.type_name),
            super_type_names=list(entity_type.all_super_types),
            create_time=now,
            update_time=now,
            created_by=user,
            updated_by=user,
            version=entity.version or 0,
            is_incomplete=bool(entity.is_incomplete),
            is_proxy=entity.is_proxy,
            provenance_type=entity.provenance_type or 0,
            home_id=entity.home_id,
            labels=entity.labels,
            custom_attributes=entity.custom_attributes,
            attributes=stored_attributes(entity.attributes or {}, entity_type),
        )

    def touched(self, *, now: int, user: str | None) -> Self:
        """This entity, changed at ``now`` by ``user`` (``updateModificationMetadata``)."""
        return self.model_copy(update={"update_time": now, "updated_by": user})

    def listing(self, relationship_guid: str) -> Self:
        """This entity listing relationship ``relationship_guid`` as one it is an end of (DD-061)."""
        guids = list(self.relationship_guids or [])
        if relationship_guid not in guids:
            guids.append(relationship_guid)
        return self.model_copy(update={"relationship_guids": guids})

    def unlisting(self, relationship_guids: set[str]) -> Self:
        """This entity no longer listing these relationships (DD-061)."""
        guids = [guid for guid in self.relationship_guids or [] if guid not in relationship_guids]
        return self.model_copy(update={"relationship_guids": guids or None})

    def unique_keys(self, entity_type: EntityType) -> list[UniqueKey]:
        """The unique values this entity holds: those of its unique attributes with a value, while ``ACTIVE``."""
        if self.state is not EntityStatus.ACTIVE:
            return []
        keys = []
        for attribute in entity_type.unique_attributes.values():
            value = self.attributes.get(attribute.qualified_name)
            if value is not None:
                keys.append(UniqueKey(self.type_name, attribute.qualified_name, value))
        return keys

    def reference_guids(self, entity_type: EntityType) -> list[str]:
        """The GUIDs this entity's references name, each once (EDL-10, DD-057).

        Its own object id attributes and the elements and values of its arrays and maps of object ids; not soft
        references, nor references in structs, which Atlas keeps as properties rather than edges.
        """
        guids: dict[str, None] = {}
        for attribute in entity_type.all_attributes.values():
            value = self.attributes.get(attribute.qualified_name)
            if value is None or attribute.attribute_def.is_soft_referenced():
                continue
            type_ = attribute.attribute_type
            if type_.category is TypeCategory.OBJECT_ID_TYPE:
                guids[str(value)] = None
            elif isinstance(type_, ArrayType | MapType):
                element = resolved(type_.element_type if isinstance(type_, ArrayType) else type_.value_type)
                items = value.values() if isinstance(value, dict) else value if isinstance(value, list) else []
                if element.category is TypeCategory.OBJECT_ID_TYPE:
                    guids.update((str(item), None) for item in items if item is not None)
        return list(guids)

    def to_entity(self, entity_type: EntityType) -> AtlasEntity:
        """The entity with its system properties and the stored attribute values by attribute name (ERD-03).

        ``labels`` is a list even when empty, as Java's ``getLabels`` returns a set; ``EntityRetriever`` reads the
        attribute values as Atlas answers them.
        """
        attributes = {
            name: self.attributes[attribute.qualified_name]
            for name, attribute in entity_type.all_attributes.items()
            if attribute.qualified_name in self.attributes
        }
        return AtlasEntity(
            guid=self.guid,
            type_name=self.type_name,
            status=self.state,
            create_time=_EPOCH + self.create_time * _MILLISECOND,
            update_time=_EPOCH + self.update_time * _MILLISECOND,
            created_by=self.created_by,
            updated_by=self.updated_by,
            version=self.version,
            is_incomplete=self.is_incomplete,
            is_proxy=self.is_proxy,
            provenance_type=self.provenance_type,
            home_id=self.home_id,
            labels=self.labels or [],
            custom_attributes=self.custom_attributes,
            attributes=attributes,
        )


def stored_attributes(attributes: dict[str, Any], entity_type: EntityType) -> dict[str, Any]:
    """Attribute values keyed by qualified name; names the type does not have are left out (DD-043)."""
    stored: dict[str, Any] = {}
    for name, value in attributes.items():
        attribute = entity_type.all_attributes.get(name)
        if attribute is not None:
            stored[attribute.qualified_name] = value
    return stored
