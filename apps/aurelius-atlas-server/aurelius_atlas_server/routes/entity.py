"""The endpoints of ``EntityREST`` under ``/api/atlas/v2/entity``: reads, writes, deletes, classifications, audit.

ERD-01 to ERD-10, EWR-01 to EWR-16, EDL-01 to EDL-08, CLS-03 to CLS-09, CLA-01 to CLA-04, AUD-06 to AUD-09, CAU-07;
each checked as Atlas's entity store checks it (AUZ-07, AUZ-08, AUZ-11).
"""

from collections.abc import Mapping
from typing import Annotated, Any

from aurelius_atlas_core.classification_associator import ClassificationRetriever
from aurelius_atlas_core.entity_audit_repository import EntityAuditRepository, list_events_sorted
from aurelius_atlas_core.entity_business_metadata import business_metadata_headers
from aurelius_atlas_core.entity_retriever import EntityRetriever
from aurelius_atlas_model.audit import EntityAuditActionV2, EntityAuditEventV2
from aurelius_atlas_model.bulk_import import BulkImportResponse
from aurelius_atlas_model.errors import validate_guid, validate_param_length
from aurelius_atlas_model.instance import (
    AtlasClassification,
    AtlasClassifications,
    AtlasEntitiesWithExtInfo,
    AtlasEntityHeader,
    AtlasEntityHeaders,
    AtlasEntityWithExtInfo,
    ClassificationAssociateRequest,
    EntityMutationResponse,
)
from aurelius_atlas_model.lists import ClassificationsList, Labels
from aurelius_atlas_model.maps import AttributeValues, BusinessAttributesMap, JsonValue
from aurelius_atlas_model.params import (
    ClassificationDeleteParams,
    EntityAuditParams,
    EntityGuidParams,
    EntityHeadersParams,
    PartialAttributeParams,
)
from fastapi import APIRouter, Depends, Request, Response
from starlette.datastructures import UploadFile

from aurelius_atlas_server.authorization import AtlasPrivilege, verify_access
from aurelius_atlas_server.bodies import Body, json_model, json_root, model_body
from aurelius_atlas_server.deps import Authorizer, Settings, StoreSet
from aurelius_atlas_server.errors import AtlasError, AtlasErrorCode, AtlasJSONResponse
from aurelius_atlas_server.openapi import (
    array_of,
    download_response,
    form_request,
    json_response,
    request_body,
)
from aurelius_atlas_server.openapi import no_content as no_content_response
from aurelius_atlas_server.services import (
    READ_ENTITY_GUID,
    Associator,
    BusinessMetadataService,
    Classifications,
    LabelsService,
    Store,
    Updater,
    Writer,
    delete_type,
    ensure_classification_type,
    ensure_entity_type,
    flag,
    guid_by_unique_attributes,
    read_query,
    retriever,
    unique_attribute_sets,
    unique_attributes,
    validate_unique_attributes,
)
from aurelius_atlas_server.uploads import read_upload

ENTITY = APIRouter(prefix="/api/atlas/v2/entity", tags=["Entity"])


def _json(content: Any) -> AtlasJSONResponse:  # noqa: ANN401 - Atlas JSON
    return AtlasJSONResponse(content=content)


NO_CONTENT = 204
NO_CLASSIFICATION = "no classification"
NO_TARGETS = "Need either list of GUIDs or entity type and list of qualified Names"
NO_GUID_FOUND = "No guid found for given entity Type Name and list of attributes"

CLASSIFICATIONS_BODY = json_root(ClassificationsList)
"""``addClassifications``/``updateClassifications``: a list of classifications, each validated (CLS-04)."""

LABELS_BODY = json_root(Labels)
"""``setLabels``/``addLabels``/``removeLabels``: a JSON array of labels (LBL-01)."""

ATTRIBUTE_VALUES_BODY = json_root(AttributeValues)
"""One business metadata's attribute values: a JSON object of them (BMD-01, BMD-03)."""

BUSINESS_ATTRIBUTES_BODY = json_root(BusinessAttributesMap)
"""Business attribute values by business metadata name (BMD-01, BMD-05)."""

ENTITY_BODY = json_model(AtlasEntityWithExtInfo)
"""``createOrUpdate``/``partialUpdateEntityByUniqueAttrs``: one entity with the entities it names (EWR-02)."""

