"""Loading the built-in models and applying their typedef patches (MDL-01 to MDL-14).

Read from ``AtlasTypeDefStoreInitializer`` of Apache Atlas 2.4.0: ``loadBootstrapTypeDefs``, ``loadModelsInFolder``,
``applyTypePatches`` and its nine ``PatchHandler``s; and from the patch files of ``addons/models``.
"""

import json
from pathlib import Path
from typing import Any

import pytest
from aurelius_atlas_core.model_loader import (
    BUILTIN_MODELS_DIR,
    PATCH_HANDLERS,
    ModelLoader,
    PatchDataError,
    TypedefPatch,
    add_attribute,
    add_mandatory_attribute,
    add_super_types,
    is_patch_applicable,
    load_plan,
    remove_legacy_ref_attributes,
    set_service_type,
    sorted_entries,
    update_attribute,
    update_attribute_metadata,
    update_enum_def,
    update_typedef_options,
)
from aurelius_atlas_core.testing.memory import MemoryTypedefDocument
from aurelius_atlas_core.typedef_store import TypedefStore, types_def_of
from aurelius_atlas_model.errors import AtlasError, AtlasErrorCode
from aurelius_atlas_model.patches import AtlasPatch, PatchStatus
from aurelius_atlas_model.typedef import (
    AtlasAttributeDef,
    AtlasBaseTypeDef,
    AtlasBusinessMetadataDef,
    AtlasClassificationDef,
    AtlasEntityDef,
    AtlasEnumDef,
    AtlasEnumElementDef,
    AtlasRelationshipDef,
    AtlasRelationshipEndDef,
    AtlasStructDef,
    Cardinality,
    IndexType,
    RelationshipCategory,
    TypeCategory,
)
from aurelius_atlas_typesystem.registry import TypeRegistry


@pytest.fixture
def document() -> MemoryTypedefDocument:
    """An empty in-memory document."""
    return MemoryTypedefDocument()


@pytest.fixture
async def store(document: MemoryTypedefDocument) -> TypedefStore:
    """A loaded store on ``document``."""
    store = TypedefStore(TypeRegistry(), document)
    await store.load()
    return store


def attr(name: str, type_name: str = "string", **fields: object) -> AtlasAttributeDef:
    """An optional attribute definition, unless ``fields`` say otherwise."""
    return AtlasAttributeDef.model_validate({"name": name, "type_name": type_name, "is_optional": True, **fields})


def write_json(path: Path, content: object) -> Path:
    """Write ``content`` as JSON at ``path``, creating its directory."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(content))
    return path


def model(*typedefs: AtlasBaseTypeDef) -> dict[str, Any]:
    """A model file's JSON."""
    return types_def_of(typedefs).to_json()


def patches(*patch_list: dict[str, Any]) -> dict[str, Any]:
    """A patch file's JSON."""
    return {"patches": list(patch_list)}


def patch(action: str, type_name: str = "t", **fields: object) -> TypedefPatch:
    """A patch from ``1.0`` to ``1.1``."""
    return TypedefPatch.model_validate(
        {
            "id": f"{action}-{type_name}",
            "action": action,
            "typeName": type_name,
            "applyToVersion": "1.0",
            "updateToVersion": "1.1",
            **fields,
        }
    )


async def apply(store: TypedefStore, typedef_patch: TypedefPatch) -> PatchStatus | None:
    """Apply ``typedef_patch`` with its action's handler."""
    handler = PATCH_HANDLERS[str(typedef_patch.action)]
    return await store.apply_patch(typedef_patch.record(), lambda registry: handler(typedef_patch, registry))


def entity(name: str = "t", *attributes: AtlasAttributeDef, version: str = "1.0") -> AtlasEntityDef:
    """An entity definition at ``version``."""
    return AtlasEntityDef(name=name, attribute_defs=list(attributes), type_version=version)


def stored[T: AtlasBaseTypeDef](store: TypedefStore, name: str, kind: type[T]) -> T:
    """The registered definition named ``name``."""
    typedef = store.registry.typedef_by_name(name)
    assert isinstance(typedef, kind)
    return typedef


def handler_error(handler: Any, typedef_patch: TypedefPatch, store: TypedefStore) -> AtlasError:  # noqa: ANN401
    """The ``AtlasError`` a handler raises."""
    with pytest.raises(AtlasError) as raised:
        handler(typedef_patch, store.registry)
    return raised.value


