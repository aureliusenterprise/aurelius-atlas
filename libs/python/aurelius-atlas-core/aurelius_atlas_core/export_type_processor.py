"""``ExportTypeProcessor``: an exported entity's types, and its assigned terms' glossaries (EXP-05, EXP-06).

An entity type brings its attributes' types, its relationship types and their end types, the business metadata
that applies to it and its super types; a classification type its attributes' types and super types.
"""

from typing import TYPE_CHECKING

from aurelius_atlas_model.errors import AtlasError
from aurelius_atlas_model.instance import AtlasEntity, AtlasRelatedObjectId
from aurelius_atlas_model.typedef import TypeCategory
from aurelius_atlas_typesystem.array_type import ArrayType
from aurelius_atlas_typesystem.atlas_type import AtlasType, resolved
from aurelius_atlas_typesystem.map_type import MapType
from aurelius_atlas_typesystem.struct_type import StructType

from aurelius_atlas_core.entity_store import EntityStore
from aurelius_atlas_core.glossary_service import GlossaryService

if TYPE_CHECKING:
    from aurelius_atlas_core.export_service import ExportContext

MEANINGS = "meanings"
"""``RELATIONSHIP_ATTR_MEANINGS``: the relationship attribute holding the terms assigned to an entity."""


class ExportTypeProcessor:
    """``ExportTypeProcessor`` over the types and glossary of ``store``."""

    def __init__(self, store: EntityStore) -> None:
        self._store = store
        self._registry = store.registry

    async def add_types(self, entity: AtlasEntity, context: ExportContext) -> None:
        """``addTypes``: the entity's type and its classifications', and its terms' glossaries (EXP-05, EXP-06)."""
        self._add_entity_type(entity.type_name, context)
        for classification in entity.classifications or []:
            self._add_classification_type(classification.type_name, context)
        await self._add_terms(entity, context)

    async def _add_terms(self, entity: AtlasEntity, context: ExportContext) -> None:
        """``addTerms``: the glossary of each term in the entity's ``meanings``; a term not read is left out."""
        meanings = (entity.relationship_attributes or {}).get(MEANINGS)
        if not isinstance(meanings, list):
            return
        glossary = GlossaryService(self._store)
        for term in meanings:
            if isinstance(term, AtlasRelatedObjectId) and term.guid is not None:
                try:
                    anchor = (await glossary.get_term(term.guid)).anchor
                except AtlasError:
                    continue
                if anchor is not None and anchor.glossary_guid is not None:
                    context.terms_glossary[term.guid] = anchor.glossary_guid

    def _add_type(self, type_name: str | None, context: ExportContext) -> None:
        """``addType`` of a name: an unknown one is left out."""
        try:
            found = self._registry.get_type(type_name)
        except AtlasError:
            return
        self._add_atlas_type(found, context)

    def _add_atlas_type(self, found: AtlasType, context: ExportContext) -> None:
        """``addType``: what an attribute's type needs, by its kind."""
        found = resolved(found)
        category = found.category
        if isinstance(found, ArrayType | MapType):
            parts = [found.element_type] if isinstance(found, ArrayType) else [found.key_type, found.value_type]
            for part in parts:
                if part is not None:
                    self._add_atlas_type(part, context)
        elif category is TypeCategory.ENTITY:
            self._add_entity_type(found.type_name, context)
        elif category is TypeCategory.CLASSIFICATION:
            self._add_classification_type(found.type_name, context)
        elif category is TypeCategory.RELATIONSHIP:
            self._add_relationship_type(found.type_name, context)
        elif category is TypeCategory.BUSINESS_METADATA:
            self._add_struct(found.type_name, context.business_metadata_types, context)
        elif category is TypeCategory.STRUCT:
            self._add_struct(found.type_name, context.struct_types, context)
        elif category is TypeCategory.ENUM and found.type_name not in context.enum_types:
            context.enum_types.append(str(found.type_name))

    def _add_entity_type(self, type_name: str | None, context: ExportContext) -> None:
        """``addEntityType``: once, with its attributes', relationships', business metadata's and super types."""
        entity_type = self._registry.entity_type(type_name)
        if entity_type is None or entity_type.type_name in context.entity_types:
            return
        context.entity_types.append(str(entity_type.type_name))
        self._add_attribute_types(entity_type, context)
        for relationships in entity_type.relationship_attributes.values():
            for relationship_type in relationships:
                self._add_relationship_type(relationship_type, context)
        for name in entity_type.business_attributes:
            self._add_struct(name, context.business_metadata_types, context)
        for super_type in entity_type.all_super_types:
            self._add_entity_type(super_type, context)

    def _add_classification_type(self, type_name: str | None, context: ExportContext) -> None:
        """``addClassificationType``: once, with its attributes' and super types."""
        classification_type = self._registry.classification_type(type_name)
        if classification_type is None or classification_type.type_name in context.classification_types:
            return
        context.classification_types.append(str(classification_type.type_name))
        self._add_attribute_types(classification_type, context)
        for super_type in classification_type.all_super_types:
            self._add_classification_type(super_type, context)

    def _add_relationship_type(self, type_name: str | None, context: ExportContext) -> None:
        """``addRelationshipType``: once, with its attributes' and its two end types."""
        relationship_type = self._registry.relationship_type(type_name)
        if relationship_type is None or relationship_type.type_name in context.relationship_types:
            return
        context.relationship_types.append(str(relationship_type.type_name))
        self._add_attribute_types(relationship_type, context)
        for end in (relationship_type.end1_type, relationship_type.end2_type):
            if end is not None:
                self._add_entity_type(end.type_name, context)

    def _add_struct(self, type_name: str | None, collected: list[str], context: ExportContext) -> None:
        """``addStructType`` and ``addBusinessMetadataType``: once, with its attributes' types."""
        found = self._registry.struct_type(type_name) or self._registry.business_metadata_type(type_name)
        if found is None or found.type_name in collected:
            return
        collected.append(str(found.type_name))
        self._add_attribute_types(found, context)

    def _add_attribute_types(self, struct_type: StructType, context: ExportContext) -> None:
        """``addAttributeTypes``: the type of each attribute the definition declares."""
        for attribute_def in struct_type.struct_def.attribute_defs:
            self._add_type(attribute_def.type_name, context)
