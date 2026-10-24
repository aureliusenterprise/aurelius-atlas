"""The request and response shapes of the lineage-model API (CL-30, LM-01/LM-04; DD-203).

The ids of this module's rules stay here: ``LineageModelParams`` is LM-01's query
(DV-72/DV-73 are its rejections), ``LineageModelResponse`` is the LM-04/LM-01
forward of the data2model answer (DV-68's contract). Field descriptions are the
public OpenAPI documentation, so they name no rule ids; the Java classes ported
are in the increment spec.

The query of ``GET /`` and the answer it forwards from data2model, stated once so
the app validates its own query with the same model a caller builds (CL-07). The
lineage directions are imported from ``aurelius-atlas-server-client`` — the lineage
vocabulary belongs to the lineage API (CL-12), not to each consumer; reusing it is
CL-10's rule applied to types.
"""

from typing import Any
from uuid import UUID

from aurelius_atlas_server_client.lineage import Direction
from pydantic import BaseModel, ConfigDict, Field

__all__ = ["DEFAULT_DEPTH", "MIN_DEPTH", "Direction", "LineageModelParams", "LineageModelResponse"]

DEFAULT_DEPTH = 3
"""The lineage depth the endpoint defaults to when the query omits it (LM-01)."""

MIN_DEPTH = 1
"""The smallest depth the endpoint accepts (LM-01's ``ge=1``)."""


# LM-01; CL-30. The app validates its own query parameters against these
# constraints, and a caller builds them — the 400 of DV-72/DV-73 is a body
# this model rejects.
class LineageModelParams(BaseModel):
    """The ``GET /`` query of the lineage-model API: which entity, how deep, which way."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    guid: UUID = Field(
        description="The guid of the entity whose lineage is flattened.",
    )

    depth: int = Field(
        default=DEFAULT_DEPTH,
        ge=MIN_DEPTH,
        description="How many hops of lineage to walk; at least one.",
    )

    direction: Direction = Field(
        default="BOTH",
        description="Which way to walk the lineage: upstream, downstream, or both.",
    )


# LM-01/LM-04; CL-30. The data2model body, forwarded verbatim: ``model`` is
# the ar3 model as a JSON *string* (DV-68's contract, kept by the passthrough);
# ``metadata`` is open by the data2model contract, so a plain map.
class LineageModelResponse(BaseModel):
    """The answer of ``GET /``: the flattened lineage as an ar3 model and its metadata."""

    model_config = ConfigDict(extra="ignore", frozen=True)

    model: str = Field(
        description="The ar3 model, JSON-encoded as a string; the browser draws it.",
    )

    metadata: list[dict[str, Any]] = Field(
        default_factory=list,
        description=(
            "One entry per element, edge, and view: the provenance of each row "
            "and its mapped attributes, as open key/value maps."
        ),
    )