@pytest.mark.covers(
    "aurelius_atlas_core.model_loader.ModelLoader.load",
    "aurelius_atlas_core.model_loader.load_plan",
    "aurelius_atlas_core.model_loader.sorted_entries",
    rules=["MDL-01"],
)
async def test__folders_then_the_top_folder_each_files_then_patches(store: TypedefStore, tmp_path: Path) -> None:
    """``loadBootstrapTypeDefs``: sub-folders by name, then the top folder; each folder's files, then its patches.

    ``10`` sorts before ``9``, and a folder's patches run before the next folder's files.
    """
    write_json(tmp_path / "9-second" / "1.json", model(entity("child").model_copy(update={"super_types": ["base"]})))
    write_json(tmp_path / "10-first" / "1.json", model(entity("base")))
    write_json(tmp_path / "10-first" / "patches" / "1.json", patches(patch("SET_SERVICE_TYPE", "base").to_json()))
    write_json(tmp_path / "9-second" / "patches" / "1.json", patches(patch("SET_SERVICE_TYPE", "child").to_json()))
    write_json(tmp_path / "top.json", model(entity("top", attr("child", "child"))))
    write_json(tmp_path / "patches" / "1.json", patches(patch("SET_SERVICE_TYPE", "top").to_json()))
    (tmp_path / "empty").mkdir()

    result = await ModelLoader(store).load(tmp_path)

    assert [(path.relative_to(tmp_path).as_posix(), is_patch) for path, is_patch in load_plan(tmp_path)] == [
        ("10-first/1.json", False),
        ("10-first/patches/1.json", True),
        ("9-second/1.json", False),
        ("9-second/patches/1.json", True),
        ("top.json", False),
        ("patches/1.json", True),
    ]
    assert [entry.name for entry in sorted_entries(tmp_path)] == [
        "10-first",
        "9-second",
        "empty",
        "patches",
        "top.json",
    ]
    assert list(result.patches) == ["SET_SERVICE_TYPE-base", "SET_SERVICE_TYPE-child", "SET_SERVICE_TYPE-top"]
    assert set(result.patches.values()) == {PatchStatus.APPLIED}
    assert result.failed_files == []
    assert stored(store, "top", AtlasEntityDef).type_version == "1.1"


@pytest.mark.covers(rules=["MDL-01"])
async def test__a_missing_directory_loads_nothing(store: TypedefStore, document: MemoryTypedefDocument) -> None:
    """``Types directory ... does not exist``: no error, no write."""
    result = await ModelLoader(store).load(Path("/does/not/exist"))

    assert (result.failed_files, result.patches, document.writes) == ([], {}, 0)


@pytest.mark.covers(rules=["MDL-01"])
async def test__a_folder_with_only_patches_applies_them(store: TypedefStore, tmp_path: Path) -> None:
    """A folder whose only entry is ``patches`` is not empty, so its patches are applied."""
    write_json(tmp_path / "a" / "1.json", model(entity()))
    write_json(tmp_path / "b" / "patches" / "1.json", patches(patch("SET_SERVICE_TYPE").to_json()))

    result = await ModelLoader(store).load(tmp_path)

    assert result.patches == {"SET_SERVICE_TYPE-t": PatchStatus.APPLIED}


@pytest.mark.covers(rules=["MDL-02", "MDL-04"])
async def test__a_failing_model_file_is_skipped_and_loading_goes_on(store: TypedefStore, tmp_path: Path) -> None:
    """``error while registering types in file``: unreadable JSON and an unknown type each skip their file only."""
    (tmp_path / "1-broken.json").write_text("{not json")
    write_json(tmp_path / "2-unknown.json", model(entity("u", attr("a", "missing"))))
    write_json(tmp_path / "3-empty.json", {})
    write_json(tmp_path / "4-good.json", model(entity("good")))

    result = await ModelLoader(store).load(tmp_path)

    assert [path.name for path in result.failed_files] == ["1-broken.json", "2-unknown.json"]
    assert store.registry.entity_type("good") is not None
    assert store.registry.entity_type("u") is None


@pytest.mark.covers(rules=["MDL-02"])
async def test__loading_again_changes_only_newer_versions(
    store: TypedefStore, document: MemoryTypedefDocument, tmp_path: Path
) -> None:
    """The second start finds every type registered: only a greater ``typeVersion`` updates it."""
    path = write_json(tmp_path / "1.json", model(entity("t", attr("a"))))
    await ModelLoader(store).load(tmp_path)
    writes = document.writes

    await ModelLoader(store).load(tmp_path)
    unchanged = document.writes
    write_json(path, model(entity("t", attr("b"), version="1.1")))
    await ModelLoader(store).load(tmp_path)

    assert unchanged == writes
    assert document.writes == writes + 1
    assert [a.name for a in stored(store, "t", AtlasEntityDef).attribute_defs] == ["b", "a"]


