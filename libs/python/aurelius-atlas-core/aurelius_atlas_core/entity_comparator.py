"""``EntityComparator``: whether an update changes what is stored (EWR-08).

``AtlasEntityComparator`` as ``createOrUpdate`` uses it: classifications and business attributes are not compared.
"""

from collections.abc import Mapping

from aurelius_atlas_model.instance import AtlasEntity
from aurelius_atlas_typesystem.entity_type import EntityType
from aurelius_atlas_typesystem.values import relationship_type_of

from aurelius_atlas_core.entity_retriever import EntityRetriever
from aurelius_atlas_core.stored_entity import StoredEntity


class EntityComparator:
    """Compares request entities with stored ones, GUIDs mapped through the request's assignments."""

    def __init__(self, retriever: EntityRetriever, guid_assignments: Mapping[str, str]) -> None:
        self._retriever = retriever
        self._guid_assignments = dict(guid_assignments)

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
        return entity.custom_attributes is not None and entity.custom_attributes != stored.custom_attributes
