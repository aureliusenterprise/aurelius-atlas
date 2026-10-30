"""``DataAccess`` with the glossary, category and term DTOs: glossary objects as entities (DD-246).

A glossary object is saved as its entity, created or updated, and loaded back from the entity and its relationship
attributes (GLS-01, GCT-01, GLS-06, GTM-01). Relationships between glossary objects are the glossary utilities' to
write.
"""

from collections.abc import Iterable, Sequence
from typing import Any

from aurelius_atlas_model.errors import AtlasError, AtlasErrorCode
from aurelius_atlas_model.glossary import (
    AtlasGlossary,
    AtlasGlossaryCategory,
    AtlasGlossaryHeader,
    AtlasGlossaryTerm,
    AtlasRelatedCategoryHeader,
    AtlasRelatedTermHeader,
    AtlasTermCategorizationHeader,
    AtlasTermRelationshipStatus,
    Relation,
)
from aurelius_atlas_model.instance import (
    AtlasEntitiesWithExtInfo,
    AtlasEntity,
    AtlasObjectId,
    AtlasRelatedObjectId,
    EntityStatus,
    RelationshipStatus,
)

from aurelius_atlas_core.delete_type import DeleteType
from aurelius_atlas_core.entity_retriever import EntityRetriever
from aurelius_atlas_core.entity_store import EntityStore
from aurelius_atlas_core.entity_writer import EntityWriter

ATLAS_GLOSSARY_TYPENAME = "AtlasGlossary"
ATLAS_GLOSSARY_CATEGORY_TYPENAME = "AtlasGlossaryCategory"
ATLAS_GLOSSARY_TERM_TYPENAME = "AtlasGlossaryTerm"

type GlossaryObject = AtlasGlossary | AtlasGlossaryCategory | AtlasGlossaryTerm


def glossary_from(entity: AtlasEntity) -> AtlasGlossary:
    """``AtlasGlossaryDTO.from``: the attributes, and the headers of its categories and terms."""
    glossary = AtlasGlossary(
        guid=str(entity.guid),
        qualified_name=entity.get_attribute("qualifiedName"),
        name=entity.get_attribute("name"),
        short_description=entity.get_attribute("shortDescription"),
        long_description=entity.get_attribute("longDescription"),
        language=entity.get_attribute("language"),
        usage=entity.get_attribute("usage"),
        additional_attributes=entity.get_attribute("additionalAttributes"),
    )
    categories = [related_category_header(found) for found in _related(entity, "categories")]
    terms = [related_term_header(found) for found in _related(entity, "terms")]
    glossary.categories = categories or None
    glossary.terms = terms or None
    return glossary


def category_from(entity: AtlasEntity) -> AtlasGlossaryCategory:
    """``AtlasGlossaryCategoryDTO.from``: the attributes, its anchor, parent, active children and terms."""
    category = AtlasGlossaryCategory(
        guid=str(entity.guid),
        qualified_name=entity.get_attribute("qualifiedName"),
        name=entity.get_attribute("name"),
        short_description=entity.get_attribute("shortDescription"),
        long_description=entity.get_attribute("longDescription"),
        additional_attributes=entity.get_attribute("additionalAttributes"),
    )
    anchor = _related(entity, "anchor")
    if anchor:
        category.anchor = AtlasGlossaryHeader(glossary_guid=anchor[0].guid, relation_guid=anchor[0].relationship_guid)
    parent = _related(entity, "parentCategory")
    if parent:
        category.parent_category = related_category_header(parent[0])
    children = [
        related_category_header(found)
        for found in _related(entity, "childrenCategories")
        if found.relationship_status is RelationshipStatus.ACTIVE
    ]
    terms = [related_term_header(found) for found in _related(entity, "terms")]
    category.children_categories = children or None
    category.terms = terms or None
    return category


def term_from(entity: AtlasEntity) -> AtlasGlossaryTerm:
    """``AtlasGlossaryTermDTO.from``: the attributes, anchor, categories, active assigned entities and relations."""
    term = AtlasGlossaryTerm(
        guid=str(entity.guid),
        qualified_name=entity.get_attribute("qualifiedName"),
        name=entity.get_attribute("name"),
        short_description=entity.get_attribute("shortDescription"),
        long_description=entity.get_attribute("longDescription"),
        examples=entity.get_attribute("examples"),
        abbreviation=entity.get_attribute("abbreviation"),
        usage=entity.get_attribute("usage"),
        additional_attributes=entity.get_attribute("additionalAttributes"),
        classifications=entity.classifications or None,
    )
    anchor = _related(entity, "anchor")
    if anchor:
        term.anchor = AtlasGlossaryHeader(glossary_guid=anchor[0].guid, relation_guid=anchor[0].relationship_guid)
    term.categories = [categorization_header(found) for found in _related(entity, "categories")] or None
    term.assigned_entities = [
        found
        for found in _related(entity, "assignedEntities")
        if found.relationship_status is RelationshipStatus.ACTIVE
    ] or None
    for relation in Relation:
        headers = [related_term_header(found) for found in _related(entity, relation.attr_name)]
        setattr(term, relation.field, headers or None)
    return term


def categorization_header(found: AtlasRelatedObjectId) -> AtlasTermCategorizationHeader:
    """``constructTermCategorizationId``."""
    attributes = found.relationship_attributes
    header = AtlasTermCategorizationHeader(category_guid=found.guid, relation_guid=found.relationship_guid)
    if attributes is not None:
        header.description = attributes.get_attribute("description")
        status = attributes.get_attribute("status")
        if isinstance(status, str):
            header.status = AtlasTermRelationshipStatus(status)
    return header


