"""``GlossaryService``: glossaries, their categories and terms (GLS-01 to GLS-06, GCT-01 to GCT-07, GTM-01 to GTM-07).

The assignment of terms to entities follows in 5.2c.
"""

import contextlib
from collections.abc import Sequence
from enum import Enum

from aurelius_atlas_model.errors import AtlasError, AtlasErrorCode
from aurelius_atlas_model.glossary import (
    AtlasGlossary,
    AtlasGlossaryCategory,
    AtlasGlossaryExtInfo,
    AtlasGlossaryTerm,
    AtlasRelatedCategoryHeader,
    AtlasRelatedTermHeader,
    AtlasTermCategorizationHeader,
    Relation,
)

from aurelius_atlas_core.entity_retriever import EntityRetriever
from aurelius_atlas_core.entity_store import EntityStore
from aurelius_atlas_core.glossary_category_utils import GlossaryCategoryUtils
from aurelius_atlas_core.glossary_dto import (
    ATLAS_GLOSSARY_CATEGORY_TYPENAME,
    ATLAS_GLOSSARY_TERM_TYPENAME,
    ATLAS_GLOSSARY_TYPENAME,
    DataAccess,
    glossary_from,
)
from aurelius_atlas_core.glossary_term_utils import GlossaryTermUtils
from aurelius_atlas_core.glossary_utils import (
    RelationshipOperation,
    category_skeleton,
    glossary_skeleton,
    term_skeleton,
)
from aurelius_atlas_core.search_query import SearchQuery

INVALID_NAME_CHARS = frozenset("@.<>")
GLOSSARY_QUALIFIED_NAME_FIELD = "keyword.AtlasGlossary.qualifiedName"
MAX_GLOSSARIES = 10_000
"""The most glossaries a list reads (the search's window)."""


class SortOrder(Enum):
    """``SortOrder``: ``ASC`` unless ``DESC`` (``toSortOrder``)."""

    ASCENDING = "ASC"
    DESCENDING = "DESC"

    @classmethod
    def of(cls, text: str | None) -> SortOrder:
        """``toSortOrder``: ``DESC`` descending, anything else ascending (GLS-05)."""
        return cls.DESCENDING if text == "DESC" else cls.ASCENDING


def is_name_invalid(name: str | None) -> bool:
    """``isNameInvalid``: a name with ``@``, ``.``, ``<`` or ``>`` (GLS-02)."""
    return name is not None and any(character in INVALID_NAME_CHARS for character in name)


def paginate[T](items: Sequence[T], offset: int, limit: int) -> list[T]:
    """``PaginationHelper``: ``limit`` from ``offset``, all for a negative limit; none past the end (GLS-05)."""
    size = len(items)
    limit = size if limit < 0 else min(size, limit)
    start = max(0, offset)
    end = min(limit + start, size)
    if start > size:
        return []
    return list(items[start:end]) if start <= end else list(items)


