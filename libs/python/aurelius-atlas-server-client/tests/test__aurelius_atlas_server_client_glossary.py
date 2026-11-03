"""``GlossaryApi`` against the recording transport (CLG-01..CLG-09).

One test per rule cluster of the 8.10 coverage matrix, each naming the client
methods it exercises (ADR 056); the recorder pins method, path, query, and body
for every route of ``routes/glossary.py`` (CL-02). The paging defaults travel as
absence (CLG-02), the create methods send the anchor as given (CLG-05), the
updates send the caller's model as given (CLG-08), and the two file routes cross
as bytes (CLG-06, CL-64).
"""

import json
from typing import Any

import httpx2 as httpx
import pytest
from aurelius_atlas_model.glossary import (
    AtlasGlossary,
    AtlasGlossaryCategory,
    AtlasGlossaryHeader,
    AtlasGlossaryTerm,
)
from aurelius_atlas_model.instance import AtlasRelatedObjectId
from aurelius_atlas_server_client.client import AtlasClient, AtlasClientError
from server_recorder import Recorder

G_LOAN = "00000000-0000-4000-8000-00000000000a"
G_TERM = "00000000-0000-4000-8000-00000000000b"
G_CAT = "00000000-0000-4000-8000-00000000000c"
G_ENTITY = "00000000-0000-4000-8000-00000000000d"
ROOT = "/api/atlas/v2/glossary"
"""The mounted prefix of the route module, as the server answers it (CLG-01)."""

ERROR_BODY = {"errorCode": "ATLAS-400-00-017", "errorMessage": "no such glossary"}

GLOSSARY_ANSWER: dict[str, Any] = {"guid": G_LOAN, "name": "business_glossary", "qualifiedName": "bg"}
CATEGORY_ANSWER: dict[str, Any] = {"guid": G_CAT, "name": "Finance", "anchor": {"glossaryGuid": G_LOAN}}
TERM_ANSWER: dict[str, Any] = {"guid": G_TERM, "name": "loan", "anchor": {"glossaryGuid": G_LOAN}}
HEADER_ANSWER: dict[str, Any] = {"termGuid": G_TERM, "displayText": "loan"}
CATEGORY_HEADER_ANSWER: dict[str, Any] = {"categoryGuid": G_CAT, "displayText": "Finance"}
ASSIGNED_ANSWER: list[dict[str, Any]] = [{"guid": G_ENTITY, "typeName": "sales_table", "displayText": "t"}]
IMPORT_ANSWER: dict[str, Any] = {"successImportInfoList": [{"childObjectName": "loan", "importStatus": "SUCCESS"}]}
DETAILED_ANSWER: dict[str, Any] = {
    **GLOSSARY_ANSWER,
    "termInfo": {G_TERM: TERM_ANSWER},
    "categoryInfo": {G_CAT: CATEGORY_ANSWER},
}


def _client(recorder: Recorder) -> AtlasClient:
    """The client under test on the recording transport (CL-02)."""
    return AtlasClient(httpx.AsyncClient(base_url="https://atlas.test", transport=recorder.transport()), "tok")


def _params(request: httpx.Request) -> dict[str, str]:
    """The request's query parameters."""
    return dict(request.url.params.multi_items())


def _body(request: httpx.Request) -> Any:  # noqa: ANN401 - the JSON body of the request
    """The request's JSON body."""
    return json.loads(request.content)


def _glossary() -> AtlasGlossary:
    """A glossary body with a name, so ``to_json`` keeps it (DD-309)."""
    return AtlasGlossary(guid=G_LOAN, name="business_glossary")


def _term() -> AtlasGlossaryTerm:
    """A term body anchored to the glossary (its anchor travels as given, CLG-05)."""
    return AtlasGlossaryTerm(guid=G_TERM, name="loan", anchor=AtlasGlossaryHeader(glossary_guid=G_LOAN))


def _category() -> AtlasGlossaryCategory:
    """A category body anchored to the glossary."""
    return AtlasGlossaryCategory(guid=G_CAT, name="Finance", anchor=AtlasGlossaryHeader(glossary_guid=G_LOAN))


def _object_ids() -> list[AtlasRelatedObjectId]:
    """One assigned-entity object id for the assignment trio."""
    return [AtlasRelatedObjectId(guid=G_ENTITY, type_name="sales_table")]


# ---------------------------------------------------------------------------
# The glossary CRUD (CLG-01, CLG-08, CLG-09) and paging (CLG-02)
# ---------------------------------------------------------------------------


