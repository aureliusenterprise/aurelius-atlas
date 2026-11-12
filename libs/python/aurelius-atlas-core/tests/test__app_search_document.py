"""An App Search document's own fields, the hash a write checks, the stale mark, what it names, its mapping and
the listings (LAS-01 to LAS-03, ASD-01 to ASD-04, ASU-01 to ASU-04), without a catalogue.
"""  # noqa: D205 - one sentence

import pytest
from aurelius_atlas_core.app_search_document import (
    app_search_mapping,
    attribute_value,
    has_document,
    identity,
    named_guids,
    own_document,
    source_hash,
    source_type,
    with_current_app_search,
)
from aurelius_atlas_core.entity_documents import ElasticsearchEntityDocuments, LinkedKind, LinkedWrite
from aurelius_atlas_core.stored_entity import StoredAppSearch, StoredEntity
from aurelius_atlas_core.stored_relationship import StoredRelationship
from aurelius_atlas_core.testing.memory import MemoryEntityDocuments
from aurelius_atlas_model.instance import EntityStatus, RelationshipStatus
from aurelius_atlas_store_es.testing.fake import FakeClient

A = "aurelius_atlas_core.app_search_document"
D = "aurelius_atlas_core.entity_documents.ElasticsearchEntityDocuments"
M = "aurelius_atlas_core.testing.memory.MemoryEntityDocuments"


def entity(guid: str = "g", type_name: str = "m4i_data_entity", **attributes: object) -> StoredEntity:
    """An entity of ``type_name`` with ``attributes`` under their qualified names."""
    return StoredEntity(guid=guid, type_name=type_name, attributes=dict(attributes))


def indexed(stored: StoredEntity, **fields: object) -> StoredEntity:
    """``stored`` with the document of its own fields, and ``fields`` of the derived ones."""
    return stored.model_copy(update={"app_search": own_document(stored).model_copy(update=fields)})


def relationship(guid: str, state: RelationshipStatus, seen: RelationshipStatus | None) -> StoredRelationship:
    """A relationship in ``state`` whose ends' documents saw ``seen``."""
    return StoredRelationship(
        guid=guid, type_name="t", end1_guid="a", end2_guid="b", state=state, app_search_state=seen
    )


RELATIONSHIPS = [
    relationship("active", RelationshipStatus.ACTIVE, None),
    relationship("deleted", RelationshipStatus.DELETED, None),
    relationship("seen", RelationshipStatus.DELETED, RelationshipStatus.DELETED),
    relationship("restored", RelationshipStatus.ACTIVE, RelationshipStatus.DELETED),
]
"""Two whose ends saw their state, and two deleted or restored since (ASU-04)."""


@pytest.mark.covers(f"{A}.has_document", rules=["LAS-01"])
def test__active_m4i_entities_have_a_document_but_sources_and_scores() -> None:
    """Every m4i type but ``m4i_source`` and ``m4i_dq_score``; no other type, and no deleted entity (DD-500)."""
    assert has_document(entity(type_name="m4i_data_entity"))
    assert has_document(entity(type_name="m4i_gov_data_quality"))
    assert not has_document(entity(type_name="m4i_source"))
    assert not has_document(entity(type_name="m4i_dq_score"))
    assert not has_document(entity(type_name="hive_table"))
    assert not has_document(entity().model_copy(update={"state": EntityStatus.DELETED}))


@pytest.mark.covers(f"{A}.attribute_value")
@pytest.mark.covers(f"{A}.own_document", rules=["LAS-02"])
def test__the_own_fields_fall_back_to_the_qualified_name_the_guid_and_empty() -> None:
    """Name, else qualified name; qualified name, else the GUID; definition, else ``""``; a person's email only."""
    named = own_document(
        entity(**{"Referenceable.qualifiedName": "q", "m4i_data_entity.name": "N", "m4i_data_entity.definition": "D"})
    )
    unnamed = own_document(entity(**{"Referenceable.qualifiedName": "q", "m4i_data_entity.email": "e@x"}))
    bare = own_document(entity(type_name="m4i_generic_process"))
    person = own_document(entity(type_name="m4i_person", **{"m4i_person.email": "p@x"}))

    assert (named.name, named.referenceablequalifiedname, named.definition) == ("N", "q", "D")
    assert (unnamed.name, unnamed.email) == ("q", None)
    assert (bare.name, bare.referenceablequalifiedname, bare.definition) == (None, "g", "")
    assert person.email == "p@x"
    assert attribute_value(entity(**{"Asset.name": None, "m4i_data_entity.name": "N"}), "name") == "N"


