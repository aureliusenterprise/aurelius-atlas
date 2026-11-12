"""The m4i data dictionary types, loaded after Atlas's models (MDD-01 to MDD-04, DD-362), on the in-memory document.

The model file is the data dictionary group of ``m4i_atlas_core`` (54d9e04): its entity, relationship and
classification definitions as the sample exports in ``data/atlas-sample/`` carry them, without what a stored
definition adds.
"""

import json
import shutil
import zipfile
from pathlib import Path
from typing import Any

import pytest
from aurelius_atlas_core.entity_store import EntityStore
from aurelius_atlas_core.entity_writer import EntityWriter
from aurelius_atlas_core.import_service import ImportService
from aurelius_atlas_core.model_loader import BUILTIN_MODELS_DIR, M4I_MODELS_DIR, ModelLoader
from aurelius_atlas_core.testing.memory import MemoryEntityDocuments, MemoryTypedefDocument
from aurelius_atlas_core.typedef_change_listener import ChangedTypeDefs
from aurelius_atlas_core.typedef_store import TypedefStore
from aurelius_atlas_model.impexp import AtlasImportRequest
from aurelius_atlas_model.typedef import AtlasEntityDef
from aurelius_atlas_typesystem.registry import TypeRegistry

SAMPLES = Path(__file__).parents[4] / "data" / "atlas-sample"
MODEL = M4I_MODELS_DIR / "0010-m4i_data_dictionary_model.json"
CLASSIFICATIONS = {"PII", "key_data", "low_risk", "medium_risk", "high_risk"}
STORED = {
    "guid",
    "createdBy",
    "updatedBy",
    "createTime",
    "updateTime",
    "version",
    "category",
    "subTypes",
    "relationshipAttributeDefs",
    "businessAttributeDefs",
}
"""What a stored definition adds, which a model file does not carry."""


def m4i_of(types_def: dict[str, Any]) -> dict[str, dict[str, Any]]:
    """The m4i definitions of a types definition by name, without what storing them added."""
    return {
        definition["name"]: {key: value for key, value in definition.items() if key not in STORED}
        for kind in ("classificationDefs", "entityDefs", "relationshipDefs")
        for definition in types_def.get(kind, [])
        if definition["name"].startswith("m4i_") or definition["name"] in CLASSIFICATIONS
    }


async def loaded(*models_dirs: Path) -> TypedefStore:
    """A typedef store with the models directories loaded in order."""
    store = TypedefStore(TypeRegistry(), MemoryTypedefDocument())
    await store.load()
    for models_dir in models_dirs:
        assert (await ModelLoader(store).load(models_dir)).failed_files == []
    return store


@pytest.mark.covers("aurelius_atlas_core.model_loader.ModelLoader.load", rules=["MDD-02"])
def test__the_model_holds_the_sample_exports_m4i_types() -> None:
    """The 14 entity, 20 relationship and 5 classification types of the samples: as ``small.zip`` and
    ``sample_data.zip`` define them, and with the same attributes as the older ``only_gov_quality.zip``.
    """  # noqa: D205 - one sentence
    model = m4i_of(json.loads(MODEL.read_text(encoding="utf-8")))
    samples = {sample.name: m4i_of(_typesdef(sample)) for sample in sorted(SAMPLES.glob("*.zip"))}

    assert sorted(set().union(*samples.values())) == sorted(model)
    assert len([name for name in model if name in CLASSIFICATIONS]) == len(CLASSIFICATIONS)
    for name in ("small.zip", "sample_data.zip"):
        assert samples[name] == {found: model[found] for found in samples[name]}, name
    for found, definition in samples["only_gov_quality.zip"].items():
        assert _attributes(definition) == _attributes(model[found]), found


def _typesdef(sample: Path) -> dict[str, Any]:
    with zipfile.ZipFile(sample) as archive:
        return json.loads(archive.read("atlas-typesdef.json"))


