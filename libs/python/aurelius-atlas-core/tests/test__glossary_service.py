"""Glossaries and categories (GLS-01 to GLS-06, GCT-01 to GCT-07) on the in-memory documents.

Read from ``GlossaryService``, ``GlossaryCategoryUtils``, ``DataAccess`` and the glossary DTOs of Apache Atlas 2.4.0,
with the glossaries and categories of its ``GlossaryServiceTest``, on its ``0011-glossary_model``.
"""

import json

import pytest
from aurelius_atlas_core.entity_store import EntityStore
from aurelius_atlas_core.glossary_service import GlossaryService, SortOrder, is_name_invalid, paginate
from aurelius_atlas_core.model_loader import BUILTIN_MODELS_DIR
from aurelius_atlas_core.testing.memory import MemoryEntityDocuments
from aurelius_atlas_model.errors import AtlasError, AtlasErrorCode
from aurelius_atlas_model.glossary import (
    AtlasGlossary,
    AtlasGlossaryCategory,
    AtlasGlossaryHeader,
    AtlasRelatedCategoryHeader,
)
from aurelius_atlas_model.typedef import AtlasTypesDef
from aurelius_atlas_typesystem.registry import TypeRegistry

S = "aurelius_atlas_core.glossary_service.GlossaryService"
D = "aurelius_atlas_core.glossary_dto"
U = "aurelius_atlas_core.glossary_category_utils"
MODELS = BUILTIN_MODELS_DIR / "0000-Area0"


@pytest.fixture
def service() -> GlossaryService:
    """A service on a store with the base and glossary models."""
    registry = TypeRegistry()
    with registry.update() as transient:
        for name in ("0010-base_model.json", "0011-glossary_model.json"):
            transient.add_types(AtlasTypesDef.model_validate(json.loads((MODELS / name).read_text(encoding="utf-8"))))
    return GlossaryService(EntityStore(registry, MemoryEntityDocuments()))


async def glossary(service: GlossaryService, name: str, **fields: str) -> AtlasGlossary:
    """A glossary created by name."""
    return await service.create_glossary(AtlasGlossary.model_validate({"name": name, **fields}))


async def category(
    service: GlossaryService, name: str, glossary_guid: str, parent: str | None = None
) -> AtlasGlossaryCategory:
    """A category created in the glossary, below ``parent`` when given."""
    created = AtlasGlossaryCategory(name=name, anchor=AtlasGlossaryHeader(glossary_guid=glossary_guid))
    if parent is not None:
        created.parent_category = AtlasRelatedCategoryHeader(category_guid=parent)
    return await service.create_category(created)


async def failure(awaitable: object) -> AtlasErrorCode:
    """The code of the error the awaitable raises."""
    with pytest.raises(AtlasError) as raised:
        await awaitable  # type: ignore[misc]
    return raised.value.code


@pytest.mark.covers(
    f"{S}.create_glossary",
    f"{S}.get_glossary",
    f"{D}.DataAccess.save",
    f"{D}.DataAccess.load",
    f"{D}.glossary_from",
    f"{D}.to_entity",
    f"{U}.glossary_skeleton",
    rules=["GLS-01", "GLS-02"],
)
async def test__a_glossary_is_named_by_its_name(service: GlossaryService) -> None:
    """``testCreateGlossary``: the name as qualified name, the GUID assigned; the same name again fails."""
    created = await glossary(service, "bankGlossary", shortDescription="Short description", language="English")
    assert (created.qualified_name, created.name, created.short_description, created.language) == (
        "bankGlossary",
        "bankGlossary",
        "Short description",
        "English",
    )
    assert not created.guid.startswith("-")
    assert (await service.get_glossary(created.guid)).name == "bankGlossary"
    assert await failure(glossary(service, "bankGlossary")) is AtlasErrorCode.GLOSSARY_ALREADY_EXISTS


