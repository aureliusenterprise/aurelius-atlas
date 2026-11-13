"""The glossary, category and term endpoints of ``GlossaryREST`` under ``/api/atlas/v2/glossary``.

GLS-01 to GLS-06, GCT-01 to GCT-07, GTM-01 to GTM-07, GTA-01 to GTA-04 and GIM-01 to GIM-06.
"""

from typing import Annotated, Any

from aurelius_atlas_core.entity_store import EntityStore
from aurelius_atlas_core.glossary_service import GlossaryService, SortOrder
from aurelius_atlas_core.glossary_term_utils import glossary_term_headers
from aurelius_atlas_model.bulk_import import BulkImportResponse
from aurelius_atlas_model.glossary import (
    AtlasGlossary,
    AtlasGlossaryCategory,
    AtlasGlossaryExtInfo,
    AtlasGlossaryTerm,
    AtlasRelatedCategoryHeader,
    AtlasRelatedTermHeader,
    RelatedCategories,
    RelatedTerms,
)
from aurelius_atlas_model.instance import AtlasRelatedObjectId
from aurelius_atlas_model.lists import GlossaryCategories, GlossaryTerms, RelatedObjectIds
from aurelius_atlas_model.maps import AttributeValues
from aurelius_atlas_model.params import PageParams, read_params
from fastapi import APIRouter, Depends, Request, Response
from starlette.datastructures import UploadFile

from aurelius_atlas_server.authentication import acting_user
from aurelius_atlas_server.authorization import authorizer
from aurelius_atlas_server.bodies import json_model, json_root
from aurelius_atlas_server.errors import AtlasError, AtlasErrorCode, AtlasJSONResponse
from aurelius_atlas_server.openapi import (
    array_of,
    download_response,
    form_request,
    json_response,
    request_body,
)
from aurelius_atlas_server.openapi import no_content as no_content_response
from aurelius_atlas_server.routes.entity import Store, notifier, tasks_enabled
from aurelius_atlas_server.routes.types import validate_param_length

GLOSSARY = APIRouter(prefix="/api/atlas/v2/glossary", tags=["Glossary"])

NO_PARTIAL_UPDATES = "PartialUpdates missing or empty"

GLOSSARY_BODY = json_model(AtlasGlossary)
"""``createGlossary``/``updateGlossary``: the glossary, validated by its model (GLS-02, GLS-03)."""

GLOSSARY_TERM_BODY = json_model(AtlasGlossaryTerm)
"""``createGlossaryTerm``/``updateGlossaryTerm``: the term, validated by its model (GTM-02, GTM-04)."""

GLOSSARY_TERMS_BODY = json_root(GlossaryTerms)
"""``createGlossaryTerms``: every term to create, each validated (GTM-02)."""

GLOSSARY_CATEGORY_BODY = json_model(AtlasGlossaryCategory)
"""``createGlossaryCategory``/``updateGlossaryCategory``: the category, validated by its model (GCT-02, GCT-04)."""

GLOSSARY_CATEGORIES_BODY = json_root(GlossaryCategories)
"""``createGlossaryCategories``: every category to create, each validated (GCT-02)."""

PARTIAL_UPDATE_BODY = json_root(AttributeValues)
"""The partial updates: the attributes to set by name, a JSON object of them (GLS-03, GCT-05, GTM-04)."""

ASSIGNED_ENTITIES_BODY = json_root(RelatedObjectIds)
"""``assignTermToEntities`` and friends: the entities to assign the term to or remove it from (GTA-02, GTA-03)."""

type GlossaryBody = Annotated[AtlasGlossary | None, Depends(GLOSSARY_BODY)]
type GlossaryTermBody = Annotated[AtlasGlossaryTerm | None, Depends(GLOSSARY_TERM_BODY)]
type GlossaryTermsBody = Annotated[list[AtlasGlossaryTerm] | None, Depends(GLOSSARY_TERMS_BODY)]
type GlossaryCategoryBody = Annotated[AtlasGlossaryCategory | None, Depends(GLOSSARY_CATEGORY_BODY)]
type GlossaryCategoriesBody = Annotated[list[AtlasGlossaryCategory] | None, Depends(GLOSSARY_CATEGORIES_BODY)]
type PartialUpdateBody = Annotated[dict[str, Any] | None, Depends(PARTIAL_UPDATE_BODY)]
type AssignedEntitiesBody = Annotated[list[AtlasRelatedObjectId] | None, Depends(ASSIGNED_ENTITIES_BODY)]


