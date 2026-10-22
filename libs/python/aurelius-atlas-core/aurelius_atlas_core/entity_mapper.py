"""``EntityMapper``: an entity of a write request onto its stored form (EWR-09 to EWR-12, EWR-17, DD-049).

The value side of ``EntityGraphMapper``: what ``mapAttributes``, ``mapRelationshipAttributes`` and ``mapAttribute``
put on a vertex and its edges, here into the attribute values of a ``StoredEntity``.
"""

from collections.abc import Callable, Mapping
from datetime import UTC, datetime, timedelta
from typing import Any

from aurelius_atlas_model.errors import AtlasError, AtlasErrorCode, java_string
from aurelius_atlas_model.instance import AtlasEntity, AtlasObjectId, AtlasStruct, EntityOperation
from aurelius_atlas_model.typedef import Cardinality, TypeCategory
from aurelius_atlas_typesystem.array_type import ArrayType
from aurelius_atlas_typesystem.atlas_type import AtlasType, resolved
from aurelius_atlas_typesystem.attribute import AtlasAttribute
from aurelius_atlas_typesystem.builtin.object_id_type import is_assigned_guid
from aurelius_atlas_typesystem.entity_type import EntityType
from aurelius_atlas_typesystem.map_type import MapType
from aurelius_atlas_typesystem.registry import TypeRegistry
from aurelius_atlas_typesystem.struct_type import StructType, struct_attributes
from aurelius_atlas_typesystem.values import java_distinct, relationship_type_of

from aurelius_atlas_core.entity_retriever import SOFT_REFERENCE_SEPARATOR
from aurelius_atlas_core.stored_entity import StoredEntity

_EPOCH = datetime(1970, 1, 1, tzinfo=UTC)
_MILLISECOND = timedelta(milliseconds=1)
_PRIMITIVES = {TypeCategory.PRIMITIVE, TypeCategory.ENUM}
_KEEP = object()
"""What a mapping answers when the stored value stays as it is."""

type Resolve = Callable[[Any], str]
"""The GUID of the entity a reference value names; raises ``INVALID_OBJECT_ID`` when it names none."""


