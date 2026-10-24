"""The Atlas ``v2/lineage/{guid}`` body, as the server client's contract (CL-12, LM-04).

Moved here from ``aurelius_atlas_lineage_model.lineage`` by increment 8.4 (DD-114):
the body is the *server's* answer — the Aurelius ``LineageInfo`` wire shape of
``libs/m4i-atlas-core`` (ADR 055 R4), stated as pydantic (DD-109) so the serving
side (5.1's lineage feed) and every calling side (8.2 today) validate one class.

The *flattening* is not here: ``PROCESS_TYPES``, ``LINEAGE_RULES`` and
``flatten_relations`` are 8.2's app logic and stay in the app (8.4 spec, CL-12).
"""

from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

type Direction = Literal["BOTH", "INPUT", "OUTPUT"]
"""The lineage directions Atlas accepts (the legacy's ``LineageDirection`` enum, LM-01)."""


# LM-02. Extra fields are ignored — Atlas's header carries classifications,
# labels, statuses and more that the lineage rows never use.
class EntityHeaderLite(BaseModel):
    """The fields of an Atlas entity header the lineage body carries."""

    model_config = ConfigDict(populate_by_name=True, extra="ignore")

    guid: UUID = Field(description="The entity's guid.")

    type_name: str = Field(alias="typeName", default="", description="The entity's type name.")

    display_text: str | None = Field(
        alias="displayText",
        default=None,
        description="The entity's display text, when it has one.",
    )


# LM-02.
class LineageRelation(BaseModel):
    """One Atlas lineage relation: an edge between two entity guids."""

    model_config = ConfigDict(populate_by_name=True, extra="ignore")

    from_entity_id: UUID = Field(alias="fromEntityId", description="The guid of the source entity.")

    relationship_id: str = Field(alias="relationshipId", description="The id of the lineage relation.")

    to_entity_id: UUID = Field(alias="toEntityId", description="The guid of the target entity.")


# LM-04. The legacy's ``LineageInfo`` dataclass, as a pydantic model: the
# camelCase wire names are the aliases; ``baseEntityGuid``, ``lineageDepth``
# and ``lineageDirection`` exist upstream but the flattening reads none of them.
class LineageInfo(BaseModel):
    """The body of Atlas's ``v2/lineage/{guid}`` answer."""

    model_config = ConfigDict(populate_by_name=True, extra="ignore")

    guid_entity_map: dict[UUID, EntityHeaderLite] = Field(
        alias="guidEntityMap",
        default_factory=dict,
        description="The entity headers of the lineage graph, keyed by guid.",
    )

    relations: list[LineageRelation] = Field(
        default_factory=list,
        description="The lineage edges of the graph.",
    )