ENTITIES_BODY = json_model(AtlasEntitiesWithExtInfo)
"""``createOrUpdate`` of a bulk request: every entity to create or update (EWR-02)."""

ENTITY_HEADERS_BODY = json_model(AtlasEntityHeaders)
"""``setClassifications``: the classifications to set on each named entity (CLA-04)."""

ASSOCIATE_BODY = json_model(ClassificationAssociateRequest)
"""``addClassification``: one classification and the entities named for it (CLS-07)."""

ATTRIBUTE_VALUE_BODY = json_root(JsonValue)
"""``partialUpdateEntityAttrByGuid``: the attribute's new value, of any JSON kind (EWR-15)."""

type ClassificationsBody = Annotated[list[AtlasClassification] | None, Depends(CLASSIFICATIONS_BODY)]
type LabelsBody = Annotated[list[str] | None, Depends(LABELS_BODY)]
type AttributeValuesBody = Annotated[dict[str, Any] | None, Depends(ATTRIBUTE_VALUES_BODY)]
type BusinessAttributesBody = Annotated[dict[str, dict[str, Any] | None] | None, Depends(BUSINESS_ATTRIBUTES_BODY)]
type EntityBody = Annotated[AtlasEntityWithExtInfo | None, Depends(ENTITY_BODY)]
type EntitiesBody = Annotated[AtlasEntitiesWithExtInfo | None, Depends(ENTITIES_BODY)]
type EntityHeadersBody = Annotated[AtlasEntityHeaders | None, Depends(ENTITY_HEADERS_BODY)]
type AssociateBody = Annotated[ClassificationAssociateRequest | None, Depends(ASSOCIATE_BODY)]
type AttributeValueBody = Annotated[Any, Depends(ATTRIBUTE_VALUE_BODY)]


def _verify_read_by_unique_attributes(authorized: Authorizer, type_name: str, attributes: Mapping[str, Any]) -> None:
    """``read entity: typeName=<type>, uniqueAttributes={...}`` needs ``ENTITY_READ`` (AUZ-11)."""
    action = ("read entity: typeName=", type_name, ", uniqueAttributes=", dict(attributes))
    verify_access(authorized, AtlasPrivilege.ENTITY_READ, *action)


@ENTITY.get(
    "/guid/{guid}",
    responses=json_response(AtlasEntityWithExtInfo, description="The entity and the entities it owns (ERD-02)."),
)
async def get_by_id(guid: str, request: Request, store: Store, authorized: Authorizer) -> AtlasJSONResponse:
    """``getById``: the entity and the entities it owns (ERD-02, AUZ-11)."""
    validate_guid("guid", guid)
    found = await retriever(request, store).entity_with_ext_info(guid)
    verify_access(authorized, AtlasPrivilege.ENTITY_READ, READ_ENTITY_GUID, guid)
    return _json(found.to_json())


@ENTITY.get(
    "/guid/{guid}/header",
    responses=json_response(AtlasEntityHeader, description="The entity's header with its classifications (ERD-07)."),
)
async def get_header_by_id(guid: str, store: Store, authorized: Authorizer) -> AtlasJSONResponse:
    """``getHeaderById``: the entity's header with its classifications (ERD-07, AUZ-11)."""
    validate_guid("guid", guid)
    found = await EntityRetriever(store).header(guid)
    verify_access(authorized, AtlasPrivilege.ENTITY_READ, READ_ENTITY_GUID, guid)
    return _json(found.to_json())


@ENTITY.get(
    "/uniqueAttribute/type/{type_name}",
    responses=json_response(AtlasEntityWithExtInfo, description="The entity holding the attr: values (ERD-08)."),
)
async def get_by_unique_attributes(
    type_name: str, request: Request, store: Store, authorized: Authorizer
) -> AtlasJSONResponse:
    """``getByUniqueAttributes``: the entity holding the ``attr:`` values (ERD-08, ERD-09, AUZ-11)."""
    validate_param_length("typeName", type_name)
    attributes = unique_attributes(request)
    entity_type = ensure_entity_type(store, type_name)
    validate_unique_attributes(entity_type, attributes)
    found = await retriever(request, store).entity_by_unique_attributes(entity_type, attributes)
    _verify_read_by_unique_attributes(authorized, type_name, attributes)
    return _json(found.to_json())


