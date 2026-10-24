"""Unit tests for the flattening, the fixed rules, and the proxy behaviour (LM-02..LM-07)."""

import json
from collections.abc import Callable
from typing import Any
from uuid import UUID

import httpx2 as httpx
import pytest
from aurelius_atlas_data2model_client.models import RulesDef
from aurelius_atlas_lineage_model.lineage import (
    LINEAGE_RULES,
    PROCESS_TYPES,
    LineageInfo,
    flatten_relations,
)
from fake_upstream import FakeUpstream

# The graph's entity guids: the fixed UUIDs the fixtures of 8.2 use (DV-27).
E_IN = UUID("00000000-0000-4000-8000-000000000001")
P_LOAD = UUID("00000000-0000-4000-8000-000000000002")
E_OUT = UUID("00000000-0000-4000-8000-000000000003")

# The lineage body the flattening tests share: a dataset, a process, a dataset,
# joined by two relations — the shape Atlas's v2/lineage answers.
LINEAGE: dict[str, Any] = {
    "baseEntityGuid": str(E_IN),
    "lineageDepth": 3,
    "lineageDirection": "BOTH",
    "guidEntityMap": {
        str(E_IN): {"guid": str(E_IN), "typeName": "kafka_topic", "displayText": "Ingest Topic"},
        str(P_LOAD): {"guid": str(P_LOAD), "typeName": "m4i_generic_process", "displayText": "Load Job"},
        str(E_OUT): {"guid": str(E_OUT), "typeName": "hive_table", "displayText": "Sales Table"},
    },
    "relations": [
        {"fromEntityId": str(E_IN), "relationshipId": "rel-1", "toEntityId": str(P_LOAD)},
        {"fromEntityId": str(P_LOAD), "relationshipId": "rel-2", "toEntityId": str(E_OUT)},
    ],
}

ROW_KEYS = [
    "id",
    "from_entity_id",
    "from_entity_name",
    "from_entity_type",
    "from_process_id",
    "from_process_name",
    "from_process_type",
    "to_entity_id",
    "to_entity_name",
    "to_entity_type",
    "to_process_id",
    "to_process_name",
    "to_process_type",
]


def _bearer(token: str) -> dict[str, str]:
    """The authorization header for a bearer token."""
    return {"authorization": f"Bearer {token}"}


def _info(payload: dict[str, Any]) -> LineageInfo:
    """Parse a lineage body as the app's model does."""
    return LineageInfo.model_validate(payload)


# ---------------------------------------------------------------------------
# LM-02 — the flattening
# ---------------------------------------------------------------------------


@pytest.mark.covers("aurelius_atlas_lineage_model.lineage.flatten_relations", rules=["LM-02"])
def test__a_process_endpoint_fills_the_process_slots() -> None:
    """An endpoint whose type is a process fills its *_process_* slots; the entity slots are null."""
    row = flatten_relations(_info(LINEAGE))[0]
    assert row["id"] == "rel-1"
    assert row["to_process_id"] == P_LOAD
    assert row["to_process_name"] == "Load Job"
    assert row["to_process_type"] == "m4i_generic_process"
    assert row["to_entity_id"] is None
    assert row["to_entity_name"] is None
    assert row["to_entity_type"] is None


@pytest.mark.covers("aurelius_atlas_lineage_model.lineage.flatten_relations", rules=["LM-02"])
def test__an_entity_endpoint_fills_the_entity_slots() -> None:
    """An endpoint of any other type fills its *_entity_* slots; the process slots are null."""
    row = flatten_relations(_info(LINEAGE))[0]
    assert row["from_entity_id"] == E_IN
    assert row["from_entity_name"] == "Ingest Topic"
    assert row["from_entity_type"] == "kafka_topic"
    assert row["from_process_id"] is None
    assert row["from_process_name"] is None
    assert row["from_process_type"] is None


