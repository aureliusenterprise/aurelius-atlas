"""Classification propagation (PRO-01 to PRO-10) on the in-memory documents.

Lineage: ``p1`` reads ``a`` and writes ``b``, ``p2`` reads ``b`` and writes ``c``; ``p_input`` and ``p_output``
propagate downstream. The expected propagations are read from ``DeleteHandlerV1`` (``addTagPropagation``,
``removeTagPropagation``, ``updateTagPropagations``, ``handleBlockedClassifications``, ``deleteAllClassifications``),
``EntityGraphRetriever`` (``traverseImpactedVertices``, ``readClassificationsFromEdge``) and ``EntityGraphMapper`` of
Apache Atlas 2.4.0.
"""

from typing import Any

import pytest
from aurelius_atlas_core.delete_type import DeleteType
from aurelius_atlas_core.entity_classifications import EntityClassifications
from aurelius_atlas_core.entity_documents import VersionedEntity
from aurelius_atlas_core.entity_store import EntityStore
from aurelius_atlas_core.entity_writer import EntityWriter
from aurelius_atlas_core.relationship_store import RelationshipStore
from aurelius_atlas_core.testing.entity_samples import sample_registry
from aurelius_atlas_core.testing.memory import MemoryEntityDocuments
from aurelius_atlas_core.transaction_view import TransactionView
from aurelius_atlas_model import codec
from aurelius_atlas_model.errors import AtlasError, AtlasErrorCode
from aurelius_atlas_model.instance import AtlasClassification, AtlasEntitiesWithExtInfo, AtlasRelationship

P = "aurelius_atlas_core.tag_propagation.TagPropagation"
C = "aurelius_atlas_core.entity_classifications.EntityClassifications"


@pytest.fixture
def documents() -> MemoryEntityDocuments:
    """The documents the store keeps entities in."""
    return MemoryEntityDocuments()


@pytest.fixture
def store(documents: MemoryEntityDocuments) -> EntityStore:
    """A store of the sample, write and classification types."""
    return EntityStore(sample_registry(classifications=True), documents)


GUIDS: dict[str, str] = {}
FLOWS: dict[str, str] = {}


@pytest.fixture(autouse=True)
def _guids() -> None:
    GUIDS.clear()
    FLOWS.clear()


def ref(name: str, type_name: str) -> dict[str, Any]:
    """An object id of an entity by name: its GUID, or its request GUID ``-name``."""
    return {"guid": GUIDS.get(name, f"-{name}"), "typeName": type_name}


def data(name: str) -> dict[str, Any]:
    """A ``p_data`` entity named ``name``."""
    return {"typeName": "p_data", "guid": f"-{name}", "attributes": {"qualifiedName": name}}


def process(name: str, reads: list[str], writes: list[str]) -> dict[str, Any]:
    """A ``p_process`` reading and writing ``p_data`` entities by name."""
    return {
        "typeName": "p_process",
        "guid": f"-{name}",
        "attributes": {"qualifiedName": name},
        "relationshipAttributes": {
            "inputs": [ref(r, "p_data") for r in reads],
            "outputs": [ref(w, "p_data") for w in writes],
        },
    }


async def create(store: EntityStore, *entities: dict[str, Any]) -> None:
    """Create the entities; their GUIDs in ``GUIDS`` by name."""
    created = await EntityWriter(store).create_or_update(
        AtlasEntitiesWithExtInfo.model_validate({"entities": list(entities)})
    )
    GUIDS.update({key.removeprefix("-"): value for key, value in (created.guid_assignments or {}).items()})


async def chain(store: EntityStore) -> None:
    """``a -> p1 -> b -> p2 -> c``, ``d`` and ``p3`` apart; the relationships in ``FLOWS`` as ``a.p1``, …."""
    await create(
        store,
        data("a"),
        data("b"),
        data("c"),
        data("d"),
        process("p1", ["a"], ["b"]),
        process("p2", ["b"], ["c"]),
        process("p3", [], []),
    )
    for name in ("p1", "p2"):
        found = await store.get(GUIDS[name])
        assert found is not None
        by_guid = {guid: key for key, guid in GUIDS.items()}
        for relationship in (await store.get_relationships(found.entity.relationship_guids or [])).values():
            ends = relationship.relationship.ends()
            FLOWS[f"{by_guid[ends[0]]}.{by_guid[ends[1]]}"] = relationship.relationship.guid


