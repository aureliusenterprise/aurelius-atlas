"""``AtlasLineageInfo`` and its parts: a lineage graph as ``LineageREST`` answers it (LIN-05, LIN-07)."""

from enum import StrEnum

from pydantic import Field

from aurelius_atlas_model.base import AtlasModel, JavaBool, JavaInt
from aurelius_atlas_model.instance import AtlasEntityHeader


class LineageDirection(StrEnum):
    """``AtlasLineageInfo.LineageDirection``."""

    INPUT = "INPUT"
    OUTPUT = "OUTPUT"
    BOTH = "BOTH"


class LineageOnDemandConstraints(AtlasModel):
    """``LineageOnDemandConstraints``: how far lineage on demand goes from one entity (LIN-06)."""

    direction: LineageDirection | None = None
    input_relations_limit: JavaInt = 0
    output_relations_limit: JavaInt = 0
    depth: JavaInt = 0


class LineageRelation(AtlasModel):
    """``LineageRelation``: an edge of the lineage, from data set to process or process to data set (LIN-04)."""

    from_entity_id: str | None = None
    to_entity_id: str | None = None
    relationship_id: str | None = None


class LineageInfoOnDemand(AtlasModel):
    """``LineageInfoOnDemand``: what lineage on demand left out at an entity, and what it counted (LIN-07).

    Atlas serializes the two flags and the two counts; its limits and constraints are not shown.
    """

    has_more_inputs: JavaBool = False
    has_more_outputs: JavaBool = False
    input_relations_count: JavaInt = 0
    output_relations_count: JavaInt = 0


class AtlasLineageInfo(AtlasModel):
    """``AtlasLineageInfo``: the entities and relations of an entity's lineage; ``visitedEdges`` is not shown."""

    base_entity_guid: str | None = None
    lineage_direction: LineageDirection | None = None
    lineage_depth: JavaInt = 0
    guid_entity_map: dict[str, AtlasEntityHeader] | None = None
    relations: list[LineageRelation] | None = None
    relations_on_demand: dict[str, LineageInfoOnDemand] | None = None
    lineage_on_demand_payload: dict[str, LineageOnDemandConstraints] | None = Field(default=None)