@pytest.mark.covers("aurelius_atlas_core.model_loader.TypedefPatch.record", rules=["MDL-05"])
async def test__patches_run_once_unknown_actions_are_skipped(
    store: TypedefStore, document: MemoryTypedefDocument, tmp_path: Path
) -> None:
    """``patchRegistry.isApplicable``: a recorded patch is not applied again.

    An unknown action has no record, unknown fields are ignored, and a patch without an id is applied every time
    (DV-08).
    """
    write_json(tmp_path / "1.json", model(entity()))
    write_json(
        tmp_path / "patches" / "1.json",
        patches(
            {"id": "unknown", "action": "NO_SUCH_ACTION", "typeName": "t"},
            {**patch("SET_SERVICE_TYPE").to_json(), "extra": "ignored"},
            {
                **patch("UPDATE_TYPEDEF_OPTIONS", typeDefOptions={"k": "v"}).to_json(),
                "id": None,
                "applyToVersion": "1.1",
            },
        ),
    )

    first = await ModelLoader(store).load(tmp_path)
    writes = document.writes
    second = await ModelLoader(store).load(tmp_path)

    assert first.patches == {"SET_SERVICE_TYPE-t": PatchStatus.APPLIED}
    assert second.patches == {"SET_SERVICE_TYPE-t": None}
    assert document.writes == writes + 1
    assert stored(store, "t", AtlasEntityDef).options == {"k": "v"}
    assert [AtlasPatch.model_validate(record).id for record in document.patches] == ["SET_SERVICE_TYPE-t"]
    assert patch("SET_SERVICE_TYPE").record() == AtlasPatch(id="SET_SERVICE_TYPE-t", action="SET_SERVICE_TYPE")


@pytest.mark.covers(rules=["MDL-06"])
async def test__an_error_other_than_atlas_s_ends_the_patch_file(store: TypedefStore, tmp_path: Path) -> None:
    """``Failed to apply patches in file``: the failing patch is not recorded, and the rest of its file not run.

    The next file is applied.
    """
    write_json(tmp_path / "1.json", model(entity("t", attr("a"))))
    write_json(
        tmp_path / "patches" / "1.json",
        patches(
            patch("SET_SERVICE_TYPE", serviceType="svc").to_json(),
            patch(
                "UPDATE_ATTRIBUTE_METADATA", attributeName="a", params={"nonsense": 1}, applyToVersion="1.1"
            ).to_json(),
            patch("UPDATE_TYPEDEF_OPTIONS", typeDefOptions={"k": "v"}, applyToVersion="1.1").to_json(),
        ),
    )
    write_json(tmp_path / "patches" / "2.json", patches(patch("ADD_SUPER_TYPES", superTypes=[]).to_json()))
    (tmp_path / "patches" / "3.json").write_text("{not json")

    result = await ModelLoader(store).load(tmp_path)

    assert result.patches == {"SET_SERVICE_TYPE-t": PatchStatus.APPLIED, "ADD_SUPER_TYPES-t": PatchStatus.SKIPPED}
    assert [path.name for path in result.stopped_patch_files] == ["1.json", "3.json"]
    assert stored(store, "t", AtlasEntityDef).options is None


@pytest.mark.covers(rules=["MDL-06"])
async def test__a_patch_that_cannot_be_recorded_is_reported_failed(
    store: TypedefStore, document: MemoryTypedefDocument, tmp_path: Path
) -> None:
    """Losing the write twice (``FAILED_TO_OBTAIN_TYPE_UPDATE_LOCK``) fails the patch unrecorded; loading goes on."""
    write_json(tmp_path / "1.json", model(entity()))
    write_json(tmp_path / "patches" / "1.json", patches(patch("SET_SERVICE_TYPE").to_json()))
    loader = ModelLoader(store)
    await loader.load(tmp_path.parent / "nothing")
    await store.create_update_types_def(types_def_of([entity()]))
    document.conflicts = 2

    result = await loader.load(tmp_path)

    assert result.patches == {"SET_SERVICE_TYPE-t": PatchStatus.FAILED}
    assert document.patches == []


@pytest.mark.covers("aurelius_atlas_core.model_loader.is_patch_applicable", rules=["MDL-07"])
@pytest.mark.parametrize(
    ("current", "apply_to", "applicable"),
    [
        (None, "1.0", True),
        ("1.0", "1.0", True),
        ("v1.0", "V1.0", True),
        ("1.0.3", "1.0", True),
        ("1.1", "1.0", False),
        ("1.01", "1.0", False),
        ("null.1", None, True),
        ("1.0", None, False),
    ],
)
def test__a_patch_applies_to_its_version_and_below_it(
    current: str | None, apply_to: str | None, *, applicable: bool
) -> None:
    """``isPatchApplicable``: equal ignoring case, or starting with ``applyToVersion + "."``, Java's ``null`` too."""
    typedef = AtlasEntityDef(name="t", type_version=current)
    typedef_patch = TypedefPatch(action="SET_SERVICE_TYPE", type_name="t", apply_to_version=apply_to)

    assert is_patch_applicable(typedef_patch, typedef) is applicable


