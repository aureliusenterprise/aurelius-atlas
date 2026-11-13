"""The draft entity the browser posts to ``POST /`` (VEV-01, AUX-06, DD-558).

The app reads only the draft's ``attributes``: a verdict runs over attributes, never
over relationships or classifications (VEV-01). Since 8.23 the route reads its body
through this model instead of an ``isinstance`` check inside the handler, so the
OpenAPI document and the validation are one definition (AUX-06) and a draft the app
cannot read is refused at parse time. The rest of the body is ignored, as the rule
has always said: extra keys stay unmodelled.

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
