"""The App Search documents kept up to date as the catalogue changes (LAS-08, LAS-09, ASU-02 to ASU-05, ASU-07).

Each test indexes a small catalogue in the in-memory store, changes it, and runs one round. Then every stored
document must be the one the indexer derives from scratch (DD-486), nothing stale or unseen is left, and the
fields the change is about read as LAS-08 and LAS-09 say.
"""

import pytest
from aurelius_atlas_core.app_search_indexer import AppSearchIndexer
from aurelius_atlas_core.entity_store import EntityStore
from aurelius_atlas_core.entity_writer import EntityWriter
from aurelius_atlas_core.model_loader import BUILTIN_MODELS_DIR, M4I_MODELS_DIR, ModelLoader
from aurelius_atlas_core.relationship_store import RelationshipStore
from aurelius_atlas_core.stored_entity import StoredAppSearch
from aurelius_atlas_core.testing.memory import MemoryEntityDocuments, MemoryTypedefDocument
from aurelius_atlas_core.typedef_store import TypedefStore
from aurelius_atlas_model import codec
from aurelius_atlas_model.instance import AtlasEntitiesWithExtInfo, AtlasEntity, AtlasObjectId
from aurelius_atlas_typesystem.registry import TypeRegistry

X = "aurelius_atlas_core.app_search_indexer.AppSearchIndexer"

_LOADED: dict[str, TypedefStore] = {}


async def m4i_types() -> TypedefStore:
    """A typedef store with Atlas's and the data dictionary's models (ADR 058), loaded once for the module."""
    if "m4i" not in _LOADED:
        types = TypedefStore(TypeRegistry(), MemoryTypedefDocument())
        await types.load()
        for models_dir in (BUILTIN_MODELS_DIR, M4I_MODELS_DIR):
            assert (await ModelLoader(types).load(models_dir)).failed_files == []
        _LOADED["m4i"] = types
    return _LOADED["m4i"]


def m4i(type_name: str, key: str, **relations: list[str]) -> AtlasEntity:
    """An entity named after ``key``, with relationship attributes naming other entities of the request by key."""
    return AtlasEntity(
        type_name=type_name,
        guid=f"-{key}",
        attributes={"qualifiedName": key, "name": key.upper()},
        relationship_attributes={
            name: [AtlasObjectId(guid=f"-{other}") for other in others] for name, others in relations.items()
        },
    )


class Catalogue:
    """A small catalogue of m4i entities, written through the store and indexed, each known by its key."""

    def __init__(self, types: TypedefStore) -> None:
        self.documents = MemoryEntityDocuments()
        self.store = EntityStore(types.registry, self.documents)
        self.indexer = AppSearchIndexer(self.documents, types.registry)
        self.writer = EntityWriter(self.store, user="u")
        self.guids: dict[str, str] = {}

    @classmethod
    async def indexed(cls, *entities: AtlasEntity) -> Catalogue:
        """The entities, created in one request, and a round of the indexer."""
        catalogue = cls(await m4i_types())
        response = await catalogue.writer.create_or_update(AtlasEntitiesWithExtInfo(entities=list(entities)))
        catalogue.guids = {key.removeprefix("-"): guid for key, guid in (response.guid_assignments or {}).items()}
        await catalogue.indexer.run_once()
        return catalogue

    async def stored(self, key: str) -> StoredAppSearch | None:
        """The key's stored document."""
        guid = self.guids[key]
        return (await self.documents.get([guid]))[guid].entity.app_search

    async def document(self, key: str) -> StoredAppSearch:
        """The key's stored document, which must exist."""
        document = await self.stored(key)
        assert document is not None, key
        return document

    async def relationship(self, key: str, other: str) -> str:
        """The GUID of the relationship between two keys' entities."""
        found = await self.documents.get([self.guids[key], self.guids[other]])
        listed = set(found[self.guids[key]].entity.relationship_guids or [])
        (guid,) = listed & set(found[self.guids[other]].entity.relationship_guids or [])
        return guid

    def keys(self, guids: list[str]) -> list[str]:
        """The keys of these GUIDs."""
        by_guid = {guid: key for key, guid in self.guids.items()}
        return [by_guid[guid] for guid in guids]

    async def assert_current(self) -> None:
        """Every stored document is the one derived from scratch; none is stale, no relationship is unseen."""
        found = await self.documents.get(list(self.guids.values()))
        derived = await self.indexer.derive([versioned.entity for versioned in found.values()])
        stored = {guid: versioned.entity.app_search for guid, versioned in found.items()}
        assert stored == derived
        assert await self.documents.without_app_search(100) == []
        assert await self.documents.unseen_relationships(100) == []


