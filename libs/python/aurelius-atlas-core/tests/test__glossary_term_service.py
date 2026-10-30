"""Glossary terms (GTM-01 to GTM-07) on the in-memory documents.

Read from ``GlossaryService``, ``GlossaryTermUtils``, ``DataAccess`` and ``AtlasGlossaryTermDTO`` of Apache Atlas
2.4.0, with the terms of its ``GlossaryServiceTest``, on its ``0011-glossary_model``.
"""

import json

import pytest
from aurelius_atlas_core.entity_store import EntityStore
from aurelius_atlas_core.entity_writer import EntityWriter
from aurelius_atlas_core.glossary_service import GlossaryService, SortOrder
from aurelius_atlas_core.model_loader import BUILTIN_MODELS_DIR
from aurelius_atlas_core.relationship_store import RelationshipStore
from aurelius_atlas_core.testing.memory import MemoryEntityDocuments
from aurelius_atlas_model.errors import AtlasError, AtlasErrorCode
from aurelius_atlas_model.glossary import (
    AtlasGlossary,
    AtlasGlossaryCategory,
    AtlasGlossaryHeader,
    AtlasGlossaryTerm,
    AtlasRelatedTermHeader,
    AtlasTermCategorizationHeader,
    AtlasTermRelationshipStatus,
    Relation,
)
from aurelius_atlas_model.instance import AtlasEntitiesWithExtInfo, AtlasEntity, AtlasObjectId, AtlasRelationship
from aurelius_atlas_model.typedef import AtlasTypesDef
from aurelius_atlas_typesystem.registry import TypeRegistry

S = "aurelius_atlas_core.glossary_service.GlossaryService"
D = "aurelius_atlas_core.glossary_dto"
T = "aurelius_atlas_core.glossary_term_utils.GlossaryTermUtils"
MODELS = BUILTIN_MODELS_DIR / "0000-Area0"


@pytest.fixture
def store() -> EntityStore:
    """A store with the base and glossary models."""
    registry = TypeRegistry()
    with registry.update() as transient:
        for name in ("0010-base_model.json", "0011-glossary_model.json"):
            transient.add_types(AtlasTypesDef.model_validate(json.loads((MODELS / name).read_text(encoding="utf-8"))))
    return EntityStore(registry, MemoryEntityDocuments())


@pytest.fixture
def service(store: EntityStore) -> GlossaryService:
    """The service on that store."""
    return GlossaryService(store)


@pytest.fixture
async def bank(service: GlossaryService) -> AtlasGlossary:
    """``testBankingGlossary``."""
    return await service.create_glossary(AtlasGlossary(name="testBankingGlossary"))


def new_term(name: str, glossary_guid: str | None, **fields: object) -> AtlasGlossaryTerm:
    """A term of the glossary, as ``GlossaryServiceTest`` sets it up."""
    return AtlasGlossaryTerm.model_validate(
        {
            "name": name,
            "shortDescription": "Short description",
            "longDescription": "Long description",
            "examples": ["Personal", "Joint"],
            "usage": "N/A",
            "anchor": None if glossary_guid is None else {"glossaryGuid": glossary_guid},
            **fields,
        }
    )


def related(guid: str, **fields: object) -> AtlasRelatedTermHeader:
    """A related term's header with ``testTermCreateWithRelation``'s attributes."""
    return AtlasRelatedTermHeader.model_validate(
        {
            "termGuid": guid,
            "description": "test description",
            "expression": "test expression",
            "source": "UT",
            "steward": "UT",
            "status": "ACTIVE",
            **fields,
        }
    )


async def failure(awaitable: object) -> AtlasErrorCode:
    """The code of the error the awaitable raises."""
    with pytest.raises(AtlasError) as raised:
        await awaitable  # type: ignore[misc]
    return raised.value.code


