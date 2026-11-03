"""``EntityApi`` against the recording transport (CLE-01..CLE-12).

One test per rule cluster of the 8.9 coverage matrix, each naming the client
methods it exercises (ADR 056); the recorder pins method, path, query, and body
for every route of ``routes/entity.py`` (CL-02). A 204 answers every
classification and label write (CLE-05), and the file routes cross as bytes
(CLE-09, DD-310).
"""

import json
from typing import Any

import httpx2 as httpx
import pytest
from aurelius_atlas_model.audit import EntityAuditActionV2
from aurelius_atlas_model.instance import (
    AtlasClassification,
    AtlasEntitiesWithExtInfo,
    AtlasEntity,
    AtlasEntityHeader,
    AtlasEntityHeaders,
    AtlasEntityWithExtInfo,
    ClassificationAssociateRequest,
)
from aurelius_atlas_server_client.client import AtlasClient, AtlasClientError, DeleteType
from server_recorder import Recorder

GUID = "00000000-0000-4000-8000-000000000001"
ROOT = "/api/atlas/v2/entity"
"""The mounted prefix of the route module, as the server answers it (CLE-01)."""

ERROR_BODY = {"errorCode": "ATLAS-400-00-007", "errorMessage": "no such entity"}

ENTITY_ANSWER: dict[str, Any] = {"entity": {"guid": GUID, "typeName": "sales_table"}}
ENTITIES_ANSWER: dict[str, Any] = {"entities": [{"guid": GUID, "typeName": "sales_table"}]}
HEADER_ANSWER: dict[str, Any] = {"guid": GUID, "typeName": "sales_table", "displayText": "sales_table"}
MUTATION_ANSWER: dict[str, Any] = {
    "mutatedEntities": {"CREATE": [{"guid": GUID, "typeName": "sales_table"}]},
    "guidAssignments": {"-1": GUID},
}
CLASSIFICATION_ANSWER: dict[str, Any] = {"typeName": "PII", "entityGuid": GUID}
CLASSIFICATIONS_ANSWER: dict[str, Any] = {"list": [CLASSIFICATION_ANSWER], "totalCount": 1}
AUDIT_ANSWER: list[dict[str, Any]] = [
    {"entityId": GUID, "timestamp": 1_700_000_000_000, "user": "alice", "action": "ENTITY_CREATE"}
]
BULK_HEADERS_ANSWER: dict[str, Any] = {"guidHeaderMap": {GUID: HEADER_ANSWER}}
SET_CLASSIFICATIONS_ANSWER: list[dict[str, Any]] = [
    {"guid": GUID, "classifications": ["PII"]},
    {"guid": "second", "classifications": []},
]


def _client(recorder: Recorder) -> AtlasClient:
    """The client under test on the recording transport (CL-02)."""
    return AtlasClient(httpx.AsyncClient(base_url="https://atlas.test", transport=recorder.transport()), "tok")


def _params(request: httpx.Request) -> dict[str, str]:
    """The request's query parameters, the last value of each."""
    return dict(request.url.params.multi_items())


def _query(request: httpx.Request) -> list[tuple[str, str]]:
    """The request's query parameters in wire order — repeated names kept."""
    return list(request.url.params.multi_items())


def _body(request: httpx.Request) -> Any:  # noqa: ANN401 - the JSON body of the request
    """The request's JSON body."""
    return json.loads(request.content)


def _entity_body() -> AtlasEntityWithExtInfo:
    """A one-entity request body, its entity named so ``to_json`` keeps it (DD-309)."""
    return AtlasEntityWithExtInfo(entity=AtlasEntity(guid=GUID, type_name="sales_table"))


# ---------------------------------------------------------------------------
# The reads (CLE-02, CLE-03, CLE-10, CLE-11)
# ---------------------------------------------------------------------------