@pytest.mark.covers("aurelius_atlas_lineage_model.lineage.flatten_relations", rules=["LM-02"])
def test__the_rows_are_twelve_columns_in_upstream_order() -> None:
    """One row per relation, in upstream order: the id plus the 12 columns the rules read."""
    rows = flatten_relations(_info(LINEAGE))
    assert [row["id"] for row in rows] == ["rel-1", "rel-2"]
    assert all(set(row) == set(ROW_KEYS) and len(row) == 13 for row in rows)
    assert rows[1]["from_process_id"] == P_LOAD
    assert rows[1]["to_entity_id"] == E_OUT


@pytest.mark.covers("aurelius_atlas_lineage_model.lineage.flatten_relations", rules=["LM-03"])
def test__the_process_family_is_the_legacy_list() -> None:
    """The seven m4i_*_process type names, verbatim from the legacy's process_types."""
    assert (
        frozenset(
            {
                "m4i_generic_process",
                "m4i_api_operation_process",
                "m4i_connector_process",
                "m4i_ingress_controller_process",
                "m4i_ingress_object_process",
                "m4i_kubernetes_service_process",
                "m4i_microservice_process",
            }
        )
        == PROCESS_TYPES
    )


# ---------------------------------------------------------------------------
# LM-04 — the extract body and the forwarded token
# ---------------------------------------------------------------------------


@pytest.mark.covers(
    "aurelius_atlas_lineage_model.app.create_app",
    rules=["LM-04", "CL-03", "CL-07", "CL-50"],
)
async def test__the_extract_request_carries_the_rows_and_fixed_rules(
    client: httpx.AsyncClient,
    token: Callable[..., str],
    upstream: FakeUpstream,
) -> None:
    """The flattening's rows plus the fixed rules document, POSTed to data2model/extract.

    The body is the client library's ``ExtractionRequest`` (CL-07), and the
    answer the route returns is the library's ``ExtractionResponse`` dumped
    verbatim (CL-50).
    """
    upstream.handler = lambda request: (
        upstream.json(200, LINEAGE)
        if request.url.path == f"/v2/lineage/{E_IN}"
        else upstream.json(200, {"model": "{}", "metadata": []})
    )

    response = await client.get("/", params={"guid": str(E_IN)}, headers=_bearer(token()))

    assert response.status_code == 200
    extract = upstream.of("/extract")
    assert len(extract) == 1
    sent = json.loads(extract[0].content)
    # The client serialises the rules through the contract model, which fills in
    # the defaults the 8.2 fixture left out (empty strings). Compared as parsed
    # rules so the assertion is about semantics, not key presence.
    assert RulesDef.model_validate(sent["rules"]) == RulesDef.model_validate(LINEAGE_RULES)
    assert [row["id"] for row in sent["data"]] == ["rel-1", "rel-2"]


@pytest.mark.covers("aurelius_atlas_lineage_model.app.create_app", rules=["LM-04"])
async def test__both_upstream_calls_carry_the_callers_token(
    client: httpx.AsyncClient,
    token: Callable[..., str],
    upstream: FakeUpstream,
) -> None:
    """The fetch and the extract run with the caller's raw bearer token (the legacy's forwarding)."""
    caller = token()  # the caller's own token, minted for this app's audience
    upstream.handler = lambda request: (
        upstream.json(200, LINEAGE)
        if request.url.path == f"/v2/lineage/{E_IN}"
        else upstream.json(200, {"model": "{}", "metadata": []})
    )

    response = await client.get("/", params={"guid": str(E_IN)}, headers=_bearer(caller))

    assert response.status_code == 200
    assert upstream.of(f"/v2/lineage/{E_IN}")[0].headers["authorization"] == f"Bearer {caller}"
    assert upstream.of("/extract")[0].headers["authorization"] == f"Bearer {caller}"