@pytest.mark.covers(
    f"{S}.create_term",
    f"{S}.get_term",
    f"{D}.term_from",
    f"{D}.to_entity",
    "aurelius_atlas_core.glossary_utils.term_skeleton",
    f"{T}.process_term_relations",
    rules=["GTM-01", "GTM-02"],
)
async def test__a_term_is_named_below_its_glossary(service: GlossaryService, bank: AtlasGlossary) -> None:
    """``testTermCreationWithoutAnyRelations``: ``name@glossary``, anchored; the glossary lists it."""
    created = await service.create_term(new_term("A checking account", bank.guid, abbreviation="CHK"))
    assert (created.qualified_name, created.abbreviation, created.examples, created.usage) == (
        "A checking account@testBankingGlossary",
        "CHK",
        ["Personal", "Joint"],
        "N/A",
    )
    assert created.anchor is not None
    assert created.anchor.glossary_guid == bank.guid
    assert created.anchor.relation_guid
    assert (await service.get_term(created.guid)).same_as(created)
    listed = await service.get_glossary(bank.guid)
    assert [(header.term_guid, header.display_text) for header in listed.terms or []] == [
        (created.guid, "A checking account")
    ]


@pytest.mark.covers(f"{S}.create_term", f"{S}.create_terms", rules=["GTM-02"])
async def test__a_term_needs_an_anchor_and_a_unique_valid_name(service: GlossaryService, bank: AtlasGlossary) -> None:
    """The anchor, the name and its characters, the glossary's name, and no second term of the name."""
    await service.create_term(new_term("t", bank.guid))
    assert await failure(service.create_term(None)) is AtlasErrorCode.BAD_REQUEST
    assert await failure(service.create_terms(None)) is AtlasErrorCode.BAD_REQUEST
    assert await failure(service.create_term(new_term("t", None))) is AtlasErrorCode.MISSING_MANDATORY_ANCHOR
    no_name = new_term("", bank.guid)
    assert await failure(service.create_term(no_name)) is AtlasErrorCode.GLOSSARY_TERM_QUALIFIED_NAME_CANT_BE_DERIVED
    bad = new_term("current@account", bank.guid)
    assert await failure(service.create_term(bad)) is AtlasErrorCode.INVALID_DISPLAY_NAME
    lost = new_term("t", "nope")
    assert await failure(service.create_term(lost)) is AtlasErrorCode.GLOSSARY_QUALIFIED_NAME_CANT_BE_DERIVED
    assert await failure(service.create_term(new_term("t", bank.guid))) is AtlasErrorCode.GLOSSARY_TERM_ALREADY_EXISTS
    created = await service.create_terms([new_term("u", bank.guid), new_term("v", bank.guid)])
    assert [term.qualified_name for term in created] == ["u@testBankingGlossary", "v@testBankingGlossary"]


@pytest.mark.covers(
    f"{S}.create_term",
    f"{S}.get_related_terms",
    f"{D}.related_term_header",
    "aurelius_atlas_core.glossary_utils.term_relation_attributes",
    "aurelius_atlas_core.glossary_utils.relationship",
    rules=["GTM-01", "GTM-03", "GTM-06"],
)
async def test__related_terms_are_relationships_of_the_relations_type(
    service: GlossaryService, bank: AtlasGlossary, store: EntityStore
) -> None:
    """``testTermCreateWithRelation``: the header's attributes on the relationship; both terms list it."""
    checking = await service.create_term(new_term("A checking account", bank.guid))
    savings = await service.create_term(new_term("A savings account", bank.guid, seeAlso=[related(checking.guid)]))
    assert [(h.term_guid, h.display_text, h.qualified_name, h.status) for h in savings.see_also or []] == [
        (
            checking.guid,
            "A checking account",
            "A checking account@testBankingGlossary",
            AtlasTermRelationshipStatus.ACTIVE,
        )
    ]
    header = (savings.see_also or [])[0]
    found = await RelationshipStore(store).get_by_id(str(header.relation_guid))
    assert (found.type_name, found.end1.guid if found.end1 else None) == ("AtlasGlossaryRelatedTerm", savings.guid)
    assert (header.description, header.expression, header.source, header.steward) == (
        "test description",
        "test expression",
        "UT",
        "UT",
    )
    assert [h.term_guid for h in (await service.get_term(checking.guid)).see_also or []] == [savings.guid]
    assert set(await service.get_related_terms(savings.guid)) == {Relation.SEE_ALSO}
    assert await service.get_related_terms((await service.create_term(new_term("lone", bank.guid))).guid) == {}


