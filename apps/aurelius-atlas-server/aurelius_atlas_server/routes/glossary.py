"""The glossary, category and term endpoints of ``GlossaryREST`` under ``/api/atlas/v2/glossary``.

GLS-01 to GLS-06, GCT-01 to GCT-07, GTM-01 to GTM-07, GTA-01 to GTA-04 and GIM-01 to GIM-06.
"""

from typing import Any

from aurelius_atlas_core.entity_store import EntityStore
from aurelius_atlas_core.glossary_service import GlossaryService, SortOrder
from aurelius_atlas_core.glossary_term_utils import glossary_term_headers
from aurelius_atlas_model.glossary import AtlasGlossary, AtlasGlossaryCategory, AtlasGlossaryTerm
from aurelius_atlas_model.instance import AtlasRelatedObjectId
from fastapi import APIRouter, Request, Response
from starlette.datastructures import UploadFile

from aurelius_atlas_server.errors import AtlasError, AtlasErrorCode, AtlasJSONResponse
from aurelius_atlas_server.routes.entity import (
    INT_RANGE,
    Body,
    Store,
    first_value,
    java_number,
    notifier,
    tasks_enabled,
)
from aurelius_atlas_server.routes.types import validate_param_length

GLOSSARY = APIRouter(prefix="/api/atlas/v2/glossary", tags=["Glossary"])

NO_PARTIAL_UPDATES = "PartialUpdates missing or empty"


def _page(request: Request) -> tuple[int, int, SortOrder]:
    """``limit`` (-1), ``offset`` (0) and ``sort`` (``ASC``); ``BAD_REQUEST`` for no number (GLS-05, DV-99)."""
    return (
        java_number(request, "limit", -1, INT_RANGE),
        java_number(request, "offset", 0, INT_RANGE),
        SortOrder.of(first_value(request, "sort") or "ASC"),
    )


def _json(content: Any) -> AtlasJSONResponse:  # noqa: ANN401 - Atlas JSON
    return AtlasJSONResponse(content=content)


def _service(request: Request, store: EntityStore) -> GlossaryService:
    """The service, its term assignments propagating as ``tasks_enabled`` says and audited (GTA-02, GTA-04)."""
    return GlossaryService(store, tasks=tasks_enabled(request), notifier=notifier(request, store))


def _glossary(body: Any) -> AtlasGlossary | None:  # noqa: ANN401 - the request body
    return None if body is None else AtlasGlossary.model_validate(body)


def _category(body: Any) -> AtlasGlossaryCategory | None:  # noqa: ANN401 - the request body
    return None if body is None else AtlasGlossaryCategory.model_validate(body)


def _entities(body: Any) -> list[AtlasRelatedObjectId]:  # noqa: ANN401 - the request body
    return [AtlasRelatedObjectId.model_validate(item) for item in body or []]


def _term(body: Any) -> AtlasGlossaryTerm | None:  # noqa: ANN401 - the request body
    return None if body is None else AtlasGlossaryTerm.model_validate(body)


@GLOSSARY.get("")
async def get_glossaries(request: Request, store: Store) -> AtlasJSONResponse:
    """``getGlossaries``: every glossary, paged and sorted (GLS-05)."""
    limit, offset, sort = _page(request)
    found = await _service(request, store).get_glossaries(limit, offset, sort)
    return _json([glossary.to_json() for glossary in found])


@GLOSSARY.post("")
async def create_glossary(request: Request, body: Body, store: Store) -> AtlasJSONResponse:
    """``createGlossary`` (GLS-02)."""
    return _json((await _service(request, store).create_glossary(_glossary(body))).to_json())


@GLOSSARY.get("/import/template")
async def produce_template() -> Response:
    """``produceTemplate``: the import template's header line, as a download (GIM-06)."""
    return Response(content=glossary_term_headers().encode(), media_type="application/octet-stream")


@GLOSSARY.post("/import")
async def import_glossary_data(request: Request, store: Store) -> AtlasJSONResponse:
    """``importGlossaryData``: the form's ``file``, a CSV or Excel file of terms; no file is no file type (DV-104)."""
    upload = (await request.form()).get("file")
    file_name, content = (upload.filename, await upload.read()) if isinstance(upload, UploadFile) else (None, b"")
    return _json((await _service(request, store).import_glossary_data(file_name, content)).to_json())


@GLOSSARY.get("/term/{term_guid}")
async def get_glossary_term(request: Request, term_guid: str, store: Store) -> AtlasJSONResponse:
    """``getGlossaryTerm`` (GTM-01)."""
    validate_param_length("termGuid", term_guid)
    return _json((await _service(request, store).get_term(term_guid)).to_json())