@ENTITY.get(
    "/uniqueAttribute/type/{type_name}/header",
    responses=json_response(
        AtlasEntityHeader, description="The header of the entity holding the attr: values (ERD-07)."
    ),
)
async def get_entity_header_by_unique_attributes(
    type_name: str, request: Request, store: Store, authorized: Authorizer
) -> AtlasJSONResponse:
    """``getEntityHeaderByUniqueAttributes``: the header of the entity holding the ``attr:`` values (ERD-07, AUZ-11)."""
    validate_param_length("typeName", type_name)
    attributes = unique_attributes(request)
    entity_type = ensure_entity_type(store, type_name)
    validate_unique_attributes(entity_type, attributes)
    found = await EntityRetriever(store).header_by_unique_attributes(entity_type, attributes)
    _verify_read_by_unique_attributes(authorized, type_name, attributes)
    return _json(found.to_json())


@ENTITY.get(
    "/bulk/uniqueAttribute/type/{type_name}",
    responses=json_response(AtlasEntitiesWithExtInfo, description="The entity each attr_<n>: set finds (ERD-08)."),
)
async def get_entities_by_unique_attributes(
    type_name: str, request: Request, store: Store, authorized: Authorizer
) -> AtlasJSONResponse:
    """``getEntitiesByUniqueAttributes``: the entity each ``attr_<n>:`` set finds (ERD-08, ERD-09)."""
    validate_param_length("typeName", type_name)
    sets = unique_attribute_sets(request)
    entity_type = ensure_entity_type(store, type_name)
    for attributes in sets:
        validate_unique_attributes(entity_type, attributes)
    found = await retriever(request, store).entities_by_unique_attributes(entity_type, sets)
    for entity in found.entities or []:
        verify_access(
            authorized, AtlasPrivilege.ENTITY_READ, "read entity: typeName=", type_name, ", guid=", entity.guid
        )
    return _json(found.to_json())


@ENTITY.get(
    "/bulk",
    responses=json_response(
        AtlasEntitiesWithExtInfo, description="The entities of every guid query parameter, in order (ERD-01)."
    ),
)
async def get_by_guids(request: Request, store: Store, authorized: Authorizer) -> AtlasJSONResponse:
    """``getByGuids``: the entities of every ``guid``, in order (ERD-01, ERD-02).

    Raises:
        AtlasError: ``INSTANCE_GUID_NOT_FOUND`` naming ``[]`` when no ``guid`` is given.
    """
    guids = read_query(EntityGuidParams, request).checked()
    if not guids:
        raise AtlasError(AtlasErrorCode.INSTANCE_GUID_NOT_FOUND, guids)
    found = await retriever(request, store).entities_with_ext_info(guids)
    for guid in guids:
        verify_access(authorized, AtlasPrivilege.ENTITY_READ, READ_ENTITY_GUID, guid)
    return _json(found.to_json())


@ENTITY.post(
    "",
    responses=json_response(EntityMutationResponse, description="The created and updated entities (EWR-02)."),
    **request_body(AtlasEntityWithExtInfo, description="The entity to create or update, with the entities it names."),
)
async def create_or_update(entity_body: EntityBody, updater: Updater) -> AtlasJSONResponse:
    """``createOrUpdate``: create the entity, and the entities it names, or update them (EWR-02)."""
    entity = entity_body or AtlasEntityWithExtInfo()
    return _json((await updater.create_or_update(entity)).to_json())


@ENTITY.post(
    "/bulk",
    responses=json_response(EntityMutationResponse, description="The created and updated entities (EWR-02)."),
    **request_body(AtlasEntitiesWithExtInfo, description="The entities to create or update."),
)
async def create_or_update_bulk(entities_body: EntitiesBody, updater: Updater) -> AtlasJSONResponse:
    """``createOrUpdate`` of a bulk request: create or update every entity (EWR-02)."""
    return _json((await updater.create_or_update(entities_body)).to_json())


