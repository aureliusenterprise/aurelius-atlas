"""Classifications attached directly to entities (CLS-02 to CLS-12) on the in-memory documents.

The expected classifications, errors and responses are read from ``AtlasEntityStoreV2`` (``addClassifications``,
``addClassification``, ``updateClassifications``, ``deleteClassification``, ``getClassification``,
``validateEntityAssociations``), ``EntityGraphMapper`` (``addClassifications``, ``updateClassifications``,
``mapClassification``, ``mapAttributesAndClassifications``), ``EntityGraphRetriever#toAtlasClassification`` and
``DeleteHandlerV1#deleteAllClassifications`` of Apache Atlas 2.4.0.
"""

from typing import Any

import pytest
from aurelius_atlas_core.delete_type import DeleteType
from aurelius_atlas_core.entity_classifications import EntityClassifications
from aurelius_atlas_core.entity_retriever import EntityRetriever
from aurelius_atlas_core.entity_store import EntityStore
from aurelius_atlas_core.entity_writer import EntityWriter
from aurelius_atlas_core.testing.entity_samples import sample_registry
from aurelius_atlas_core.testing.memory import MemoryEntityDocuments
from aurelius_atlas_model import codec
from aurelius_atlas_model.errors import AtlasError, AtlasErrorCode
from aurelius_atlas_model.instance import AtlasClassification, AtlasEntitiesWithExtInfo

C = "aurelius_atlas_core.entity_classifications.EntityClassifications"
NOW = 5000


@pytest.fixture
def documents() -> MemoryEntityDocuments:
    """The documents the store keeps entities in."""
    return MemoryEntityDocuments()


@pytest.fixture
def store(documents: MemoryEntityDocuments) -> EntityStore:
    """A store of the sample, write and classification types at time ``NOW``."""
    return EntityStore(sample_registry(classifications=True), documents, clock=lambda: NOW / 1000)


GUIDS: dict[str, str] = {}


@pytest.fixture(autouse=True)
def _guids() -> None:
    GUIDS.clear()


def g(request_guid: str) -> str:
    """The GUID assigned to the request's ``request_guid``."""
    return GUIDS[request_guid]


def as_json(value: Any) -> Any:  # noqa: ANN401 - Atlas JSON
    """A model's JSON as a client reads it."""
    return codec.loads(codec.dumps(value.to_json()))


async def write(store: EntityStore, *entities: dict[str, Any], delete_type: DeleteType = DeleteType.SOFT) -> Any:  # noqa: ANN401
    """The JSON answer to creating or updating these entities; their GUIDs are kept for ``g``."""
    request = AtlasEntitiesWithExtInfo.model_validate({"entities": list(entities)})
    answer = as_json(await EntityWriter(store, delete_type=delete_type).create_or_update(request))
    GUIDS.update(answer.get("guidAssignments", {}))
    return answer


def entity(type_name: str, guid: str, **attributes: Any) -> dict[str, Any]:  # noqa: ANN401 - Atlas JSON
    """An entity as Atlas JSON."""
    return {"typeName": type_name, "guid": guid, "attributes": attributes}


def tag(type_name: str, **more: Any) -> AtlasClassification:  # noqa: ANN401 - Atlas JSON
    """A classification as a request gives it."""
    return AtlasClassification.model_validate({"typeName": type_name, **more})


async def classifications(store: EntityStore, guid: str) -> list[dict[str, Any]]:
    """The entity's classifications as ``GET guid/{guid}/classifications`` lists them."""
    return [as_json(found) for found in await EntityClassifications(store).get_classifications(guid)]


async def failure(call: Any) -> tuple[AtlasErrorCode, str]:  # noqa: ANN401 - an awaitable
    """The code and message a call fails with."""
    with pytest.raises(AtlasError) as raised:
        await call
    return raised.value.code, raised.value.message


