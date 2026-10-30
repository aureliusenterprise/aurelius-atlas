"""``GlossaryCategoryUtils`` with ``GlossaryUtils``: a category's relationships and its children's names (GCT-02).

A category's anchor, parent, children and terms are relationships the service writes apart from the category's
entity, as Atlas's ``processCategoryRelations`` writes them; a change of anchor or parent renames the category and,
down the hierarchy, its children, which are answered as the impacted categories to save.
"""

from collections.abc import Iterable
from enum import Enum

from aurelius_atlas_model.errors import AtlasError, AtlasErrorCode
from aurelius_atlas_model.glossary import (
    AtlasGlossary,
    AtlasGlossaryCategory,
    AtlasRelatedCategoryHeader,
    AtlasRelatedTermHeader,
)
from aurelius_atlas_model.instance import AtlasObjectId, AtlasRelationship

from aurelius_atlas_core.delete_type import DeleteType
from aurelius_atlas_core.entity_store import EntityStore
from aurelius_atlas_core.glossary_dto import DataAccess
from aurelius_atlas_core.relationship_store import RelationshipStore

CATEGORY_ANCHOR = "AtlasGlossaryCategoryAnchor"
CATEGORY_HIERARCHY = "AtlasGlossaryCategoryHierarchyLink"
TERM_CATEGORIZATION = "AtlasGlossaryTermCategorization"


class RelationshipOperation(Enum):
    """``GlossaryUtils.RelationshipOperation``."""

    CREATE = "CREATE"
    UPDATE = "UPDATE"
    DELETE = "DELETE"


def glossary_skeleton(guid: str | None) -> AtlasGlossary:
    """``getGlossarySkeleton``."""
    glossary = AtlasGlossary()
    glossary.guid = guid or ""
    return glossary


def category_skeleton(guid: str | None) -> AtlasGlossaryCategory:
    """``getAtlasGlossaryCategorySkeleton``."""
    category = AtlasGlossaryCategory()
    category.guid = guid or ""
    return category


type Impacted = dict[str, AtlasGlossaryCategory]