@ENTITY.put(
    "/uniqueAttribute/type/{type_name}",
    responses=json_response(EntityMutationResponse, description="The updated entity (EWR-14)."),
    **request_body(AtlasEntityWithExtInfo, description="The attribute values to set, with the entity's typeName."),
)
async def partial_update_entity_by_unique_attrs(
    type_name: str, request: Request, body: Body, store: Store, updater: Updater
) -> AtlasJSONResponse:
    """``partialUpdateEntityByUniqueAttrs``: partially update the entity holding the ``attr:`` values (EWR-14)."""
    validate_param_length("typeName", type_name)
    # the body is validated only now: Java answers a long typeName before touching an invalid body (EWR-14)
    entity_body = model_body(AtlasEntityWithExtInfo, body)
    attributes = unique_attributes(request)
    entity_type = ensure_entity_type(store, type_name)
    validate_unique_attributes(entity_type, attributes)
    updated = await updater.update_by_unique_attributes(entity_type, attributes, entity_body)
    return _json(updated.to_json())


@ENTITY.put(
    "/guid/{guid}",
    responses=json_response(EntityMutationResponse, description="The updated entity (EWR-15)."),
    **request_body(JsonValue, description="The attribute's new value: any JSON value."),
)
async def partial_update_entity_attr_by_guid(
    guid: str, request: Request, value: AttributeValueBody, updater: Updater
) -> AtlasJSONResponse:
    """``partialUpdateEntityAttrByGuid``: set the attribute ``name`` of the entity to the body (EWR-15)."""
    validate_guid("guid", guid)
    name = read_query(PartialAttributeParams, request).checked()
    return _json((await updater.update_attribute_by_guid(guid, name, value)).to_json())


@ENTITY.delete(
    "/guid/{guid}",
    responses=json_response(EntityMutationResponse, description="The deleted entity (EDL-01)."),
)
async def delete_by_guid(guid: str, request: Request, writer: Writer, settings: Settings) -> AtlasJSONResponse:
    """``deleteByGuid``: the entity and what it owns (EDL-01, EDL-03)."""
    validate_guid("guid", guid)
    return _json((await writer.delete_by_id(guid, delete_type(request, settings))).to_json())


@ENTITY.delete(
    "/bulk",
    responses=json_response(EntityMutationResponse, description="The deleted entities (EDL-02)."),
)
async def delete_by_guids(request: Request, writer: Writer, settings: Settings) -> AtlasJSONResponse:
    """``deleteByGuids``: the entities of every ``guid`` and what they own (EDL-01, EDL-02)."""
    guids = read_query(EntityGuidParams, request).checked()
    return _json((await writer.delete_by_ids(guids, delete_type(request, settings))).to_json())


@ENTITY.delete(
    "/uniqueAttribute/type/{type_name}",
    responses=json_response(EntityMutationResponse, description="The deleted entity (EDL-02)."),
)
async def delete_by_unique_attribute(
    type_name: str, request: Request, store: Store, writer: Writer, settings: Settings
) -> AtlasJSONResponse:
    """``deleteByUniqueAttribute``: the entity holding the ``attr:`` values; they are not checked (EDL-02)."""
    validate_param_length("typeName", type_name)
    attributes = unique_attributes(request)
    entity_type = ensure_entity_type(store, type_name)
    deleted = await writer.delete_by_unique_attributes(entity_type, attributes, delete_type(request, settings))
    return _json(deleted.to_json())


@ENTITY.get(
    "/guid/{guid}/classification/{classification_name}",
    responses=json_response(AtlasClassification, description="The entity's classification of the name (CLS-03)."),
)
async def get_classification(
    guid: str, classification_name: str, store: Store, classifications: Classifications
) -> AtlasJSONResponse:
    """``getClassification``: the entity's classification of the name (CLS-03)."""
    validate_guid("guid", guid)
    validate_param_length("classificationName", classification_name)
    ensure_classification_type(store, classification_name)
    found = await classifications.get_classification(guid, classification_name)
    return _json(found.to_json())


@ENTITY.get(
    "/guid/{guid}/classifications",
    responses=json_response(AtlasClassifications, description="The entity's classifications as a PList (CLS-03)."),
)
async def get_classifications(guid: str, classifications: Classifications) -> AtlasJSONResponse:
    """``getClassifications``: the entity's classifications as a ``PList`` (CLS-03, AUZ-08)."""
    validate_guid("guid", guid)
    found = await classifications.get_classifications(guid)
    return _json(AtlasClassifications.of(found).to_json())