@pytest.mark.covers("aurelius_atlas_server_client.client.EntityApi.by_guid", rules=["CLE-01", "CLE-02"])
async def test__by_guid_reads_the_entity_and_the_default_flags_are_absent(recorder: Recorder) -> None:
    """``GET guid/{guid}``; an unset flag travels as its absence (CL-13's default-absence rule)."""
    recorder.answer(200, ENTITY_ANSWER)

    found = await _client(recorder).entity.by_guid(GUID)

    sent = recorder.sent()
    assert sent.method == "GET"
    assert sent.url.path == f"{ROOT}/guid/{GUID}"
    assert sent.url.params.multi_items() == []
    assert found.entity is not None
    assert found.entity.guid == GUID


@pytest.mark.covers("aurelius_atlas_server_client.client.EntityApi.by_guid", rules=["CLE-02"])
async def test__by_guid_sends_the_set_flags(recorder: Recorder) -> None:
    """A set retriever flag renders ``true``, the shape the route's ``flag`` parses (CLE-02)."""
    recorder.answer(200, ENTITY_ANSWER)

    await _client(recorder).entity.by_guid(GUID, min_ext_info=True, ignore_relationships=True)

    assert _params(recorder.sent()) == {"minExtInfo": "true", "ignoreRelationships": "true"}


@pytest.mark.covers("aurelius_atlas_server_client.client.EntityApi.header_by_guid", rules=["CLE-01"])
async def test__header_by_guid_reads_the_header(recorder: Recorder) -> None:
    """``GET guid/{guid}/header`` — the header with its classifications (ERD-07)."""
    recorder.answer(200, HEADER_ANSWER)

    header = await _client(recorder).entity.header_by_guid(GUID)

    assert recorder.sent().url.path == f"{ROOT}/guid/{GUID}/header"
    assert header.guid == GUID


@pytest.mark.covers("aurelius_atlas_server_client.client.EntityApi.by_unique_attributes", rules=["CLE-03", "CLE-02"])
async def test__by_unique_attributes_sends_the_attr_prefixed_parameters(recorder: Recorder) -> None:
    """Each attribute travels as ``attr:<name>=<value>``, as ``routes/entity.py`` reads them (ERD-08)."""
    recorder.answer(200, ENTITY_ANSWER)

    await _client(recorder).entity.by_unique_attributes("sales_table", {"qualifiedName": "s.t", "name": "t"})

    assert _params(recorder.sent()) == {"attr:qualifiedName": "s.t", "attr:name": "t"}


@pytest.mark.covers("aurelius_atlas_server_client.client.EntityApi.header_by_unique_attributes", rules=["CLE-03"])
async def test__header_by_unique_attributes_sends_the_attr_parameters(recorder: Recorder) -> None:
    """``GET uniqueAttribute/type/{t}/header`` on the same parameter shape."""
    recorder.answer(200, HEADER_ANSWER)

    header = await _client(recorder).entity.header_by_unique_attributes("sales_table", {"qualifiedName": "s.t"})

    sent = recorder.sent()
    assert sent.url.path == f"{ROOT}/uniqueAttribute/type/sales_table/header"
    assert _params(sent) == {"attr:qualifiedName": "s.t"}
    assert header.guid == GUID


@pytest.mark.covers(
    "aurelius_atlas_server_client.client.EntityApi.entities_by_unique_attributes", rules=["CLE-03", "CLE-02"]
)
async def test__entities_by_unique_attributes_numbers_the_sets_1_based(recorder: Recorder) -> None:
    """The bulk form renders ``attr_<n>:<name>``, 1-based, in the order given (DV-19)."""
    recorder.answer(200, ENTITIES_ANSWER)

    await _client(recorder).entity.entities_by_unique_attributes(
        "sales_table", [{"name": "a"}, {"name": "b"}], min_ext_info=True
    )

    sent = recorder.sent()
    assert sent.url.path == f"{ROOT}/bulk/uniqueAttribute/type/sales_table"
    assert _query(sent) == [("attr_1:name", "a"), ("attr_2:name", "b"), ("minExtInfo", "true")]


