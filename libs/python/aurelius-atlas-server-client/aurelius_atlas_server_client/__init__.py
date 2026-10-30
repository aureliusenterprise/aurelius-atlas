"""The Aurelius Atlas server API as a contract and a client (increment 8.4, DD-203).

The wire contract of the Atlas metadata API the server routes answer — the admin
endpoints, the typedef endpoints and the ``v2/lineage/{guid}`` body — as pydantic
models, and an async client for them. The server itself keeps the models it already
had (``aurelius-atlas-model``, reused here, never forked); this library adds the
response shapes the routes never stated (CL-10) and the client every consumer calls
(CL-11), the Python twin of ``libs/angular/aurelius-atlas-data-access``.
"""

from aurelius_atlas_server_client.client import AtlasClient, AtlasClientError, SearchApi, TokenSource
from aurelius_atlas_server_client.lineage import (
    Direction,
    EntityHeaderLite,
    LineageInfo,
    LineageRelation,
)
from aurelius_atlas_server_client.models import (
    AtlasErrorInfo,
    AtlasSessionInfo,
    AtlasStatus,
    AtlasVersion,
)

__all__ = [
    "AtlasClient",
    "AtlasClientError",
    "AtlasErrorInfo",
    "AtlasSessionInfo",
    "AtlasStatus",
    "AtlasVersion",
    "Direction",
    "EntityHeaderLite",
    "LineageInfo",
    "LineageRelation",
    "SearchApi",
    "TokenSource",
]