def _page(request: Request) -> tuple[int, int, SortOrder]:
    """``limit`` (-1), ``offset`` (0) and ``sort`` (``ASC``); ``BAD_REQUEST`` for no number (GLS-05, DV-99)."""
    page = read_params(PageParams, request.query_params)
    return (page.limit, page.offset, SortOrder.of(page.sort_name()))


def _json(content: Any) -> AtlasJSONResponse:  # noqa: ANN401 - Atlas JSON
    return AtlasJSONResponse(content=content)


def _service(request: Request, store: EntityStore) -> GlossaryService:
    """The service, its term assignments propagating as ``tasks_enabled`` says and audited (GTA-02, GTA-04).

    Each read and change is checked as the entity and relationship stores check it (AUZ-10).
    """
    return GlossaryService(
        store,
        user=acting_user(request),
        tasks=tasks_enabled(request),
        notifier=notifier(request, store),
        authorizer=authorizer(request),
    )


@GLOSSARY.get(
    "", responses=json_response(array_of(AtlasGlossary), description="Every glossary, paged and sorted (GLS-05).")
)
async def get_glossaries(request: Request, store: Store) -> AtlasJSONResponse:
    """``getGlossaries``: every glossary, paged and sorted (GLS-05)."""
    limit, offset, sort = _page(request)
    found = await _service(request, store).get_glossaries(limit, offset, sort)
    return _json([glossary.to_json() for glossary in found])


@GLOSSARY.post(
    "",
    responses=json_response(AtlasGlossary, description="The created glossary, with its GUID (GLS-02)."),
    **request_body(AtlasGlossary, description="The glossary to create."),
)
async def create_glossary(request: Request, glossary_body: GlossaryBody, store: Store) -> AtlasJSONResponse:
    """``createGlossary`` (GLS-02)."""
    return _json((await _service(request, store).create_glossary(glossary_body)).to_json())


@GLOSSARY.get(
    "/import/template",
    responses=download_response(
        "application/octet-stream", description="The import template's header line, as a download (GIM-06)."
    ),
)
async def produce_template() -> Response:
    """``produceTemplate``: the import template's header line, as a download (GIM-06)."""
    return Response(content=glossary_term_headers().encode(), media_type="application/octet-stream")


@GLOSSARY.post(
    "/import",
    responses=json_response(BulkImportResponse, description="The outcome per line of the file (GIM-01 to GIM-05)."),
    **form_request(fields={"file": "A CSV or Excel file of terms."}),
)
async def import_glossary_data(request: Request, store: Store) -> AtlasJSONResponse:
    """``importGlossaryData``: the form's ``file``, a CSV or Excel file of terms; no file is no file type (DV-104)."""
    upload = (await request.form()).get("file")
    file_name, content = (upload.filename, await upload.read()) if isinstance(upload, UploadFile) else (None, b"")
    return _json((await _service(request, store).import_glossary_data(file_name, content)).to_json())


@GLOSSARY.get(
    "/term/{term_guid}", responses=json_response(AtlasGlossaryTerm, description="The term of the GUID (GTM-01).")
)
async def get_glossary_term(request: Request, term_guid: str, store: Store) -> AtlasJSONResponse:
    """``getGlossaryTerm`` (GTM-01)."""
    validate_param_length("termGuid", term_guid)
    return _json((await _service(request, store).get_term(term_guid)).to_json())


@GLOSSARY.post(
    "/term",
    responses=json_response(AtlasGlossaryTerm, description="The created term, with its GUID (GTM-02)."),
    **request_body(AtlasGlossaryTerm, description="The term to create; its anchor is required."),
)
async def create_glossary_term(request: Request, term_body: GlossaryTermBody, store: Store) -> AtlasJSONResponse:
    """``createGlossaryTerm``: the anchor checked first (GTM-02)."""
    term = term_body
    if term is not None and term.anchor is None:
        raise AtlasError(AtlasErrorCode.MISSING_MANDATORY_ANCHOR)
    return _json((await _service(request, store).create_term(term)).to_json())