@pytest.mark.covers("aurelius_atlas_server_client.client.GlossaryApi.glossaries", rules=["CLG-01", "CLG-02"])
async def test__glossaries_sends_no_paging_parameters_by_default(recorder: Recorder) -> None:
    """Limit -1, offset 0 and sort ASC are the server's defaults: absence carries them (GLS-05)."""
    recorder.answer(200, [GLOSSARY_ANSWER])

    found = await _client(recorder).glossary.glossaries()

    sent = recorder.sent()
    assert sent.method == "GET"
    assert sent.url.path == ROOT
    assert sent.url.params.multi_items() == []
    assert found[0].name == "business_glossary"


@pytest.mark.covers("aurelius_atlas_server_client.client.GlossaryApi.glossaries", rules=["CLG-02"])
async def test__glossaries_sends_every_paging_parameter_the_caller_gives(recorder: Recorder) -> None:
    """A chosen limit (even -1, the default's value), offset and sort travel as parameters."""
    recorder.answer(200, [])

    await _client(recorder).glossary.glossaries(limit=-1, offset=20, sort="DESC")

    assert _params(recorder.sent()) == {"limit": "-1", "offset": "20", "sort": "DESC"}


@pytest.mark.covers("aurelius_atlas_server_client.client.GlossaryApi.create_glossary", rules=["CLG-01"])
async def test__create_glossary_posts_the_body(recorder: Recorder) -> None:
    """``POST ""`` with the model's JSON; the created glossary answers (GLS-02)."""
    recorder.answer(200, GLOSSARY_ANSWER)

    created = await _client(recorder).glossary.create_glossary(_glossary())

    sent = recorder.sent()
    assert sent.method == "POST"
    assert sent.url.path == ROOT
    assert _body(sent)["name"] == "business_glossary"
    assert created.guid == G_LOAN


@pytest.mark.covers("aurelius_atlas_server_client.client.GlossaryApi.glossary", rules=["CLG-01"])
async def test__glossary_reads_one_glossary(recorder: Recorder) -> None:
    """``GET /{guid}`` (GLS-01)."""
    recorder.answer(200, GLOSSARY_ANSWER)

    found = await _client(recorder).glossary.glossary(G_LOAN)

    assert recorder.sent().url.path == f"{ROOT}/{G_LOAN}"
    assert found.guid == G_LOAN


@pytest.mark.covers("aurelius_atlas_server_client.client.GlossaryApi.detailed_glossary", rules=["CLG-01"])
async def test__detailed_glossary_reads_the_ext_info(recorder: Recorder) -> None:
    """``GET /{guid}/detailed``: the glossary with its terms and categories by GUID (GLS-06)."""
    recorder.answer(200, DETAILED_ANSWER)

    found = await _client(recorder).glossary.detailed_glossary(G_LOAN)

    assert recorder.sent().url.path == f"{ROOT}/{G_LOAN}/detailed"
    assert found.term_info is not None
    assert found.term_info[G_TERM].name == "loan"
    assert found.category_info is not None


@pytest.mark.covers("aurelius_atlas_server_client.client.GlossaryApi.glossary_categories", rules=["CLG-02"])
async def test__glossary_categories_is_paged(recorder: Recorder) -> None:
    """``GET /{guid}/categories`` — defaults absent, a set sort travels (GLS-05)."""
    recorder.answer(200, [CATEGORY_ANSWER])

    found = await _client(recorder).glossary.glossary_categories(G_LOAN, limit=2, sort="DESC")

    sent = recorder.sent()
    assert sent.url.path == f"{ROOT}/{G_LOAN}/categories"
    assert _params(sent) == {"limit": "2", "sort": "DESC"}
    assert found[0].name == "Finance"


@pytest.mark.covers("aurelius_atlas_server_client.client.GlossaryApi.glossary_categories_headers", rules=["CLG-02"])
async def test__glossary_categories_headers_is_paged(recorder: Recorder) -> None:
    """``GET /{guid}/categories/headers`` (GLS-05)."""
    recorder.answer(200, [CATEGORY_HEADER_ANSWER])

    found = await _client(recorder).glossary.glossary_categories_headers(G_LOAN, offset=5)

    sent = recorder.sent()
    assert sent.url.path == f"{ROOT}/{G_LOAN}/categories/headers"
    assert _params(sent) == {"offset": "5"}
    assert found[0].category_guid == G_CAT


