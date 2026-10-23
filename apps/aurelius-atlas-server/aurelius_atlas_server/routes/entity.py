"""The entity reads, writes and deletes of ``EntityREST`` under ``/api/atlas/v2/entity``, and their classifications.

ERD-01 to ERD-10, EWR-01 to EWR-16, EDL-01 to EDL-08, CLS-03 to CLS-09.
"""

from collections.abc import Mapping
from typing import Annotated, Any

from aurelius_atlas_core.delete_type import DeleteType
from aurelius_atlas_core.entity_classifications import EntityClassifications
from aurelius_atlas_core.entity_retriever import EntityRetriever
from aurelius_atlas_core.entity_store import EntityStore
from aurelius_atlas_core.entity_writer import EntityWriter
from aurelius_atlas_model import codec
from aurelius_atlas_model.base import AtlasModel
from aurelius_atlas_model.errors import java_string
from aurelius_atlas_model.instance import (
    AtlasClassification,
    AtlasClassifications,
    AtlasEntitiesWithExtInfo,
    AtlasEntityWithExtInfo,
    ClassificationAssociateRequest,
)
from aurelius_atlas_model.typedef import TypeCategory
from aurelius_atlas_typesystem.entity_type import EntityType
from fastapi import APIRouter, Depends, Request, Response
from pydantic import TypeAdapter, ValidationError

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


def writer(request: Request, store: EntityStore) -> EntityWriter:
    """A writer deleting as the server's ``delete_type`` setting says unless a request chooses (EDL-04)."""
    settings = request.app.state.settings
    return EntityWriter(store, delete_type=DeleteType.of(settings.delete_type))


def delete_type(request: Request) -> DeleteType:
    """The request's ``deleteType`` when the override is enabled, else ``DEFAULT`` (EDL-04, DD-059)."""
    if not request.app.state.settings.delete_type_override:
        return DeleteType.DEFAULT
    return DeleteType.of(request.query_params.get("deleteType"))


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


async def json_body(request: Request) -> Any:  # noqa: ANN401 - any JSON value
    """The request body read by Atlas's JSON codec (DD-039); None when it is empty, as Jersey gives null.

    Raises:
        AtlasError: ``BAD_REQUEST`` for a body that is not JSON (DV-10).
    """
    body = await request.body()
    if not body.strip():
        return None
    try:
        return codec.loads(body)
    except ValueError as error:
        raise AtlasError(AtlasErrorCode.BAD_REQUEST, f"Invalid JSON: {error}") from error


def model_body[T: AtlasModel](model: type[T], body: Any) -> T | None:  # noqa: ANN401 - any JSON value
    """``body`` as ``model``, or None for no body; unknown fields are ignored.

    Raises:
        AtlasError: ``BAD_REQUEST`` for a body that is not a ``model`` (DV-10).
    """
    if body is None:
        return None
    try:
        return model.model_validate(body)
    except ValidationError as error:
        problem = error.errors(include_url=False)[0]
        location = ".".join(str(part) for part in problem["loc"])
        message = f"Invalid {model.__name__}: {problem['msg']}" + (f" at {location}" if location else "")
        raise AtlasError(AtlasErrorCode.BAD_REQUEST, message) from error


type Body = Annotated[Any, Depends(json_body)]

_CLASSIFICATIONS = TypeAdapter(list[AtlasClassification])
NO_CONTENT = 204
NO_CLASSIFICATION = "no classification"
NO_TARGETS = "Need either list of GUIDs or entity type and list of qualified Names"
NO_GUID_FOUND = "No guid found for given entity Type Name and list of attributes"


def classifications_body(body: Any) -> list[AtlasClassification] | None:  # noqa: ANN401 - any JSON value
    """A body that is a list of classifications, or None for no body (CLS-04).

    Raises:
        AtlasError: ``BAD_REQUEST`` for a body that is no such list (DV-10).
    """
    if body is None:
        return None
    try:
        return _CLASSIFICATIONS.validate_python(body)
    except ValidationError as error:
        raise AtlasError(
            AtlasErrorCode.BAD_REQUEST, f"Invalid list of AtlasClassification: {error.errors()[0]['msg']}"
        ) from error


def ensure_classification_type(store: EntityStore, name: str) -> None:
    """``ensureClassificationType``: a classification type is named ``name`` (CLS-03, CLS-09).

    Raises:
        AtlasError: ``TYPE_NAME_INVALID`` (``CLASSIFICATION``) when there is none.
    """
    if store.registry.classification_type(name) is None:
        raise AtlasError(AtlasErrorCode.TYPE_NAME_INVALID, TypeCategory.CLASSIFICATION.value, name)


