"""The glossary, category and term DTOs of ``DataAccess``: glossary objects as entities (DD-246, DD-252).

A glossary object is saved as its entity, created or updated, and loaded back from the entity and its relationship
attributes (GLS-01, GCT-01, GLS-06, GTM-01). Relationships between glossary objects are the glossary utilities' to
write.
"""

from collections.abc import Callable
from typing import Any

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
    AtlasEntity,
    AtlasEntityWithExtInfo,
    AtlasObjectId,
    AtlasRelatedObjectId,
    RelationshipStatus,
)

from aurelius_atlas_core.authorization import ALLOW_ALL, Authorizer
from aurelius_atlas_core.data_access import DataAccess, Registry
from aurelius_atlas_core.entity_store import EntityStore

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


class _GlossaryObjectDTO[T: GlossaryObject]:
    """``AbstractGlossaryDTO``: a glossary object of one type, found by its qualified name (DD-246)."""

    def __init__(self, type_name: str, read: Callable[[AtlasEntity], T]) -> None:
        self._type_name = type_name
        self._read = read

    @property
    def type_name(self) -> str:
        """The entity type of the objects."""
        return self._type_name

    def from_entity(self, found: AtlasEntityWithExtInfo) -> T:
        """``from``: the object of the entity and its relationship attributes."""
        return self._read(found.entity)  # type: ignore[arg-type]  # a read answers the entity

    def to_entities(self, obj: T) -> list[AtlasEntity]:
        """``toEntityWithExtInfo``: the object's entity alone; its relationships are written apart."""
        return [to_entity(obj)]

    def unique_attributes(self, obj: T) -> dict[str, Any]:
        """``getUniqueAttributes``: the qualified name."""
        return {"qualifiedName": obj.qualified_name}


GLOSSARY_DTOS: Registry = {
    AtlasGlossary: _GlossaryObjectDTO(ATLAS_GLOSSARY_TYPENAME, glossary_from),
    AtlasGlossaryCategory: _GlossaryObjectDTO(ATLAS_GLOSSARY_CATEGORY_TYPENAME, category_from),
    AtlasGlossaryTerm: _GlossaryObjectDTO(ATLAS_GLOSSARY_TERM_TYPENAME, term_from),
}
"""``AtlasGlossaryDTO``, ``AtlasGlossaryCategoryDTO``, ``AtlasGlossaryTermDTO`` (DD-252)."""


def glossary_data_access(
    store: EntityStore, *, user: str | None = None, authorizer: Authorizer = ALLOW_ALL
) -> DataAccess:
    """The ``DataAccess`` of glossary objects in ``store``, written as ``user`` and checked by ``authorizer``."""
    return DataAccess(store, GLOSSARY_DTOS, user=user, authorizer=authorizer)


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