class GlossaryCategoryUtils:
    """The category relationships of ``store``, written through ``data_access`` and its relationship store."""

    def __init__(self, store: EntityStore, data_access: DataAccess, *, user: str | None = None) -> None:
        self._store = store
        self._data_access = data_access
        self._relationships = RelationshipStore(store, user=user)

    async def process_category_relations(
        self, stored: AtlasGlossaryCategory, updated: AtlasGlossaryCategory, op: RelationshipOperation
    ) -> Impacted:
        """``processCategoryRelations``: anchor, parent, children and terms; the children renamed (GCT-02 to GCT-06)."""
        impacted: Impacted = {}
        await self._anchor(stored, updated, op, impacted)
        await self._parent(stored, updated, op, impacted)
        await self._children(stored, updated, op, impacted)
        await self._terms(stored, updated, op)
        return impacted

    async def _anchor(
        self,
        stored: AtlasGlossaryCategory,
        updated: AtlasGlossaryCategory,
        op: RelationshipOperation,
        impacted: Impacted,
    ) -> None:
        """``processCategoryAnchor``."""
        if updated.anchor is None and op is not RelationshipOperation.DELETE:
            raise AtlasError(AtlasErrorCode.MISSING_MANDATORY_ANCHOR)
        if op is RelationshipOperation.CREATE and updated.anchor is not None:
            if not updated.anchor.glossary_guid:
                raise AtlasError(AtlasErrorCode.INVALID_NEW_ANCHOR_GUID)
            await self._create(CATEGORY_ANCHOR, updated.anchor.glossary_guid, stored.guid)
        elif op is RelationshipOperation.UPDATE and updated.anchor is not None:
            if stored.anchor is not None and stored.anchor.same_as(updated.anchor):
                return
            if updated.anchor.glossary_guid is None:
                raise AtlasError(AtlasErrorCode.INVALID_NEW_ANCHOR_GUID)
            if stored.anchor is not None:
                await self._delete(stored.anchor.relation_guid)
            glossary = await self._data_access.load(glossary_skeleton(updated.anchor.glossary_guid))
            stored.qualified_name = f"{stored.name}@{glossary.qualified_name}"
            await self._create(CATEGORY_ANCHOR, updated.anchor.glossary_guid, stored.guid)
            await self._update_children(stored, stored.children_categories or [], impacted, parent_removed=False)
        elif op is RelationshipOperation.DELETE and stored.anchor is not None:
            await self._delete(stored.anchor.relation_guid)

    async def _parent(
        self,
        stored: AtlasGlossaryCategory,
        updated: AtlasGlossaryCategory,
        op: RelationshipOperation,
        impacted: Impacted,
    ) -> None:
        """``processParentCategory``."""
        new, existing = updated.parent_category, stored.parent_category
        if op is RelationshipOperation.CREATE:
            if new is not None:
                await self._new_parent(stored, new, impacted)
        elif op is RelationshipOperation.UPDATE:
            if _key(new) == _key(existing):
                return
            if existing is None and new is not None:
                await self._new_parent(stored, new, impacted)
            elif new is None and existing is not None:
                await self._parent_removed(stored, updated, existing, impacted)
            elif new is not None and existing is not None:
                if existing.category_guid == new.category_guid:
                    relationship = await self._relationships.get_by_id(str(existing.relation_guid))
                    relationship.set_attribute("description", new.description)
                    await self._relationships.update(relationship)
                else:
                    await self._delete(existing.relation_guid)
                    await self._create(CATEGORY_HIERARCHY, new.category_guid, stored.guid, description=new.description)
        elif existing is not None:
            await self._parent_removed(stored, updated, existing, impacted)

    async def _new_parent(
        self, stored: AtlasGlossaryCategory, parent: AtlasRelatedCategoryHeader, impacted: Impacted
    ) -> None:
        """``processNewParent``: link it and rename the category below its parent."""
        await self._create(CATEGORY_HIERARCHY, parent.category_guid, stored.guid, description=parent.description)
        found = await self._data_access.load(category_skeleton(parent.category_guid))
        stored.qualified_name = f"{stored.name}.{found.qualified_name}"
        await self._update_children(stored, stored.children_categories or [], impacted, parent_removed=False)

    async def _parent_removed(
        self,
        stored: AtlasGlossaryCategory,
        updated: AtlasGlossaryCategory,
        existing: AtlasRelatedCategoryHeader,
        impacted: Impacted,
    ) -> None:
        """``processParentRemoval``: unlink it and rename the category below its glossary."""
        await self._delete(existing.relation_guid)
        anchor = updated.anchor.glossary_guid if updated.anchor is not None else None
        glossary = await self._data_access.load(glossary_skeleton(anchor))
        stored.qualified_name = f"{stored.name}@{glossary.qualified_name}"
        await self._update_children(stored, stored.children_categories or [], impacted, parent_removed=False)

    async def _children(
        self,
        stored: AtlasGlossaryCategory,
        updated: AtlasGlossaryCategory,
        op: RelationshipOperation,
        impacted: Impacted,
    ) -> None:
        """``processCategoryChildren``."""
        new, existing = _by_category(updated.children_categories), _by_category(stored.children_categories)
        if op is RelationshipOperation.DELETE:
            await self._delete_all(header.relation_guid for header in existing.values())
            return
        if op is RelationshipOperation.CREATE or not existing:
            await self._link_children(stored, new.values())
            await self._update_children(stored, list(new.values()), impacted, parent_removed=False)
            return
        if not new:
            await self._delete_all(header.relation_guid for header in existing.values())
            await self._update_children(stored, list(existing.values()), impacted, parent_removed=True)
            return
        added = [header for guid, header in new.items() if guid not in existing]
        await self._link_children(stored, added)
        await self._update_children(stored, added, impacted, parent_removed=False)
        for guid, header in new.items():
            if header.relation_guid is not None and _key(header) != _key(existing.get(guid)):
                relationship = await self._relationships.get_by_id(header.relation_guid)
                relationship.set_attribute("description", header.description)
                await self._relationships.update(relationship)
        await self._delete_all(header.relation_guid for guid, header in existing.items() if guid not in new)

    async def _link_children(
        self, stored: AtlasGlossaryCategory, children: Iterable[AtlasRelatedCategoryHeader]
    ) -> None:
        """``createCategoryRelationships``: children of the category's own glossary only (GCT-03)."""
        listed = {_key(header) for header in stored.children_categories or []}
        for child in children:
            if _key(child) in listed:
                continue
            found = await self._data_access.load(category_skeleton(child.category_guid))
            stored_anchor = stored.anchor.glossary_guid if stored.anchor is not None else None
            child_anchor = found.anchor.glossary_guid if found.anchor is not None else None
            if stored_anchor != child_anchor:
                raise AtlasError(AtlasErrorCode.INVALID_CHILD_CATEGORY_DIFFERENT_GLOSSARY, child.category_guid)
            await self._create(CATEGORY_HIERARCHY, stored.guid, child.category_guid, description=child.description)

    async def _update_children(
        self,
        parent: AtlasGlossaryCategory,
        children: list[AtlasRelatedCategoryHeader],
        impacted: Impacted,
        *,
        parent_removed: bool,
    ) -> None:
        """``updateChildCategories``: each child named below its parent, or its glossary, in its parent's glossary."""
        parent_anchor = parent.anchor.glossary_guid if parent.anchor is not None else None
        for header in children:
            child = await self._data_access.load(category_skeleton(header.category_guid))
            child_anchor = child.anchor.glossary_guid if child.anchor is not None else None
            if parent_removed:
                glossary = await self._data_access.load(glossary_skeleton(child_anchor))
                child.qualified_name = f"{child.name}.{glossary.qualified_name}"
                child.parent_category = None
            else:
                child.qualified_name = f"{child.name}.{parent.qualified_name}"
            if child_anchor != parent_anchor and child.anchor is not None:
                await self._delete(child.anchor.relation_guid)
                await self._create(CATEGORY_ANCHOR, parent_anchor, child.guid)
                child.anchor.glossary_guid = parent_anchor
            impacted[child.guid] = child
            await self._update_children(child, child.children_categories or [], impacted, parent_removed=False)

    async def _terms(
        self, stored: AtlasGlossaryCategory, updated: AtlasGlossaryCategory, op: RelationshipOperation
    ) -> None:
        """``processAssociatedTerms``: the category's term categorizations."""
        new, existing = _by_term(updated.terms), _by_term(stored.terms)
        if op is RelationshipOperation.DELETE:
            await self._delete_all(header.relation_guid for header in existing.values())
            return
        if op is RelationshipOperation.CREATE or not existing:
            await self._categorize(stored, new.values())
            return
        if not new:
            await self._delete_all(header.relation_guid for header in existing.values())
            return
        await self._categorize(stored, [header for guid, header in new.items() if guid not in existing])
        for guid, header in new.items():
            if header.relation_guid is not None and header.key() != existing[guid].key():
                relationship = await self._relationships.get_by_id(header.relation_guid)
                _term_relation_attributes(relationship, header)
                await self._relationships.update(relationship)
        await self._delete_all(header.relation_guid for guid, header in existing.items() if guid not in new)

    async def _categorize(self, stored: AtlasGlossaryCategory, terms: Iterable[AtlasRelatedTermHeader]) -> None:
        """``createTermCategorizationRelationships``."""
        listed = {header.key() for header in stored.terms or []}
        for term in terms:
            if term.term_guid is None:
                raise AtlasError(AtlasErrorCode.MISSING_TERM_ID_FOR_CATEGORIZATION)
            if term.key() in listed:
                continue
            relationship = _relationship(TERM_CATEGORIZATION, stored.guid, term.term_guid)
            _term_relation_attributes(relationship, term)
            await self._get_or_create(relationship)

    async def _create(
        self, type_name: str, end1: str | None, end2: str | None, *, description: str | None = None
    ) -> None:
        relationship = _relationship(type_name, end1, end2)
        if type_name == CATEGORY_HIERARCHY:
            relationship.set_attribute("description", description)
        await self._get_or_create(relationship)

    async def _get_or_create(self, relationship: AtlasRelationship) -> None:
        """``getOrCreate``: a relationship of the type between the ends exists already, or is created."""
        try:
            await self._relationships.create(relationship)
        except AtlasError as error:
            if error.code is not AtlasErrorCode.RELATIONSHIP_ALREADY_EXISTS:
                raise

    async def _delete(self, guid: str | None) -> None:
        """``deleteById(guid, true)``: the relationship removed for good."""
        if guid:
            await self._relationships.delete_by_id(guid, DeleteType.HARD)

    async def _delete_all(self, guids: Iterable[str | None]) -> None:
        for guid in list(guids):
            await self._delete(guid)