async def guid_by_unique_attributes(store: EntityStore, type_name: str, request: Request) -> str:
    """``getGuidByUniqueAttributes`` of the ``attr:`` values (CLS-06).

    Raises:
        AtlasError: ``TYPE_NAME_INVALID``, ``INSTANCE_BY_UNIQUE_ATTRIBUTE_NOT_FOUND``.
    """
    validate_param_length("typeName", type_name)
    entity_type = ensure_entity_type(store, type_name)
    attributes = unique_attributes(request)
    found = await store.find_by_unique_attributes(entity_type, attributes)
    if found is None:
        raise AtlasError(AtlasErrorCode.INSTANCE_BY_UNIQUE_ATTRIBUTE_NOT_FOUND, type_name, java_string(attributes))
    return found.entity.guid


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


@ENTITY.post("")
async def create_or_update(body: Body, store: Store) -> AtlasJSONResponse:
    """``createOrUpdate``: create the entity, and the entities it names, or update them (EWR-02)."""
    entity = model_body(AtlasEntityWithExtInfo, body) or AtlasEntityWithExtInfo()
    return _json((await EntityWriter(store).create_or_update(entity)).to_json())


@ENTITY.post("/bulk")
async def create_or_update_bulk(body: Body, store: Store) -> AtlasJSONResponse:
    """``createOrUpdate`` of a bulk request: create or update every entity (EWR-02)."""
    entities = model_body(AtlasEntitiesWithExtInfo, body)
    return _json((await EntityWriter(store).create_or_update(entities)).to_json())


@ENTITY.put("/uniqueAttribute/type/{type_name}")
async def partial_update_entity_by_unique_attrs(
    type_name: str, request: Request, body: Body, store: Store
) -> AtlasJSONResponse:
    """``partialUpdateEntityByUniqueAttrs``: partially update the entity holding the ``attr:`` values (EWR-14)."""
    validate_param_length("typeName", type_name)
    attributes = unique_attributes(request)
    entity_type = ensure_entity_type(store, type_name)
    validate_unique_attributes(entity_type, attributes)
    entity = model_body(AtlasEntityWithExtInfo, body)
    return _json((await EntityWriter(store).update_by_unique_attributes(entity_type, attributes, entity)).to_json())


@ENTITY.put("/guid/{guid}")
async def partial_update_entity_attr_by_guid(
    guid: str, request: Request, body: Body, store: Store
) -> AtlasJSONResponse:
    """``partialUpdateEntityAttrByGuid``: set the attribute ``name`` of the entity to the body (EWR-15)."""
    validate_param_length("guid", guid)
    name = request.query_params.get("name")
    if name is not None:
        validate_param_length("name", name)
    return _json((await EntityWriter(store).update_attribute_by_guid(guid, name, body)).to_json())


@ENTITY.delete("/guid/{guid}")
async def delete_by_guid(guid: str, request: Request, store: Store) -> AtlasJSONResponse:
    """``deleteByGuid``: the entity and what it owns (EDL-01, EDL-03)."""
    validate_param_length("guid", guid)
    return _json((await writer(request, store).delete_by_id(guid, delete_type(request))).to_json())


@ENTITY.delete("/bulk")
async def delete_by_guids(request: Request, store: Store) -> AtlasJSONResponse:
    """``deleteByGuids``: the entities of every ``guid`` and what they own (EDL-01, EDL-02)."""
    guids = request.query_params.getlist("guid")
    for guid in guids:
        validate_param_length("guid", guid)
    return _json((await writer(request, store).delete_by_ids(guids, delete_type(request))).to_json())


@ENTITY.delete("/uniqueAttribute/type/{type_name}")
async def delete_by_unique_attribute(type_name: str, request: Request, store: Store) -> AtlasJSONResponse:
    """``deleteByUniqueAttribute``: the entity holding the ``attr:`` values; they are not checked (EDL-02)."""
    validate_param_length("typeName", type_name)
    attributes = unique_attributes(request)
    entity_type = ensure_entity_type(store, type_name)
    deleted = await writer(request, store).delete_by_unique_attributes(entity_type, attributes, delete_type(request))
    return _json(deleted.to_json())


@ENTITY.get("/guid/{guid}/classification/{classification_name}")
async def get_classification(guid: str, classification_name: str, store: Store) -> AtlasJSONResponse:
    """``getClassification``: the entity's classification of the name (CLS-03)."""
    validate_param_length("guid", guid)
    validate_param_length("classificationName", classification_name)
    ensure_classification_type(store, classification_name)
    return _json((await EntityClassifications(store).get_classification(guid, classification_name)).to_json())


