"""The glossary and category endpoints of ``GlossaryREST`` under ``/api/atlas/v2/glossary`` (GLS-01 to GCT-07).

Terms (5.2b) and their assignment (5.2c) follow; glossary import is a later increment.
"""

from typing import Any

from aurelius_atlas_core.entity_store import EntityStore
from aurelius_atlas_core.glossary_service import GlossaryService, SortOrder
from aurelius_atlas_model.glossary import AtlasGlossary, AtlasGlossaryCategory
from fastapi import APIRouter, Request, Response

from aurelius_atlas_server.errors import AtlasError, AtlasErrorCode, AtlasJSONResponse
from aurelius_atlas_server.routes.entity import INT_RANGE, Body, Store, first_value, java_number
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


def _service(store: EntityStore) -> GlossaryService:
    return GlossaryService(store)


def _glossary(body: Any) -> AtlasGlossary | None:  # noqa: ANN401 - the request body
    return None if body is None else AtlasGlossary.model_validate(body)


def _category(body: Any) -> AtlasGlossaryCategory | None:  # noqa: ANN401 - the request body
    return None if body is None else AtlasGlossaryCategory.model_validate(body)


@GLOSSARY.get("")
async def get_glossaries(request: Request, store: Store) -> AtlasJSONResponse:
    """``getGlossaries``: every glossary, paged and sorted (GLS-05)."""
    limit, offset, sort = _page(request)
    found = await _service(store).get_glossaries(limit, offset, sort)
    return _json([glossary.to_json() for glossary in found])


@GLOSSARY.post("")
async def create_glossary(body: Body, store: Store) -> AtlasJSONResponse:
    """``createGlossary`` (GLS-02)."""
    return _json((await _service(store).create_glossary(_glossary(body))).to_json())


@GLOSSARY.get("/category/{category_guid}")
async def get_glossary_category(category_guid: str, store: Store) -> AtlasJSONResponse:
    """``getGlossaryCategory`` (GCT-01)."""
    validate_param_length("categoryGuid", category_guid)
    return _json((await _service(store).get_category(category_guid)).to_json())


@GLOSSARY.get("/category/{category_guid}/related")
async def get_related_categories(category_guid: str, store: Store) -> AtlasJSONResponse:
    """``getRelatedCategories``: its parent and children (GCT-07)."""
    validate_param_length("categoryGuid", category_guid)
    related = await _service(store).get_related_categories(category_guid)
    return _json({key: [header.to_json() for header in headers] for key, headers in related.items()})


@GLOSSARY.post("/category")
async def create_glossary_category(body: Body, store: Store) -> AtlasJSONResponse:
    """``createGlossaryCategory``: the anchor checked first (GCT-02)."""
    category = _category(body)
    if category is not None and category.anchor is None:
        raise AtlasError(AtlasErrorCode.MISSING_MANDATORY_ANCHOR)
    return _json((await _service(store).create_category(category)).to_json())


@GLOSSARY.post("/categories")
async def create_glossary_categories(body: Body, store: Store) -> AtlasJSONResponse:
    """``createGlossaryCategories``: every anchor checked first (GCT-02)."""
    categories = None if body is None else [AtlasGlossaryCategory.model_validate(item) for item in body]
    if any(category.anchor is None for category in categories or []):
        raise AtlasError(AtlasErrorCode.MISSING_MANDATORY_ANCHOR)
    created = await _service(store).create_categories(categories)
    return _json([category.to_json() for category in created])


@GLOSSARY.put("/category/{category_guid}")
async def update_glossary_category(category_guid: str, body: Body, store: Store) -> AtlasJSONResponse:
    """``updateGlossaryCategory``: the category of the path's GUID (GCT-04)."""
    validate_param_length("categoryGuid", category_guid)
    category = _category(body)
    if category is not None:
        category.guid = category_guid
    return _json((await _service(store).update_category(category)).to_json())