@pytest.mark.covers("aurelius_atlas_lineage_model.app.create_app", rules=["LM-01"])
async def test__the_fetch_carries_depth_and_direction(
    client: httpx.AsyncClient,
    token: Callable[..., str],
    upstream: FakeUpstream,
) -> None:
    """GET /v2/lineage/{guid}?depth&direction — the legacy's upstream call (LM-01, LM-04)."""
    upstream.handler = lambda request: (
        upstream.json(200, LINEAGE)
        if request.url.path == f"/v2/lineage/{E_IN}"
        else upstream.json(200, {"model": "{}", "metadata": []})
    )

    response = await client.get(
        "/", params={"guid": str(E_IN), "depth": 5, "direction": "INPUT"}, headers=_bearer(token())
    )

    assert response.status_code == 200
    fetch = upstream.of(f"/v2/lineage/{E_IN}")[0]
    assert dict(httpx.URL(str(fetch.url)).params) == {"depth": "5", "direction": "INPUT"}


# ---------------------------------------------------------------------------
# LM-05..LM-07 — the upstream statuses
# ---------------------------------------------------------------------------


def _answer_lineage(payload: dict[str, Any]) -> Callable[[httpx.Request], httpx.Response]:
    """A handler answering the fetch with the payload and the extract with a model body."""

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == f"/v2/lineage/{E_IN}":
            return FakeUpstream.json(200, payload)
        return FakeUpstream.json(200, {"model": "{}", "metadata": []})

    return handler


@pytest.mark.covers("aurelius_atlas_lineage_model.app.create_app", rules=["LM-05"])
async def test__an_unknown_guid_is_204(
    client: httpx.AsyncClient,
    token: Callable[..., str],
    upstream: FakeUpstream,
) -> None:
    """The upstream's 404 (no lineage for the guid) is answered 204, empty (the legacy's contract)."""
    upstream.handler = lambda _request: httpx.Response(404)

    response = await client.get("/", params={"guid": "00000000-0000-4000-8000-000000000009"}, headers=_bearer(token()))

    assert response.status_code == 204
    assert response.content == b""
    assert upstream.of("/extract") == []


@pytest.mark.covers("aurelius_atlas_lineage_model.app.create_app", rules=["LM-05"])
async def test__an_upstream_bad_request_is_400(
    client: httpx.AsyncClient,
    token: Callable[..., str],
    upstream: FakeUpstream,
) -> None:
    """The upstream's 400 (it rejected the request) travels as a 400 with the Atlas error body."""
    upstream.handler = lambda _request: httpx.Response(400)

    response = await client.get("/", params={"guid": str(E_IN)}, headers=_bearer(token()))

    assert response.status_code == 400
    assert response.json()["errorCode"] == "ATLAS-400-00-029"


@pytest.mark.covers("aurelius_atlas_lineage_model.app.create_app", rules=["LM-06"])
async def test__a_lineage_without_relations_is_204(
    client: httpx.AsyncClient,
    token: Callable[..., str],
    upstream: FakeUpstream,
) -> None:
    """A lineage whose relations are empty is answered 204 — no extract call (the legacy's guard)."""
    upstream.handler = _answer_lineage({"guidEntityMap": {}, "relations": []})

    response = await client.get("/", params={"guid": str(E_IN)}, headers=_bearer(token()))

    assert response.status_code == 204
    assert response.content == b""
    assert upstream.of("/extract") == []


@pytest.mark.covers("aurelius_atlas_lineage_model.app.create_app", rules=["LM-07"])
async def test__an_upstream_server_failure_is_502(
    client: httpx.AsyncClient,
    token: Callable[..., str],
    upstream: FakeUpstream,
) -> None:
    """A lineage 5xx is a gateway failure: 502 with the Atlas error body (DV-22)."""
    upstream.handler = lambda _request: httpx.Response(503)

    response = await client.get("/", params={"guid": str(E_IN)}, headers=_bearer(token()))

    assert response.status_code == 502
    assert response.json()["errorCode"] == "ATLAS-400-00-029"


