"""``DeleteType``: how a delete removes entities, as a request may choose it (EDL-04)."""

from enum import StrEnum


class DeleteType(StrEnum):
    """``DEFAULT`` is the server's configured type; ``SOFT`` marks entities deleted; ``HARD`` removes them."""

    DEFAULT = "DEFAULT"
    SOFT = "SOFT"
    HARD = "HARD"

    @classmethod
    def of(cls, text: str | None) -> DeleteType:
        """``DeleteType.from``: ``soft`` or ``hard`` in any case; anything else, or nothing, is ``DEFAULT``."""
        match (text or "").lower():
            case "soft":
                return cls.SOFT
            case "hard":
                return cls.HARD
            case _:
                return cls.DEFAULT
