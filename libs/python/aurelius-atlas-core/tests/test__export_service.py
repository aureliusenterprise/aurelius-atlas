"""Export (EXP-02 to EXP-06) on the in-memory documents.

Read from ``ExportService``, ``StartEntityFetchByExportRequest``, ``EntitiesExtractor``, ``VertexExtractor``,
``RelationshipAttributesExtractor``, ``ExportTypeProcessor`` and ``ZipSink`` of Apache Atlas 2.4.0, and its
``ExportServiceTest`` and ``ExportSkipLineageTest``: tables of two databases, a process loading one from two others,
and a glossary term assigned to the first.
"""

import io
import itertools
import json
import zipfile
from typing import Any

import pytest
from aurelius_atlas_core.entity_store import EntityStore
from aurelius_atlas_core.entity_writer import EntityWriter
from aurelius_atlas_core.export_service import ExportFetchType, ExportService, overall_operation_status
from aurelius_atlas_core.glossary_service import GlossaryService
from aurelius_atlas_core.model_loader import BUILTIN_MODELS_DIR
from aurelius_atlas_core.testing.memory import MemoryEntityDocuments
from aurelius_atlas_core.zip_sink import ZipSink
from aurelius_atlas_model.glossary import AtlasGlossary, AtlasGlossaryHeader, AtlasGlossaryTerm
from aurelius_atlas_model.impexp import AtlasExportRequest, OperationStatus
from aurelius_atlas_model.instance import AtlasEntitiesWithExtInfo, AtlasRelatedObjectId
from aurelius_atlas_model.typedef import AtlasTypesDef
from aurelius_atlas_typesystem.registry import TypeRegistry

S = "aurelius_atlas_core.export_service"
GUIDS: dict[str, str] = {}
TYPES = {
    "classificationDefs": [{"name": "PII"}],
    "entityDefs": [
        {"name": "hive_db", "superTypes": ["Asset"]},
        {"name": "hive_table", "superTypes": ["DataSet"]},
        {"name": "hive_process", "superTypes": ["Process"]},
        {"name": "plain", "attributeDefs": [{"name": "qualifiedName", "typeName": "string", "isUnique": True}]},
    ],
    "relationshipDefs": [
        {
            "name": "hive_table_db",
            "relationshipCategory": "ASSOCIATION",
            "endDef1": {"type": "hive_table", "name": "db", "cardinality": "SINGLE"},
            "endDef2": {"type": "hive_db", "name": "tables", "cardinality": "SET"},
        }
    ],
}


def _named(type_name: str, name: str, **attributes: Any) -> dict[str, Any]:  # noqa: ANN401 - Atlas JSON
    return {
        "typeName": type_name,
        "guid": f"-{name}",
        "attributes": {"qualifiedName": name, "name": name, **attributes},
    }


def _ref(type_name: str, name: str) -> dict[str, str]:
    return {"typeName": type_name, "guid": f"-{name}"}


@pytest.fixture
async def store() -> EntityStore:
    """``sales``: ``sales_fact`` (``PII``, the term ``loan``); ``reporting``: ``sales_daily``, ``other_table``;
    ``load_daily`` loads ``sales_daily`` from ``sales_fact`` and ``time_dim``.
    """  # noqa: D205 - one sentence
    registry = TypeRegistry()
    with registry.update() as transient:
        for name in ("0010-base_model.json", "0011-glossary_model.json"):
            model = json.loads((BUILTIN_MODELS_DIR / "0000-Area0" / name).read_text(encoding="utf-8"))
            transient.add_types(AtlasTypesDef.model_validate(model))
        transient.add_types(AtlasTypesDef.model_validate(TYPES))
    ticks = itertools.count(1000)
    found = EntityStore(registry, MemoryEntityDocuments(), clock=lambda: next(ticks) / 1000)
    entities = [
        _named("hive_db", "sales"),
        _named("hive_db", "reporting"),
        {**_named("hive_table", "sales_fact"), "relationshipAttributes": {"db": _ref("hive_db", "sales")}},
        _named("hive_table", "time_dim"),
        {**_named("hive_table", "sales_daily"), "relationshipAttributes": {"db": _ref("hive_db", "reporting")}},
        {**_named("hive_table", "other_table"), "relationshipAttributes": {"db": _ref("hive_db", "reporting")}},
        _named(
            "hive_process",
            "load_daily",
            inputs=[_ref("hive_table", "sales_fact"), _ref("hive_table", "time_dim")],
            outputs=[_ref("hive_table", "sales_daily")],
        ),
        _named("plain", "lonely"),
    ]
    entities[2]["classifications"] = [{"typeName": "PII"}]
    created = await EntityWriter(found).create_or_update(
        AtlasEntitiesWithExtInfo.model_validate({"entities": entities})
    )
    GUIDS.clear()
    GUIDS.update({key.removeprefix("-"): value for key, value in (created.guid_assignments or {}).items()})
    glossaries = GlossaryService(found)
    glossary = await glossaries.create_glossary(AtlasGlossary(name="bank"))
    term = await glossaries.create_term(
        AtlasGlossaryTerm(name="loan", anchor=AtlasGlossaryHeader(glossary_guid=glossary.guid))
    )
    await glossaries.assign_term_to_entities(str(term.guid), [AtlasRelatedObjectId(guid=GUIDS["sales_fact"])])
    GUIDS.update(bank=str(glossary.guid), loan=str(term.guid))
    return found