@pytest.mark.covers(
    f"{C}.add_classifications",
    f"{C}.get_classifications",
    f"{C}.get_classification",
    "aurelius_atlas_core.entity_retriever.EntityRetriever.classifications",
    "aurelius_atlas_core.entity_store.EntityStore.get_classifications",
    "aurelius_atlas_core.stored_classification.StoredClassification.to_classification",
    "aurelius_atlas_core.entity_mapper.EntityMapper.struct_attributes",
    rules=["CLS-02", "CLS-03", "CLS-04", "CLS-05"],
)
async def test__added_classifications_take_atlass_defaults_and_read_with_the_entity(store: EntityStore) -> None:
    """Defaults, every attribute of the type, validity periods; the entity, its header and the lookups show them."""
    await write(store, entity("s_table", "-1", qualifiedName="t@cl"))
    classifier = EntityClassifications(store, user="ann")
    period = {"startTime": "2024/01/01 00:00:00", "endTime": "2024/12/31 23:59:59", "timeZone": "UTC"}

    await classifier.add_classifications(
        g("-1"), [tag("c_pii", attributes={"level": "2"}, validityPeriods=[period]), tag("c_tabular", propagate=False)]
    )
    read = as_json(await EntityRetriever(store).entity_with_ext_info(g("-1")))["entity"]
    header = as_json(await EntityRetriever(store).header(g("-1")))
    found = await store.get(g("-1"))

    assert read["classifications"] == [
        {
            "typeName": "c_pii",
            "attributes": {"level": 2, "note": None, "since": 0},
            "entityGuid": g("-1"),
            "entityStatus": "ACTIVE",
            "propagate": True,
            "validityPeriods": [period],
            "removePropagationsOnEntityDelete": False,
        },
        {
            "typeName": "c_tabular",
            "entityGuid": g("-1"),
            "entityStatus": "ACTIVE",
            "propagate": False,
            "removePropagationsOnEntityDelete": False,
        },
    ]
    assert (header["classificationNames"], header["classifications"]) == (
        ["c_pii", "c_tabular"],
        read["classifications"],
    )
    assert found is not None
    assert (found.entity.update_time, found.entity.updated_by) == (NOW, "ann")
    assert await classifications(store, g("-1")) == read["classifications"]
    assert as_json(await classifier.get_classification(g("-1"), "C_PII"))["typeName"] == "c_pii"
    assert await failure(classifier.get_classification(g("-1"), "c_secret")) == (
        AtlasErrorCode.CLASSIFICATION_NOT_FOUND,
        "Given classification c_secret was invalid",
    )


@pytest.mark.covers(f"{C}.add_classifications", rules=["CLS-04", "CLS-05"])
async def test__an_add_is_checked_before_anything_is_written(store: EntityStore) -> None:
    """Parameters, the entity, the types and values, then each association; a propagated one is left out."""
    await write(store, entity("s_table", "-1", qualifiedName="t@cl"), entity("s_column", "-2", qualifiedName="c@cl"))
    classifier = EntityClassifications(store)
    await classifier.add_classifications(g("-1"), [tag("c_pii")])
    bad_period = {"startTime": "never", "timeZone": "UTC"}

    assert await failure(classifier.add_classifications("", [tag("c_pii")])) == (
        AtlasErrorCode.INVALID_PARAMETERS,
        "invalid parameters: Guid(s) not specified",
    )
    assert (await failure(classifier.add_classifications(g("-1"), [])))[1].endswith("classifications(s) not specified")
    assert (await failure(classifier.add_classifications("nope", [tag("c_pii")])))[0] is (
        AtlasErrorCode.INSTANCE_GUID_NOT_FOUND
    )
    assert (await failure(classifier.add_classifications(g("-1"), [tag("nope")])))[0] is (
        AtlasErrorCode.CLASSIFICATION_NOT_FOUND
    )
    assert (await failure(classifier.add_classifications(g("-1"), [tag("c_owned")])))[0] is (
        AtlasErrorCode.INVALID_PARAMETERS
    )
    assert (await failure(classifier.add_classifications(g("-1"), [tag("c_secret", validityPeriods=[bad_period])])))[
        0
    ] is (AtlasErrorCode.INVALID_PARAMETERS)
    assert await failure(classifier.add_classifications(g("-1"), [tag("c_secret"), tag("c_pii")])) == (
        AtlasErrorCode.INVALID_PARAMETERS,
        f"invalid parameters: entity: {g('-1')}, already associated with classification: c_pii",
    )
    assert (await failure(classifier.add_classifications(g("-2"), [tag("c_tabular")])))[0] is (
        AtlasErrorCode.INVALID_ENTITY_FOR_CLASSIFICATION
    )
    await classifier.add_classifications(g("-2"), [tag("c_pii", propagate=True, entityGuid=g("-1")), tag("c_secret")])
    assert [found["typeName"] for found in await classifications(store, g("-1"))] == ["c_pii"]
    assert [found["typeName"] for found in await classifications(store, g("-2"))] == ["c_secret"]


