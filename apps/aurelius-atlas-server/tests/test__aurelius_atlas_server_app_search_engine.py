"""The App Search API in the server: its two paths, the quality engine, an unknown engine, the privilege it needs,
and a refused body (ASE-01, ASE-02, ASE-04, ASQ-01), on the fake store.
"""  # noqa: D205 - one sentence

import httpx2 as httpx
import pytest
from aurelius_atlas_core.app_search_document import own_document
from aurelius_atlas_core.entity_documents import ElasticsearchEntityDocuments
from aurelius_atlas_core.stored_entity import StoredEntity, StoredQualityResult
from aurelius_atlas_store_es.testing.fake import FakeClient
from fake_issuer import FakeIssuer

R = "aurelius_atlas_server.routes.app_search.search"
ENGINES = "/api/as/v1/engines"


def as_roles(issuer: FakeIssuer, user: str, *roles: str) -> dict[str, str]:
    """The ``Authorization`` header of a token of the user holding these roles of the server's client."""
    return {"Authorization": f"Bearer {issuer.token(user, atlas_roles=roles)}"}


async def indexed(fake_es: FakeClient) -> None:
    """A domain with its App Search document in the server's store."""
    entity = StoredEntity(guid="d", type_name="m4i_data_domain", attributes={"Asset.name": "Sales"})
    documents = ElasticsearchEntityDocuments(fake_es)  # type: ignore[arg-type]
    await documents.write([(entity.model_copy(update={"app_search": own_document(entity)}), None)])


@pytest.mark.covers(R, rules=["ASE-01"])
async def test__both_paths_answer_the_engine_alike(client: httpx.AsyncClient, fake_es: FakeClient) -> None:
    """``search`` and ``search.json``: the same results in App Search's shape; an empty body is a match-all."""
    await indexed(fake_es)
    body = {"query": "sales", "result_fields": {"name": {"raw": {}}}}

    plain = await client.post(f"{ENGINES}/atlas-dev/search", json=body)
    dotted = await client.post(f"{ENGINES}/atlas-dev/search.json", json=body)
    empty = await client.post(f"{ENGINES}/atlas-dev/search.json")

    assert plain.status_code == dotted.status_code == empty.status_code == 200
    for response in (plain, dotted):
        assert [result["name"] for result in response.json()["results"]] == [{"raw": "Sales"}]
    assert empty.json()["meta"]["page"]["total_results"] == 1


@pytest.mark.covers(R, rules=["ASQ-01"])
async def test__the_quality_engine_answers_its_results_on_both_paths(
    client: httpx.AsyncClient, fake_es: FakeClient
) -> None:
    """A score's result by ``fieldguid``, the field page's filter; the engine named in the answer."""
    result = StoredQualityResult(qualityguid="r", name="Rule 1", fieldguid=["f"], dqscore=0.5)
    score = StoredEntity(guid="s", type_name="m4i_dq_score", attributes={}, quality_result=result)
    await ElasticsearchEntityDocuments(fake_es).write([(score, None)])  # type: ignore[arg-type]
    body = {"filters": {"all": [{"fieldguid": ["f"]}]}, "result_fields": {"name": {"raw": {}}, "dqscore": {"raw": {}}}}

    for path in ("search", "search.json"):
        response = await client.post(f"{ENGINES}/atlas-dev-quality/{path}", json=body)
        assert response.status_code == 200
        answer = response.json()
        assert answer["meta"]["engine"]["name"] == "atlas-dev-quality"
        assert [(found["name"], found["dqscore"]) for found in answer["results"]] == [({"raw": "Rule 1"}, {"raw": 0.5})]


@pytest.mark.covers(R, rules=["ASE-01", "ASQ-01"])
async def test__another_engine_is_not_found(client: httpx.AsyncClient) -> None:
    """The governance engine comes with 14.6."""
    response = await client.post(f"{ENGINES}/atlas-dev-gov-quality/search.json", json={})

    assert (response.status_code, response.json()) == (404, {"errors": ["Could not find engine."]})


@pytest.mark.covers(R, rules=["ASE-02"])
async def test__a_user_without_entity_read_is_refused(client: httpx.AsyncClient, issuer: FakeIssuer) -> None:
    """403 in App Search's shape; a reader is answered; no user at all is the server's 401 (DD-526)."""
    nobody = await client.post(f"{ENGINES}/atlas-dev/search", json={}, headers=as_roles(issuer, "nobody"))
    reader = await client.post(f"{ENGINES}/atlas-dev/search", json={}, headers=as_roles(issuer, "reader", "atlas-read"))
    anonymous = await client.post(f"{ENGINES}/atlas-dev/search", json={}, headers={"Authorization": ""})

    assert (nobody.status_code, nobody.json()) == (403, {"errors": ["The user is not authorized to read entities"]})
    assert reader.status_code == 200
    assert anonymous.status_code == 401


@pytest.mark.covers(R, rules=["ASE-04"])
async def test__a_refused_body_is_answered_400_with_its_errors(client: httpx.AsyncClient) -> None:
    """Invalid JSON, and an option App Search refuses."""
    broken = await client.post(
        f"{ENGINES}/atlas-dev/search", content=b"{", headers={"Content-Type": "application/json"}
    )
    paged = await client.post(f"{ENGINES}/atlas-dev/search", json={"page": {"size": 0}})

    assert (broken.status_code, broken.json()) == (400, {"errors": ["The request body must be valid JSON"]})
    assert (paged.status_code, paged.json()) == (400, {"errors": ["Page size must be between 1 and 1000"]})
