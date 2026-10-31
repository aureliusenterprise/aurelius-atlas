"""Terms assigned to entities (GTA-01 to GTA-07) on the in-memory documents.

Read from ``GlossaryService``, ``GlossaryTermUtils``, ``EntityGraphRetriever#mapAssignedTerms``,
``EntityAuditListenerV2``, ``SearchContext``, ``TermSearchProcessor`` and ``GremlinQueryComposer#addHasTerm`` of
Apache Atlas 2.4.0, with ``GlossaryServiceTest``'s ``testTermAssignmentAndDissociation``.
"""

import json

import pytest
from aurelius_atlas_core.discovery_service import EntityDiscoveryService
from aurelius_atlas_core.entity_audit_listener import EntityAuditListener, term_audit_string
from aurelius_atlas_core.entity_change_notifier import EntityChangeNotifier
from aurelius_atlas_core.entity_classifications import EntityClassifications
from aurelius_atlas_core.entity_retriever import EntityRetriever
from aurelius_atlas_core.entity_store import EntityStore
from aurelius_atlas_core.entity_writer import EntityWriter
from aurelius_atlas_core.glossary_service import GlossaryService, SortOrder
from aurelius_atlas_core.model_loader import BUILTIN_MODELS_DIR
from aurelius_atlas_core.relationship_store import RelationshipStore
from aurelius_atlas_core.testing.memory import InMemoryEntityAuditRepository, MemoryEntityDocuments
from aurelius_atlas_model.audit import EntityAuditActionV2
from aurelius_atlas_model.discovery import SearchParameters
from aurelius_atlas_model.errors import AtlasError, AtlasErrorCode
from aurelius_atlas_model.glossary import AtlasGlossary, AtlasGlossaryHeader, AtlasGlossaryTerm
from aurelius_atlas_model.instance import (
    AtlasClassification,
    AtlasEntitiesWithExtInfo,
    AtlasEntity,
    AtlasRelatedObjectId,
    AtlasStruct,
    AtlasTermAssignmentStatus,
)
from aurelius_atlas_model.typedef import AtlasClassificationDef, AtlasTypesDef
from aurelius_atlas_typesystem.registry import TypeRegistry

S = "aurelius_atlas_core.glossary_service.GlossaryService"
T = "aurelius_atlas_core.glossary_term_utils.GlossaryTermUtils"
P = "aurelius_atlas_core.term_search_processor"
N = "aurelius_atlas_core.entity_change_notifier.EntityChangeNotifier"
A = "aurelius_atlas_core.entity_audit_listener"
MODELS = BUILTIN_MODELS_DIR / "0000-Area0"


@pytest.fixture
def store() -> EntityStore:
    """A store with the base and glossary models and a classification ``PII``."""
    registry = TypeRegistry()
    with registry.update() as transient:
        for name in ("0010-base_model.json", "0011-glossary_model.json"):
            transient.add_types(AtlasTypesDef.model_validate(json.loads((MODELS / name).read_text(encoding="utf-8"))))
        transient.add_types(AtlasTypesDef(classification_defs=[AtlasClassificationDef(name="PII")]))
    return EntityStore(registry, MemoryEntityDocuments())


@pytest.fixture
def audits() -> InMemoryEntityAuditRepository:
    """The audit events the service's notifier records."""
    return InMemoryEntityAuditRepository()


@pytest.fixture
def service(store: EntityStore, audits: InMemoryEntityAuditRepository) -> GlossaryService:
    """A service whose term changes are audited."""
    notifier = EntityChangeNotifier(store, [EntityAuditListener(audits, store.now)])
    return GlossaryService(store, user="admin", notifier=notifier)


async def term(
    service: GlossaryService, name: str = "Conventional mortgage", glossary: str = "bank"
) -> AtlasGlossaryTerm:
    """A term of a glossary of that name, created with it when there is none."""
    found = await service.get_glossaries(-1, 0, SortOrder.ASCENDING)
    anchor = next((g for g in found if g.name == glossary), None) or await service.create_glossary(
        AtlasGlossary(name=glossary)
    )
    return await service.create_term(
        AtlasGlossaryTerm(name=name, anchor=AtlasGlossaryHeader(glossary_guid=anchor.guid))
    )


async def asset(store: EntityStore, name: str) -> str:
    """The GUID of a new ``Asset``."""
    entity = AtlasEntity(type_name="Asset", attributes={"qualifiedName": name, "name": name})
    response = await EntityWriter(store).create_or_update(AtlasEntitiesWithExtInfo(entities=[entity]))
    return (response.guid_assignments or {})[str(entity.guid)]


def related(guid: str, **attributes: object) -> AtlasRelatedObjectId:
    """An entity to assign, with the assignment's attributes."""
    found = AtlasRelatedObjectId(guid=guid, type_name="Asset")
    if attributes:
        found.relationship_attributes = AtlasStruct(attributes=attributes)
    return found


