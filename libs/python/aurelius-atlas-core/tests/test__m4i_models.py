"""The m4i data dictionary types, loaded after Atlas's models (MDD-01 to MDD-04, DD-362), on the in-memory document.

The model file is the data dictionary group of ``m4i_atlas_core`` (54d9e04): its entity, relationship and
classification definitions as the sample exports in ``data/atlas-sample/`` carry them, without what a stored
definition adds.
"""

import asyncio
import json
import re
import shutil
import zipfile
from functools import cache
from pathlib import Path
from typing import Any

import pytest
from aurelius_atlas_core.entity_store import EntityStore
from aurelius_atlas_core.import_service import ImportService
from aurelius_atlas_core.import_writer import ImportWriter
from aurelius_atlas_core.model_loader import BUILTIN_MODELS_DIR, M4I_MODELS_DIR, ModelLoader
from aurelius_atlas_core.testing.memory import MemoryEntityDocuments, MemoryTypedefDocument
from aurelius_atlas_core.typedef_change_listener import ChangedTypeDefs
from aurelius_atlas_core.typedef_store import TypedefStore
from aurelius_atlas_model.impexp import AtlasImportRequest
from aurelius_atlas_model.typedef import (
    AtlasEntityDef,
    AtlasRelationshipDef,
    AtlasStructDef,
    TypeCategory,
)
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
    """The 13 entity, 19 relationship and 5 classification types of the samples: as ``small.zip`` and
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


@pytest.mark.covers(
    "aurelius_atlas_core.model_loader.ModelLoader.load",
    "aurelius_atlas_core.zip_source.ZipSource.types_def",
    rules=["MDD-04", "IMS-03", "MMS-06"],
)
async def test__a_sample_export_imports_without_creating_a_type() -> None:
    """``small.zip`` and ``sample_data.zip`` find every type they carry and bring no new type (IMS-03, MMS-06).

    The ``atlas-typesdef.json`` of a sample names types outside the metamodel, so the import would
    create them (DD-718). The bootstrap holds no domain type before the import, and holds none after it.
    """
    types = await loaded(BUILTIN_MODELS_DIR, M4I_MODELS_DIR)
    store = EntityStore(types.registry, MemoryEntityDocuments())

    for name in ("small.zip", "sample_data.zip"):
        assert types.registry.typedef_by_name("hive_table") is None, name
        content = (SAMPLES / name).read_bytes()
        result = await ImportService(store, types, ImportWriter(store, user="importer")).run(
            content, AtlasImportRequest(), "importer", "h", "ip"
        )
        created = {key: count for key, count in (result.metrics or {}).items() if key.startswith("typedef:") and count}

        assert result.operation_status.value == "SUCCESS", name
        assert created == {}, name
        assert types.registry.typedef_by_name("hive_table") is None, name


# The nine hierarchy relationships: the child's end, its attribute and the child's type (HCA-01, HCA-02, HCA-08).
HIERARCHIES: dict[str, tuple[str, str, str]] = {
    "m4i_data_entity_assignment": ("endDef2", "dataDomain", "m4i_data_entity"),
    "m4i_parent_entity_assignment": ("endDef1", "parentEntity", "m4i_data_entity"),
    "m4i_data_entity_attribute_assignment": ("endDef2", "dataEntity", "m4i_data_attribute"),
    "m4i_field_assignment": ("endDef2", "datasets", "m4i_field"),
    "m4i_field_parent_assignment": ("endDef1", "parentField", "m4i_field"),
    "m4i_system_parent_assignment": ("endDef1", "parentSystem", "m4i_system"),
    "m4i_system_process_assignment": ("endDef2", "system", "m4i_generic_process"),
    "m4i_dataset_assignment": ("endDef1", "collections", "m4i_dataset"),
    "m4i_dataset_parent_assignment": ("endDef1", "parentDataset", "m4i_dataset"),
}


@pytest.mark.covers("aurelius_atlas_core.model_loader.ModelLoader.load", rules=["HCA-01", "HCA-02", "DCP-02"])
def test__every_hierarchy_child_end_is_single_and_holds_no_mirrored_attribute() -> None:
    """The dictionary names SINGLE on the child end, keeps SET on the parent end, and declares no mirrored
    attribute on the child entity (HCA-01, HCA-02, DCP-02).
    """  # noqa: D205 - one sentence
    model = json.loads(MODEL.read_text(encoding="utf-8"))
    relationships = {definition["name"]: definition for definition in model["relationshipDefs"]}
    entities = {definition["name"]: definition for definition in model["entityDefs"]}

    for name, (end, attribute, child) in HIERARCHIES.items():
        other = "endDef2" if end == "endDef1" else "endDef1"
        definition = relationships[name]
        child_attributes = [a["name"] for a in entities[child]["attributeDefs"]]

        assert (definition[end]["name"], definition[end]["cardinality"]) == (attribute, "SINGLE"), name
        assert definition[other]["cardinality"] == "SET", name
        assert definition[end]["type"] == child, name
        assert child_attributes, name
        assert attribute not in child_attributes, name  # no mirrored attribute (HCA-02)


# The six child ends that name a parent group, with the group each belongs to (PME-04, DCP-01).
PARENT_GROUPS = {
    "m4i_data_entity_assignment": ("endDef2", "dataDomain", "m4i_data_entity_parent"),
    "m4i_parent_entity_assignment": ("endDef1", "parentEntity", "m4i_data_entity_parent"),
    "m4i_field_assignment": ("endDef2", "datasets", "m4i_field_parent"),
    "m4i_field_parent_assignment": ("endDef1", "parentField", "m4i_field_parent"),
    "m4i_dataset_assignment": ("endDef1", "collections", "m4i_dataset_parent"),
    "m4i_dataset_parent_assignment": ("endDef1", "parentDataset", "m4i_dataset_parent"),
}


@pytest.mark.covers("aurelius_atlas_core.model_loader.ModelLoader.load", rules=["PME-04", "DCP-01"])
def test__the_parent_choice_is_named_on_the_child_ends_of_the_dictionary() -> None:
    """The six ends of the three parent choices carry one group each, and only their definitions go to ``1.2``
    (PME-04, DCP-01).
    """  # noqa: D205 - one sentence
    model = json.loads(MODEL.read_text(encoding="utf-8"))
    relationships = {definition["name"]: definition for definition in model["relationshipDefs"]}

    for name, (end, attribute, group) in PARENT_GROUPS.items():
        definition = relationships[name]
        assert definition[end]["name"] == attribute, name
        assert definition[end]["constraints"] == [{"type": "mutuallyExclusive", "params": {"group": group}}], name
        assert definition["typeVersion"] == "1.2", name

    grouped = {name for name, (_end, _attribute, _group) in PARENT_GROUPS.items()}
    assert sorted(
        name for name, definition in relationships.items() if definition.get("typeVersion") == "1.2"
    ) == sorted(grouped)


@pytest.mark.covers("aurelius_atlas_core.zip_source.ZipSource.types_def", rules=["PME-04", "DCP-01"])
def test__every_bundle_carries_the_parent_groups_of_the_model() -> None:
    """Each bundle's typedef file answers the same constraints and type version as the model (PME-04, DCP-01)."""
    for sample in sorted(SAMPLES.glob("*.zip")):
        types = m4i_of(_typesdef(sample))
        for name, (end, _attribute, group) in PARENT_GROUPS.items():
            definition = types[name]
            assert definition[end]["constraints"] == [{"type": "mutuallyExclusive", "params": {"group": group}}], (
                sample.name,
                name,
            )
            assert definition["typeVersion"] == "1.2", (sample.name, name)


