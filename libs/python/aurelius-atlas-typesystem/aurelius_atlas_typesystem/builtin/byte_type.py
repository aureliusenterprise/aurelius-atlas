"""``AtlasBuiltInTypes.AtlasByteType`` (VAL-04)."""

from aurelius_atlas_model.typedef import ATLAS_TYPE_BYTE

from aurelius_atlas_typesystem.builtin.integral_type import IntegralType


class ByteType(IntegralType):
    """``byte``: a 8-bit Java integer."""

    def __init__(self) -> None:
        super().__init__(ATLAS_TYPE_BYTE, 8)
