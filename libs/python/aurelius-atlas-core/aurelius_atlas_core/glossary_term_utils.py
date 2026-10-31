"""``GlossaryTermUtils``: a term's anchor, related terms, categories and assignments, and terms read from a file.

A term's relationships are written apart from its entity, as Atlas's ``processTermRelations`` writes them; a change
of anchor renames the term below its new glossary (GTM-03 to GTM-05). A term is assigned to an entity by a semantic
assignment from the term to the entity, and dissociated by removing it (GTA-02, GTA-03). An import reads the rows of
a file twice: as terms without relations, then as their relations (GIM-03 to GIM-05).
"""

from collections.abc import Iterable, Sequence
from dataclasses import dataclass, field

from aurelius_atlas_model.bulk_import import BulkImportResponse, ImportInfo, ImportStatus
from aurelius_atlas_model.errors import AtlasError, AtlasErrorCode, java_string
from aurelius_atlas_model.glossary import (
    AtlasGlossary,
    AtlasGlossaryHeader,
    AtlasGlossaryTerm,
    AtlasRelatedTermHeader,
    AtlasTermCategorizationHeader,
    Relation,
)
from aurelius_atlas_model.instance import AtlasObjectId, AtlasRelatedObjectId, AtlasRelationship

from aurelius_atlas_core.file_utils import COLON_CHARACTER, PIPE_CHARACTER, Row, java_split
from aurelius_atlas_core.glossary_utils import (
    GlossaryUtils,
    RelationshipOperation,
    glossary_skeleton,
    relationship,
    term_relation_attributes,
    term_skeleton,
)

TERM_ANCHOR = "AtlasGlossaryTermAnchor"
TERM_CATEGORIZATION = "AtlasGlossaryTermCategorization"
TERM_ASSIGNMENT = "AtlasGlossarySemanticAssignment"
INDEX_FOR_GLOSSARY_AT_RECORD = 0
INDEX_FOR_TERM_AT_RECORD = 1
GLOSSARY_TERM_HEADERS = (
    "GlossaryName",
    "TermName",
    "ShortDescription",
    "LongDescription",
    "Examples",
    "Abbreviation",
    "Usage",
    "AdditionalAttributes",
    "TranslationTerms",
    "ValidValuesFor",
    "Synonyms",
    "ReplacedBy",
    "ValidValues",
    "ReplacementTerms",
    "SeeAlso",
    "TranslatedTerms",
    "IsA",
    "Antonyms",
    "Classifies",
    "PreferredToTerms",
    "PreferredTerms",
)
"""The template's columns (``getGlossaryTermHeaders``)."""
IMPORT_RELATIONS = (
    Relation.TRANSLATION_TERMS,
    Relation.VALID_VALUES_FOR,
    Relation.SYNONYMS,
    Relation.REPLACED_BY,
    Relation.VALID_VALUES,
    Relation.REPLACEMENT_TERMS,
    Relation.SEE_ALSO,
    Relation.TRANSLATED_TERMS,
    Relation.ISA,
    Relation.ANTONYMS,
    Relation.CLASSIFIES,
    Relation.PREFERRED_TO_TERMS,
    Relation.PREFERRED_TERMS,
)
"""The relations of the columns after ``AdditionalAttributes``, in their order."""


def glossary_term_headers() -> str:
    """``getGlossaryTermHeaders``: the template, its columns joined by ``, `` (GIM-06)."""
    return ", ".join(GLOSSARY_TERM_HEADERS)


@dataclass
class ImportCache:
    """An import's caches (``glossaryNameGuidCache``, ``glossaryTermOrderCache``, ``glossaryTermQNameGuidCache``)."""

    glossary_guids: dict[str, str | None] = field(default_factory=dict)
    term_order: dict[str, int] = field(default_factory=dict)
    related_guids: dict[str, str] = field(default_factory=dict)


