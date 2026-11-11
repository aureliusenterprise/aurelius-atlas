"""The App Search documents the indexer derives (LAS-01 to LAS-06, ASD-04), on the in-memory store.

The sample catalogue (``data/atlas-sample/sample_data.zip``) is imported and indexed once; each of its tests
compares one rule's fields with ``atlas-dev`` (DD-484), and names the documents allowed to differ (DD-485). Small
catalogues written for one test show what the sample does not: a cycle, a deleted parent, a write in between.
"""

import asyncio
import json
from functools import cache
from pathlib import Path
from typing import Any

import pytest
from aurelius_atlas_core.app_search_document import source_hash, with_current_app_search
from aurelius_atlas_core.app_search_indexer import AppSearchIndexer
from aurelius_atlas_core.entity_retriever import EntityRetriever
from aurelius_atlas_core.entity_store import EntityStore
from aurelius_atlas_core.entity_writer import EntityWriter
from aurelius_atlas_core.import_service import ImportService
from aurelius_atlas_core.model_loader import BUILTIN_MODELS_DIR, M4I_MODELS_DIR, ModelLoader
from aurelius_atlas_core.stored_entity import StoredAppSearch, StoredEntity
from aurelius_atlas_core.testing.memory import MemoryEntityDocuments, MemoryTypedefDocument
from aurelius_atlas_core.typedef_store import TypedefStore
from aurelius_atlas_model import codec
from aurelius_atlas_model.impexp import AtlasImportRequest
from aurelius_atlas_model.instance import AtlasEntitiesWithExtInfo, AtlasEntity, AtlasObjectId, EntityStatus
from aurelius_atlas_typesystem.registry import TypeRegistry

FIXTURES = Path(__file__).parent / "fixtures"
SAMPLE = Path(__file__).parents[4] / "data" / "atlas-sample" / "sample_data.zip"

RELATION_FIELDS = (
    "deriveddatadomain",
    "deriveddataentity",
    "deriveddataattribute",
    "derivedfield",
    "deriveddataset",
    "derivedcollection",
    "derivedsystem",
    "derivedperson",
    "derivedprocess",
)

Document = dict[str, Any]


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


class Indexed:
    """The sample catalogue in the in-memory store, indexed, and how many documents the round wrote."""

    def __init__(self) -> None:
        self.documents = MemoryEntityDocuments()
        self.registry = TypeRegistry()
        self.written = 0

    async def build(self) -> None:
        """Import the sample and run one round."""
        types = await m4i_types()
        self.registry = types.registry
        store = EntityStore(self.registry, self.documents)
        result = await ImportService(store, types, EntityWriter(store, user="importer")).run(
            SAMPLE.read_bytes(), AtlasImportRequest(), "importer", "h", "ip"
        )
        assert result.operation_status.value == "SUCCESS"
        self.written = await AppSearchIndexer(self.documents, self.registry, batch_size=50).run_once()

    def entities(self) -> dict[str, StoredEntity]:
        """Every stored entity by GUID."""
        return {guid: StoredEntity.model_validate(source) for guid, (source, _) in self.documents.entities.items()}

    def derived(self) -> dict[str, StoredAppSearch]:
        """The documents the round wrote, by GUID."""
        return {guid: entity.app_search for guid, entity in self.entities().items() if entity.app_search}


@cache
def indexed() -> Indexed:
    """The sample catalogue, imported and indexed once for the module."""
    found = Indexed()
    asyncio.run(found.build())
    return found


@cache
def legacy() -> dict[str, Document]:
    """``atlas-dev``'s documents by GUID."""
    return {
        document["guid"]: document
        for document in json.loads(FIXTURES.joinpath("legacy-app-search-atlas-dev.json").read_text())
    }


def differing(field: str) -> dict[str, str]:
    """The documents whose ``field`` is not the legacy value, by GUID, with their type; empty counts as none."""
    derived = indexed().derived()
    return {
        guid: document["typename"]
        for guid, document in legacy().items()
        if (getattr(derived[guid], field) or None) != (document[field] or None)
    }


