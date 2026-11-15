"""The draft entity the browser posts to ``POST /`` (VEV-01, AUX-06, DD-558).

The app reads the draft's ``attributes``, its ``typeName`` (the type whose rules judge
it, VEV-07) and its ``relationshipAttributes`` (the picker's picks, which ride the
record the check reads, VEV-08); classifications and the rest of the body stay
ignored (VEV-01). Since 8.23 the route reads its body through this model instead of an
``isinstance`` check inside the handler, so the OpenAPI document and the validation
are one definition (AUX-06) and a draft the app cannot read is refused at parse time.
Extra keys stay unmodelled.

The model is app-side rather than a client library's: the client twin stays the
loose mapping CL-40 states — a caller may post any entity — while the server owns
what IT can read.
"""

from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class DraftEntity(BaseModel):
    """The ``POST /`` body: an entity object whose ``attributes`` is a JSON object."""

    model_config = ConfigDict(extra="ignore")

    attributes: dict[str, Any] = Field(
        description="The draft entity's attributes: what the governance rules run over (VEV-01).",
    )

    type_name: str | None = Field(
        default=None,
        alias="typeName",
        description="The draft's entity type: the rules of this type judge the draft (VEV-07). "
        "A draft without one is judged by nothing.",
    )

    relationship_attributes: dict[str, Any] | None = Field(
        default=None,
        alias="relationshipAttributes",
        description="The draft's relationship picks, by attribute name: they ride the record the "
        "check reads, as a stored entity's ends do (VEV-08, ASG-04's reading).",
    )