def related_category_header(found: AtlasRelatedObjectId) -> AtlasRelatedCategoryHeader:
    """``constructRelatedCategoryId``."""
    attributes = found.relationship_attributes
    return AtlasRelatedCategoryHeader(
        category_guid=found.guid,
        relation_guid=found.relationship_guid,
        display_text=found.display_text,
        description=None if attributes is None else attributes.get_attribute("description"),
        parent_category_guid=None if attributes is None else attributes.get_attribute("parentCategoryGuid"),
    )


def related_term_header(found: AtlasRelatedObjectId) -> AtlasRelatedTermHeader:
    """``constructRelatedTermId``."""
    attributes = found.relationship_attributes
    header = AtlasRelatedTermHeader(
        term_guid=found.guid, relation_guid=found.relationship_guid, display_text=found.display_text
    )
    if attributes is not None:
        header.description = attributes.get_attribute("description")
        header.expression = attributes.get_attribute("expression")
        header.source = attributes.get_attribute("source")
        header.steward = attributes.get_attribute("steward")
        status = attributes.get_attribute("status")
        if isinstance(status, str):
            header.status = AtlasTermRelationshipStatus(status)
    return header


def to_entity(obj: GlossaryObject) -> AtlasEntity:
    """``toEntity``: the object's attributes, a category's or term's anchor too; other relationships are apart."""
    attributes: dict[str, Any] = {
        "qualifiedName": obj.qualified_name,
        "name": obj.name,
        "shortDescription": obj.short_description,
        "longDescription": obj.long_description,
        "additionalAttributes": obj.additional_attributes,
    }
    classifications = None
    if isinstance(obj, AtlasGlossary):
        attributes |= {"language": obj.language, "usage": obj.usage}
    elif isinstance(obj, AtlasGlossaryTerm):
        attributes |= {"examples": obj.examples, "abbreviation": obj.abbreviation, "usage": obj.usage}
        classifications = obj.classifications or None
    if not isinstance(obj, AtlasGlossary) and obj.anchor is not None:
        attributes["anchor"] = AtlasObjectId(guid=obj.anchor.glossary_guid)
    return AtlasEntity(type_name=_type_name(obj), guid=obj.guid, attributes=attributes, classifications=classifications)


class DataAccess:
    """``DataAccess``: glossary objects saved and loaded as the entities of ``store``."""

    def __init__(self, store: EntityStore, *, user: str | None = None) -> None:
        self._store = store
        self._user = user

    async def save[T: GlossaryObject](self, obj: T) -> T:
        """``save``: create or update the object's entity, its new GUID taken, and load it back."""
        response = await EntityWriter(self._store, user=self._user).create_or_update(
            AtlasEntitiesWithExtInfo(entities=[to_entity(obj)])
        )
        assigned = (response.guid_assignments or {}).get(obj.guid)
        if response.get_created_entities() and assigned is not None and assigned != obj.guid:
            obj.guid = assigned
        return await self.load(obj)

    async def save_all[T: GlossaryObject](self, objects: Iterable[T]) -> list[T]:
        """``save`` of each, in order."""
        return [await self.save(obj) for obj in objects]

    async def load[T: GlossaryObject](self, obj: T) -> T:
        """``load``: by GUID, or by qualified name for a new object (GLS-06).

        Raises:
            AtlasError: ``INSTANCE_GUID_NOT_FOUND`` or ``INSTANCE_BY_UNIQUE_ATTRIBUTE_NOT_FOUND``, ``UNEXPECTED_TYPE``
                for another type, ``INSTANCE_GUID_DELETED`` for a deleted one.
        """
        retriever = EntityRetriever(self._store)
        expected = _type_name(obj)
        if obj.guid and not obj.guid.startswith("-"):
            found = await retriever.entity_with_ext_info(obj.guid)
        else:
            entity_type = self._store.registry.entity_type(expected)
            if entity_type is None:  # pragma: no cover - the glossary model is loaded with the server
                raise AtlasError(AtlasErrorCode.TYPE_NAME_NOT_FOUND, expected)
            found = await retriever.entity_by_unique_attributes(entity_type, {"qualifiedName": obj.qualified_name})
        entity = found.entity
        if entity is None:  # pragma: no cover - a read answers the entity
            raise AtlasError(AtlasErrorCode.INSTANCE_GUID_NOT_FOUND, obj.guid)
        if entity.type_name != expected:
            raise AtlasError(AtlasErrorCode.UNEXPECTED_TYPE, expected, entity.type_name)
        if entity.status is EntityStatus.DELETED:
            raise AtlasError(AtlasErrorCode.INSTANCE_GUID_DELETED, obj.guid)
        if isinstance(obj, AtlasGlossary):
            return glossary_from(entity)  # type: ignore[return-value]  # the loader of T's class
        if isinstance(obj, AtlasGlossaryTerm):
            return term_from(entity)  # type: ignore[return-value]
        return category_from(entity)  # type: ignore[return-value]

    async def load_all[T: GlossaryObject](self, objects: Sequence[T]) -> list[T]:
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


def _type_name(obj: GlossaryObject) -> str:
    if isinstance(obj, AtlasGlossary):
        return ATLAS_GLOSSARY_TYPENAME
    if isinstance(obj, AtlasGlossaryTerm):
        return ATLAS_GLOSSARY_TERM_TYPENAME
    return ATLAS_GLOSSARY_CATEGORY_TYPENAME


def _related(entity: AtlasEntity, name: str) -> list[AtlasRelatedObjectId]:
    """The entity's relationship attribute as related object ids, one or many."""
    value = entity.get_relationship_attribute(name)
    items = value if isinstance(value, list) else [] if value is None else [value]
    return [
        item if isinstance(item, AtlasRelatedObjectId) else AtlasRelatedObjectId.model_validate(item) for item in items
    ]