@pytest.mark.covers("aurelius_atlas_server_client.client.EntityApi.by_guids", rules=["CLE-02"])
async def test__by_guids_repeats_the_guid_parameter_in_order(recorder: Recorder) -> None:
    """``GET bulk?guid=a&guid=b`` — the repeated parameter, its order kept (ERD-01)."""
    recorder.answer(200, ENTITIES_ANSWER)

    await _client(recorder).entity.by_guids([GUID, "00000000-0000-4000-8000-000000000002"])

    sent = recorder.sent()
    assert sent.url.path == f"{ROOT}/bulk"
    assert _query(sent) == [("guid", GUID), ("guid", "00000000-0000-4000-8000-000000000002")]


@pytest.mark.covers("aurelius_atlas_server_client.client.EntityApi.audit_events", rules=["CLE-10"])
async def test__audit_events_sends_only_the_parameters_set(recorder: Recorder) -> None:
    """The defaults (count 100, offset -1) stay the server's: an unset parameter is absent (AUD-06)."""
    recorder.answer(200, AUDIT_ANSWER)

    events = await _client(recorder).entity.audit_events(GUID, action=EntityAuditActionV2.ENTITY_CREATE)

    sent = recorder.sent()
    assert sent.url.path == f"{ROOT}/{GUID}/audit"
    assert _params(sent) == {"auditAction": "ENTITY_CREATE"}
    assert events[0].action is EntityAuditActionV2.ENTITY_CREATE


@pytest.mark.covers("aurelius_atlas_server_client.client.EntityApi.audit_events", rules=["CLE-10"])
async def test__audit_events_sends_a_count_of_zero_as_a_choice(recorder: Recorder) -> None:
    """A zero ``count`` or ``offset`` is a chosen value, not a default — unlike ``_present`` it travels."""
    recorder.answer(200, AUDIT_ANSWER)

    await _client(recorder).entity.audit_events(
        GUID, start_key="k", count=0, offset=0, sort_by="timestamp", sort_order="DESC"
    )

    assert _params(recorder.sent()) == {
        "startKey": "k",
        "count": "0",
        "offset": "0",
        "sortBy": "timestamp",
        "sortOrder": "DESC",
    }


@pytest.mark.covers("aurelius_atlas_server_client.client.EntityApi.changed_classifications", rules=["CLE-11"])
async def test__changed_classifications_sends_only_the_start_time(recorder: Recorder) -> None:
    """``GET bulk/headers?tagUpdateStartTime=…``; no end time — the server uses its own clock (CAU-07)."""
    recorder.answer(200, BULK_HEADERS_ANSWER)

    headers = await _client(recorder).entity.changed_classifications(1_700_000_000_000)

    sent = recorder.sent()
    assert sent.url.path == f"{ROOT}/bulk/headers"
    assert _params(sent) == {"tagUpdateStartTime": "1700000000000"}
    assert headers.guid_header_map is not None
    assert GUID in headers.guid_header_map


# ---------------------------------------------------------------------------
# The writes (CLE-04)
# ---------------------------------------------------------------------------


@pytest.mark.covers("aurelius_atlas_server_client.client.EntityApi.create_or_update", rules=["CLE-01"])
async def test__create_or_update_posts_the_entity_body(recorder: Recorder) -> None:
    """``POST /v2/entity`` with the model's JSON body; the mutation response answers (EWR-02)."""
    recorder.answer(200, MUTATION_ANSWER)

    response = await _client(recorder).entity.create_or_update(_entity_body())

    sent = recorder.sent()
    assert sent.method == "POST"
    assert sent.url.path == ROOT
    assert _body(sent)["entity"]["guid"] == GUID
    created = response.get_created_entities()
    assert created is not None
    assert created[0].guid == GUID


