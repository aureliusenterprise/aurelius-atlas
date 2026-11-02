"""``EntityBusinessMetadata``: entities' business attributes (BMD-02 to BMD-06) and their import (BMI-01 to BMI-05).

The business metadata methods of ``AtlasEntityStoreV2`` (``addOrUpdateBusinessAttributes``,
``removeBusinessAttributes``, ``validateBusinessAttributes``) and the mapping ``EntityGraphMapper`` does for them
(``setBusinessAttributes``, ``addOrUpdateBusinessAttributes``, ``removeBusinessAttributes``), and
``bulkCreateOrUpdateBusinessAttributes`` with the parsers of ``AtlasGraphUtilsV2`` it uses. A business attribute
is stored among the entity's attributes under its qualified name, ``<business metadata>.<attribute>``, as Atlas
stores it as a vertex property of that name (DD-302). Each request is one write, run again once after a lost race
(DD-052).
"""

from collections.abc import Awaitable, Callable, Mapping
from typing import Any

from aurelius_atlas_model.bulk_import import BulkImportResponse, ImportInfo, ImportStatus
from aurelius_atlas_model.errors import AtlasError, AtlasErrorCode, java_string
from aurelius_atlas_model.instance import EntityOperation
from aurelius_atlas_typesystem.array_type import ArrayType
from aurelius_atlas_typesystem.attribute import AtlasAttribute
from aurelius_atlas_typesystem.business_metadata_type import BusinessAttribute
from aurelius_atlas_typesystem.entity_type import EntityType
from aurelius_atlas_typesystem.enum_type import EnumType
from aurelius_atlas_typesystem.java import (
    INT_MAX,
    INT_MIN,
    LONG_MAX,
    LONG_MIN,
    SHORT_MAX,
    SHORT_MIN,
    parse_double,
    parse_float,
    parse_long,
)
from aurelius_atlas_typesystem.registry import TypeRegistry

from aurelius_atlas_core.authorization import ALLOW_ALL, AtlasPrivilege, Authorizer
from aurelius_atlas_core.entity_change_notifier import EntityChangeNotifier
from aurelius_atlas_core.entity_documents import VersionedEntity
from aurelius_atlas_core.entity_mapper import EntityMapper
from aurelius_atlas_core.entity_retriever import EntityRetriever
from aurelius_atlas_core.entity_store import (
    EntityChange,
    EntityStore,
    EntityVersionConflictError,
    EntityWriteError,
    UniqueValueTakenError,
)
from aurelius_atlas_core.file_utils import PIPE_CHARACTER, Row, java_split, read_file_data
from aurelius_atlas_core.stored_entity import StoredEntity

ATTEMPTS = 2
"""A request that loses a race is run once more (DD-052)."""

NO_GUID = "guid is null/empty"
NO_BUSINESS_ATTRIBUTES = "businessAttributes is null/empty"

TYPENAME_COLUMN_INDEX = 0
UNIQUE_ATTR_VALUE_COLUMN_INDEX = 1
BM_ATTR_NAME_COLUMN_INDEX = 2
BM_ATTR_VALUE_COLUMN_INDEX = 3
UNIQUE_ATTR_NAME_COLUMN_INDEX = 4
"""``FileUtils``: the columns of a business metadata import row."""
QUALIFIED_NAME = "qualifiedName"
"""``AtlasTypeUtil.ATTRIBUTE_QUALIFIED_NAME``: the unique attribute a row names unless it names another."""


HEADERS = (
    "EntityType",
    "EntityUniqueAttributeValue",
    "BusinessAttributeName",
    "BusinessAttributeValue",
    "EntityUniqueAttributeName[optional]",
)


def business_metadata_headers() -> str:
    """``FileUtils.getBusinessMetadataHeaders``: the import template's header line (BMI-01)."""
    return ",".join(HEADERS)


type BusinessAttributes = Mapping[str, Mapping[str, Any] | None]
"""Business attribute values by business metadata name, then attribute name, as a request gives them."""
type Updated = dict[str, dict[str, Any]]
"""The values a change gave each business attribute it changed, None for one it removed."""


