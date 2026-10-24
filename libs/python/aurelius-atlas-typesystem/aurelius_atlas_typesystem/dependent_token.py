"""``DependentToken``: ``{a.b}`` in a dynamic attribute's template, an attribute of a related entity (EWR-03)."""

from dataclasses import dataclass, field

from aurelius_atlas_model.instance import AtlasEntity

DEPENDENT_TOKEN_TEXT = "TEMP"  # noqa: S105 - not a password
"""What Atlas 2.4.0 evaluates every dependent token to: the lookup is not implemented."""


@dataclass(frozen=True)
class DependentToken:
    """A path through references to an attribute; ``value`` is the path as written."""

    value: str
    object_path: list[str] = field(init=False)
    attribute_name: str = field(init=False)

    def __post_init__(self) -> None:
        """Split the path into the references followed and the attribute read."""
        parts = self.value.split(".")
        while len(parts) > 1 and not parts[-1]:
            parts.pop()  # Java's split drops trailing empty parts
        object.__setattr__(self, "object_path", parts[:-1])
        object.__setattr__(self, "attribute_name", parts[-1])

    def eval(self, entity: AtlasEntity) -> str:  # noqa: ARG002 - Atlas does not follow the path
        """``TEMP``, as Atlas 2.4.0 answers."""
        return DEPENDENT_TOKEN_TEXT