async def names(store: EntityStore, name: str) -> list[tuple[str | None, str | None]]:
    """The classifications of entity ``name``: type and the entity each is attached to, by name."""
    by_guid = {guid: key for key, guid in GUIDS.items()}
    return [
        (c.type_name, by_guid.get(c.entity_guid or "", c.entity_guid))
        for c in await EntityClassifications(store).get_classifications(GUIDS[name])
    ]


def tag(type_name: str = "c_pii", **more: Any) -> AtlasClassification:  # noqa: ANN401 - Atlas JSON
    """A classification as a request gives it."""
    return AtlasClassification.model_validate({"typeName": type_name, **more})


@pytest.mark.covers(
    f"{P}.impacted",
    f"{P}.add",
    f"{P}.add_instances",
    f"{P}.entity",
    f"{P}.propagation_enabled",
    f"{C}.add_classifications",
    rules=["PRO-01", "PRO-02", "PRO-03", "PRO-10"],
)
async def test__an_added_classification_reaches_everything_downstream(store: EntityStore) -> None:
    """``c_pii`` on ``a`` reaches ``p1``, ``b``, ``p2`` and ``c``; one not propagating does not; ``d`` is apart."""
    await chain(store)
    classifier = EntityClassifications(store)

    await classifier.add_classifications(GUIDS["a"], [tag(), tag("c_secret", propagate=False)])
    await classifier.add_classifications(GUIDS["d"], [tag()])

    assert await names(store, "a") == [("c_pii", "a"), ("c_secret", "a")]
    assert [await names(store, n) for n in ("p1", "b", "p2", "c")] == [[("c_pii", "a")]] * 4
    assert await names(store, "d") == [("c_pii", "d")]


@pytest.mark.covers(
    f"{C}.update_classifications", f"{C}.delete_classification", f"{P}.remove_all", f"{P}.remove", rules=["PRO-03"]
)
async def test__turning_propagation_off_and_on_and_deleting_move_the_propagation(store: EntityStore) -> None:
    """``propagate`` false removes it downstream, true brings it back; a delete removes it everywhere."""
    await chain(store)
    classifier = EntityClassifications(store)
    await classifier.add_classifications(GUIDS["a"], [tag()])

    await classifier.update_classifications(GUIDS["a"], [tag(propagate=False)])
    off = await names(store, "c")
    await classifier.update_classifications(GUIDS["a"], [tag(propagate=True)])
    on = await names(store, "c")
    await classifier.delete_classification(GUIDS["a"], "c_pii")

    assert (off, on) == ([], [("c_pii", "a")])
    assert await names(store, "b") == []
    assert not await store.type_in_use("c_pii")


@pytest.mark.covers(
    f"{P}.relationship_created",
    f"{P}.entity_changes",
    f"{P}.put_entity",
    "aurelius_atlas_core.relationship_mapper.RelationshipMapper.created",
    rules=["PRO-04", "PRO-10"],
)
async def test__a_new_relationship_carries_what_its_upstream_end_has(store: EntityStore) -> None:
    """Over REST, ``c`` read by ``p3`` takes ``a``'s ``c_pii`` on; a new ``p4`` reading ``c`` and writing ``e`` too."""
    await chain(store)
    await EntityClassifications(store).add_classifications(GUIDS["a"], [tag()])

    await RelationshipStore(store).create(
        AtlasRelationship.model_validate(
            {"typeName": "p_input", "end1": {"guid": GUIDS["c"]}, "end2": {"guid": GUIDS["p3"]}}
        )
    )
    await create(store, data("e"), process("p4", ["c"], ["e"]))

    assert await names(store, "p3") == [("c_pii", "a")]
    assert await names(store, "e") == [("c_pii", "a")]