@pytest.mark.covers(rules=["MDL-07"])
@pytest.mark.parametrize("action", sorted(PATCH_HANDLERS))
async def test__every_action_fails_on_an_unknown_type(store: TypedefStore, action: str) -> None:
    """``PATCH_FOR_UNKNOWN_TYPE`` (action, type name), before anything else."""
    error = handler_error(PATCH_HANDLERS[action], patch(action, "missing"), store)

    assert (error.code, error.params) == (AtlasErrorCode.PATCH_FOR_UNKNOWN_TYPE, (action, "missing"))


@pytest.mark.covers(rules=["MDL-07"])
@pytest.mark.parametrize(
    "action",
    [
        "UPDATE_ENUMDEF",
        "ADD_ATTRIBUTE",
        "UPDATE_ATTRIBUTE",
        "ADD_MANDATORY_ATTRIBUTE",
        "REMOVE_LEGACY_REF_ATTRIBUTES",
        "SET_SERVICE_TYPE",
        "UPDATE_ATTRIBUTE_METADATA",
    ],
)
async def test__a_patch_for_another_version_is_skipped(store: TypedefStore, action: str) -> None:
    """``patch skipped``: the type is at ``1.1``, the patch applies to ``1.0``."""
    await store.create_types_def(types_def_of([entity(version="1.1")]))

    assert await apply(store, patch(action, attributeDefs=[], elementDefs=[])) is PatchStatus.SKIPPED
    assert stored(store, "t", AtlasEntityDef).type_version == "1.1"


@pytest.mark.covers("aurelius_atlas_core.model_loader.update_enum_def", rules=["MDL-08"])
async def test__update_enumdef_adds_elements(store: TypedefStore) -> None:
    """``UpdateEnumDefPatchHandler``: elements added at the end, one with the same value replaced; enums only."""
    elements = [AtlasEnumElementDef(value="A", ordinal=1), AtlasEnumElementDef(value="B", ordinal=2)]
    await store.create_types_def(
        types_def_of([AtlasEnumDef(name="e", element_defs=elements, type_version="1.0"), entity()])
    )
    new = [{"value": "a", "ordinal": 7}, {"value": "C", "ordinal": 3}]

    status = await apply(store, patch("UPDATE_ENUMDEF", "e", elementDefs=new))
    error = handler_error(update_enum_def, patch("UPDATE_ENUMDEF", elementDefs=new), store)

    assert status is PatchStatus.APPLIED
    enum = stored(store, "e", AtlasEnumDef)
    assert [(e.value, e.ordinal) for e in enum.element_defs] == [("B", 2), ("a", 7), ("C", 3)]
    assert enum.type_version == "1.1"
    assert (error.code, error.params) == (
        AtlasErrorCode.PATCH_NOT_APPLICABLE_FOR_TYPE,
        ("UPDATE_ENUMDEF", "AtlasEntityDef"),
    )


def relationship(name: str = "r", *, legacy1: bool = False, legacy2: bool = False) -> AtlasRelationshipDef:
    """A relationship between ``a.toB`` and ``b.toA`` at ``1.0``."""
    return AtlasRelationshipDef(
        name=name,
        type_version="1.0",
        relationship_category=RelationshipCategory.ASSOCIATION,
        relationship_label="label",
        end_def1=AtlasRelationshipEndDef(
            type="a", name="toB", cardinality=Cardinality.SINGLE, is_legacy_attribute=legacy1
        ),
        end_def2=AtlasRelationshipEndDef(
            type="b", name="toA", cardinality=Cardinality.SINGLE, is_legacy_attribute=legacy2
        ),
    )


