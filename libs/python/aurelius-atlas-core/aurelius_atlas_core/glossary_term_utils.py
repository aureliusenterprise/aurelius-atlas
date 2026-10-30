"""``GlossaryTermUtils``: a term's anchor, related terms and categories (GTM-03 to GTM-05).

A term's relationships are written apart from its entity, as Atlas's ``processTermRelations`` writes them; a change
of anchor renames the term below its new glossary. Assigning terms to entities follows in 5.2c.
"""

from collections.abc import Iterable

from aurelius_atlas_model.errors import AtlasError, AtlasErrorCode
from aurelius_atlas_model.glossary import (
    AtlasGlossaryTerm,
    AtlasRelatedTermHeader,
    AtlasTermCategorizationHeader,
    Relation,
)
from aurelius_atlas_model.instance import AtlasRelationship

from aurelius_atlas_core.glossary_utils import (
    GlossaryUtils,
    RelationshipOperation,
    glossary_skeleton,
    relationship,
    term_relation_attributes,
)

TERM_ANCHOR = "AtlasGlossaryTermAnchor"
TERM_CATEGORIZATION = "AtlasGlossaryTermCategorization"


class GlossaryTermUtils(GlossaryUtils):
    """The term relationships of ``store``, written through ``data_access`` and its relationship store."""

    async def process_term_relations(
        self, stored: AtlasGlossaryTerm, updated: AtlasGlossaryTerm, op: RelationshipOperation
    ) -> None:
        """``processTermRelations``: anchor, related terms and categories (GTM-03 to GTM-05)."""
        await self._anchor(stored, updated, op)
        await self._related_terms(stored, updated, op)
        await self._categories(stored, updated, op)

    async def _anchor(self, stored: AtlasGlossaryTerm, updated: AtlasGlossaryTerm, op: RelationshipOperation) -> None:
        """``processTermAnchor``: a new anchor moves the term below its glossary."""
        if updated.anchor is None and op is not RelationshipOperation.DELETE:
            raise AtlasError(AtlasErrorCode.MISSING_MANDATORY_ANCHOR)
        current = stored.anchor.glossary_guid if stored.anchor is not None else None
        if op is RelationshipOperation.CREATE and updated.anchor is not None:
            if updated.anchor.glossary_guid is None:
                raise AtlasError(AtlasErrorCode.INVALID_NEW_ANCHOR_GUID)
            if updated.anchor.glossary_guid != current:
                await self._get_or_create(relationship(TERM_ANCHOR, updated.anchor.glossary_guid, stored.guid))
        elif op is RelationshipOperation.UPDATE and updated.anchor is not None:
            if updated.anchor.same_as(stored.anchor):
                return
            if updated.anchor.glossary_guid is None:
                raise AtlasError(AtlasErrorCode.INVALID_NEW_ANCHOR_GUID)
            if stored.anchor is not None:
                await self._delete(stored.anchor.relation_guid)
            glossary = await self._data_access.load(glossary_skeleton(updated.anchor.glossary_guid))
            stored.qualified_name = f"{stored.name}@{glossary.qualified_name}"
            await self._get_or_create(relationship(TERM_ANCHOR, updated.anchor.glossary_guid, stored.guid))
        elif op is RelationshipOperation.DELETE and stored.anchor is not None:
            await self._delete(stored.anchor.relation_guid)

    async def _related_terms(
        self, stored: AtlasGlossaryTerm, updated: AtlasGlossaryTerm, op: RelationshipOperation
    ) -> None:
        """``processRelatedTerms``: per relation, the listed terms added, changed and removed."""
        for relation in Relation:
            new, existing = _by_term(updated.relation_terms(relation)), _by_term(stored.relation_terms(relation))
            if op is RelationshipOperation.DELETE:
                await self._delete_all(header.relation_guid for header in existing.values())
            elif op is RelationshipOperation.CREATE or not existing:
                await self._relate(stored, relation, new.values())
            elif not new:
                await self._delete_all(header.relation_guid for header in existing.values())
            else:
                await self._relate(stored, relation, [header for guid, header in new.items() if guid not in existing])
                for guid, header in new.items():
                    if header.relation_guid is not None and header.key() != _key(existing.get(guid)):
                        found = await self._relationships.get_by_id(header.relation_guid)
                        term_relation_attributes(found, header)
                        await self._relationships.update(found)
                await self._delete_all(header.relation_guid for guid, header in existing.items() if guid not in new)

    async def _relate(
        self, stored: AtlasGlossaryTerm, relation: Relation, terms: Iterable[AtlasRelatedTermHeader]
    ) -> None:
        """``createTermRelationships``: of the relation's type, the term on the relation's side; never to itself."""
        existing = _by_term(stored.relation_terms(relation))
        for term in terms:
            if term.term_guid in existing:
                continue
            if term.term_guid == stored.guid:
                raise AtlasError(AtlasErrorCode.INVALID_TERM_RELATION_TO_SELF)
            ends = (term.term_guid, stored.guid) if relation.is_end2_attr else (stored.guid, term.term_guid)
            created = relationship(relation.type_name, *ends)
            term_relation_attributes(created, term)
            await self._get_or_create(created)

    async def _categories(
        self, stored: AtlasGlossaryTerm, updated: AtlasGlossaryTerm, op: RelationshipOperation
    ) -> None:
        """``processAssociatedCategories``: the term's categorizations added, changed and removed."""
        new, existing = _by_category(updated.categories), _by_category(stored.categories)
        if op is RelationshipOperation.DELETE:
            await self._delete_all(header.relation_guid for header in existing.values())
        elif op is RelationshipOperation.CREATE or not existing:
            await self._categorize(stored, new.values())
        elif not new:
            await self._delete_all(header.relation_guid for header in existing.values())
        else:
            await self._categorize(stored, [header for guid, header in new.items() if guid not in existing])
            for guid, header in new.items():
                if header.relation_guid is not None and header.key() != _key(existing.get(guid)):
                    found = await self._relationships.get_by_id(header.relation_guid)
                    _categorization_attributes(found, header)
                    await self._relationships.update(found)
            await self._delete_all(header.relation_guid for guid, header in existing.items() if guid not in new)

    async def _categorize(self, stored: AtlasGlossaryTerm, categories: Iterable[AtlasTermCategorizationHeader]) -> None:
        """``createTermCategorizationRelationships``: from each category to the term."""
        listed = {header.key() for header in stored.categories or []}
        for category in categories:
            if category.key() in listed:
                continue
            created = relationship(TERM_CATEGORIZATION, category.category_guid, stored.guid)
            _categorization_attributes(created, category)
            await self._get_or_create(created)


