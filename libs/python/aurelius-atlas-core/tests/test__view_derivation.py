"""The shared derivation of the card and the view, from the entity document alone (AVS-02..04, AVS-06, AVS-08, VDR-02).

Every ``view_of`` test hands it a ``StoredEntity`` and an ``EntityType`` and nothing else: no store, no client, no
other entity (AVS-08). Some documents come from the real indexer (the fixture of 14.3) so the derived fields
are the ones a worker writes; the last test derives every indexed document of the sample catalogue, the way
the search door of 16.2 will. The last section hands ``read_ends`` the in-memory store (DD-051): the read door
of 16.5b passes it the entity's own edges, keyed by relationship attribute (VDR-02).
"""

import asyncio
from typing import Any

import pytest
from aurelius_atlas_core.app_search_document import own_document
from aurelius_atlas_core.app_search_engine import AppSearchEngine
from aurelius_atlas_core.entity_store import EntityStore
from aurelius_atlas_core.entity_writer import EntityWriter
from aurelius_atlas_core.relationship_store import RelationshipStore
from aurelius_atlas_core.stored_entity import (
    StoredDimensionTotals,
    StoredEntity,
    StoredQualityTotals,
)
from aurelius_atlas_core.testing.memory import MemoryEntityDocuments
from aurelius_atlas_core.view_derivation import QUALITY_DIMENSIONS, card_of, read_ends, view_of
from aurelius_atlas_model.instance import (
    AtlasEntitiesWithExtInfo,
    AtlasEntity,
    AtlasObjectId,
    AtlasRelationship,
    EntityStatus,
)
from aurelius_atlas_model.typedef import AtlasTypesDef
from aurelius_atlas_typesystem.entity_type import EntityType
from aurelius_atlas_typesystem.registry import TypeRegistry
from test__app_search_engine import indexed_sample
from test__app_search_quality import m4i_types

V = "aurelius_atlas_core.view_derivation"

TYPES = {
    "entityDefs": [
        {
            "name": "asset",
            "attributeDefs": [
                {"name": "qualifiedName", "typeName": "string", "isUnique": True},
                {"name": "name", "typeName": "string", "isOptional": True},
            ],
        },
        {"name": "table", "superTypes": ["asset"], "attributeDefs": []},
    ],
    "businessMetadataDefs": [
        {
            "name": "cost",
            "attributeDefs": [
                {
                    "name": "centre",
                    "typeName": "string",
                    "isOptional": True,
                    "options": {"applicableEntityTypes": '["table"]', "maxStrLength": "20"},
                },
            ],
        },
    ],
}


def registry() -> TypeRegistry:
    """A registry of ``table``, with business metadata ``cost``."""
    types = TypeRegistry()
    with types.update() as transient:
        transient.add_types(AtlasTypesDef.model_validate(TYPES))
    return types


def type_of(registry: TypeRegistry, name: str) -> EntityType:
    """The registered entity type ``name``, required to be one."""
    found = registry.entity_type(name)
    assert found is not None
    return found


def hand(type_name: str, entity_type: EntityType, **values: Any) -> StoredEntity:  # noqa: ANN401
    """A stored entity of ``type_name`` holding ``values``, as the store holds them: by defining qualified name."""
    attributes = {
        defining.qualified_name: value
        for name, value in values.items()
        for defining in [entity_type.attribute(name)]
        if defining is not None
    }
    return StoredEntity(guid="g", type_name=type_name, attributes=attributes)


@pytest.fixture(scope="module")
def m4i() -> TypeRegistry:
    """Atlas's and the data dictionary's models, as 14.3 loads them."""
    return asyncio.run(m4i_types()).registry