@pytest.mark.covers("aurelius_atlas_core.zip_source.ZipSource.types_def", rules=["HCA-08", "DCP-07"])
def test__every_bundle_holds_at_most_one_value_per_hierarchy_child() -> None:
    """Each bundle keeps the model's child ends, and every entity holds at most one value per child attribute
    (HCA-08, DCP-07).
    """  # noqa: D205 - one sentence
    for sample in sorted(SAMPLES.glob("*.zip")):
        children: dict[str, list[str]] = {}
        for _end, attribute, child in HIERARCHIES.values():
            children.setdefault(child, []).append(attribute)
        with zipfile.ZipFile(sample) as archive:
            types = m4i_of(_typesdef(sample))
            for name, (end, _attribute, _child) in HIERARCHIES.items():
                assert types[name][end]["cardinality"] == "SINGLE", (sample.name, name)
            for entry in archive.namelist():
                if not entry.endswith(".json") or entry.startswith("atlas-"):
                    continue
                entity = json.loads(archive.read(entry)).get("entity")
                if not entity:
                    continue
                for attribute in children.get(entity["typeName"], []):
                    assert (entity.get("attributes") or {}).get(attribute) is None, (sample.name, entry, attribute)
                    value = (entity.get("relationshipAttributes") or {}).get(attribute)
                    assert not isinstance(value, list), (sample.name, entry, attribute)


