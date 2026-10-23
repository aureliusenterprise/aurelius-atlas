"""The request and response shapes of the lineage-model API (CL-30, LM-01/LM-04; DD-114).

The query of ``GET /`` and the answer it forwards from data2model, stated once so
the app validates its own query with the same model a caller builds (CL-07). The
lineage directions are imported from ``aurelius-atlas-server-client`` — the lineage
vocabulary belongs to the lineage API (CL-12), not to each consumer; reusing it is
CL-10's rule applied to types.
"""

from typing import Annotated, Any

from aurelius_atlas_server_client.lineage import Direction
from pydantic import BaseModel, ConfigDict, Field

__all__ = ["DEFAULT_DEPTH", "MIN_DEPTH", "Direction", "LineageModelParams", "LineageModelResponse"]

DEFAULT_DEPTH = 3
"""The lineage depth the endpoint defaults to when the query omits it (LM-01)."""

MIN_DEPTH = 1
"""The smallest depth the endpoint accepts (LM-01's ``ge=1``)."""


class LineageModelParams(BaseModel):
    """The ``GET /`` query: guid, depth, direction (LM-01; CL-30).

    The app validates its own query parameters against these constraints, and a
    caller builds them — the 400 of DV-20/DV-21 is a body this model rejects.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    guid: str = Field(min_length=1)
    """The entity whose lineage flattens; required (DV-21)."""

    depth: Annotated[int, Field(ge=MIN_DEPTH)] = DEFAULT_DEPTH
    """How many hops to walk; at least one, three by default (LM-01)."""

    direction: Direction = "BOTH"
    """Which way to walk the lineage (LM-01, DV-20)."""


class LineageModelResponse(BaseModel):
    """The answer of ``GET /``: the data2model body, forwarded verbatim (LM-01/LM-04; CL-30).

    ``model`` is the ar3 model as a JSON *string* (DV-15's contract, kept by the
    passthrough); ``metadata`` is open by the data2model contract, so a plain map.
    """

    model_config = ConfigDict(extra="ignore", frozen=True)

    model: str
    """The ar3 model, JSON-encoded — the browser draws it."""

    metadata: list[dict[str, Any]] = Field(default_factory=list)
    """One entry per element/edge row and per view (DTM-03)."""
