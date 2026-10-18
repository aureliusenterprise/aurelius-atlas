"""The typedef store's start-up operations: create-or-update and patches with their records (MDL-02 to MDL-15).

Read from ``AtlasTypeDefStoreInitializer`` (``getTypesToCreate``, ``getTypesToUpdate``, ``applyTypePatches``),
``AtlasTypeDefGraphStore.createUpdateTypesDef``, ``AtlasPatchRegistry`` and its test ``AtlasPatchRegistryTest``, and
what ``RequestContext.isInTypePatching`` allows in ``AtlasStructDefStoreV2`` and ``AtlasRelationshipDefStoreV2``.
"""

from datetime import UTC, datetime, timedelta

import pytest
from aurelius_atlas_core.testing.memory import MemoryTypedefDocument
from aurelius_atlas_core.typedef_store import (
    ADD_MANDATORY_ATTRIBUTE,
    PatchChange,
    TypedefStore,
    is_newer_version,
    java_compare,
    types_def_of,
    types_to_create,
    types_to_update,
)
from aurelius_atlas_model.errors import AtlasError, AtlasErrorCode
from aurelius_atlas_model.patches import TYPEDEF_PATCH_TYPE, AtlasPatch, PatchStatus
from aurelius_atlas_model.typedef import (
    AtlasAttributeDef,
    AtlasBaseTypeDef,
    AtlasEntityDef,
    AtlasEnumDef,
    AtlasEnumElementDef,
    AtlasRelationshipDef,
    AtlasRelationshipEndDef,
    AtlasStructDef,
    AtlasTypesDef,
    Cardinality,
    RelationshipCategory,
)
from aurelius_atlas_typesystem.registry import TypeRegistry

NOW = datetime(2026, 10, 18, 12, 0, tzinfo=UTC)
NOW_MILLIS = int(NOW.timestamp() * 1000)


class Clock:
    """A clock the test moves."""

    def __init__(self) -> None:
        self.now = NOW

    def __call__(self) -> datetime:
        """The current time."""
        return self.now


@pytest.fixture
def document() -> MemoryTypedefDocument:
    """An empty in-memory document."""
    return MemoryTypedefDocument()


@pytest.fixture
def clock() -> Clock:
    """The store's clock."""
    return Clock()


@pytest.fixture
async def store(document: MemoryTypedefDocument, clock: Clock) -> TypedefStore:
    """A loaded store on ``document``."""
    store = TypedefStore(TypeRegistry(), document, now=clock)
    await store.load()
    return store


def attr(name: str, type_name: str = "string", **fields: object) -> AtlasAttributeDef:
    """An attribute definition."""
    return AtlasAttributeDef.model_validate({"name": name, "type_name": type_name, **fields})


def entity(name: str, *attributes: AtlasAttributeDef, version: str | None = None) -> AtlasEntityDef:
    """An entity definition."""
    return AtlasEntityDef(name=name, attribute_defs=list(attributes), type_version=version)


def types(*typedefs: AtlasBaseTypeDef) -> AtlasTypesDef:
    """An ``AtlasTypesDef`` of ``typedefs``."""
    return types_def_of(typedefs)


def record(patch_id: str | None = "p-1", action: str = "SET_SERVICE_TYPE") -> AtlasPatch:
    """A patch's record before its status is known."""
    return AtlasPatch(id=patch_id, description=f"patch {patch_id}", action=action)


@pytest.mark.covers("aurelius_atlas_core.typedef_store.java_compare", rules=["MDL-01"])
def test__strings_compare_by_utf16_code_unit() -> None:
    """``String.compareTo``: a character above the BMP sorts below U+FFFD, which it is above by code point."""
    assert java_compare("a", "b") < 0
    assert java_compare("b", "a") > 0
    assert java_compare("same", "same") == 0
    assert java_compare("\U0001f600", "�") < 0


@pytest.mark.covers("aurelius_atlas_core.typedef_store.is_newer_version", rules=["MDL-02"])
@pytest.mark.parametrize(
    ("new", "old", "newer"),
    [
        ("1.1", "1.0", True),
        ("1.0", "1.0", False),
        ("1.0", "1.1", False),
        ("1.10", "1.9", False),
        ("1.0", None, True),
        (None, "1.0", False),
        (None, None, False),
    ],
)
def test__a_version_is_newer_as_a_string(new: str | None, old: str | None, *, newer: bool) -> None:
    """``ObjectUtils.compare(new, old) > 0``: ``1.10`` is not newer than ``1.9``; absent is less than any."""
    assert is_newer_version(new, old) is newer