@pytest.mark.covers(f"{S}.create_term", f"{T}.process_term_relations", rules=["GTM-03"])
async def test__an_end2_relation_points_from_the_related_term(
    service: GlossaryService, bank: AtlasGlossary, store: EntityStore
) -> None:
    """``isA`` is the relationship's second end: the related term classifies this one."""
    general = await service.create_term(new_term("account", bank.guid))
    special = await service.create_term(new_term("savings", bank.guid, isA=[related(general.guid)]))
    header = (special.is_a or [])[0]
    found = await RelationshipStore(store).get_by_id(str(header.relation_guid))
    assert (found.type_name, found.end1.guid if found.end1 else None, found.end2.guid if found.end2 else None) == (
        "AtlasGlossaryIsARelationship",
        general.guid,
        special.guid,
    )
    assert [h.term_guid for h in (await service.get_term(general.guid)).classifies or []] == [special.guid]


@pytest.mark.covers(
    f"{S}.create_term", f"{D}.categorization_header", f"{S}.get_category_terms", rules=["GTM-01", "GTM-03", "GTM-06"]
)
async def test__a_term_is_categorized_from_its_category(service: GlossaryService, bank: AtlasGlossary) -> None:
    """``testTermCreationWithCategory`` and ``testGetCategoryTerms``: the categorization's attributes, paged."""
    mortgage = await service.create_category(
        AtlasGlossaryCategory(name="Mortgage", anchor=AtlasGlossaryHeader(glossary_guid=bank.guid))
    )
    header = AtlasTermCategorizationHeader(
        category_guid=mortgage.guid, description="Test description", status=AtlasTermRelationshipStatus.DRAFT
    )
    fixed, adjustable = await service.create_terms(
        [
            new_term("Conventional mortgage", bank.guid, categories=[header.to_json()]),
            new_term("ARM loans", bank.guid, categories=[header.to_json()]),
        ]
    )
    assert [(h.category_guid, h.display_text, h.description, h.status) for h in fixed.categories or []] == [
        (mortgage.guid, "Mortgage", "Test description", AtlasTermRelationshipStatus.DRAFT)
    ]
    names = [h.display_text for h in await service.get_category_terms(mortgage.guid, 0, -1, SortOrder.ASCENDING)]
    assert names == ["ARM loans", "Conventional mortgage"]
    for offset, limit, expected in ((0, -1, 2), (0, 2, 2), (1, 5, 1), (2, 5, 0)):
        assert len(await service.get_category_terms(mortgage.guid, offset, limit, SortOrder.ASCENDING)) == expected
    descending = await service.get_category_terms(mortgage.guid, 0, 1, SortOrder.DESCENDING)
    assert [h.term_guid for h in descending] == [fixed.guid]
    assert adjustable.categories is not None


@pytest.mark.covers(f"{S}.update_term", rules=["GTM-04"])
async def test__an_update_keeps_the_guid_and_qualified_name(service: GlossaryService, bank: AtlasGlossary) -> None:
    """``testUpdateGlossaryTerm``: the descriptions changed, the name kept as the qualified name's."""
    created = await service.create_term(new_term("Test term update", bank.guid))
    change = await service.get_term(created.guid)
    change.short_description, change.qualified_name = "Updated short description", "ignored"
    updated = await service.update_term(change)
    assert (updated.guid, updated.short_description, updated.qualified_name) == (
        created.guid,
        "Updated short description",
        "Test term update@testBankingGlossary",
    )
    assert (await service.update_term(updated)).same_as(updated)
    change.name = "<Test term update>"
    assert await failure(service.update_term(change)) is AtlasErrorCode.INVALID_DISPLAY_NAME
    change.name = None
    assert await failure(service.update_term(change)) is AtlasErrorCode.BAD_REQUEST
    assert await failure(service.update_term(None)) is AtlasErrorCode.BAD_REQUEST


