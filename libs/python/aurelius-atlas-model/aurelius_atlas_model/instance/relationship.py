"""``AtlasRelationship``: an instance of a relationship type between two entities (REL-01)."""

from pydantic import Field

from aurelius_atlas_model.base import Timestamp
from aurelius_atlas_model.instance.classification import AtlasClassification
from aurelius_atlas_model.instance.entity import next_internal_id
from aurelius_atlas_model.instance.object_id import AtlasObjectId
from aurelius_atlas_model.instance.relationship_status import RelationshipStatus
from aurelius_atlas_model.instance.struct import AtlasStruct
from aurelius_atlas_model.typedef import PropagateTags


class AtlasRelationship(AtlasStruct):
    """A relationship: a struct with a GUID, its two ends, a label, tag propagation, a status and audit fields.

    Read with the defaults of Java's no-argument constructor, whose ``init()`` assigns a temporary GUID and clears
    ``propagateTags`` and ``status`` (REL-01).
    """

    guid: str | None = Field(default_factory=next_internal_id)
    home_id: str | None = None
    provenance_type: int | None = 0
    end1: AtlasObjectId | None = None
    end2: AtlasObjectId | None = None
    label: str | None = None
    propagate_tags: PropagateTags | None = None
    status: RelationshipStatus | None = None
    created_by: str | None = None
    updated_by: str | None = None
    create_time: Timestamp | None = None
    update_time: Timestamp | None = None
    version: int | None = 0
    propagated_classifications: list[AtlasClassification] | None = None
    blocked_propagated_classifications: list[AtlasClassification] | None = None