class EntityBusinessMetadata:
    """Business attributes of the entities of ``store``, changed as ``user``; ``notifier`` is told the attributes each
    change updated once it is written, and ``authorizer`` checks each business metadata changed (AUZ-17).
    """  # noqa: D205 - one sentence

    def __init__(
        self,
        store: EntityStore,
        *,
        user: str | None = None,
        notifier: EntityChangeNotifier | None = None,
        authorizer: Authorizer = ALLOW_ALL,
    ) -> None:
        self._store = store
        self._user = user
        self._notifier = notifier
        self._authorizer = authorizer

    async def add_or_update_business_attributes(
        self, guid: str, given: BusinessAttributes | None, *, is_overwrite: bool = False
    ) -> None:
        """``addOrUpdateBusinessAttributes``: the given values set on the entity; with ``is_overwrite``, every
        business attribute of its type becomes the given value or none (BMD-03, BMD-04, AUZ-17).

        Raises:
            AtlasError: ``INVALID_PARAMETERS``, ``INSTANCE_GUID_NOT_FOUND``, ``UNAUTHORIZED_ACCESS``,
                ``INSTANCE_CRUD_INVALID_PARAMS``.
        """  # noqa: D205 - one sentence
        if not guid:
            raise AtlasError(AtlasErrorCode.INVALID_PARAMETERS, NO_GUID)
        if not given:
            raise AtlasError(AtlasErrorCode.INVALID_PARAMETERS, NO_BUSINESS_ATTRIBUTES)

        async def attempt() -> Updated:
            found = await self._entity(guid)
            entity_type = self._entity_type(found.entity)
            current = await EntityRetriever(self._store).business_attributes(found.entity) or {}
            for name in entity_type.business_attributes:
                values = given.get(name)
                if values is None and not is_overwrite:
                    continue
                if (not values and not current.get(name)) or values == current.get(name):
                    continue
                self._authorizer.verify_access(
                    AtlasPrivilege.ENTITY_UPDATE_BUSINESS_METADATA,
                    "add/update business-metadata: guid=",
                    guid,
                    ", business-metadata-name=",
                    name,
                )
            validate_business_attributes(found.entity, entity_type, given, is_overwrite=is_overwrite)
            mapper = self._mapper()
            entity, updated = (
                set_business_attributes(mapper, found.entity, entity_type, given)
                if is_overwrite
                else add_or_update_business_attributes(mapper, found.entity, entity_type, given)
            )
            if updated or is_overwrite:
                await self._write(found, entity)
            return updated

        await self._run(guid, attempt)

    async def remove_business_attributes(self, guid: str, given: BusinessAttributes | None) -> None:
        """``removeBusinessAttributes``: the given attributes, or all of a business metadata given none, removed
        from the entity (BMD-05, AUZ-17).

        Raises:
            AtlasError: ``INVALID_PARAMETERS``, ``INSTANCE_GUID_NOT_FOUND``, ``UNAUTHORIZED_ACCESS``.
        """  # noqa: D205 - one sentence
        if not guid:
            raise AtlasError(AtlasErrorCode.INVALID_PARAMETERS, NO_GUID)
        if not given:
            raise AtlasError(AtlasErrorCode.INVALID_PARAMETERS, NO_BUSINESS_ATTRIBUTES)

        async def attempt() -> Updated:
            found = await self._entity(guid)
            entity_type = self._entity_type(found.entity)
            for name in given:
                self._authorizer.verify_access(
                    AtlasPrivilege.ENTITY_UPDATE_BUSINESS_METADATA,
                    "remove business-metadata: guid=",
                    guid,
                    ", business-metadata=",
                    name,
                )
            attributes = dict(found.entity.attributes)
            updated: Updated = {}
            for name, business_attributes in entity_type.business_attributes.items():
                if name not in given:
                    continue
                values = given[name]
                for attribute in business_attributes.values():
                    if not values or str(attribute.name) in values:
                        attributes.pop(attribute.qualified_name, None)
                        updated.setdefault(name, {})[str(attribute.name)] = None
            if updated:
                await self._write(found, found.entity.model_copy(update={"attributes": attributes}))
            return updated

        await self._run(guid, attempt)

    async def bulk_create_or_update_business_attributes(
        self, file_name: str | None, content: bytes
    ) -> BulkImportResponse:
        """``bulkCreateOrUpdateBusinessAttributes``: each entity the file's rows name overwritten with its business
        attributes and the rows' values; the rows that fail first, then each entity's outcome (BMI-02 to BMI-05).

        Raises:
            AtlasError: ``FILE_NAME_NOT_FOUND`` for a blank file name; ``INVALID_FILE_TYPE``, ``NOT_VALID_FILE`` or
                ``NO_DATA_FOUND`` for the file.
        """  # noqa: D205 - one sentence
        if file_name is None or not file_name.strip():
            raise AtlasError(AtlasErrorCode.FILE_NAME_NOT_FOUND)
        response = BulkImportResponse()
        for guid, business_attributes in await self._business_metadata_rows(
            read_file_data(file_name, content), response
        ):
            given = java_string(business_attributes)
            try:
                await self.add_or_update_business_attributes(guid, business_attributes, is_overwrite=True)
            except AtlasError as error:
                info = ImportInfo(
                    parent_object_name=guid,
                    child_object_name=given,
                    import_status=ImportStatus.FAILED,
                    remarks=error.message,
                )
                response.failed_import_info_list.append(info)
            else:
                info = ImportInfo(parent_object_name=guid, child_object_name=given, import_status=ImportStatus.SUCCESS)
                response.success_import_info_list.append(info)
        return response

    async def _business_metadata_rows(
        self, rows: list[Row], response: BulkImportResponse
    ) -> list[tuple[str, dict[str, dict[str, Any]]]]:
        """``getBusinessMetadataDefList``: each entity's business attributes, its stored ones with the rows' values
        set, in the order the entities are first named (DV-119); each row that fails is reported (BMI-02, BMI-03).
        """  # noqa: D205 - one sentence
        found: dict[str, tuple[str, dict[str, dict[str, Any]]]] = {}
        failed: list[str] = []
        for index, row in enumerate(rows):
            line = f"Line #{index + 2}: "
            named = _named(self._store.registry, row)
            if isinstance(named, str):
                failed.append(line + named)
                continue
            entity_type, unique, unique_name = named
            unique_value, name = str(row[UNIQUE_ATTR_VALUE_COLUMN_INDEX]), str(row[BM_ATTR_NAME_COLUMN_INDEX])
            key = f"{unique.qualified_name}_{unique_value}"
            if key not in found:
                entity = await self._store.find_by_unique_attributes(entity_type, {unique_name: unique_value})
                if entity is None or entity.entity.type_name != entity_type.type_name:
                    failed.append(f"{line}no {entity_type.type_name} entity found with {unique_name}={unique_value}")
                    continue
                current = await EntityRetriever(self._store).business_attributes(entity.entity) or {}
                found[key] = (entity.entity.guid, current)
            metadata_name, _, attribute_name = name.partition(".")
            attribute = entity_type.business_attribute(metadata_name, attribute_name) if "." in name else None
            if attribute is None:
                failed.append(f"{line}invalid business-metadata '{name}' for entity type '{entity_type.type_name}'")
                continue
            value: object = str(row[BM_ATTR_VALUE_COLUMN_INDEX])
            if isinstance(attribute.attribute_type, ArrayType):
                value = _values(str(value), attribute.attribute_type, failed, index + 1)
            found[key][1].setdefault(metadata_name, {})[attribute_name] = value
        response.failed_import_info_list += [
            ImportInfo(parent_object_name="", child_object_name="", import_status=ImportStatus.FAILED, remarks=message)
            for message in failed
        ]
        return list(found.values())

    async def _entity(self, guid: str) -> VersionedEntity:
        found = await self._store.get(guid)
        if found is None:
            raise AtlasError(AtlasErrorCode.INSTANCE_GUID_NOT_FOUND, guid)
        return found

    def _entity_type(self, stored: StoredEntity) -> EntityType:
        entity_type = self._store.registry.entity_type(stored.type_name)
        if entity_type is None:  # pragma: no cover - a stored entity's type is registered
            raise AtlasError(AtlasErrorCode.TYPE_NAME_INVALID, "ENTITY", stored.type_name)
        return entity_type

    def _mapper(self) -> EntityMapper:
        return EntityMapper(
            self._store.registry, resolve=_unresolved, guid_assignments={}, now=self._store.now(), user=self._user
        )

    async def _write(self, found: VersionedEntity, entity: StoredEntity) -> None:
        """The entity written, changed at the request's time by its user (``updateModificationMetadata``)."""
        touched = entity.touched(now=self._store.now(), user=self._user)
        await self._store.write([EntityChange(touched, found.version)])

    async def _run(self, guid: str, attempt: Callable[[], Awaitable[Updated]]) -> None:
        """Run once more after a lost race; a second loss or a failed write is ``INTERNAL_ERROR`` (DD-052).

        The attributes the write updated are told after it (BMD-06).
        """
        for number in range(1, ATTEMPTS + 1):
            try:
                updated = await attempt()
            except EntityVersionConflictError as conflict:
                if number == ATTEMPTS:
                    raise AtlasError(AtlasErrorCode.INTERNAL_ERROR, str(conflict)) from conflict
            except (UniqueValueTakenError, EntityWriteError) as failure:
                raise AtlasError(AtlasErrorCode.INTERNAL_ERROR, str(failure)) from failure
            else:
                if updated and self._notifier is not None:
                    await self._notifier.on_business_attributes_updated(guid, updated, user=self._user)
                return