@ENTITY.post(
    "/uniqueAttribute/type/{type_name}/classifications",
    responses=no_content_response("The classifications are attached (CLS-04)."),
    **request_body(array_of(AtlasClassification), description="The classifications to attach."),
)
async def add_classifications_by_unique_attribute(
    type_name: str,
    request: Request,
    classifications_body: ClassificationsBody,
    store: Store,
    classifications: Classifications,
) -> Response:
    """``addClassificationsByUniqueAttribute`` (CLS-04 to CLS-06)."""
    guid = await guid_by_unique_attributes(store, type_name, request)
    await classifications.add_classifications(guid, classifications_body)
    return Response(status_code=NO_CONTENT)


@ENTITY.post(
    "/guid/{guid}/classifications",
    responses=no_content_response("The classifications are attached (CLS-04)."),
    **request_body(array_of(AtlasClassification), description="The classifications to attach."),
)
async def add_classifications(
    guid: str, classifications_body: ClassificationsBody, classifications: Classifications
) -> Response:
    """``addClassifications``: attach the classifications to the entity (CLS-04, CLS-05)."""
    validate_guid("guid", guid)
    await classifications.add_classifications(guid, classifications_body)
    return Response(status_code=NO_CONTENT)


@ENTITY.put(
    "/uniqueAttribute/type/{type_name}/classifications",
    responses=no_content_response("The entity's classifications become those given (CLS-08)."),
    **request_body(array_of(AtlasClassification), description="The classifications to keep."),
)
async def update_classifications_by_unique_attribute(
    type_name: str,
    request: Request,
    classifications_body: ClassificationsBody,
    store: Store,
    classifications: Classifications,
) -> Response:
    """``updateClassificationsByUniqueAttribute`` (CLS-06, CLS-08)."""
    guid = await guid_by_unique_attributes(store, type_name, request)
    await classifications.update_classifications(guid, classifications_body)
    return Response(status_code=NO_CONTENT)


@ENTITY.put(
    "/guid/{guid}/classifications",
    responses=no_content_response("The entity's classifications become those given (CLS-08)."),
    **request_body(array_of(AtlasClassification), description="The classifications to keep."),
)
async def update_classifications(
    guid: str, classifications_body: ClassificationsBody, classifications: Classifications
) -> Response:
    """``updateClassifications``: change the entity's classifications (CLS-08)."""
    validate_guid("guid", guid)
    await classifications.update_classifications(guid, classifications_body)
    return Response(status_code=NO_CONTENT)


@ENTITY.delete(
    "/uniqueAttribute/type/{type_name}/classification/{classification_name}",
    responses=no_content_response("The classification is removed (CLS-09)."),
)
async def delete_classification_by_unique_attribute(
    type_name: str, classification_name: str, request: Request, store: Store, classifications: Classifications
) -> Response:
    """``deleteClassificationByUniqueAttribute`` (CLS-06, CLS-09)."""
    validate_param_length("classificationName", classification_name)
    guid = await guid_by_unique_attributes(store, type_name, request)
    await classifications.delete_classification(guid, classification_name)
    return Response(status_code=NO_CONTENT)


@ENTITY.delete(
    "/guid/{guid}/classification/{classification_name}",
    responses=no_content_response("The classification is removed (CLS-09)."),
)
async def delete_classification(
    guid: str, classification_name: str, request: Request, store: Store, classifications: Classifications
) -> Response:
    """``deleteClassification``: remove the entity's classification of the name (CLS-09)."""
    associated = read_query(ClassificationDeleteParams, request).checked()
    validate_guid("guid", guid)
    validate_param_length("classificationName", classification_name)
    ensure_classification_type(store, classification_name)
    await classifications.delete_classification(guid, classification_name, associated)
    return Response(status_code=NO_CONTENT)