@GLOSSARY.put("/category/{category_guid}/partial")
async def partial_update_glossary_category(category_guid: str, body: Body, store: Store) -> AtlasJSONResponse:
    """``partialUpdateGlossaryCategory``: name and descriptions; Atlas's arguments swapped in its message (GCT-05)."""
    validate_param_length("categoryGuid", category_guid)
    if not body:
        raise AtlasError(AtlasErrorCode.BAD_REQUEST, NO_PARTIAL_UPDATES)
    service = _service(store)
    category = await service.get_category(category_guid)
    for key, value in dict(body).items():
        try:
            category.set_attribute(str(key), value)
        except ValueError as error:
            raise AtlasError(AtlasErrorCode.INVALID_PARTIAL_UPDATE_ATTR, "Glossary Category", key) from error
    return _json((await service.update_category(category)).to_json())


@GLOSSARY.delete("/category/{category_guid}", status_code=204)
async def delete_glossary_category(category_guid: str, store: Store) -> Response:
    """``deleteGlossaryCategory`` (GCT-06)."""
    validate_param_length("categoryGuid", category_guid)
    await _service(store).delete_category(category_guid)
    return Response(status_code=204)


@GLOSSARY.get("/{glossary_guid}")
async def get_glossary(glossary_guid: str, store: Store) -> AtlasJSONResponse:
    """``getGlossary`` (GLS-01, GLS-06)."""
    validate_param_length("glossaryGuid", glossary_guid)
    return _json((await _service(store).get_glossary(glossary_guid)).to_json())


@GLOSSARY.get("/{glossary_guid}/detailed")
async def get_detailed_glossary(glossary_guid: str, store: Store) -> AtlasJSONResponse:
    """``getDetailedGlossary`` (GLS-06)."""
    validate_param_length("glossaryGuid", glossary_guid)
    return _json((await _service(store).get_detailed_glossary(glossary_guid)).to_json())


@GLOSSARY.get("/{glossary_guid}/categories")
async def get_glossary_categories(glossary_guid: str, request: Request, store: Store) -> AtlasJSONResponse:
    """``getGlossaryCategories`` (GLS-05)."""
    validate_param_length("glossaryGuid", glossary_guid)
    limit, offset, sort = _page(request)
    found = await _service(store).get_glossary_categories(glossary_guid, offset, limit, sort)
    return _json([category.to_json() for category in found])


@GLOSSARY.get("/{glossary_guid}/categories/headers")
async def get_glossary_categories_headers(glossary_guid: str, request: Request, store: Store) -> AtlasJSONResponse:
    """``getGlossaryCategoriesHeaders`` (GLS-05)."""
    validate_param_length("glossaryGuid", glossary_guid)
    limit, offset, sort = _page(request)
    found = await _service(store).get_glossary_categories_headers(glossary_guid, offset, limit, sort)
    return _json([header.to_json() for header in found])


@GLOSSARY.put("/{glossary_guid}")
async def update_glossary(glossary_guid: str, body: Body, store: Store) -> AtlasJSONResponse:
    """``updateGlossary``: the glossary of the path's GUID (GLS-03)."""
    validate_param_length("glossaryGuid", glossary_guid)
    glossary = _glossary(body)
    if glossary is not None:
        glossary.guid = glossary_guid
    return _json((await _service(store).update_glossary(glossary)).to_json())


@GLOSSARY.put("/{glossary_guid}/partial")
async def partial_update_glossary(glossary_guid: str, body: Body, store: Store) -> AtlasJSONResponse:
    """``partialUpdateGlossary``: name, descriptions, language and usage (GLS-03)."""
    validate_param_length("glossaryGuid", glossary_guid)
    if not body:
        raise AtlasError(AtlasErrorCode.BAD_REQUEST, NO_PARTIAL_UPDATES)
    service = _service(store)
    glossary = await service.get_glossary(glossary_guid)
    for key, value in dict(body).items():
        try:
            glossary.set_attribute(str(key), value)
        except ValueError as error:
            raise AtlasError(AtlasErrorCode.INVALID_PARTIAL_UPDATE_ATTR, key, "Glossary") from error
    return _json((await service.update_glossary(glossary)).to_json())


@GLOSSARY.delete("/{glossary_guid}", status_code=204)
async def delete_glossary(glossary_guid: str, store: Store) -> Response:
    """``deleteGlossary`` (GLS-04)."""
    validate_param_length("glossaryGuid", glossary_guid)
    await _service(store).delete_glossary(glossary_guid)
    return Response(status_code=204)