@pytest.mark.covers(f"{S}.create_glossary", "aurelius_atlas_core.glossary_service.is_name_invalid", rules=["GLS-02"])
async def test__a_glossary_needs_a_valid_name(service: GlossaryService) -> None:
    """No name, or a name with ``@ . < >``, fails; a qualified name given is kept."""
    assert await failure(service.create_glossary(None)) is AtlasErrorCode.BAD_REQUEST
    assert (
        await failure(service.create_glossary(AtlasGlossary()))
        is AtlasErrorCode.GLOSSARY_QUALIFIED_NAME_CANT_BE_DERIVED
    )
    assert await failure(glossary(service, "a.b")) is AtlasErrorCode.INVALID_DISPLAY_NAME
    assert [is_name_invalid(name) for name in ("a@b", "a<b", "a>b", "ab", None)] == [True, True, True, False, False]
    kept = await service.create_glossary(AtlasGlossary(name="x", qualified_name="qx"))
    assert kept.qualified_name == "qx"


@pytest.mark.covers(f"{S}.update_glossary", rules=["GLS-03"])
async def test__a_glossary_update_keeps_its_guid_and_qualified_name(service: GlossaryService) -> None:
    """``testUpdateGlossary``: the description changed, the qualified name not; a bad name fails."""
    created = await glossary(service, "g")
    change = AtlasGlossary(guid=created.guid, name="renamed", short_description="new", qualified_name="ignored")
    updated = await service.update_glossary(change)
    assert (updated.guid, updated.name, updated.qualified_name, updated.short_description) == (
        created.guid,
        "renamed",
        "g",
        "new",
    )
    assert await failure(service.update_glossary(AtlasGlossary(guid=created.guid))) is AtlasErrorCode.BAD_REQUEST
    assert await failure(service.update_glossary(None)) is AtlasErrorCode.BAD_REQUEST
    bad = AtlasGlossary(guid=created.guid, name="a@b")
    assert await failure(service.update_glossary(bad)) is AtlasErrorCode.INVALID_DISPLAY_NAME


@pytest.mark.covers(
    f"{S}.get_glossaries",
    "aurelius_atlas_core.glossary_service.paginate",
    "aurelius_atlas_core.glossary_service.SortOrder.of",
    rules=["GLS-05"],
)
async def test__glossaries_are_listed_by_qualified_name_and_paged(service: GlossaryService) -> None:
    """Ascending unless ``DESC``; ``limit`` -1 for all; past the end none (``PaginationHelperTest``)."""
    for name in ("b", "a", "c"):
        await glossary(service, name)
    names = [found.name for found in await service.get_glossaries(-1, 0, SortOrder.of("ASC"))]
    assert names == ["a", "b", "c"]
    assert [found.name for found in await service.get_glossaries(2, 1, SortOrder.of("DESC"))] == ["b", "a"]
    assert await service.get_glossaries(5, 9, SortOrder.of("x")) == []
    assert paginate([1, 2, 3], 0, -1) == [1, 2, 3]
    assert paginate([1, 2, 3], 1, 1) == [2]
    assert paginate([1, 2, 3], 3, 1) == []


@pytest.mark.covers(f"{S}.get_glossary", rules=["GLS-06"])
async def test__a_read_of_another_entity_fails(service: GlossaryService) -> None:
    """A category's GUID read as a glossary is ``UNEXPECTED_TYPE``; no entity ``INSTANCE_GUID_NOT_FOUND``."""
    created = await glossary(service, "g")
    found = await category(service, "c", created.guid)
    assert await failure(service.get_glossary(found.guid)) is AtlasErrorCode.UNEXPECTED_TYPE
    assert await failure(service.get_glossary("nope")) is AtlasErrorCode.INSTANCE_GUID_NOT_FOUND