@pytest.mark.covers("aurelius_atlas_core.app_search_indexer.AppSearchIndexer.run_once", rules=["LAS-01", "ASD-04"])
def test__every_entity_of_atlas_dev_gets_its_document_and_no_other() -> None:
    """The 684 documents of ``atlas-dev``, written in one round; the three sources have none."""
    found = indexed()

    assert set(found.derived()) == set(legacy())
    assert found.written == 684
    assert {entity.type_name for guid, entity in found.entities().items() if guid not in legacy()} == {"m4i_source"}


@pytest.mark.covers("aurelius_atlas_core.app_search_document.own_document", rules=["LAS-02", "LAS-03"])
def test__the_own_fields_are_the_legacy_ones_but_dd_485_s() -> None:
    """Name, qualified name, definition, email and source type; the differences of the spec's table only."""
    derived = indexed().derived()

    assert list(differing("name").values()) == ["m4i_gov_data_quality"]
    assert sorted(differing("referenceablequalifiedname").values()) == [
        *["m4i_generic_process"] * 19,
        "m4i_gov_data_quality",
    ]
    assert len(differing("definition")) == 87
    assert differing("email") == {}
    assert differing("sourcetype") == {}
    assert all(derived[guid].referenceablequalifiedname != guid for guid in derived)


@pytest.mark.covers("aurelius_atlas_core.app_search_indexer.AppSearchIndexer.derive", rules=["LAS-04"])
def test__the_breadcrumbs_are_the_legacy_ones_but_two_datasets() -> None:
    """GUIDs, names, types and parent of all 684; two datasets under their first parent dataset, not the second."""
    differences = {
        guid
        for field in ("breadcrumbguid", "breadcrumbname", "breadcrumbtype", "parentguid")
        for guid in differing(field)
    }

    assert sorted(legacy()[guid]["typename"] for guid in differences) == ["m4i_dataset", "m4i_dataset"]
    assert differing("breadcrumbname").keys() <= differences


@pytest.mark.covers("aurelius_atlas_core.app_search_indexer.AppSearchIndexer.derive", rules=["LAS-05", "LAS-06"])
def test__the_derived_relations_are_the_legacy_ones_but_five_datasets() -> None:
    """Every relation field, as sets of GUID and name; five datasets list the 18 relations the legacy lost."""
    derived = indexed().derived()
    gained: list[tuple[str, str]] = []
    for guid, document in legacy().items():
        for field in RELATION_FIELDS:
            mine = getattr(derived[guid], field + "guid")
            names = getattr(derived[guid], field)
            assert len(mine) == len(set(mine)) == len(names), (guid, field)
            pairs = set(zip(mine, names, strict=True))
            theirs = set(zip(document[field + "guid"], document[field], strict=True))
            assert theirs <= pairs, (guid, field)
            gained += [(document["typename"], field)] * len(pairs - theirs)

    assert {typename for typename, _ in gained} == {"m4i_dataset"}
    assert sorted({field for _, field in gained}) == ["derivedfield", "derivedprocess"]
    assert len(gained) == 18


@pytest.mark.covers("aurelius_atlas_core.app_search_document.with_current_app_search", rules=["ASD-03"])
def test__a_document_is_kept_only_while_its_own_fields_are_the_entity_s() -> None:
    """Unchanged, kept; renamed, deleted or with another relationship, dropped."""
    entity = next(entity for entity in indexed().entities().values() if entity.type_name == "m4i_field")
    renamed = entity.model_copy(update={"attributes": entity.attributes | {"Referenceable.name": "renamed"}})
    deleted = entity.model_copy(update={"state": EntityStatus.DELETED})
    related = entity.model_copy(update={"relationship_guids": [*(entity.relationship_guids or []), "new"]})

    assert entity.app_search is not None
    assert entity.app_search.source_hash == source_hash(entity)
    assert with_current_app_search(entity).app_search == entity.app_search
    for changed in (renamed, deleted, related):
        assert with_current_app_search(changed).app_search is None