@ENTITY.get("/guid/{guid}/classifications")
async def get_classifications(guid: str, store: Store) -> AtlasJSONResponse:
    """``getClassifications``: the entity's classifications as a ``PList`` (CLS-03)."""
    validate_param_length("guid", guid)
    found = await EntityClassifications(store).get_classifications(guid)
    return _json(AtlasClassifications.of(found).to_json())


@ENTITY.post("/uniqueAttribute/type/{type_name}/classifications")
async def add_classifications_by_unique_attribute(
    type_name: str, request: Request, body: Body, store: Store
) -> Response:
    """``addClassificationsByUniqueAttribute`` (CLS-04 to CLS-06)."""
    guid = await guid_by_unique_attributes(store, type_name, request)
    await EntityClassifications(store).add_classifications(guid, classifications_body(body))
    return Response(status_code=NO_CONTENT)


@ENTITY.post("/guid/{guid}/classifications")
async def add_classifications(guid: str, body: Body, store: Store) -> Response:
    """``addClassifications``: attach the classifications to the entity (CLS-04, CLS-05)."""
    validate_param_length("guid", guid)
    await EntityClassifications(store).add_classifications(guid, classifications_body(body))
    return Response(status_code=NO_CONTENT)


@ENTITY.put("/uniqueAttribute/type/{type_name}/classifications")
async def update_classifications_by_unique_attribute(
    type_name: str, request: Request, body: Body, store: Store
) -> Response:
    """``updateClassificationsByUniqueAttribute`` (CLS-06, CLS-08)."""
    guid = await guid_by_unique_attributes(store, type_name, request)
    await EntityClassifications(store).update_classifications(guid, classifications_body(body))
    return Response(status_code=NO_CONTENT)


@ENTITY.put("/guid/{guid}/classifications")
async def update_classifications(guid: str, body: Body, store: Store) -> Response:
    """``updateClassifications``: change the entity's classifications (CLS-08)."""
    validate_param_length("guid", guid)
    await EntityClassifications(store).update_classifications(guid, classifications_body(body))
    return Response(status_code=NO_CONTENT)


@ENTITY.delete("/uniqueAttribute/type/{type_name}/classification/{classification_name}")
async def delete_classification_by_unique_attribute(
    type_name: str, classification_name: str, request: Request, store: Store
) -> Response:
    """``deleteClassificationByUniqueAttribute`` (CLS-06, CLS-09)."""
    validate_param_length("classificationName", classification_name)
    guid = await guid_by_unique_attributes(store, type_name, request)
    await EntityClassifications(store).delete_classification(guid, classification_name)
    return Response(status_code=NO_CONTENT)


@ENTITY.delete("/guid/{guid}/classification/{classification_name}")
async def delete_classification(guid: str, classification_name: str, request: Request, store: Store) -> Response:
    """``deleteClassification``: remove the entity's classification of the name (CLS-09)."""
    associated = request.query_params.get("associatedEntityGuid")
    validate_param_length("guid", guid)
    validate_param_length("classificationName", classification_name)
    if associated is not None:
        validate_param_length("associatedEntityGuid", associated)
    ensure_classification_type(store, classification_name)
    await EntityClassifications(store).delete_classification(guid, classification_name, associated)
    return Response(status_code=NO_CONTENT)


@ENTITY.post("/bulk/classification")
async def add_classification(body: Body, store: Store) -> Response:
    """``addClassification``: attach one classification to entities by GUID or by unique attributes (CLS-07).

    Raises:
        AtlasError: ``INVALID_PARAMETERS`` without a classification or entities, or when no entity is found.
    """
    associate = model_body(ClassificationAssociateRequest, body) or ClassificationAssociateRequest()
    classification = associate.classification
    if classification is None or not classification.type_name:
        raise AtlasError(AtlasErrorCode.INVALID_PARAMETERS, NO_CLASSIFICATION)
    guids = list(associate.entity_guids or [])
    sets = associate.entities_unique_attributes or []
    if not guids and (not sets or associate.entity_type_name is None):
        raise AtlasError(AtlasErrorCode.INVALID_PARAMETERS, NO_TARGETS)
    if sets and associate.entity_type_name is not None:
        entity_type = ensure_entity_type(store, associate.entity_type_name)
        for attributes in sets:
            found = await store.find_by_unique_attributes(entity_type, attributes)
            if found is not None:
                guids.append(found.entity.guid)
        if not guids:
            raise AtlasError(AtlasErrorCode.INVALID_PARAMETERS, NO_GUID_FOUND)
    await EntityClassifications(store).add_classification(guids, classification)
    return Response(status_code=NO_CONTENT)
