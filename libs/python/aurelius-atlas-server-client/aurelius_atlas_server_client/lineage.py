"""The Atlas ``v2/lineage/{guid}`` body, as the server client's contract (CL-12, LM-04).

Moved here from ``aurelius_atlas_lineage_model.lineage`` by increment 8.4 (DD-114):
the body is the *server's* answer — the Aurelius ``LineageInfo`` wire shape of
``libs/m4i-atlas-core`` (ADR 055 R4), stated as pydantic (DD-109) so the serving
side (5.1's lineage feed) and every calling side (8.2 today) validate one class.

The *flattening* is not here: ``PROCESS_TYPES``, ``LINEAGE_RULES`` and
``flatten_relations`` are 8.2's app logic and stay in the app (8.4 spec, CL-12).
"""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

type Direction = Literal["BOTH", "INPUT", "OUTPUT"]
"""The lineage directions Atlas accepts (the legacy's ``LineageDirection`` enum, LM-01)."""


class EntityHeaderLite(BaseModel):
    """The fields of an Atlas entity header the lineage body carries (LM-02).

    Extra fields are ignored — Atlas's header carries classifications,
    labels, statuses and more that the lineage rows never use.
    """

    model_config = ConfigDict(populate_by_name=True, extra="ignore")

    guid: str
    type_name: str = Field(alias="typeName", default="")
    display_text: str | None = Field(alias="displayText", default=None)


class LineageRelation(BaseModel):
    """One Atlas lineage relation: an edge between two entity guids (LM-02)."""

    model_config = ConfigDict(populate_by_name=True, extra="ignore")

    from_entity_id: str = Field(alias="fromEntityId")
    relationship_id: str = Field(alias="relationshipId")
    to_entity_id: str = Field(alias="toEntityId")


class LineageInfo(BaseModel):
    """The body of Atlas's ``v2/lineage/{guid}`` answer (LM-04).

    The legacy's ``LineageInfo`` dataclass, as a pydantic model: the camelCase
    wire names are the aliases; ``baseEntityGuid``, ``lineageDepth`` and
    ``lineageDirection`` exist upstream but the flattening reads none of them.
    """

    model_config = ConfigDict(populate_by_name=True, extra="ignore")

    guid_entity_map: dict[str, EntityHeaderLite] = Field(alias="guidEntityMap", default_factory=dict)
    relations: list[LineageRelation] = Field(default_factory=list)