@pytest.mark.covers("aurelius_atlas_server_client.client.GlossaryApi.glossary_terms", rules=["CLG-02"])
async def test__glossary_terms_is_paged(recorder: Recorder) -> None:
    """``GET /{guid}/terms`` (GTM-06)."""
    recorder.answer(200, [TERM_ANSWER])

    found = await _client(recorder).glossary.glossary_terms(G_LOAN)

    sent = recorder.sent()
    assert sent.url.path == f"{ROOT}/{G_LOAN}/terms"
    assert sent.url.params.multi_items() == []
    assert found[0].name == "loan"


@pytest.mark.covers("aurelius_atlas_server_client.client.GlossaryApi.glossary_terms_headers", rules=["CLG-02"])
async def test__glossary_terms_headers_is_paged(recorder: Recorder) -> None:
    """``GET /{guid}/terms/headers`` (GTM-06)."""
    recorder.answer(200, [HEADER_ANSWER])

    found = await _client(recorder).glossary.glossary_terms_headers(G_LOAN)

    sent = recorder.sent()
    assert sent.url.path == f"{ROOT}/{G_LOAN}/terms/headers"
    assert found[0].term_guid == G_TERM


@pytest.mark.covers("aurelius_atlas_server_client.client.GlossaryApi.update_glossary", rules=["CLG-08"])
async def test__update_glossary_puts_the_body_as_given(recorder: Recorder) -> None:
    """``PUT /{guid}``: a body without the path's guid is the caller's model; the server grafts it (GLS-03)."""
    recorder.answer(200, GLOSSARY_ANSWER)

    await _client(recorder).glossary.update_glossary(G_LOAN, AtlasGlossary(name="renamed"))

    sent = recorder.sent()
    assert sent.method == "PUT"
    assert sent.url.path == f"{ROOT}/{G_LOAN}"
    assert _body(sent)["name"] == "renamed"


@pytest.mark.covers("aurelius_atlas_server_client.client.GlossaryApi.partial_update_glossary", rules=["CLG-03"])
async def test__partial_update_glossary_sends_the_plain_object(recorder: Recorder) -> None:
    """``PUT /{guid}/partial``: the bare JSON object of attribute values (GLS-03)."""
    recorder.answer(200, GLOSSARY_ANSWER)

    await _client(recorder).glossary.partial_update_glossary(G_LOAN, {"name": "renamed", "language": "EN"})

    sent = recorder.sent()
    assert sent.url.path == f"{ROOT}/{G_LOAN}/partial"
    assert _body(sent) == {"name": "renamed", "language": "EN"}


@pytest.mark.covers("aurelius_atlas_server_client.client.GlossaryApi.partial_update_glossary", rules=["CLG-03"])
async def test__partial_update_with_no_fields_is_refused_before_the_wire(recorder: Recorder) -> None:
    """No fields at all is a caller bug: ValueError client-side, nothing sent (NO_PARTIAL_UPDATES)."""
    client = _client(recorder)

    with pytest.raises(ValueError, match="NO_PARTIAL_UPDATES"):
        await client.glossary.partial_update_glossary(G_LOAN, {})
    with pytest.raises(ValueError, match="NO_PARTIAL_UPDATES"):
        await client.glossary.partial_update_term(G_TERM, {})
    with pytest.raises(ValueError, match="NO_PARTIAL_UPDATES"):
        await client.glossary.partial_update_category(G_CAT, {})

    assert recorder.requests == []


@pytest.mark.covers("aurelius_atlas_server_client.client.GlossaryApi.delete_glossary", rules=["CLG-09"])
async def test__delete_glossary_answers_204_with_none(recorder: Recorder) -> None:
    """``DELETE /{guid}`` (GLS-04, CLG-09)."""
    recorder.answer(204)

    assert await _client(recorder).glossary.delete_glossary(G_LOAN) is None

    sent = recorder.sent()
    assert sent.method == "DELETE"
    assert sent.url.path == f"{ROOT}/{G_LOAN}"


# ---------------------------------------------------------------------------
# The terms (CLG-01, CLG-04, CLG-05, CLG-07)
# ---------------------------------------------------------------------------


@pytest.mark.covers("aurelius_atlas_server_client.client.GlossaryApi.term", rules=["CLG-01"])
async def test__term_reads_one_term(recorder: Recorder) -> None:
    """``GET /term/{guid}`` (GTM-01)."""
    recorder.answer(200, TERM_ANSWER)

    found = await _client(recorder).glossary.term(G_TERM)

    assert recorder.sent().url.path == f"{ROOT}/term/{G_TERM}"
    assert found.name == "loan"


