"""App-wiring tests: the verdict endpoint, the auth gate, the draft rejections, liveness (VE-03/04; VEV-01/02/06)."""

import json
from collections.abc import Callable

import httpx2 as httpx
import pytest
from aurelius_atlas_auth import KeycloakAuth
from aurelius_atlas_server_client.client import AtlasClient
from aurelius_atlas_validate_entity.app import create_app
from aurelius_atlas_validate_entity.settings import ValidateEntitySettings
from fake_catalogue import FakeCatalogue, rule_entity, search_result

NAME_RULE = rule_entity(
    "rule-dataset-name",
    "Dataset has a name",
    {
        "name": "Dataset has a name",
        "active": True,
        "dqcheckkind": "ATTRIBUTE_PRESENT",
        "dqattribute": "name",
        "compliantMessage": "This dataset has a name",
        "nonCompliantMessage": "This dataset should have a name",
    },
)
DRAFT = {"guid": "e-in", "typeName": "m4i_dataset", "attributes": {"name": "Sales Orders"}}


def _bearer(token: str) -> dict[str, str]:
    """The authorization header for a bearer token."""
    return {"authorization": f"Bearer {token}"}


def _answers_one_page(catalogue: FakeCatalogue, *entities: dict[str, object]) -> None:
    """The fake catalogue answers the rule walk with one page and the end marker."""
    catalogue.handler = lambda request: FakeCatalogue.json(
        200, search_result(list(entities), "-1" if _marker(request) == "*" else None)
    )


def _marker(request: httpx.Request) -> str | None:
    """The marker of a recorded search request: the basic search carries it in the body (SRC-01)."""
    return json.loads(request.content).get("marker")


@pytest.mark.covers("aurelius_atlas_validate_entity.app.create_app", rules=["VEV-02"])
async def test__the_draft_answers_with_the_rules_verdicts(
    client: httpx.AsyncClient, token: Callable[..., str], catalogue: FakeCatalogue
) -> None:
    """200 with one verdict per active rule, boolean compliant, the rule's own line (VEV-02)."""
    _answers_one_page(catalogue, NAME_RULE)

    response = await client.post("/", json=DRAFT, headers=_bearer(token()))

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("application/json")
    assert response.json() == {
        "verdicts": [
            {
                "ruleGuid": "rule-dataset-name",
                "ruleName": "Dataset has a name",
                "attribute": "name",
                "dimension": "COMPLETENESS",
                "compliant": True,
                "message": "This dataset has a name",
            }
        ],
        "unreadRules": [],
    }


@pytest.mark.covers("aurelius_atlas_validate_entity.app.create_app", rules=["VEV-01"])
@pytest.mark.parametrize(
    ("body", "content_type"),
    [
        (b"", "application/json"),
        (b"not json {", "application/json"),
        (b"[]", "application/json"),
        (b'{"attributes": null}', "application/json"),
        (b'{"attributes": "name"}', "application/json"),
        (b"raw bytes, no declared type", None),
    ],
)
async def test__a_draft_the_app_cannot_read_is_400(
    client: httpx.AsyncClient, token: Callable[..., str], body: bytes, content_type: str | None
) -> None:
    """No object body, or no object ``attributes``: the 400 of VEV-01, in the Atlas error body (DV-79)."""
    headers = _bearer(token())
    if content_type is not None:
        headers["content-type"] = content_type

    response = await client.post("/", content=body, headers=headers)

    assert response.status_code == 400
    assert response.json()["errorCode"] == "ATLAS-400-00-029"
    if body:  # an absent body is FastAPI's "Field required"; a present-but-unreadable one names the attributes
        message = response.json()["errorMessage"]
        assert "attributes" in message or "invalid validation request" in message


@pytest.mark.covers("aurelius_atlas_validate_entity.app.create_app", rules=["VEV-06"])
async def test__a_failing_catalogue_answers_502_never_a_no_rules_answer(
    client: httpx.AsyncClient, token: Callable[..., str], catalogue: FakeCatalogue
) -> None:
    """The catalogue 500s: the draft is answered 502 with the Atlas body, not an empty verdict set (VEV-05/06)."""
    catalogue.handler = lambda _request: FakeCatalogue.json(500, {"errorMessage": "store down"})

    response = await client.post("/", json=DRAFT, headers=_bearer(token()))

    assert response.status_code == 502
    assert response.json()["errorCode"] == "ATLAS-400-00-029"
    assert "verdicts" not in response.json()


@pytest.mark.covers("aurelius_atlas_validate_entity.app.create_app", rules=["VEV-06"])
async def test__an_unreachable_catalogue_answers_502(
    settings: ValidateEntitySettings, auth: KeycloakAuth, token: Callable[..., str]
) -> None:
    """A refused connection is the same 502 (VEV-06, DV-80's sibling): httpx's error, mapped at the root."""
    refusing = FakeCatalogue()
    refusing.handler = lambda _request: (_ for _ in ()).throw(httpx.ConnectError("refused"))
    app = create_app(
        settings,
        auth=auth,
        atlas=AtlasClient(httpx.AsyncClient(base_url="http://catalogue.test", transport=refusing.transport()), "t"),
    )
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://validate-entity") as call_client:
        response = await call_client.post("/", json=DRAFT, headers=_bearer(token()))

    assert response.status_code == 502
    assert response.json()["errorCode"] == "ATLAS-400-00-029"


@pytest.mark.covers("aurelius_atlas_validate_entity.app.create_app", rules=["VE-03"])
async def test__a_missing_token_is_rejected(client: httpx.AsyncClient) -> None:
    """No bearer credential is a 401 (VE-03, DV-75) — the legacy's transparent auth accepted any."""
    response = await client.post("/", json=DRAFT)

    assert response.status_code == 401