@pytest.mark.covers(f"{X}.run_once", rules=["LAS-08", "ASU-02", "ASU-03"])
async def test__a_rename_shows_in_the_breadcrumbs_below_and_the_relations_at_the_other_ends() -> None:
    """The entity's new name on its document, its attribute's breadcrumb and its domain's relation; nothing else."""
    catalogue = await Catalogue.indexed(
        m4i("m4i_data_domain", "d"),
        m4i("m4i_data_entity", "e", dataDomain=["d"]),
        m4i("m4i_data_attribute", "a", dataEntity=["e"]),
        m4i("m4i_system", "y"),
    )

    await catalogue.writer.update_attribute_by_guid(catalogue.guids["e"], "name", "Renamed")
    written = await catalogue.indexer.run_once()

    await catalogue.assert_current()
    assert written == 3
    assert (await catalogue.document("e")).name == "Renamed"
    assert (await catalogue.document("a")).breadcrumbname == ["D", "Renamed"]
    assert (await catalogue.document("d")).deriveddataentity == ["Renamed"]


@pytest.mark.covers(f"{X}.run_once", rules=["LAS-08", "ASU-03"])
async def test__a_changed_definition_shows_on_the_entity_s_own_document_only() -> None:
    """One document written: no other document holds a definition."""
    catalogue = await Catalogue.indexed(m4i("m4i_data_domain", "d"), m4i("m4i_data_entity", "e", dataDomain=["d"]))

    await catalogue.writer.update_attribute_by_guid(catalogue.guids["d"], "definition", "What d is")
    written = await catalogue.indexer.run_once()

    await catalogue.assert_current()
    assert written == 1
    assert (await catalogue.document("d")).definition == "What d is"


@pytest.mark.covers(f"{X}.run_once", rules=["LAS-09", "ASU-02", "ASU-03", "ASU-04"])
async def test__a_deleted_entity_leaves_every_document_and_those_below_get_their_next_parent() -> None:
    """Its document goes; its domain no longer lists it; the entity below falls back to the domain, and so does
    the breadcrumb of the attribute below that.
    """  # noqa: D205 - one sentence
    catalogue = await Catalogue.indexed(
        m4i("m4i_data_domain", "d"),
        m4i("m4i_data_entity", "e1", dataDomain=["d"]),
        m4i("m4i_data_entity", "e2", parentEntity=["e1"], dataDomain=["d"]),
        m4i("m4i_data_attribute", "a", dataEntity=["e2"]),
    )

    await catalogue.writer.delete_by_id(catalogue.guids["e1"])
    await catalogue.indexer.run_once()

    await catalogue.assert_current()
    assert await catalogue.stored("e1") is None
    assert catalogue.keys((await catalogue.document("d")).deriveddataentityguid) == ["e2"]
    assert catalogue.keys((await catalogue.document("e2")).breadcrumbguid) == ["d"]
    assert catalogue.keys((await catalogue.document("a")).breadcrumbguid) == ["d", "e2"]


@pytest.mark.covers(f"{X}.run_once", rules=["ASU-04"])
@pytest.mark.covers("aurelius_atlas_core.relationship_store.RelationshipStore.get_by_id", rules=["ASU-07"])
async def test__a_relationship_deleted_on_its_own_leaves_its_ends_and_its_answer_shows_no_record() -> None:
    """Neither end hash changes; the relationship's own listing reaches both, and Atlas's answer is as before."""
    catalogue = await Catalogue.indexed(m4i("m4i_dataset", "s"), m4i("m4i_field", "f", datasets=["s"]))
    guid = await catalogue.relationship("f", "s")

    await RelationshipStore(catalogue.store, user="u").delete_by_id(guid)
    await catalogue.indexer.run_once()

    await catalogue.assert_current()
    assert (await catalogue.document("s")).derivedfield == []
    assert (await catalogue.document("f")).breadcrumbguid == []
    answer = codec.dumps((await RelationshipStore(catalogue.store).get_by_id(guid)).to_json()).decode()
    assert "appSearch" not in answer


