"""Import transforms (ITR-01 to ITR-05).

Read from Apache Atlas 2.4.0's ``ImportTransforms``, ``ImportTransformer`` and ``ImportTransformsShaper``, and its
``ImportTransformsTest`` and ``ImportTransformerTest``.
"""

import json
from typing import Any

import pytest
from aurelius_atlas_core.entity_retriever import EntityRetriever
from aurelius_atlas_core.entity_store import EntityStore
from aurelius_atlas_core.entity_writer import EntityWriter
from aurelius_atlas_core.export_service import ExportService
from aurelius_atlas_core.import_service import ImportService
from aurelius_atlas_core.import_transforms import ImportTransforms, shape, transformer
from aurelius_atlas_core.model_loader import BUILTIN_MODELS_DIR
from aurelius_atlas_core.testing.memory import MemoryEntityDocuments, MemoryTypedefDocument
from aurelius_atlas_core.typedef_store import TypedefStore
from aurelius_atlas_core.zip_sink import ZipSink
from aurelius_atlas_model.impexp import AtlasExportRequest, AtlasImportRequest
from aurelius_atlas_model.instance import AtlasEntitiesWithExtInfo, AtlasEntity, AtlasEntityWithExtInfo
from aurelius_atlas_model.typedef import AtlasTypesDef
from aurelius_atlas_typesystem.registry import TypeRegistry

T = "aurelius_atlas_core.import_transforms"
BASE = json.loads((BUILTIN_MODELS_DIR / "0000-Area0" / "0010-base_model.json").read_text(encoding="utf-8"))
TYPES = {
    "entityDefs": [{"name": "tr_table", "superTypes": ["DataSet"]}, {"name": "tr_view", "superTypes": ["tr_table"]}]
}


def entity(**attributes: Any) -> AtlasEntity:  # noqa: ANN401 - attribute values
    """A ``tr_table`` of these attributes."""
    return AtlasEntity.model_validate({"typeName": "tr_table", "guid": "g", "attributes": attributes})


def applied(spec: str, value: Any) -> Any:  # noqa: ANN401 - any value
    """The value through the transformer the specification names."""
    found = transformer(spec)
    assert found is not None
    return found(value)


@pytest.mark.covers(f"{T}.transformer", f"{T}.AddValueToAttribute.__call__", rules=["ITR-02", "ITR-03"])
def test__each_transformer_changes_what_it_names() -> None:
    """Text transformers change text only; entity transformers change an entity only."""
    assert applied("lowercase", "AbC") == "abc"
    assert applied("uppercase", "AbC") == "ABC"
    assert applied("replace:@cl1:@cl2", "db@cl1") == "db@cl2"
    assert applied("replace::x", "abc") == "abc"  # empty parameters dropped: nothing to find
    assert applied("lowercase", 3) == 3
    assert applied("lowercase", entity()).type_name == "tr_table"
    cleared = applied("clearAttrValue:a,b", entity(a=1, b=2, c=3))
    assert cleared.attributes == {"a": None, "b": None, "c": 3}
    assert applied("setDeleted", entity()).status.value == "DELETED"
    assert applied("add:tags=list:x", entity(tags=["a"])).attributes["tags"] == ["a", "x"]
    assert applied("add:tags=list:x", entity()).attributes["tags"] == ["x"]
    assert applied("add:owner=bob", entity(owner="ann")).attributes["owner"] == "bob"
    classified = AtlasEntity.model_validate(
        {"typeName": "t", "classifications": [{"typeName": "PII"}, {"typeName": "X"}]}
    )
    assert [c.type_name for c in applied("removeClassification:PII", classified).classifications] == ["X"]
    assert transformer("unknown") is None
    assert transformer("") is None


@pytest.mark.covers(
    f"{T}.ImportTransforms.from_json",
    f"{T}.ImportTransforms.apply",
    f"{T}.ImportTransforms.add_parent_transforms_to_sub_types",
    f"{T}.AddClassification.__call__",
    f"{T}.shape",
    rules=["ITR-01", "ITR-03", "ITR-04"],
)
async def test__the_transforms_of_a_type_apply_to_it_and_its_sub_types() -> None:
    """``*`` before attributes; a sub type takes its parent's; ``topLevel`` adds a classification to export items."""
    types = TypedefStore(TypeRegistry(), MemoryTypedefDocument())
    await types.load()
    await types.create_types_def(AtlasTypesDef.model_validate(BASE))
    await types.create_types_def(AtlasTypesDef.model_validate(TYPES))
    option = json.dumps(
        {
            "tr_table": {
                "qualifiedName": ["lowercase", "replace:@a:@b"],
                "*": ["addClassification:REPLICATED:topLevel", "nonsense"],
            }
        }
    )
    transforms = ImportTransforms.from_json(option)
    assert transforms is not None
    request = AtlasExportRequest.model_validate({"itemsToExport": [{"guid": "top"}]})

    await shape(transforms, request, types, "u")
    top = AtlasEntity.model_validate({"typeName": "tr_view", "guid": "top", "attributes": {"qualifiedName": "T@A"}})
    owned = AtlasEntity.model_validate({"typeName": "tr_table", "guid": "o", "attributes": {"qualifiedName": "O@a"}})
    found = transforms.apply(AtlasEntityWithExtInfo(entity=top, referred_entities={"o": owned}))

    assert found is not None
    assert types.registry.classification_type("REPLICATED") is not None
    assert (top.attributes or {})["qualifiedName"] == "t@b"
    assert (owned.attributes or {})["qualifiedName"] == "o@b"
    assert [c.type_name for c in top.classifications or []] == ["REPLICATED"]
    assert owned.classifications is None
    assert ImportTransforms.from_json(None) is None
    empty = ImportTransforms.from_json("not json")
    assert empty is not None
    assert empty.transforms == {}


@pytest.mark.covers("aurelius_atlas_core.import_service.ImportService.run", rules=["ITR-05"])
async def test__an_import_writes_its_entities_transformed() -> None:
    """The ``transforms`` option of an import changes each entity before it is written."""
    types = TypedefStore(TypeRegistry(), MemoryTypedefDocument())
    await types.load()
    for model in (BASE, TYPES):
        await types.create_types_def(AtlasTypesDef.model_validate(model))
    store = EntityStore(types.registry, MemoryEntityDocuments())
    body = {"entities": [{"typeName": "tr_table", "guid": "-1", "attributes": {"qualifiedName": "T@CL1", "name": "t"}}]}
    created = await EntityWriter(store).create_or_update(AtlasEntitiesWithExtInfo.model_validate(body))
    guid = (created.guid_assignments or {})["-1"]
    sink = ZipSink()
    await ExportService(store).run(
        sink, AtlasExportRequest.model_validate({"itemsToExport": [{"guid": guid}]}), "u", "h", "i"
    )
    target = EntityStore(types.registry, MemoryEntityDocuments())
    option = json.dumps({"tr_table": {"qualifiedName": ["lowercase"]}})
    request = AtlasImportRequest.model_validate({"options": {"transforms": option}})

    await ImportService(target, types, EntityWriter(target)).run(sink.close(), request, "u", "h", "i")
    imported = (await EntityRetriever(target).entity_with_ext_info(guid)).entity

    assert imported is not None
    assert (imported.attributes or {})["qualifiedName"] == "t@cl1"