@pytest.mark.covers(
    "aurelius_atlas_server_client.client.GlossaryApi.create_term",
    "aurelius_atlas_server_client.client.GlossaryApi.create_category",
    rules=["CLG-05"],
)
async def test__create_term_and_category_send_the_anchor_as_given(recorder: Recorder) -> None:
    """The anchor is not checked client-side: an un-anchored body goes and the server answers (GTM-02)."""
    recorder.answer(200, TERM_ANSWER)
    recorder.answer(200, CATEGORY_ANSWER)

    client = _client(recorder)
    await client.glossary.create_term(AtlasGlossaryTerm(name="unanchored"))
    await client.glossary.create_category(_category())

    term_sent, category_sent = recorder.sent(0), recorder.sent(1)
    assert term_sent.url.path == f"{ROOT}/term"
    assert "anchor" not in _body(term_sent)
    assert category_sent.url.path == f"{ROOT}/category"
    assert _body(category_sent)["anchor"]["glossaryGuid"] == G_LOAN


@pytest.mark.covers(
    "aurelius_atlas_server_client.client.GlossaryApi.create_terms",
    "aurelius_atlas_server_client.client.GlossaryApi.create_categories",
    rules=["CLG-05"],
)
async def test__create_terms_and_categories_post_the_arrays(recorder: Recorder) -> None:
    """``POST /terms`` and ``POST /categories``: JSON arrays of bodies, lists of models back (GTM-02, GCT-02)."""
    recorder.answer(200, [TERM_ANSWER])
    recorder.answer(200, [CATEGORY_ANSWER])

    client = _client(recorder)
    terms = await client.glossary.create_terms([_term()])
    categories = await client.glossary.create_categories([_category()])

    terms_sent, categories_sent = recorder.sent(0), recorder.sent(1)
    assert terms_sent.url.path == f"{ROOT}/terms"
    assert _body(terms_sent)[0]["name"] == "loan"
    assert categories_sent.url.path == f"{ROOT}/categories"
    assert terms[0].guid == G_TERM
    assert categories[0].guid == G_CAT


@pytest.mark.covers("aurelius_atlas_server_client.client.GlossaryApi.update_term", rules=["CLG-08"])
async def test__update_term_puts_the_body_as_given(recorder: Recorder) -> None:
    """``PUT /term/{guid}`` — the path guid is the server's to graft (GTM-04)."""
    recorder.answer(200, TERM_ANSWER)

    await _client(recorder).glossary.update_term(G_TERM, AtlasGlossaryTerm(name="renamed"))

    sent = recorder.sent()
    assert sent.method == "PUT"
    assert sent.url.path == f"{ROOT}/term/{G_TERM}"
    assert _body(sent)["name"] == "renamed"


@pytest.mark.covers("aurelius_atlas_server_client.client.GlossaryApi.partial_update_term", rules=["CLG-03"])
async def test__partial_update_term_sends_the_plain_object(recorder: Recorder) -> None:
    """``PUT /term/{guid}/partial`` (GTM-04)."""
    recorder.answer(200, TERM_ANSWER)

    await _client(recorder).glossary.partial_update_term(G_TERM, {"abbreviation": "LN"})

    sent = recorder.sent()
    assert sent.url.path == f"{ROOT}/term/{G_TERM}/partial"
    assert _body(sent) == {"abbreviation": "LN"}


@pytest.mark.covers("aurelius_atlas_server_client.client.GlossaryApi.delete_term", rules=["CLG-09"])
async def test__delete_term_answers_204_with_none(recorder: Recorder) -> None:
    """``DELETE /term/{guid}`` (GTM-05)."""
    recorder.answer(204)

    assert await _client(recorder).glossary.delete_term(G_TERM) is None

    sent = recorder.sent()
    assert sent.method == "DELETE"
    assert sent.url.path == f"{ROOT}/term/{G_TERM}"


@pytest.mark.covers("aurelius_atlas_server_client.client.GlossaryApi.related_terms", rules=["CLG-07"])
async def test__related_terms_parses_the_keyed_mapping(recorder: Recorder) -> None:
    """The relation names are the keys, the headers the values; no page parameters (GTM-06)."""
    recorder.answer(200, {"seeAlso": [HEADER_ANSWER], "synonyms": []})

    found = await _client(recorder).glossary.related_terms(G_TERM)

    sent = recorder.sent()
    assert sent.url.path == f"{ROOT}/terms/{G_TERM}/related"
    assert sent.url.params.multi_items() == []
    assert found["seeAlso"][0].term_guid == G_TERM
    assert found["synonyms"] == []


