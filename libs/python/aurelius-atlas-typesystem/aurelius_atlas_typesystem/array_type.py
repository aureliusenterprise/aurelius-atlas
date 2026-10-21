"""``AtlasArrayType``: ``array<T>``, its counts and cardinality, and its values (TRG-02, VAL-12)."""

from collections.abc import Callable
from typing import TYPE_CHECKING, Any, TypeGuard

from aurelius_atlas_model.errors import java_string
from aurelius_atlas_model.typedef import (
    COUNT_NOT_SET,
    SERVICE_TYPE_ATLAS_CORE,
    Cardinality,
    TypeCategory,
    array_type_name,
)

from aurelius_atlas_typesystem.atlas_type import AtlasType, resolved, type_name_of
from aurelius_atlas_typesystem.values import java_distinct, parse_json

if TYPE_CHECKING:
    from aurelius_atlas_typesystem.registry import TypeRegistry


class ArrayType(AtlasType):
    """``array<T>`` with its cardinality and value counts (``AtlasArrayType``, TRG-02)."""

    def __init__(
        self,
        element_type_name: str,
        *,
        element_type: AtlasType | None = None,
        min_count: int = COUNT_NOT_SET,
        max_count: int = COUNT_NOT_SET,
        cardinality: Cardinality = Cardinality.LIST,
    ) -> None:
        super().__init__(array_type_name(element_type_name), TypeCategory.ARRAY, SERVICE_TYPE_ATLAS_CORE)
        self.element_type_name = element_type_name
        self.element_type = element_type
        self.min_count = min_count
        self.max_count = max_count
        self.cardinality = cardinality

    def type_for_attribute(self) -> AtlasType:
        """This array, or a new one over the element's attribute type when that differs (TRG-11)."""
        element = resolved(self.element_type).type_for_attribute()
        if element is self.element_type:
            return self
        return ArrayType(
            type_name_of(element),
            element_type=element,
            min_count=self.min_count,
            max_count=self.max_count,
            cardinality=self.cardinality,
        )

    def create_default_value(self) -> list[Any]:
        """The element's default, ``minCount`` times when that is set, else once (VAL-12)."""
        return [resolved(self.element_type).create_default_value() for _ in range(max(1, self.min_count))]

    def is_valid_value(self, value: object) -> bool:
        """Null, or a list with a valid count of valid elements; a string is not (VAL-12)."""
        return self._is_valid(value, resolved(self.element_type).is_valid_value)

    def is_valid_value_for_update(self, value: object) -> bool:
        """As ``is_valid_value``, with the elements' ``isValidValueForUpdate``."""
        return self._is_valid(value, resolved(self.element_type).is_valid_value_for_update)

    def get_normalized_value(self, value: object) -> list[Any] | None:
        """A string parsed as JSON, then each element normalised, nulls kept; None for a wrong count or element."""
        return self._normalized(value, resolved(self.element_type).get_normalized_value)

    def get_normalized_value_for_update(self, value: object) -> list[Any] | None:
        """As ``get_normalized_value``, with the elements' ``getNormalizedValueForUpdate``."""
        return self._normalized(value, resolved(self.element_type).get_normalized_value_for_update)

    def validate_value(self, value: object, name: str, messages: list[str]) -> bool:
        """Report a wrong count, then validate each element as ``<name>[<i>]`` (VAL-12)."""
        return self._validate(value, name, messages, resolved(self.element_type).validate_value)

    def validate_value_for_update(self, value: object, name: str, messages: list[str]) -> bool:
        """As ``validate_value``, with the elements' ``validateValueForUpdate``."""
        return self._validate(value, name, messages, resolved(self.element_type).validate_value_for_update)

    def are_equal_values(self, left: object, right: object, guid_assignments: dict[str, str] | None) -> bool:
        """A ``SET`` as sets, anything else as lists, each element compared by the element type (VAL-12)."""
        if left is None or right is None:
            return left is None and right is None
        if left is right:
            return True
        elements = resolved(self.element_type)
        first, second = _elements_of(left), _elements_of(right)
        if first is None or second is None:  # pragma: no cover - Java fails on these with a NullPointerException
            return False
        if self.cardinality is Cardinality.SET:
            first, second = java_distinct(first), java_distinct(second)
            return len(first) == len(second) and all(
                any(elements.are_equal_values(a, b, guid_assignments) for b in second) for a in first
            )
        return len(first) == len(second) and all(
            elements.are_equal_values(a, b, guid_assignments) for a, b in zip(first, second, strict=True)
        )

    def _valid_count(self, count: int) -> bool:
        """``isValidElementCount``: within ``minCount`` and ``maxCount``, each when set."""
        return (self.min_count == COUNT_NOT_SET or count >= self.min_count) and (
            self.max_count == COUNT_NOT_SET or count <= self.max_count
        )

    def _is_valid(self, value: object, valid: Callable[[object], bool]) -> bool:
        if value is None:
            return True
        if not _is_collection(value):
            return False
        return self._valid_count(len(value)) and all(valid(element) for element in value)

    def _normalized(self, value: object, normalize: Callable[[object], Any]) -> list[Any] | None:
        if isinstance(value, str):
            value = parse_json(value)
        if not _is_collection(value) or not self._valid_count(len(value)):
            return None
        normalized: list[Any] = []
        for element in value:
            if element is None:
                normalized.append(None)
                continue
            element_value = normalize(element)
            if element_value is None:
                return None
            normalized.append(element_value)
        return normalized

    def _validate(
        self, value: object, name: str, messages: list[str], validate: Callable[[object, str, list[str]], bool]
    ) -> bool:
        if value is None:
            return True
        if not _is_collection(value):
            messages.append(f"{name}={java_string(value)}: invalid value for type {self.type_name}")
            return False
        valid = True
        if not self._valid_count(len(value)):
            valid = False
            messages.append(
                f"{name}: incorrect number of values. found={len(value)}; "
                f"expected: minCount={self.min_count}, maxCount={self.max_count}"
            )
        for index, element in enumerate(value):
            valid = validate(element, f"{name}[{index}]", messages) and valid
        return valid

    def _resolve_references(self, registry: TypeRegistry) -> None:
        self.element_type = registry.get_type(self.element_type_name)


def _is_collection(value: object) -> TypeGuard[list[Any] | tuple[Any, ...] | set[Any] | frozenset[Any]]:
    """A Java ``List``, ``Set`` or array: a list, set or tuple."""
    return isinstance(value, list | tuple | set | frozenset)


def _elements_of(value: object) -> list[Any] | None:
    """``getListFromValue`` and ``getSetFromValue``: the elements of a collection, or of a JSON string."""
    if isinstance(value, str):
        value = parse_json(value)
    return list(value) if _is_collection(value) else None
