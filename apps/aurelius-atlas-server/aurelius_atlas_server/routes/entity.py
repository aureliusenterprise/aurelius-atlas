"""The entity reads of ``EntityREST`` under ``/api/atlas/v2/entity`` (ERD-01 to ERD-10)."""

from collections.abc import Mapping
from typing import Annotated, Any

from aurelius_atlas_core.entity_retriever import EntityRetriever
from aurelius_atlas_core.entity_store import EntityStore
from aurelius_atlas_model.typedef import TypeCategory
from aurelius_atlas_typesystem.entity_type import EntityType
from fastapi import APIRouter, Depends, Request

from aurelius_atlas_server.errors import AtlasError, AtlasErrorCode, AtlasJSONResponse
from aurelius_atlas_server.routes.types import validate_param_length

ENTITY = APIRouter(prefix="/api/atlas/v2/entity", tags=["Entity"])

PREFIX_ATTR = "attr:"
"""The query parameters of a unique attribute: ``attr:qualifiedName=x``."""

PREFIX_ATTR_ = "attr_"
"""The query parameters of a set of unique attributes: ``attr_1:qualifiedName=x``."""


async def entity_store(request: Request) -> EntityStore:
    """The server's entity store, its registry refreshed when due (ERD-10, TDS-13)."""
    await request.app.state.typedef_store.refresh()
    store: EntityStore = request.app.state.entity_store
    return store


type Store = Annotated[EntityStore, Depends(entity_store)]


def flag(request: Request, name: str) -> bool:
    """A boolean query parameter as JAX-RS reads one: its first value, true only for ``true`` in any case."""
    values = request.query_params.getlist(name)
    return bool(values) and values[0].lower() == "true"


def retriever(request: Request, store: EntityStore) -> EntityRetriever:
    """A retriever with the request's ``minExtInfo`` and ``ignoreRelationships``."""
    return EntityRetriever(
        store, min_ext_info=flag(request, "minExtInfo"), ignore_relationships=flag(request, "ignoreRelationships")
    )


def unique_attributes(request: Request) -> dict[str, Any]:
    """``getAttributes``: each ``attr:<name>`` parameter with its first value (ERD-08)."""
    found: dict[str, Any] = {}
    for key, value in request.query_params.multi_items():
        if key.startswith(PREFIX_ATTR):
            found.setdefault(key.removeprefix(PREFIX_ATTR), value)
    return found


def unique_attribute_sets(request: Request) -> list[dict[str, Any]]:
    """``getAttributesList``: one set per index of ``attr_<n>:<name>``, in the order indices appear (ERD-08, DV-19)."""
    sets: dict[str, dict[str, Any]] = {}
    seen: set[str] = set()
    for key, value in request.query_params.multi_items():
        if not key.startswith(PREFIX_ATTR_) or key in seen:
            continue
        seen.add(key)
        index, separator, name = key.removeprefix(PREFIX_ATTR_).partition(":")
        if separator:
            sets.setdefault(index, {})[name] = value
    return list(sets.values())


def ensure_entity_type(store: EntityStore, type_name: str) -> EntityType:
    """``ensureEntityType``: the entity type named ``type_name`` (ERD-08).

    Raises:
        AtlasError: ``TYPE_NAME_INVALID`` when there is no such entity type.
    """
    entity_type = store.registry.entity_type(type_name)
    if entity_type is None:
        raise AtlasError(AtlasErrorCode.TYPE_NAME_INVALID, TypeCategory.ENTITY.value, type_name)
    return entity_type


def validate_unique_attributes(entity_type: EntityType, attributes: Mapping[str, Any]) -> None:
    """``validateUniqueAttribute``: at least one attribute, each a unique one of the type (ERD-08).

    Raises:
        AtlasError: ``ATTRIBUTE_UNIQUE_INVALID`` naming the type and the attribute, or ``""`` for none.
    """
    if not attributes:
        raise AtlasError(AtlasErrorCode.ATTRIBUTE_UNIQUE_INVALID, entity_type.type_name, "")
    for name in attributes:
        attribute = entity_type.attribute(name)
        if attribute is None or not attribute.attribute_def.is_unique:
            raise AtlasError(AtlasErrorCode.ATTRIBUTE_UNIQUE_INVALID, entity_type.type_name, name)


def _json(content: Any) -> AtlasJSONResponse:  # noqa: ANN401 - Atlas JSON
    return AtlasJSONResponse(content=content)


@ENTITY.get("/guid/{guid}")
async def get_by_id(guid: str, request: Request, store: Store) -> AtlasJSONResponse:
    """``getById``: the entity and the entities it owns (ERD-02)."""
    validate_param_length("guid", guid)
    return _json((await retriever(request, store).entity_with_ext_info(guid)).to_json())


@ENTITY.get("/guid/{guid}/header")
async def get_header_by_id(guid: str, store: Store) -> AtlasJSONResponse:
    """``getHeaderById``: the entity's header with its classifications (ERD-07)."""
    validate_param_length("guid", guid)
    return _json((await EntityRetriever(store).header(guid)).to_json())


@ENTITY.get("/uniqueAttribute/type/{type_name}")
async def get_by_unique_attributes(type_name: str, request: Request, store: Store) -> AtlasJSONResponse:
    """``getByUniqueAttributes``: the entity holding the ``attr:`` values (ERD-08, ERD-09)."""
    validate_param_length("typeName", type_name)
    attributes = unique_attributes(request)
    entity_type = ensure_entity_type(store, type_name)
    validate_unique_attributes(entity_type, attributes)
    return _json((await retriever(request, store).entity_by_unique_attributes(entity_type, attributes)).to_json())


@ENTITY.get("/uniqueAttribute/type/{type_name}/header")
async def get_entity_header_by_unique_attributes(type_name: str, request: Request, store: Store) -> AtlasJSONResponse:
    """``getEntityHeaderByUniqueAttributes``: the header of the entity holding the ``attr:`` values (ERD-07)."""
    validate_param_length("typeName", type_name)
    attributes = unique_attributes(request)
    entity_type = ensure_entity_type(store, type_name)
    validate_unique_attributes(entity_type, attributes)
    return _json((await EntityRetriever(store).header_by_unique_attributes(entity_type, attributes)).to_json())


@ENTITY.get("/bulk/uniqueAttribute/type/{type_name}")
async def get_entities_by_unique_attributes(type_name: str, request: Request, store: Store) -> AtlasJSONResponse:
    """``getEntitiesByUniqueAttributes``: the entity each ``attr_<n>:`` set finds (ERD-08, ERD-09)."""
    validate_param_length("typeName", type_name)
    sets = unique_attribute_sets(request)
    entity_type = ensure_entity_type(store, type_name)
    for attributes in sets:
        validate_unique_attributes(entity_type, attributes)
    return _json((await retriever(request, store).entities_by_unique_attributes(entity_type, sets)).to_json())


@ENTITY.get("/bulk")
async def get_by_guids(request: Request, store: Store) -> AtlasJSONResponse:
    """``getByGuids``: the entities of every ``guid``, in order (ERD-01, ERD-02).

    Raises:
        AtlasError: ``INSTANCE_GUID_NOT_FOUND`` naming ``[]`` when no ``guid`` is given.
    """
    guids = request.query_params.getlist("guid")
    for guid in guids:
        validate_param_length("guid", guid)
    if not guids:
        raise AtlasError(AtlasErrorCode.INSTANCE_GUID_NOT_FOUND, guids)
    return _json((await retriever(request, store).entities_with_ext_info(guids)).to_json())