@pytest.mark.covers(f"{V}.view_of", rules=["AVS-02", "AVS-03"])
def test__a_stored_document_becomes_crumbs_relations_and_the_business_metadata(m4i: TypeRegistry) -> None:
    """Crumbs zip the stored arrays in their order; each pair becomes a relation in RELATION_FIELDS' order."""
    entity_type = type_of(m4i, "m4i_data_attribute")
    stored = hand(
        "m4i_data_attribute",
        entity_type,
        qualifiedName="a",
        name="A",
        definition="An attribute",
    ).model_copy(
        update={
            "app_search": own_document(hand("m4i_data_attribute", entity_type, qualifiedName="a", name="A")).model_copy(
                update={
                    "breadcrumbguid": ["d", "e"],
                    "breadcrumbname": ["D", "E"],
                    "breadcrumbtype": ["m4i_data_domain", "m4i_data_entity"],
                    "deriveddataentity": ["E"],
                    "deriveddataentityguid": ["e"],
                    "derivedfield": [None],
                    "derivedfieldguid": ["f"],
                },
            ),
        },
    )

    view = view_of(stored, entity_type)

    assert [(crumb.guid, crumb.name, crumb.type_name) for crumb in view.breadcrumb] == [
        ("d", "D", "m4i_data_domain"),
        ("e", "E", "m4i_data_entity"),
    ]
    assert [(r.attribute, [(e.guid, e.name) for e in r.entities]) for r in view.relations] == [
        ("m4i_data_entity", [("e", "E")]),  # the RELATION_FIELDS order, not the stored-field order
        ("m4i_field", [("f", None)]),  # ASU-02's pair: the GUID stays, the name is gone
    ]
    assert (view.name, view.qualified_name, view.display_text, view.definition) == ("A", "a", "A", "An attribute")
    assert view.attributes == {"qualifiedName": "a", "name": "A", "definition": "An attribute"}


@pytest.mark.covers(f"{V}.view_of", rules=["AVS-02"])
def test__an_entity_without_a_document_answers_empty_and_unmarked() -> None:
    """No document: breadcrumb, relations and quality empty; no governed key; not stale (AVS-02)."""
    entity_type = type_of(registry(), "table")
    view = view_of(hand("table", entity_type, qualifiedName="t", name="T"), entity_type)

    assert (view.breadcrumb, view.relations, view.quality) == ([], [], [])
    assert (view.governed, view.stale) == (None, False)
    assert "governed" not in view.to_json()


@pytest.mark.covers(f"{V}.view_of", rules=["AVS-03"])
def test__display_text_falls_back_to_the_qualified_name_then_to_empty_text() -> None:
    """The name when it is there, the qualified name when it is not, empty when neither is (AVS-03)."""
    entity_type = type_of(registry(), "table")

    assert view_of(hand("table", entity_type, qualifiedName="t", name="T"), entity_type).display_text == "T"
    assert view_of(hand("table", entity_type, qualifiedName="t"), entity_type).display_text == "t"
    assert view_of(StoredEntity(guid="g", type_name="table"), entity_type).display_text == ""


@pytest.mark.covers(f"{V}.view_of", rules=["AVS-01"])
def test__the_quality_entries_come_per_dimension_with_their_rules(m4i: TypeRegistry) -> None:
    """One entry per dimension and overall, in order, each with its score, count, total and rule GUIDs (AVS-01)."""
    entity_type = type_of(m4i, "m4i_dataset")
    stored = hand("m4i_dataset", entity_type, qualifiedName="s", name="S").model_copy(
        update={
            "quality_totals": StoredQualityTotals(
                accuracy=StoredDimensionTotals(total=4.0, count=3.0, score=0.75, rules=["rg1"]),
                overall=StoredDimensionTotals(total=4.0, count=3.0, score=0.75, rules=["rg1"]),
            ),
            "governed": True,
        },
    )

    quality = view_of(stored, entity_type).quality

    assert [entry.dimension for entry in quality] == list(QUALITY_DIMENSIONS)
    assert (quality[0].score, quality[0].count, quality[0].total, quality[0].rule_guids) == (0.75, 3.0, 4.0, ["rg1"])
    assert all(entry.rule_guids == [] for entry in quality[1:-1])
    assert view_of(stored, entity_type).governed is True