@GLOSSARY.post(
    "/terms",
    responses=json_response(array_of(AtlasGlossaryTerm), description="The created terms (GTM-02)."),
    **request_body(array_of(AtlasGlossaryTerm), description="The terms to create; each anchor is required."),
)
async def create_glossary_terms(request: Request, terms_body: GlossaryTermsBody, store: Store) -> AtlasJSONResponse:
    """``createGlossaryTerms``: every anchor checked first (GTM-02)."""
    terms = terms_body
    if any(term.anchor is None for term in terms or []):
        raise AtlasError(AtlasErrorCode.MISSING_MANDATORY_ANCHOR)
    created = await _service(request, store).create_terms(terms)
    return _json([term.to_json() for term in created])


@GLOSSARY.put(
    "/term/{term_guid}",
    responses=json_response(AtlasGlossaryTerm, description="The updated term (GTM-04)."),
    **request_body(AtlasGlossaryTerm, description="The term to update; its GUID is the path's."),
)
async def update_glossary_term(
    request: Request, term_guid: str, term_body: GlossaryTermBody, store: Store
) -> AtlasJSONResponse:
    """``updateGlossaryTerm``: the term of the path's GUID (GTM-04)."""
    validate_param_length("termGuid", term_guid)
    term = term_body
    if term is not None:
        term.guid = term_guid
    return _json((await _service(request, store).update_term(term)).to_json())


@GLOSSARY.put(
    "/term/{term_guid}/partial",
    responses=json_response(AtlasGlossaryTerm, description="The updated term (GTM-04)."),
    **request_body(AttributeValues, description="The attributes to set, by name; at least one is required."),
)
async def partial_update_glossary_term(
    request: Request, term_guid: str, values: PartialUpdateBody, store: Store
) -> AtlasJSONResponse:
    """``partialUpdateGlossaryTerm``: name, descriptions, abbreviation and usage; arguments swapped (GTM-04)."""
    validate_param_length("termGuid", term_guid)
    if not values:
        raise AtlasError(AtlasErrorCode.BAD_REQUEST, NO_PARTIAL_UPDATES)
    service = _service(request, store)
    term = await service.get_term(term_guid)
    for key, value in values.items():
        try:
            term.set_attribute(str(key), value)
        except ValueError as error:
            raise AtlasError(AtlasErrorCode.INVALID_PARTIAL_UPDATE_ATTR, "Glossary Term", key) from error
    return _json((await service.update_term(term)).to_json())


@GLOSSARY.delete("/term/{term_guid}", status_code=204, responses=no_content_response("The term is deleted (GTM-05)."))
async def delete_glossary_term(request: Request, term_guid: str, store: Store) -> Response:
    """``deleteGlossaryTerm`` (GTM-05)."""
    validate_param_length("termGuid", term_guid)
    await _service(request, store).delete_term(term_guid)
    return Response(status_code=204)


@GLOSSARY.get(
    "/terms/{term_guid}/related",
    responses=json_response(RelatedTerms, description="The related terms, by relation attribute name (GTM-06)."),
)
async def get_related_terms(term_guid: str, request: Request, store: Store) -> AtlasJSONResponse:
    """``getRelatedTerms``: by relation; the page parameters read and unused, as in Atlas (GTM-06)."""
    validate_param_length("termGuid", term_guid)
    _page(request)
    related = await _service(request, store).get_related_terms(term_guid)
    return _json(
        {relation.attr_name: [header.to_json() for header in headers] for relation, headers in related.items()}
    )


@GLOSSARY.get(
    "/terms/{term_guid}/assignedEntities",
    responses=json_response(array_of(AtlasRelatedObjectId), description="The entities assigned the term (GTA-01)."),
)
async def get_entities_assigned_with_term(term_guid: str, request: Request, store: Store) -> AtlasJSONResponse:
    """``getEntitiesAssignedWithTerm`` (GTA-01)."""
    validate_param_length("termGuid", term_guid)
    limit, offset, sort = _page(request)
    found = await _service(request, store).get_assigned_entities(term_guid, offset, limit, sort)
    return _json([entity.to_json() for entity in found])


