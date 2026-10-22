"""``ConstantToken``: text of a dynamic attribute's template outside braces (EWR-03)."""

from dataclasses import dataclass

from aurelius_atlas_model.instance import AtlasEntity


@dataclass(frozen=True)
class ConstantToken:
    """Text taken as it is."""

    value: str

    def eval(self, entity: AtlasEntity) -> str:  # noqa: ARG002 - a constant does not depend on the entity
        """The text itself."""
        return self.value