def _relationship(type_name: str, end1: str | None, end2: str | None) -> AtlasRelationship:
    return AtlasRelationship(
        type_name=type_name, end1=AtlasObjectId(guid=end1), end2=AtlasObjectId(guid=end2), attributes={}
    )


def _term_relation_attributes(relationship: AtlasRelationship, header: AtlasRelatedTermHeader) -> None:
    """``updateRelationshipAttributes`` of a term relation."""
    for name in ("expression", "description", "steward", "source"):
        relationship.set_attribute(name, getattr(header, name))
    if header.status is not None:
        relationship.set_attribute("status", header.status.value)


def _key(header: AtlasRelatedCategoryHeader | None) -> tuple[object, ...] | None:
    return None if header is None else header.key()


def _by_category(headers: list[AtlasRelatedCategoryHeader] | None) -> dict[str, AtlasRelatedCategoryHeader]:
    """``getChildren``: by category GUID, a header with a relationship over one without."""
    found: dict[str, AtlasRelatedCategoryHeader] = {}
    for header in headers or []:
        known = found.get(str(header.category_guid))
        if known is None or (not known.relation_guid and header.relation_guid):
            found[str(header.category_guid)] = header
    return found


def _by_term(headers: list[AtlasRelatedTermHeader] | None) -> dict[str, AtlasRelatedTermHeader]:
    """``getTerms``: by term GUID, a header with a relationship over one without."""
    found: dict[str, AtlasRelatedTermHeader] = {}
    for header in headers or []:
        known = found.get(str(header.term_guid))
        if known is None or (not known.relation_guid and header.relation_guid):
            found[str(header.term_guid)] = header
    return found