def validate_business_attributes(
    stored: StoredEntity, entity_type: EntityType, given: BusinessAttributes, *, is_overwrite: bool
) -> None:
    """``validateBusinessAttributes``: each business metadata the type's, each value valid and short enough, each
    mandatory attribute given or, unless overwriting, stored (BMD-03).

    Raises:
        AtlasError: ``INSTANCE_CRUD_INVALID_PARAMS`` with every message.
    """  # noqa: D205 - one sentence
    messages: list[str] = []
    type_name = str(entity_type.type_name)
    for name, values in given.items():
        business_attributes = entity_type.business_attributes.get(name)
        if business_attributes is None:
            messages.append(f"{name}: invalid business-metadata for entity type {type_name}")
            continue
        for attribute in business_attributes.values():
            value = (values or {}).get(str(attribute.name))
            field = f"{type_name}.{name}.{attribute.name}"
            if value is not None:
                attribute.attribute_type.validate_value(value, field, messages)
                if not _valid_length(attribute, value):
                    messages.append(f"{field}:  Business attribute-value exceeds maximum length limit")
            elif not attribute.attribute_def.is_optional and (
                is_overwrite or stored.attributes.get(attribute.qualified_name) is None
            ):
                messages.append(f"{field}: mandatory business-metadata attribute value missing in type {type_name}")
    if messages:
        raise AtlasError(AtlasErrorCode.INSTANCE_CRUD_INVALID_PARAMS, messages)