class Catalogue:
    """A small catalogue of m4i entities, written through the store, each known by its key."""

    def __init__(self, types: TypedefStore) -> None:
        self.documents = MemoryEntityDocuments()
        self.registry = types.registry
        self.store = EntityStore(self.registry, self.documents)
        self.guids: dict[str, str] = {}

    @classmethod
    async def of(cls, *entities: AtlasEntity) -> Catalogue:
        """The entities, created in one request."""
        catalogue = cls(await m4i_types())
        response = await EntityWriter(catalogue.store, user="u").create_or_update(
            AtlasEntitiesWithExtInfo(entities=list(entities))
        )
        catalogue.guids = {key.removeprefix("-"): guid for key, guid in (response.guid_assignments or {}).items()}
        return catalogue

    def indexer(self, batch_size: int = 100) -> AppSearchIndexer:
        """An indexer over the catalogue."""
        return AppSearchIndexer(self.documents, self.registry, batch_size=batch_size)

    async def documents_of(self) -> dict[str, StoredAppSearch]:
        """Every entity's document as derived now, by key."""
        found = await self.documents.get(list(self.guids.values()))
        derived = await self.indexer().derive([found[guid].entity for guid in self.guids.values()])
        return {key: derived[guid] for key, guid in self.guids.items()}

    def keys(self, guids: list[str]) -> list[str]:
        """The keys of these GUIDs."""
        by_guid = {guid: key for key, guid in self.guids.items()}
        return [by_guid[guid] for guid in guids]


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


@pytest.mark.covers(f"{X}.derive", rules=["LAS-04"])
async def test__a_breadcrumb_follows_the_first_parent_of_the_type_s_order_up() -> None:
    """An entity's parent entity comes before its domain; the chain from the top, its parent last."""
    catalogue = await Catalogue.of(
        m4i("m4i_data_domain", "d"),
        m4i("m4i_data_entity", "e1", dataDomain=["d"]),
        m4i("m4i_data_entity", "e2", parentEntity=["e1"], dataDomain=["d"]),
        m4i("m4i_data_attribute", "a", dataEntity=["e2"]),
    )

    documents = await catalogue.documents_of()

    attribute = documents["a"]
    assert catalogue.keys(attribute.breadcrumbguid) == ["d", "e1", "e2"]
    assert attribute.breadcrumbname == ["D", "E1", "E2"]
    assert attribute.breadcrumbtype == ["m4i_data_domain", "m4i_data_entity", "m4i_data_entity"]
    assert attribute.parentguid == catalogue.guids["e2"]
    assert catalogue.keys(documents["e2"].breadcrumbguid) == ["d", "e1"]
    assert (documents["d"].breadcrumbguid, documents["d"].parentguid) == ([], None)


@pytest.mark.covers(f"{X}.derive", rules=["LAS-04"])
async def test__an_entity_already_in_the_chain_ends_it() -> None:
    """Two entities each the other's parent: each has the other as its whole breadcrumb."""
    catalogue = await Catalogue.of(
        m4i("m4i_data_entity", "x", parentEntity=["y"]), m4i("m4i_data_entity", "y", parentEntity=["x"])
    )

    documents = await catalogue.documents_of()

    assert catalogue.keys(documents["x"].breadcrumbguid) == ["y"]
    assert catalogue.keys(documents["y"].breadcrumbguid) == ["x"]


@pytest.mark.covers(f"{X}.derive", rules=["LAS-04", "LAS-05"])
async def test__a_deleted_parent_is_passed_over_and_listed_nowhere() -> None:
    """With its parent entity deleted, an entity's first parent is its domain; no document lists the deleted one."""
    catalogue = await Catalogue.of(
        m4i("m4i_data_domain", "d"),
        m4i("m4i_data_entity", "e1", dataDomain=["d"]),
        m4i("m4i_data_entity", "e2", parentEntity=["e1"], dataDomain=["d"]),
    )
    await EntityWriter(catalogue.store, user="u").delete_by_id(catalogue.guids["e1"])

    documents = await catalogue.documents_of()

    assert catalogue.keys(documents["e2"].breadcrumbguid) == ["d"]
    assert catalogue.keys(documents["d"].deriveddataentityguid) == ["e2"]
    assert documents["e2"].deriveddataentityguid == []


