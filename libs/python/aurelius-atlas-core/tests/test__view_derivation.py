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
from aurelius_atlas_core.app_search_answer import AppSearchEngine
from aurelius_atlas_core.app_search_document import own_document
from aurelius_atlas_core.entity_classifications import EntityClassifications
from aurelius_atlas_core.entity_store import EntityStore
from aurelius_atlas_core.entity_writer import EntityWriter
from aurelius_atlas_core.relationship_store import RelationshipStore
from aurelius_atlas_core.stored_entity import (
    StoredDimensionTotals,
    StoredEntity,
    StoredQualityTotals,
)
from aurelius_atlas_core.testing.entity_samples import sample_registry
from aurelius_atlas_core.testing.memory import MemoryEntityDocuments
from aurelius_atlas_core.view_derivation import (
    QUALITY_DIMENSIONS,
    card_of,
    read_ends,
    read_propagations,
    view_of,
)
from aurelius_atlas_model.instance import (
    AtlasClassification,
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
        description="An attribute",
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
    assert view.attributes == {"qualifiedName": "a", "name": "A", "description": "An attribute"}


@pytest.mark.covers(f"{V}.view_of", rules=["AVS-10"])
def test__the_role_pairs_follow_the_type_keyed_relations_and_leave_the_sections_alone(m4i: TypeRegistry) -> None:
    """The card's relations answer the stored role pairs after the type-keyed ones, each keyed by its
    relationship attribute; the sections stay what they were, as the role pairs ride the card only (AVS-10).
    """  # noqa: D205 - one sentence
    entity_type = type_of(m4i, "m4i_data_entity")
    stored = hand("m4i_data_entity", entity_type, qualifiedName="e", name="E").model_copy(
        update={
            "app_search": own_document(hand("m4i_data_entity", entity_type, qualifiedName="e", name="E")).model_copy(
                update={
                    "deriveddatadomain": ["D"],
                    "deriveddatadomainguid": ["d"],
                    "deriveddataowner": ["Alice"],
                    "deriveddataownerguid": ["alice"],
                    "deriveddatasteward": ["Bob", "Alice"],
                    "deriveddatastewardguid": ["bob", "alice"],
                },
            ),
        },
    )

    view = view_of(stored, entity_type)

    assert [(r.attribute, [(e.guid, e.name) for e in r.entities]) for r in view.relations] == [
        ("m4i_data_domain", [("d", "D")]),  # the type-keyed pairs first (AVS-02)
        ("businessOwner", [("alice", "Alice")]),  # then the role pairs, in ROLE_FIELDS' order (ASD-06)
        ("steward", [("bob", "Bob"), ("alice", "Alice")]),
    ]
    # the sections never saw the role pairs: the People box reads the read ends, not these (VCF-17)
    assert [(r.attribute, [e.guid for e in r.entities]) for r in view.sections] == [("m4i_data_domain", ["d"])]


@pytest.mark.covers(f"{V}._card_definition", rules=["AVS-03", "DD-614", "SPA-05"])
def test__the_card_definition_is_the_description_attribute(m4i: TypeRegistry) -> None:
    """The card's definition field carries the one prose attribute, and none when it is absent (AVS-03, DD-833)."""
    entity_type = type_of(m4i, "m4i_dataset")

    described = hand("m4i_dataset", entity_type, qualifiedName="s", description="Described")

    assert view_of(described, entity_type).definition == "Described"
    assert view_of(hand("m4i_dataset", entity_type, qualifiedName="s"), entity_type).definition is None
    # the card field is a copy: the view's attributes are the stored ones (AVS-01)
    assert view_of(described, entity_type).attributes == {"qualifiedName": "s", "description": "Described"}


@pytest.mark.covers(f"{V}.view_of", rules=["MMS-09"])
def test__the_card_carries_the_type_alias_whenever_it_holds_one(m4i: TypeRegistry) -> None:
    """attributes.typeAlias rides the card as typeAlias; empty or absent answers none (MMS-09, DD-721)."""
    entity_type = type_of(m4i, "m4i_dataset")

    aliased = hand("m4i_dataset", entity_type, qualifiedName="s", typeAlias="Data Set")
    assert view_of(aliased, entity_type).type_alias == "Data Set"
    assert view_of(aliased, entity_type).to_json()["typeAlias"] == "Data Set"

    blank = hand("m4i_dataset", entity_type, qualifiedName="s", typeAlias="")
    assert view_of(blank, entity_type).type_alias is None
    assert "typeAlias" not in view_of(blank, entity_type).to_json()
    assert view_of(hand("m4i_dataset", entity_type, qualifiedName="s"), entity_type).type_alias is None


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


@pytest.mark.covers(f"{V}.view_of", rules=["VDR-05"])
def test__a_view_holds_its_propagated_classifications_with_their_sources() -> None:
    """The door's read answers one entry per propagated name, with each source named (VDR-05).

    Two sources of one name answer one entry with both, as the legacy header counted them (DD-834); an entity
    the door read nothing about answers the field empty (DD-835).
    """
    entity_type = type_of(registry(), "table")
    stored = hand("table", entity_type, qualifiedName="t", name="T")
    sources = [
        StoredEntity(guid="a", type_name="table", attributes={"asset.name": "A"}, state=EntityStatus.ACTIVE),
        StoredEntity(guid="b", type_name="table", attributes={"asset.qualifiedName": "b"}),
    ]

    view = view_of(stored, entity_type, propagated=[("c_pii", [sources[0]]), ("c_pii", [sources[1]])])

    assert [
        (c.type_name, [(e.guid, e.name, e.type_name) for e in c.entities]) for c in view.propagated_classifications
    ] == [
        ("c_pii", [("a", "A", "table"), ("b", None, "table")])  # b has no name attribute (ASU-02)
    ]
    assert view.classification_names == []  # a propagated name never joins the entity's own (AVS-01)
    assert view_of(stored, entity_type).propagated_classifications == []
    nameless = view_of(stored, entity_type, propagated=[("c_pii", [])])
    assert [(c.type_name, c.entities) for c in nameless.propagated_classifications] == [("c_pii", [])]
    assert card_of(view).model_dump(include={"propagated_classifications"}) == {}  # a card has no such field


async def _propagation_store() -> tuple[EntityStore, dict[str, str]]:
    """A store of the sample types holding ``a -> p1 -> b``, with ``c_pii`` attached to ``a``.

    The tag propagates downstream through ``p_input``/``p_output`` (PRO-01), so ``b`` carries it from ``a``.
    """
    store = EntityStore(sample_registry(classifications=True), MemoryEntityDocuments())
    created = await EntityWriter(store).create_or_update(
        AtlasEntitiesWithExtInfo.model_validate(
            {
                "entities": [
                    {"typeName": "p_data", "guid": "-a", "attributes": {"qualifiedName": "a", "name": "A"}},
                    {"typeName": "p_data", "guid": "-b", "attributes": {"qualifiedName": "b", "name": "B"}},
                    {
                        "typeName": "p_process",
                        "guid": "-p1",
                        "attributes": {"qualifiedName": "p1"},
                        "relationshipAttributes": {"inputs": [{"guid": "-a"}], "outputs": [{"guid": "-b"}]},
                    },
                ]
            }
        )
    )
    guids = {key.removeprefix("-"): value for key, value in (created.guid_assignments or {}).items()}
    await EntityClassifications(store).add_classifications(
        guids["a"], [AtlasClassification.model_validate({"typeName": "c_pii", "attributes": {"level": 5}})]
    )
    return store, guids


@pytest.mark.covers(f"{V}.read_propagations", rules=["VDR-05"])
async def test__read_propagations_answer_the_tag_and_the_entity_it_came_from() -> None:
    """The propagated name and its source answer for the downstream entity; its own tag answers nothing (VDR-05)."""
    store, guids = await _propagation_store()
    b = await store.get(guids["b"])
    assert b is not None

    assert await read_propagations(store, b.entity) == [("c_pii", [await _source(store, guids["a"])])]

    a = await store.get(guids["a"])
    assert a is not None
    assert await read_propagations(store, a.entity) == []  # the tag attached here is a's own (AVS-01)


@pytest.mark.covers(f"{V}.read_propagations", rules=["VDR-05"])
async def test__read_propagations_answer_nothing_once_the_sources_tag_is_gone() -> None:
    """Deleting the tag on its source takes the propagated one with it, so the view answers no name (VDR-05, PRO-04)."""
    store, guids = await _propagation_store()
    await EntityClassifications(store).delete_classification(guids["a"], "c_pii")
    b = await store.get(guids["b"])
    assert b is not None

    assert await read_propagations(store, b.entity) == []


async def _source(store: EntityStore, guid: str) -> StoredEntity:
    """The stored entity ``guid``, for comparing a source the door read."""
    found = await store.get(guid)
    assert found is not None
    return found.entity
