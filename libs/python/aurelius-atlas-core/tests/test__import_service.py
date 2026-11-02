"""Import (IMS-01 to IMS-06) of an export's ZIP into a second store, on the in-memory documents.

Read from Apache Atlas 2.4.0's ``ImportService``, ``ZipSource``, ``ImportTypeDefProcessor``,
``TypeAttributeDifference`` and ``RegularImport``, and its ``ImportServiceTest``: a database and a classified table
exported from one catalogue and imported into another that lacks their types.
"""

import io
import json
import zipfile
from pathlib import Path
from typing import Any

import pytest
from aurelius_atlas_core.entity_retriever import EntityRetriever
from aurelius_atlas_core.entity_store import EntityStore
from aurelius_atlas_core.entity_writer import EntityWriter
from aurelius_atlas_core.export_service import ExportService
from aurelius_atlas_core.import_service import ImportService
from aurelius_atlas_core.model_loader import BUILTIN_MODELS_DIR
from aurelius_atlas_core.testing.memory import MemoryEntityDocuments, MemoryTypedefDocument
from aurelius_atlas_core.typedef_store import TypedefStore
from aurelius_atlas_core.zip_sink import ZipSink
from aurelius_atlas_core.zip_source import ZipSource
from aurelius_atlas_model.errors import AtlasError, AtlasErrorCode
from aurelius_atlas_model.impexp import AtlasExportRequest, AtlasImportRequest
from aurelius_atlas_model.instance import AtlasEntitiesWithExtInfo
from aurelius_atlas_model.typedef import AtlasTypesDef
from aurelius_atlas_typesystem.registry import TypeRegistry

S = "aurelius_atlas_core.import_service.ImportService"
BASE = json.loads((BUILTIN_MODELS_DIR / "0000-Area0" / "0010-base_model.json").read_text(encoding="utf-8"))
DB_ATTRIBUTES = [{"name": "region", "typeName": "string", "isOptional": True}]
TYPES = {
    "classificationDefs": [{"name": "PII"}],
    "entityDefs": [
        {"name": "imp_db", "superTypes": ["Asset"], "attributeDefs": DB_ATTRIBUTES},
        {"name": "imp_table", "superTypes": ["DataSet"]},
    ],
    "relationshipDefs": [
        {
            "name": "imp_table_db",
            "relationshipCategory": "ASSOCIATION",
            "endDef1": {"type": "imp_table", "name": "db", "cardinality": "SINGLE"},
            "endDef2": {"type": "imp_db", "name": "tables", "cardinality": "SET"},
        }
    ],
}


async def catalogue(*models: dict[str, Any]) -> tuple[EntityStore, TypedefStore]:
    """An entity store and its typedef store, of these models."""
    types = TypedefStore(TypeRegistry(), MemoryTypedefDocument())
    await types.load()
    for model in models:
        await types.create_types_def(AtlasTypesDef.model_validate(model))
    return EntityStore(types.registry, MemoryEntityDocuments()), types


@pytest.fixture
async def exported() -> tuple[bytes, dict[str, str]]:
    """The ZIP of a full export of a classified table and its database, and their GUIDs."""
    store, _ = await catalogue(BASE, TYPES)
    entities = [
        {"typeName": "imp_db", "guid": "-1", "attributes": {"qualifiedName": "d", "name": "d", "region": "eu"}},
        {
            "typeName": "imp_table",
            "guid": "-2",
            "attributes": {"qualifiedName": "t", "name": "t"},
            "classifications": [{"typeName": "PII"}],
            "relationshipAttributes": {"db": {"typeName": "imp_db", "guid": "-1"}},
        },
    ]
    created = await EntityWriter(store).create_or_update(
        AtlasEntitiesWithExtInfo.model_validate({"entities": entities})
    )
    guids = {"db": (created.guid_assignments or {})["-1"], "table": (created.guid_assignments or {})["-2"]}
    sink = ZipSink()
    request = AtlasExportRequest.model_validate({"itemsToExport": [{"guid": guids["table"]}]})
    await ExportService(store).run(sink, request, "exporter", "h", "ip")
    return sink.close(), guids


