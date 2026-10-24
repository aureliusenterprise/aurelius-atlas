"""``AtlasMapType``: ``map<K,V>`` and its values (TRG-02, VAL-13)."""

from collections.abc import Callable, Mapping
from typing import TYPE_CHECKING, Any

from aurelius_atlas_model.errors import java_string
from aurelius_atlas_model.typedef import SERVICE_TYPE_ATLAS_CORE, TypeCategory, map_type_name

from aurelius_atlas_typesystem.atlas_type import AtlasType, resolved, type_name_of
from aurelius_atlas_typesystem.values import parse_json

if TYPE_CHECKING:
    from aurelius_atlas_typesystem.registry import TypeRegistry


class MapType(AtlasType):
    """``map<K,V>`` (``AtlasMapType``, TRG-02)."""

    def __init__(
        self,
        key_type_name: str,
        value_type_name: str,
        *,
        key_type: AtlasType | None = None,
        value_type: AtlasType | None = None,
    ) -> None:
        super().__init__(map_type_name(key_type_name, value_type_name), TypeCategory.MAP, SERVICE_TYPE_ATLAS_CORE)
        self.key_type_name = key_type_name
        self.value_type_name = value_type_name
        self.key_type = key_type
        self.value_type = value_type

    def type_for_attribute(self) -> AtlasType:
        """This map, or a new one over the key's and value's attribute types when they differ (TRG-11)."""
        key = resolved(self.key_type).type_for_attribute()
        value = resolved(self.value_type).type_for_attribute()
        if key is self.key_type and value is self.value_type:
            return self
        return MapType(type_name_of(key), type_name_of(value), key_type=key, value_type=value)

    def create_default_value(self) -> dict[Any, Any]:
        """The key's default mapped to the value's, or an empty map when the key has no default (VAL-13)."""
        key = resolved(self.key_type).create_default_value()
        return {} if key is None else {key: resolved(self.value_type).create_default_value()}

    def is_valid_value(self, value: object) -> bool:
        """Null, or a map of valid keys and values; a string is not (VAL-13)."""
        return self._is_valid(value, resolved(self.value_type).is_valid_value)

    def is_valid_value_for_update(self, value: object) -> bool:
        """As ``is_valid_value``, with the values' ``isValidValueForUpdate``."""
        return self._is_valid(value, resolved(self.value_type).is_valid_value_for_update)

    def get_normalized_value(self, value: object) -> dict[Any, Any] | None:
        """A string parsed as JSON, then keys and values normalised, null values kept; None for a bad one."""
        return self._normalized(value, resolved(self.value_type).get_normalized_value)

    def get_normalized_value_for_update(self, value: object) -> dict[Any, Any] | None:
        """As ``get_normalized_value``, with the values' ``getNormalizedValueForUpdate``."""
        return self._normalized(value, resolved(self.value_type).get_normalized_value_for_update)

    def validate_value(self, value: object, name: str, messages: list[str]) -> bool:
        """Report each invalid key, and validate each value as ``<name>.<key>`` (VAL-13)."""
        return self._validate(value, name, messages, resolved(self.value_type).validate_value)

    def validate_value_for_update(self, value: object, name: str, messages: list[str]) -> bool:
        """As ``validate_value``, with the values' ``validateValueForUpdate``."""
        return self._validate(value, name, messages, resolved(self.value_type).validate_value_for_update)

    def are_equal_values(self, left: object, right: object, guid_assignments: dict[str, str] | None) -> bool:
        """Null equals an empty map; otherwise the same size and equal values by key (VAL-13)."""
        if left is None:
            return _is_empty_map(right)
        if right is None:
            return _is_empty_map(left)
        first, second = _map_of(left), _map_of(right)
        if first is None or second is None or len(first) != len(second):
            return False
        values = resolved(self.value_type)
        return all(values.are_equal_values(item, second.get(key), guid_assignments) for key, item in first.items())

    def _is_valid(self, value: object, valid: Callable[[object], bool]) -> bool:
        if value is None:
            return True
        if not isinstance(value, Mapping):
            return False
        keys = resolved(self.key_type)
        return all(keys.is_valid_value(key) and valid(item) for key, item in value.items())

    def _normalized(self, value: object, normalize: Callable[[object], Any]) -> dict[Any, Any] | None:
        if value is None:
            return None
        if isinstance(value, str):
            value = parse_json(value)
        if not isinstance(value, Mapping):
            return None
        keys = resolved(self.key_type)
        normalized: dict[Any, Any] = {}
        for key, item in value.items():
            normalized_key = keys.get_normalized_value(key)
            if normalized_key is None:
                return None
            if item is None:
                normalized[normalized_key] = None
                continue
            normalized_item = normalize(item)
            if normalized_item is None:
                return None
            normalized[normalized_key] = normalized_item
        return normalized

    def _validate(
        self, value: object, name: str, messages: list[str], validate: Callable[[object, str, list[str]], bool]
    ) -> bool:
        if value is None:
            return True
        if not isinstance(value, Mapping):
            messages.append(f"{name}={java_string(value)}: invalid value for type {self.type_name}")
            return False
        keys = resolved(self.key_type)
        valid = True
        for key, item in value.items():
            if not keys.is_valid_value(key):
                valid = False
                messages.append(f"{name}.{java_string(key)}: invalid key for type {self.type_name}")
            else:
                valid = validate(item, f"{name}.{java_string(key)}", messages) and valid
        return valid

    def _resolve_references(self, registry: TypeRegistry) -> None:
        self.key_type = registry.get_type(self.key_type_name)
        self.value_type = registry.get_type(self.value_type_name)


def _map_of(value: object) -> Mapping[Any, Any] | None:
    """``getMapFromValue``: a map, or the map of a JSON string; else None."""
    if isinstance(value, str):
        value = parse_json(value)
    return value if isinstance(value, Mapping) else None


def _is_empty_map(value: object) -> bool:
    """``isEmptyMapValue``: null, an empty map, or a string that is not a map or is an empty one."""
    if value is None:
        return True
    if isinstance(value, Mapping):
        return not value
    if isinstance(value, str):
        parsed = parse_json(value)
        return not isinstance(parsed, Mapping) or not parsed
    return False