async def export(store: EntityStore, items: list[dict[str, Any]], **options: Any) -> dict[str, Any]:  # noqa: ANN401 - options
    """The ZIP an export of these items writes, its entries by name, read as JSON."""
    sink = ZipSink()
    request = AtlasExportRequest.model_validate({"itemsToExport": items, "options": options})
    await ExportService(store).run(sink, request, "u", "host", "10.0.0.1")
    with zipfile.ZipFile(io.BytesIO(sink.close())) as archive:
        return {name: json.loads(archive.read(name)) for name in archive.namelist()}


def names(order: list[str]) -> list[str]:
    """The names of the GUIDs in the export order."""
    by_guid = {guid: name for name, guid in GUIDS.items()}
    return [by_guid[guid] for guid in order]


SALES_FACT = {"typeName": "hive_table", "uniqueAttributes": {"qualifiedName": "sales_fact"}}


@pytest.mark.covers(
    f"{S}.ExportService.run",
    f"{S}.ExportService.process_entity",
    "aurelius_atlas_core.relationship_attributes_extractor.RelationshipAttributesExtractor.full_fetch",
    "aurelius_atlas_core.export_type_processor.ExportTypeProcessor.add_types",
    "aurelius_atlas_core.zip_sink.ZipSink.add",
    "aurelius_atlas_core.zip_sink.ZipSink.has_entity",
    "aurelius_atlas_core.zip_sink.ZipSink.set_result",
    "aurelius_atlas_core.zip_sink.ZipSink.set_types_def",
    "aurelius_atlas_core.zip_sink.ZipSink.set_export_order",
    "aurelius_atlas_core.zip_sink.ZipSink.close",
    rules=["EXP-04", "EXP-05", "EXP-06"],
)
async def test__a_full_export_reaches_every_related_entity_lineage_last(store: EntityStore) -> None:
    """The term's glossary and term first, then the entity, what it relates to, then lineage and beyond."""
    found = await export(store, [SALES_FACT])

    order = found["atlas-export-order.json"]
    assert names(order) == [
        "bank",
        "loan",
        "sales_fact",
        "sales",
        "load_daily",
        "time_dim",
        "sales_daily",
        "reporting",
        "other_table",
    ]
    assert sorted(found) == sorted(
        [f"{guid}.json" for guid in order]
        + ["atlas-export-order.json", "atlas-typesdef.json", "atlas-export-info.json"]
    )
    assert found[f"{GUIDS['sales_fact']}.json"]["entity"]["classifications"][0]["typeName"] == "PII"
    types = found["atlas-typesdef.json"]
    entity_types = [typedef["name"] for typedef in types["entityDefs"]]
    assert entity_types[:2] == ["hive_table", "hive_db"]  # its relationships' end types before its super types
    assert {"hive_db", "hive_process", "Process", "AtlasGlossary", "AtlasGlossaryTerm"} <= set(entity_types)
    assert [typedef["name"] for typedef in types["classificationDefs"]] == ["PII"]
    assert {"hive_table_db", "dataset_process_inputs", "AtlasGlossarySemanticAssignment"} <= {
        typedef["name"] for typedef in types["relationshipDefs"]
    }
    info = found["atlas-export-info.json"]
    assert info["request"]["itemsToExport"] == [SALES_FACT]
    assert (info["userName"], info["clientIpAddress"], info["hostName"]) == ("u", "10.0.0.1", "host")
    assert (info["operationStatus"], info["sourceClusterName"]) == ("SUCCESS", "default")
    assert "data" not in info
    assert info["metrics"]["entity:hive_table"] == 4
    assert info["metrics"]["entity:withExtInfo"] == 9
    assert info["changeMarker"] == info["timeStamp"]