def _categorization_attributes(found: AtlasRelationship, header: AtlasTermCategorizationHeader) -> None:
    """``updateRelationshipAttributes`` of a categorization."""
    found.set_attribute("description", header.description)
    if header.status is not None:
        found.set_attribute("status", header.status.value)


def _key(header: AtlasRelatedTermHeader | AtlasTermCategorizationHeader | None) -> tuple[object, ...] | None:
    return None if header is None else header.key()


def _by_term(headers: list[AtlasRelatedTermHeader] | None) -> dict[str | None, AtlasRelatedTermHeader]:
    """``getRelatedTermHeaders``: by term GUID, a header with a relationship over one without."""
    found: dict[str | None, AtlasRelatedTermHeader] = {}
    for header in headers or []:
        known = found.get(header.term_guid)
        if known is None or (not known.relation_guid and header.relation_guid):
            found[header.term_guid] = header
    return found


def _by_category(
    headers: list[AtlasTermCategorizationHeader] | None,
) -> dict[str | None, AtlasTermCategorizationHeader]:
    """``getAssociatedCategories``: by category GUID, a header with a relationship over one without."""
    found: dict[str | None, AtlasTermCategorizationHeader] = {}
    for header in headers or []:
        known = found.get(header.category_guid)
        if known is None or (not known.relation_guid and header.relation_guid):
            found[header.category_guid] = header
    return found
