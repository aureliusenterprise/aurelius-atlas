"""``TypeDefChangeListener`` and ``ChangedTypeDefs``: what a typedef change created, updated and deleted (ADA-03)."""

from dataclasses import dataclass, field
from typing import Protocol

from aurelius_atlas_model.typedef import AtlasBaseTypeDef


@dataclass
class ChangedTypeDefs:
    """``ChangedTypeDefs``: the definitions a change created, updated and deleted."""

    created: list[AtlasBaseTypeDef] = field(default_factory=list)
    updated: list[AtlasBaseTypeDef] = field(default_factory=list)
    deleted: list[AtlasBaseTypeDef] = field(default_factory=list)

    def is_empty(self) -> bool:
        """Whether the change created, updated and deleted nothing."""
        return not (self.created or self.updated or self.deleted)


class TypeDefChangeListener(Protocol):
    """``TypeDefChangeListener``: told of each change of the type definitions once it is written."""

    async def on_change(self, changed: ChangedTypeDefs) -> None:
        """``onChange``: the change written."""
        ...
