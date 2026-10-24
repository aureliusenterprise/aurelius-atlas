"""``AtlasBuiltInTypes.AtlasIntType`` (VAL-04)."""

from aurelius_atlas_model.typedef import ATLAS_TYPE_INT

from aurelius_atlas_typesystem.builtin.integral_type import IntegralType


class IntType(IntegralType):
    """``int``: a 32-bit Java integer."""

    def __init__(self) -> None:
        super().__init__(ATLAS_TYPE_INT, 32)