@ENTITY.post(
    "/bulk/classification",
    responses=no_content_response("The classification is attached to every entity named (CLS-07)."),
    **request_body(
        ClassificationAssociateRequest,
        description="One classification and the entities to attach it to: by GUIDs, or type name and attributes.",
    ),
)
async def add_classification(associate_body: AssociateBody, store: Store, classifications: Classifications) -> Response:
    """``addClassification``: attach one classification to entities by GUID or by unique attributes (CLS-07).

    Raises:
        AtlasError: ``INVALID_PARAMETERS`` without a classification or entities, or when no entity is found.
    """
    associate = associate_body or ClassificationAssociateRequest()
    classification = associate.classification
    if classification is None or not classification.type_name:
        raise AtlasError(AtlasErrorCode.INVALID_PARAMETERS, NO_CLASSIFICATION)
    guids = list(associate.entity_guids or [])
    if not guids and (not associate.entities_unique_attributes or associate.entity_type_name is None):
        raise AtlasError(AtlasErrorCode.INVALID_PARAMETERS, NO_TARGETS)
    if associate.entities_unique_attributes and associate.entity_type_name is not None:
        guids += await _targets_from_sets(store, associate)
    await classifications.add_classification(guids, classification)
    return Response(status_code=NO_CONTENT)


async def _targets_from_sets(store: Store, associate: ClassificationAssociateRequest) -> list[str]:
    """The GUIDs the request's unique-attribute sets name, refusing when none of them is an entity (CLS-07).

    Raises:
        AtlasError: ``INVALID_PARAMETERS`` when no set names a stored entity.
    """
    entity_type = ensure_entity_type(store, str(associate.entity_type_name))
    guids: list[str] = []
    for attributes in associate.entities_unique_attributes or []:
        found = await store.find_by_unique_attributes(entity_type, attributes)
        if found is not None:
            guids.append(found.entity.guid)
    if not guids:
        raise AtlasError(AtlasErrorCode.INVALID_PARAMETERS, NO_GUID_FOUND)
    return guids


@ENTITY.post(
    "/bulk/setClassifications",
    responses=json_response(
        array_of(str), description="One summary line per step taken: what was added, updated, or skipped (CLA-04)."
    ),
    **request_body(AtlasEntityHeaders, description="The classifications to set on each named entity."),
)
async def set_classifications(headers: EntityHeadersBody, associator: Associator) -> Response:
    """``setClassifications``: each header's entity gets its classifications; a JSON array of summaries (CLA-04).

    The array is Java's text, answered as it is; no body answers ``[]`` (DV-36).
    """
    summary = await associator.set_classifications(None if headers is None else headers.guid_header_map)
    return Response(content=summary, media_type="application/json")


@ENTITY.post(
    "/guid/{guid}/businessmetadata",
    responses=no_content_response("The business attribute values are set (BMD-01)."),
    **request_body(
        BusinessAttributesMap, required=False, description="Business attribute values by business metadata name."
    ),
)
async def add_or_update_business_attributes(
    guid: str, request: Request, given: BusinessAttributesBody, business_metadata: BusinessMetadataService
) -> Response:
    """``addOrUpdateBusinessAttributes``: the body's values set, or with ``isOverwrite`` all replaced (BMD-01)."""
    validate_guid("guid", guid)
    await business_metadata.add_or_update_business_attributes(guid, given, is_overwrite=flag(request, "isOverwrite"))
    return Response(status_code=NO_CONTENT)


@ENTITY.delete(
    "/guid/{guid}/businessmetadata",
    responses=no_content_response("The business attributes are removed (BMD-05)."),
    **request_body(
        BusinessAttributesMap,
        required=False,
        description="The business attributes to remove, by business metadata name; a name alone removes all of them.",
    ),
)
async def remove_business_attributes(
    guid: str, given: BusinessAttributesBody, business_metadata: BusinessMetadataService
) -> Response:
    """``removeBusinessAttributes``: the body's attributes removed (BMD-01, BMD-05)."""
    validate_guid("guid", guid)
    await business_metadata.remove_business_attributes(guid, given)
    return Response(status_code=NO_CONTENT)


@ENTITY.post(
    "/guid/{guid}/businessmetadata/{bm_name}",
    responses=no_content_response("The values of one business metadata are set (BMD-01)."),
    **request_body(
        AttributeValues, required=False, description="Business attribute values of the named business metadata."
    ),
)
async def add_or_update_business_attributes_of(
    guid: str, bm_name: str, values: AttributeValuesBody, business_metadata: BusinessMetadataService
) -> Response:
    """``addOrUpdateBusinessAttributes`` of one business metadata: the body's values set (BMD-01, BMD-03)."""
    validate_guid("guid", guid)
    await business_metadata.add_or_update_business_attributes(guid, {bm_name: values})
    return Response(status_code=NO_CONTENT)