def _attributes(definition: dict[str, Any]) -> list[tuple[str, str]]:
    return [(attribute["name"], attribute["typeName"]) for attribute in definition.get("attributeDefs", [])]


class Changes:
    """The typedef changes a store tells."""

    def __init__(self) -> None:
        self.told: list[ChangedTypeDefs] = []

    async def on_change(self, changed: ChangedTypeDefs) -> None:
        """Note a change."""
        self.told.append(changed)


@pytest.mark.covers("aurelius_atlas_core.model_loader.ModelLoader.load", rules=["MDD-01", "MDD-04"])
async def test__the_m4i_types_load_after_atlas_models_and_once(tmp_path: Path) -> None:
    """Every type resolves against Atlas's base model; a second load of the same versions changes nothing (MDL-02)."""
    base = tmp_path / "models" / "0000-Area0"
    base.mkdir(parents=True)
    shutil.copy(BUILTIN_MODELS_DIR / "0000-Area0" / "0010-base_model.json", base)
    store = await loaded(tmp_path / "models")
    registry = store.registry
    model = json.loads(MODEL.read_text(encoding="utf-8"))
    changes = Changes()
    store.change_listeners.append(changes)

    first = await ModelLoader(store).load(M4I_MODELS_DIR)
    told = len(changes.told)
    again = await ModelLoader(store).load(M4I_MODELS_DIR)
    dataset = registry.entity_type("m4i_dataset")

    assert all(registry.entity_type(d["name"]) is not None for d in model["entityDefs"])
    assert all(registry.relationship_type(d["name"]) is not None for d in model["relationshipDefs"])
    assert all(registry.classification_type(d["name"]) is not None for d in model["classificationDefs"])
    assert dataset is not None
    assert {"DataSet", "m4i_referenceable"} <= set(dataset.all_super_types)
    assert (first.failed_files, again.failed_files) == ([], [])
    assert told == 4  # the two model files and the two patch files each change the store once
    assert len(changes.told) == told


@pytest.mark.covers("aurelius_atlas_core.model_loader.ModelLoader.load", rules=["GQ-08"])
async def test__the_gov_quality_patch_lands_on_the_governance_type() -> None:
    """Patch 002 adds the vocabulary attributes to ``m4i_gov_data_quality`` and keeps its legacy fields (GQ-08)."""
    store = await loaded(BUILTIN_MODELS_DIR, M4I_MODELS_DIR)
    gov = store.registry.typedef_by_name("m4i_gov_data_quality")
    assert isinstance(gov, AtlasEntityDef)
    types_by_attribute = {attribute.name: attribute.type_name for attribute in gov.attribute_defs}

    assert types_by_attribute["dqcheckkind"] == "string"
    assert types_by_attribute["dqattribute"] == "string"
    assert types_by_attribute["dqanyOf"] == "array<string>"
    assert gov.type_version == "1.1"
    for kept in ("expression", "ruleType", "qualityDimension", "compliantMessage", "nonCompliantMessage"):
        assert kept in types_by_attribute, kept  # a stored value is never dropped (ADR 046)


@pytest.mark.covers("aurelius_atlas_core.model_loader.ModelLoader.load", rules=["MDD-04"])
async def test__a_sample_export_imports_without_creating_a_type() -> None:
    """``small.zip`` and ``sample_data.zip`` find every type they carry: the import counts none created (IMS-03)."""
    types = await loaded(BUILTIN_MODELS_DIR, M4I_MODELS_DIR)
    store = EntityStore(types.registry, MemoryEntityDocuments())

    for name in ("small.zip", "sample_data.zip"):
        content = (SAMPLES / name).read_bytes()
        result = await ImportService(store, types, EntityWriter(store, user="importer")).run(
            content, AtlasImportRequest(), "importer", "h", "ip"
        )
        created = {key: count for key, count in (result.metrics or {}).items() if key.startswith("typedef:") and count}

        assert result.operation_status.value == "SUCCESS", name
        assert created == {}, name