@pytest.mark.covers(f"{V}.view_of", rules=["AVS-06"])
def test__a_stale_document_marks_the_view_and_the_entity_time_carries_it(m4i: TypeRegistry) -> None:
    """Stale is the document's flag, updateTime the entity's, and nothing else is claimed (AVS-06)."""
    entity_type = type_of(m4i, "m4i_dataset")
    bare = hand("m4i_dataset", entity_type, qualifiedName="s")
    stored = hand("m4i_dataset", entity_type, qualifiedName="s", name="S").model_copy(
        update={"update_time": 123, "app_search": own_document(bare).model_copy(update={"stale": True})},
    )

    view = view_of(stored, entity_type)

    assert (view.stale, view.to_json()["updateTime"]) == (True, 123)


@pytest.mark.covers(f"{V}.view_of", rules=["AVS-04"])
def test__sections_merge_the_read_ends_with_the_stored_pairs_each_end_once(m4i: TypeRegistry) -> None:
    """A stored pair keeps the document's name; a read end adds type and state and wins its place (AVS-04)."""
    entity_type = type_of(m4i, "m4i_data_entity")
    stored = hand("m4i_data_entity", entity_type, qualifiedName="e", name="E").model_copy(
        update={
            "app_search": own_document(hand("m4i_data_entity", entity_type, qualifiedName="e", name="E")).model_copy(
                update={
                    "deriveddatadomain": ["D-stale"],
                    "deriveddatadomainguid": ["d"],
                    "deriveddataset": ["S"],
                    "deriveddatasetguid": ["s"],
                },
            ),
        },
    )

    read_end = StoredEntity(
        guid="d",
        type_name="m4i_data_domain",
        attributes={"m4i_data_domain.name": "D"},
        state=EntityStatus.DELETED,
    )
    view = view_of(stored, entity_type, ends={"m4i_data_domain": [read_end]})

    entries = [(r.attribute, [(e.guid, e.name, e.type_name, e.status) for e in r.entities]) for r in view.sections]
    # the read end wins the pair's place; the pair stays as the document named it
    assert entries == [
        ("m4i_data_domain", [("d", "D", "m4i_data_domain", EntityStatus.DELETED)]),
        ("m4i_dataset", [("s", "S", None, None)]),
    ]


@pytest.mark.covers(f"{V}.view_of", rules=["AVS-04"])
def test__attributes_hold_the_own_values_and_business_metadata_the_bm_values() -> None:
    """Business attributes are not repeated in ``attributes``; their values answer under their metadata (AVS-04)."""
    entity_type = type_of(registry(), "table")
    stored = hand("table", entity_type, qualifiedName="t", name="T").model_copy(
        update={"attributes": {"asset.qualifiedName": "t", "asset.name": "T", "cost.centre": "C", "gone.attribute": 1}},
    )

    view = view_of(stored, entity_type)

    assert view.attributes == {"qualifiedName": "t", "name": "T"}
    assert view.business_metadata == {"cost": {"centre": "C"}}  # the type no longer has "gone.attribute" (DD-043)


@pytest.mark.covers(f"{V}.view_of", rules=["AVS-01"])
def test__classification_names_read_the_attached_names_only(m4i: TypeRegistry) -> None:
    """The stored attached names answer; propagated ones, which belong to their source, do not (DD-326)."""
    entity_type = type_of(m4i, "m4i_dataset")
    stored = hand("m4i_dataset", entity_type, qualifiedName="s", name="S").model_copy(
        update={"search": {"keyword.__traitNames": ["PII"], "keyword.__propagatedTraitNames": ["Sensitive"]}},
    )

    assert view_of(stored, entity_type).classification_names == ["PII"]


