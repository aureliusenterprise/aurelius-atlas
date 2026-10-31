"""Unit tests for the realm browser-origins step — no cluster needed (CHT-107).

The admin REST is steered with an httpx MockTransport, so the read-merge-write
logic (and its idempotence) runs against canned client resources.
"""

import json

import httpx2 as httpx
import pytest
from aurelius_atlas_cluster_lane.origins import ensure_browser_origins

HOST = "atlas.atlas.test"


def _client_resource(*, redirect_uris: list[str], web_origins: list[str], post_logout: str = "*") -> dict:
    return {
        "id": "c-1",
        "clientId": "aurelius",
        "redirectUris": redirect_uris,
        "webOrigins": web_origins,
        "attributes": {"post.logout.redirect.uris": post_logout},
    }


def _steer(resource: dict) -> tuple[httpx.Client, list[dict]]:
    """A client that answers the search with ``resource`` and records PUT bodies."""
    puts: list[dict] = []

    def handler(request: httpx.Request) -> httpx.Response:
        if request.method == "GET" and request.url.path.endswith("/clients"):
            return httpx.Response(200, json=[dict(resource)])
        if request.method == "PUT":
            puts.append(json.loads(request.content))
            return httpx.Response(204)
        msg = f"unexpected {request.method} {request.url}"
        raise AssertionError(msg)

    return httpx.Client(transport=httpx.MockTransport(handler), base_url="https://kc.test"), puts


@pytest.mark.covers("aurelius_atlas_cluster_lane.origins.ensure_browser_origins", rules=["CHT-107"])
def test__adds_the_edge_origin_to_an_imported_dev_client() -> None:
    """The master asset's localhost-only client gains the edge host on all three lists (CHT-107)."""
    client, puts = _steer(
        _client_resource(
            redirect_uris=["http://localhost:4200/*"],
            web_origins=["http://localhost:4200"],
            post_logout="https://localhost:18444/*",
        )
    )
    added = ensure_browser_origins(client, realm="master", client_id="aurelius", host=HOST)

    assert set(added) == {"redirectUris", "webOrigins", "post.logout.redirect.uris"}
    (body,) = puts
    assert f"https://{HOST}/*" in body["redirectUris"]
    assert f"https://{HOST}" in body["webOrigins"]
    assert f"https://{HOST}/*" in body["attributes"]["post.logout.redirect.uris"].split()
    assert "http://localhost:4200/*" in body["redirectUris"]  # the import's own origins stay


@pytest.mark.covers("aurelius_atlas_cluster_lane.origins.ensure_browser_origins", rules=["CHT-107"])
def test__a_covered_client_is_untouched() -> None:
    """Idempotence: an already-registered host PUTs nothing — re-runs converge (CHT-107)."""
    client, puts = _steer(
        _client_resource(
            redirect_uris=[f"https://{HOST}/*"],
            web_origins=[f"https://{HOST}"],
            post_logout=f"https://{HOST}/*",
        )
    )
    added = ensure_browser_origins(client, realm="master", client_id="aurelius", host=HOST)

    assert added == ()
    assert puts == []


@pytest.mark.covers("aurelius_atlas_cluster_lane.origins.ensure_browser_origins", rules=["CHT-107"])
def test__a_wildcard_list_is_left_alone() -> None:
    """A bare ``*`` entry already covers the host; appending to it is invalid input (CHT-107)."""
    client, puts = _steer(
        _client_resource(
            redirect_uris=["*"],
            web_origins=["*"],
            post_logout="*",
        )
    )
    added = ensure_browser_origins(client, realm="master", client_id="aurelius", host=HOST)

    assert added == ()
    assert puts == []


@pytest.mark.covers("aurelius_atlas_cluster_lane.origins.ensure_browser_origins", rules=["CHT-107"])
def test__a_missing_client_fails_loudly() -> None:
    """No matching client: the failure names the realm and the client (CHT-107)."""

    def handler(request: httpx.Request) -> httpx.Response:  # noqa: ARG001 - transport signature
        return httpx.Response(200, json=[])

    client = httpx.Client(transport=httpx.MockTransport(handler), base_url="https://kc.test")
    with pytest.raises(AssertionError, match="aurelius"):
        ensure_browser_origins(client, realm="master", client_id="aurelius", host=HOST)
