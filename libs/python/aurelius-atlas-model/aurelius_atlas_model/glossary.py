"""The glossary models: ``AtlasGlossary``, ``AtlasGlossaryCategory``, ``AtlasGlossaryTerm`` and their headers.

Atlas's ``AtlasBaseModelObject`` gives a new object a negative GUID; its sets of headers are JSON arrays.
``set_attribute`` is the partial update of ``GlossaryREST`` (GLS-03, GCT-05, GTM-04).
"""

import itertools
import json
import time
from enum import Enum, StrEnum
from typing import Any

from pydantic import Field

from aurelius_atlas_model.base import AtlasModel
from aurelius_atlas_model.instance import AtlasClassification, AtlasRelatedObjectId

_NEXT_ID = itertools.count(time.monotonic_ns())


def _new_guid() -> str:
    """``AtlasBaseModelObject.init``: ``-`` and the next internal id."""
    return f"-{next(_NEXT_ID) + 1}"


class AtlasTermRelationshipStatus(StrEnum):
    """``AtlasTermRelationshipStatus``."""

    DRAFT = "DRAFT"
    ACTIVE = "ACTIVE"
    DEPRECATED = "DEPRECATED"
    OBSOLETE = "OBSOLETE"
    OTHER = "OTHER"


class AtlasGlossaryHeader(AtlasModel):
    """``AtlasGlossaryHeader``: a category's or term's glossary; equal by GUID and relationship."""

    glossary_guid: str | None = None
    relation_guid: str | None = None
    display_text: str | None = None

    def same_as(self, other: AtlasGlossaryHeader | None) -> bool:
        """``equals``."""
        return other is not None and (self.glossary_guid, self.relation_guid) == (
            other.glossary_guid,
            other.relation_guid,
        )


class AtlasRelatedCategoryHeader(AtlasModel):
    """``AtlasRelatedCategoryHeader``: a related category, its parent and the relationship's description."""

    category_guid: str | None = None
    parent_category_guid: str | None = None
    relation_guid: str | None = None
    display_text: str | None = None
    description: str | None = None

    def key(self) -> tuple[Any, ...]:
        """What ``equals`` compares: all but the display text."""
        return (self.category_guid, self.parent_category_guid, self.relation_guid, self.description)


class AtlasRelatedTermHeader(AtlasModel):
    """``AtlasRelatedTermHeader``: a related term and the attributes of the relationship to it."""

    term_guid: str | None = None
    relation_guid: str | None = None
    display_text: str | None = None
    description: str | None = None
    expression: str | None = None
    steward: str | None = None
    source: str | None = None
    status: AtlasTermRelationshipStatus | None = None
    qualified_name: str | None = None

    def key(self) -> tuple[Any, ...]:
        """What ``equals`` compares: the term, the relationship and its attributes."""
        return (
            self.term_guid,
            self.relation_guid,
            self.description,
            self.expression,
            self.steward,
            self.source,
            self.status,
        )


class AtlasTermCategorizationHeader(AtlasModel):
    """``AtlasTermCategorizationHeader``: a term's category and the categorization's attributes."""

    category_guid: str | None = None
    relation_guid: str | None = None
    description: str | None = None
    display_text: str | None = None
    status: AtlasTermRelationshipStatus | None = None

    def key(self) -> tuple[Any, ...]:
        """What ``equals`` compares: all but the display text."""
        return (self.category_guid, self.relation_guid, self.description, self.status)


class AtlasGlossaryBaseObject(AtlasModel):
    """``AtlasGlossaryBaseObject``: what glossaries, categories and terms share."""

    guid: str = Field(default_factory=_new_guid)
    qualified_name: str | None = None
    name: str | None = None
    short_description: str | None = None
    long_description: str | None = None
    additional_attributes: dict[str, Any] | None = None
    classifications: list[AtlasClassification] | None = None

    def base_key(self) -> tuple[Any, ...]:
        """What ``AtlasGlossaryBaseObject.equals`` compares."""
        return (
            self.qualified_name,
            self.name,
            self.short_description,
            self.long_description,
            self.additional_attributes,
            [classification.to_json() for classification in self.classifications or []] or None,
        )


_GLOSSARY_ATTRIBUTES = ("name", "short_description", "long_description", "language", "usage")
_CATEGORY_ATTRIBUTES = ("name", "short_description", "long_description")
_CAMEL = {"name": "name", "shortDescription": "short_description", "longDescription": "long_description"}