@pytest.mark.covers(f"{C}.add_classification", rules=["CLS-07"])
async def test__one_classification_is_added_to_many_entities_all_or_none(store: EntityStore) -> None:
    """Each entity is checked before any changes; then each gets an instance of its own."""
    await write(store, entity("s_table", "-1", qualifiedName="a@cl"), entity("s_table", "-2", qualifiedName="b@cl"))
    classifier = EntityClassifications(store)
    await classifier.add_classifications(g("-2"), [tag("c_secret")])

    assert (await failure(classifier.add_classification([g("-1"), g("-2")], tag("c_secret"))))[0] is (
        AtlasErrorCode.INVALID_PARAMETERS
    )
    assert await classifications(store, g("-1")) == []
    assert (await failure(classifier.add_classification([], tag("c_pii"))))[1].endswith("Guid(s) not specified")
    assert (await failure(classifier.add_classification([g("-1")], None)))[1].endswith("classification not specified")
    await classifier.add_classification([g("-1"), g("-2")], tag("c_pii", attributes={"note": "x"}))
    for guid in (g("-1"), g("-2")):
        assert (await classifications(store, guid))[-1]["attributes"]["note"] == "x"
    listed = [found.entity.classification_guids or [] for found in (await store.get_many([g("-1"), g("-2")])).values()]
    assert set(listed[0]) & set(listed[1]) == set()


@pytest.mark.covers(f"{C}.update_classifications", rules=["CLS-08"])
async def test__an_update_changes_given_attributes_periods_and_flags(store: EntityStore) -> None:
    """Attributes merge; validity periods and flags change only when given; the entity's update time moves."""
    await write(store, entity("s_table", "-1", qualifiedName="t@cl"))
    classifier = EntityClassifications(store)
    await classifier.add_classifications(g("-1"), [tag("c_pii", attributes={"level": 1, "note": "a"})])

    await classifier.update_classifications(g("-1"), [tag("c_pii", attributes={"level": 3}, propagate=False)])
    updated = (await classifications(store, g("-1")))[0]

    assert (updated["attributes"], updated["propagate"], updated["removePropagationsOnEntityDelete"]) == (
        {"level": 3, "note": "a", "since": 0},
        False,
        False,
    )
    assert (await failure(classifier.update_classifications("", [tag("c_pii")])))[1].endswith("Guid not specified")
    assert (await failure(classifier.update_classifications(g("-1"), None)))[0] is AtlasErrorCode.INVALID_PARAMETERS
    assert await failure(classifier.update_classifications(g("-1"), [tag("c_pii", entityGuid="other")])) == (
        AtlasErrorCode.CLASSIFICATION_UPDATE_FROM_PROPAGATED_ENTITY,
        "Update to classification c_pii is not allowed from propagated entity",
    )
    assert await failure(classifier.update_classifications(g("-1"), [tag("c_secret")])) == (
        AtlasErrorCode.CLASSIFICATION_NOT_ASSOCIATED_WITH_ENTITY,
        "Classification c_secret is not associated with entity",
    )


@pytest.mark.covers(f"{C}.delete_classification", rules=["CLS-09", "CLS-12"])
async def test__a_delete_removes_the_instance_and_the_type_is_free_again(store: EntityStore) -> None:
    """None attached, another name, a propagated one; then the removal, whatever the delete type."""
    await write(store, entity("s_table", "-1", qualifiedName="t@cl"))
    classifier = EntityClassifications(store)

    assert await failure(classifier.delete_classification(g("-1"), "c_pii")) == (
        AtlasErrorCode.NO_CLASSIFICATIONS_FOUND_FOR_ENTITY,
        f"No classifications associated with entity: {g('-1')}",
    )
    await classifier.add_classifications(g("-1"), [tag("c_pii")])
    assert await store.type_in_use("c_pii")
    assert (await failure(classifier.delete_classification(g("-1"), "C_PII")))[0] is (
        AtlasErrorCode.CLASSIFICATION_NOT_ASSOCIATED_WITH_ENTITY
    )
    assert await failure(classifier.delete_classification(g("-1"), "c_pii", "other")) == (
        AtlasErrorCode.PROPAGATED_CLASSIFICATION_NOT_ASSOCIATED_WITH_ENTITY,
        f"Propagated classification c_pii is not associated with entity {g('-1')}, it is associated with entity other",
    )
    assert (await failure(classifier.delete_classification("", "c_pii")))[1].endswith("Guid(s) not specified")
    assert (await failure(classifier.delete_classification(g("-1"), "")))[1].endswith("classifications not specified")
    await classifier.delete_classification(g("-1"), "c_pii", g("-1"))
    found = await store.get(g("-1"))

    assert await classifications(store, g("-1")) == []
    assert found is not None
    assert found.entity.classification_guids is None
    assert not await store.type_in_use("c_pii")