@pytest.mark.covers("aurelius_atlas_core.typedef_store.types_def_of", rules=["MDL-03"])
def test__definitions_are_grouped_by_kind() -> None:
    """Each definition goes to the list of its kind, in order."""
    grouped = types_def_of([entity("b"), AtlasEnumDef(name="e"), entity("a")])

    assert [typedef.name for typedef in grouped.entity_defs or []] == ["b", "a"]
    assert [typedef.name for typedef in grouped.enum_defs or []] == ["e"]


@pytest.mark.covers(
    "aurelius_atlas_core.typedef_store.types_to_create",
    "aurelius_atlas_core.typedef_store.types_to_update",
    rules=["MDL-02"],
)
async def test__a_model_creates_new_names_and_updates_newer_versions(store: TypedefStore) -> None:
    """``getTypesToCreate``, ``getTypesToUpdate``: a name of another kind is neither; an update keeps what it lacks."""
    await store.create_types_def(
        types(
            entity("t", attr("kept"), attr("both"), version="1.0"),
            entity("same", version="1.0"),
            AtlasStructDef(name="s", attribute_defs=[attr("a")], type_version="1.0"),
            AtlasEnumDef(
                name="e",
                type_version="1.0",
                element_defs=[
                    AtlasEnumElementDef(value="OLD", ordinal=1),
                    AtlasEnumElementDef(value="BOTH", ordinal=2),
                ],
            ),
        )
    )
    model = types(
        entity("t", attr("both", description="new"), attr("added"), version="1.1"),
        entity("same", attr("ignored"), version="1.0"),
        entity("s", version="2.0"),
        entity("string"),
        entity("new"),
        AtlasEnumDef(
            name="e",
            type_version="1.1",
            element_defs=[AtlasEnumElementDef(value="both", ordinal=5), AtlasEnumElementDef(value="NEW", ordinal=6)],
        ),
    )

    created = types_to_create(model, store.registry)
    updated = types_to_update(model, store.registry, check_type_version=True)
    unchecked = types_to_update(model, store.registry, check_type_version=False)

    assert [typedef.name for typedef in created.entity_defs or []] == ["new"]
    assert [typedef.name for typedef in updated.entity_defs or []] == ["t"]
    assert [typedef.name for typedef in unchecked.entity_defs or []] == ["t", "same"]
    entity_update = (updated.entity_defs or [])[0]
    assert [(a.name, a.description) for a in entity_update.attribute_defs] == [
        ("both", "new"),
        ("added", None),
        ("kept", None),
    ]
    enum_update = (updated.enum_defs or [])[0]
    assert [element.value for element in enum_update.element_defs] == ["both", "NEW", "OLD"]
    assert (model.entity_defs or [])[0].attribute_defs[-1].name == "added"


@pytest.mark.covers("aurelius_atlas_core.typedef_store.TypedefStore.create_update_types_def", rules=["MDL-03"])
async def test__creations_and_updates_are_one_write(store: TypedefStore, document: MemoryTypedefDocument) -> None:
    """``createUpdateTypesDef``: an update a creation refers to is replaced first; one write for both."""
    await store.create_types_def(types(entity("t", version="1.0")))
    writes = document.writes

    changed = await store.create_update_types_def(
        types(
            entity("u", attr("ref", "t")),
            entity("t", attr("a", is_optional=True), version="1.1"),
        ),
        check_type_version=True,
    )

    assert [typedef.name for typedef in changed.entity_defs or []] == ["u", "t"]
    assert document.writes == writes + 1
    stored_t = store.registry.typedef_by_name("t")
    assert stored_t is not None
    assert (stored_t.version, stored_t.type_version) == (2, "1.1")
    assert store.registry.entity_type("u") is not None