@GLOSSARY.post(
    "/terms/{term_guid}/assignedEntities",
    status_code=204,
    responses=no_content_response("The term is assigned to the entities (GTA-02)."),
    **request_body(array_of(AtlasRelatedObjectId), description="The entities to assign the term to."),
)
async def assign_term_to_entities(
    term_guid: str, request: Request, entities_body: AssignedEntitiesBody, store: Store
) -> Response:
    """``assignTermToEntities`` (GTA-02)."""
    validate_param_length("termGuid", term_guid)
    await _service(request, store).assign_term_to_entities(term_guid, entities_body or [])
    return Response(status_code=204)


@GLOSSARY.delete(
    "/terms/{term_guid}/assignedEntities",
    status_code=204,
    responses=no_content_response("The term's assignment to the entities is removed (GTA-03)."),
    **request_body(array_of(AtlasRelatedObjectId), description="The entities to remove the term from."),
)
async def remove_term_assignment_from_entities(
    term_guid: str, request: Request, entities_body: AssignedEntitiesBody, store: Store
) -> Response:
    """``removeTermAssignmentFromEntities`` (GTA-03)."""
    return await _remove_term(term_guid, request, entities_body, store)


@GLOSSARY.put(
    "/terms/{term_guid}/assignedEntities",
    status_code=204,
    responses=no_content_response("The term's assignment to the entities is removed (GTA-03)."),
    **request_body(array_of(AtlasRelatedObjectId), description="The entities to disassociate the term from."),
)
async def disassociate_term_assignment_from_entities(
    term_guid: str, request: Request, entities_body: AssignedEntitiesBody, store: Store
) -> Response:
    """``disassociateTermAssignmentFromEntities``: as the ``DELETE`` (GTA-03)."""
    return await _remove_term(term_guid, request, entities_body, store)


async def _remove_term(
    term_guid: str, request: Request, entities: list[AtlasRelatedObjectId] | None, store: EntityStore
) -> Response:
    """``removeTermFromGlossary``."""
    validate_param_length("termGuid", term_guid)
    await _service(request, store).remove_term_from_entities(term_guid, entities or [])
    return Response(status_code=204)


@GLOSSARY.get(
    "/category/{category_guid}/terms",
    responses=json_response(array_of(AtlasRelatedTermHeader), description="The category's terms, as headers (GTM-06)."),
)
async def get_category_terms(category_guid: str, request: Request, store: Store) -> AtlasJSONResponse:
    """``getCategoryTerms`` (GTM-06)."""
    validate_param_length("categoryGuid", category_guid)
    limit, offset, sort = _page(request)
    found = await _service(request, store).get_category_terms(category_guid, offset, limit, sort)
    return _json([header.to_json() for header in found])


@GLOSSARY.get(
    "/category/{category_guid}",
    responses=json_response(AtlasGlossaryCategory, description="The category of the GUID (GCT-01)."),
)
async def get_glossary_category(request: Request, category_guid: str, store: Store) -> AtlasJSONResponse:
    """``getGlossaryCategory`` (GCT-01)."""
    validate_param_length("categoryGuid", category_guid)
    return _json((await _service(request, store).get_category(category_guid)).to_json())


@GLOSSARY.get(
    "/category/{category_guid}/related",
    responses=json_response(RelatedCategories, description="The category's parent and children (GCT-07)."),
)
async def get_related_categories(request: Request, category_guid: str, store: Store) -> AtlasJSONResponse:
    """``getRelatedCategories``: its parent and children (GCT-07)."""
    validate_param_length("categoryGuid", category_guid)
    related = await _service(request, store).get_related_categories(category_guid)
    return _json({key: [header.to_json() for header in headers] for key, headers in related.items()})


@GLOSSARY.post(
    "/category",
    responses=json_response(AtlasGlossaryCategory, description="The created category, with its GUID (GCT-02)."),
    **request_body(AtlasGlossaryCategory, description="The category to create; its anchor is required."),
)
async def create_glossary_category(
    request: Request, category_body: GlossaryCategoryBody, store: Store
) -> AtlasJSONResponse:
    """``createGlossaryCategory``: the anchor checked first (GCT-02)."""
    category = category_body
    if category is not None and category.anchor is None:
        raise AtlasError(AtlasErrorCode.MISSING_MANDATORY_ANCHOR)
    return _json((await _service(request, store).create_category(category)).to_json())