@GLOSSARY.post("/term")
async def create_glossary_term(request: Request, body: Body, store: Store) -> AtlasJSONResponse:
    """``createGlossaryTerm``: the anchor checked first (GTM-02)."""
    term = _term(body)
    if term is not None and term.anchor is None:
        raise AtlasError(AtlasErrorCode.MISSING_MANDATORY_ANCHOR)
    return _json((await _service(request, store).create_term(term)).to_json())


@GLOSSARY.post("/terms")
async def create_glossary_terms(request: Request, body: Body, store: Store) -> AtlasJSONResponse:
    """``createGlossaryTerms``: every anchor checked first (GTM-02)."""
    terms = None if body is None else [AtlasGlossaryTerm.model_validate(item) for item in body]
    if any(term.anchor is None for term in terms or []):
        raise AtlasError(AtlasErrorCode.MISSING_MANDATORY_ANCHOR)
    created = await _service(request, store).create_terms(terms)
    return _json([term.to_json() for term in created])


@GLOSSARY.put("/term/{term_guid}")
async def update_glossary_term(request: Request, term_guid: str, body: Body, store: Store) -> AtlasJSONResponse:
    """``updateGlossaryTerm``: the term of the path's GUID (GTM-04)."""
    validate_param_length("termGuid", term_guid)
    term = _term(body)
    if term is not None:
        term.guid = term_guid
    return _json((await _service(request, store).update_term(term)).to_json())


@GLOSSARY.put("/term/{term_guid}/partial")
async def partial_update_glossary_term(request: Request, term_guid: str, body: Body, store: Store) -> AtlasJSONResponse:
    """``partialUpdateGlossaryTerm``: name, descriptions, abbreviation and usage; arguments swapped (GTM-04)."""
    validate_param_length("termGuid", term_guid)
    if not body:
        raise AtlasError(AtlasErrorCode.BAD_REQUEST, NO_PARTIAL_UPDATES)
    service = _service(request, store)
    term = await service.get_term(term_guid)
    for key, value in dict(body).items():
        try:
            term.set_attribute(str(key), value)
        except ValueError as error:
            raise AtlasError(AtlasErrorCode.INVALID_PARTIAL_UPDATE_ATTR, "Glossary Term", key) from error
    return _json((await service.update_term(term)).to_json())


@GLOSSARY.delete("/term/{term_guid}", status_code=204)
async def delete_glossary_term(request: Request, term_guid: str, store: Store) -> Response:
    """``deleteGlossaryTerm`` (GTM-05)."""
    validate_param_length("termGuid", term_guid)
    await _service(request, store).delete_term(term_guid)
    return Response(status_code=204)


@GLOSSARY.get("/terms/{term_guid}/related")
async def get_related_terms(term_guid: str, request: Request, store: Store) -> AtlasJSONResponse:
    """``getRelatedTerms``: by relation; the page parameters read and unused, as in Atlas (GTM-06)."""
    validate_param_length("termGuid", term_guid)
    _page(request)
    related = await _service(request, store).get_related_terms(term_guid)
    return _json(
        {relation.attr_name: [header.to_json() for header in headers] for relation, headers in related.items()}
    )


@GLOSSARY.get("/terms/{term_guid}/assignedEntities")
async def get_entities_assigned_with_term(term_guid: str, request: Request, store: Store) -> AtlasJSONResponse:
    """``getEntitiesAssignedWithTerm`` (GTA-01)."""
    validate_param_length("termGuid", term_guid)
    limit, offset, sort = _page(request)
    found = await _service(request, store).get_assigned_entities(term_guid, offset, limit, sort)
    return _json([entity.to_json() for entity in found])


@GLOSSARY.post("/terms/{term_guid}/assignedEntities", status_code=204)
async def assign_term_to_entities(term_guid: str, request: Request, body: Body, store: Store) -> Response:
    """``assignTermToEntities`` (GTA-02)."""
    validate_param_length("termGuid", term_guid)
    await _service(request, store).assign_term_to_entities(term_guid, _entities(body))
    return Response(status_code=204)


@GLOSSARY.delete("/terms/{term_guid}/assignedEntities", status_code=204)
async def remove_term_assignment_from_entities(term_guid: str, request: Request, body: Body, store: Store) -> Response:
    """``removeTermAssignmentFromEntities`` (GTA-03)."""
    return await _remove_term(term_guid, request, body, store)