@ENTITY.delete(
    "/guid/{guid}/businessmetadata/{bm_name}",
    responses=no_content_response("The business attributes of one metadata are removed (BMD-05)."),
    **request_body(
        AttributeValues, required=False, description="The business attributes to remove; no body removes them all."
    ),
)
async def remove_business_attributes_of(
    guid: str, bm_name: str, values: AttributeValuesBody, business_metadata: BusinessMetadataService
) -> Response:
    """``removeBusinessAttributes`` of one business metadata: the body's attributes, or all, removed (BMD-05)."""
    validate_guid("guid", guid)
    await business_metadata.remove_business_attributes(guid, {bm_name: values})
    return Response(status_code=NO_CONTENT)


@ENTITY.get(
    "/businessmetadata/import/template",
    responses=download_response(
        "application/octet-stream", description="The import template's header line, as a download (BMI-01)."
    ),
)
async def produce_template() -> Response:
    """``produceTemplate``: the business metadata import template's header line, as a download (BMI-01)."""
    return Response(
        content=business_metadata_headers().encode(),
        media_type="application/octet-stream",
        headers={"Content-Disposition": 'attachment; filename="template_business_metadata"'},
    )


@ENTITY.post(
    "/businessmetadata/import",
    responses=json_response(BulkImportResponse, description="The outcome per line of the file (BMI-02 to BMI-05)."),
    **form_request(fields={"file": "A CSV or Excel file of business attribute values."}),
)
async def import_bm_attributes(
    request: Request, settings: Settings, business_metadata: BusinessMetadataService
) -> AtlasJSONResponse:
    """``importBMAttributes``: the form's ``file``, a CSV or Excel file of business attribute values (BMI-02 to
    BMI-05); no file is a blank file name (DV-119).
    """  # noqa: D205 - one sentence
    upload = (await request.form()).get("file")
    file_name = upload.filename if isinstance(upload, UploadFile) else None
    content = await read_upload(request, settings, "file", "file")
    found = await business_metadata.bulk_create_or_update_business_attributes(file_name, content)
    return _json(found.to_json())


@ENTITY.post(
    "/guid/{guid}/labels",
    responses=no_content_response("The entity's labels become those given (LBL-01)."),
    **request_body(array_of(str), description="The labels to set."),
)
async def set_labels(guid: str, labels_body: LabelsBody, labels: LabelsService) -> Response:
    """``setLabels``: the entity's labels become those of the body (LBL-01, LBL-02)."""
    validate_guid("guid", guid)
    await labels.set_labels(guid, labels_body)
    return Response(status_code=NO_CONTENT)


@ENTITY.put(
    "/guid/{guid}/labels",
    responses=no_content_response("The labels given are added to the entity's (LBL-01)."),
    **request_body(array_of(str), description="The labels to add."),
)
async def add_labels(guid: str, labels_body: LabelsBody, labels: LabelsService) -> Response:
    """``addLabels``: the body's labels added to the entity's (LBL-01, LBL-03)."""
    validate_guid("guid", guid)
    await labels.add_labels(guid, labels_body)
    return Response(status_code=NO_CONTENT)


@ENTITY.delete(
    "/guid/{guid}/labels",
    responses=no_content_response("The labels given are taken from the entity's (LBL-01)."),
    **request_body(array_of(str), description="The labels to remove."),
)
async def remove_labels(guid: str, labels_body: LabelsBody, labels: LabelsService) -> Response:
    """``removeLabels``: the body's labels taken from the entity's (LBL-01, LBL-04)."""
    validate_guid("guid", guid)
    await labels.remove_labels(guid, labels_body)
    return Response(status_code=NO_CONTENT)


@ENTITY.post(
    "/uniqueAttribute/type/{type_name}/labels",
    responses=no_content_response("The entity's labels become those given (LBL-01)."),
    **request_body(array_of(str), description="The labels to set."),
)
async def set_labels_by_unique_attribute(
    type_name: str, request: Request, labels_body: LabelsBody, store: Store, labels: LabelsService
) -> Response:
    """``setLabels`` of the entity holding the ``attr:`` values (LBL-01, LBL-02)."""
    guid = await guid_by_unique_attributes(store, type_name, request)
    await labels.set_labels(guid, labels_body)
    return Response(status_code=NO_CONTENT)


