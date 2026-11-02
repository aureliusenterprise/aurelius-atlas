"""``ImportTypeDefProcessor`` and ``TypeAttributeDifference``: an import's types merged into the registry (IMS-03).

The types the registry lacks are created; to those it has, the attributes and enum elements the import adds.
"""

from aurelius_atlas_model.errors import AtlasError, AtlasErrorCode
from aurelius_atlas_model.impexp import AtlasImportResult
from aurelius_atlas_model.typedef import (
    AtlasBaseTypeDef,
    AtlasEnumDef,
    AtlasStructDef,
    AtlasTypesDef,
    TypeCategory,
)

from aurelius_atlas_core.typedef_store import TypedefStore, types_to_create

CREATED_METRICS = (
    ("typedef:classification", "classification_defs"),
    ("typedef:enum", "enum_defs"),
    ("typedef:entitydef", "entity_defs"),
    ("typedef:struct", "struct_defs"),
    ("typedef:relationship", "relationship_defs"),
    ("typedef:businessmetadata", "business_metadata_defs"),
)
"""``updateMetricsForTypesDef``: the count of each kind created."""
UPDATED = (
    ("enum_defs", "typedef:enum:update"),
    ("struct_defs", "typedef:struct:update"),
    ("classification_defs", "typedef:classification:update"),
    ("entity_defs", "typedef:entitydef:update"),
    ("relationship_defs", "typedef:relationshipdef:update"),
    ("business_metadata_defs", "typedef:businessmetadatadef:update"),
)
"""``updateTypes``: each kind, in Atlas's order, and the count of each updated."""


class ImportTypeDefProcessor:
    """``ImportTypeDefProcessor`` into ``store``, as ``user``."""

    def __init__(self, store: TypedefStore, user: str | None) -> None:
        self._store = store
        self._user = user

    async def process_types(self, types_def: AtlasTypesDef, result: AtlasImportResult) -> None:
        """``processTypes``: GUIDs dropped, the new types created and counted, then the known ones extended.

        Raises:
            AtlasError: as creating and updating types does; ``INVALID_IMPORT_ATTRIBUTE_TYPE_CHANGED``.
        """
        types_def = types_def.model_copy(deep=True)
        for _, field in CREATED_METRICS:
            for typedef in getattr(types_def, field) or []:
                typedef.guid = None
        created = types_to_create(types_def, self._store.registry)
        if any(getattr(created, field) for _, field in CREATED_METRICS):
            await self._store.create_types_def(created, self._user)
            for key, field in CREATED_METRICS:
                result.increment_metrics_counter(key, len(getattr(created, field) or []))
        await self._update_types(types_def, result)

    async def _update_types(self, types_def: AtlasTypesDef, result: AtlasImportResult) -> None:
        """``TypeAttributeDifference.updateTypes``: each known type given what the import adds to it."""
        for field, key in UPDATED:
            for incoming in getattr(types_def, field) or []:
                existing = self._store.registry.typedef_by_name(incoming.name)
                if existing is None or existing.category is not incoming.category:
                    continue
                extended = self._extended(existing, incoming)
                if extended is not None:
                    await self._store.update_types_def(_types_def_of(field, extended), self._user)
                    result.increment_metrics_counter(key)

    def _extended(self, existing: AtlasBaseTypeDef, incoming: AtlasBaseTypeDef) -> AtlasBaseTypeDef | None:
        """The existing definition with what the incoming one adds, or None when it adds nothing.

        Raises:
            AtlasError: ``INVALID_IMPORT_ATTRIBUTE_TYPE_CHANGED`` for an attribute of another type.
        """
        if isinstance(existing, AtlasEnumDef) and isinstance(incoming, AtlasEnumDef):
            known = {element.value for element in existing.element_defs or []}
            added = [element for element in incoming.element_defs or [] if element.value not in known]
            return (
                existing.model_copy(update={"element_defs": [*(existing.element_defs or []), *added]})
                if added
                else None
            )
        if not isinstance(existing, AtlasStructDef) or not isinstance(incoming, AtlasStructDef):
            return None
        current = {attribute.name: attribute for attribute in existing.attribute_defs or []}
        added = []
        for attribute in incoming.attribute_defs or []:
            found = current.get(attribute.name)
            if found is None:
                if not self._legacy_end(str(existing.name), str(attribute.name)):
                    added.append(attribute)
            elif found.type_name != attribute.type_name:
                raise AtlasError(
                    AtlasErrorCode.INVALID_IMPORT_ATTRIBUTE_TYPE_CHANGED,
                    existing.name,
                    found.name,
                    found.type_name,
                    attribute.type_name,
                )
        if not added:
            return None
        return existing.model_copy(update={"attribute_defs": [*(existing.attribute_defs or []), *added]})

    def _legacy_end(self, type_name: str, attribute_name: str) -> bool:
        """``findRelationshipWithLegacyRelationshipEnd``: a relationship type's legacy end is the attribute."""
        for relationship in self._store.registry.typedefs(TypeCategory.RELATIONSHIP):
            for end in (getattr(relationship, "end_def1", None), getattr(relationship, "end_def2", None)):
                if end is not None and end.is_legacy_attribute and (end.type, end.name) == (type_name, attribute_name):
                    return True
        return False


def _types_def_of(field: str, typedef: AtlasBaseTypeDef) -> AtlasTypesDef:
    return AtlasTypesDef.model_validate({}).model_copy(update={field: [typedef]})