def _guids_of(value: object) -> list[str]:
    """The guids a relationship attribute value holds, read from a single object or from a list."""
    items = value if isinstance(value, list) else [] if value is None else [value]
    guids: list[str] = []
    for item in items:
        if isinstance(item, str):
            guids.append(item)
        elif isinstance(item, dict):
            guids.append(str(item["guid"]))
    return guids


@pytest.mark.covers("aurelius_atlas_core.zip_source.ZipSource.types_def", rules=["HCA-08", "DCP-07", "PME-04"])
def test__every_bundle_holds_each_child_under_one_parent_of_its_choice() -> None:
    """Each child of a bundle answers one parent, counting its own value and its parents' listings together
    (HCA-08, DCP-07, PME-04).

    A child names its parent from its own end, and a parent lists its children from its side. The two views of
    the same edge must not disagree, because an import writes both sides of the edge it reads (RPS-08) and the
    store then holds the child under two parents. 18.5's first scan of the corpus found two datasets listed by
    a parent their own ``parentDataset`` did not name, which the corpus no longer does (DD-766).
    """  # noqa: D205 - one sentence
    for sample in sorted(SAMPLES.glob("*.zip")):
        types = m4i_of(_typesdef(sample))
        groups: dict[str, list[tuple[str, str, str, str]]] = {}
        for name, (child_end, _attribute, group) in PARENT_GROUPS.items():
            parent_end = "endDef2" if child_end == "endDef1" else "endDef1"
            definition = types[name]
            groups.setdefault(group, []).append(
                (
                    definition[child_end]["name"],
                    definition[child_end]["type"],
                    definition[parent_end]["name"],
                    definition[parent_end]["type"],
                )
            )

        with zipfile.ZipFile(sample) as archive:
            payload = [
                json.loads(archive.read(entry))
                for entry in archive.namelist()
                if entry.endswith(".json") and not entry.startswith("atlas-")
            ]
        entities = [document["entity"] for document in payload if document.get("entity")]

        for group, ends in groups.items():
            parents: dict[str, set[str]] = {}
            for entity in entities:
                held = entity.get("relationshipAttributes") or {}
                for child_attribute, child_type, parent_attribute, parent_type in ends:
                    if entity["typeName"] == child_type:
                        parents.setdefault(entity["guid"], set()).update(_guids_of(held.get(child_attribute)))
                    if entity["typeName"] == parent_type:
                        for child in _guids_of(held.get(parent_attribute)):
                            parents.setdefault(child, set()).add(entity["guid"])
            assert {child: sorted(seen) for child, seen in parents.items() if len(seen) > 1} == {}, (
                sample.name,
                group,
            )


# The rule of the sample corpus that measures a SINGLE parent, and the sentences it must hold (PME-11).
PARENT_RULE_SENTENCES = {
    "name": "Data entity belongs to a data domain or parent entity",
    "ruleDescription": "A data entity should belong to a data domain or parent entity",
    "compliantMessage": "This data entity has a data domain or parent entity",
    "nonCompliantMessage": "This data entity should have a data domain or parent entity",
}


