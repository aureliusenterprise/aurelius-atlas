"""``UniqueKey``: one unique attribute value of one entity type, the id of its reservation (ENS-05, DD-045)."""

import hashlib
from dataclasses import dataclass
from typing import Any

from aurelius_atlas_model import codec


@dataclass(frozen=True)
class UniqueKey:
    """A value of a unique attribute of an entity type: what Atlas's ``PER_TYPE_UNIQUE`` index keeps once.

    ``attribute`` is the attribute's qualified name (``Referenceable.qualifiedName``), ``value`` the normalised value.
    """

    type_name: str
    attribute: str
    value: Any

    @property
    def id(self) -> str:
        """The reservation's document id: a SHA-256 of type, attribute and value as the codec writes them."""
        return hashlib.sha256(codec.dumps([self.type_name, self.attribute, self.value])).hexdigest()