@pytest.mark.covers(f"{V}.card_of", rules=["AVS-04", "AVS-08"])
async def test__every_indexed_sample_document_derives_a_card_from_its_document_alone() -> None:
    """The sample catalogue, derived the way 16.2's search door will: each hit's own document, no other read."""
    documents = await indexed_sample()
    engine = AppSearchEngine(documents)
    answer = await engine.search({"query": "", "size": 500, "result_fields": {"guid": {"raw": {}}}})
    guids = [hit["guid"]["raw"] for hit in answer["results"]]
    found = await documents.get(guids)
    registry_ = await m4i_types()

    cards = []
    for guid in sorted(guids):
        stored = found[guid].entity
        if stored.app_search is None:
            continue
        cards.append(card_of(view_of(stored, type_of(registry_.registry, stored.type_name))))  # no ends: AVS-08

    assert len(cards) > 5
    assert all(card.display_text for card in cards)  # every indexed document names itself (LAS-02)
    for card in cards:
        stored = found[card.guid].entity
        assert stored.app_search is not None
        assert [crumb.guid for crumb in card.breadcrumb] == list(stored.app_search.breadcrumbguid)
        assert card.stale == stored.app_search.stale


async def ends_store(m4i: TypeRegistry) -> EntityStore:
    """A store of the data dictionary's types holding entity ``e``, domain ``d`` and person ``p``.

    ``d`` owns ``e`` and ``p`` owns ``e`` as its business owner, so ``e`` answers two attributes and a
    type with no edges of its own answers none.
    """
    store = EntityStore(m4i, MemoryEntityDocuments())
    await EntityWriter(store, user="u").create_or_update(
        AtlasEntitiesWithExtInfo(
            entities=[
                AtlasEntity(type_name="m4i_data_entity", attributes={"qualifiedName": "e", "name": "E"}),
                AtlasEntity(type_name="m4i_data_domain", attributes={"qualifiedName": "d", "name": "D"}),
                AtlasEntity(type_name="m4i_person", attributes={"qualifiedName": "p", "name": "P"}),
            ],
        )
    )
    return store


async def guid_of(store: EntityStore, type_name: str, qualified_name: str) -> str:
    """The GUID of the stored entity of ``type_name`` with that ``qualifiedName``."""
    entity_type = store.registry.entity_type(type_name)
    assert entity_type is not None
    found = await store.find_by_unique_attributes(entity_type, {"qualifiedName": qualified_name})
    assert found is not None
    return found.entity.guid


async def connect(store: EntityStore, type_name: str, end1: AtlasObjectId, end2: AtlasObjectId) -> str:
    """The relationship ``end1``-``end2`` of ``type_name``, created through the store; its GUID back."""
    created = await RelationshipStore(store, user="u").create(
        AtlasRelationship(type_name=type_name, end1=end1, end2=end2)
    )
    assert created.guid is not None
    return created.guid


@pytest.mark.covers(f"{V}.read_ends", rules=["VDR-02"])
async def test__read_ends_answer_the_active_edges_keyed_by_relationship_attribute(m4i: TypeRegistry) -> None:
    """Each ACTIVE edge answers under its own attribute, with its end's name, type and state (VDR-02, DD-604)."""
    store = await ends_store(m4i)
    e, d, p = (
        await guid_of(store, "m4i_data_entity", "e"),
        await guid_of(store, "m4i_data_domain", "d"),
        await guid_of(store, "m4i_person", "p"),
    )
    await connect(
        store,
        "m4i_data_entity_assignment",
        AtlasObjectId(guid=d, type_name="m4i_data_domain"),
        AtlasObjectId(guid=e, type_name="m4i_data_entity"),
    )
    await connect(
        store,
        "m4i_data_entity_business_owner_assignment",
        AtlasObjectId(guid=p, type_name="m4i_person"),
        AtlasObjectId(guid=e, type_name="m4i_data_entity"),
    )
    found = await store.get(e)
    assert found is not None

    ends = await read_ends(store, found.entity, type_of(m4i, "m4i_data_entity"))

    assert {name: [(end.guid, end.type_name) for end in listed] for name, listed in ends.items()} == {
        "dataDomain": [(d, "m4i_data_domain")],  # the end's own attribute name, not the type field
        "businessOwner": [(p, "m4i_person")],
    }