@pytest.mark.covers(f"{X}.derive", rules=["LAS-05", "LAS-06"])
async def test__the_relations_list_both_ends_and_a_field_joins_its_dataset_and_data_entity() -> None:
    """Each end lists the other once, name with GUID; the dataset and the data entity list each other; the
    data quality rule, of a type that is not mapped, lists nothing and is listed nowhere.
    """  # noqa: D205 - one sentence
    quality = m4i("m4i_data_quality", "q", fields=["f"])
    quality.attributes = (quality.attributes or {}) | {"id": 1}
    catalogue = await Catalogue.of(
        m4i("m4i_person", "p"),
        m4i("m4i_data_entity", "e", steward=["p"]),
        m4i("m4i_data_attribute", "a", dataEntity=["e"]),
        m4i("m4i_dataset", "s"),
        m4i("m4i_field", "f", datasets=["s"], attributes=["a"]),
        quality,
    )

    documents = await catalogue.documents_of()

    dataset, entity, field = documents["s"], documents["e"], documents["f"]
    assert (catalogue.keys(dataset.derivedfieldguid), dataset.derivedfield) == (["f"], ["F"])
    assert (catalogue.keys(dataset.deriveddataentityguid), dataset.deriveddataentity) == (["e"], ["E"])
    assert catalogue.keys(entity.deriveddatasetguid) == ["s"]
    assert catalogue.keys(entity.derivedpersonguid) == ["p"]
    assert catalogue.keys(entity.deriveddataattributeguid) == ["a"]
    assert catalogue.keys(documents["p"].deriveddataentityguid) == ["e"]
    assert (catalogue.keys(field.deriveddatasetguid), catalogue.keys(field.deriveddataattributeguid)) == (["s"], ["a"])
    assert field.deriveddataentityguid == []
    quality = documents["q"].model_dump(exclude={"source_hash", "name", "referenceablequalifiedname"})
    assert all(not value for value in quality.values())


@pytest.mark.covers(f"{X}.run_once", rules=["LAS-01", "ASD-04"])
async def test__an_entity_changed_while_its_document_was_derived_gets_it_in_a_later_round() -> None:
    """The write that met a change leaves the entity for the next round; sources and deleted entities get none."""
    catalogue = await Catalogue.of(
        m4i("m4i_data_domain", "d"),
        m4i("m4i_data_entity", "e", dataDomain=["d"]),
        m4i("m4i_system", "y"),
        m4i("m4i_source", "src"),
        m4i("m4i_data_entity", "gone"),
    )
    await EntityWriter(catalogue.store, user="u").delete_by_id(catalogue.guids["gone"])
    catalogue.documents.fail[catalogue.guids["e"]] = "conflict"

    first = await catalogue.indexer().run_once()
    second = await catalogue.indexer().run_once()

    stored = await catalogue.documents.get(list(catalogue.guids.values()))
    with_document = {key for key, guid in catalogue.guids.items() if stored[guid].entity.app_search is not None}
    assert (first, second) == (2, 1)
    assert catalogue.guids["e"] not in catalogue.documents.fail
    assert with_document == {"d", "e", "y"}
    assert await catalogue.documents.without_app_search(10) == []


@pytest.mark.covers("aurelius_atlas_core.entity_retriever.EntityRetriever.entity_with_ext_info", rules=["ASD-05"])
async def test__no_atlas_answer_shows_an_entity_s_document() -> None:
    """An indexed entity reads through the retriever as before: none of its document's fields in its JSON."""
    catalogue = await Catalogue.of(m4i("m4i_data_domain", "d"), m4i("m4i_data_entity", "e", dataDomain=["d"]))
    await catalogue.indexer().run_once()
    guid = catalogue.guids["e"]
    assert (await catalogue.documents.get([guid]))[guid].entity.app_search is not None

    answer = codec.dumps((await EntityRetriever(catalogue.store).entity_with_ext_info(guid)).to_json()).decode()

    assert "appSearch" not in answer
    assert "breadcrumb" not in answer