@pytest.mark.covers(
    "aurelius_atlas_core.model_loader.add_attribute",
    "aurelius_atlas_core.model_loader.update_attribute",
    rules=["MDL-09"],
)
async def test__add_and_update_attribute_add_attributes_to_their_kinds(store: TypedefStore) -> None:
    """``AddAttributePatchHandler`` takes relationships too, ``UpdateAttributePatchHandler`` does not.

    Neither takes business metadata, and TDS-08 still applies.
    """
    await store.create_types_def(
        types_def_of(
            [
                entity("t", attr("a", description="old")),
                entity("a"),
                entity("b"),
                relationship(),
                AtlasBusinessMetadataDef(name="bm", type_version="1.0"),
            ]
        )
    )

    on_relationship = handler_error(update_attribute, patch("UPDATE_ATTRIBUTE", "r", attributeDefs=[]), store)
    on_business = handler_error(add_attribute, patch("ADD_ATTRIBUTE", "bm", attributeDefs=[]), store)
    added = await apply(store, patch("ADD_ATTRIBUTE", "r", attributeDefs=[attr("x").to_json()]))
    updated = await apply(store, patch("UPDATE_ATTRIBUTE", attributeDefs=[attr("a", description="new").to_json()]))
    mandatory = await apply(
        store, patch("ADD_ATTRIBUTE", "a", attributeDefs=[attr("y", "int", is_optional=False).to_json()])
    )

    assert (added, updated, mandatory) == (PatchStatus.APPLIED, PatchStatus.APPLIED, PatchStatus.FAILED)
    assert [a.name for a in stored(store, "r", AtlasRelationshipDef).attribute_defs] == ["x"]
    assert [a.description for a in stored(store, "t", AtlasEntityDef).attribute_defs] == ["new"]
    assert on_relationship.params == ("UPDATE_ATTRIBUTE", "AtlasRelationshipDef")
    assert on_business.params == ("ADD_ATTRIBUTE", "AtlasBusinessMetadataDef")


@pytest.mark.covers(rules=["MDL-06", "MDL-09"])
async def test__a_patch_without_its_data_is_a_runtime_error(store: TypedefStore) -> None:
    """Java dereferences ``attributeDefs`` without a check: a ``NullPointerException``, not an Atlas error."""
    await store.create_types_def(types_def_of([entity()]))

    with pytest.raises(PatchDataError, match="attributeDefs"):
        add_attribute(patch("ADD_ATTRIBUTE"), store.registry)


@pytest.mark.covers("aurelius_atlas_core.model_loader.add_mandatory_attribute", rules=["MDL-10"])
async def test__add_mandatory_attribute_keeps_valid_mandatory_attributes(store: TypedefStore) -> None:
    """``getAttributesToAdd``: only new, mandatory, defaulted, primitive and not unique attributes are added."""
    await store.create_types_def(
        types_def_of(
            [
                entity("t", attr("have")),
                AtlasEnumDef(name="colour", element_defs=[AtlasEnumElementDef(value="R", ordinal=1)]),
            ]
        )
    )
    candidates = [
        attr("have", "int", is_optional=False, default_value="1"),
        attr("optional", "int", default_value="1"),
        attr("no_default", "int", is_optional=False),
        attr("enum", "colour", is_optional=False, default_value="R"),
        attr("unique", "int", is_optional=False, default_value="1", is_unique=True),
        attr("kept", "int", is_optional=False, default_value="0"),
    ]

    status = await apply(store, patch("ADD_MANDATORY_ATTRIBUTE", attributeDefs=[a.to_json() for a in candidates]))

    assert status is PatchStatus.APPLIED
    assert [a.name for a in stored(store, "t", AtlasEntityDef).attribute_defs] == ["have", "kept"]


@pytest.mark.covers(rules=["MDL-10"])
async def test__add_mandatory_attribute_skips_and_fails_as_atlas_does(store: TypedefStore) -> None:
    """None kept is ``SKIPPED``; an unknown attribute type is the registry's error.

    A relationship is not applicable once there is something to add; an enum cannot be cast to a struct.
    """
    await store.create_types_def(
        types_def_of(
            [
                entity("t"),
                entity("a"),
                entity("b"),
                relationship(),
                AtlasEnumDef(name="e", type_version="1.0", element_defs=[AtlasEnumElementDef(value="X", ordinal=1)]),
            ]
        )
    )
    mandatory = attr("m", "int", is_optional=False, default_value="0").to_json()

    skipped = await apply(store, patch("ADD_MANDATORY_ATTRIBUTE", attributeDefs=[attr("o", "int").to_json()]))
    unknown = handler_error(
        add_mandatory_attribute, patch("ADD_MANDATORY_ATTRIBUTE", attributeDefs=[attr("u", "nope").to_json()]), store
    )
    on_relationship = handler_error(
        add_mandatory_attribute, patch("ADD_MANDATORY_ATTRIBUTE", "r", attributeDefs=[mandatory]), store
    )

    assert skipped is PatchStatus.SKIPPED
    assert unknown.code is AtlasErrorCode.TYPE_NAME_NOT_FOUND
    assert on_relationship.params == ("ADD_MANDATORY_ATTRIBUTE", "AtlasRelationshipDef")
    with pytest.raises(PatchDataError):
        add_mandatory_attribute(patch("ADD_MANDATORY_ATTRIBUTE", "e", attributeDefs=[mandatory]), store.registry)