@pytest.mark.covers("aurelius_atlas_core.zip_source.ZipSource.types_def", rules=["PME-11"])
def test__every_bundle_words_its_single_parent_rule_for_one_parent_of_each_kind() -> None:
    """Each bundle's data-entity parent rule states one data domain or parent entity (PME-11, DD-752).

    18.2 made both parent ends `SINGLE`, so the rule no longer counts a set and must not read "at least
    one". The rule is read from each bundle, because the banner prints what the corpus stores (GQ-06).
    The `--source` companion of `sample_data.zip` states the same three sentences, so a rule page names
    one thing. `small.zip` ships no governance rule, so only the two rules bundles carry it.
    """
    holding = 0
    for sample in sorted(SAMPLES.glob("*.zip")):
        with zipfile.ZipFile(sample) as archive:
            rules: dict[str, dict[str, Any]] = {}
            for entry in archive.namelist():
                if not entry.endswith(".json") or entry.startswith("atlas-"):
                    continue
                entity = json.loads(archive.read(entry)).get("entity")
                if not entity or entity["typeName"] != "m4i_gov_data_quality":
                    continue
                attributes = entity["attributes"]
                qualified_name = str(attributes.get("qualifiedName") or "")
                if qualified_name.startswith("m4i_data_entity--dataDomain"):
                    rules[qualified_name] = attributes

            if "m4i_data_entity--dataDomain" not in rules:
                continue
            holding += 1
            rule = rules["m4i_data_entity--dataDomain"]
            assert rule["expression"] == "length('dataDomain', 1) | length('parentEntity', 1)", sample.name
            for attribute, sentence in PARENT_RULE_SENTENCES.items():
                assert rule[attribute] == sentence, (sample.name, attribute)

            if sample.name == "sample_data.zip":
                companion = rules["m4i_data_entity--dataDomain--source"]
                for attribute in ("ruleDescription", "compliantMessage", "nonCompliantMessage"):
                    assert companion[attribute] == PARENT_RULE_SENTENCES[attribute], attribute

    assert holding == 2  # both rules bundles carry it


# A bare camelCase identifier (no m4i_ prefix glued to it) reads as developer-speak in a sentence.
_BARE_CAMEL = re.compile(r"\b[a-z]+(?:[A-Z][a-z0-9]*)+\b")
# The three fields the banner and the rule page print verbatim (GQ-06).
_RULE_PROSE = ("ruleDescription", "compliantMessage", "nonCompliantMessage")


@pytest.mark.covers("aurelius_atlas_core.zip_source.ZipSource.types_def", rules=["PME-12"])
def test__no_bundle_words_its_governance_rules_in_camel_case() -> None:
    """Every governance rule sentence in every bundle is plain English (PME-12, DD-753).

    The banner prints what the rule stores (GQ-06), so a field name left in camel case would show a reader
    ``parentDataset`` instead of "parent dataset". A snake-case Atlas type name a relation sentence quotes
    (``m4i_indexPattern``) stays: it names a type, not a field, and carries no separate word to split.
    """
    for sample in sorted(SAMPLES.glob("*.zip")):
        with zipfile.ZipFile(sample) as archive:
            for entry in archive.namelist():
                if not entry.endswith(".json") or entry.startswith("atlas-"):
                    continue
                entity = json.loads(archive.read(entry)).get("entity")
                if not entity or entity["typeName"] != "m4i_gov_data_quality":
                    continue
                attributes = entity["attributes"]
                for field in _RULE_PROSE:
                    sentence = str(attributes.get(field) or "")
                    leaked = _BARE_CAMEL.findall(sentence)
                    assert not leaked, (sample.name, entry, field, sentence, leaked)