# ---------------------------------------------------------------------------
# The term assignments (CLG-02, CLG-04)
# ---------------------------------------------------------------------------


@pytest.mark.covers(
    "aurelius_atlas_server_client.client.GlossaryApi.assign_term",
    "aurelius_atlas_server_client.client.GlossaryApi.remove_term_assignment",
    "aurelius_atlas_server_client.client.GlossaryApi.disassociate_term_assignment",
    rules=["CLG-04"],
)
async def test__the_assignment_trio_sends_the_object_id_array_and_answers_none(
    recorder: Recorder,
) -> None:
    """POST/PUT/DELETE on ``assignedEntities``: the array of ``AtlasRelatedObjectId``, 204 each (GTA-02, GTA-03)."""
    for _ in range(3):
        recorder.answer(204)

    client = _client(recorder)
    ids = _object_ids()
    assert await client.glossary.assign_term(G_TERM, ids) is None
    assert await client.glossary.remove_term_assignment(G_TERM, ids) is None
    assert await client.glossary.disassociate_term_assignment(G_TERM, ids) is None

    assign, remove, disassociate = recorder.sent(0), recorder.sent(1), recorder.sent(2)
    assert (assign.method, remove.method, disassociate.method) == ("POST", "DELETE", "PUT")
    for sent in (assign, remove, disassociate):
        assert sent.url.path == f"{ROOT}/terms/{G_TERM}/assignedEntities"
        assert _body(sent) == [{"guid": G_ENTITY, "typeName": "sales_table"}]


@pytest.mark.covers("aurelius_atlas_server_client.client.GlossaryApi.assigned_entities", rules=["CLG-02"])
async def test__assigned_entities_is_paged(recorder: Recorder) -> None:
    """``GET /terms/{guid}/assignedEntities`` (GTA-01)."""
    recorder.answer(200, ASSIGNED_ANSWER)

    found = await _client(recorder).glossary.assigned_entities(G_TERM, limit=1)

    sent = recorder.sent()
    assert sent.url.path == f"{ROOT}/terms/{G_TERM}/assignedEntities"
    assert _params(sent) == {"limit": "1"}
    assert isinstance(found[0], AtlasRelatedObjectId)
    assert found[0].guid == G_ENTITY


# ---------------------------------------------------------------------------
# The categories (CLG-01, CLG-07)
# ---------------------------------------------------------------------------


@pytest.mark.covers("aurelius_atlas_server_client.client.GlossaryApi.category", rules=["CLG-01"])
async def test__category_reads_one_category(recorder: Recorder) -> None:
    """``GET /category/{guid}`` (GCT-01)."""
    recorder.answer(200, CATEGORY_ANSWER)

    found = await _client(recorder).glossary.category(G_CAT)

    assert recorder.sent().url.path == f"{ROOT}/category/{G_CAT}"
    assert found.name == "Finance"


@pytest.mark.covers("aurelius_atlas_server_client.client.GlossaryApi.related_categories", rules=["CLG-07"])
async def test__related_categories_parses_parent_and_children(recorder: Recorder) -> None:
    """The keys are ``parent`` and ``children``; an absent relation is simply absent (GCT-07)."""
    recorder.answer(200, {"parent": [CATEGORY_HEADER_ANSWER]})

    found = await _client(recorder).glossary.related_categories(G_CAT)

    assert recorder.sent().url.path == f"{ROOT}/category/{G_CAT}/related"
    assert found["parent"][0].category_guid == G_CAT
    assert "children" not in found


@pytest.mark.covers("aurelius_atlas_server_client.client.GlossaryApi.category_terms", rules=["CLG-02"])
async def test__category_terms_is_paged(recorder: Recorder) -> None:
    """``GET /category/{guid}/terms`` (GTM-06)."""
    recorder.answer(200, [HEADER_ANSWER])

    found = await _client(recorder).glossary.category_terms(G_CAT)

    sent = recorder.sent()
    assert sent.url.path == f"{ROOT}/category/{G_CAT}/terms"
    assert sent.url.params.multi_items() == []
    assert found[0].term_guid == G_TERM


