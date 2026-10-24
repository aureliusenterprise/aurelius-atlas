"""The ``/extract`` request contract, imported from its client library (CL-07, DD-203).

The rule models moved to ``aurelius-atlas-data2model-client`` by increment 8.4 —
the library owns the contract, the app imports it, and this module keeps the app's
import path (and its DTM docstrings' citations) alive: the engine, the tests and
the 8.1 spec all name ``aurelius_atlas_data2model.rules``.
"""

from aurelius_atlas_data2model_client.models import (
    UNKNOWN_CONCEPT_TYPE_ERROR,
    UNKNOWN_ELEMENT_RULE_ERROR,
    UNKNOWN_RELATIONSHIP_TYPE_ERROR,
    UNKNOWN_VIEW_EDGE_RULE_ERROR,
    UNKNOWN_VIEW_NODE_RULE_ERROR,
    ElementRule,
    ExtractionRequest,
    ExtractionResponse,
    LegacyStr,
    MappingEntry,
    MetadataEntry,
    RelationRule,
    RulesDef,
    ViewEdgeRule,
    ViewNodeRule,
    ViewRule,
)

__all__ = [
    "UNKNOWN_CONCEPT_TYPE_ERROR",
    "UNKNOWN_ELEMENT_RULE_ERROR",
    "UNKNOWN_RELATIONSHIP_TYPE_ERROR",
    "UNKNOWN_VIEW_EDGE_RULE_ERROR",
    "UNKNOWN_VIEW_NODE_RULE_ERROR",
    "ElementRule",
    "ExtractionRequest",
    "ExtractionResponse",
    "LegacyStr",
    "MappingEntry",
    "MetadataEntry",
    "RelationRule",
    "RulesDef",
    "ViewEdgeRule",
    "ViewNodeRule",
    "ViewRule",
]