@ENTITY.put(
    "/uniqueAttribute/type/{type_name}/labels",
    responses=no_content_response("The labels given are added to the entity's (LBL-01)."),
    **request_body(array_of(str), description="The labels to add."),
)
async def add_labels_by_unique_attribute(
    type_name: str, request: Request, labels_body: LabelsBody, store: Store, labels: LabelsService
) -> Response:
    """``addLabels`` to the entity holding the ``attr:`` values (LBL-01, LBL-03)."""
    guid = await guid_by_unique_attributes(store, type_name, request)
    await labels.add_labels(guid, labels_body)
    return Response(status_code=NO_CONTENT)


@ENTITY.delete(
    "/uniqueAttribute/type/{type_name}/labels",
    responses=no_content_response("The labels given are taken from the entity's (LBL-01)."),
    **request_body(array_of(str), description="The labels to remove."),
)
async def remove_labels_by_unique_attribute(
    type_name: str, request: Request, labels_body: LabelsBody, store: Store, labels: LabelsService
) -> Response:
    """``removeLabels`` from the entity holding the ``attr:`` values (LBL-01, LBL-04)."""
    guid = await guid_by_unique_attributes(store, type_name, request)
    await labels.remove_labels(guid, labels_body)
    return Response(status_code=NO_CONTENT)


@ENTITY.get(
    "/{guid}/audit",
    responses=json_response(
        array_of(EntityAuditEventV2), description="The entity's audit events, sorted as asked (AUD-06)."
    ),
)
async def get_audit_events(
    guid: str, request: Request, store: Store, found: StoreSet, authorized: Authorizer
) -> AtlasJSONResponse:
    """``getAuditEvents``: the entity's audit events, sorted and paged, or newest first from a key (AUD-06 to AUD-09).

    Reading them needs ``ENTITY_READ``, ``read entity audit`` for a purged entity (AUZ-11).

    Raises:
        AtlasError: ``INSTANCE_GUID_NOT_FOUND`` for an entity that neither exists nor was purged, ``BAD_REQUEST`` for
            a parameter that is no value of its type (DV-39), ``UNAUTHORIZED_ACCESS``.
    """
    validate_guid("guid", guid)
    audits: EntityAuditRepository = found.entity_audits
    asked = read_query(EntityAuditParams, request)
    action, count, offset = asked.audit_action, asked.count, asked.offset
    sort_by, sort_order = asked.sort_by, asked.sort_order
    if await store.get(guid) is None:
        purges = await audits.list_events(guid, EntityAuditActionV2.ENTITY_PURGE, None, 1)
        if not purges or purges[0].entity_header() is None:
            raise AtlasError(AtlasErrorCode.INSTANCE_GUID_NOT_FOUND, guid)
        verify_access(authorized, AtlasPrivilege.ENTITY_READ, "read entity audit: guid=", guid)
    else:
        verify_access(authorized, AtlasPrivilege.ENTITY_READ, READ_ENTITY_GUID, guid)
    if sort_by is not None or offset > -1:
        descending = (sort_order or "").lower() == "desc"
        events = await list_events_sorted(
            audits, guid, action, sort_by, descending=descending, offset=offset, limit=count
        )
    else:
        events = await audits.list_events(guid, action, asked.start_key, count)
    return _json([event.to_json() for event in events])


@ENTITY.get(
    "/bulk/headers",
    responses=json_response(
        AtlasEntityHeaders, description="The entities whose classifications changed since the start time (CAU-07)."
    ),
)
async def get_entity_headers(request: Request, store: Store, found: StoreSet) -> AtlasJSONResponse:
    """``getEntityHeaders``: the entities whose classifications changed since ``tagUpdateStartTime`` (CAU-07).

    Raises:
        AtlasError: ``BAD_REQUEST`` for a start after now, or one that is no number (DV-41).
    """
    end = store.now()
    start = read_query(EntityHeadersParams, request).checked(end)
    headers = await ClassificationRetriever(store, found.entity_audits).get(start, end)
    return _json(headers.to_json())