class EntityMapper:
    """Maps entities of one request at ``now``; ``touched`` lists the entities new references reached (EWR-12)."""

    def __init__(
        self,
        registry: TypeRegistry,
        *,
        resolve: Resolve,
        guid_assignments: Mapping[str, str],
        now: int,
        user: str | None,
    ) -> None:
        self._registry = registry
        self._resolve = resolve
        self._guid_assignments = guid_assignments
        self._now = now
        self._user = user
        self._recording = True
        self.touched: list[str] = []

    def create(self, entity: AtlasEntity, entity_type: EntityType, guid: str) -> StoredEntity:
        """``createVertexWithGuid`` and ``mapAttributes(CREATE)``: a new entity as stored (EWR-09)."""
        attributes: dict[str, Any] = {}
        self._relationship_attributes(entity, entity_type, attributes, EntityOperation.CREATE)
        if entity.attributes:
            for name, attribute in entity_type.all_attributes.items():
                self._set(attributes, attribute, entity.attributes.get(name), EntityOperation.CREATE)
        return StoredEntity(
            guid=guid,
            type_name=str(entity_type.type_name),
            super_type_names=list(entity_type.all_super_types),
            create_time=self._now,
            update_time=self._now,
            created_by=self._user,
            updated_by=self._user,
            version=entity.version or 0,
            labels=list(dict.fromkeys(entity.labels or [])) or None,
            custom_attributes=entity.custom_attributes,
            attributes=attributes,
        )

    def update(
        self, entity: AtlasEntity, entity_type: EntityType, stored: StoredEntity, *, partial: bool
    ) -> StoredEntity:
        """``mapAttributes(UPDATE)``: the given attributes and custom attributes over the stored ones (EWR-10)."""
        operation = EntityOperation.PARTIAL_UPDATE if partial else EntityOperation.UPDATE
        attributes = dict(stored.attributes)
        changed = self._relationship_attributes(entity, entity_type, attributes, operation)
        for name, value in (entity.attributes or {}).items():
            attribute = entity_type.attribute(name)
            if attribute is not None:
                self._set(attributes, attribute, value, operation)
            changed = True
        update: dict[str, Any] = {"attributes": attributes}
        if entity.custom_attributes is not None:
            update["custom_attributes"] = entity.custom_attributes
        if changed:
            update.update(update_time=self._now, updated_by=self._user)
        return stored.model_copy(update=update)

    def touch(self, stored: StoredEntity) -> StoredEntity:
        """``updateModificationMetadata``: the entity, changed by this request (EWR-12)."""
        return stored.touched(now=self._now, user=self._user)

    def _relationship_attributes(
        self, entity: AtlasEntity, entity_type: EntityType, attributes: dict[str, Any], operation: EntityOperation
    ) -> bool:
        """``mapRelationshipAttributes``: a legacy end's value as its attribute's, others checked only (EWR-17)."""
        if not entity.relationship_attributes:
            return False
        for name in entity_type.relationship_attributes:
            if operation is not EntityOperation.CREATE and not entity.has_relationship_attribute(name):
                continue
            value = entity.get_relationship_attribute(name)
            attribute = entity_type.relationship_attribute(name, relationship_type_of(value))
            legacy = entity_type.all_attributes.get(name)
            if attribute is None:
                continue  # pragma: no cover - every relationship attribute name has an attribute
            if legacy is not None:
                self._set(attributes, attribute, value, operation, key=legacy.qualified_name)
            else:
                self._recording = False
                try:
                    self._set({}, attribute, value, operation)
                finally:
                    self._recording = True
        return True

    def _set(
        self,
        target: dict[str, Any],
        attribute: AtlasAttribute,
        value: object,
        operation: EntityOperation,
        *,
        key: str | None = None,
    ) -> None:
        name = key or attribute.qualified_name
        mapped = self._attribute(attribute, value, target.get(name), operation)
        if mapped is None:
            target.pop(name, None)
        elif mapped is not _KEEP:
            target[name] = mapped

    def _attribute(self, attribute: AtlasAttribute, value: object, current: object, operation: EntityOperation) -> Any:  # noqa: ANN401, PLR0911 - one case per kind, as Java's switch
        """``mapAttribute`` and ``mapToVertexByTypeCategory``: the value to store, or ``_KEEP``."""
        type_ = attribute.attribute_type
        category = type_.category
        if value is None and category is TypeCategory.PRIMITIVE:
            value = _default(attribute)
        if category in _PRIMITIVES:
            return _primitive(type_, value)
        if operation is EntityOperation.CREATE and value is None:
            return _KEEP
        if category is TypeCategory.STRUCT and isinstance(type_, StructType):
            return self._struct(type_, value, current, operation)
        if category is TypeCategory.OBJECT_ID_TYPE:
            if attribute.attribute_def.is_soft_referenced():
                return self._soft_reference(value)
            guid = None if value is None else self._resolve(value)
            if self._recording and current is None and guid is not None and guid not in self.touched:
                self.touched.append(guid)
            return guid
        if isinstance(type_, ArrayType):
            return self._array(attribute, type_, value, current, operation)
        if isinstance(type_, MapType):
            return self._map(attribute, type_, value, current, operation)
        raise AtlasError(AtlasErrorCode.TYPE_CATEGORY_INVALID, category.value)  # pragma: no cover - no other kind

    def _struct(self, type_: StructType, value: object, current: object, operation: EntityOperation) -> Any:  # noqa: ANN401 - a stored struct
        """``mapStructValue``: a stored struct takes the given attributes; a null value leaves it (EWR-10)."""
        if isinstance(current, Mapping):
            if value is None:
                return current
            _, given = _struct_of(type_, value)
            attributes = dict(current.get("attributes") or {})
            struct_type = self._registry.struct_type(str(current.get("typeName"))) or type_
            self._struct_attributes(struct_type, given, attributes, EntityOperation.UPDATE)
            return {"typeName": current.get("typeName"), "attributes": attributes}
        if value is None:
            return None
        type_name, given = _struct_of(type_, value)
        struct_type = self._registry.struct_type(type_name)
        if struct_type is None:
            raise AtlasError(AtlasErrorCode.TYPE_NAME_INVALID, type_name)
        attributes: dict[str, Any] = {}
        self._struct_attributes(struct_type, given, attributes, operation)
        return {"typeName": type_name, "attributes": attributes}

    def _struct_attributes(
        self, struct_type: StructType, given: Mapping[str, Any], target: dict[str, Any], operation: EntityOperation
    ) -> None:
        """``mapAttributes`` of a struct: every attribute on create, the given ones on update, by name."""
        if not given:
            return
        if operation is EntityOperation.CREATE:
            for name, attribute in struct_type.all_attributes.items():
                self._set(target, attribute, given.get(str(name)), operation, key=str(name))
            return
        for name, value in given.items():
            attribute = struct_type.attribute(name)
            if attribute is not None:
                self._set(target, attribute, value, operation, key=name)

    def _array(
        self, attribute: AtlasAttribute, type_: ArrayType, value: object, current: object, operation: EntityOperation
    ) -> list[Any] | None:
        """``mapArrayValue``: each element mapped, nulls dropped, appended on a partial update if asked (EWR-11)."""
        element = resolved(type_.element_type)
        stored = list(current) if isinstance(current, list) else []
        appending = (
            operation is EntityOperation.PARTIAL_UPDATE
            and attribute.attribute_def.is_append_on_partial_update()
            and bool(stored)
        )
        if value is None and not appending:
            return None
        items = list(value) if isinstance(value, list | tuple | set) else []
        if attribute.attribute_def.cardinality is Cardinality.SET:
            items = java_distinct(items)
        mapped: list[Any] = []
        for index, item in enumerate(items):
            existing = stored[index] if not appending and index < len(stored) else None
            found = self._element(attribute, element, item, existing, operation)
            if found is not None:
                mapped.append(found)
        if appending:
            mapped = stored + mapped
            if attribute.attribute_def.cardinality is Cardinality.SET:
                mapped = java_distinct(mapped)
        return mapped

    def _map(
        self, attribute: AtlasAttribute, type_: MapType, value: object, current: object, operation: EntityOperation
    ) -> dict[str, Any] | None:
        """``mapMapValue``: each entry mapped by key; appended on a partial update if asked (EWR-11)."""
        item_type = resolved(type_.value_type)
        stored = dict(current) if isinstance(current, Mapping) else {}
        appending = (
            operation is EntityOperation.PARTIAL_UPDATE
            and attribute.attribute_def.is_append_on_partial_update()
            and bool(stored)
        )
        if value is None and not appending:
            return None
        entries = value if isinstance(value, Mapping) else {}
        mapped: dict[str, Any] = {}
        for key, item in entries.items():
            text = java_string(key)
            if item_type.category in _PRIMITIVES or item_type.category in {TypeCategory.ARRAY, TypeCategory.MAP}:
                mapped[text] = _primitive(item_type, item)
                continue
            found = self._element(attribute, item_type, item, stored.get(text), operation)
            if found is not None or attribute.attribute_def.is_soft_referenced():
                mapped[text] = found
        return {**stored, **mapped} if appending else mapped

    def _element(
        self, attribute: AtlasAttribute, element: AtlasType, item: object, existing: object, operation: EntityOperation
    ) -> Any:  # noqa: ANN401 - a stored element
        """``mapCollectionElementsToVertex``: an element of an array or a value of a map."""
        if element.category is TypeCategory.STRUCT and isinstance(element, StructType):
            return self._struct(element, item, existing, operation)
        if element.category is TypeCategory.OBJECT_ID_TYPE:
            if attribute.attribute_def.is_soft_referenced():
                return self._soft_reference(item)
            if item is None:
                raise AtlasError(AtlasErrorCode.INVALID_OBJECT_ID, None)
            return self._resolve(item)
        return _primitive(element, item)

    def _soft_reference(self, value: object) -> str | None:
        """``mapSoftRefValue``: ``typeName:guid`` of an object id, a GUID assigned here for an unassigned one."""
        if not isinstance(value, AtlasObjectId):
            return None
        guid = value.guid
        if guid and not is_assigned_guid(guid):
            guid = self._guid_assignments.get(guid)
        return f"{java_string(value.type_name)}{SOFT_REFERENCE_SEPARATOR}{java_string(guid)}"