@pytest.mark.covers("aurelius_atlas_server_client.client.EntityApi.create_or_update_bulk", rules=["CLE-01"])
async def test__create_or_update_bulk_posts_the_entities_body(recorder: Recorder) -> None:
    """``POST bulk`` with ``AtlasEntitiesWithExtInfo`` (EWR-02)."""
    recorder.answer(200, MUTATION_ANSWER)

    await _client(recorder).entity.create_or_update_bulk(
        AtlasEntitiesWithExtInfo(entities=[AtlasEntity(guid=GUID, type_name="sales_table")])
    )

    sent = recorder.sent()
    assert sent.url.path == f"{ROOT}/bulk"
    assert _body(sent)["entities"][0]["guid"] == GUID


@pytest.mark.covers("aurelius_atlas_server_client.client.EntityApi.partial_update_attribute", rules=["CLE-01"])
async def test__partial_update_attribute_sends_the_value_as_the_body(recorder: Recorder) -> None:
    """``PUT guid/{guid}?name=…`` — the body is the bare JSON value, as EWR-15 reads it."""
    recorder.answer(200, MUTATION_ANSWER)

    await _client(recorder).entity.partial_update_attribute(GUID, "description", "new text")

    sent = recorder.sent()
    assert sent.method == "PUT"
    assert sent.url.path == f"{ROOT}/guid/{GUID}"
    assert _params(sent) == {"name": "description"}
    assert json.loads(sent.content) == "new text"


@pytest.mark.covers(
    "aurelius_atlas_server_client.client.EntityApi.partial_update_by_unique_attributes", rules=["CLE-03"]
)
async def test__partial_update_by_unique_attributes_puts_the_entity(recorder: Recorder) -> None:
    """``PUT uniqueAttribute/type/{t}`` with the ``attr:`` parameters and the entity body (EWR-14)."""
    recorder.answer(200, MUTATION_ANSWER)

    await _client(recorder).entity.partial_update_by_unique_attributes(
        "sales_table", {"qualifiedName": "s.t"}, _entity_body()
    )

    sent = recorder.sent()
    assert sent.method == "PUT"
    assert sent.url.path == f"{ROOT}/uniqueAttribute/type/sales_table"
    assert _params(sent) == {"attr:qualifiedName": "s.t"}
    assert _body(sent)["entity"]["guid"] == GUID


@pytest.mark.covers("aurelius_atlas_server_client.client.EntityApi.delete_by_guid", rules=["CLE-04"])
async def test__delete_by_guid_sends_no_delete_type_by_default(recorder: Recorder) -> None:
    """The client has no default of its own: an absent parameter lets the server apply its setting (EDL-04)."""
    recorder.answer(200, MUTATION_ANSWER)

    await _client(recorder).entity.delete_by_guid(GUID)

    sent = recorder.sent()
    assert sent.method == "DELETE"
    assert sent.url.path == f"{ROOT}/guid/{GUID}"
    assert sent.url.params.multi_items() == []


@pytest.mark.covers("aurelius_atlas_server_client.client.EntityApi.delete_by_guid", rules=["CLE-04"])
async def test__delete_by_guid_sends_a_hard_delete_type(recorder: Recorder) -> None:
    """A given ``delete_type`` travels as the ``deleteType`` parameter (EDL-04, DD-311)."""
    recorder.answer(200, MUTATION_ANSWER)

    await _client(recorder).entity.delete_by_guid(GUID, delete_type=DeleteType.HARD)

    assert _params(recorder.sent()) == {"deleteType": "HARD"}


@pytest.mark.covers("aurelius_atlas_server_client.client.EntityApi.delete_by_guids", rules=["CLE-04"])
async def test__delete_by_guids_repeats_the_guid_parameter(recorder: Recorder) -> None:
    """``DELETE bulk?guid=…&deleteType=SOFT`` (EDL-01)."""
    recorder.answer(200, MUTATION_ANSWER)

    await _client(recorder).entity.delete_by_guids([GUID], delete_type=DeleteType.SOFT)

    assert _query(recorder.sent()) == [("guid", GUID), ("deleteType", "SOFT")]