@pytest.mark.covers(f"{S}.update_term", rules=["GTM-03", "GTM-04"])
async def test__an_update_adds_changes_and_removes_relations(service: GlossaryService, bank: AtlasGlossary) -> None:
    """``testTermRelation``: a related term added, its attributes changed, then removed; never itself or twice."""
    checking = await service.create_term(new_term("checking", bank.guid))
    savings = await service.create_term(new_term("savings", bank.guid))
    checking.see_also = [related(savings.guid, status="DRAFT", description="Related term")]
    checking = await service.update_term(checking)
    assert [(h.term_guid, h.status) for h in checking.see_also or []] == [
        (savings.guid, AtlasTermRelationshipStatus.DRAFT)
    ]
    (checking.see_also or [])[0].description = "changed"
    checking = await service.update_term(checking)
    assert [h.description for h in checking.see_also or []] == ["changed"]
    checking.synonyms = [related(savings.guid)]
    checking = await service.update_term(checking)
    assert [h.term_guid for h in checking.synonyms or []] == [savings.guid]
    checking.see_also = None
    checking.synonyms = [related(savings.guid, relationGuid=(checking.synonyms or [])[0].relation_guid)]
    checking = await service.update_term(checking)
    assert (checking.see_also, [h.term_guid for h in checking.synonyms or []]) == (None, [savings.guid])
    checking.antonyms = [related(checking.guid)]
    assert await failure(service.update_term(checking)) is AtlasErrorCode.INVALID_TERM_RELATION_TO_SELF
    checking.antonyms = [related(savings.guid), related(savings.guid, description="again")]
    assert await failure(service.update_term(checking)) is AtlasErrorCode.GLOSSARY_TERM_ALREADY_EXISTS


@pytest.mark.covers(f"{S}.update_term", rules=["GTM-03", "GTM-04"])
async def test__an_update_changes_and_removes_categorizations(service: GlossaryService, bank: AtlasGlossary) -> None:
    """Categories as related terms: added, their attributes changed, removed."""
    anchor = AtlasGlossaryHeader(glossary_guid=bank.guid)
    first = await service.create_category(AtlasGlossaryCategory(name="first", anchor=anchor))
    second = await service.create_category(AtlasGlossaryCategory(name="second", anchor=anchor))
    term = await service.create_term(new_term("t", bank.guid))
    term.categories = [AtlasTermCategorizationHeader(category_guid=first.guid)]
    term = await service.update_term(term)
    (term.categories or [])[0].description = "now described"
    term.categories = [*(term.categories or []), AtlasTermCategorizationHeader(category_guid=second.guid)]
    term = await service.update_term(term)
    found = {h.category_guid: h.description for h in term.categories or []}
    assert found == {first.guid: "now described", second.guid: None}
    term.categories = [h for h in term.categories or [] if h.category_guid == second.guid]
    term = await service.update_term(term)
    assert [h.category_guid for h in term.categories or []] == [second.guid]
    term.categories = None
    assert (await service.update_term(term)).categories is None


