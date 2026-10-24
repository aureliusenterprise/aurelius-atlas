"""``AtlasBuiltInTypes.AtlasLongType`` (VAL-04)."""

from aurelius_atlas_model.typedef import ATLAS_TYPE_LONG

from aurelius_atlas_typesystem.builtin.integral_type import IntegralType


class LongType(IntegralType):
    """``long``: a 64-bit Java integer."""

    def __init__(self) -> None:
        super().__init__(ATLAS_TYPE_LONG, 64)