@pytest.mark.covers(
    "aurelius_atlas_core.relationship_attributes_extractor.RelationshipAttributesExtractor.connected_fetch",
    f"{S}.ExportContext.add_to_be_processed",
    rules=["EXP-02", "EXP-04"],
)
async def test__a_connected_export_follows_the_direction_it_reached_in(store: EntityStore) -> None:
    """From a table out to its database, in to its process and term; the process's tables, not their databases'
    other tables; skipping lineage stops at the process.
    """  # noqa: D205 - one sentence
    connected = await export(store, [SALES_FACT], fetchType="CONNECTED")
    skipped = await export(store, [SALES_FACT], skipLineage="true")

    assert names(connected["atlas-export-order.json"]) == [
        "bank",
        "loan",
        "sales_fact",
        "sales",
        "load_daily",
        "time_dim",
        "sales_daily",
        "reporting",
    ]
    assert names(skipped["atlas-export-order.json"]) == ["bank", "loan", "sales_fact", "sales"]


@pytest.mark.covers(
    "aurelius_atlas_core.start_entity_fetch_by_export_request.StartEntityFetchByExportRequest.get",
    "aurelius_atlas_core.entity_store.EntityStore.of_types",
    "aurelius_atlas_core.entity_documents.EntityDocuments.of_types",
    f"{S}.overall_operation_status",
    rules=["EXP-03", "EXP-06"],
)
async def test__the_starting_entities_are_found_by_guid_type_or_value(store: EntityStore) -> None:
    """``forType`` every entity of the types; ``startsWith`` and the others on text; a miss fails its item."""
    for_type = await export(store, [{"typeName": "hive_db,plain"}], matchType="forType", skipLineage=True)
    starts = await export(
        store, [{"typeName": "hive_db", "uniqueAttributes": {"qualifiedName": "rep"}}], matchType="startsWith"
    )
    mixed = await export(store, [{"guid": GUIDS["lonely"]}, {"guid": "missing"}])
    nothing = await export(store, [{"typeName": "nope", "uniqueAttributes": {"qualifiedName": "x"}}])

    assert {"sales", "reporting", "lonely"} <= set(names(for_type["atlas-export-order.json"]))
    assert names(for_type["atlas-export-order.json"])[0] == "sales"
    assert names(starts["atlas-export-order.json"])[0] == "reporting"
    assert names(mixed["atlas-export-order.json"]) == ["lonely"]
    assert mixed["atlas-export-info.json"]["operationStatus"] == "PARTIAL_SUCCESS"
    assert nothing["atlas-export-info.json"]["operationStatus"] == "FAIL"
    assert nothing["atlas-export-order.json"] == []
    assert overall_operation_status([]) is OperationStatus.FAIL


@pytest.mark.covers(
    "aurelius_atlas_core.vertex_extractor.VertexExtractor.full_fetch",
    "aurelius_atlas_core.vertex_extractor.VertexExtractor.connected_fetch",
    "aurelius_atlas_core.entities_extractor.EntitiesExtractor.set_extractor",
    "aurelius_atlas_core.entities_extractor.EntitiesExtractor.get",
    "aurelius_atlas_core.entities_extractor.ExtractStrategy.full_fetch",
    "aurelius_atlas_core.entities_extractor.ExtractStrategy.connected_fetch",
    rules=["EXP-04"],
)
async def test__an_item_without_a_type_is_followed_through_its_relationships(store: EntityStore) -> None:
    """By GUID alone: every relationship of the entity either way, or connected the way reached."""
    full = await export(store, [{"guid": GUIDS["sales_daily"]}], skipLineage=True)
    connected = await export(store, [{"guid": GUIDS["sales_daily"]}], fetchType="connected")

    assert names(full["atlas-export-order.json"]) == ["sales_daily", "reporting", "other_table"]
    assert names(connected["atlas-export-order.json"])[:2] == ["sales_daily", "reporting"]


@pytest.mark.covers(
    f"{S}.ExportContext.does_timestamp_qualify",
    f"{S}.ExportContext.entities_with_modified_timestamp",
    f"{S}.ExportContext.add_to_sink",
    f"{S}.ExportFetchType.of",
    rules=["EXP-02", "EXP-05"],
)
async def test__an_incremental_export_adds_what_changed_since_its_marker(store: EntityStore) -> None:
    """Every entity reached is followed, only those updated at or after the marker are added."""
    sales = await store.get(GUIDS["sales"])
    assert sales is not None
    marker = sales.entity.update_time + 1
    found = await export(
        store, [{"guid": GUIDS["sales"]}], fetchType="incremental", changeMarker=str(marker), skipLineage=True
    )

    assert "sales" not in names(found["atlas-export-order.json"])
    assert ExportFetchType.of("Connected") is ExportFetchType.CONNECTED
    assert ExportFetchType.of("other") is ExportFetchType.FULL