@pytest.mark.covers("aurelius_atlas_validate_entity.app.create_app", rules=["VE-03"])
async def test__a_token_minted_for_another_audience_is_rejected(
    client: httpx.AsyncClient, token: Callable[..., str]
) -> None:
    """A token for a client outside the audience is a 401 (VE-03, AUX-04)."""
    forged = token(azp="some-other-client", audience="some-other-client")

    response = await client.post("/", json=DRAFT, headers=_bearer(forged))

    assert response.status_code == 401


@pytest.mark.covers("aurelius_atlas_validate_entity.app.create_app", rules=["VEV-04"])
async def test__the_callers_token_never_rides_the_rules_read(
    client: httpx.AsyncClient, token: Callable[..., str], catalogue: FakeCatalogue
) -> None:
    """The search carries the app's identity, never the caller's bearer (VEV-04, DD-499)."""
    _answers_one_page(catalogue, NAME_RULE)

    await client.post("/", json=DRAFT, headers=_bearer(token()))

    (search,) = catalogue.searches()
    assert search.headers["authorization"] == "Bearer app-identity"


@pytest.mark.covers("aurelius_atlas_validate_entity.app.create_app", rules=["VEV-03"])
async def test__the_rules_search_pages_to_the_end_and_asks_the_rule_attributes(
    client: httpx.AsyncClient, token: Callable[..., str], catalogue: FakeCatalogue
) -> None:
    """The walk starts at ``*`` and ends at ``-1``, asking the governance type's attributes (VEV-03, SRC-08)."""
    pages = iter(
        [
            FakeCatalogue.json(200, search_result([NAME_RULE], "page-2")),
            FakeCatalogue.json(
                200,
                search_result(
                    [
                        rule_entity(
                            "rule-legacy",
                            "Legacy expression",
                            {"name": "Legacy expression", "expression": "completeness('owner')"},
                        )
                    ],
                    "-1",
                ),
            ),
        ]
    )
    catalogue.handler = lambda _request: next(pages)

    response = await client.post("/", json=DRAFT, headers=_bearer(token()))

    searches = catalogue.searches()
    bodies = [json.loads(request.content) for request in searches]
    assert [body["marker"] for body in bodies] == ["*", "page-2"]
    assert bodies[0]["typeName"] == "m4i_gov_data_quality"
    assert "dqcheckkind" in bodies[0]["attributes"]
    body = response.json()
    assert [verdict["ruleGuid"] for verdict in body["verdicts"]] == ["rule-dataset-name"]
    assert body["unreadRules"] == [
        {
            "ruleGuid": "rule-legacy",
            "ruleName": "Legacy expression",
            "error": "the rule names no 'dqcheckkind': a stored expression rule needs re-authoring (DV-146)",
        }
    ]


@pytest.mark.covers("aurelius_atlas_validate_entity.app.create_app", rules=["VE-04"])
async def test__liveness_needs_no_token(client: httpx.AsyncClient) -> None:
    """The container healthcheck answers 204, anonymous (VE-04, DV-76)."""
    response = await client.get("/liveness")

    assert response.status_code == 204


@pytest.mark.covers("aurelius_atlas_validate_entity.app.create_app", rules=["VEV-05"])
async def test__the_rules_are_read_once_per_cache_window(
    client: httpx.AsyncClient, token: Callable[..., str], catalogue: FakeCatalogue
) -> None:
    """Two drafts in one window answer live but read the catalogue once (VEV-05)."""
    _answers_one_page(catalogue, NAME_RULE)
    bearer = _bearer(token())

    first = await client.post("/", json=DRAFT, headers=bearer)
    second = await client.post("/", json=DRAFT, headers=bearer)

    assert len(catalogue.searches()) == 1
    assert first.json() == second.json()


@pytest.mark.covers("aurelius_atlas_validate_entity.app.create_app", rules=["VEV-05"])
async def test__a_failed_read_caches_nothing(
    client: httpx.AsyncClient, token: Callable[..., str], catalogue: FakeCatalogue
) -> None:
    """The failed read answers 502 and is not remembered: the next call reads again (VEV-05)."""
    answers = iter([FakeCatalogue.json(500, {}), FakeCatalogue.json(200, search_result([NAME_RULE], "-1"))])
    catalogue.handler = lambda _request: next(answers)
    bearer = _bearer(token())

    failed = await client.post("/", json=DRAFT, headers=bearer)
    recovered = await client.post("/", json=DRAFT, headers=bearer)

    assert failed.status_code == 502
    assert recovered.status_code == 200
    assert len(catalogue.searches()) == 2


@pytest.mark.covers("aurelius_atlas_validate_entity.app.create_app")
async def test__the_validate_route_is_post_only(client: httpx.AsyncClient, token: Callable[..., str]) -> None:
    """A GET on the validate route is a 405: the legacy endpoint is POST-only (DV-67's route shape).

    No rule states it — the framework does; the test names the route for ADR 049.
    """
    response = await client.get("/", headers=_bearer(token()))

    assert response.status_code == 405
    assert response.headers["allow"] == "POST"


@pytest.mark.covers("aurelius_atlas_validate_entity.app.create_app", rules=["VE-05"])
def test__the_app_is_built_from_the_settings(settings: ValidateEntitySettings) -> None:
    """The factory wires the settings, the verifier, the door and the breaker onto the app state."""
    app = create_app(settings)

    assert app.state.settings is settings
    assert app.state.engine is not None
    assert app.state.server_breaker.name == "validate_entity_server"
    assert app.title == "aurelius-atlas-validate-entity"
    assert app.docs_url is None  # an auxiliary API publishes no docs surface