@pytest.mark.covers(
    f"{P}.relationship_updated",
    f"{P}.handle_blocked",
    f"{P}.evaluate",
    f"{P}.propagatable",
    f"{P}.put_relationship",
    "aurelius_atlas_core.entity_retriever.EntityRetriever.classification_of",
    rules=["PRO-05", "PRO-09"],
)
async def test__propagate_tags_and_blocks_on_a_relationship_change_its_reach(store: EntityStore) -> None:
    """``a.p1`` set to ``NONE`` cuts all off; blocking ``c_pii`` on ``p2.c`` cuts ``c`` only; reads show it."""
    await chain(store)
    await EntityClassifications(store).add_classifications(GUIDS["a"], [tag()])
    relationships = RelationshipStore(store)

    await relationships.update(AtlasRelationship.model_validate({"guid": FLOWS["a.p1"], "propagateTags": "NONE"}))
    cut = (await names(store, "b"), await names(store, "c"))
    await relationships.update(AtlasRelationship.model_validate({"guid": FLOWS["a.p1"], "propagateTags": "ONE_TO_TWO"}))
    blocked = await relationships.update(
        AtlasRelationship.model_validate(
            {
                "guid": FLOWS["p2.c"],
                "blockedPropagatedClassifications": [{"typeName": "c_pii", "entityGuid": GUIDS["a"]}],
            }
        )
    )
    after_block = (await names(store, "b"), await names(store, "c"))
    flowing = codec.loads(codec.dumps((await relationships.get_ext_info_by_id(FLOWS["a.p1"])).to_json()))
    await relationships.update(
        AtlasRelationship.model_validate({"guid": FLOWS["p2.c"], "blockedPropagatedClassifications": []})
    )

    assert cut == ([], [])
    assert after_block == ([("c_pii", "a")], [])
    assert [c["typeName"] for c in codec.loads(codec.dumps(blocked.to_json()))["blockedPropagatedClassifications"]] == [
        "c_pii"
    ]
    assert [c["entityGuid"] for c in flowing["relationship"]["propagatedClassifications"]] == [GUIDS["a"]]
    assert GUIDS["a"] in flowing["referredEntities"]
    assert await names(store, "c") == [("c_pii", "a")]


@pytest.mark.covers(f"{P}.relationship_removed", f"{P}.remove_relationship", rules=["PRO-06"])
async def test__a_removed_relationship_takes_away_only_what_says_so(store: EntityStore) -> None:
    """A soft delete leaves the propagation; a hard one removes a classification's that removes propagations."""
    await chain(store)
    classifier = EntityClassifications(store)
    await classifier.add_classifications(GUIDS["a"], [tag(), tag("c_secret", removePropagationsOnEntityDelete=True)])
    relationships = RelationshipStore(store)

    await relationships.delete_by_id(FLOWS["p2.c"])
    soft = await names(store, "c")
    await RelationshipStore(store, delete_type=DeleteType.HARD).delete_by_id(FLOWS["a.p1"])

    assert soft == [("c_pii", "a"), ("c_secret", "a")]
    assert await names(store, "b") == [("c_pii", "a")]
    assert await names(store, "c") == [("c_pii", "a"), ("c_secret", "a")]


@pytest.mark.covers(f"{P}.listed_by", f"{P}.propagated_to", f"{P}.changed_entities", rules=["PRO-07"])
async def test__deleting_the_classified_entity_removes_or_keeps_the_propagation(store: EntityStore) -> None:
    """``c_secret`` removes its propagation with ``a``; ``c_pii`` stays, ``DELETED``, then ``PURGED`` but listed."""
    await chain(store)
    await EntityClassifications(store).add_classifications(
        GUIDS["a"], [tag(), tag("c_secret", removePropagationsOnEntityDelete=True)]
    )

    await EntityWriter(store).delete_by_id(GUIDS["a"])
    deleted = await EntityClassifications(store).get_classifications(GUIDS["b"])
    await EntityWriter(store).purge_by_ids([GUIDS["a"]])
    purged = await EntityClassifications(store).get_classifications(GUIDS["c"])

    assert [(c.type_name, c.entity_status) for c in deleted] == [("c_pii", "DELETED")]
    assert [(c.type_name, c.entity_status) for c in purged] == [("c_pii", "PURGED")]
    assert await store.type_in_use("c_pii")