@pytest.mark.covers("aurelius_atlas_server_client.client.GlossaryApi.update_category", rules=["CLG-08"])
async def test__update_category_puts_the_body_as_given(recorder: Recorder) -> None:
    """``PUT /category/{guid}`` (GCT-04)."""
    recorder.answer(200, CATEGORY_ANSWER)

    await _client(recorder).glossary.update_category(G_CAT, AtlasGlossaryCategory(name="renamed"))

    sent = recorder.sent()
    assert sent.method == "PUT"
    assert sent.url.path == f"{ROOT}/category/{G_CAT}"
    assert _body(sent)["name"] == "renamed"


@pytest.mark.covers("aurelius_atlas_server_client.client.GlossaryApi.partial_update_category", rules=["CLG-03"])
async def test__partial_update_category_sends_the_plain_object(recorder: Recorder) -> None:
    """``PUT /category/{guid}/partial`` (GCT-05)."""
    recorder.answer(200, CATEGORY_ANSWER)

    await _client(recorder).glossary.partial_update_category(G_CAT, {"shortDescription": "short"})

    sent = recorder.sent()
    assert sent.url.path == f"{ROOT}/category/{G_CAT}/partial"
    assert _body(sent) == {"shortDescription": "short"}


@pytest.mark.covers("aurelius_atlas_server_client.client.GlossaryApi.delete_category", rules=["CLG-09"])
async def test__delete_category_answers_204_with_none(recorder: Recorder) -> None:
    """``DELETE /category/{guid}`` (GCT-06)."""
    recorder.answer(204)

    assert await _client(recorder).glossary.delete_category(G_CAT) is None

    sent = recorder.sent()
    assert sent.method == "DELETE"
    assert sent.url.path == f"{ROOT}/category/{G_CAT}"


# ---------------------------------------------------------------------------
# The file routes (CLG-06, CL-64)
# ---------------------------------------------------------------------------


@pytest.mark.covers("aurelius_atlas_server_client.client.GlossaryApi.import_template", rules=["CLG-06", "CL-64"])
async def test__import_template_returns_bytes_and_content_type(recorder: Recorder) -> None:
    """The download crosses as bytes and its content type — never a parsed model (GIM-06, DD-310)."""
    recorder.handler = lambda _request: httpx.Response(
        200,
        content=b"term_name,synonyms,antonyms\n",
        headers={"content-type": "application/octet-stream"},
    )

    content, content_type = await _client(recorder).glossary.import_template()

    sent = recorder.sent()
    assert sent.method == "GET"
    assert sent.url.path == f"{ROOT}/import/template"
    assert content.startswith(b"term_name,")
    assert "octet-stream" in content_type


@pytest.mark.covers("aurelius_atlas_server_client.client.GlossaryApi.import_data", rules=["CLG-06", "CL-64"])
async def test__import_data_sends_the_file_as_multipart(recorder: Recorder) -> None:
    """The caller's bytes travel as ``multipart/form-data``, part name ``file`` (GIM-01, DD-310)."""
    recorder.answer(200, IMPORT_ANSWER)

    found = await _client(recorder).glossary.import_data("terms.csv", b"term_name,synonyms\n")

    sent = recorder.sent()
    await sent.aread()
    assert sent.method == "POST"
    assert sent.url.path == f"{ROOT}/import"
    assert sent.headers["content-type"].startswith("multipart/form-data")
    assert b'filename="terms.csv"' in sent.content
    assert found.success_import_info_list[0].import_status is not None


# ---------------------------------------------------------------------------
# The failure contract, re-pinned here (CLG-01's shared transport)
# ---------------------------------------------------------------------------


@pytest.mark.covers("aurelius_atlas_server_client.client.GlossaryApi.glossary", rules=["CL-04"])
async def test__a_failed_glossary_read_raises_the_library_error(recorder: Recorder) -> None:
    """A non-2xx answer is an ``AtlasClientError`` with the status and the Atlas error body (CL-04)."""
    recorder.answer(404, ERROR_BODY)

    with pytest.raises(AtlasClientError) as raised:
        await _client(recorder).glossary.glossary(G_LOAN)

    assert raised.value.status_code == 404
    assert raised.value.info is not None
    assert raised.value.info.error_code == "ATLAS-400-00-017"


@pytest.mark.covers("aurelius_atlas_server_client.client.GlossaryApi.create_glossary", rules=["CL-05"])
async def test__an_unreachable_server_propagates_httpxs_own_error(recorder: Recorder) -> None:
    """The client maps nothing: a transport failure is ``httpx``'s (CL-05, DV-80)."""
    recorder.handler = lambda _request: (_ for _ in ()).throw(httpx.ConnectError("refused"))

    with pytest.raises(httpx.ConnectError):
        await _client(recorder).glossary.create_glossary(_glossary())