@GLOSSARY.post(
    "/categories",
    responses=json_response(array_of(AtlasGlossaryCategory), description="The created categories (GCT-02)."),
    **request_body(array_of(AtlasGlossaryCategory), description="The categories to create; each anchor is required."),
)
async def create_glossary_categories(
    request: Request, categories_body: GlossaryCategoriesBody, store: Store
) -> AtlasJSONResponse:
    """``createGlossaryCategories``: every anchor checked first (GCT-02)."""
    categories = categories_body
    if any(category.anchor is None for category in categories or []):
        raise AtlasError(AtlasErrorCode.MISSING_MANDATORY_ANCHOR)
    created = await _service(request, store).create_categories(categories)
    return _json([category.to_json() for category in created])


@GLOSSARY.put(
    "/category/{category_guid}",
    responses=json_response(AtlasGlossaryCategory, description="The updated category (GCT-04)."),
    **request_body(AtlasGlossaryCategory, description="The category to update; its GUID is the path's."),
)
async def update_glossary_category(
    request: Request, category_guid: str, category_body: GlossaryCategoryBody, store: Store
) -> AtlasJSONResponse:
    """``updateGlossaryCategory``: the category of the path's GUID (GCT-04)."""
    validate_param_length("categoryGuid", category_guid)
    category = category_body
    if category is not None:
        category.guid = category_guid
    return _json((await _service(request, store).update_category(category)).to_json())


@GLOSSARY.put(
    "/category/{category_guid}/partial",
    responses=json_response(AtlasGlossaryCategory, description="The updated category (GCT-05)."),
    **request_body(AttributeValues, description="The attributes to set, by name; at least one is required."),
)
async def partial_update_glossary_category(
    request: Request, category_guid: str, values: PartialUpdateBody, store: Store
) -> AtlasJSONResponse:
    """``partialUpdateGlossaryCategory``: name and descriptions; Atlas's arguments swapped in its message (GCT-05)."""
    validate_param_length("categoryGuid", category_guid)
    if not values:
        raise AtlasError(AtlasErrorCode.BAD_REQUEST, NO_PARTIAL_UPDATES)
    service = _service(request, store)
    category = await service.get_category(category_guid)
    for key, value in values.items():
        try:
            category.set_attribute(str(key), value)
        except ValueError as error:
            raise AtlasError(AtlasErrorCode.INVALID_PARTIAL_UPDATE_ATTR, "Glossary Category", key) from error
    return _json((await service.update_category(category)).to_json())


@GLOSSARY.delete(
    "/category/{category_guid}", status_code=204, responses=no_content_response("The category is deleted (GCT-06).")
)
async def delete_glossary_category(request: Request, category_guid: str, store: Store) -> Response:
    """``deleteGlossaryCategory`` (GCT-06)."""
    validate_param_length("categoryGuid", category_guid)
    await _service(request, store).delete_category(category_guid)
    return Response(status_code=204)


@GLOSSARY.get(
    "/{glossary_guid}", responses=json_response(AtlasGlossary, description="The glossary of the GUID (GLS-01).")
)
async def get_glossary(request: Request, glossary_guid: str, store: Store) -> AtlasJSONResponse:
    """``getGlossary`` (GLS-01, GLS-06)."""
    validate_param_length("glossaryGuid", glossary_guid)
    return _json((await _service(request, store).get_glossary(glossary_guid)).to_json())


@GLOSSARY.get(
    "/{glossary_guid}/detailed",
    responses=json_response(AtlasGlossaryExtInfo, description="The glossary with its categories and terms (GLS-06)."),
)
async def get_detailed_glossary(request: Request, glossary_guid: str, store: Store) -> AtlasJSONResponse:
    """``getDetailedGlossary`` (GLS-06)."""
    validate_param_length("glossaryGuid", glossary_guid)
    return _json((await _service(request, store).get_detailed_glossary(glossary_guid)).to_json())


@GLOSSARY.get(
    "/{glossary_guid}/categories",
    responses=json_response(array_of(AtlasGlossaryCategory), description="The glossary's categories (GLS-05)."),
)
async def get_glossary_categories(glossary_guid: str, request: Request, store: Store) -> AtlasJSONResponse:
    """``getGlossaryCategories`` (GLS-05)."""
    validate_param_length("glossaryGuid", glossary_guid)
    limit, offset, sort = _page(request)
    found = await _service(request, store).get_glossary_categories(glossary_guid, offset, limit, sort)
    return _json([category.to_json() for category in found])