@pytest.mark.covers(
    "aurelius_atlas_core.entity_writer.EntityWriter.create_or_update", f"{C}.attached", rules=["CLS-10"]
)
async def test__a_create_attaches_its_classifications_and_an_update_ignores_them(store: EntityStore) -> None:
    """Unchecked but for the type; the ``CREATE`` header shows none; an unknown type fails."""
    answer = await write(
        store, {**entity("s_column", "-1", qualifiedName="c@cl"), "classifications": [{"typeName": "c_tabular"}]}
    )
    update = await write(
        store,
        {**entity("s_column", g("-1"), qualifiedName="c@cl", comment="x"), "classifications": [{"typeName": "c_pii"}]},
    )

    assert answer["mutatedEntities"]["CREATE"][0]["classificationNames"] == []
    assert answer["mutatedEntities"]["CREATE"][0]["classifications"] == []
    assert [found["typeName"] for found in await classifications(store, g("-1"))] == ["c_tabular"]
    assert update["mutatedEntities"]["UPDATE"][0]["classificationNames"] == ["c_tabular"]
    with pytest.raises(AtlasError) as raised:
        await write(
            store, {**entity("s_column", "-2", qualifiedName="d@cl"), "classifications": [{"typeName": "nope"}]}
        )
    assert raised.value.code is AtlasErrorCode.CLASSIFICATION_NOT_FOUND


@pytest.mark.covers("aurelius_atlas_core.entity_writer.EntityWriter.delete_by_id", rules=["CLS-11"])
async def test__a_soft_delete_keeps_classifications_deleted_and_a_purge_removes_them(store: EntityStore) -> None:
    """``entityStatus`` ``DELETED`` after the delete; the purge's header has them, and then they are gone."""
    await write(store, entity("s_table", "-1", qualifiedName="t@cl"), entity("s_table", "-2", qualifiedName="u@cl"))
    classifier = EntityClassifications(store)
    await classifier.add_classifications(g("-1"), [tag("c_pii")])
    await classifier.add_classifications(g("-2"), [tag("c_pii")])
    writer = EntityWriter(store)

    await writer.delete_by_id(g("-1"))
    deleted = await classifications(store, g("-1"))
    purged = as_json(await writer.purge_by_ids([g("-1")]))
    await EntityWriter(store, delete_type=DeleteType.HARD).delete_by_id(g("-2"))

    assert [found["entityStatus"] for found in deleted] == ["DELETED"]
    assert [found["typeName"] for found in purged["mutatedEntities"]["PURGE"][0]["classifications"]] == ["c_pii"]
    assert not await store.type_in_use("c_pii")


@pytest.mark.covers(
    "aurelius_atlas_core.transaction_view.TransactionView.get_classifications",
    "aurelius_atlas_core.transaction_view.EntityView.get_classifications",
    rules=["CLS-11"],
)
async def test__an_owned_entity_an_update_drops_keeps_its_classifications_deleted(store: EntityStore) -> None:
    """The delete through the request's view marks them as the entity: ``DELETED``."""
    await write(store, entity("s_column", "-1", qualifiedName="c@cl"))
    await write(
        store, entity("s_table", "-2", qualifiedName="t@cl", columns=[{"guid": g("-1"), "typeName": "s_column"}])
    )
    await EntityClassifications(store).add_classifications(g("-1"), [tag("c_pii")])

    await write(store, entity("s_table", g("-2"), qualifiedName="t@cl", columns=[]))

    assert [found["entityStatus"] for found in await classifications(store, g("-1"))] == ["DELETED"]


@pytest.mark.covers(f"{C}.add_classifications", rules=["CLS-05"])
async def test__a_lost_race_is_run_again_and_a_failed_write_is_an_internal_error(
    store: EntityStore, documents: MemoryEntityDocuments
) -> None:
    """One conflict runs the add again; a write error fails it with ``INTERNAL_ERROR``."""
    await write(store, entity("s_table", "-1", qualifiedName="t@cl"))
    classifier = EntityClassifications(store)

    documents.fail[g("-1")] = "conflict"
    await classifier.add_classifications(g("-1"), [tag("c_pii")])
    documents.fail[g("-1")] = "error"

    assert (await failure(classifier.add_classifications(g("-1"), [tag("c_secret")])))[0] is (
        AtlasErrorCode.INTERNAL_ERROR
    )
    assert [found["typeName"] for found in await classifications(store, g("-1"))] == ["c_pii"]
