"""The Aurelius Atlas validate-entity API as a contract and a client (increment 8.4, DD-203).

The wire contract of the 8.3 app — ``POST /`` with an entity in, the fixed
governance-quality document out (DV-67's mock) — as pydantic models, and an async
client for it. The entity body stays a plain mapping: the mock never reads it
(VE-01, DD-201), so a request model would invent a contract the endpoint does not
have; the *response* is the browser's card contract, and that is modelled (CL-40).
"""

from aurelius_atlas_validate_entity_client.client import (
    TokenSource,
    ValidateEntityClient,
    ValidateEntityClientError,
)
from aurelius_atlas_validate_entity_client.models import (
    GovQualityItem,
    GovQualityMeta,
    GovQualityValue,
    ValidationCard,
    ValidationResponse,
)

__all__ = [
    "GovQualityItem",
    "GovQualityMeta",
    "GovQualityValue",
    "TokenSource",
    "ValidateEntityClient",
    "ValidateEntityClientError",
    "ValidationCard",
    "ValidationResponse",
]
