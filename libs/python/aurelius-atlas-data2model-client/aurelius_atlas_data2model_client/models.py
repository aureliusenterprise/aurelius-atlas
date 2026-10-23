"""The ``/extract`` request contract as pydantic models (DTM-01, DTM-11, DTM-12; DD-109).

The legacy chain built these from ``m4i-analytics`` dict adapters (``ConceptDefinition``
and subclasses, ``**kwargs``-tolerant); the port states the same fields as pydantic
models, so FastAPI validates the public request at the boundary: an unknown concept
or relationship type, a missing required key, or a dangling rule reference is a 400
(DTM-11), not a 500 as in the legacy.

The legacy adapters normalise ``None`` prefixes/keys to ``''`` — the lineage caller
sends nulls for them — so the string fields accept ``None`` and normalise to ``''``;
extra keys (``alias``, ``description``, ``include``, …) are ignored, as the ``**kwargs``
did. The tabular ``data`` stays a plain list of row maps: the columns are the rules'
keys, so the rows are a mapping, not a model (DD-109).
"""

from __future__ import annotations

from typing import Annotated, Any

from pydantic import BaseModel, BeforeValidator, ConfigDict, Field, field_validator, model_validator

from aurelius_atlas_data2model_client.types import ELEMENT_TYPE_LAYERS, RELATIONSHIP_SHORTHANDS

LegacyStr = Annotated[str, BeforeValidator(lambda v: "" if v is None else v)]
"""A legacy string field: null arrives as ``''``, as the legacy adapters normalise it."""

UNKNOWN_CONCEPT_TYPE_ERROR = "unknown concept type: {value!r}"
"""A concept_type outside the ported type table (DTM-11)."""

UNKNOWN_RELATIONSHIP_TYPE_ERROR = "unknown relationship type: {value!r}"
"""A relationship_type outside the ported shorthand table (DTM-11)."""

UNKNOWN_ELEMENT_RULE_ERROR = "relation rule {rule!r} names an unknown element rule as {side}: {ref!r}"
"""A relation rule's dangling source/target reference (DTM-11)."""

UNKNOWN_VIEW_NODE_RULE_ERROR = "view rule {rule!r} names an unknown element rule: {ref!r}"
"""A view rule's dangling view_nodes reference (DTM-11)."""

UNKNOWN_VIEW_EDGE_RULE_ERROR = "view rule {rule!r} names an unknown relation rule: {ref!r}"
"""A view rule's dangling view_edges reference (DTM-11)."""


class _Rule(BaseModel):
    """A rule: identified, ignores the caller's extra keys, immutable once parsed."""

    model_config = ConfigDict(extra="ignore", frozen=True)

    id: LegacyStr = ""
    """The rule's id — the caller's reference into ``rules`` (relation/view rules name it)."""


class MappingEntry(_Rule):
    """One ``{key, value}``: attach column ``value`` as metadata attribute ``key`` (DTM-03)."""

    key: str
    """The metadata attribute's name."""

    value: str
    """The source column's name."""


class ElementRule(_Rule):
    """An element rule (legacy ``ElementDefinition``): one node per row of ``id_key`` (DTM-02)."""

    id_key: str
    """The column holding each node's id; rows with a null id are dropped, first row per id wins."""

    concept_type: str
    """The node's Archimate element type tag (DTM-11 validates it).

    The lineage chain uses ``lineage_dataset``/``lineage_process``.
    """

    id_prefix: LegacyStr = ""
    """Prefix of the node id (DTM-02)."""

    concept_name_prefix: LegacyStr = ""
    """Prefix of the node name."""

    concept_name_key: LegacyStr = ""
    """The column holding the node name; empty means the name is ``''`` (DTM-02)."""

    concept_label_prefix: LegacyStr = ""
    """Prefix of the node label (kept for the legacy contract; the ar3 writer ignores labels)."""

    concept_label_key: LegacyStr = ""
    """The column holding the node label; the ar3 writer ignores labels."""

    mapping: list[MappingEntry] = Field(default_factory=list)
    """Metadata attributes to attach per row (DTM-03)."""

    @field_validator("concept_type")
    @classmethod
    def _known_concept_type(cls, value: str) -> str:
        """Accept only the Archimate element types the port carries (DTM-11)."""
        if value not in ELEMENT_TYPE_LAYERS:
            raise ValueError(UNKNOWN_CONCEPT_TYPE_ERROR.format(value=value))
        return value


