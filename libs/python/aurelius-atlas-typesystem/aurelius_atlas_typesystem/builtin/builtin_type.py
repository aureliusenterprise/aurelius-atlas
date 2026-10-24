"""``AtlasBuiltInTypes``: what the primitive types share (TRG-01)."""

from aurelius_atlas_model.typedef import SERVICE_TYPE_ATLAS_CORE, TypeCategory

from aurelius_atlas_typesystem.atlas_type import AtlasType


class BuiltInType(AtlasType):
    """A primitive type such as ``string`` or ``int``, of the ``atlas_core`` service type (TRG-01)."""

    def __init__(self, type_name: str) -> None:
        super().__init__(type_name, TypeCategory.PRIMITIVE, SERVICE_TYPE_ATLAS_CORE)