class AtlasGlossary(AtlasGlossaryBaseObject):
    """``AtlasGlossary``: its terms' and categories' headers."""

    language: str | None = None
    usage: str | None = None
    terms: list[AtlasRelatedTermHeader] | None = None
    categories: list[AtlasRelatedCategoryHeader] | None = None

    def set_attribute(self, name: str, value: str) -> None:
        """``setAttribute``: ``name``, ``shortDescription``, ``longDescription``, ``language`` or ``usage`` (GLS-03).

        Raises:
            ValueError: For any other attribute.
        """
        field = {**_CAMEL, "language": "language", "usage": "usage"}.get(name)
        if field not in _GLOSSARY_ATTRIBUTES:
            msg = f"Invalid attribute '{name}' for object AtlasGlossary"
            raise ValueError(msg)
        setattr(self, str(field), value)

    def same_as(self, other: AtlasGlossary) -> bool:
        """``equals``: the shared fields, language, usage and the headers as sets."""
        return (
            self.base_key() == other.base_key()
            and (self.language, self.usage) == (other.language, other.usage)
            and _keys(self.terms) == _keys(other.terms)
            and _keys(self.categories) == _keys(other.categories)
        )


class AtlasGlossaryCategory(AtlasGlossaryBaseObject):
    """``AtlasGlossaryCategory``: its glossary, parent, children and terms."""

    anchor: AtlasGlossaryHeader | None = None
    parent_category: AtlasRelatedCategoryHeader | None = None
    children_categories: list[AtlasRelatedCategoryHeader] | None = None
    terms: list[AtlasRelatedTermHeader] | None = None

    def set_attribute(self, name: str, value: str) -> None:
        """``setAttribute``: ``name``, ``shortDescription`` or ``longDescription`` (GCT-05).

        Raises:
            ValueError: For any other attribute.
        """
        field = _CAMEL.get(name)
        if field not in _CATEGORY_ATTRIBUTES:
            msg = f"Invalid attribute '{name}' for object AtlasGlossaryCategory"
            raise ValueError(msg)
        setattr(self, str(field), value)

    def same_as(self, other: AtlasGlossaryCategory) -> bool:
        """``equals``: the shared fields, the anchor, the parent and the headers as sets."""
        anchors_equal = (self.anchor is None and other.anchor is None) or (
            self.anchor is not None and self.anchor.same_as(other.anchor)
        )
        parents = (None if self.parent_category is None else self.parent_category.key()) == (
            None if other.parent_category is None else other.parent_category.key()
        )
        return (
            self.base_key() == other.base_key()
            and anchors_equal
            and parents
            and _keys(self.children_categories) == _keys(other.children_categories)
            and _keys(self.terms) == _keys(other.terms)
        )


class Relation(Enum):
    """``AtlasGlossaryTerm.Relation``: a term relation's relationship type, attribute and side (GTM-03).

    A relation whose attribute is the relationship's second end points from the related term to this one.
    """

    SEE_ALSO = ("AtlasGlossaryRelatedTerm", "seeAlso", False)
    SYNONYMS = ("AtlasGlossarySynonym", "synonyms", False)
    ANTONYMS = ("AtlasGlossaryAntonym", "antonyms", False)
    PREFERRED_TO_TERMS = ("AtlasGlossaryPreferredTerm", "preferredToTerms", True)
    PREFERRED_TERMS = ("AtlasGlossaryPreferredTerm", "preferredTerms", False)
    REPLACEMENT_TERMS = ("AtlasGlossaryReplacementTerm", "replacementTerms", True)
    REPLACED_BY = ("AtlasGlossaryReplacementTerm", "replacedBy", False)
    TRANSLATION_TERMS = ("AtlasGlossaryTranslation", "translationTerms", True)
    TRANSLATED_TERMS = ("AtlasGlossaryTranslation", "translatedTerms", False)
    ISA = ("AtlasGlossaryIsARelationship", "isA", True)
    CLASSIFIES = ("AtlasGlossaryIsARelationship", "classifies", False)
    VALID_VALUES = ("AtlasGlossaryValidValue", "validValues", True)
    VALID_VALUES_FOR = ("AtlasGlossaryValidValue", "validValuesFor", False)

    @property
    def type_name(self) -> str:
        """``getName``: the relationship type."""
        return self.value[0]

    @property
    def attr_name(self) -> str:
        """``getAttrName``: the term's attribute, the relation's JSON name."""
        return self.value[1]

    @property
    def is_end2_attr(self) -> bool:
        """``isEnd2Attr``."""
        return self.value[2]

    @property
    def field(self) -> str:
        """The model field holding the relation's headers."""
        return _SNAKE.get(self.attr_name, self.attr_name)