# The check functions a governance rule calls name one attribute of the type it governs.
_RULE_ATTRIBUTE = re.compile(r"\b(?:completeness|length|uniqueness)\(\s*'([^']+)'")
# A relation rule maps one relationship definition to the type the author must reach.
_RELATION_BLOCK = re.compile(r"conditional_value\([^,]+,[^,]+,\s*\{([^}]*)\}")
_RELATION_ENTRY = re.compile(r"'([^']+)'\s*:\s*'([^']+)'")


@cache
def m4i_registry() -> TypeRegistry:
    """The loaded typesystem (Atlas's models then the m4i dictionary) the governance rules answer to."""
    return asyncio.run(loaded(BUILTIN_MODELS_DIR, M4I_MODELS_DIR)).registry


def type_names(registry: TypeRegistry, kind: TypeCategory) -> set[str]:
    """The names of every definition of one kind."""
    return {name for definition in registry.typedefs(kind) if (name := definition.name)}


def answerable_names(registry: TypeRegistry, rule_type: str) -> set[str]:
    """Every attribute a type answers to, from its own definitions, its supertypes, and its relationship ends."""
    supertypes: set[str] = set()
    pending = [rule_type]
    while pending:
        current = pending.pop()
        if current in supertypes:
            continue
        supertypes.add(current)
        definition = registry.typedef_by_name(current)
        if isinstance(definition, AtlasEntityDef):
            pending.extend(definition.super_types)
    owned = {
        attribute.name
        for name in supertypes
        if isinstance(definition := registry.typedef_by_name(name), AtlasStructDef)
        for attribute in definition.attribute_defs
        if attribute.name
    }
    owned |= {
        end.name
        for definition in registry.typedefs(TypeCategory.RELATIONSHIP)
        if isinstance(definition, AtlasRelationshipDef)
        for end in (definition.end_def1, definition.end_def2)
        if end is not None and end.name and end.type in supertypes
    }
    return {name for name in owned if name}


def missing_rule_names(registry: TypeRegistry, rule_type: str, expression: str) -> list[str]:
    """The names ``expression`` needs that the model does not define; empty when the model answers it."""
    entities = type_names(registry, TypeCategory.ENTITY)
    if rule_type not in entities:
        return [f"type {rule_type}"]
    owned = answerable_names(registry, rule_type)
    relationships = type_names(registry, TypeCategory.RELATIONSHIP)
    missing = [f"attribute {name}" for name in _RULE_ATTRIBUTE.findall(expression) if name not in owned]
    for block in _RELATION_BLOCK.findall(expression):
        for key, value in _RELATION_ENTRY.findall(block):
            if key not in relationships:
                missing.append(f"relationship {key}")
            if value not in entities:
                missing.append(f"type {value}")
    return missing


@pytest.mark.covers("aurelius_atlas_core.model_loader.ModelLoader.load", rules=["PME-13"])
def test__every_bundle_ships_only_governance_rules_the_model_can_answer() -> None:
    """Every governance rule of every bundle names only a type, attribute or relationship the model defines.

    PME-13, DD-754. A rule over a name the model lacks is false on every entity of its type forever, so 18.3
    drops its 29 records from the corpus (DV-185). The attribute a check names is one the subject type owns
    or gains from a relationship end. The key of a relation rule names a relationship definition, and its
    value a type. ``small.zip`` ships no governance rule, so only the two rules bundles carry it.
    """
    registry = m4i_registry()

    for sample in sorted(SAMPLES.glob("*.zip")):
        with zipfile.ZipFile(sample) as archive:
            for entry in archive.namelist():
                if not entry.endswith(".json") or entry.startswith("atlas-"):
                    continue
                entity = json.loads(archive.read(entry)).get("entity")
                if not entity or entity["typeName"] != "m4i_gov_data_quality":
                    continue
                attributes = entity["attributes"]
                qualified_name = str(attributes.get("qualifiedName") or "")
                rule_type = qualified_name.split("--", maxsplit=1)[0]
                missing = missing_rule_names(registry, rule_type, str(attributes.get("expression") or ""))
                assert not missing, (sample.name, qualified_name, missing)