@pytest.mark.covers(f"{A}.source_type", rules=["LAS-03"])
def test__the_source_type_is_technical_business_or_empty() -> None:
    """Four technical types, three business ones, and the rest."""
    assert [source_type(name) for name in ("m4i_field", "m4i_system", "m4i_data_attribute", "m4i_person")] == [
        "Technical",
        "Technical",
        "Business",
        "",
    ]


@pytest.mark.covers(f"{A}.source_hash", rules=["ASD-03"])
@pytest.mark.covers(f"{A}.with_current_app_search", rules=["ASD-03", "ASU-01"])
def test__a_document_is_stale_once_its_own_fields_or_relationships_change() -> None:
    """The hash follows the type, state, own attributes and listed relationships; nothing else (DD-499, DD-518)."""
    stored = indexed(entity(**{"m4i_data_entity.name": "N"}, relationship_guids=None))
    touched = stored.model_copy(update={"update_time": 5, "attributes": stored.attributes | {"Asset.owner": "jo"}})
    reordered = indexed(stored.model_copy(update={"relationship_guids": ["r1", "r2"]}))

    assert with_current_app_search(touched).app_search == stored.app_search
    assert source_hash(reordered) == source_hash(reordered.model_copy(update={"relationship_guids": ["r2", "r1"]}))
    for changed in (
        stored.model_copy(update={"attributes": {"m4i_data_entity.name": "M"}}),
        stored.model_copy(update={"state": EntityStatus.DELETED}),
        stored.model_copy(update={"relationship_guids": ["r1"]}),
    ):
        kept = with_current_app_search(changed).app_search
        assert kept == stored.app_search.model_copy(update={"stale": True})  # type: ignore[union-attr]
        assert with_current_app_search(with_current_app_search(changed)).app_search == kept


@pytest.mark.covers(f"{A}.named_guids", rules=["ASU-03"])
@pytest.mark.covers(f"{A}.identity", rules=["ASU-03"])
def test__a_document_names_its_breadcrumb_and_relations_and_is_known_by_name_breadcrumb_and_guids() -> None:
    """Each GUID once, breadcrumb first; a definition is no part of what others know (DD-519)."""
    document = own_document(entity(**{"m4i_data_entity.name": "N"})).model_copy(
        update={"breadcrumbguid": ["d"], "deriveddataattributeguid": ["a", "d"], "derivedpersonguid": ["p"]}
    )

    assert named_guids(document) == ["d", "a", "p"]
    assert named_guids(None) == []
    assert identity(None) is None
    assert identity(document.model_copy(update={"definition": "other", "stale": True})) == identity(document)
    for other in ({"name": "M"}, {"breadcrumbname": ["D"]}, {"derivedfieldguid": ["f"]}):
        assert identity(document.model_copy(update=other)) != identity(document)


@pytest.mark.covers(f"{A}.app_search_mapping", rules=["ASD-02"])
def test__names_are_keywords_with_text_and_guids_and_types_keywords() -> None:
    """Every field of the stored document is mapped; the names also as text."""
    properties = app_search_mapping()["properties"]

    assert properties["name"]["fields"]["text"] == {"type": "text"}
    assert properties["deriveddataentity"]["type"] == "keyword"
    assert properties["deriveddataentityguid"] == {"type": "keyword"}
    assert properties["sourceHash"] == {"type": "keyword"}
    assert properties["stale"] == {"type": "boolean"}
    assert set(properties) == {field.alias for field in StoredAppSearch.model_fields.values()}