@GLOSSARY.put("/terms/{term_guid}/assignedEntities", status_code=204)
async def disassociate_term_assignment_from_entities(
    term_guid: str, request: Request, body: Body, store: Store
) -> Response:
    """``disassociateTermAssignmentFromEntities``: as the ``DELETE`` (GTA-03)."""
    return await _remove_term(term_guid, request, body, store)


async def _remove_term(term_guid: str, request: Request, body: Any, store: EntityStore) -> Response:  # noqa: ANN401 - the request body
    """``removeTermFromGlossary``."""
    validate_param_length("termGuid", term_guid)
    await _service(request, store).remove_term_from_entities(term_guid, _entities(body))
    return Response(status_code=204)


@GLOSSARY.get("/category/{category_guid}/terms")
async def get_category_terms(category_guid: str, request: Request, store: Store) -> AtlasJSONResponse:
    """``getCategoryTerms`` (GTM-06)."""
    validate_param_length("categoryGuid", category_guid)
    limit, offset, sort = _page(request)
    found = await _service(request, store).get_category_terms(category_guid, offset, limit, sort)
    return _json([header.to_json() for header in found])


@GLOSSARY.get("/category/{category_guid}")
async def get_glossary_category(request: Request, category_guid: str, store: Store) -> AtlasJSONResponse:
    """``getGlossaryCategory`` (GCT-01)."""
    validate_param_length("categoryGuid", category_guid)
    return _json((await _service(request, store).get_category(category_guid)).to_json())


@GLOSSARY.get("/category/{category_guid}/related")
async def get_related_categories(request: Request, category_guid: str, store: Store) -> AtlasJSONResponse:
    """``getRelatedCategories``: its parent and children (GCT-07)."""
    validate_param_length("categoryGuid", category_guid)
    related = await _service(request, store).get_related_categories(category_guid)
    return _json({key: [header.to_json() for header in headers] for key, headers in related.items()})


@GLOSSARY.post("/category")
async def create_glossary_category(request: Request, body: Body, store: Store) -> AtlasJSONResponse:
    """``createGlossaryCategory``: the anchor checked first (GCT-02)."""
    category = _category(body)
    if category is not None and category.anchor is None:
        raise AtlasError(AtlasErrorCode.MISSING_MANDATORY_ANCHOR)
    return _json((await _service(request, store).create_category(category)).to_json())


@GLOSSARY.post("/categories")
async def create_glossary_categories(request: Request, body: Body, store: Store) -> AtlasJSONResponse:
    """``createGlossaryCategories``: every anchor checked first (GCT-02)."""
    categories = None if body is None else [AtlasGlossaryCategory.model_validate(item) for item in body]
    if any(category.anchor is None for category in categories or []):
        raise AtlasError(AtlasErrorCode.MISSING_MANDATORY_ANCHOR)
    created = await _service(request, store).create_categories(categories)
    return _json([category.to_json() for category in created])


@GLOSSARY.put("/category/{category_guid}")
async def update_glossary_category(request: Request, category_guid: str, body: Body, store: Store) -> AtlasJSONResponse:
    """``updateGlossaryCategory``: the category of the path's GUID (GCT-04)."""
    validate_param_length("categoryGuid", category_guid)
    category = _category(body)
    if category is not None:
        category.guid = category_guid
    return _json((await _service(request, store).update_category(category)).to_json())


@GLOSSARY.put("/category/{category_guid}/partial")
async def partial_update_glossary_category(
    request: Request, category_guid: str, body: Body, store: Store
) -> AtlasJSONResponse:
    """``partialUpdateGlossaryCategory``: name and descriptions; Atlas's arguments swapped in its message (GCT-05)."""
    validate_param_length("categoryGuid", category_guid)
    if not body:
        raise AtlasError(AtlasErrorCode.BAD_REQUEST, NO_PARTIAL_UPDATES)
    service = _service(request, store)
    category = await service.get_category(category_guid)
    for key, value in dict(body).items():
        try:
            category.set_attribute(str(key), value)
        except ValueError as error:
            raise AtlasError(AtlasErrorCode.INVALID_PARTIAL_UPDATE_ATTR, "Glossary Category", key) from error
    return _json((await service.update_category(category)).to_json())


@GLOSSARY.delete("/category/{category_guid}", status_code=204)
async def delete_glossary_category(request: Request, category_guid: str, store: Store) -> Response:
    """``deleteGlossaryCategory`` (GCT-06)."""
    validate_param_length("categoryGuid", category_guid)
    await _service(request, store).delete_category(category_guid)
    return Response(status_code=204)


