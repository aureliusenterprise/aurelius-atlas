"""``EntityLineageService``: an entity's lineage, over the relationships of the process edges (LIN-02 to LIN-07).

Atlas's default traversal (``getLineageInfoV2``) and lineage on demand (``getLineageInfoOnDemand``) walk the
``__Process.inputs`` and ``__Process.outputs`` edges; here those are relationships, each going out of end 1 (the
process) into end 2 (the data set), read through the entities that list them (DD-061, DD-245).
"""

from dataclasses import dataclass, field

from aurelius_atlas_model.errors import AtlasError, AtlasErrorCode
from aurelius_atlas_model.instance import AtlasEntityHeader
from aurelius_atlas_model.lineage import (
    AtlasLineageInfo,
    LineageDirection,
    LineageInfoOnDemand,
    LineageOnDemandConstraints,
    LineageRelation,
)
from aurelius_atlas_typesystem.edge_direction import EdgeDirection

from aurelius_atlas_core.entity_retriever import EntityRetriever
from aurelius_atlas_core.entity_store import EntityStore
from aurelius_atlas_core.graph_helper import edges_for_label
from aurelius_atlas_core.stored_relationship import StoredRelationship

PROCESS_INPUTS_EDGE = "__Process.inputs"
PROCESS_OUTPUTS_EDGE = "__Process.outputs"
DATA_SET_SUPER_TYPE = "DataSet"
PROCESS_SUPER_TYPE = "Process"
DEFAULT_LINEAGE_MAX_NODE_COUNT = 9000
LINEAGE_ON_DEMAND_DEFAULT_DEPTH = 3
LINEAGE_ON_DEMAND_ENABLED = "atlas.lineage.on.demand.enabled"
SEPARATOR = "->"


@dataclass
class _OnDemand:
    """``LineageInfoOnDemand``: an entity's relation counts against its constraints (LIN-07)."""

    constraints: LineageOnDemandConstraints
    has_more_inputs: bool = False
    has_more_outputs: bool = False
    input_count: int = 0
    output_count: int = 0
    input_reached: bool = False
    output_reached: bool = False

    def increment_input(self) -> None:
        """``incrementInputRelationsCount``."""
        if self.has_more_inputs:
            return
        if self.input_reached:
            self.has_more_inputs = True
            return
        self.input_count += 1
        if self.input_count == self.constraints.input_relations_limit:
            self.input_reached = True

    def increment_output(self) -> None:
        """``incrementOutputRelationsCount``."""
        if self.has_more_outputs:
            return
        if self.output_reached:
            self.has_more_outputs = True
            return
        self.output_count += 1
        if self.output_count == self.constraints.output_relations_limit:
            self.output_reached = True


@dataclass
class _Lineage:
    """The lineage being built: ``AtlasLineageInfo`` with its ``visitedEdges``."""

    guid: str
    direction: LineageDirection
    depth: int
    entities: dict[str, AtlasEntityHeader] = field(default_factory=dict)
    relations: list[LineageRelation] = field(default_factory=list)
    visited: set[str] = field(default_factory=set)
    on_demand: dict[str, _OnDemand] = field(default_factory=dict)

    def info(self) -> AtlasLineageInfo:
        return AtlasLineageInfo(
            base_entity_guid=self.guid,
            lineage_direction=self.direction,
            lineage_depth=self.depth,
            guid_entity_map=self.entities,
            relations=self.relations,
            relations_on_demand={
                guid: LineageInfoOnDemand(
                    has_more_inputs=found.has_more_inputs,
                    has_more_outputs=found.has_more_outputs,
                    input_relations_count=found.input_count,
                    output_relations_count=found.output_count,
                )
                for guid, found in self.on_demand.items()
            },
        )