@pytest.mark.covers(
    f"{S}.create_category",
    f"{S}.get_category",
    f"{S}.get_detailed_glossary",
    f"{D}.DataAccess.load_all",
    f"{D}.DataAccess.save_all",
    f"{D}.category_from",
    f"{D}.related_category_header",
    f"{D}.related_term_header",
    f"{U}.GlossaryCategoryUtils.process_category_relations",
    f"{U}.category_skeleton",
    rules=["GCT-01", "GCT-02", "GLS-06"],
)
async def test__a_category_is_anchored_and_named_below_its_glossary(service: GlossaryService) -> None:
    """``testCreateGlossaryCategory``: ``name@glossary``; the glossary lists it, its detail holds it."""
    created = await glossary(service, "g")
    found = await category(service, "accounts", created.guid)
    assert found.qualified_name == "accounts@g"
    assert found.anchor is not None
    assert found.anchor.glossary_guid == created.guid
    listed = await service.get_glossary(created.guid)
    assert [(header.category_guid, header.display_text) for header in listed.categories or []] == [
        (found.guid, "accounts")
    ]
    detailed = await service.get_detailed_glossary(created.guid)
    assert list((detailed.category_info or {}).keys()) == [found.guid]
    assert await failure(category(service, "accounts", created.guid)) is AtlasErrorCode.GLOSSARY_CATEGORY_ALREADY_EXISTS


@pytest.mark.covers(f"{S}.create_category", f"{S}.create_categories", rules=["GCT-02"])
async def test__a_category_needs_an_anchor_and_a_valid_name(service: GlossaryService) -> None:
    """No body, anchor or name, or a bad name, fails."""
    created = await glossary(service, "g")
    anchor = AtlasGlossaryHeader(glossary_guid=created.guid)
    assert await failure(service.create_category(None)) is AtlasErrorCode.BAD_REQUEST
    assert await failure(service.create_categories(None)) is AtlasErrorCode.BAD_REQUEST
    assert (
        await failure(service.create_category(AtlasGlossaryCategory(name="c")))
        is AtlasErrorCode.MISSING_MANDATORY_ANCHOR
    )
    nameless = AtlasGlossaryCategory(anchor=anchor)
    assert (
        await failure(service.create_category(nameless))
        is AtlasErrorCode.GLOSSARY_CATEGORY_QUALIFIED_NAME_CANT_BE_DERIVED
    )
    dotted = AtlasGlossaryCategory(name="a.b", anchor=anchor)
    assert await failure(service.create_category(dotted)) is AtlasErrorCode.INVALID_DISPLAY_NAME
    made = await service.create_categories([AtlasGlossaryCategory(name="x", anchor=anchor)])
    assert [found.qualified_name for found in made] == ["x@g"]


@pytest.mark.covers(f"{S}.create_category", f"{S}.get_related_categories", rules=["GCT-03", "GCT-07"])
async def test__a_child_is_named_below_its_parent(service: GlossaryService) -> None:
    """``testCategoryRelation``: ``child.parent@glossary`` down the hierarchy; parent and children related."""
    created = await glossary(service, "g")
    parent = await category(service, "parent", created.guid)
    child = await category(service, "child", created.guid, parent=parent.guid)
    grandchild = await category(service, "leaf", created.guid, parent=child.guid)
    assert (child.qualified_name, grandchild.qualified_name) == ("child.parent@g", "leaf.child.parent@g")
    related = await service.get_related_categories(child.guid)
    assert [header.category_guid for header in related["parent"]] == [parent.guid]
    assert [header.category_guid for header in related["children"]] == [grandchild.guid]
    leaf_related = await service.get_related_categories(grandchild.guid)
    assert list(leaf_related) == ["parent"]
    assert [header.category_guid for header in leaf_related["parent"]] == [child.guid]


@pytest.mark.covers(f"{S}.create_category", rules=["GCT-03"])
async def test__children_listed_on_create_are_renamed_and_of_the_same_glossary(service: GlossaryService) -> None:
    """Children given on create are linked and renamed; a child of another glossary fails."""
    created = await glossary(service, "g")
    other = await glossary(service, "o")
    child = await category(service, "kid", created.guid)
    stranger = await category(service, "s", other.guid)
    parent = AtlasGlossaryCategory(
        name="p",
        anchor=AtlasGlossaryHeader(glossary_guid=created.guid),
        children_categories=[AtlasRelatedCategoryHeader(category_guid=child.guid)],
    )
    made = await service.create_category(parent)
    assert (await service.get_category(child.guid)).qualified_name == "kid.p@g"
    assert [header.display_text for header in made.children_categories or []] == ["kid"]
    wrong = AtlasGlossaryCategory(
        name="q",
        anchor=AtlasGlossaryHeader(glossary_guid=created.guid),
        children_categories=[AtlasRelatedCategoryHeader(category_guid=stranger.guid)],
    )
    assert await failure(service.create_category(wrong)) is AtlasErrorCode.INVALID_CHILD_CATEGORY_DIFFERENT_GLOSSARY


