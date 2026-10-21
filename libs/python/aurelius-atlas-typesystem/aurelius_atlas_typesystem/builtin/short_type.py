"""``AtlasBuiltInTypes.AtlasShortType`` (VAL-04)."""

from aurelius_atlas_model.typedef import ATLAS_TYPE_SHORT

from aurelius_atlas_typesystem.builtin.integral_type import IntegralType


class ShortType(IntegralType):
    """``short``: a 16-bit Java integer."""

    def __init__(self) -> None:
        super().__init__(ATLAS_TYPE_SHORT, 16)