class RelationRule(_Rule):
    """A relation rule (legacy ``RelationshipDefinition``): one edge per row (DTM-04).

    ``fmt_relation`` resolved ``source``/``target`` into the referenced element rule's
    ``id_key``/``id_prefix``; the port keeps the rule references and resolves them the
    same way, in :mod:`aurelius_atlas_data2model.extract`.
    """

    id_key: str
    """The column holding each edge's id."""

    relationship_type: str
    """The Archimate relationship shorthand (``lr`` for the lineage chain; DTM-11 validates it)."""

    source: LegacyStr = ""
    """The id of the element rule holding the source ids."""

    target: LegacyStr = ""
    """The id of the element rule holding the target ids."""

    id_prefix: LegacyStr = ""
    """Prefix of the edge id."""

    relationship_name_key: LegacyStr = ""
    """The column holding the edge name; empty means the name is ``''``."""

    relationship_label_key: LegacyStr = ""
    """The column holding the edge label; the ar3 writer ignores labels."""

    mapping: list[MappingEntry] = Field(default_factory=list)
    """Metadata attributes to attach per row (DTM-03)."""

    @field_validator("relationship_type")
    @classmethod
    def _known_relationship_type(cls, value: str) -> str:
        """Accept only the Archimate relationship shorthands the port carries (DTM-11)."""
        if value not in RELATIONSHIP_SHORTHANDS:
            raise ValueError(UNKNOWN_RELATIONSHIP_TYPE_ERROR.format(value=value))
        return value


class ViewNodeRule(_Rule):
    """A view node entry: includes the referenced element rule's nodes (DTM-07)."""

    rule: str
    """The id of the element rule whose rows fill the view (resolved at parse time, DTM-11)."""


class ViewEdgeRule(_Rule):
    """A view edge entry: includes the referenced relation rule's edges (DTM-07)."""

    rule: str
    """The id of the relation rule whose rows fill the view (resolved at parse time, DTM-11)."""


class ViewRule(_Rule):
    """A view rule (legacy ``ViewDefinition``): one diagram per layout match (DTM-06)."""

    view_layout: LegacyStr = ""
    """The layout name; a layout the registry does not know drops the view entirely (DTM-06)."""

    id_type: LegacyStr = "dynamic"
    """``static``: one view ided by ``id_value``; ``dynamic``: one view per value of ``id_key``."""

    id_key: LegacyStr = ""
    """The grouping column for a dynamic view."""

    id_value: LegacyStr = ""
    """The view id for a static view (``lineage_view`` for the lineage chain)."""

    id_prefix: LegacyStr = ""
    """Prefix of a dynamic view id."""

    view_name_type: LegacyStr = "dynamic"
    """``static``: the name is ``view_name_value``; ``dynamic``: the name comes from ``view_name_key``."""

    view_name_key: LegacyStr = ""
    """The column holding the view name for a dynamic view."""

    view_name_value: LegacyStr = ""
    """The view name for a static view (``Lineage`` for the lineage chain)."""

    view_name_prefix: LegacyStr = ""
    """Prefix of a dynamic view name."""

    view_nodes: list[ViewNodeRule] = Field(default_factory=list)
    """The element rules whose nodes fill the view, in order (DTM-07)."""

    view_edges: list[ViewEdgeRule] = Field(default_factory=list)
    """The relation rules whose edges fill the view; empty means all model edges between the view nodes (DTM-07)."""

    view_path: list[LegacyStr] = Field(default_factory=list)
    """Extra organization folders below ``Views`` (legacy ``ViewPathMapping``s; static entries only)."""

    mapping: list[MappingEntry] = Field(default_factory=list)
    """Metadata attributes to attach per view (legacy: unused by the writer; kept for the contract)."""