@GLOSSARY.get("/{glossary_guid}")
async def get_glossary(request: Request, glossary_guid: str, store: Store) -> AtlasJSONResponse:
    """``getGlossary`` (GLS-01, GLS-06)."""
    validate_param_length("glossaryGuid", glossary_guid)
    return _json((await _service(request, store).get_glossary(glossary_guid)).to_json())


@GLOSSARY.get("/{glossary_guid}/detailed")
async def get_detailed_glossary(request: Request, glossary_guid: str, store: Store) -> AtlasJSONResponse:
    """``getDetailedGlossary`` (GLS-06)."""
    validate_param_length("glossaryGuid", glossary_guid)
    return _json((await _service(request, store).get_detailed_glossary(glossary_guid)).to_json())


@GLOSSARY.get("/{glossary_guid}/categories")
async def get_glossary_categories(glossary_guid: str, request: Request, store: Store) -> AtlasJSONResponse:
    """``getGlossaryCategories`` (GLS-05)."""
    validate_param_length("glossaryGuid", glossary_guid)
    limit, offset, sort = _page(request)
    found = await _service(request, store).get_glossary_categories(glossary_guid, offset, limit, sort)
    return _json([category.to_json() for category in found])


@GLOSSARY.get("/{glossary_guid}/categories/headers")
async def get_glossary_categories_headers(glossary_guid: str, request: Request, store: Store) -> AtlasJSONResponse:
    """``getGlossaryCategoriesHeaders`` (GLS-05)."""
    validate_param_length("glossaryGuid", glossary_guid)
    limit, offset, sort = _page(request)
    found = await _service(request, store).get_glossary_categories_headers(glossary_guid, offset, limit, sort)
    return _json([header.to_json() for header in found])


@GLOSSARY.get("/{glossary_guid}/terms")
async def get_glossary_terms(glossary_guid: str, request: Request, store: Store) -> AtlasJSONResponse:
    """``getGlossaryTerms`` (GTM-06)."""
    validate_param_length("glossaryGuid", glossary_guid)
    limit, offset, sort = _page(request)
    found = await _service(request, store).get_glossary_terms(glossary_guid, offset, limit, sort)
    return _json([term.to_json() for term in found])


@GLOSSARY.get("/{glossary_guid}/terms/headers")
async def get_glossary_term_headers(glossary_guid: str, request: Request, store: Store) -> AtlasJSONResponse:
    """``getGlossaryTermHeaders`` (GTM-06)."""
    validate_param_length("glossaryGuid", glossary_guid)
    limit, offset, sort = _page(request)
    found = await _service(request, store).get_glossary_terms_headers(glossary_guid, offset, limit, sort)
    return _json([header.to_json() for header in found])


@GLOSSARY.put("/{glossary_guid}")
async def update_glossary(request: Request, glossary_guid: str, body: Body, store: Store) -> AtlasJSONResponse:
    """``updateGlossary``: the glossary of the path's GUID (GLS-03)."""
    validate_param_length("glossaryGuid", glossary_guid)
    glossary = _glossary(body)
    if glossary is not None:
        glossary.guid = glossary_guid
    return _json((await _service(request, store).update_glossary(glossary)).to_json())


@GLOSSARY.put("/{glossary_guid}/partial")
async def partial_update_glossary(request: Request, glossary_guid: str, body: Body, store: Store) -> AtlasJSONResponse:
    """``partialUpdateGlossary``: name, descriptions, language and usage (GLS-03)."""
    validate_param_length("glossaryGuid", glossary_guid)
    if not body:
        raise AtlasError(AtlasErrorCode.BAD_REQUEST, NO_PARTIAL_UPDATES)
    service = _service(request, store)
    glossary = await service.get_glossary(glossary_guid)
    for key, value in dict(body).items():
        try:
            glossary.set_attribute(str(key), value)
        except ValueError as error:
            raise AtlasError(AtlasErrorCode.INVALID_PARTIAL_UPDATE_ATTR, key, "Glossary") from error
    return _json((await service.update_glossary(glossary)).to_json())


@GLOSSARY.delete("/{glossary_guid}", status_code=204)
async def delete_glossary(request: Request, glossary_guid: str, store: Store) -> Response:
    """``deleteGlossary`` (GLS-04)."""
    validate_param_length("glossaryGuid", glossary_guid)
    await _service(request, store).delete_glossary(glossary_guid)
    return Response(status_code=204)