@pytest.mark.covers(
    "aurelius_atlas_server_client.client.EntityApi.delete_by_unique_attributes", rules=["CLE-03", "CLE-04"]
)
async def test__delete_by_unique_attributes_sends_the_attr_parameters(recorder: Recorder) -> None:
    """``DELETE uniqueAttribute/type/{t}`` on the ``attr:`` parameters; the values are not checked (EDL-02)."""
    recorder.answer(200, MUTATION_ANSWER)

    await _client(recorder).entity.delete_by_unique_attributes("sales_table", {"qualifiedName": "s.t"})

    sent = recorder.sent()
    assert sent.method == "DELETE"
    assert sent.url.path == f"{ROOT}/uniqueAttribute/type/sales_table"
    assert _params(sent) == {"attr:qualifiedName": "s.t"}


# ---------------------------------------------------------------------------
# The classifications (CLE-05, CLE-08)
# ---------------------------------------------------------------------------


@pytest.mark.covers("aurelius_atlas_server_client.client.EntityApi.get_classification", rules=["CLE-01"])
async def test__get_classification_reads_one_classification(recorder: Recorder) -> None:
    """``GET guid/{g}/classification/{c}`` (CLS-03)."""
    recorder.answer(200, CLASSIFICATION_ANSWER)

    found = await _client(recorder).entity.get_classification(GUID, "PII")

    assert recorder.sent().url.path == f"{ROOT}/guid/{GUID}/classification/PII"
    assert found.type_name == "PII"


@pytest.mark.covers("aurelius_atlas_server_client.client.EntityApi.get_classifications", rules=["CLE-01"])
async def test__get_classifications_reads_the_plist(recorder: Recorder) -> None:
    """``GET guid/{g}/classifications`` — the ``PList`` wrapper parsed (CLS-03)."""
    recorder.answer(200, CLASSIFICATIONS_ANSWER)

    found = await _client(recorder).entity.get_classifications(GUID)

    assert recorder.sent().url.path == f"{ROOT}/guid/{GUID}/classifications"
    assert found.list is not None
    assert found.list[0].type_name == "PII"


def _classifications() -> list[AtlasClassification]:
    """One classification body for a write."""
    return [AtlasClassification(type_name="PII")]


@pytest.mark.covers(
    "aurelius_atlas_server_client.client.EntityApi.add_classifications",
    "aurelius_atlas_server_client.client.EntityApi.update_classifications",
    rules=["CLE-05"],
)
async def test__classification_writes_post_and_put_the_array_and_answer_none(recorder: Recorder) -> None:
    """The body is a JSON array; a 204 answers and the client returns None (CLE-05)."""
    recorder.answer(204)
    recorder.answer(204)

    client = _client(recorder)
    assert await client.entity.add_classifications(GUID, _classifications()) is None
    assert await client.entity.update_classifications(GUID, _classifications()) is None

    add, update = recorder.sent(0), recorder.sent(1)
    assert (add.method, update.method) == ("POST", "PUT")
    assert add.url.path == update.url.path == f"{ROOT}/guid/{GUID}/classifications"
    assert [item["typeName"] for item in _body(add)] == ["PII"]


@pytest.mark.covers(
    "aurelius_atlas_server_client.client.EntityApi.add_classifications_by_unique_attributes",
    "aurelius_atlas_server_client.client.EntityApi.update_classifications_by_unique_attributes",
    rules=["CLE-03", "CLE-05"],
)
async def test__classification_writes_by_unique_attributes_carry_the_attr_parameters(
    recorder: Recorder,
) -> None:
    """The unique-attribute form of each write, on the ``attr:`` parameters (CLS-06)."""
    recorder.answer(204)
    recorder.answer(204)

    client = _client(recorder)
    await client.entity.add_classifications_by_unique_attributes("sales_table", {"name": "t"}, _classifications())
    await client.entity.update_classifications_by_unique_attributes("sales_table", {"name": "t"}, _classifications())

    add, update = recorder.sent(0), recorder.sent(1)
    assert (add.method, update.method) == ("POST", "PUT")
    for sent in (add, update):
        assert sent.url.path == f"{ROOT}/uniqueAttribute/type/sales_table/classifications"
        assert _params(sent) == {"attr:name": "t"}


