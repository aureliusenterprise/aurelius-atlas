"""The Aurelius Atlas lineage-model API as a contract and a client (increment 8.4, DD-114).

The wire contract of the 8.2 app — ``GET /?guid=&depth=&direction=`` in, the
data2model ``{model, metadata}`` passthrough out — as pydantic models, and an async
client for it. The flattening itself (rows, rules) stays in the app; this library
states what a caller sends and receives (CL-30).
"""

from aurelius_atlas_lineage_model_client.client import LineageModelClient, LineageModelClientError, TokenSource
from aurelius_atlas_lineage_model_client.models import (
    DEFAULT_DEPTH,
    LineageModelParams,
    LineageModelResponse,
)

__all__ = [
    "DEFAULT_DEPTH",
    "LineageModelClient",
    "LineageModelClientError",
    "LineageModelParams",
    "LineageModelResponse",
    "TokenSource",
]
