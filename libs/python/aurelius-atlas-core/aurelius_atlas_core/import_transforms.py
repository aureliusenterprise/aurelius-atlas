"""``ImportTransforms``, ``ImportTransformer`` and ``ImportTransformsShaper``: an import's ``transforms`` (ITR-01).

The rules change each entity read from the ZIP before it is written (ITR-01 to ITR-05).

The option is JSON of entity type name, then attribute name (``*`` for the entity itself), then a list of
transformer specifications, each a name and its parameters apart by ``:``.
"""

import json
from collections.abc import Callable, Iterable
from typing import Any

from aurelius_atlas_model.impexp import AtlasExportRequest
from aurelius_atlas_model.instance import (
    AtlasClassification,
    AtlasEntity,
    AtlasEntityWithExtInfo,
    AtlasObjectId,
    EntityStatus,
)
from aurelius_atlas_model.typedef import AtlasClassificationDef, AtlasTypesDef

from aurelius_atlas_core.typedef_store import TypedefStore

ALL_ATTRIBUTES = "*"
TOP_LEVEL = "topLevel"
LIST_PREFIX = "list:"

type Transform = Callable[[Any], Any]
"""A transformer: the value or entity it is given, changed."""


class AddClassification:
    """``AddClassification``: the classification added to an entity that lacks it; with ``topLevel``, only to an
    entity an export item names (ITR-03).
    """  # noqa: D205 - one sentence

    def __init__(self, name: str, scope: str) -> None:
        self.classification_name = name
        self._scope = scope
        self.filters: list[AtlasObjectId] = []

    def __call__(self, value: Any) -> Any:  # noqa: ANN401 - any value
        """Add the classification to an entity that passes the filters."""
        if not isinstance(value, AtlasEntity) or not self._passes(value):
            return value
        if value.classifications is None:
            value.classifications = []
        if all(found.type_name != self.classification_name for found in value.classifications):
            value.classifications.append(AtlasClassification(type_name=self.classification_name))
        return value

    def _passes(self, entity: AtlasEntity) -> bool:
        if self._scope != TOP_LEVEL:
            return True
        return any(_matches(found, entity) for found in self.filters)


class AddValueToAttribute:
    """``AddValueToAttribute``: ``name=value`` set, appended to a list, or replacing another value as text (ITR-03)."""

    def __init__(self, name_value: str) -> None:
        self._name: str | None = None
        self._raw: str | None = None
        self._value: object = None
        if "=" not in name_value:
            return
        parts = _split(name_value, "=")
        self._name = parts[0] if parts else None
        self._raw = parts[1] if len(parts) > 1 else ""
        self._value = [self._raw.replace(LIST_PREFIX, "")] if self._raw.startswith(LIST_PREFIX) else self._raw

    def __call__(self, value: Any) -> Any:  # noqa: ANN401 - any value
        """Set or append the value on an entity."""
        if not isinstance(value, AtlasEntity) or self._name is None:
            return value
        existing = value.get_attribute(self._name)
        if existing is None:
            value.set_attribute(self._name, list(self._value) if isinstance(self._value, list) else self._value)
        elif isinstance(existing, list):
            existing.extend(self._value if isinstance(self._value, list) else [self._value])
        else:
            value.set_attribute(self._name, self._raw)
        return value


def _replace(found: str, replaced: str) -> Transform:
    """``Replace``: each occurrence of the text replaced in a text value (``StringUtils.replace``)."""
    return lambda value: value.replace(found, replaced) if isinstance(value, str) and found else value


def _lowercase(value: Any) -> Any:  # noqa: ANN401 - any value
    """``Lowercase``: a text value in lower case."""
    return value.lower() if isinstance(value, str) else value


def _uppercase(value: Any) -> Any:  # noqa: ANN401 - any value
    """``Uppercase``: a text value in upper case."""
    return value.upper() if isinstance(value, str) else value


def _remove_classification(name: str) -> Transform:
    """``RemoveClassification``: each classification of the name taken from an entity."""

    def remove(value: Any) -> Any:  # noqa: ANN401 - any value
        if isinstance(value, AtlasEntity) and value.classifications:
            value.classifications = [found for found in value.classifications if found.type_name != name]
        return value

    return remove


def _clear_attributes(names: str) -> Transform:
    """``ClearAttributes``: each attribute of a comma-separated list set to null on an entity."""

    def clear(value: Any) -> Any:  # noqa: ANN401 - any value
        if isinstance(value, AtlasEntity):
            for name in _split(names, ","):
                value.set_attribute(name, None)
        return value

    return clear


def _set_deleted(value: Any) -> Any:  # noqa: ANN401 - any value
    """``SetDeleted``: an entity's status ``DELETED``."""
    if isinstance(value, AtlasEntity):
        value.status = EntityStatus.DELETED
    return value