class GlossaryTermUtils(GlossaryUtils):
    """The term relationships of ``store``, written through ``data_access`` and its relationship store."""

    async def process_term_relations(
        self, stored: AtlasGlossaryTerm, updated: AtlasGlossaryTerm, op: RelationshipOperation
    ) -> None:
        """``processTermRelations``: anchor, related terms and categories (GTM-03 to GTM-05)."""
        await self._anchor(stored, updated, op)
        await self._related_terms(stored, updated, op)
        await self._categories(stored, updated, op)

    async def process_term_assignments(self, term: AtlasGlossaryTerm, entities: Iterable[AtlasRelatedObjectId]) -> None:
        """``processTermAssignments``: an assignment from the term to each entity not listed as assigned (GTA-02).

        The entity's relationship attributes are the assignment's.
        """
        listed = [found.to_json() for found in term.assigned_entities or []]
        for entity in entities:
            if entity.to_json() in listed:
                continue
            created = relationship(TERM_ASSIGNMENT, term.guid, entity.guid)
            created.end2 = AtlasObjectId(
                guid=entity.guid, type_name=entity.type_name, unique_attributes=entity.unique_attributes
            )
            given = entity.relationship_attributes
            for name, value in ((given.attributes or {}) if given is not None else {}).items():
                created.set_attribute(name, value)
            await self._get_or_create(created)

    async def process_term_dissociation(
        self, term: AtlasGlossaryTerm, entities: Iterable[AtlasRelatedObjectId]
    ) -> None:
        """``processTermDissociation``: each entity's assignment of the term removed, named by its GUID (GTA-03).

        Raises:
            AtlasError: ``TERM_DISSOCIATION_MISSING_RELATION_GUID`` without one, ``INVALID_TERM_DISSOCIATION`` for
                one that is not the term's assignment to the entity (DV-102).
        """
        assigned = {found.guid: found for found in term.assigned_entities or []}
        for entity in entities:
            if entity.relationship_guid is None:
                raise AtlasError(AtlasErrorCode.TERM_DISSOCIATION_MISSING_RELATION_GUID)
            existing = assigned.get(entity.guid)
            if existing is None or existing.relationship_guid != entity.relationship_guid:
                raise AtlasError(
                    AtlasErrorCode.INVALID_TERM_DISSOCIATION, entity.relationship_guid, term.guid, entity.guid
                )
            await self._delete(entity.relationship_guid)

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

    async def glossary_term_data_without_relations(
        self, rows: Sequence[Row], response: BulkImportResponse, cache: ImportCache
    ) -> list[AtlasGlossaryTerm]:
        """``getGlossaryTermDataWithoutRelations``: a term of each row, its glossary found or created (GIM-03).

        A row without a glossary name, or with one no glossary can be named, is reported failed.
        """
        terms: list[AtlasGlossaryTerm] = []
        for row_number, row in enumerate(rows, start=1):
            failures: list[str] = []
            term = AtlasGlossaryTerm()
            glossary_name = ""
            if not row or _is_blank(row[INDEX_FOR_GLOSSARY_AT_RECORD]):
                failures.append(f"The GlossaryName is blank for the record : {_record(row)}")
            else:
                glossary_name = str(row[INDEX_FOR_GLOSSARY_AT_RECORD])
                guid = cache.glossary_guids.get(glossary_name)
                if not guid:
                    guid = await self._glossary_guid(glossary_name) or await self._create_glossary(
                        glossary_name, failures
                    )
                    cache.glossary_guids[glossary_name] = guid
                if guid:
                    term = await self._term_of(failures, row, guid, relations=False)
                    term.qualified_name = f"{java_string(term.name)}@{glossary_name}"
                    cache.term_order[term.qualified_name] = row_number
                    terms.append(term)
            if failures:
                response.failed_import_info_list.append(
                    ImportInfo(
                        parent_object_name=glossary_name,
                        child_object_name=term.name,
                        import_status=ImportStatus.FAILED,
                        remarks="\n".join(failures),
                        row_number=row_number,
                    )
                )
        return terms

    async def glossary_term_data_with_relations(
        self, rows: Sequence[Row], response: BulkImportResponse, cache: ImportCache
    ) -> list[AtlasGlossaryTerm]:
        """``getGlossaryTermDataWithRelations``: each row's term with its related terms, found by qualified name
        (GIM-04).
        """  # noqa: D205 - one sentence
        terms: list[AtlasGlossaryTerm] = []
        for row_number, row in enumerate(rows, start=1):
            if not row or _is_blank(row[INDEX_FOR_GLOSSARY_AT_RECORD]):
                continue
            failures: list[str] = []
            term = AtlasGlossaryTerm()
            glossary_name = str(row[INDEX_FOR_GLOSSARY_AT_RECORD])
            guid = cache.glossary_guids.get(glossary_name)
            if guid:
                term = await self._term_of(failures, row, guid, relations=True, cache=cache)
                term.qualified_name = f"{java_string(term.name)}@{glossary_name}"
                terms.append(term)
            if failures:
                response.failed_import_info_list.append(
                    ImportInfo(
                        parent_object_name=glossary_name,
                        child_object_name=term.name,
                        import_status=ImportStatus.FAILED,
                        remarks="\n".join(failures),
                        row_number=row_number,
                    )
                )
        return terms

    async def update_glossary_term_relations(self, term: AtlasGlossaryTerm, cache: ImportCache) -> None:
        """``updateGlossaryTermRelations``: a term an earlier row relates to keeps the relations stored (GIM-05)."""
        guid = cache.related_guids.get(str(term.qualified_name))
        if guid is None:
            return
        try:
            stored = await self._data_access.load(term_skeleton(guid))
        except AtlasError:
            return
        for relation in Relation:
            found = stored.relation_terms(relation)
            if found:
                setattr(term, relation.field, [*(term.relation_terms(relation) or []), *found])

    async def _term_of(
        self,
        failures: list[str],
        row: Row,
        glossary_guid: str,
        *,
        relations: bool,
        cache: ImportCache | None = None,
    ) -> AtlasGlossaryTerm:
        """``populateGlossaryTermObject``: the row's term, anchored to the glossary, its relations when asked."""
        term = AtlasGlossaryTerm()
        if len(row) > INDEX_FOR_TERM_AT_RECORD:
            term.name = row[INDEX_FOR_TERM_AT_RECORD]
        if _is_blank(term.name):
            if not relations:
                failures.append(f"The TermName is blank for provided record: {_record(row)}")
            return term
        values = [*row[INDEX_FOR_TERM_AT_RECORD + 1 :], *([None] * len(GLOSSARY_TERM_HEADERS))]
        term.anchor = AtlasGlossaryHeader(glossary_guid=glossary_guid)
        term.short_description, term.long_description = values[0], values[1]
        term.examples = None if _is_blank(values[2]) else java_split(str(values[2]), PIPE_CHARACTER)
        term.abbreviation, term.usage = values[3], values[4]
        term.additional_attributes = _map_value(values[5], failures, relations=relations)
        if relations and cache is not None:
            glossary_name = str(row[INDEX_FOR_GLOSSARY_AT_RECORD])
            for relation, value in zip(IMPORT_RELATIONS, values[6:], strict=False):
                found = await self._related_term_headers(value, str(term.name), glossary_name, failures, cache)
                setattr(term, relation.field, found)
        return term

    async def _related_term_headers(
        self, value: str | None, term_name: str, glossary_name: str, failures: list[str], cache: ImportCache
    ) -> list[AtlasRelatedTermHeader] | None:
        """``getAtlasRelatedTermHeaderSet``: ``glossary:term`` pairs joined by ``|``, each an existing term."""
        if _is_blank(value):
            return None
        found: dict[str, AtlasRelatedTermHeader] = {}
        current = f"{term_name}@{glossary_name}"
        for data in java_split(str(value), PIPE_CHARACTER):
            parts = java_split(data, COLON_CHARACTER)
            if len(parts) != 2:  # noqa: PLR2004 - a glossary and a term
                failures.append(f"Incorrect relation data specified for the term : {current}")
                continue
            related = f"{parts[1]}@{parts[0]}"
            if related.lower() == current.lower():
                failures.append("Invalid relationship specified for Term. Term cannot have a relationship with self")
                continue
            guid = await self._term_guid(related)
            if guid is None:
                failures.append(
                    f"The provided Reference {parts[1]}@{parts[0]} does not exist at Atlas referred at record with "
                    f"TermName  : {term_name} and GlossaryName : {glossary_name}"
                )
                continue
            _cache_related(cache, current, related, guid)
            found.setdefault(guid, AtlasRelatedTermHeader(term_guid=guid))
        return list(found.values())

    async def _glossary_guid(self, name: str) -> str | None:
        """``getGlossaryGUIDFromGraphDB``: the active glossary of the qualified name."""
        return await self._guid_of("AtlasGlossary", name)

    async def _term_guid(self, qualified_name: str) -> str | None:
        return await self._guid_of("AtlasGlossaryTerm", qualified_name)

    async def _guid_of(self, type_name: str, qualified_name: str) -> str | None:
        entity_type = self._store.registry.entity_type(type_name)
        if entity_type is None:  # pragma: no cover - the glossary model is loaded with the server
            return None
        found = await self._store.find_by_unique_attributes(entity_type, {"qualifiedName": qualified_name})
        return None if found is None else found.entity.guid

    async def _create_glossary(self, name: str, failures: list[str]) -> str | None:
        """``createGlossary``: a glossary of the name, unless the name is invalid."""
        if any(character in "@.<>" for character in name):
            invalid = AtlasError(AtlasErrorCode.INVALID_DISPLAY_NAME).message
            failures.append(f"The provided Glossary Name {{{name}}} is invalid : {invalid}")
            return None
        return (await self._data_access.save(AtlasGlossary(qualified_name=name, name=name))).guid


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


def _is_blank(value: str | None) -> bool:
    """``StringUtils.isBlank``."""
    return value is None or not value.strip()


def _record(row: Row) -> str:
    """``Arrays.toString`` of a row."""
    return "[" + ", ".join(java_string(value) for value in row) + "]"


def _map_value(value: str | None, failures: list[str], *, relations: bool) -> dict[str, object] | None:
    """``getMapValue``: ``key:value`` pairs joined by ``|``; the first pass reports a pair that is none."""
    if _is_blank(value):
        return None
    found: dict[str, object] = {}
    for record in java_split(str(value), PIPE_CHARACTER):
        parts = java_split(record, COLON_CHARACTER)
        if parts and len(parts) % 2 == 0:
            found[parts[0]] = parts[1]
        elif not relations:
            failures.append(
                f"The Data in the uploaded file is incorrectly specified  : {value}\n"
                "AdditionalAttributes needs to be a key:value pair"
            )
    return found


def _cache_related(cache: ImportCache, current: str, related: str, guid: str) -> None:
    """``cacheRelatedTermQNameGuid``: a related term of a later row, whose stored relations its update keeps."""
    order = cache.term_order
    if related not in cache.related_guids and current in order and related in order and order[current] < order[related]:
        cache.related_guids[related] = guid