async def importing(store: EntityStore, types: TypedefStore, content: bytes, **options: object) -> dict[str, Any]:
    """The result of importing the ZIP into the store, as JSON."""
    request = AtlasImportRequest.model_validate({"options": options})
    service = ImportService(store, types, EntityWriter(store, user="importer"))
    return (await service.run(content, request, "importer", "host", "10.0.0.2")).to_json()


@pytest.mark.covers(
    f"{S}.run",
    "aurelius_atlas_core.import_type_def_processor.ImportTypeDefProcessor.process_types",
    "aurelius_atlas_core.regular_import.RegularImport.run",
    "aurelius_atlas_core.zip_source.ZipSource.types_def",
    "aurelius_atlas_core.zip_source.ZipSource.export_result",
    "aurelius_atlas_core.zip_source.ZipSource.has_next",
    "aurelius_atlas_core.zip_source.ZipSource.next_entity_with_ext_info",
    rules=["IMS-01", "IMS-02", "IMS-03", "IMS-04"],
)
async def test__an_export_imports_into_a_catalogue_without_its_types(exported: tuple[bytes, dict[str, str]]) -> None:
    """The types created and counted, the entities written with their GUIDs and relationship, counted by type."""
    content, guids = exported
    store, types = await catalogue(BASE)

    found = await importing(store, types, content)
    table = (await EntityRetriever(store).entity_with_ext_info(guids["table"])).entity

    assert found["operationStatus"] == "SUCCESS"
    assert (found["userName"], found["clientIpAddress"], found["hostName"]) == ("importer", "10.0.0.2", "host")
    assert found["metrics"]["typedef:entitydef"] == 2
    assert found["metrics"]["typedef:classification"] == 1
    assert found["metrics"]["typedef:relationship"] == 1
    assert (found["metrics"]["entity:imp_table:created"], found["metrics"]["entity:imp_db:created"]) == (1, 1)
    assert sorted(found["processedEntities"]) == sorted(guids.values())
    assert found["exportResult"]["operationStatus"] == "SUCCESS"
    assert table is not None
    assert [c.type_name for c in table.classifications or []] == ["PII"]
    assert table.to_json()["relationshipAttributes"]["db"]["guid"] == guids["db"]

    again = await importing(store, types, content)
    assert not any(key.endswith(":created") for key in again["metrics"])
    assert "typedef:entitydef" not in again["metrics"]


@pytest.mark.covers(f"{S}.run", rules=["IMS-03"])
async def test__a_known_type_gets_the_attributes_the_import_adds(exported: tuple[bytes, dict[str, str]]) -> None:
    """``TypeAttributeDifference``: a missing attribute added and counted; a changed type fails the import."""
    content, _ = exported
    narrow = {**TYPES, "entityDefs": [{**TYPES["entityDefs"][0], "attributeDefs": []}, TYPES["entityDefs"][1]]}
    store, types = await catalogue(BASE, narrow)

    found = await importing(store, types, content)

    assert found["metrics"]["typedef:entitydef:update"] == 1
    db_def = types.registry.typedef_by_name("imp_db")
    assert [attribute.name for attribute in getattr(db_def, "attribute_defs", None) or []] == ["region"]
    changed = {
        **TYPES,
        "entityDefs": [
            {**TYPES["entityDefs"][0], "attributeDefs": [{**DB_ATTRIBUTES[0], "typeName": "int"}]},
            TYPES["entityDefs"][1],
        ],
    }
    other, other_types = await catalogue(BASE, changed)
    with pytest.raises(AtlasError) as raised:
        await importing(other, other_types, content)
    assert raised.value.code is AtlasErrorCode.INVALID_IMPORT_ATTRIBUTE_TYPE_CHANGED
    skipped, skipped_types = await catalogue(BASE, narrow)
    kept = await importing(skipped, skipped_types, content, updateTypeDefinition="false")
    assert "typedef:entitydef:update" not in kept["metrics"]