@pytest.mark.covers("aurelius_atlas_server_client.client.EntityApi.delete_classification", rules=["CLE-05"])
async def test__delete_classification_sends_the_optional_associated_guid(recorder: Recorder) -> None:
    """``DELETE guid/{g}/classification/{c}``; the associated guid travels only when given."""
    recorder.answer(204)
    recorder.answer(204)

    client = _client(recorder)
    await client.entity.delete_classification(GUID, "PII")
    await client.entity.delete_classification(GUID, "PII", associated_entity_guid="other-guid")

    plain, associated = recorder.sent(0), recorder.sent(1)
    assert plain.method == "DELETE"
    assert plain.url.path == f"{ROOT}/guid/{GUID}/classification/PII"
    assert plain.url.params.multi_items() == []
    assert _params(associated) == {"associatedEntityGuid": "other-guid"}


@pytest.mark.covers(
    "aurelius_atlas_server_client.client.EntityApi.delete_classification_by_unique_attributes",
    rules=["CLE-03", "CLE-05"],
)
async def test__delete_classification_by_unique_attributes_sends_the_attr_parameters(
    recorder: Recorder,
) -> None:
    """``DELETE uniqueAttribute/type/{t}/classification/{c}`` (CLS-06)."""
    recorder.answer(204)

    await _client(recorder).entity.delete_classification_by_unique_attributes("sales_table", {"name": "t"}, "PII")

    sent = recorder.sent()
    assert sent.url.path == f"{ROOT}/uniqueAttribute/type/sales_table/classification/PII"
    assert _params(sent) == {"attr:name": "t"}


@pytest.mark.covers("aurelius_atlas_server_client.client.EntityApi.associate_classification", rules=["CLE-01"])
async def test__associate_classification_posts_the_associate_request(recorder: Recorder) -> None:
    """``POST bulk/classification`` — one classification, many entities, by GUID (CLS-07). Answers 204."""
    recorder.answer(204)

    await _client(recorder).entity.associate_classification(
        ClassificationAssociateRequest(classification=AtlasClassification(type_name="PII"), entity_guids=[GUID])
    )

    sent = recorder.sent()
    assert sent.method == "POST"
    assert sent.url.path == f"{ROOT}/bulk/classification"
    body = _body(sent)
    assert body["classification"]["typeName"] == "PII"
    assert body["entityGuids"] == [GUID]


@pytest.mark.covers("aurelius_atlas_server_client.client.EntityApi.set_classifications", rules=["CLE-08"])
async def test__set_classifications_returns_the_parsed_array_never_reordered(recorder: Recorder) -> None:
    """The DV-36 text: a JSON array of per-guid summaries, returned parsed, in the answer's order."""
    recorder.answer(200, SET_CLASSIFICATIONS_ANSWER)

    summary = await _client(recorder).entity.set_classifications(
        AtlasEntityHeaders(guid_header_map={GUID: AtlasEntityHeader(guid=GUID, type_name="sales_table")})
    )

    sent = recorder.sent()
    assert sent.url.path == f"{ROOT}/bulk/setClassifications"
    assert _body(sent)["guidHeaderMap"][GUID]["guid"] == GUID
    assert summary == SET_CLASSIFICATIONS_ANSWER


# ---------------------------------------------------------------------------
# The business metadata (CLE-07) and the file routes (CLE-09)
# ---------------------------------------------------------------------------


