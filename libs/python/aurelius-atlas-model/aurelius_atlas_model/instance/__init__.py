"""Atlas entities and their parts, one module per Java class of ``org.apache.atlas.model.instance`` (DD-037).

Ported from Apache Atlas 2.4.0. The models read and write Atlas's REST JSON as the typedef models do (ENT-01);
validating their values against the types is 2.1b.
"""

from aurelius_atlas_model.instance.classification import AtlasClassification, AtlasClassifications
from aurelius_atlas_model.instance.classification_associate_request import ClassificationAssociateRequest
from aurelius_atlas_model.instance.entities_with_ext_info import AtlasEntitiesWithExtInfo
from aurelius_atlas_model.instance.entity import AtlasEntity, next_internal_id
from aurelius_atlas_model.instance.entity_ext_info import AtlasEntityExtInfo
from aurelius_atlas_model.instance.entity_header import AtlasEntityHeader
from aurelius_atlas_model.instance.entity_headers import AtlasEntityHeaders
from aurelius_atlas_model.instance.entity_mutation_response import EntityMutationResponse
from aurelius_atlas_model.instance.entity_operation import EntityOperation
from aurelius_atlas_model.instance.entity_status import EntityStatus
from aurelius_atlas_model.instance.entity_with_ext_info import AtlasEntityWithExtInfo
from aurelius_atlas_model.instance.object_id import AtlasObjectId
from aurelius_atlas_model.instance.related_object_id import AtlasRelatedObjectId
from aurelius_atlas_model.instance.relationship import AtlasRelationship
from aurelius_atlas_model.instance.relationship_status import RelationshipStatus
from aurelius_atlas_model.instance.relationship_with_ext_info import AtlasRelationshipWithExtInfo
from aurelius_atlas_model.instance.struct import AtlasStruct
from aurelius_atlas_model.instance.term_assignment_header import AtlasTermAssignmentHeader
from aurelius_atlas_model.instance.term_assignment_status import AtlasTermAssignmentStatus
from aurelius_atlas_model.instance.time_boundary import TimeBoundary

__all__ = [
    "AtlasClassification",
    "AtlasClassifications",
    "AtlasEntitiesWithExtInfo",
    "AtlasEntity",
    "AtlasEntityExtInfo",
    "AtlasEntityHeader",
    "AtlasEntityHeaders",
    "AtlasEntityWithExtInfo",
    "AtlasObjectId",
    "AtlasRelatedObjectId",
    "AtlasRelationship",
    "AtlasRelationshipWithExtInfo",
    "AtlasStruct",
    "AtlasTermAssignmentHeader",
    "AtlasTermAssignmentStatus",
    "ClassificationAssociateRequest",
    "EntityMutationResponse",
    "EntityOperation",
    "EntityStatus",
    "RelationshipStatus",
    "TimeBoundary",
    "next_internal_id",
]
