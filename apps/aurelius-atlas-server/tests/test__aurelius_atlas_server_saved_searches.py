"""The saved-search endpoints of ``DiscoveryREST`` (SVS-02, SVS-04, SVS-07, DV-110) on the fake Elasticsearch.

Read from ``DiscoveryREST`` of Apache Atlas 2.4.0; the service is tested in ``aurelius-atlas-core``, the round trip
by the ``search/saved-searches`` scenario.
"""

import shutil
from pathlib import Path
from typing import Any

import httpx2 as httpx
import pytest
from aurelius_atlas_core.model_loader import BUILTIN_MODELS_DIR
from fake_issuer import FakeIssuer

D = "aurelius_atlas_server.routes.discovery"
SAVED = "/api/atlas/v2/search/saved"
MODELS = Path("0000-Area0") / "0010-base_model.json"


@pytest.fixture
def models_dir(tmp_path: Path) -> Path:
    """Atlas's base model alone, which holds the profile and saved-search types (MDL-16)."""
    directory = tmp_path / "core-models"
    (directory / MODELS.parent).mkdir(parents=True)
    shutil.copy(BUILTIN_MODELS_DIR / MODELS, directory / MODELS)
    return directory


async def send(client: httpx.AsyncClient, method: str, url: str, **kwargs: Any) -> tuple[int, Any]:  # noqa: ANN401
    """The status and the JSON body, None without one."""
    response = await client.request(method, url, **kwargs)
    return response.status_code, response.json() if response.content else None


@pytest.mark.covers(f"{D}.get_saved_searches", f"{D}.add_saved_search", rules=["SVS-02", "SVS-04", "SVS-07"])
async def test__each_user_lists_their_own_searches(client: httpx.AsyncClient, issuer: FakeIssuer) -> None:
    """Nothing (204) before a first search; then only the user's own; another user's token sees none of them."""
    assert await send(client, "GET", SAVED) == (204, None)
    status, saved = await send(client, "POST", SAVED, json={"name": "mine", "searchParameters": {"typeName": "Asset"}})
    assert (status, saved["ownerName"]) == (200, "admin")
    assert [found["name"] for found in (await send(client, "GET", SAVED, params={"user": "admin"}))[1]] == ["mine"]
    other = {"Authorization": f"Bearer {issuer.token('ann')}"}
    assert await send(client, "GET", SAVED, headers=other) == (204, None)
    assert (await send(client, "GET", f"{SAVED}/mine", headers=other))[0] == 404
    refused = await send(client, "DELETE", f"{SAVED}/{saved['guid']}", headers=other)
    assert refused == (400, {"errorCode": "ATLAS-400-00-029", "errorMessage": "invalid data"})


@pytest.mark.covers(f"{D}.add_saved_search", f"{D}.update_saved_search", rules=["SVS-07"])
async def test__a_request_needs_a_search_of_valid_lengths(client: httpx.AsyncClient) -> None:
    """No body answers ``BAD_REQUEST`` (DV-110); a name or a query too long is refused as Atlas refuses it."""
    for method in ("POST", "PUT"):
        status, body = await send(client, method, SAVED)
        assert (status, body["errorMessage"]) == (400, "The saved search is missing")
    status, body = await send(client, "POST", SAVED, json={"name": "n" * 5000})
    assert (status, body["errorCode"]) == (400, "ATLAS-400-00-057")
    status, body = await send(client, "POST", SAVED, json={"name": "n", "searchParameters": {"query": "q" * 5000}})
    assert (status, body["errorCode"]) == (400, "ATLAS-400-00-058")
    status, body = await send(client, "GET", SAVED, params={"user": "u" * 5000})
    assert (status, body["errorCode"]) == (400, "ATLAS-400-00-057")