@pytest.mark.covers(f"{S}.update_category", rules=["GCT-04"])
async def test__a_category_moves_to_another_parent_or_glossary(service: GlossaryService) -> None:
    """A removed parent names it below its glossary; a new anchor moves it and its children."""
    first = await glossary(service, "g")
    second = await glossary(service, "h")
    parent = await category(service, "p", first.guid)
    child = await category(service, "c", first.guid, parent=parent.guid)
    leaf = await category(service, "l", first.guid, parent=child.guid)
    loose = await service.get_category(child.guid)
    loose.parent_category = None
    updated = await service.update_category(loose)
    assert updated.qualified_name == "c@g"
    assert (await service.get_category(leaf.guid)).qualified_name == "l.c@g"
    moved = await service.get_category(child.guid)
    moved.anchor = AtlasGlossaryHeader(glossary_guid=second.guid)
    moved = await service.update_category(moved)
    assert moved.qualified_name == "c@h"
    moved_leaf = await service.get_category(leaf.guid)
    assert moved_leaf.qualified_name == "l.c@h"
    assert moved_leaf.anchor is not None
    assert moved_leaf.anchor.glossary_guid == second.guid


@pytest.mark.covers(f"{S}.update_category", rules=["GCT-04"])
async def test__a_category_update_needs_a_valid_name_and_keeps_its_name(service: GlossaryService) -> None:
    """No body or name fails; an unchanged category is not written; a new description is."""
    created = await glossary(service, "g")
    found = await category(service, "c", created.guid)
    assert await failure(service.update_category(None)) is AtlasErrorCode.BAD_REQUEST
    assert await failure(service.update_category(AtlasGlossaryCategory(guid=found.guid))) is AtlasErrorCode.BAD_REQUEST
    same = await service.update_category(await service.get_category(found.guid))
    assert same.qualified_name == "c@g"
    changed = await service.get_category(found.guid)
    changed.short_description = "about"
    assert (await service.update_category(changed)).short_description == "about"


@pytest.mark.covers(
    f"{S}.delete_category", f"{S}.delete_glossary", f"{D}.DataAccess.delete", rules=["GCT-06", "GLS-04"]
)
async def test__deletes_remove_categories_then_the_glossary(service: GlossaryService) -> None:
    """``testDeleteGlossary``: a deleted category is gone from its glossary; internal types are deleted for good."""
    created = await glossary(service, "g")
    kept = await category(service, "kept", created.guid)
    gone = await category(service, "gone", created.guid)
    await service.delete_category(gone.guid)
    assert [header.category_guid for header in (await service.get_glossary(created.guid)).categories or []] == [
        kept.guid
    ]
    assert await failure(service.get_category(gone.guid)) is AtlasErrorCode.INSTANCE_GUID_NOT_FOUND
    await service.delete_glossary(created.guid)
    assert await failure(service.get_glossary(created.guid)) is AtlasErrorCode.INSTANCE_GUID_NOT_FOUND
    assert await failure(service.get_category(kept.guid)) is AtlasErrorCode.INSTANCE_GUID_NOT_FOUND


@pytest.mark.covers(f"{S}.get_glossary_categories_headers", f"{S}.get_glossary_categories", rules=["GLS-05"])
async def test__a_glossary_s_categories_by_display_text(service: GlossaryService) -> None:
    """Sorted by name, paged; the full categories of those headers."""
    created = await glossary(service, "g")
    for name in ("b", "c", "a"):
        await category(service, name, created.guid)
    headers = await service.get_glossary_categories_headers(created.guid, 0, -1, SortOrder.ASCENDING)
    assert [header.display_text for header in headers] == ["a", "b", "c"]
    page = await service.get_glossary_categories(created.guid, 1, 1, SortOrder.DESCENDING)
    assert [found.name for found in page] == ["b"]