@pytest.mark.covers(f"{C}.delete_classification", rules=["PRO-08"])
async def test__a_propagated_classification_is_removed_only_once_its_entity_is_deleted(store: EntityStore) -> None:
    """Not while ``a`` is ``ACTIVE``; after its soft delete ``c`` lets go of it; another name is not associated."""
    await chain(store)
    classifier = EntityClassifications(store)
    await classifier.add_classifications(GUIDS["a"], [tag()])

    with pytest.raises(AtlasError) as active:
        await classifier.delete_classification(GUIDS["c"], "c_pii", GUIDS["a"])
    with pytest.raises(AtlasError) as other:
        await classifier.delete_classification(GUIDS["c"], "c_secret", GUIDS["a"])
    await EntityWriter(store).delete_by_id(GUIDS["a"])
    await classifier.delete_classification(GUIDS["c"], "c_pii", GUIDS["a"])

    assert (active.value.code, active.value.message) == (
        AtlasErrorCode.PROPAGATED_CLASSIFICATION_REMOVAL_NOT_SUPPORTED,
        f"Removal of classification c_pii, which is propagated from entity {GUIDS['a']}, is not supported",
    )
    assert other.value.code is AtlasErrorCode.PROPAGATED_CLASSIFICATION_NOT_ASSOCIATED_WITH_ENTITY
    assert await names(store, "c") == []
    assert await names(store, "b") == [("c_pii", "a")]


@pytest.mark.covers(f"{C}.add_classifications", rules=["PRO-10"])
async def test__a_propagation_that_cannot_be_written_writes_nothing(
    store: EntityStore, documents: MemoryEntityDocuments
) -> None:
    """A failing entity downstream fails the add, and ``a`` has no classification either."""
    await chain(store)
    documents.fail[GUIDS["c"]] = "error"

    with pytest.raises(AtlasError):
        await EntityClassifications(store).add_classifications(GUIDS["a"], [tag()])

    assert (await names(store, "a"), await names(store, "b")) == ([], [])


@pytest.mark.covers("aurelius_atlas_core.relationship_mapper.RelationshipMapper.removed", rules=["PRO-06"])
async def test__an_entity_write_that_removes_a_relationship_removes_what_it_carried(store: EntityStore) -> None:
    """A hard update of ``p1`` without its input takes ``c_secret`` (which removes propagations) off downstream."""
    await chain(store)
    await EntityClassifications(store).add_classifications(
        GUIDS["a"], [tag(), tag("c_secret", removePropagationsOnEntityDelete=True)]
    )
    request = {**process("p1", [], ["b"]), "guid": GUIDS["p1"]}

    await EntityWriter(store, delete_type=DeleteType.HARD).create_or_update(
        AtlasEntitiesWithExtInfo.model_validate({"entities": [request]})
    )

    assert await names(store, "b") == [("c_pii", "a")]
    assert await names(store, "c") == [("c_pii", "a")]


@pytest.mark.covers(
    "aurelius_atlas_core.transaction_view.TransactionView.classified",
    "aurelius_atlas_core.transaction_view.EntityView.classified",
    "aurelius_atlas_core.entity_store.EntityStore.classified",
    rules=["PRO-07"],
)
async def test__a_request_view_finds_classified_entities_as_the_request_changed_them(store: EntityStore) -> None:
    """Stored listings, unless the request's own document of an entity says otherwise."""
    await chain(store)
    await EntityClassifications(store).add_classifications(GUIDS["a"], [tag()])
    found = await store.get(GUIDS["b"])
    assert found is not None
    instance = (found.entity.classification_guids or [])[0]
    unlisted = found.entity.model_copy(update={"classification_guids": None})
    view = TransactionView(
        store, entities={GUIDS["b"]: VersionedEntity(unlisted, found.version)}, relationships={}, removed=()
    )

    stored = {item.entity.guid for item in await store.classified([instance])}
    seen = {item.entity.guid for item in await view.classified([instance])}

    assert GUIDS["b"] in stored
    assert seen == stored - {GUIDS["b"]}