async def failure(awaitable: object) -> AtlasErrorCode:
    """The code of the error the awaitable raises."""
    with pytest.raises(AtlasError) as raised:
        await awaitable  # type: ignore[misc]
    return raised.value.code


@pytest.mark.covers(
    f"{S}.assign_term_to_entities",
    f"{S}.get_assigned_entities",
    f"{T}.process_term_assignments",
    rules=["GTA-01", "GTA-02"],
)
async def test__a_term_is_assigned_to_entities(service: GlossaryService, store: EntityStore) -> None:
    """``testTermAssignmentAndDissociation``: the term lists the entities, by display text, paged; once each.

    An entity there is not fails as a relationship to no end (DV-102).
    """
    fixed = await term(service)
    b, a = await asset(store, "b"), await asset(store, "a")
    await service.assign_term_to_entities(fixed.guid, [related(b, description="d", confidence=80), related(a)])
    await service.assign_term_to_entities(fixed.guid, [related(a)])
    listed = await service.get_assigned_entities(fixed.guid, 0, -1, SortOrder.ASCENDING)
    assert [(found.guid, found.display_text) for found in listed] == [(a, "a"), (b, "b")]
    assert [found.guid for found in await service.get_assigned_entities(fixed.guid, 0, 1, SortOrder.DESCENDING)] == [b]
    attributes = listed[1].relationship_attributes
    assert attributes is not None
    assert (attributes.get_attribute("description"), attributes.get_attribute("confidence")) == ("d", 80)
    assert await failure(service.assign_term_to_entities(fixed.guid, [related("nope")])) is (
        AtlasErrorCode.RELATIONSHIP_END_IS_NULL
    )
    assert await failure(service.delete_term(fixed.guid)) is AtlasErrorCode.TERM_HAS_ENTITY_ASSOCIATION


@pytest.mark.covers(f"{S}.remove_term_from_entities", f"{T}.process_term_dissociation", rules=["GTA-03"])
async def test__an_assignment_is_removed_by_its_relationship(service: GlossaryService, store: EntityStore) -> None:
    """The assignment's GUID is needed and must be the term's to the entity (DV-102); it is removed for good."""
    fixed = await term(service)
    entity = await asset(store, "a")
    await service.assign_term_to_entities(fixed.guid, [related(entity)])
    (assigned,) = await service.get_assigned_entities(fixed.guid, 0, -1, SortOrder.ASCENDING)
    no_guid = service.remove_term_from_entities(fixed.guid, [related(entity)])
    assert await failure(no_guid) is AtlasErrorCode.TERM_DISSOCIATION_MISSING_RELATION_GUID
    wrong = related(entity)
    wrong.relationship_guid = "other"
    assert (
        await failure(service.remove_term_from_entities(fixed.guid, [wrong]))
        is AtlasErrorCode.INVALID_TERM_DISSOCIATION
    )
    stranger = related(await asset(store, "b"))
    stranger.relationship_guid = assigned.relationship_guid
    assert await failure(service.remove_term_from_entities(fixed.guid, [stranger])) is (
        AtlasErrorCode.INVALID_TERM_DISSOCIATION
    )
    await service.remove_term_from_entities(fixed.guid, [assigned])
    assert await service.get_assigned_entities(fixed.guid, 0, -1, SortOrder.ASCENDING) == []
    assert await failure(RelationshipStore(store).get_by_id(str(assigned.relationship_guid))) is (
        AtlasErrorCode.RELATIONSHIP_GUID_NOT_FOUND
    )
    await service.delete_term(fixed.guid)


@pytest.mark.covers(
    f"{N}.on_term_added_to_entities",
    f"{N}.on_term_deleted_from_entities",
    f"{A}.EntityAuditListener.on_term_added",
    f"{A}.EntityAuditListener.on_term_deleted",
    f"{A}.term_audit_string",
    rules=["GTA-04"],
)
async def test__assignments_are_audited_on_the_entities(
    service: GlossaryService, store: EntityStore, audits: InMemoryEntityAuditRepository
) -> None:
    """``onTermAdded``, ``onTermDeleted``: ``TERM_ADD``, ``TERM_DELETE`` with the term's GUID and names."""
    fixed = await term(service)
    entity = await asset(store, "a")
    await service.assign_term_to_entities(fixed.guid, [related(entity)])
    (assigned,) = await service.get_assigned_entities(fixed.guid, 0, -1, SortOrder.ASCENDING)
    await service.remove_term_from_entities(fixed.guid, [assigned])
    audit = term_audit_string(fixed)
    assert audit == (
        f'{{"guid":"{fixed.guid}","qualifiedName":"Conventional mortgage@bank","name":"Conventional mortgage"}}'
    )
    found = [(event.entity_id, event.action, event.details, event.user) for event in audits.events]
    assert found == [
        (entity, EntityAuditActionV2.TERM_ADD, f"Added term: {audit}", "admin"),
        (entity, EntityAuditActionV2.TERM_DELETE, f"Deleted term: {audit}", "admin"),
    ]