@pytest.mark.covers("aurelius_atlas_lineage_model.app.create_app", rules=["LM-07"])
async def test__a_lineage_with_a_dangling_guid_is_502(
    client: httpx.AsyncClient,
    token: Callable[..., str],
    upstream: FakeUpstream,
) -> None:
    """A relation naming a guid the upstream's own map lacks is a gateway failure, not a crash (DV-22)."""
    dangling = {
        "guidEntityMap": {str(E_IN): {"guid": str(E_IN), "typeName": "kafka_topic", "displayText": "Ingest"}},
        "relations": [
            {"fromEntityId": str(E_IN), "relationshipId": "rel-1", "toEntityId": str(UUID(int=9))},
        ],
    }
    upstream.handler = _answer_lineage(dangling)

    response = await client.get("/", params={"guid": str(E_IN)}, headers=_bearer(token()))

    assert response.status_code == 502
    assert response.json()["errorCode"] == "ATLAS-400-00-029"
    assert "token" not in response.text.lower()  # the caller's credential stays out of the answer


@pytest.mark.covers("aurelius_atlas_lineage_model.app.create_app", rules=["LM-07"])
async def test__a_failing_extract_is_502(
    client: httpx.AsyncClient,
    token: Callable[..., str],
    upstream: FakeUpstream,
) -> None:
    """A data2model answer that is not a 200 is a gateway failure (DV-22)."""
    upstream.handler = lambda request: (
        upstream.json(200, LINEAGE) if request.url.path == f"/v2/lineage/{E_IN}" else httpx.Response(500)
    )

    response = await client.get("/", params={"guid": str(E_IN)}, headers=_bearer(token()))

    assert response.status_code == 502


@pytest.mark.covers("aurelius_atlas_lineage_model.app.create_app", rules=["LM-07"])
async def test__an_invalid_direction_is_400(
    client: httpx.AsyncClient,
    token: Callable[..., str],
) -> None:
    """A direction outside BOTH/INPUT/OUTPUT is a client error, not the legacy's Enum crash (DV-20)."""
    response = await client.get("/", params={"guid": str(E_IN), "direction": "SIDEWAYS"}, headers=_bearer(token()))

    assert response.status_code == 400
    assert response.json()["errorCode"] == "ATLAS-400-00-029"


@pytest.mark.covers("aurelius_atlas_lineage_model.app.create_app", rules=["LM-07"])
async def test__a_non_numeric_depth_is_400(
    client: httpx.AsyncClient,
    token: Callable[..., str],
) -> None:
    """A depth that is not an integer is a client error, not the legacy's int() crash (DV-20)."""
    response = await client.get("/", params={"guid": str(E_IN), "depth": "deep"}, headers=_bearer(token()))

    assert response.status_code == 400


@pytest.mark.covers("aurelius_atlas_lineage_model.app.create_app", rules=["LM-07"])
async def test__a_missing_guid_is_400(
    client: httpx.AsyncClient,
    token: Callable[..., str],
    upstream: FakeUpstream,
) -> None:
    """No guid is a client error, not the legacy's fetch of the literal guid None (DV-21)."""
    response = await client.get("/", headers=_bearer(token()))

    assert response.status_code == 400
    assert upstream.requests == []


@pytest.mark.covers("aurelius_atlas_lineage_model.app.create_app", rules=["LM-07"])
async def test__a_guid_that_is_not_a_uuid_is_400(
    client: httpx.AsyncClient,
    token: Callable[..., str],
    upstream: FakeUpstream,
) -> None:
    """A guid outside the UUID shape is the same client error, answered before any upstream call (DV-21, DV-27)."""
    response = await client.get("/", params={"guid": "e-in"}, headers=_bearer(token()))

    assert response.status_code == 400
    assert response.json()["errorCode"] == "ATLAS-400-00-029"
    assert upstream.requests == []