@pytest.mark.covers("aurelius_atlas_core.regular_import.RegularImport.run", rules=["IMS-05"])
async def test__an_entity_holding_the_same_values_is_imported_as_that_entity(
    exported: tuple[bytes, dict[str, str]],
) -> None:
    """A stored database of the same name keeps its GUID; the table relates to it."""
    content, guids = exported
    store, types = await catalogue(BASE, TYPES)
    created = await EntityWriter(store).create_or_update(
        AtlasEntitiesWithExtInfo.model_validate(
            {"entities": [{"typeName": "imp_db", "guid": "-1", "attributes": {"qualifiedName": "d", "name": "d"}}]}
        )
    )
    existing = (created.guid_assignments or {})["-1"]

    found = await importing(store, types, content)
    table = (await EntityRetriever(store).entity_with_ext_info(guids["table"])).entity

    assert table is not None
    assert table.to_json()["relationshipAttributes"]["db"]["guid"] == existing
    assert await store.get(guids["db"]) is None
    assert found["metrics"]["entity:imp_db:updated"] == 1


@pytest.mark.covers(
    "aurelius_atlas_core.zip_source.ZipSource.set_position",
    "aurelius_atlas_core.zip_source.ZipSource.set_position_using_entity_guid",
    "aurelius_atlas_core.zip_source.ZipSource.on_import_complete",
    "aurelius_atlas_core.zip_source.ZipSource.size",
    rules=["IMS-02"],
)
async def test__an_import_starts_after_the_position_asked_and_refuses_an_empty_zip(
    exported: tuple[bytes, dict[str, str]],
) -> None:
    """``startGuid`` and ``startPosition`` skip up to and with the entity named; an empty ZIP is refused."""
    content, guids = exported
    source = ZipSource(content)
    assert source.size() == 2

    store, types = await catalogue(BASE)
    found = await importing(store, types, content, startGuid=guids["table"])
    assert "entity:imp_table:created" not in found["metrics"]
    other, other_types = await catalogue(BASE)
    by_position = await importing(other, other_types, content, startPosition="0")
    assert "entity:imp_table:created" not in by_position["metrics"]

    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        archive.writestr("atlas-export-order.json", "[]")
    for empty in (buffer.getvalue(), b"no zip"):
        with pytest.raises(AtlasError) as raised:
            ZipSource(empty)
        assert raised.value.code is AtlasErrorCode.IMPORT_ATTEMPTING_EMPTY_ZIP


@pytest.mark.covers(f"{S}.run_file", rules=["IMS-06"])
async def test__a_file_is_imported_only_from_the_import_folder(
    exported: tuple[bytes, dict[str, str]], tmp_path: Path
) -> None:
    """The file name within the folder; none, one outside it, or no folder is not found."""
    content, _ = exported
    folder = tmp_path / "imports"
    folder.mkdir()
    (folder / "export.zip").write_bytes(content)
    (tmp_path / "outside.zip").write_bytes(content)
    store, types = await catalogue(BASE)
    service = ImportService(store, types, EntityWriter(store, user="importer"))

    def request(name: str) -> AtlasImportRequest:
        return AtlasImportRequest.model_validate({"options": {"fileName": name}})

    found = await service.run_file(request("export.zip"), folder, "u", "h", "ip")
    assert found.operation_status.value == "SUCCESS"
    for name, where, message in (
        (" ", folder, "invalid parameters: FILENAME parameter not found"),
        ("../outside.zip", folder, "invalid parameters: ../outside.zip: file not found"),
        ("export.zip", None, "invalid parameters: export.zip: file not found"),
        ("missing.zip", folder, "invalid parameters: missing.zip: file not found"),
    ):
        with pytest.raises(AtlasError) as raised:
            await service.run_file(request(name), where, "u", "h", "ip")
        assert raised.value.message == message