async def legacy_store(store: TypedefStore, *, legacy1: bool = True, legacy2: bool = False) -> None:
    """``a`` and ``b`` with the attributes a legacy relationship ``r`` replaces."""
    await store.create_types_def(
        types_def_of(
            [
                entity("a", attr("toB", "b"), attr("keep")),
                entity("b", attr("toA", "a")),
                relationship(legacy1=legacy1, legacy2=legacy2),
            ]
        )
    )


@pytest.mark.covers("aurelius_atlas_core.model_loader.remove_legacy_ref_attributes", rules=["MDL-11"])
async def test__remove_legacy_ref_attributes_moves_the_attributes_to_the_relationship(store: TypedefStore) -> None:
    """``RemoveLegacyRefAttributesPatchHandler``: one update of the relationship and both entity types.

    The label is the legacy end's qualified name, the ends' attributes are removed and the ends swapped.
    """
    await legacy_store(store)

    status = await apply(store, patch("REMOVE_LEGACY_REF_ATTRIBUTES", "r", params={"swapEnds": "TRUE"}))

    assert status is PatchStatus.APPLIED
    updated = stored(store, "r", AtlasRelationshipDef)
    assert updated.relationship_label == "__a.toB"
    assert updated.type_version == "1.1"
    assert updated.end_def1 is not None
    assert updated.end_def1.type == "b"
    assert [a.name for a in stored(store, "a", AtlasEntityDef).attribute_defs] == ["keep"]
    assert stored(store, "b", AtlasEntityDef).attribute_defs == []


@pytest.mark.covers(rules=["MDL-11"])
@pytest.mark.parametrize(
    ("legacy1", "legacy2", "params", "label"),
    [
        (False, True, {}, "__b.toA"),
        (False, False, {}, "label"),
        (True, True, {"relationshipLabel": "given"}, "given"),
        (True, False, {"relationshipLabel": ""}, "__a.toB"),
    ],
)
async def test__the_label_comes_from_the_patch_or_the_legacy_end(
    store: TypedefStore, *, legacy1: bool, legacy2: bool, params: dict[str, str], label: str
) -> None:
    """The patch's label wins unless it is empty; then the one legacy end's, else the current label."""
    await legacy_store(store, legacy1=legacy1, legacy2=legacy2)

    await apply(store, patch("REMOVE_LEGACY_REF_ATTRIBUTES", "r", params=params))

    assert stored(store, "r", AtlasRelationshipDef).relationship_label == label


@pytest.mark.covers(rules=["MDL-11"])
async def test__remove_legacy_ref_attributes_fails_and_ends_unknown_as_atlas_does(store: TypedefStore) -> None:
    """Two legacy ends need a label; a new category must be one; any other kind ends ``UNKNOWN``, unchanged."""
    await legacy_store(store, legacy1=True, legacy2=True)

    missing = handler_error(remove_legacy_ref_attributes, patch("REMOVE_LEGACY_REF_ATTRIBUTES", "r"), store)
    other_kind = await apply(store, patch("REMOVE_LEGACY_REF_ATTRIBUTES", "a"))

    assert (missing.code, missing.params) == (
        AtlasErrorCode.PATCH_MISSING_RELATIONSHIP_LABEL,
        ("REMOVE_LEGACY_REF_ATTRIBUTES", "r"),
    )
    assert other_kind is PatchStatus.UNKNOWN
    assert stored(store, "a", AtlasEntityDef).type_version == "1.0"
    with pytest.raises(PatchDataError):
        remove_legacy_ref_attributes(
            patch(
                "REMOVE_LEGACY_REF_ATTRIBUTES", "r", params={"relationshipLabel": "x", "relationshipCategory": "NOPE"}
            ),
            store.registry,
        )


@pytest.mark.covers(rules=["MDL-06", "MDL-11"])
async def test__a_legacy_end_without_its_attribute_is_a_runtime_error(store: TypedefStore) -> None:
    """``end1Type.getAttribute(...)`` is null, and its qualified name a ``NullPointerException``."""
    await store.create_types_def(types_def_of([entity("a"), entity("b"), relationship(legacy1=True)]))

    with pytest.raises(PatchDataError, match=r"a\.toB"):
        remove_legacy_ref_attributes(patch("REMOVE_LEGACY_REF_ATTRIBUTES", "r"), store.registry)


@pytest.mark.covers(rules=["MDL-11"])
async def test__a_new_category_is_set(store: TypedefStore) -> None:
    """``relationshipCategory`` replaces the category while patching, which TDS-08 otherwise refuses."""
    await store.create_types_def(
        types_def_of(
            [
                entity("a", attr("toB", "b")),
                entity("b"),
                relationship(legacy1=True).model_copy(
                    update={
                        "end_def2": AtlasRelationshipEndDef(
                            type="b", name="toA", cardinality=Cardinality.SET, is_container=True
                        ),
                        "relationship_category": RelationshipCategory.AGGREGATION,
                    }
                ),
            ]
        )
    )

    status = await apply(
        store, patch("REMOVE_LEGACY_REF_ATTRIBUTES", "r", params={"relationshipCategory": "COMPOSITION"})
    )

    assert status is PatchStatus.APPLIED
    assert stored(store, "r", AtlasRelationshipDef).relationship_category is RelationshipCategory.COMPOSITION


