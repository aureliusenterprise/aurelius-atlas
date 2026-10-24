"""``AtlasTermAssignmentHeader``: a glossary term assigned to an entity, as the entity lists it (ENT-15)."""

from typing import Any

from pydantic import SerializerFunctionWrapHandler, model_serializer

from aurelius_atlas_model.base import AtlasModel, JavaInt
from aurelius_atlas_model.instance.term_assignment_status import AtlasTermAssignmentStatus


class AtlasTermAssignmentHeader(AtlasModel):
    """The term, the assignment's relationship and how it was made (``glossary.relations``).

    Atlas writes it with ``@AtlasJSON``, ``NON_EMPTY``: null fields and empty strings are left out, but the
    ``int`` ``confidence`` is always written.
    """

    term_guid: str | None = None
    relation_guid: str | None = None
    description: str | None = None
    display_text: str | None = None
    expression: str | None = None
    created_by: str | None = None
    steward: str | None = None
    source: str | None = None
    confidence: JavaInt = 0
    status: AtlasTermAssignmentStatus | None = None
    qualified_name: str | None = None

    @model_serializer(mode="wrap")
    def _non_empty(self, handler: SerializerFunctionWrapHandler) -> dict[str, Any]:
        written: dict[str, Any] = handler(self)
        return {name: value for name, value in written.items() if value is not None and value != ""}
