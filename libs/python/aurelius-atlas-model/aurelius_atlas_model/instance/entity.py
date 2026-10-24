"""``AtlasEntity``: an instance of an entity type, with its system fields (ENT-04 to ENT-08)."""

import itertools
import time
from typing import Any

from pydantic import AliasChoices, Field

from aurelius_atlas_model.base import OptionalNameSet, Timestamp
from aurelius_atlas_model.instance.classification import AtlasClassification
from aurelius_atlas_model.instance.entity_status import EntityStatus
from aurelius_atlas_model.instance.struct import AtlasStruct
from aurelius_atlas_model.instance.term_assignment_header import AtlasTermAssignmentHeader

_next_ids = itertools.count(time.monotonic_ns())


def next_internal_id() -> str:
    """A new temporary GUID: ``-`` and a number counted up from the clock (``AtlasEntity.nextInternalId``, ENT-04).

    A client names entities it has not created yet by such GUIDs; the store replaces them on creation.
    """
    return f"-{next(_next_ids)}"


class AtlasEntity(AtlasStruct):
    """An entity: a struct with a GUID, a status, audit fields, relationships, classifications and labels.

    Read with the defaults of Java's no-argument constructor, whose ``init()`` assigns a temporary GUID and
    clears ``status`` (ENT-04). ``isProxy`` is read under that name and written as ``proxy`` (ENT-05).
    """

    guid: str | None = Field(default_factory=next_internal_id)
    home_id: str | None = None
    is_proxy: bool | None = Field(
        default=False, validation_alias=AliasChoices("isProxy", "is_proxy"), serialization_alias="proxy"
    )
    is_incomplete: bool | None = False
    provenance_type: int | None = 0
    status: EntityStatus | None = None
    created_by: str | None = None
    updated_by: str | None = None
    create_time: Timestamp | None = None
    update_time: Timestamp | None = None
    version: int | None = 0
    relationship_attributes: dict[str, Any] | None = None
    classifications: list[AtlasClassification] | None = None
    meanings: list[AtlasTermAssignmentHeader] | None = None
    custom_attributes: dict[str, str] | None = None
    business_attributes: dict[str, dict[str, Any]] | None = None
    labels: OptionalNameSet = None
    pending_tasks: OptionalNameSet = None

    def has_relationship_attribute(self, name: str) -> bool:
        """Whether relationship attribute ``name`` is present, even with a null value."""
        return self.relationship_attributes is not None and name in self.relationship_attributes

    def get_relationship_attribute(self, name: str) -> Any:  # noqa: ANN401 - relationship values are untyped JSON
        """The value of relationship attribute ``name``, or None."""
        return None if self.relationship_attributes is None else self.relationship_attributes.get(name)

    def set_relationship_attribute(self, name: str, value: Any) -> None:  # noqa: ANN401 - untyped JSON
        """Set relationship attribute ``name``, creating the map when there is none."""
        if self.relationship_attributes is None:
            self.relationship_attributes = {}
        self.relationship_attributes[name] = value

    def get_business_attribute(self, business_metadata: str, name: str) -> Any:  # noqa: ANN401 - untyped JSON
        """The value of attribute ``name`` of business metadata ``business_metadata``, or None."""
        attributes = (self.business_attributes or {}).get(business_metadata)
        return None if attributes is None else attributes.get(name)

    def set_business_attribute(self, business_metadata: str, name: str, value: Any) -> None:  # noqa: ANN401
        """Set attribute ``name`` of business metadata ``business_metadata``, creating the maps it needs."""
        if self.business_attributes is None:
            self.business_attributes = {}
        self.business_attributes.setdefault(business_metadata, {})[name] = value

    def add_classifications(self, classifications: list[AtlasClassification]) -> None:
        """Append classifications, creating the list."""
        self.classifications = [*(self.classifications or []), *classifications]

    def add_meaning(self, meaning: AtlasTermAssignmentHeader) -> None:
        """Append a meaning, creating the list."""
        self.meanings = [*(self.meanings or []), meaning]