@pytest.mark.covers(rules=["MDL-02", "MDL-03"])
async def test__nothing_new_writes_nothing(store: TypedefStore, document: MemoryTypedefDocument) -> None:
    """``No new type in file``: no write, and the registry is unchanged."""
    await store.create_types_def(types(entity("t", version="1.0")))
    writes = document.writes

    changed = await store.create_update_types_def(types(entity("t", version="1.0")), check_type_version=True)

    assert changed.is_empty()
    assert document.writes == writes
    assert store.registry.entity_type("t") is not None


@pytest.mark.covers(rules=["MDL-03"])
async def test__a_failing_creation_stores_nothing_of_the_file(
    store: TypedefStore, document: MemoryTypedefDocument
) -> None:
    """An unknown type is a bad request, as TDS-01; the update in the same file is not stored either."""
    await store.create_types_def(types(entity("t", version="1.0")))
    writes = document.writes

    with pytest.raises(AtlasError) as raised:
        await store.create_update_types_def(
            types(entity("u", attr("ref", "missing")), entity("t", attr("a", is_optional=True), version="1.1")),
            check_type_version=True,
        )

    assert raised.value.code is AtlasErrorCode.BAD_REQUEST
    assert document.writes == writes
    stored_t = store.registry.typedef_by_name("t")
    assert stored_t is not None
    assert stored_t.type_version == "1.0"


@pytest.mark.covers(rules=["MDL-15"])
async def test__a_model_another_process_loaded_first_is_decided_again(
    store: TypedefStore, document: MemoryTypedefDocument
) -> None:
    """DD-033: after a conflict the file is decided on the other process's types, and nothing is created twice."""
    other = TypedefStore(TypeRegistry(), document, now=lambda: NOW)
    await other.load()
    await other.create_update_types_def(types(entity("t", version="1.0")), check_type_version=True)
    writes = document.writes

    changed = await store.create_update_types_def(types(entity("t", version="1.0")), check_type_version=True)

    assert changed.is_empty()
    assert document.writes == writes
    assert store.registry.entity_type("t") is not None


def set_service_type(registry: TypeRegistry, service_type: str) -> PatchChange:
    """A change that sets ``t``'s service type, as the patch handlers produce them."""
    typedef = registry.typedef_by_name("t")
    assert typedef is not None
    return PatchChange(
        PatchStatus.APPLIED, types(typedef.model_copy(update={"service_type": service_type, "type_version": "1.1"}))
    )


@pytest.mark.covers("aurelius_atlas_core.typedef_store.TypedefStore.apply_patch", rules=["MDL-05", "MDL-06"])
async def test__a_patch_is_recorded_with_its_change(
    store: TypedefStore, document: MemoryTypedefDocument, clock: Clock
) -> None:
    """``register``: the record and the change are one write; an applied patch is not applied again."""
    await store.create_types_def(types(entity("t", version="1.0")))
    writes = document.writes

    status = await store.apply_patch(record(), lambda registry: set_service_type(registry, "svc"))
    clock.now = NOW + timedelta(seconds=1)
    again = await store.apply_patch(record(), lambda registry: set_service_type(registry, "other"))

    assert (status, again) == (PatchStatus.APPLIED, None)
    assert document.writes == writes + 1
    stored = store.registry.typedef_by_name("t")
    assert stored is not None
    assert stored.service_type == "svc"
    assert [AtlasPatch.model_validate(p) for p in document.patches] == [
        AtlasPatch(
            id="p-1",
            description="patch p-1",
            type=TYPEDEF_PATCH_TYPE,
            action="SET_SERVICE_TYPE",
            status=PatchStatus.APPLIED,
            created_time=NOW_MILLIS,
            updated_time=NOW_MILLIS,
        )
    ]


@pytest.mark.covers(rules=["MDL-05", "MDL-06"])
async def test__a_skipped_patch_is_recorded_and_not_tried_again(
    store: TypedefStore, document: MemoryTypedefDocument
) -> None:
    """A ``SKIPPED`` record is final, as ``APPLIED`` is; the registry is not touched."""
    status = await store.apply_patch(record(), lambda _registry: PatchChange(PatchStatus.SKIPPED))
    again = await store.apply_patch(record(), lambda _registry: pytest.fail("decided again"))

    assert (status, again) == (PatchStatus.SKIPPED, None)
    assert [p["status"] for p in document.patches] == ["SKIPPED"]


