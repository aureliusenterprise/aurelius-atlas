"""The Aurelius Atlas data2model API as a contract and a client (increment 8.4, DD-114).

The wire contract of ``POST /extract`` — the tabular rows, the element/relation/view
rules document, and the ``{model, metadata}`` answer — as pydantic models, and an
async client for the API. The ``aurelius-atlas-data2model`` app imports this
contract (CL-07); the 8.2 lineage chain builds its payload from the same rule
models the server validates (CL-21).
"""

from aurelius_atlas_data2model_client.client import Data2ModelClient, Data2ModelClientError, TokenSource
from aurelius_atlas_data2model_client.models import (
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
from aurelius_atlas_data2model_client.types import ELEMENT_TYPE_LAYERS, LAYOUT_NAMES, RELATIONSHIP_SHORTHANDS

__all__ = [
    "ELEMENT_TYPE_LAYERS",
    "LAYOUT_NAMES",
    "RELATIONSHIP_SHORTHANDS",
    "Data2ModelClient",
    "Data2ModelClientError",
    "ElementRule",
    "ExtractionRequest",
    "ExtractionResponse",
    "LegacyStr",
    "MappingEntry",
    "MetadataEntry",
    "RelationRule",
    "RulesDef",
    "TokenSource",
    "ViewEdgeRule",
    "ViewNodeRule",
    "ViewRule",
]
