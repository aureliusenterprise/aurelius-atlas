"""``EntityMapper``: an entity of a write request onto its stored form (EWR-09 to EWR-12, DD-049).

The value side of ``EntityGraphMapper``: what ``mapAttributes`` and ``mapAttribute`` put on a vertex and its edges,
here into the attribute values of a ``StoredEntity``. Relationship attributes are ``RelationshipMapper``'s (DD-064).
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
from aurelius_atlas_typesystem.values import java_distinct

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
    """Maps entities of one request at ``now``; ``touched`` lists the entities new references reached (EWR-12).

    ``dropped`` lists the owned entities updates no longer name (OWN-01), ``revived`` the ``DELETED`` ones owned map
    entries keep naming (OWN-04); ``is_deleted`` tells whether an entity is ``DELETED``.
    """

    def __init__(  # noqa: PLR0913 - the request's context, as ``EntityMutationContext``
        self,
        registry: TypeRegistry,
        *,
        resolve: Resolve,
        guid_assignments: Mapping[str, str],
        now: int,
        user: str | None,
        is_deleted: Callable[[str], bool] = lambda _: False,
    ) -> None:
        self._registry = registry
        self._resolve = resolve
        self._guid_assignments = guid_assignments
        self._now = now
        self._user = user
        self._is_deleted = is_deleted
        self.touched: list[str] = []
        self.dropped: list[str] = []
        self.revived: list[str] = []

    def create(self, entity: AtlasEntity, entity_type: EntityType, guid: str) -> StoredEntity:
        """``createVertexWithGuid`` and ``mapAttributes(CREATE)``: a new entity as stored (EWR-09)."""
        attributes: dict[str, Any] = {}
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
        changed = bool(entity.relationship_attributes)  # mapRelationshipAttributes changes it too (REL-11)
        for name, value in (entity.attributes or {}).items():
            attribute = entity_type.attribute(name)
            if attribute is not None:
                self._set(attributes, attribute, value, operation)
                if _plainly_owned(attribute):
                    self._owned(attribute, stored.attributes.get(attribute.qualified_name), attributes)
            changed = True
        update: dict[str, Any] = {"attributes": attributes}
        if entity.custom_attributes is not None:
            update["custom_attributes"] = entity.custom_attributes
        if changed:
            update.update(update_time=self._now, updated_by=self._user)
        return stored.model_copy(update=update)

    def _owned(self, attribute: AtlasAttribute, before: object, attributes: Mapping[str, Any]) -> None:
        """``deleteEdgeReference`` and ``updateInConsistentOwnedMapVertices`` of a plain owned reference.

        An entity the stored value named and the new one does not is dropped (OWN-01); a ``DELETED`` one a map entry
        keeps naming is revived (OWN-04).
        """
        after = attributes.get(attribute.qualified_name)
        kept = set(_guids(after))
        self.dropped += [guid for guid in _guids(before) if guid not in kept and guid not in self.dropped]
        if isinstance(before, Mapping) and isinstance(after, Mapping):
            for key, guid in after.items():
                if before.get(key) == guid and self._is_deleted(str(guid)) and guid not in self.revived:
                    self.revived.append(str(guid))

    def touch(self, stored: StoredEntity) -> StoredEntity:
        """``updateModificationMetadata``: the entity, changed by this request (EWR-12)."""
        return stored.touched(now=self._now, user=self._user)

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
            if current is None and guid is not None and guid not in self.touched:
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
            self.struct_attributes(struct_type, given, attributes, EntityOperation.UPDATE)
            return {"typeName": current.get("typeName"), "attributes": attributes}
        if value is None:
            return None
        type_name, given = _struct_of(type_, value)
        struct_type = self._registry.struct_type(type_name)
        if struct_type is None:
            raise AtlasError(AtlasErrorCode.TYPE_NAME_INVALID, type_name)
        attributes: dict[str, Any] = {}
        self.struct_attributes(struct_type, given, attributes, operation)
        return {"typeName": type_name, "attributes": attributes}

    def struct_attributes(
        self, struct_type: StructType, given: Mapping[str, Any], target: dict[str, Any], operation: EntityOperation
    ) -> None:
        """``mapAttributes`` of a struct or classification: every attribute on create, the given ones on update.

        Values go into ``target`` by name (EWR-10, CLS-05, CLS-08).
        """
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


def _plainly_owned(attribute: AtlasAttribute) -> bool:
    """An owned attribute holding references as values: not soft, not a relationship end (DD-064)."""
    return (
        attribute.is_owned_ref
        and attribute.is_object_ref
        and not attribute.attribute_def.is_soft_referenced()
        and attribute.relationship_name is None
    )


def _guids(value: object) -> list[str]:
    """The GUIDs a stored reference value names: a single one, an array's elements or a map's values."""
    items = list(value.values()) if isinstance(value, Mapping) else value if isinstance(value, list) else [value]
    return [str(item) for item in items if item is not None]


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
