"""``AtlasType``: what every type has, its name and category, and the value contract (VAL-02, DD-041)."""

from typing import TYPE_CHECKING, Any

from aurelius_atlas_model.errors import AtlasError, AtlasErrorCode, java_string
from aurelius_atlas_model.typedef import TypeCategory

if TYPE_CHECKING:
    from aurelius_atlas_typesystem.registry import TypeRegistry

UNIMPLEMENTED_VALUE_ERROR = "{type} has no value side yet (2.1c)"


class AtlasType:
    """A type: its name, category and service type, and how it checks, normalises and compares values.

    The value methods are Java's, in snake_case: ``create_default_value`` is ``createDefaultValue``,
    ``is_valid_value`` is ``isValidValue`` and so on. A value is a Java value as DD-040 holds it.
    """

    def __init__(self, type_name: str | None, category: TypeCategory, service_type: str | None) -> None:
        self.type_name = type_name
        self.category = category
        self.service_type = service_type

    def type_for_attribute(self) -> AtlasType:
        """The type an attribute of this type holds; an entity type is held as an ``objectid`` (TRG-11)."""
        return self

    def create_default_value(self) -> Any:  # noqa: ANN401 - a Java value of this type
        """The value an attribute of this type gets by default (``createDefaultValue()``)."""
        raise NotImplementedError(UNIMPLEMENTED_VALUE_ERROR.format(type=self.type_name))

    def create_optional_default_value(self) -> Any:  # noqa: ANN401 - a Java value of this type
        """The default of an optional attribute; the default, unless a type says otherwise."""
        return self.create_default_value()

    def create_default_value_of(self, value: object) -> Any:  # noqa: ANN401 - a Java value of this type
        """``createDefaultValue(Object)``: the default for null, else the normalised value (VAL-02)."""
        return self.create_default_value() if value is None else self.get_normalized_value(value)

    def is_valid_value(self, value: object) -> bool:
        """Whether ``value`` is a value of this type (``isValidValue``)."""
        raise NotImplementedError(UNIMPLEMENTED_VALUE_ERROR.format(type=self.type_name))

    def get_normalized_value(self, value: object) -> Any:  # noqa: ANN401 - a Java value of this type
        """``value`` as this type holds it, or None when it is not a value of this type (``getNormalizedValue``)."""
        raise NotImplementedError(UNIMPLEMENTED_VALUE_ERROR.format(type=self.type_name))

    def validate_value(self, value: object, name: str, messages: list[str]) -> bool:
        """Whether ``value`` is valid; if not, add ``<name>=<value>: invalid value for type <type>`` (VAL-02)."""
        valid = self.is_valid_value(value)
        if not valid:
            messages.append(f"{name}={java_string(value)}: invalid value for type {self.type_name}")
        return valid

    def is_valid_value_for_update(self, value: object) -> bool:
        """``isValidValueForUpdate``: as ``is_valid_value``, unless a type says otherwise."""
        return self.is_valid_value(value)

    def get_normalized_value_for_update(self, value: object) -> Any:  # noqa: ANN401 - a Java value of this type
        """``getNormalizedValueForUpdate``: as ``get_normalized_value``, unless a type says otherwise."""
        return self.get_normalized_value(value)

    def validate_value_for_update(self, value: object, name: str, messages: list[str]) -> bool:
        """``validateValueForUpdate``: as ``validate_value``, unless a type says otherwise."""
        return self.validate_value(value, name, messages)

    def are_equal_values(
        self,
        left: object,
        right: object,
        guid_assignments: dict[str, str] | None,  # noqa: ARG002 - Java's signature; object ids use it
    ) -> bool:
        """``areEqualValues``: both null, or both normalise to equal values (VAL-02)."""
        if left is None or right is None:
            return left is None and right is None
        normalized_left = self.get_normalized_value(left)
        if normalized_left is None:
            return False
        normalized_right = self.get_normalized_value(right)
        return normalized_right is not None and normalized_left == normalized_right

    def _resolve_references(self, registry: TypeRegistry) -> None:
        """Phase 1: resolve the names this type refers to."""

    def _resolve_references_phase2(self, registry: TypeRegistry) -> None:
        """Phase 2: link what needs every type's phase 1 done."""

    def _resolve_references_phase3(self, registry: TypeRegistry) -> None:
        """Phase 3: link what needs every type's phase 2 done."""


def resolved(type_: AtlasType | None) -> AtlasType:
    """A type a containing type has resolved; it is resolved before its values or attribute type are asked for.

    Raises:
        AtlasError: ``INTERNAL_ERROR`` for an unresolved type.
    """
    if type_ is None:  # pragma: no cover - a type is resolved before it is used
        raise AtlasError(AtlasErrorCode.INTERNAL_ERROR, "unresolved type")
    return type_


def type_name_of(type_: AtlasType) -> str:
    """The name of ``type_``, which every resolved type has."""
    return str(type_.type_name)