@GLOSSARY.get(
    "/{glossary_guid}/categories/headers",
    responses=json_response(
        array_of(AtlasRelatedCategoryHeader), description="The glossary's categories, as headers (GLS-05)."
    ),
)
async def get_glossary_categories_headers(glossary_guid: str, request: Request, store: Store) -> AtlasJSONResponse:
    """``getGlossaryCategoriesHeaders`` (GLS-05)."""
    validate_param_length("glossaryGuid", glossary_guid)
    limit, offset, sort = _page(request)
    found = await _service(request, store).get_glossary_categories_headers(glossary_guid, offset, limit, sort)
    return _json([header.to_json() for header in found])


@GLOSSARY.get(
    "/{glossary_guid}/terms",
    responses=json_response(array_of(AtlasGlossaryTerm), description="The glossary's terms (GTM-06)."),
)
async def get_glossary_terms(glossary_guid: str, request: Request, store: Store) -> AtlasJSONResponse:
    """``getGlossaryTerms`` (GTM-06)."""
    validate_param_length("glossaryGuid", glossary_guid)
    limit, offset, sort = _page(request)
    found = await _service(request, store).get_glossary_terms(glossary_guid, offset, limit, sort)
    return _json([term.to_json() for term in found])


@GLOSSARY.get(
    "/{glossary_guid}/terms/headers",
    responses=json_response(array_of(AtlasRelatedTermHeader), description="The glossary's terms, as headers (GTM-06)."),
)
async def get_glossary_term_headers(glossary_guid: str, request: Request, store: Store) -> AtlasJSONResponse:
    """``getGlossaryTermHeaders`` (GTM-06)."""
    validate_param_length("glossaryGuid", glossary_guid)
    limit, offset, sort = _page(request)
    found = await _service(request, store).get_glossary_terms_headers(glossary_guid, offset, limit, sort)
    return _json([header.to_json() for header in found])


@GLOSSARY.put(
    "/{glossary_guid}",
    responses=json_response(AtlasGlossary, description="The updated glossary (GLS-03)."),
    **request_body(AtlasGlossary, description="The glossary to update; its GUID is the path's."),
)
async def update_glossary(
    request: Request, glossary_guid: str, glossary_body: GlossaryBody, store: Store
) -> AtlasJSONResponse:
    """``updateGlossary``: the glossary of the path's GUID (GLS-03)."""
    validate_param_length("glossaryGuid", glossary_guid)
    glossary = glossary_body
    if glossary is not None:
        glossary.guid = glossary_guid
    return _json((await _service(request, store).update_glossary(glossary)).to_json())


@GLOSSARY.put(
    "/{glossary_guid}/partial",
    responses=json_response(AtlasGlossary, description="The updated glossary (GLS-03)."),
    **request_body(AttributeValues, description="The attributes to set, by name; at least one is required."),
)
async def partial_update_glossary(
    request: Request, glossary_guid: str, values: PartialUpdateBody, store: Store
) -> AtlasJSONResponse:
    """``partialUpdateGlossary``: name, descriptions, language and usage (GLS-03)."""
    validate_param_length("glossaryGuid", glossary_guid)
    if not values:
        raise AtlasError(AtlasErrorCode.BAD_REQUEST, NO_PARTIAL_UPDATES)
    service = _service(request, store)
    glossary = await service.get_glossary(glossary_guid)
    for key, value in values.items():
        try:
            glossary.set_attribute(str(key), value)
        except ValueError as error:
            raise AtlasError(AtlasErrorCode.INVALID_PARTIAL_UPDATE_ATTR, key, "Glossary") from error
    return _json((await service.update_glossary(glossary)).to_json())


@GLOSSARY.delete(
    "/{glossary_guid}", status_code=204, responses=no_content_response("The glossary is deleted (GLS-04).")
)
async def delete_glossary(request: Request, glossary_guid: str, store: Store) -> Response:
    """``deleteGlossary`` (GLS-04)."""
    validate_param_length("glossaryGuid", glossary_guid)
    await _service(request, store).delete_glossary(glossary_guid)
    return Response(status_code=204)