class RulesDef(_Rule):
    """The ``rules`` body: elements, relations, views, in rule order (DTM-03)."""

    elements: list[ElementRule] = Field(default_factory=list)
    """The element rules."""

    relations: list[RelationRule] = Field(default_factory=list)
    """The relation rules."""

    views: list[ViewRule] = Field(default_factory=list)
    """The view rules."""

    @model_validator(mode="after")
    def _references_resolve(self) -> RulesDef:
        """Resolve the cross-rule references the legacy ``fmt_relation``/``fmt_view`` did (DTM-11).

        The legacy raised ``KeyError`` (a 500) on a dangling reference; the port names
        the offender in a 400.
        """
        element_ids = {rule.id for rule in self.elements}
        relation_ids = {rule.id for rule in self.relations}
        for relation in self.relations:
            for side, ref in (("source", relation.source), ("target", relation.target)):
                if ref not in element_ids:
                    msg = UNKNOWN_ELEMENT_RULE_ERROR.format(rule=relation.id, side=side, ref=ref)
                    raise ValueError(msg)
        for view in self.views:
            for node in view.view_nodes:
                if node.rule not in element_ids:
                    msg = UNKNOWN_VIEW_NODE_RULE_ERROR.format(rule=view.id, ref=node.rule)
                    raise ValueError(msg)
            for edge in view.view_edges:
                if edge.rule not in relation_ids:
                    msg = UNKNOWN_VIEW_EDGE_RULE_ERROR.format(rule=view.id, ref=edge.rule)
                    raise ValueError(msg)
        return self


class ExtractionRequest(_Rule):
    """The ``POST /extract`` body: ``{data: [row…], rules: {...}}`` (DTM-01).

    An absent ``data``/``rules`` is the empty extraction the legacy answers with the
    model skeleton (DTM-11); ``data`` is a list of row maps, columns keyed by name —
    a key absent from a row reads as null, as the legacy's missing DataFrame cell.
    """

    data: list[dict[str, Any]] = Field(default_factory=list)
    """The tabular rows; plain maps, not models (DD-109)."""

    rules: RulesDef = Field(default_factory=RulesDef)
    """The element/relation/view rules."""


class MetadataEntry(BaseModel):
    """One ``{id, data}`` metadata entry of the extraction answer (DTM-03; CL-20).

    ``data`` carries the rule's provenance (``created_by``, ``m4i_id_prefix``,
    ``m4i_original_id``, …) plus the row's mapped attributes, keyed by the
    ``mapping`` entries — open by contract, so a plain map.
    """

    model_config = ConfigDict(extra="ignore", frozen=True)

    id: str
    """The element/edge/view id the entry describes, with its rule's prefix."""

    data: dict[str, Any] = Field(default_factory=dict)
    """The provenance and mapped attributes; open keys by contract (DTM-03)."""


class ExtractionResponse(BaseModel):
    """The ``POST /extract`` answer: ``{metadata: […], model: "<ar3 JSON string>"}`` (DTM-01; CL-20).

    The model is a JSON *string* inside the JSON body, as the legacy answer is
    (DV-15); ``model_validate_json`` of it is the caller's ar3 document.
    """

    model_config = ConfigDict(extra="ignore", frozen=True)

    metadata: list[MetadataEntry] = Field(default_factory=list)
    """One entry per element/edge row and per view (DTM-03)."""

    model: str
    """The ar3 model, JSON-encoded — the browser draws it (DV-15)."""