@pytest.mark.covers(
    f"{S}.update_term",
    f"{S}.get_glossary_terms_headers",
    "aurelius_atlas_core.relationship_mapper.RelationshipMapper.map",
    rules=["GTM-04", "GTM-06", "GTM-08"],
)
async def test__a_new_anchor_moves_the_term(service: GlossaryService, bank: AtlasGlossary) -> None:
    """``testTermMigration``: renamed below the new glossary, which lists it; its relations removed."""
    union = await service.create_glossary(AtlasGlossary(name="testCreditUnionGlossary"))
    checking = await service.create_term(new_term("checking", bank.guid))
    savings = await service.create_term(new_term("savings", bank.guid, seeAlso=[related(checking.guid)]))
    savings.anchor = AtlasGlossaryHeader(glossary_guid=union.guid)
    savings.see_also = None
    moved = await service.update_term(savings)
    assert (moved.qualified_name, moved.see_also) == ("savings@testCreditUnionGlossary", None)
    assert moved.anchor is not None
    assert moved.anchor.glossary_guid == union.guid
    headers = await service.get_glossary_terms_headers(union.guid, 0, 5, SortOrder.ASCENDING)
    assert [h.term_guid for h in headers] == [moved.guid]
    assert [h.term_guid for h in await service.get_glossary_terms_headers(bank.guid, 0, 5, SortOrder.ASCENDING)] == [
        checking.guid
    ]
    clash = await service.create_term(new_term("checking", union.guid))
    checking.anchor = AtlasGlossaryHeader(glossary_guid=union.guid)
    assert await failure(service.update_term(checking)) is AtlasErrorCode.GLOSSARY_TERM_ALREADY_EXISTS
    assert clash.qualified_name == "checking@testCreditUnionGlossary"


@pytest.mark.covers(f"{S}.delete_term", f"{S}.delete_glossary", rules=["GTM-05"])
async def test__a_term_is_deleted_with_its_relationships(
    service: GlossaryService, bank: AtlasGlossary, store: EntityStore
) -> None:
    """Its relations and anchor go; a term assigned to an entity stays; a glossary deletes its terms."""
    checking = await service.create_term(new_term("checking", bank.guid))
    savings = await service.create_term(new_term("savings", bank.guid, seeAlso=[related(checking.guid)]))
    await service.delete_term(savings.guid)
    assert (await service.get_term(checking.guid)).see_also is None
    assert [h.term_guid for h in (await service.get_glossary(bank.guid)).terms or []] == [checking.guid]
    asset = AtlasEntity(type_name="Asset", attributes={"qualifiedName": "testAsset", "name": "testAsset"})
    response = await EntityWriter(store).create_or_update(AtlasEntitiesWithExtInfo(entities=[asset]))
    entity_guid = (response.guid_assignments or {})[str(asset.guid)]
    await RelationshipStore(store).create(
        AtlasRelationship(
            type_name="AtlasGlossarySemanticAssignment",
            end1=AtlasObjectId(guid=checking.guid),
            end2=AtlasObjectId(guid=entity_guid),
        )
    )
    assert await failure(service.delete_term(checking.guid)) is AtlasErrorCode.TERM_HAS_ENTITY_ASSOCIATION
    assert await failure(service.delete_glossary(bank.guid)) is AtlasErrorCode.TERM_HAS_ENTITY_ASSOCIATION
    other = await service.create_glossary(AtlasGlossary(name="other"))
    gone = await service.create_term(new_term("gone", other.guid))
    await service.delete_glossary(other.guid)
    assert await failure(service.get_term(gone.guid)) is AtlasErrorCode.INSTANCE_GUID_NOT_FOUND


@pytest.mark.covers(
    f"{S}.get_glossary_terms",
    f"{S}.get_glossary_terms_headers",
    f"{S}.get_detailed_glossary",
    rules=["GTM-06", "GTM-07"],
)
async def test__a_glossarys_terms_are_listed_by_name(service: GlossaryService, bank: AtlasGlossary) -> None:
    """``testGetGlossaryTerms``: by display text, paged; the detailed glossary holds them by GUID."""
    created = [await service.create_term(new_term(name, bank.guid)) for name in ("b", "a", "d", "c")]
    for offset, limit, expected in ((0, -1, 4), (0, 2, 2), (2, 6, 2)):
        assert len(await service.get_glossary_terms_headers(bank.guid, offset, limit, SortOrder.ASCENDING)) == expected
    terms = await service.get_glossary_terms(bank.guid, 1, 2, SortOrder.DESCENDING)
    assert [term.name for term in terms] == ["c", "b"]
    detailed = await service.get_detailed_glossary(bank.guid)
    assert set((detailed.term_info or {}).keys()) == {term.guid for term in created}
