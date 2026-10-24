"""``EntityMutationResponse`` (ENT-17).

Read from ``org.apache.atlas.model.instance.EntityMutationResponse`` of Atlas 2.4.0.
"""

import pytest
from aurelius_atlas_model.instance import AtlasEntityHeader, EntityMutationResponse, EntityOperation

M = "aurelius_atlas_model.instance.entity_mutation_response.EntityMutationResponse"


def header(guid: str, type_name: str = "t", name: str | None = None) -> AtlasEntityHeader:
    """A header of type ``type_name`` with GUID ``guid`` and, when given, attribute ``name``."""
    return AtlasEntityHeader(guid=guid, type_name=type_name, attributes=None if name is None else {"name": name})


@pytest.mark.covers(f"{M}.partial_updated_entities", rules=["ENT-17"])
def test__partial_updates_are_written_twice_and_read_once() -> None:
    """``getPartialUpdatedEntities`` lacks ``@JsonIgnore``; reading ignores ``partialUpdatedEntities``."""
    body = {
        "mutatedEntities": {"PARTIAL_UPDATE": [{"guid": "g", "status": "ACTIVE", "isIncomplete": False}]},
        "guidAssignments": {"-1": "g"},
    }

    response = EntityMutationResponse.model_validate(
        {**body, "partialUpdatedEntities": [{"guid": "other", "status": "ACTIVE", "isIncomplete": False}]}
    )

    assert response.to_json() == {**body, "partialUpdatedEntities": body["mutatedEntities"]["PARTIAL_UPDATE"]}
    assert EntityMutationResponse.model_validate({"mutatedEntities": {"CREATE": []}}).to_json() == {
        "mutatedEntities": {"CREATE": []}
    }
    assert EntityMutationResponse().to_json() == {}


@pytest.mark.covers(f"{M}.add_entity", f"{M}.get_entities_by_operation", rules=["ENT-17"])
def test__an_entity_is_added_once_and_an_update_of_a_created_one_counts_as_created() -> None:
    """``addEntity``: by GUID per operation; ``UPDATE`` and ``PARTIAL_UPDATE`` of a created GUID become ``CREATE``."""
    response = EntityMutationResponse()

    response.add_entity(EntityOperation.CREATE, header("a"))
    response.add_entity(EntityOperation.UPDATE, header("a"))
    response.add_entity(EntityOperation.PARTIAL_UPDATE, header("a"))
    response.add_entity(EntityOperation.UPDATE, header("b"))
    response.add_entity(EntityOperation.UPDATE, header("b"))
    response.add_entity(EntityOperation.DELETE, header("a"))

    assert [h.guid for h in response.get_entities_by_operation(EntityOperation.CREATE) or []] == ["a"]
    assert [h.guid for h in response.get_entities_by_operation(EntityOperation.UPDATE) or []] == ["b"]
    assert [h.guid for h in response.get_entities_by_operation(EntityOperation.DELETE) or []] == ["a"]
    assert response.get_entities_by_operation(EntityOperation.PURGE) is None
    assert EntityMutationResponse().get_entities_by_operation(EntityOperation.CREATE) is None


@pytest.mark.covers(
    f"{M}.get_created_entities",
    f"{M}.get_updated_entities",
    f"{M}.get_deleted_entities",
    f"{M}.get_purged_entities",
    f"{M}.get_purged_entities_ids",
    f"{M}.get_first_entity_by_operation",
    rules=["ENT-17"],
)
def test__the_entities_of_each_operation() -> None:
    """``getCreatedEntities`` to ``getPurgedEntitiesIds`` and ``getFirstEntityCreated``, …."""
    response = EntityMutationResponse()
    for operation, guid in [
        (EntityOperation.CREATE, "c"),
        (EntityOperation.UPDATE, "u"),
        (EntityOperation.DELETE, "d"),
        (EntityOperation.PURGE, "p1"),
        (EntityOperation.PURGE, "p2"),
    ]:
        response.add_entity(operation, header(guid))

    guids = [
        [h.guid for h in found or []]
        for found in (
            response.get_created_entities(),
            response.get_updated_entities(),
            response.get_deleted_entities(),
            response.get_purged_entities(),
        )
    ]

    assert guids == [["c"], ["u"], ["d"], ["p1", "p2"]]
    assert response.get_purged_entities_ids() == "p1,p2"
    assert EntityMutationResponse().get_purged_entities_ids() is None
    assert (response.get_first_entity_by_operation(EntityOperation.UPDATE) or header("x")).guid == "u"
    assert response.get_first_entity_by_operation(EntityOperation.PARTIAL_UPDATE) is None


@pytest.mark.covers(
    f"{M}.get_entities_by_type_name",
    f"{M}.get_first_entity_by_type_name",
    f"{M}.get_entity_by_type_name_and_attribute",
    rules=["ENT-17"],
)
def test__entities_are_found_by_type_and_attribute() -> None:
    """``getCreatedEntitiesByTypeName``, ``getFirstCreatedEntityByTypeName`` and ``…ByTypeNameAndAttribute``."""
    response = EntityMutationResponse()
    response.add_entity(EntityOperation.CREATE, header("1", "hive_db", "db"))
    response.add_entity(EntityOperation.CREATE, header("2", "hive_table", "t1"))
    response.add_entity(EntityOperation.CREATE, header("3", "hive_table", "t2"))
    create = EntityOperation.CREATE

    assert [h.guid for h in response.get_entities_by_type_name(create, "hive_table")] == ["2", "3"]
    assert response.get_entities_by_type_name(EntityOperation.UPDATE, "hive_table") == []
    assert (response.get_first_entity_by_type_name(create, "hive_table") or header("x")).guid == "2"
    assert response.get_first_entity_by_type_name(create, "hive_column") is None
    assert (
        response.get_entity_by_type_name_and_attribute(create, "hive_table", "name", "t2") or header("x")
    ).guid == "3"
    assert response.get_entity_by_type_name_and_attribute(create, "hive_table", "name", None) is None
    assert response.get_entity_by_type_name_and_attribute(create, "hive_db", "name", "t1") is None