@pytest.mark.covers(f"{D}.prepare", rules=["ASD-02"])
@pytest.mark.covers(f"{D}.write", rules=["ASD-03", "ASU-01"])
@pytest.mark.covers(f"{D}.without_app_search", rules=["LAS-01", "ASD-04", "ASU-02"])
async def test__the_elasticsearch_documents_map_list_and_mark_documents() -> None:
    """On the fake client: the mapping, the listing's query, and the write's check of the hash."""
    client = FakeClient()
    documents = ElasticsearchEntityDocuments(client)  # type: ignore[arg-type]
    await documents.prepare()
    await documents.write(
        [
            (indexed(entity("e", **{"m4i_data_entity.name": "N"})), None),
            (entity("f", "m4i_field"), None),
            (entity("s", "m4i_source"), None),
            (entity("h", "hive_table"), None),
        ]
    )
    read = (await documents.get(["e"]))["e"]
    await documents.write(
        [(read.entity.model_copy(update={"attributes": {"m4i_data_entity.name": "M"}}), read.version)]
    )

    assert client.index_mappings["aurelius-atlas-entities-000001"]["properties"]["appSearch"] == app_search_mapping()
    assert read.entity.app_search is not None
    assert (await documents.get(["e"]))["e"].entity.app_search.stale  # type: ignore[union-attr]
    assert [found.entity.guid for found in await documents.without_app_search(10)] == ["e", "f"]


@pytest.mark.covers(f"{D}.prepare", rules=["ASU-04"])
@pytest.mark.covers(f"{D}.naming", rules=["ASU-03"])
@pytest.mark.covers(f"{D}.unseen_relationships", rules=["ASU-04"])
async def test__the_elasticsearch_documents_list_the_naming_entities_and_the_unseen_relationships() -> None:
    """On the fake client: a term on any GUID field names the entity; deleted or restored since seen is unseen."""
    client = FakeClient()
    documents = ElasticsearchEntityDocuments(client)  # type: ignore[arg-type]
    await documents.prepare()
    await documents.write(
        [
            (indexed(entity("b"), breadcrumbguid=["x"]), None),
            (indexed(entity("r"), derivedprocessguid=["y", "x"]), None),
            (indexed(entity("n"), derivedprocessguid=["y"]), None),
        ],
        linked={LinkedKind.RELATIONSHIP: LinkedWrite(written=[(found, None) for found in RELATIONSHIPS])},
    )

    relationships = client.index_mappings["aurelius-atlas-relationships-000001"]["properties"]
    assert relationships["appSearchState"] == {"type": "keyword"}
    assert sorted(found.entity.guid for found in await documents.naming(["x"])) == ["b", "r"]
    assert await documents.naming([]) == []
    unseen = await documents.unseen_relationships(10)
    assert [found.relationship.guid for found in unseen] == ["deleted", "restored"]
    assert all(found.version is not None for found in unseen)


@pytest.mark.covers(f"{M}.without_app_search", rules=["ASD-04", "ASU-02"])
@pytest.mark.covers(f"{M}.write", rules=["ASD-03", "ASU-01"])
async def test__the_memory_documents_list_and_mark_documents_as_elasticsearch_s_do() -> None:
    """The same listing and the same check of the hash."""
    documents = MemoryEntityDocuments()
    await documents.write(
        [(indexed(entity("e")), None), (entity("f", "m4i_field"), None), (entity("s", "m4i_source"), None)]
    )
    read = (await documents.get(["e"]))["e"]

    assert read.entity.app_search is not None
    assert [found.entity.guid for found in await documents.without_app_search(10)] == ["f"]
    await documents.write([(read.entity.model_copy(update={"state": EntityStatus.DELETED}), read.version)])
    assert (await documents.get(["e"]))["e"].entity.app_search.stale  # type: ignore[union-attr]
    assert [found.entity.guid for found in await documents.without_app_search(10)] == ["e", "f"]


@pytest.mark.covers(f"{M}.naming", rules=["ASU-03"])
@pytest.mark.covers(f"{M}.unseen_relationships", rules=["ASU-04"])
async def test__the_memory_documents_list_the_naming_entities_and_the_unseen_relationships() -> None:
    """The same as Elasticsearch's."""
    documents = MemoryEntityDocuments()
    await documents.write(
        [(indexed(entity("b"), breadcrumbguid=["x"]), None), (indexed(entity("n"), derivedprocessguid=["y"]), None)],
        linked={LinkedKind.RELATIONSHIP: LinkedWrite(written=[(found, None) for found in RELATIONSHIPS])},
    )

    assert [found.entity.guid for found in await documents.naming(["x", "z"])] == ["b"]
    assert [found.relationship.guid for found in await documents.unseen_relationships(10)] == ["deleted", "restored"]
    assert len(await documents.unseen_relationships(1)) == 1
