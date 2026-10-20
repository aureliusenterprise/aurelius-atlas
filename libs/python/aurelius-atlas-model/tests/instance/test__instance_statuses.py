"""The four enums of the instance models (ENT-09).

Entity and relationship status, entity operation and term assignment status, read from ``AtlasEntity.Status``,
``AtlasRelationship.Status``, ``EntityMutations.EntityOperation`` and ``AtlasTermAssignmentStatus`` of Atlas
2.4.0.
"""

from enum import StrEnum

import pytest
from aurelius_atlas_model.instance import (
    AtlasClassification,
    AtlasEntity,
    AtlasRelatedObjectId,
    AtlasTermAssignmentHeader,
    AtlasTermAssignmentStatus,
    EntityMutationResponse,
    EntityOperation,
    EntityStatus,
    RelationshipStatus,
)
from pydantic import ValidationError


@pytest.mark.covers(rules=["ENT-09"])
@pytest.mark.parametrize(
    ("enum", "names"),
    [
        (EntityStatus, ["ACTIVE", "DELETED", "PURGED"]),
        (RelationshipStatus, ["ACTIVE", "DELETED"]),
        (EntityOperation, ["CREATE", "UPDATE", "PARTIAL_UPDATE", "DELETE", "PURGE"]),
        (
            AtlasTermAssignmentStatus,
            ["DISCOVERED", "PROPOSED", "IMPORTED", "VALIDATED", "DEPRECATED", "OBSOLETE", "OTHER"],
        ),
    ],
)
def test__each_enum_has_java_s_names_in_order(enum: type[StrEnum], names: list[str]) -> None:
    """The values are the Java constants, written by name."""
    assert [member.value for member in enum] == names


@pytest.mark.covers(rules=["ENT-09"])
def test__statuses_are_read_and_written_by_name_with_case() -> None:
    """Each enum field reads its Java names and writes them back."""
    entity = AtlasEntity.model_validate({"status": "DELETED"})
    related = AtlasRelatedObjectId.model_validate({"entityStatus": "PURGED", "relationshipStatus": "ACTIVE"})
    meaning = AtlasTermAssignmentHeader.model_validate({"status": "VALIDATED"})
    response = EntityMutationResponse.model_validate({"mutatedEntities": {"DELETE": []}})

    assert entity.to_json()["status"] == "DELETED"
    assert (related.entity_status, related.relationship_status) == (EntityStatus.PURGED, RelationshipStatus.ACTIVE)
    assert meaning.to_json()["status"] == "VALIDATED"
    assert response.to_json() == {"mutatedEntities": {"DELETE": []}}


@pytest.mark.covers(rules=["ENT-09"])
@pytest.mark.parametrize(
    ("model", "body"),
    [
        (AtlasEntity, {"status": "active"}),
        (AtlasClassification, {"entityStatus": "GONE"}),
        (AtlasRelatedObjectId, {"relationshipStatus": "PURGED"}),
        (AtlasTermAssignmentHeader, {"status": "Discovered"}),
        (EntityMutationResponse, {"mutatedEntities": {"create": []}}),
    ],
)
def test__any_other_value_is_rejected(model: type[AtlasEntity], body: dict[str, object]) -> None:
    """Jackson fails on an enum constant it does not know, or in another case."""
    with pytest.raises(ValidationError):
        model.model_validate(body)