def add_or_update_business_attributes(
    mapper: EntityMapper, stored: StoredEntity, entity_type: EntityType, given: BusinessAttributes | None
) -> tuple[StoredEntity, Updated]:
    """``EntityGraphMapper.addOrUpdateBusinessAttributes``: each attribute given set, unless its value stays.

    A business metadata the type does not have, or given no values, is left out; so is an attribute not given.
    A null value of an attribute with no stored value is left out; otherwise it sets the attribute's default, as
    ``mapAttribute`` maps a null primitive (BMD-02, BMD-03).
    """
    attributes = dict(stored.attributes)
    updated: Updated = {}
    for name, business_attributes in entity_type.business_attributes.items():
        values = (given or {}).get(name)
        if not values:
            continue
        for attribute in business_attributes.values():
            if attribute.name not in values:
                continue
            value = values[str(attribute.name)]
            existing = attributes.get(attribute.qualified_name)
            if existing is None and value is None:
                continue
            operation = EntityOperation.CREATE if existing is None else EntityOperation.UPDATE
            if _changed(mapper, attributes, attribute, value, operation):
                updated.setdefault(name, {})[str(attribute.name)] = value
    return stored.model_copy(update={"attributes": attributes}), updated


def set_business_attributes(
    mapper: EntityMapper, stored: StoredEntity, entity_type: EntityType, given: BusinessAttributes | None
) -> tuple[StoredEntity, Updated]:
    """``EntityGraphMapper.setBusinessAttributes``: every business attribute of the type becomes its given value,
    and one given none is removed (BMD-04).
    """  # noqa: D205 - one sentence
    attributes = dict(stored.attributes)
    updated: Updated = {}
    for name, business_attributes in entity_type.business_attributes.items():
        values = (given or {}).get(name) or {}
        for attribute in business_attributes.values():
            value = values.get(str(attribute.name))
            existing = attributes.get(attribute.qualified_name)
            if value is None:
                if existing is not None:
                    attributes.pop(attribute.qualified_name)
                    updated.setdefault(name, {})[str(attribute.name)] = None
                continue
            operation = EntityOperation.CREATE if existing is None else EntityOperation.UPDATE
            if _changed(mapper, attributes, attribute, value, operation):
                updated.setdefault(name, {})[str(attribute.name)] = value
    return stored.model_copy(update={"attributes": attributes}), updated