@pytest.mark.covers(
    "aurelius_atlas_server_client.client.EntityApi.add_or_update_business_metadata",
    "aurelius_atlas_server_client.client.EntityApi.remove_business_metadata",
    rules=["CLE-07"],
)
async def test__business_metadata_writes_wrap_the_body_by_metadata_name(
    recorder: Recorder,
) -> None:
    """The pair without a name sends ``{<bm>: {...}}``; ``isOverwrite`` travels only when set (BMD-01)."""
    recorder.answer(204)
    recorder.answer(204)

    client = _client(recorder)
    await client.entity.add_or_update_business_metadata(GUID, {"Customer": {"contact": "alice"}}, is_overwrite=True)
    await client.entity.remove_business_metadata(GUID, {"Customer": None})

    add, remove = recorder.sent(0), recorder.sent(1)
    assert (add.method, remove.method) == ("POST", "DELETE")
    assert add.url.path == remove.url.path == f"{ROOT}/guid/{GUID}/businessmetadata"
    assert _params(add) == {"isOverwrite": "true"}
    assert _body(add) == {"Customer": {"contact": "alice"}}
    assert _body(remove) == {"Customer": None}
    assert remove.url.params.multi_items() == []


@pytest.mark.covers(
    "aurelius_atlas_server_client.client.EntityApi.add_or_update_business_metadata_of",
    "aurelius_atlas_server_client.client.EntityApi.remove_business_metadata_of",
    rules=["CLE-07"],
)
async def test__business_metadata_writes_of_one_name_send_a_plain_object(recorder: Recorder) -> None:
    """The pair with a ``bm_name`` sends the plain attribute object — the route wraps it (BMD-03, BMD-05)."""
    recorder.answer(204)
    recorder.answer(204)

    client = _client(recorder)
    await client.entity.add_or_update_business_metadata_of(GUID, "Customer", {"contact": "alice"})
    await client.entity.remove_business_metadata_of(GUID, "Customer", {"contact": None})

    add, remove = recorder.sent(0), recorder.sent(1)
    assert (add.method, remove.method) == ("POST", "DELETE")
    for sent in (add, remove):
        assert sent.url.path == f"{ROOT}/guid/{GUID}/businessmetadata/Customer"
    assert _body(add) == {"contact": "alice"}
    assert _body(remove) == {"contact": None}


@pytest.mark.covers(
    "aurelius_atlas_server_client.client.EntityApi.business_metadata_template", rules=["CLE-09", "CL-64"]
)
async def test__business_metadata_template_returns_bytes_and_content_type(recorder: Recorder) -> None:
    """The download crosses as bytes and its content type — never a parsed model (BMI-01, DD-310)."""
    recorder.handler = lambda _request: httpx.Response(
        200,
        content=b"qualifiedName,term_name,description\n",
        headers={"content-type": "application/octet-stream"},
    )

    content, content_type = await _client(recorder).entity.business_metadata_template()

    sent = recorder.sent()
    assert sent.method == "GET"
    assert sent.url.path == f"{ROOT}/businessmetadata/import/template"
    assert content.startswith(b"qualifiedName,")
    assert "octet-stream" in content_type


@pytest.mark.covers("aurelius_atlas_server_client.client.EntityApi.import_business_metadata", rules=["CLE-09", "CL-64"])
async def test__import_business_metadata_sends_the_file_as_multipart(recorder: Recorder) -> None:
    """The caller's bytes travel as ``multipart/form-data``, part name ``file`` (BMI-02, DD-310)."""
    recorder.answer(200, {"successImportInfoList": [{"childObjectName": "s.t", "importStatus": "SUCCESS"}]})

    found = await _client(recorder).entity.import_business_metadata("bm.csv", b"qualifiedName,term_name\n")

    sent = recorder.sent()
    await sent.aread()
    assert sent.method == "POST"
    assert sent.url.path == f"{ROOT}/businessmetadata/import"
    assert sent.headers["content-type"].startswith("multipart/form-data")
    assert b'filename="bm.csv"' in sent.content
    assert found.success_import_info_list[0].import_status is not None