_SNAKE = {
    "seeAlso": "see_also",
    "preferredToTerms": "preferred_to_terms",
    "preferredTerms": "preferred_terms",
    "replacementTerms": "replacement_terms",
    "replacedBy": "replaced_by",
    "translationTerms": "translation_terms",
    "translatedTerms": "translated_terms",
    "isA": "is_a",
    "validValues": "valid_values",
    "validValuesFor": "valid_values_for",
}
_TERM_ATTRIBUTES = {**_CAMEL, "abbreviation": "abbreviation", "usage": "usage"}


class AtlasGlossaryTerm(AtlasGlossaryBaseObject):
    """``AtlasGlossaryTerm``: its glossary, categories, assigned entities and related terms by relation (GTM-01)."""

    examples: list[str] | None = None
    abbreviation: str | None = None
    usage: str | None = None
    anchor: AtlasGlossaryHeader | None = None
    assigned_entities: list[AtlasRelatedObjectId] | None = None
    categories: list[AtlasTermCategorizationHeader] | None = None
    see_also: list[AtlasRelatedTermHeader] | None = None
    synonyms: list[AtlasRelatedTermHeader] | None = None
    antonyms: list[AtlasRelatedTermHeader] | None = None
    preferred_terms: list[AtlasRelatedTermHeader] | None = None
    preferred_to_terms: list[AtlasRelatedTermHeader] | None = None
    replacement_terms: list[AtlasRelatedTermHeader] | None = None
    replaced_by: list[AtlasRelatedTermHeader] | None = None
    translation_terms: list[AtlasRelatedTermHeader] | None = None
    translated_terms: list[AtlasRelatedTermHeader] | None = None
    is_a: list[AtlasRelatedTermHeader] | None = None
    classifies: list[AtlasRelatedTermHeader] | None = None
    valid_values: list[AtlasRelatedTermHeader] | None = None
    valid_values_for: list[AtlasRelatedTermHeader] | None = None

    def related_terms(self) -> dict[Relation, list[AtlasRelatedTermHeader]]:
        """``getRelatedTerms``: the relations holding terms; empty when ``hasTerms`` is false (GTM-06)."""
        return {relation: headers for relation in Relation if (headers := self.relation_terms(relation))}

    def relation_terms(self, relation: Relation) -> list[AtlasRelatedTermHeader] | None:
        """The headers of one relation."""
        return getattr(self, relation.field)

    def set_attribute(self, name: str, value: str) -> None:
        """``setAttribute``: ``name``, the descriptions, ``abbreviation`` or ``usage`` (GTM-04).

        Raises:
            ValueError: For any other attribute.
        """
        field = _TERM_ATTRIBUTES.get(name)
        if field is None:
            msg = f"Invalid attribute '{name}' for object AtlasGlossaryTerm"
            raise ValueError(msg)
        setattr(self, field, value)

    def same_as(self, other: AtlasGlossaryTerm) -> bool:
        """``equals``: the shared fields, the anchor, examples, assigned entities and the headers as sets."""
        anchors_equal = (self.anchor is None and other.anchor is None) or (
            self.anchor is not None and self.anchor.same_as(other.anchor)
        )
        return (
            self.base_key() == other.base_key()
            and (self.examples, self.abbreviation, self.usage) == (other.examples, other.abbreviation, other.usage)
            and anchors_equal
            and _entity_keys(self.assigned_entities) == _entity_keys(other.assigned_entities)
            and _keys(self.categories) == _keys(other.categories)
            and all(
                _keys(self.relation_terms(relation)) == _keys(other.relation_terms(relation)) for relation in Relation
            )
        )


class AtlasGlossaryExtInfo(AtlasGlossary):
    """``AtlasGlossaryExtInfo``: the glossary with its terms and categories by GUID (GLS-06, GTM-07)."""

    term_info: dict[str, AtlasGlossaryTerm] | None = None
    category_info: dict[str, AtlasGlossaryCategory] | None = None


def _keys(
    headers: list[AtlasRelatedTermHeader]
    | list[AtlasRelatedCategoryHeader]
    | list[AtlasTermCategorizationHeader]
    | None,
) -> frozenset[Any] | None:
    return None if headers is None else frozenset(header.key() for header in headers)


def _entity_keys(found: list[AtlasRelatedObjectId] | None) -> frozenset[str] | None:
    return None if found is None else frozenset(json.dumps(item.to_json(), sort_keys=True) for item in found)