@pytest.mark.covers(
    "aurelius_atlas_core.entity_retriever._Reading.meanings",
    f"{S}.assign_term_to_entities",
    rules=["GTA-02", "GTA-05"],
)
async def test__an_entitys_header_lists_its_meanings(service: GlossaryService, store: EntityStore) -> None:
    """``mapAssignedTerms``: each assignment's term and attributes; a status of another enum left out (DV-103)."""
    fixed, arm = await term(service), await term(service, "ARM loans")
    entity = await asset(store, "a")
    await service.assign_term_to_entities(
        fixed.guid, [related(entity, description="d", status="DEPRECATED", confidence=9, steward="s")]
    )
    await service.assign_term_to_entities(arm.guid, [related(entity, status="ACTIVE")])
    header = await EntityRetriever(store).header(entity)
    assert header.meaning_names == ["Conventional mortgage", "ARM loans"]
    first, second = header.meanings or []
    assert (first.term_guid, first.qualified_name, first.description, first.status, first.confidence) == (
        fixed.guid,
        "Conventional mortgage@bank",
        "d",
        AtlasTermAssignmentStatus.DEPRECATED,
        9,
    )
    assert (first.steward, first.relation_guid is not None, second.status) == ("s", True, None)
    await EntityWriter(store).delete_by_id(entity)
    assert (await EntityRetriever(store).header(entity)).meaning_names == ["Conventional mortgage", "ARM loans"]


@pytest.mark.covers(f"{S}.assign_term_to_entities", rules=["GTA-02"])
async def test__a_terms_classifications_propagate_to_its_entities(service: GlossaryService, store: EntityStore) -> None:
    """The semantic assignment propagates ``ONE_TO_TWO``: from the term to the entity."""
    fixed = await term(service)
    await EntityClassifications(store).add_classifications(fixed.guid, [AtlasClassification(type_name="PII")])
    entity = await asset(store, "a")
    await service.assign_term_to_entities(fixed.guid, [related(entity)])
    found = await EntityRetriever(store).classifications(entity)
    assert [(c.type_name, c.entity_guid) for c in found] == [("PII", fixed.guid)]


@pytest.mark.covers(f"{P}.term_criterion", f"{P}.assigned_entity_guids", f"{P}.guids_criterion", rules=["GTA-06"])
async def test__a_basic_search_finds_a_terms_entities(service: GlossaryService, store: EntityStore) -> None:
    """``termName``: the active term of the qualified name; with a type, both; deleted ones as asked."""
    fixed = await term(service)
    await term(service, "unused")
    a, b, c = await asset(store, "a"), await asset(store, "b"), await asset(store, "c")
    await service.assign_term_to_entities(fixed.guid, [related(a), related(b)])
    await EntityWriter(store).delete_by_id(b)
    discovery = EntityDiscoveryService(store)

    async def names(**fields: object) -> list[str]:
        parameters = SearchParameters.model_validate({"limit": 10, **fields})
        found = (await discovery.search_with_parameters(parameters)).entities or []
        return sorted(str(header.display_text) for header in found)

    assert await names(termName="Conventional mortgage@bank") == ["a", "b"]
    assert await names(termName="Conventional mortgage@bank", excludeDeletedEntities=True) == ["a"]
    assert await names(termName="Conventional mortgage@bank", typeName="DataSet") == []
    assert await names(termName="unused@bank") == []
    with pytest.raises(AtlasError) as unknown:
        await names(termName="Conventional mortgage")
    assert (unknown.value.code, unknown.value.message) == (
        AtlasErrorCode.UNKNOWN_GLOSSARY_TERM,
        "Conventional mortgage: Unknown/invalid glossary term",
    )
    assert c not in {a, b}


@pytest.mark.covers(
    f"{P}.has_term_guids",
    "aurelius_atlas_core.dsl_query_composer._has_term",
    rules=["GTA-07"],
)
async def test__a_dsl_query_finds_entities_with_a_term(service: GlossaryService, store: EntityStore) -> None:
    """``hasTerm``: by name, or by qualified name when it holds ``@``; quoted or not; in a where clause too."""
    fixed = await term(service)
    a = await asset(store, "a")
    await asset(store, "b")
    await service.assign_term_to_entities(fixed.guid, [related(a)])
    discovery = EntityDiscoveryService(store)

    async def names(query: str) -> list[str]:
        found = (await discovery.search_using_dsl_query(query, 10, 0)).entities or []
        return [str(header.display_text) for header in found]

    assert await names('Asset hasTerm "Conventional mortgage"') == ["a"]
    assert await names('Asset hasTerm "Conventional mortgage@bank"') == ["a"]
    assert await names("Asset where name = 'a' and Asset hasTerm \"Conventional mortgage\"") == ["a"]
    assert await names('Asset hasTerm "Conventional mortgage@other"') == []
    assert await names("Asset hasTerm nothing") == []