# ---------------------------------------------------------------------------
# The labels (CLE-06) — all three verbs in one test so a swap fails loudly
# ---------------------------------------------------------------------------


@pytest.mark.covers(
    "aurelius_atlas_server_client.client.EntityApi.set_labels",
    "aurelius_atlas_server_client.client.EntityApi.add_labels",
    "aurelius_atlas_server_client.client.EntityApi.remove_labels",
    rules=["CLE-06", "CLE-05"],
)
async def test__the_label_verbs_are_the_servers_mapping(recorder: Recorder) -> None:
    """POST sets, PUT adds, DELETE removes (LBL-01..LBL-04) — not intuition; every write answers 204."""
    for _ in range(3):
        recorder.answer(204)

    client = _client(recorder)
    assert await client.entity.set_labels(GUID, ["gold"]) is None
    assert await client.entity.add_labels(GUID, ["gold"]) is None
    assert await client.entity.remove_labels(GUID, ["gold"]) is None

    set_labels, add_labels, remove_labels = recorder.sent(0), recorder.sent(1), recorder.sent(2)
    assert (set_labels.method, add_labels.method, remove_labels.method) == ("POST", "PUT", "DELETE")
    for sent in (set_labels, add_labels, remove_labels):
        assert sent.url.path == f"{ROOT}/guid/{GUID}/labels"
        assert _body(sent) == ["gold"]


@pytest.mark.covers(
    "aurelius_atlas_server_client.client.EntityApi.set_labels_by_unique_attributes",
    "aurelius_atlas_server_client.client.EntityApi.add_labels_by_unique_attributes",
    "aurelius_atlas_server_client.client.EntityApi.remove_labels_by_unique_attributes",
    rules=["CLE-03", "CLE-06"],
)
async def test__the_label_verbs_by_unique_attributes_carry_the_attr_parameters(
    recorder: Recorder,
) -> None:
    """The same three verbs on the unique-attribute form (LBL-01, CLE-03)."""
    for _ in range(3):
        recorder.answer(204)

    client = _client(recorder)
    await client.entity.set_labels_by_unique_attributes("sales_table", {"name": "t"}, ["gold"])
    await client.entity.add_labels_by_unique_attributes("sales_table", {"name": "t"}, ["gold"])
    await client.entity.remove_labels_by_unique_attributes("sales_table", {"name": "t"}, ["gold"])

    for index, verb in enumerate(("POST", "PUT", "DELETE")):
        sent = recorder.sent(index)
        assert sent.method == verb
        assert sent.url.path == f"{ROOT}/uniqueAttribute/type/sales_table/labels"
        assert _params(sent) == {"attr:name": "t"}


# ---------------------------------------------------------------------------
# The failure contract, re-pinned here (CLE-12)
# ---------------------------------------------------------------------------


@pytest.mark.covers("aurelius_atlas_server_client.client.EntityApi.by_guid", rules=["CLE-12", "CL-04"])
async def test__a_failed_entity_read_raises_the_library_error(recorder: Recorder) -> None:
    """A non-2xx answer is an ``AtlasClientError`` with the status and the Atlas error body (CLE-12)."""
    recorder.answer(404, ERROR_BODY)

    with pytest.raises(AtlasClientError) as raised:
        await _client(recorder).entity.by_guid(GUID)

    assert raised.value.status_code == 404
    assert raised.value.info is not None
    assert raised.value.info.error_code == "ATLAS-400-00-007"


@pytest.mark.covers("aurelius_atlas_server_client.client.EntityApi.create_or_update", rules=["CLE-12", "CL-05"])
async def test__an_unreachable_server_propagates_httpxs_own_error(recorder: Recorder) -> None:
    """The client maps nothing: a transport failure is ``httpx``'s (CLE-12, DV-80)."""
    recorder.handler = lambda _request: (_ for _ in ()).throw(httpx.ConnectError("refused"))

    with pytest.raises(httpx.ConnectError):
        await _client(recorder).entity.create_or_update(_entity_body())