def _default(attribute: AtlasAttribute) -> Any:  # noqa: ANN401 - a Java value
    """The value a null primitive attribute is stored with: its definition's default, else its type's (EWR-09)."""
    definition, type_ = attribute.attribute_def, attribute.attribute_type
    if definition.default_value is not None:
        return type_.create_default_value_of(definition.default_value)
    if definition.is_optional:
        return type_.create_optional_default_value()
    return type_.create_default_value()


def _primitive(type_: AtlasType, value: object) -> Any:  # noqa: ANN401 - a stored value
    """A value as stored: normalised by its type, a date as epoch milliseconds (DD-049)."""
    if value is None:
        return None
    if type_.category in _PRIMITIVES:
        normalized = type_.get_normalized_value(value)
        value = value if normalized is None else normalized
    return _plain(value)


def _plain(value: object) -> Any:  # noqa: ANN401 - a stored value
    if isinstance(value, datetime):
        return (value - _EPOCH) // _MILLISECOND
    if isinstance(value, list | tuple | set):
        return [_plain(item) for item in value]
    if isinstance(value, Mapping):
        return {java_string(key): _plain(item) for key, item in value.items()}
    return value


def _struct_of(type_: StructType, value: object) -> tuple[str, Mapping[str, Any]]:
    """The type name and attributes of a struct value: a struct's own, or a map's for ``type_`` (EWR-10)."""
    if isinstance(value, AtlasStruct):
        return str(value.type_name), value.attributes or {}
    if isinstance(value, Mapping):
        return str(type_.type_name), struct_attributes(value)
    raise AtlasError(AtlasErrorCode.INVALID_STRUCT_VALUE, value)