@pytest.mark.covers(f"{V}.read_ends", rules=["VDR-02"])
async def test__read_ends_answer_nothing_for_a_deleted_edge_or_an_entity_without_edges(m4i: TypeRegistry) -> None:
    """A soft-deleted edge answers nothing (DD-604); an entity listing no relationships needs no read."""
    store = await ends_store(m4i)
    e, d = (
        await guid_of(store, "m4i_data_entity", "e"),
        await guid_of(store, "m4i_data_domain", "d"),
    )
    relationship = await connect(
        store,
        "m4i_data_entity_assignment",
        AtlasObjectId(guid=d, type_name="m4i_data_domain"),
        AtlasObjectId(guid=e, type_name="m4i_data_entity"),
    )
    await RelationshipStore(store, user="u").delete_by_id(relationship)
    found = await store.get(e)
    assert found is not None

    assert await read_ends(store, found.entity, type_of(m4i, "m4i_data_entity")) == {}
    domain = await store.get(d)
    assert domain is not None
    assert await read_ends(store, domain.entity, type_of(m4i, "m4i_data_domain")) == {}


@pytest.mark.covers(f"{V}.read_ends", rules=["VDR-02"])
async def test__the_view_sections_answer_the_read_ends_with_type_and_state(m4i: TypeRegistry) -> None:
    """The door's shape: ends through ``view_of`` answer ``sections`` keyed by attribute, each end once."""
    store = await ends_store(m4i)
    e, d, p = (
        await guid_of(store, "m4i_data_entity", "e"),
        await guid_of(store, "m4i_data_domain", "d"),
        await guid_of(store, "m4i_person", "p"),
    )
    await connect(
        store,
        "m4i_data_entity_assignment",
        AtlasObjectId(guid=d, type_name="m4i_data_domain"),
        AtlasObjectId(guid=e, type_name="m4i_data_entity"),
    )
    found = await store.get(e)
    assert found is not None
    entity_type = type_of(m4i, "m4i_data_entity")

    view = view_of(found.entity, entity_type, ends=await read_ends(store, found.entity, entity_type))

    entries = [(r.attribute, [(x.guid, x.name, x.type_name, x.status) for x in r.entities]) for r in view.sections]
    assert entries == [("dataDomain", [(d, "D", "m4i_data_domain", EntityStatus.ACTIVE)])]
    assert [r.attribute for r in view.relations] == []  # no document yet: the pairs wait for the worker (AVS-08)
    assert p not in "".join(str(entry) for entry in entries)  # the unconnected person answers nothing


@pytest.mark.covers(f"{V}.read_ends", rules=["VDR-02"])
async def test__one_end_under_two_read_attributes_answers_under_both(m4i: TypeRegistry) -> None:
    """The process that both feeds and comes out of a dataset answers Producers and Consumers alike (REL-17).

    The read door must not answer one box by emptying the other: a read end is dropped only from the
    document's stored pairs (VDR-02, DD-604), never from another section the read itself filled.
    """
    store = EntityStore(m4i, MemoryEntityDocuments())
    await EntityWriter(store, user="u").create_or_update(
        AtlasEntitiesWithExtInfo(
            entities=[
                AtlasEntity(type_name="m4i_dataset", attributes={"qualifiedName": "s", "name": "S"}),
                AtlasEntity(type_name="m4i_generic_process", attributes={"qualifiedName": "x", "name": "X"}),
            ],
        )
    )
    s, x = await guid_of(store, "m4i_dataset", "s"), await guid_of(store, "m4i_generic_process", "x")
    await connect(
        store,
        "dataset_process_inputs",
        AtlasObjectId(guid=x, type_name="m4i_generic_process"),
        AtlasObjectId(guid=s, type_name="m4i_dataset"),
    )
    await connect(
        store,
        "process_dataset_outputs",
        AtlasObjectId(guid=x, type_name="m4i_generic_process"),
        AtlasObjectId(guid=s, type_name="m4i_dataset"),
    )
    found = await store.get(s)
    assert found is not None
    entity_type = type_of(m4i, "m4i_dataset")

    view = view_of(found.entity, entity_type, ends=await read_ends(store, found.entity, entity_type))

    entries = {r.attribute: [e.guid for e in r.entities] for r in view.sections}
    assert entries == {"inputToProcesses": [x], "outputFromProcesses": [x]}  # the one process answers both boxes