@pytest.mark.covers(rules=["MDL-05", "MDL-06"])
async def test__a_failed_patch_is_recorded_and_tried_again(
    store: TypedefStore, document: MemoryTypedefDocument, clock: Clock
) -> None:
    """An Atlas error from the decision or from the update is ``FAILED``; the next start tries again.

    The definitions stay as they were; a record keeps its created time when it is written again.
    """
    await store.create_types_def(types(entity("t", attr("a"), version="1.0")))

    def unknown(_registry: TypeRegistry) -> PatchChange:
        raise AtlasError(AtlasErrorCode.PATCH_FOR_UNKNOWN_TYPE, "SET_SERVICE_TYPE", "x")

    first = await store.apply_patch(record(), unknown)
    clock.now = NOW + timedelta(seconds=1)
    removal = PatchChange(PatchStatus.APPLIED, types(entity("t", version="1.1")))
    second = await store.apply_patch(record(), lambda _registry: removal)
    clock.now = NOW + timedelta(seconds=2)
    third = await store.apply_patch(record(), lambda registry: set_service_type(registry, "svc"))

    assert (first, second, third) == (PatchStatus.FAILED, PatchStatus.FAILED, PatchStatus.APPLIED)
    stored = store.registry.typedef_by_name("t")
    assert isinstance(stored, AtlasEntityDef)
    assert (stored.service_type, [a.name for a in stored.attribute_defs]) == ("svc", ["a"])
    assert [(p["status"], p["createdTime"], p["updatedTime"]) for p in document.patches] == [
        ("APPLIED", NOW_MILLIS, NOW_MILLIS + 2000)
    ]


@pytest.mark.covers(rules=["MDL-06"])
async def test__an_error_that_is_not_atlas_s_is_raised_and_nothing_is_recorded(
    store: TypedefStore, document: MemoryTypedefDocument
) -> None:
    """A runtime exception escapes ``applyTypePatches``' handler call: no status, no record."""

    def broken(_registry: TypeRegistry) -> PatchChange:
        message = "bad data"
        raise ValueError(message)

    with pytest.raises(ValueError, match="bad data"):
        await store.apply_patch(record(), broken)

    assert document.patches == []


@pytest.mark.covers(rules=["MDL-05"])
async def test__a_patch_without_an_id_is_applied_every_time_and_not_recorded(
    store: TypedefStore, document: MemoryTypedefDocument
) -> None:
    """DV-08: its change is written, but no record; a patch without an id and without a change writes nothing."""
    await store.create_types_def(types(entity("t", version="1.0")))
    writes = document.writes

    applied = await store.apply_patch(record(None), lambda registry: set_service_type(registry, "svc"))
    skipped = await store.apply_patch(record(None), lambda _registry: PatchChange(PatchStatus.SKIPPED))

    assert (applied, skipped) == (PatchStatus.APPLIED, PatchStatus.SKIPPED)
    assert document.writes == writes + 1
    assert document.patches == []


@pytest.mark.covers(rules=["MDL-15"])
async def test__a_patch_another_process_applied_first_is_not_applied_again(
    store: TypedefStore, document: MemoryTypedefDocument
) -> None:
    """DD-031, DD-033: the conflict reloads the records with the types, and the patch is found done."""
    await store.create_types_def(types(entity("t", version="1.0")))
    other = TypedefStore(TypeRegistry(), document, now=lambda: NOW)
    await other.load()
    await other.apply_patch(record(), lambda registry: set_service_type(registry, "first"))
    store._checked_at = None  # noqa: SLF001 - the change finds the newer document by its write's conflict

    status = await store.apply_patch(record(), lambda registry: set_service_type(registry, "second"))

    assert status is None
    stored = store.registry.typedef_by_name("t")
    assert stored is not None
    assert stored.service_type == "first"


@pytest.mark.covers(rules=["MDL-07"])
async def test__outside_patching_an_update_may_not_remove_or_add_mandatory_attributes(store: TypedefStore) -> None:
    """Patch updates without ``patching`` get TDS-08 as is: ``ADD_ATTRIBUTE`` of a mandatory attribute fails."""
    await store.create_types_def(types(entity("t", attr("a"), version="1.0")))

    removal = await store.apply_patch(
        record("r"), lambda _registry: PatchChange(PatchStatus.APPLIED, types(entity("t", version="1.1")))
    )
    mandatory = await store.apply_patch(
        record("m"),
        lambda _registry: PatchChange(
            PatchStatus.APPLIED, types(entity("t", attr("a"), attr("b", is_optional=False), version="1.1"))
        ),
    )

    assert (removal, mandatory) == (PatchStatus.FAILED, PatchStatus.FAILED)


