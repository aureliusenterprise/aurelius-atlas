"""``AtlasStructType.AtlasAttribute``: an attribute as its type resolves it (TRG-11, DD-041)."""

from typing import TYPE_CHECKING

from aurelius_atlas_model.typedef import (
    CONSTRAINT_PARAM_ATTRIBUTE,
    CONSTRAINT_TYPE_INVERSE_REF,
    CONSTRAINT_TYPE_OWNED_REF,
    AtlasAttributeDef,
    AtlasStructDef,
)

from aurelius_atlas_typesystem.atlas_type import AtlasType

if TYPE_CHECKING:
    from aurelius_atlas_typesystem.struct_type import StructType

from aurelius_atlas_model.typedef import TypeCategory

from aurelius_atlas_typesystem.array_type import ArrayType
from aurelius_atlas_typesystem.atlas_type import resolved
from aurelius_atlas_typesystem.edge_direction import EdgeDirection
from aurelius_atlas_typesystem.map_type import MapType
from aurelius_atlas_typesystem.type_names import CLASSIFICATION_ROOT_NAME, ENTITY_ROOT_NAME
from aurelius_atlas_typesystem.values import parse_json


class AtlasAttribute:
    """A resolved attribute of a struct-like type (``AtlasStructType.AtlasAttribute``)."""

    def __init__(
        self,
        defined_in: StructType,
        attribute_def: AtlasAttributeDef,
        attribute_type: AtlasType,
        relationship_name: str | None = None,
        relationship_label: str | None = None,
    ) -> None:
        self.defined_in = defined_in
        self.attribute_def = attribute_def
        self.attribute_type = attribute_type.type_for_attribute()
        self.name = attribute_def.name
        self.qualified_name = qualified_attribute_name(defined_in.struct_def, str(attribute_def.name))
        constraints = attribute_def.constraints or []
        self.is_owned_ref = any(constraint.is_constraint_type(CONSTRAINT_TYPE_OWNED_REF) for constraint in constraints)
        self.inverse_ref_attribute_name = next(
            (
                str(param)
                for constraint in constraints
                if constraint.is_constraint_type(CONSTRAINT_TYPE_INVERSE_REF)
                and (param := constraint.get_param(CONSTRAINT_PARAM_ATTRIBUTE)) is not None
            ),
            None,
        )
        self.inverse_ref_attribute: AtlasAttribute | None = None
        self.is_object_ref = _holds_object_ids(self.attribute_type)
        self.relationship_name = relationship_name
        self.relationship_edge_label = relationship_label or f"__{self.qualified_name}"
        self.relationship_edge_direction = EdgeDirection.OUT
        self.is_legacy_attribute = False

    def option_set(self, name: str) -> list[str] | None:
        """Option ``name`` read as a JSON array of names, or None when blank or not an array (``getOptionSet``)."""
        value = _option_json(self.attribute_def.get_option(name))
        return list(dict.fromkeys(str(item) for item in value)) if isinstance(value, list) else None

    def option_int(self, name: str) -> int | None:
        """Option ``name`` as an integer, or None when blank (``getOptionInt``)."""
        value = self.attribute_def.get_option(name)
        return None if value is None or not value.strip() else int(value)

    def option_string(self, name: str) -> str | None:
        """Option ``name``, or None when blank (``getOptionString``)."""
        value = self.attribute_def.get_option(name)
        return None if value is None or not value.strip() else value


def qualified_attribute_name(struct_def: AtlasStructDef, attribute_name: str) -> str:
    """``Type.attribute``, or the name itself when it contains a dot or belongs to a root type (TRG-11, THY-05)."""
    if struct_def.name in {ENTITY_ROOT_NAME, CLASSIFICATION_ROOT_NAME} or "." in attribute_name:
        return attribute_name
    return f"{struct_def.name}.{attribute_name}"


def _option_json(value: str | None) -> object:
    """``AtlasType.fromJson`` of an option: None for a missing, blank or malformed value."""
    return None if value is None or not value.strip() else parse_json(value)


def _holds_object_ids(type_: AtlasType) -> bool:
    if isinstance(type_, ArrayType):
        type_ = resolved(type_.element_type)
    elif isinstance(type_, MapType):
        type_ = resolved(type_.value_type)
    return type_.category is TypeCategory.OBJECT_ID_TYPE