class EntityLineageService:
    """The lineage of the entities of ``store``, with Atlas's lineage settings."""

    def __init__(
        self,
        store: EntityStore,
        *,
        on_demand_enabled: bool = False,
        on_demand_default_node_count: int = 3,
        max_node_count: int = DEFAULT_LINEAGE_MAX_NODE_COUNT,
    ) -> None:
        self._store = store
        self._retriever = EntityRetriever(store)
        self._on_demand_enabled = on_demand_enabled
        self._default_node_count = on_demand_default_node_count
        self._max_node_count = min(DEFAULT_LINEAGE_MAX_NODE_COUNT, max_node_count)
        self._edges: dict[str, list[StoredRelationship]] = {}

    async def get_atlas_lineage_info(self, guid: str, direction: LineageDirection, depth: int) -> AtlasLineageInfo:
        """``getAtlasLineageInfo``: the lineage ``depth`` deep (0 for all) in ``direction`` (LIN-03 to LIN-05).

        Raises:
            AtlasError: ``INSTANCE_GUID_NOT_FOUND`` or ``INVALID_LINEAGE_ENTITY_TYPE`` (LIN-02).
        """
        is_data_set = await self._is_data_set(guid)
        lineage = _Lineage(guid, direction, depth)
        depth = -1 if depth == 0 else depth
        inputs, outputs = (
            direction in {LineageDirection.INPUT, LineageDirection.BOTH},
            direction
            in {
                LineageDirection.OUTPUT,
                LineageDirection.BOTH,
            },
        )
        if is_data_set:
            if inputs:
                await self._traverse(guid, depth, set(), lineage, is_input=True)
            if outputs:
                await self._traverse(guid, depth, set(), lineage, is_input=False)
            return lineage.info()
        for is_input, wanted in ((True, inputs), (False, outputs)):
            if not wanted:
                continue
            for edge in await self._out_edges(guid, PROCESS_INPUTS_EDGE if is_input else PROCESS_OUTPUTS_EDGE):
                await self._add_edge(edge, lineage)
                await self._traverse(edge.end2_guid, depth - 1, set(), lineage, is_input=is_input)
        return lineage.info()

    async def get_atlas_lineage_info_on_demand(
        self, guid: str, constraints: dict[str, LineageOnDemandConstraints] | None
    ) -> AtlasLineageInfo:
        """``getAtlasLineageInfo`` on demand: each entity's relations limited by its constraints (LIN-06, LIN-07).

        Raises:
            AtlasError: ``LINEAGE_ON_DEMAND_NOT_ENABLED``, ``INSTANCE_GUID_NOT_FOUND`` or
                ``INVALID_LINEAGE_ENTITY_TYPE``.
        """
        if not self._on_demand_enabled:
            raise AtlasError(AtlasErrorCode.LINEAGE_ON_DEMAND_NOT_ENABLED, LINEAGE_ON_DEMAND_ENABLED)
        constraints = constraints or {guid: self._default_constraints()}
        is_data_set = await self._is_data_set(guid)
        base = self._constraints(guid, constraints)
        direction = base.direction or LineageDirection.BOTH
        lineage = _Lineage(guid, direction, base.depth)
        depth = -1 if base.depth == 0 else base.depth
        inputs = direction in {LineageDirection.INPUT, LineageDirection.BOTH}
        outputs = direction in {LineageDirection.OUTPUT, LineageDirection.BOTH}
        if is_data_set:
            lineage.on_demand.setdefault(guid, _OnDemand(base))
            if inputs:
                await self._traverse_on_demand(guid, depth, set(), constraints, lineage, is_input=True)
            if outputs:
                await self._traverse_on_demand(guid, depth, set(), constraints, lineage, is_input=False)
        else:
            for is_input, wanted in ((True, inputs), (False, outputs)):
                if wanted:
                    label = PROCESS_INPUTS_EDGE if is_input else PROCESS_OUTPUTS_EDGE
                    edges = await self._out_edges(guid, label)
                    await self._traverse_process_on_demand(edges, depth, constraints, lineage, is_input=is_input)
        info = lineage.info()
        info.lineage_on_demand_payload = constraints
        info.relations_on_demand = {
            found_guid: found
            for found_guid, found in (info.relations_on_demand or {}).items()
            if found.has_more_inputs or found.has_more_outputs
        }
        return info

    async def _is_data_set(self, guid: str) -> bool:
        """``validateEntityTypeAndCheckIfDataSet``: a data set, a process, or neither (LIN-02)."""
        header = await self._retriever.header(guid, classifications=False)
        entity_type = self._store.registry.entity_type(header.type_name)
        if entity_type is None:  # pragma: no cover - a stored entity's type is registered
            raise AtlasError(AtlasErrorCode.TYPE_NAME_NOT_FOUND, header.type_name)
        if DATA_SET_SUPER_TYPE in entity_type.type_and_all_super_types:
            return True
        if PROCESS_SUPER_TYPE not in entity_type.type_and_all_super_types:
            raise AtlasError(AtlasErrorCode.INVALID_LINEAGE_ENTITY_TYPE, guid, header.type_name)
        return False

    async def _traverse(
        self, data_set: str, depth: int, visited: set[str], lineage: _Lineage, *, is_input: bool
    ) -> None:
        """``traverseEdges``: from a data set through the processes of its edges to their other data sets."""
        if depth == 0:
            return
        visited.add(data_set)
        for incoming in await self._in_edges(data_set, PROCESS_OUTPUTS_EDGE if is_input else PROCESS_INPUTS_EDGE):
            process = incoming.end1_guid
            for outgoing in await self._out_edges(process, PROCESS_INPUTS_EDGE if is_input else PROCESS_OUTPUTS_EDGE):
                await self._add_edge(incoming, lineage)
                await self._add_edge(outgoing, lineage)
                if outgoing.end2_guid not in visited:
                    await self._traverse(outgoing.end2_guid, depth - 1, visited, lineage, is_input=is_input)

    async def _traverse_process_on_demand(
        self,
        edges: list[StoredRelationship],
        depth: int,
        constraints: dict[str, LineageOnDemandConstraints],
        lineage: _Lineage,
        *,
        is_input: bool,
    ) -> None:
        """``traverseEdgesOnDemand`` from a process: its edges, as far as the limits allow, to their data sets."""
        for edge in edges:
            if self._limit_reached(edge, constraints, lineage, is_input=edge.label == PROCESS_INPUTS_EDGE):
                break
            await self._add_edge(edge, lineage)
            data_set = edge.end2_guid
            lineage.on_demand.setdefault(data_set, _OnDemand(self._constraints(data_set, constraints)))
            await self._traverse_on_demand(data_set, depth - 1, set(), constraints, lineage, is_input=is_input)

    async def _traverse_on_demand(  # noqa: PLR0913 - Atlas's parameters
        self,
        data_set: str,
        depth: int,
        visited: set[str],
        constraints: dict[str, LineageOnDemandConstraints],
        lineage: _Lineage,
        *,
        is_input: bool,
    ) -> None:
        """``traverseEdgesOnDemand`` from a data set: ``traverseEdges`` within each entity's limits (LIN-07)."""
        if depth == 0:
            return
        visited.add(data_set)
        for incoming in await self._in_edges(data_set, PROCESS_OUTPUTS_EDGE if is_input else PROCESS_INPUTS_EDGE):
            if self._limit_reached(incoming, constraints, lineage, is_input=not is_input):
                break
            await self._add_edge(incoming, lineage)
            process = incoming.end1_guid
            for outgoing in await self._out_edges(process, PROCESS_INPUTS_EDGE if is_input else PROCESS_OUTPUTS_EDGE):
                if self._limit_reached(outgoing, constraints, lineage, is_input=is_input):
                    break
                await self._add_edge(outgoing, lineage)
                if outgoing.end2_guid not in visited:
                    await self._traverse_on_demand(
                        outgoing.end2_guid, depth - 1, visited, constraints, lineage, is_input=is_input
                    )

    def _limit_reached(
        self,
        edge: StoredRelationship,
        constraints: dict[str, LineageOnDemandConstraints],
        lineage: _Lineage,
        *,
        is_input: bool,
    ) -> bool:
        """``incrementAndCheckIfRelationsLimitReached``: count the edge for its two entities, or mark them as
        having more (LIN-07).
        """  # noqa: D205 - one sentence
        if self._visited_label(edge) in lineage.visited:
            return False
        in_guid = edge.end1_guid if is_input else edge.end2_guid
        out_guid = edge.end2_guid if is_input else edge.end1_guid
        in_info = lineage.on_demand.get(in_guid) or _OnDemand(self._constraints(in_guid, constraints))
        out_info = lineage.on_demand.get(out_guid) or _OnDemand(self._constraints(out_guid, constraints))
        reached = False
        if in_info.input_reached:
            in_info.has_more_inputs = reached = True
        else:
            in_info.increment_input()
        if out_info.output_reached:
            out_info.has_more_outputs = reached = True
        else:
            out_info.increment_output()
        if not reached:
            lineage.on_demand[in_guid] = in_info
            lineage.on_demand[out_guid] = out_info
        return reached

    async def _add_edge(self, edge: StoredRelationship, lineage: _Lineage) -> None:
        """``addEdgeToResult`` and ``processEdge``: its entities and relation, once, while under the cap (LIN-04)."""
        label = self._visited_label(edge)
        if label in lineage.visited or (lineage.relations and len(lineage.relations) > self._max_node_count):
            return
        for guid in (edge.end2_guid, edge.end1_guid):
            if guid not in lineage.entities:
                lineage.entities[guid] = await self._retriever.header(guid, classifications=False)
        if edge.label == PROCESS_INPUTS_EDGE:
            relation = LineageRelation(
                from_entity_id=edge.end2_guid, to_entity_id=edge.end1_guid, relationship_id=edge.guid
            )
        else:
            relation = LineageRelation(
                from_entity_id=edge.end1_guid, to_entity_id=edge.end2_guid, relationship_id=edge.guid
            )
        if relation not in lineage.relations:
            lineage.relations.append(relation)
        lineage.visited.add(label)

    def _visited_label(self, edge: StoredRelationship) -> str:
        """``getVisitedEdgeLabel``: the two GUIDs with lineage on demand enabled, else the relationship's."""
        if not self._on_demand_enabled:
            return edge.guid
        if edge.label == PROCESS_INPUTS_EDGE:
            return f"{edge.end2_guid}{SEPARATOR}{edge.end1_guid}"
        return f"{edge.end1_guid}{SEPARATOR}{edge.end2_guid}"

    def _default_constraints(self) -> LineageOnDemandConstraints:
        """``getDefaultLineageConstraints``: both ways, the default node count each way, depth 3."""
        return LineageOnDemandConstraints(
            direction=LineageDirection.BOTH,
            input_relations_limit=self._default_node_count,
            output_relations_limit=self._default_node_count,
            depth=LINEAGE_ON_DEMAND_DEFAULT_DEPTH,
        )

    def _constraints(self, guid: str, constraints: dict[str, LineageOnDemandConstraints]) -> LineageOnDemandConstraints:
        """``getAndValidateLineageConstraintsByGuid``: the entity's constraints, defaults filled in (LIN-06)."""
        found = constraints.get(guid)
        if found is None:
            return self._default_constraints()
        if found.direction is None:
            found.direction = LineageDirection.BOTH
        if found.input_relations_limit == 0:
            found.input_relations_limit = self._default_node_count
        if found.output_relations_limit == 0:
            found.output_relations_limit = self._default_node_count
        if found.depth == 0:
            found.depth = LINEAGE_ON_DEMAND_DEFAULT_DEPTH
        return found

    async def _in_edges(self, guid: str, label: str) -> list[StoredRelationship]:
        return edges_for_label(guid, await self._relationships(guid), label, EdgeDirection.IN)

    async def _out_edges(self, guid: str, label: str) -> list[StoredRelationship]:
        return edges_for_label(guid, await self._relationships(guid), label, EdgeDirection.OUT)

    async def _relationships(self, guid: str) -> list[StoredRelationship]:
        """The relationships the entity lists, in its order, read once per lineage (DD-061)."""
        if guid not in self._edges:
            versioned = await self._store.get(guid)
            listed = [] if versioned is None else versioned.entity.relationship_guids or []
            found = await self._store.get_relationships(listed)
            self._edges[guid] = [found[item].relationship for item in listed if item in found]
        return self._edges[guid]