def transformer(spec: str) -> Transform | None:
    """``getTransformer``: the transformer a specification names, or None for an empty or unknown one (ITR-02).

    Parameters are apart by ``:`` (or a backslash), empty ones dropped, as ``StringUtils.split`` splits.
    """
    params = _split(spec, ":\\\\")
    key = params[0] if params else spec
    rest = ":".join(params[1:])
    found: dict[str, Callable[[], Transform]] = {
        "replace": lambda: _replace(params[1] if len(params) > 1 else "", params[2] if len(params) > 2 else ""),  # noqa: PLR2004
        "lowercase": lambda: _lowercase,
        "uppercase": lambda: _uppercase,
        "removeClassification": lambda: _remove_classification(rest),
        "add": lambda: AddValueToAttribute(rest),
        "clearAttrValue": lambda: _clear_attributes(rest),
        "setDeleted": lambda: _set_deleted,
        "addClassification": lambda: AddClassification(
            params[1] if len(params) > 1 else "",
            params[2] if len(params) == 3 else "",  # noqa: PLR2004
        ),
    }
    make = found.get(key)
    return None if not key or make is None else make()


class ImportTransforms:
    """``ImportTransforms``: the transformers of each entity type and attribute (ITR-01)."""

    def __init__(self, transforms: dict[str, dict[str, list[Transform]]] | None = None) -> None:
        self.transforms = transforms or {}

    @classmethod
    def from_json(cls, text: str | None) -> ImportTransforms | None:
        """``fromJson``: the transforms of the option's JSON; None without one, none for JSON that is no map."""
        if not text:
            return None
        found = cls()
        try:
            given = json.loads(text)
        except ValueError:
            return found
        for type_name, attributes in given.items() if isinstance(given, dict) else []:
            for attribute, specs in attributes.items() if isinstance(attributes, dict) else []:
                for spec in specs if isinstance(specs, list) else []:
                    made = transformer(str(spec))
                    if made is not None:
                        found.transforms.setdefault(str(type_name), {}).setdefault(str(attribute), []).append(made)
        return found

    def add_parent_transforms_to_sub_types(self, parent: str, sub_types: Iterable[str]) -> None:
        """``addParentTransformsToSubTypes``: a sub type without transforms takes its parent's; one with them gains
        the parent's for the attributes both name (ITR-04).
        """  # noqa: D205 - one sentence
        inherited = self.transforms.get(parent, {})
        for sub_type in sub_types:
            own = self.transforms.get(sub_type)
            if own is None:
                self.transforms[sub_type] = inherited
                continue
            for attribute, transforms in inherited.items():
                if attribute in own and own[attribute] is not transforms:
                    own[attribute].extend(transforms)

    def apply(self, found: AtlasEntityWithExtInfo | None) -> AtlasEntityWithExtInfo | None:
        """``apply``: the entity's and each owned entity's transforms (ITR-01)."""
        if found is None:
            return None
        for entity in [found.entity, *(found.referred_entities or {}).values()]:
            if entity is not None:
                self._apply(entity)
        return found

    def _apply(self, entity: AtlasEntity) -> None:
        """The entity's ``*`` transformers, then each attribute's on the value it has."""
        transforms = self.transforms.get(str(entity.type_name))
        if not transforms:
            return
        for transform in transforms.get(ALL_ATTRIBUTES, []):
            transform(entity)
        for attribute, attribute_transforms in transforms.items():
            if not entity.has_attribute(attribute):
                continue
            value = entity.get_attribute(attribute)
            for transform in attribute_transforms:
                value = transform(value)
            entity.set_attribute(attribute, value)


async def shape(
    transforms: ImportTransforms, request: AtlasExportRequest | None, typedef_store: TypedefStore, user: str | None
) -> None:
    """``ImportTransformsShaper.shape``: each ``addClassification`` filtered by the export's items, its type created
    when missing; then each type's transforms given to its sub types (ITR-03, ITR-04).
    """  # noqa: D205 - one sentence
    for attributes in list(transforms.transforms.values()):
        for attribute_transforms in attributes.values():
            for transform in attribute_transforms:
                if isinstance(transform, AddClassification):
                    transform.filters += list(request.items_to_export) if request is not None else []
                    await _create_classification(transform.classification_name, typedef_store, user)
    registry = typedef_store.registry
    for type_name in list(transforms.transforms):
        entity_type = registry.entity_type(type_name)
        if entity_type is not None:
            transforms.add_parent_transforms_to_sub_types(type_name, entity_type.all_sub_types)


async def _create_classification(name: str, typedef_store: TypedefStore, user: str | None) -> None:
    """``getCreateTag``: the classification type of the name, created when there is none."""
    if typedef_store.registry.classification_type(name) is None:
        await typedef_store.create_types_def(
            AtlasTypesDef(classification_defs=[AtlasClassificationDef(name=name)]), user
        )


def _matches(object_id: AtlasObjectId, entity: AtlasEntity) -> bool:
    """``isMatch``: the item's GUID, else its type and each of its unique values."""
    if not object_id.guid:
        return object_id.type_name == entity.type_name and all(
            entity.get_attribute(name) == value for name, value in (object_id.unique_attributes or {}).items()
        )
    return object_id.guid == entity.guid


def _split(text: str, separators: str) -> list[str]:
    """``StringUtils.split`` by any of the separator characters, adjacent ones as one, no empty parts."""
    parts = [text]
    for separator in separators:
        parts = [piece for part in parts for piece in part.split(separator)]
    return [part for part in parts if part]
