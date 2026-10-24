"""``AttributeToken``: ``{attribute}`` in a dynamic attribute's template (EWR-03)."""

from dataclasses import dataclass

from aurelius_atlas_model.errors import java_string
from aurelius_atlas_model.instance import AtlasEntity


@dataclass(frozen=True)
class AttributeToken:
    """An attribute of the entity itself; ``value`` is its name."""

    value: str

    def eval(self, entity: AtlasEntity) -> str | None:
        """The attribute's value as Java's text, or None when it has none."""
        found = entity.get_attribute(self.value)
        return None if found is None else java_string(found)