@pytest.mark.covers(rules=["MDL-10"])
async def test__under_add_mandatory_attribute_an_update_may_add_mandatory_attributes(store: TypedefStore) -> None:
    """``isInAddMandatoryAttributePatch`` lifts ``CANNOT_ADD_MANDATORY_ATTRIBUTE``; it is in type patching too."""
    await store.create_types_def(types(entity("t", attr("a", is_optional=True), version="1.0")))
    mandatory = attr("b", "int", is_optional=False, default_value="0")

    status = await store.apply_patch(
        record(action=ADD_MANDATORY_ATTRIBUTE),
        lambda _registry: PatchChange(
            PatchStatus.APPLIED, types(entity("t", mandatory, version="1.1")), ADD_MANDATORY_ATTRIBUTE
        ),
    )

    assert status is PatchStatus.APPLIED
    stored = store.registry.typedef_by_name("t")
    assert isinstance(stored, AtlasEntityDef)
    assert [a.name for a in stored.attribute_defs] == ["b"]


def relationship(
    end1: tuple[str, str], end2: tuple[str, str], category: RelationshipCategory = RelationshipCategory.AGGREGATION
) -> AtlasRelationshipDef:
    """A relationship ``r`` between two entity type ends; the end on ``a`` is the container."""
    return AtlasRelationshipDef(
        name="r",
        relationship_category=category,
        end_def1=AtlasRelationshipEndDef(
            type=end1[0], name=end1[1], cardinality=Cardinality.SINGLE, is_container=end1[0] == "a"
        ),
        end_def2=AtlasRelationshipEndDef(
            type=end2[0], name=end2[1], cardinality=Cardinality.SINGLE, is_container=end2[0] == "a"
        ),
    )


@pytest.mark.covers(rules=["MDL-11"])
async def test__while_patching_attributes_may_go_ends_swap_and_the_category_change(store: TypedefStore) -> None:
    """``isInTypePatching``: attribute removal, a new category and swapped ends are allowed."""
    await store.create_types_def(types(entity("a", attr("x")), entity("b"), relationship(("a", "toB"), ("b", "toA"))))
    swapped = relationship(("b", "toA"), ("a", "toB"), RelationshipCategory.COMPOSITION)
    change = PatchChange(PatchStatus.APPLIED, types(entity("a"), swapped), "REMOVE_LEGACY_REF_ATTRIBUTES")

    status = await store.apply_patch(record(), lambda _registry: change)

    assert status is PatchStatus.APPLIED
    stored = store.registry.typedef_by_name("r")
    assert isinstance(stored, AtlasRelationshipDef)
    assert stored.relationship_category is RelationshipCategory.COMPOSITION
    assert stored.end_def1 is not None
    assert stored.end_def1.type == "b"
    a = store.registry.typedef_by_name("a")
    assert isinstance(a, AtlasEntityDef)
    assert a.attribute_defs == []


@pytest.mark.covers(rules=["MDL-11"])
async def test__while_patching_a_changed_end_still_fails(store: TypedefStore) -> None:
    """Only a swap is allowed: an end that matches neither existing end fails, and so does a swap with a changed end."""
    await store.create_types_def(types(entity("a"), entity("b"), entity("c"), relationship(("a", "toB"), ("b", "toA"))))

    def update(end1: tuple[str, str], end2: tuple[str, str]) -> PatchChange:
        return PatchChange(PatchStatus.APPLIED, types(relationship(end1, end2)), "REMOVE_LEGACY_REF_ATTRIBUTES")

    end1 = await store.apply_patch(record("1"), lambda _registry: update(("c", "toB"), ("b", "toA")))
    end2 = await store.apply_patch(record("2"), lambda _registry: update(("c", "toA"), ("a", "toB")))

    assert (end1, end2) == (PatchStatus.FAILED, PatchStatus.FAILED)