class GlossaryService:
    """Glossaries, categories and terms of the entities of ``store``."""

    def __init__(self, store: EntityStore, *, user: str | None = None) -> None:
        self._store = store
        self._data_access = DataAccess(store, user=user)
        self._category_utils = GlossaryCategoryUtils(store, self._data_access, user=user)
        self._term_utils = GlossaryTermUtils(store, self._data_access, user=user)

    async def get_glossaries(self, limit: int, offset: int, sort_order: SortOrder) -> list[AtlasGlossary]:
        """``getGlossaries``: every glossary, deleted ones too, by qualified name, paged (GLS-05, DV-100)."""
        hits = await self._store.search(
            SearchQuery(
                type_names=frozenset({ATLAS_GLOSSARY_TYPENAME}),
                sort_field=GLOSSARY_QUALIFIED_NAME_FIELD,
                descending=sort_order is SortOrder.DESCENDING,
                size=MAX_GLOSSARIES,
            )
        )
        retriever = EntityRetriever(self._store)
        found = []
        for stored in paginate(hits.entities, offset, limit):
            entity = (await retriever.entity_with_ext_info(stored.guid)).entity
            if entity is not None:
                found.append(glossary_from(entity))
        return found

    async def create_glossary(self, glossary: AtlasGlossary | None) -> AtlasGlossary:
        """``createGlossary`` (GLS-02).

        Raises:
            AtlasError: ``BAD_REQUEST``, ``GLOSSARY_QUALIFIED_NAME_CANT_BE_DERIVED``, ``INVALID_DISPLAY_NAME`` or
                ``GLOSSARY_ALREADY_EXISTS``.
        """
        if glossary is None:
            raise AtlasError(AtlasErrorCode.BAD_REQUEST, "Glossary definition missing")
        if not glossary.qualified_name:
            if not glossary.name:
                raise AtlasError(AtlasErrorCode.GLOSSARY_QUALIFIED_NAME_CANT_BE_DERIVED)
            if is_name_invalid(glossary.name):
                raise AtlasError(AtlasErrorCode.INVALID_DISPLAY_NAME)
            glossary.qualified_name = glossary.name
        if await self._exists(ATLAS_GLOSSARY_TYPENAME, glossary.qualified_name):
            raise AtlasError(AtlasErrorCode.GLOSSARY_ALREADY_EXISTS, glossary.name)
        return await self._data_access.save(glossary)

    async def get_glossary(self, guid: str | None) -> AtlasGlossary:
        """``getGlossary``: the glossary, its headers' display texts set (GLS-01, GLS-06)."""
        if guid is None:  # pragma: no cover - a path parameter is never null
            raise AtlasError(AtlasErrorCode.BAD_REQUEST, "glossaryGuid is null/empty")
        glossary = await self._data_access.load(glossary_skeleton(guid))
        await self._set_info_for_glossary(glossary)
        return glossary

    async def get_detailed_glossary(self, guid: str) -> AtlasGlossaryExtInfo:
        """``getDetailedGlossary``: the glossary with its terms and categories by GUID (GLS-06, GTM-07)."""
        glossary = await self._data_access.load(glossary_skeleton(guid))
        found = AtlasGlossaryExtInfo.model_validate(glossary.model_dump())
        if glossary.terms:
            terms = await self._data_access.load_all([term_skeleton(header.term_guid) for header in glossary.terms])
            found.term_info = {term.guid: term for term in terms}
        if glossary.categories:
            loaded = await self._data_access.load_all(
                [category_skeleton(header.category_guid) for header in glossary.categories]
            )
            found.category_info = {category.guid: category for category in loaded}
        return found

    async def update_glossary(self, glossary: AtlasGlossary | None) -> AtlasGlossary:
        """``updateGlossary``: written when it differs, its GUID and qualified name kept (GLS-03).

        Raises:
            AtlasError: ``BAD_REQUEST`` or ``INVALID_DISPLAY_NAME``.
        """
        if glossary is None:
            raise AtlasError(AtlasErrorCode.BAD_REQUEST, "Glossary is null/empty")
        _check_name(glossary.name)
        stored = await self._data_access.load(glossary)
        if not stored.same_as(glossary):
            glossary.guid, glossary.qualified_name = stored.guid, stored.qualified_name
            stored = await self._data_access.save(glossary)
            await self._set_info_for_glossary(stored)
        return stored

    async def delete_glossary(self, guid: str) -> None:
        """``deleteGlossary``: its terms and categories, then the glossary (GLS-04, GTM-05)."""
        stored = await self._data_access.load(glossary_skeleton(guid))
        for term in stored.terms or []:
            await self.delete_term(str(term.term_guid))
        for category in stored.categories or []:
            await self.delete_category(str(category.category_guid))
        await self._data_access.delete(guid)

    async def get_category(self, guid: str) -> AtlasGlossaryCategory:
        """``getCategory``: the category, its children's and terms' headers completed (GCT-01)."""
        category = await self._data_access.load(category_skeleton(guid))
        await self._set_info_for_category(category)
        return category

    async def create_category(self, category: AtlasGlossaryCategory | None) -> AtlasGlossaryCategory:
        """``createCategory``: named below its glossary or parent, its relationships written (GCT-02, GCT-03).

        Raises:
            AtlasError: ``BAD_REQUEST``, ``MISSING_MANDATORY_ANCHOR``,
                ``GLOSSARY_CATEGORY_QUALIFIED_NAME_CANT_BE_DERIVED``, ``INVALID_DISPLAY_NAME``,
                ``GLOSSARY_CATEGORY_ALREADY_EXISTS``, ``INVALID_NEW_ANCHOR_GUID`` or
                ``INVALID_CHILD_CATEGORY_DIFFERENT_GLOSSARY``.
        """
        if category is None:
            raise AtlasError(AtlasErrorCode.BAD_REQUEST, "GlossaryCategory definition missing")
        if category.anchor is None:
            raise AtlasError(AtlasErrorCode.MISSING_MANDATORY_ANCHOR)
        if not category.name:
            raise AtlasError(AtlasErrorCode.GLOSSARY_CATEGORY_QUALIFIED_NAME_CANT_BE_DERIVED)
        if is_name_invalid(category.name):
            raise AtlasError(AtlasErrorCode.INVALID_DISPLAY_NAME)
        glossary = await self._data_access.load(glossary_skeleton(category.anchor.glossary_guid))
        category.qualified_name = f"{category.name}@{glossary.qualified_name}"
        await self._check_category_new(category)
        stored = await self._data_access.save(category)
        impacted = await self._category_utils.process_category_relations(stored, category, RelationshipOperation.CREATE)
        stored = await self._renamed(category, stored)
        await self._data_access.save_all(impacted.values())
        await self._set_info_for_category(stored)
        return stored

    async def create_categories(self, categories: list[AtlasGlossaryCategory] | None) -> list[AtlasGlossaryCategory]:
        """``createCategories``: each in turn (GCT-02)."""
        if categories is None:
            raise AtlasError(AtlasErrorCode.BAD_REQUEST, "glossaryCategory is null/empty")
        return [await self.create_category(category) for category in categories]

    async def update_category(self, category: AtlasGlossaryCategory | None) -> AtlasGlossaryCategory:
        """``updateCategory``: written when it differs, its relationships and children following (GCT-04).

        Raises:
            AtlasError: ``BAD_REQUEST``, ``INVALID_DISPLAY_NAME`` or those of the relationships changed.
        """
        if category is None:
            raise AtlasError(AtlasErrorCode.BAD_REQUEST, "GlossaryCategory is null/empty")
        _check_name(category.name)
        stored = await self._data_access.load(category)
        if not stored.same_as(category):
            category.guid, category.qualified_name = stored.guid, stored.qualified_name
            with contextlib.suppress(AtlasError):  # Atlas logs a failed save and goes on with the relationships
                stored = await self._data_access.save(category)
            impacted = await self._category_utils.process_category_relations(
                stored, category, RelationshipOperation.UPDATE
            )
            stored = await self._renamed(category, stored)
            await self._data_access.save_all(impacted.values())
        await self._set_info_for_category(stored)
        return stored

    async def delete_category(self, guid: str) -> None:
        """``deleteCategory``: its relationships, then the category (GCT-06)."""
        stored = await self._data_access.load(category_skeleton(guid))
        await self._category_utils.process_category_relations(stored, stored, RelationshipOperation.DELETE)
        await self._data_access.delete(guid)

    async def get_glossary_categories_headers(
        self, guid: str, offset: int, limit: int, sort_order: SortOrder
    ) -> list[AtlasRelatedCategoryHeader]:
        """``getGlossaryCategoriesHeaders``: by display text, paged (GLS-05)."""
        glossary = await self.get_glossary(guid)
        headers = sorted(
            glossary.categories or [],
            key=lambda header: header.display_text or "",
            reverse=sort_order is SortOrder.DESCENDING,
        )
        return paginate(headers, offset, limit)

    async def get_glossary_categories(
        self, guid: str, offset: int, limit: int, sort_order: SortOrder
    ) -> list[AtlasGlossaryCategory]:
        """``getGlossaryCategories``: the categories of those headers (GLS-05)."""
        headers = await self.get_glossary_categories_headers(guid, offset, limit, sort_order)
        return [await self._data_access.load(category_skeleton(header.category_guid)) for header in headers]

    async def get_related_categories(self, guid: str) -> dict[str, list[AtlasRelatedCategoryHeader]]:
        """``getRelatedCategories``: its parent and children, each only when there is one (GCT-07)."""
        category = await self.get_category(guid)
        found: dict[str, list[AtlasRelatedCategoryHeader]] = {}
        if category.parent_category is not None:
            found["parent"] = [category.parent_category]
        if category.children_categories:
            found["children"] = list(category.children_categories)
        return found

    async def get_term(self, guid: str) -> AtlasGlossaryTerm:
        """``getTerm``: the term, its categories' and related terms' headers completed (GTM-01)."""
        term = await self._data_access.load(term_skeleton(guid))
        await self._set_info_for_term(term)
        return term

    async def create_term(self, term: AtlasGlossaryTerm | None) -> AtlasGlossaryTerm:
        """``createTerm``: named below its glossary, its relationships written (GTM-02, GTM-03).

        Raises:
            AtlasError: ``BAD_REQUEST``, ``MISSING_MANDATORY_ANCHOR``, ``GLOSSARY_TERM_QUALIFIED_NAME_CANT_BE_DERIVED``,
                ``INVALID_DISPLAY_NAME``, ``GLOSSARY_QUALIFIED_NAME_CANT_BE_DERIVED``, ``GLOSSARY_TERM_ALREADY_EXISTS``
                or ``INVALID_TERM_RELATION_TO_SELF``.
        """
        if term is None:
            raise AtlasError(AtlasErrorCode.BAD_REQUEST, "GlossaryTerm definition missing")
        if term.anchor is None:
            raise AtlasError(AtlasErrorCode.MISSING_MANDATORY_ANCHOR)
        if not term.name:
            raise AtlasError(AtlasErrorCode.GLOSSARY_TERM_QUALIFIED_NAME_CANT_BE_DERIVED)
        if is_name_invalid(term.name):
            raise AtlasError(AtlasErrorCode.INVALID_DISPLAY_NAME)
        glossary_name = await self._glossary_qualified_name(term.anchor.glossary_guid)
        if not glossary_name:
            raise AtlasError(AtlasErrorCode.GLOSSARY_QUALIFIED_NAME_CANT_BE_DERIVED)
        term.qualified_name = f"{term.name}@{glossary_name}"
        if await self._term_in_glossary(term):
            raise AtlasError(AtlasErrorCode.GLOSSARY_TERM_ALREADY_EXISTS, term.qualified_name)
        stored = await self._data_access.save(term)
        await self._term_utils.process_term_relations(stored, term, RelationshipOperation.CREATE)
        stored = await self._data_access.load(term)
        await self._set_info_for_term(stored)
        return stored

    async def create_terms(self, terms: list[AtlasGlossaryTerm] | None) -> list[AtlasGlossaryTerm]:
        """``createTerms``: each in turn (GTM-02)."""
        if terms is None:
            raise AtlasError(AtlasErrorCode.BAD_REQUEST, "glossaryTerm(s) is null/empty")
        return [await self.create_term(term) for term in terms]

    async def update_term(self, term: AtlasGlossaryTerm | None) -> AtlasGlossaryTerm:
        """``updateTerm``: written when it differs, its relationships following, renamed on a new anchor (GTM-04).

        Raises:
            AtlasError: ``BAD_REQUEST``, ``INVALID_DISPLAY_NAME``, ``GLOSSARY_TERM_ALREADY_EXISTS`` or those of the
                relationships changed.
        """
        if term is None:
            raise AtlasError(AtlasErrorCode.BAD_REQUEST, "atlasGlossaryTerm is null/empty")
        _check_name(term.name)
        duplicate = await self._duplicate_related_term(term)
        if duplicate:
            raise AtlasError(AtlasErrorCode.GLOSSARY_TERM_ALREADY_EXISTS, duplicate)
        stored = await self._data_access.load(term)
        if not stored.same_as(term):
            term.guid, term.qualified_name = stored.guid, stored.qualified_name
            stored = await self._data_access.save(term)
            await self._term_utils.process_term_relations(stored, term, RelationshipOperation.UPDATE)
            if stored.qualified_name == term.qualified_name:
                stored = await self._data_access.load(term)
            else:
                term.qualified_name = stored.qualified_name
                if await self._exists(ATLAS_GLOSSARY_TERM_TYPENAME, term.qualified_name):
                    raise AtlasError(AtlasErrorCode.GLOSSARY_TERM_ALREADY_EXISTS, term.qualified_name)
                stored = await self._data_access.save(term)
        await self._set_info_for_term(stored)
        return stored

    async def delete_term(self, guid: str) -> None:
        """``deleteTerm``: its relationships, then the term; not while it is assigned (GTM-05).

        Raises:
            AtlasError: ``TERM_HAS_ENTITY_ASSOCIATION``.
        """
        stored = await self._data_access.load(term_skeleton(guid))
        if stored.assigned_entities:
            raise AtlasError(
                AtlasErrorCode.TERM_HAS_ENTITY_ASSOCIATION, stored.guid, str(len(stored.assigned_entities))
            )
        await self._term_utils.process_term_relations(stored, stored, RelationshipOperation.DELETE)
        await self._data_access.delete(guid)

    async def get_glossary_terms_headers(
        self, guid: str, offset: int, limit: int, sort_order: SortOrder
    ) -> list[AtlasRelatedTermHeader]:
        """``getGlossaryTermsHeaders``: by display text, paged (GTM-06)."""
        glossary = await self.get_glossary(guid)
        return _sorted_page(glossary.terms, offset, limit, sort_order)

    async def get_glossary_terms(
        self, guid: str, offset: int, limit: int, sort_order: SortOrder
    ) -> list[AtlasGlossaryTerm]:
        """``getGlossaryTerms``: the terms of those headers (GTM-06)."""
        headers = await self.get_glossary_terms_headers(guid, offset, limit, sort_order)
        return [await self._data_access.load(term_skeleton(header.term_guid)) for header in headers]

    async def get_category_terms(
        self, guid: str, offset: int, limit: int, sort_order: SortOrder
    ) -> list[AtlasRelatedTermHeader]:
        """``getCategoryTerms``: by display text, paged (GTM-06)."""
        category = await self.get_category(guid)
        return _sorted_page(category.terms, offset, limit, sort_order)

    async def get_related_terms(self, guid: str) -> dict[Relation, list[AtlasRelatedTermHeader]]:
        """``getRelatedTerms``: the term's related terms by relation, none without (GTM-06)."""
        return (await self.get_term(guid)).related_terms()

    async def _renamed(self, category: AtlasGlossaryCategory, stored: AtlasGlossaryCategory) -> AtlasGlossaryCategory:
        """The category as stored, saved again under the name its relationships gave it (GCT-02 to GCT-04)."""
        if category.qualified_name == stored.qualified_name:
            return await self._data_access.load(category)
        category.qualified_name = stored.qualified_name
        await self._check_category_new(category)
        return await self._data_access.save(category)

    async def _check_category_new(self, category: AtlasGlossaryCategory) -> None:
        if await self._exists(ATLAS_GLOSSARY_CATEGORY_TYPENAME, category.qualified_name):
            raise AtlasError(AtlasErrorCode.GLOSSARY_CATEGORY_ALREADY_EXISTS, category.qualified_name)

    async def _exists(self, type_name: str, qualified_name: str | None) -> bool:
        """``glossaryExists`` and ``categoryExists``: an entity of the type holding the qualified name."""
        entity_type = self._store.registry.entity_type(type_name)
        if entity_type is None:  # pragma: no cover - the glossary model is loaded with the server
            return False
        return await self._store.find_by_unique_attributes(entity_type, {"qualifiedName": qualified_name}) is not None

    async def _glossary_qualified_name(self, guid: str | None) -> str | None:
        """``getGlossaryQualifiedName``: the qualified name of the entity of the GUID, if there is one."""
        found = None if guid is None else await self._store.get(guid)
        return None if found is None else found.entity.attributes.get(f"{ATLAS_GLOSSARY_TYPENAME}.qualifiedName")

    async def _term_in_glossary(self, term: AtlasGlossaryTerm) -> bool:
        """``termExists2``: a term anchored to the term's glossary holds its qualified name."""
        glossary = await self._data_access.load(glossary_skeleton(term.anchor.glossary_guid if term.anchor else None))
        guids = [str(header.term_guid) for header in glossary.terms or []]
        found = await self._store.get_many(guids)
        return any(
            versioned.entity.attributes.get(f"{ATLAS_GLOSSARY_TERM_TYPENAME}.qualifiedName") == term.qualified_name
            for versioned in found.values()
        )

    async def _duplicate_related_term(self, term: AtlasGlossaryTerm) -> str | None:
        """``getDuplicateGlossaryRelatedTerm``: the qualified name of a term listed twice in one relation."""
        for headers in term.related_terms().values():
            guids = [header.term_guid for header in headers]
            twice = next((guid for guid in guids if guids.count(guid) > 1), None)
            if twice is not None:
                return (await self.get_term(str(twice))).qualified_name
        return None

    async def _set_info_for_glossary(self, glossary: AtlasGlossary) -> None:
        """``setInfoForRelations`` of a glossary: its terms' names and its categories' names and parents."""
        if glossary.terms is not None:
            await self._set_term_names(glossary.terms)
        if glossary.categories is not None:
            await self._set_category_info(glossary.categories)

    async def _set_info_for_category(self, category: AtlasGlossaryCategory) -> None:
        """``setInfoForRelations`` of a category: its children's names and parents, its terms' names."""
        if category.children_categories is not None:
            await self._set_category_info(category.children_categories)
        if category.terms is not None:
            await self._set_term_names(category.terms)

    async def _set_info_for_term(self, term: AtlasGlossaryTerm) -> None:
        """``setInfoForRelations`` of a term: its categories' names, its related terms' names and qualified names."""
        if term.categories:
            await self._set_category_names(term.categories)
        for headers in term.related_terms().values():
            await self._set_term_names(headers, qualified=True)

    async def _set_category_names(self, headers: list[AtlasTermCategorizationHeader]) -> None:
        """``setDisplayNameForCategories``: each category's name."""
        found = await self._store.get_many([str(header.category_guid) for header in headers])
        for header in headers:
            versioned = found.get(str(header.category_guid))
            name = (
                None
                if versioned is None
                else versioned.entity.attributes.get(f"{ATLAS_GLOSSARY_CATEGORY_TYPENAME}.name")
            )
            if name:
                header.display_text = name

    async def _set_category_info(self, headers: list[AtlasRelatedCategoryHeader]) -> None:
        """``setInfoForRelatedCategories``."""
        loaded = await self._data_access.load_all([category_skeleton(header.category_guid) for header in headers])
        by_guid = {category.guid: category for category in loaded}
        for header in headers:
            category = by_guid.get(str(header.category_guid))
            if category is None:
                continue
            header.display_text = category.name
            if category.parent_category is not None:
                header.parent_category_guid = category.parent_category.category_guid

    async def _set_term_names(self, headers: list[AtlasRelatedTermHeader], *, qualified: bool = False) -> None:
        """``setDisplayNameForTerms``: each term's name; ``setQualifiedNameForTerms``: its qualified name too."""
        found = await self._store.get_many([str(header.term_guid) for header in headers])
        for header in headers:
            versioned = found.get(str(header.term_guid))
            attributes = {} if versioned is None else versioned.entity.attributes
            name = attributes.get(f"{ATLAS_GLOSSARY_TERM_TYPENAME}.name")
            if name:
                header.display_text = name
            qualified_name = attributes.get(f"{ATLAS_GLOSSARY_TERM_TYPENAME}.qualifiedName")
            if qualified and qualified_name:
                header.qualified_name = qualified_name


def _sorted_page(
    headers: list[AtlasRelatedTermHeader] | None, offset: int, limit: int, sort_order: SortOrder
) -> list[AtlasRelatedTermHeader]:
    """Term headers by display text, paged (GTM-06)."""
    found = sorted(
        headers or [], key=lambda header: header.display_text or "", reverse=sort_order is SortOrder.DESCENDING
    )
    return paginate(found, offset, limit)


def _check_name(name: str | None) -> None:
    """The name an update needs (GLS-03, GCT-04, GTM-04)."""
    if not name:
        raise AtlasError(AtlasErrorCode.BAD_REQUEST, "DisplayName can't be null/empty")
    if is_name_invalid(name):
        raise AtlasError(AtlasErrorCode.INVALID_DISPLAY_NAME)