@pytest.mark.covers(
    "aurelius_atlas_core.model_loader.update_typedef_options",
    "aurelius_atlas_core.model_loader.set_service_type",
    rules=["MDL-12"],
)
async def test__options_merge_and_the_service_type_is_set(store: TypedefStore) -> None:
    """``UpdateTypeDefOptionsPatchHandler`` merges options; ``SetServiceTypePatchHandler`` sets the service type.

    The patch's options win, and are required before the version check. Without a service type the stored one
    stays. Both take any kind.
    """
    await store.create_types_def(
        types_def_of(
            [
                entity().model_copy(update={"options": {"keep": "1", "change": "old"}, "service_type": "old"}),
                AtlasEnumDef(name="e", type_version="1.0", element_defs=[AtlasEnumElementDef(value="X", ordinal=1)]),
            ]
        )
    )

    options = await apply(store, patch("UPDATE_TYPEDEF_OPTIONS", typeDefOptions={"change": "new", "add": "2"}))
    service = await apply(store, patch("SET_SERVICE_TYPE", "e", serviceType="svc"))
    cleared = await apply(store, patch("SET_SERVICE_TYPE", applyToVersion="1.1", updateToVersion="1.2"))
    empty = handler_error(update_typedef_options, patch("UPDATE_TYPEDEF_OPTIONS", applyToVersion="9"), store)

    assert (options, service, cleared) == (PatchStatus.APPLIED,) * 3
    updated = stored(store, "t", AtlasEntityDef)
    assert updated.options == {"keep": "1", "change": "new", "add": "2"}
    assert (updated.service_type, updated.type_version) == ("old", "1.2")
    assert stored(store, "e", AtlasEnumDef).service_type == "svc"
    assert (empty.code, empty.params) == (AtlasErrorCode.PATCH_INVALID_DATA, ("UPDATE_TYPEDEF_OPTIONS", "t"))
    assert set_service_type(patch("SET_SERVICE_TYPE", applyToVersion="9"), store.registry).status is PatchStatus.SKIPPED


@pytest.mark.covers("aurelius_atlas_core.model_loader.update_attribute_metadata", rules=["MDL-13"])
async def test__attribute_metadata_sets_search_weight_and_index_type(store: TypedefStore) -> None:
    """``UpdateAttributeMetadataHandler``: the attribute is matched ignoring case.

    An empty index type is ignored; a type without the attribute still has the patch applied.
    """
    await store.create_types_def(
        types_def_of(
            [
                entity("t", attr("Name"), attr("other")),
                entity("u"),
                AtlasStructDef(name="s", type_version="1.0", attribute_defs=[attr("x")]),
            ]
        )
    )

    status = await apply(
        store,
        patch("UPDATE_ATTRIBUTE_METADATA", attributeName="name", params={"searchWeight": 8.9, "indexType": "STRING"}),
    )
    empty = await apply(
        store, patch("UPDATE_ATTRIBUTE_METADATA", "s", attributeName="x", params={"indexType": "", "searchWeight": -1})
    )
    missing = await apply(store, patch("UPDATE_ATTRIBUTE_METADATA", "u", attributeName="nope"))

    assert (status, empty, missing) == (PatchStatus.APPLIED,) * 3
    name, other = stored(store, "t", AtlasEntityDef).attribute_defs
    assert (name.search_weight, name.index_type) == (8, IndexType.STRING)
    assert (other.search_weight, other.index_type) == (-1, None)
    x = stored(store, "s", AtlasStructDef).attribute_defs[0]
    assert (x.search_weight, x.index_type) == (-1, None)
    assert stored(store, "u", AtlasEntityDef).type_version == "1.1"


@pytest.mark.covers(rules=["MDL-13"])
@pytest.mark.parametrize(
    "params",
    [
        {"searchWeight": 11},
        {"searchWeight": 0},
        {"searchWeight": "5"},
        {"searchWeight": True},
        {"indexType": "FULL"},
        {"indexType": 1},
        {"isOptional": True},
        None,
    ],
    ids=[
        "above-10",
        "zero",
        "string",
        "boolean",
        "unknown-index-type",
        "index-type-number",
        "other-parameter",
        "no-params",
    ],
)
async def test__invalid_attribute_metadata_is_a_runtime_error(
    store: TypedefStore, params: dict[str, Any] | None
) -> None:
    """``Error encountered in updating Model attribute``: a ``RuntimeException``, which ends the patch file."""
    await store.create_types_def(types_def_of([entity("t", attr("a"))]))

    with pytest.raises(PatchDataError):
        update_attribute_metadata(patch("UPDATE_ATTRIBUTE_METADATA", attributeName="a", params=params), store.registry)


