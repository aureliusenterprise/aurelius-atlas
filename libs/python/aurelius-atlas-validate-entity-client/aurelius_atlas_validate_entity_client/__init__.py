"""The Aurelius Atlas validate-entity API as a contract and a client (increment 8.4, DD-203; CL-40 as amended by 12.7).

The wire contract of the 8.3 app — ``POST /`` with an entity draft in, the governance
verdicts out (VEV-01/02, since 12.7) — as pydantic models, and an async client for it.
The entity body stays a plain mapping: a verdict reads only the draft's ``attributes``
(VEV-01), so a request model would invent a contract the endpoint does not have; the
*response* is the browser's verdict contract, and that is modelled (CL-40). The four
canned cards of the 8.3 mock retired with DV-67 (ADR 061).
"""

from aurelius_atlas_validate_entity_client.client import (
    TokenSource,
    ValidateEntityClient,
    ValidateEntityClientError,
)
from aurelius_atlas_validate_entity_client.models import (
    GovernanceVerdict,
    UnreadRule,
    ValidationResponse,
)

__all__ = [
    "GovernanceVerdict",
    "TokenSource",
    "UnreadRule",
    "ValidateEntityClient",
    "ValidateEntityClientError",
    "ValidationResponse",
]