@pytest.mark.covers(f"{X}.run_once", rules=["ASU-04"])
async def test__a_relationship_an_update_drops_leaves_its_ends() -> None:
    """A field updated without its dataset: the soft-deleted relationship is unseen until the round."""
    catalogue = await Catalogue.indexed(m4i("m4i_dataset", "s"), m4i("m4i_field", "f", datasets=["s"]))

    field = m4i("m4i_field", "f")
    field.guid = catalogue.guids["f"]
    field.relationship_attributes = {"datasets": []}
    await catalogue.writer.create_or_update(AtlasEntitiesWithExtInfo(entities=[field]))
    assert len(await catalogue.documents.unseen_relationships(10)) == 1
    await catalogue.indexer.run_once()

    await catalogue.assert_current()
    assert (await catalogue.document("s")).derivedfield == []


@pytest.mark.covers(f"{X}.run_once", rules=["LAS-06", "ASU-03"])
async def test__a_field_joined_to_an_attribute_and_parted_again_reaches_the_data_entity_two_hops_away() -> None:
    """The data entity's hash never changes. Joined, its attribute is stale and reaches it; parted by a deleted
    relationship, the attribute is an end, and its changed relations reach it a hop further (DD-519).
    """  # noqa: D205 - one sentence
    catalogue = await Catalogue.indexed(
        m4i("m4i_data_entity", "e"),
        m4i("m4i_data_attribute", "a", dataEntity=["e"]),
        m4i("m4i_dataset", "s"),
        m4i("m4i_field", "f", datasets=["s"]),
    )

    field = m4i("m4i_field", "f", datasets=["s"], attributes=["a"])
    field.guid = catalogue.guids["f"]
    field.relationship_attributes = {
        "datasets": [AtlasObjectId(guid=catalogue.guids["s"])],
        "attributes": [AtlasObjectId(guid=catalogue.guids["a"])],
    }
    await catalogue.writer.create_or_update(AtlasEntitiesWithExtInfo(entities=[field]))
    await catalogue.indexer.run_once()

    await catalogue.assert_current()
    assert catalogue.keys((await catalogue.document("e")).deriveddatasetguid) == ["s"]
    assert catalogue.keys((await catalogue.document("s")).deriveddataentityguid) == ["e"]

    await RelationshipStore(catalogue.store, user="u").delete_by_id(await catalogue.relationship("f", "a"))
    await catalogue.indexer.run_once()

    await catalogue.assert_current()
    assert (await catalogue.document("e")).deriveddatasetguid == []
    assert (await catalogue.document("s")).deriveddataentityguid == []


@pytest.mark.covers(f"{X}.run_once", rules=["ASU-05"])
async def test__an_affected_entity_changed_in_between_keeps_the_page_listed_for_a_later_round() -> None:
    """The attribute's write meets a conflict: the renamed entity stays stale, and the next round finishes."""
    catalogue = await Catalogue.indexed(
        m4i("m4i_data_domain", "d"),
        m4i("m4i_data_entity", "e", dataDomain=["d"]),
        m4i("m4i_data_attribute", "a", dataEntity=["e"]),
    )
    await catalogue.writer.update_attribute_by_guid(catalogue.guids["e"], "name", "Renamed")
    catalogue.documents.fail[catalogue.guids["a"]] = "conflict"

    first = await catalogue.indexer.run_once()

    assert first == 1
    assert (await catalogue.document("e")).stale
    assert (await catalogue.document("a")).breadcrumbname == ["D", "E"]
    await catalogue.indexer.run_once()
    await catalogue.assert_current()
    assert (await catalogue.document("a")).breadcrumbname == ["D", "Renamed"]