@pytest.mark.covers(rules=["MDL-13"])
async def test__attribute_metadata_takes_entities_and_structs(store: TypedefStore) -> None:
    """A classification is not applicable."""
    await store.create_types_def(types_def_of([AtlasClassificationDef(name="c", type_version="1.0")]))

    error = handler_error(update_attribute_metadata, patch("UPDATE_ATTRIBUTE_METADATA", "c"), store)

    assert error.params == ("UPDATE_ATTRIBUTE_METADATA", "AtlasClassificationDef")


@pytest.mark.covers("aurelius_atlas_core.model_loader.add_super_types", rules=["MDL-14"])
async def test__add_super_types_adds_to_entities(store: TypedefStore) -> None:
    """``AddSuperTypePatchHandler``: no super types is ``SKIPPED`` before the version check; entities only."""
    await store.create_types_def(
        types_def_of([entity("base"), entity("t"), AtlasClassificationDef(name="c", type_version="1.0")])
    )

    status = await apply(store, patch("ADD_SUPER_TYPES", superTypes=["base", "base"]))
    none = add_super_types(patch("ADD_SUPER_TYPES", applyToVersion="9"), store.registry)
    on_classification = handler_error(add_super_types, patch("ADD_SUPER_TYPES", "c", superTypes=["x"]), store)
    other_version = add_super_types(patch("ADD_SUPER_TYPES", superTypes=["base"], applyToVersion="9"), store.registry)

    assert status is PatchStatus.APPLIED
    assert stored(store, "t", AtlasEntityDef).super_types == ["base"]
    assert none.status is other_version.status is PatchStatus.SKIPPED
    assert on_classification.params == ("ADD_SUPER_TYPES", "AtlasClassificationDef")


@pytest.mark.covers(rules=["MDL-01", "MDL-02", "MDL-05", "MDL-06", "MDL-07", "MDL-09", "MDL-11", "MDL-12", "MDL-13"])
async def test__the_vendored_models_load_as_in_atlas(store: TypedefStore, document: MemoryTypedefDocument) -> None:
    """All of ``addons/models`` 2.4.0: every file loads, no patch file stops, and each patch ends as in Atlas.

    Two outcomes are Atlas's own: ``019-kafka_producer_lineage_add_options.json`` patches a type no model defines,
    so it fails, again at every start; and ``TYPEDEF_PATCH_1000_018_001`` is the id of two patches, so
    ``018-kafka_topic_add_rf_attribute.json`` is found done after ``018-fs_path_add_supertypes.json`` and
    ``kafka_topic`` never gets ``replicationFactor``.
    """
    result = await ModelLoader(store).load(BUILTIN_MODELS_DIR)
    writes = document.writes
    again = await ModelLoader(store).load(BUILTIN_MODELS_DIR)

    assert result.failed_files == result.stopped_patch_files == []
    assert {pid for pid, status in result.patches.items() if status is PatchStatus.FAILED} == {
        "TYPEDEF_PATCH_1000_019_001"
    }
    assert result.patches["TYPEDEF_PATCH_1000_018_001"] is None
    assert {pid: status for pid, status in again.patches.items() if status is not None} == {
        "TYPEDEF_PATCH_1000_019_001": PatchStatus.FAILED
    }
    assert document.writes == writes + 1
    assert len(store.registry.typedef_names(TypeCategory.ENTITY)) > 100

    referenceable = stored(store, "Referenceable", AtlasEntityDef)
    # 0000-Area0: 001 adds the replication attributes, 002 the service type, 003 the search weight.
    assert [a.name for a in referenceable.attribute_defs] == ["qualifiedName", "replicatedFrom", "replicatedTo"]
    assert referenceable.service_type == "atlas_core"
    assert referenceable.attribute_defs[0].search_weight == 10
    # 0000-Area0/006 adds the operation types to atlas_operation.
    assert stored(store, "atlas_operation", AtlasEnumDef).has_element("IMPORT_DELETE_REPL")
    # 1000-Hadoop/010 moves hbase_table's legacy namespace attribute to the relationship.
    hbase_namespace = stored(store, "hbase_table_namespace", AtlasRelationshipDef)
    assert hbase_namespace.relationship_label == "__hbase_table.namespace"
    assert not stored(store, "hbase_table", AtlasEntityDef).has_attribute("namespace")
    assert not stored(store, "kafka_topic", AtlasEntityDef).has_attribute("replicationFactor")