def _changed(
    mapper: EntityMapper,
    attributes: dict[str, Any],
    attribute: BusinessAttribute,
    value: object,
    operation: EntityOperation,
) -> bool:
    """Map the value over the stored one; whether the stored value changed (``Objects.equals``)."""
    before = attributes.get(attribute.qualified_name)
    mapper.set_value(attributes, attribute, value, operation)
    return attributes.get(attribute.qualified_name) != before


def _valid_length(attribute: BusinessAttribute, value: object) -> bool:
    """``isValidLength``: a string, or each string of an array, at most the attribute's maximum length."""
    limit = attribute.max_string_length
    type_name = str(attribute.attribute_type.type_name)
    if type_name == "string":
        return len(str(value)) <= limit
    if type_name == "array<string>" and isinstance(value, list | set | tuple):
        return all(element is None or len(str(element)) <= limit for element in value)
    return True


def _unresolved(value: object) -> str:  # pragma: no cover - business attributes hold no references
    raise AtlasError(AtlasErrorCode.INVALID_OBJECT_ID, value)


_PARSERS: dict[str, tuple[Callable[[str], object], str]] = {
    "float": (parse_float, "is Float of Long type"),
    "int": (lambda text: _ranged(text, INT_MIN, INT_MAX), "is Integer of Long type"),
    "long": (lambda text: _ranged(text, LONG_MIN, LONG_MAX), "is not of Long type"),
    "date": (lambda text: _ranged(text, LONG_MIN, LONG_MAX), "is not of Long type"),
    "short": (lambda text: _ranged(text, SHORT_MIN, SHORT_MAX), "is not of Short type"),
    "double": (parse_double, "is not of Double type"),
    "boolean": (lambda text: text.lower() == "true", ""),
}
"""``assignMultipleValues``: the parser of each element type, and the text of a value it cannot parse."""


def _values(text: str, array_type: ArrayType, failed: list[str], line: int) -> list[object]:
    """``assignMultipleValues`` and ``assignEnumValues``: the values apart by ``|``, those that fail reported."""
    values: list[object] = []
    element = array_type.element_type
    for part in java_split(text, PIPE_CHARACTER):
        if isinstance(element, EnumType):
            parsed, problem = (
                (part, None) if element.element(part) is not None else (None, "is Enumeration of Long type")
            )
        else:
            parser, problem = _PARSERS.get(str(array_type.element_type_name), (lambda value: value, ""))
            parsed = parser(part)
        if parsed is None:
            failed.append(f"Provided value {part} {problem} at line #{line}")
        else:
            values.append(parsed)
    return values


def _ranged(text: str, low: int, high: int) -> int | None:
    """``Integer.parseInt`` and its kin: the text's whole number within the range, or None."""
    value = parse_long(text)
    return value if value is not None and low <= value <= high else None


def _named(registry: TypeRegistry, row: Row) -> tuple[EntityType, AtlasAttribute, str] | str:
    """The entity type of a row, the unique attribute it names and its name; or why the row fails (BMI-02)."""
    columns = (
        TYPENAME_COLUMN_INDEX,
        UNIQUE_ATTR_VALUE_COLUMN_INDEX,
        BM_ATTR_NAME_COLUMN_INDEX,
        BM_ATTR_VALUE_COLUMN_INDEX,
    )
    if len(row) < UNIQUE_ATTR_NAME_COLUMN_INDEX or any(not (row[column] or "").strip() for column in columns):
        return f"missing fields. {java_string(row)}"
    type_name = str(row[TYPENAME_COLUMN_INDEX])
    entity_type = registry.entity_type(type_name)
    if entity_type is None:
        return f"invalid entity-type '{type_name}'"
    unique_name = QUALIFIED_NAME
    if len(row) > UNIQUE_ATTR_NAME_COLUMN_INDEX and (row[UNIQUE_ATTR_NAME_COLUMN_INDEX] or "").strip():
        unique_name = str(row[UNIQUE_ATTR_NAME_COLUMN_INDEX])
    unique = entity_type.attribute(unique_name)
    if unique is None:
        return f"attribute '{unique_name}' not found in entity-type '{type_name}'"
    if not unique.attribute_def.is_unique:
        return f"attribute '{unique_name}' is not an unique attribute in entity-type '{type_name}'"
    return entity_type, unique, unique_name
