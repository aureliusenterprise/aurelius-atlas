"""``EntityComparator``: whether an update changes what is stored (EWR-08).

``AtlasEntityComparator`` as ``createOrUpdate`` uses it: classifications and business attributes are compared only
for an import, which replaces them (IMP-06).
"""

from collections.abc import Mapping

from aurelius_atlas_model.instance import AtlasEntity
from aurelius_atlas_typesystem.entity_type import EntityType
from aurelius_atlas_typesystem.values import relationship_type_of

from aurelius_atlas_core.entity_retriever import EntityRetriever
from aurelius_atlas_core.stored_entity import StoredEntity


class EntityComparator:
    """Compares request entities with stored ones, GUIDs mapped through the request's assignments."""

    def __init__(
        self, retriever: EntityRetriever, guid_assignments: Mapping[str, str], *, importing: bool = False
    ) -> None:
        self._retriever = retriever
        self._guid_assignments = dict(guid_assignments)
        self._importing = importing

    async def has_difference(self, entity: AtlasEntity, entity_type: EntityType, stored: StoredEntity) -> bool:
        """``getDiffResult(…).hasDifference()``: a given attribute, relationship attribute or custom attributes differ.

        A relationship attribute is compared with what its relationships read (REL-18).
        """
        for name, value in (entity.attributes or {}).items():
            attribute = entity_type.all_attributes.get(name)
            if attribute is not None and not attribute.attribute_type.are_equal_values(
                await self._retriever.entity_attribute(stored, attribute), value, self._guid_assignments
            ):
                return True
        for name, value in (entity.relationship_attributes or {}).items():
            attribute = entity_type.relationship_attribute(name, relationship_type_of(value))
            if attribute is None:
                continue
            current = await self._retriever.entity_attribute(stored, attribute)
            if not attribute.attribute_type.are_equal_values(current, value, self._guid_assignments):
                return True
        if entity.custom_attributes is not None and entity.custom_attributes != stored.custom_attributes:
            return True
        return self._importing and await self._replaced_differ(entity, stored)

    async def _replaced_differ(self, entity: AtlasEntity, stored: StoredEntity) -> bool:
        """``Objects.equals`` of the classifications, then of the business attributes, given and stored (IMP-06).

        A request without classifications differs from a stored entity's empty list, as in Atlas.
        """
        current = await self._retriever.classifications(stored.guid)
        given = None if entity.classifications is None else [found.to_json() for found in entity.classifications]
        if given != [found.to_json() for found in current]:
            return True
        return entity.business_attributes != await self._retriever.business_attributes(stored)
