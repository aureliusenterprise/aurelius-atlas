"""The server under a path prefix (PFX-01 to PFX-04, DD-363): a proxy serves it at ``/atlas2``.

Uvicorn's ``root_path`` makes each request's path start with the prefix; the client here sends the paths so.
"""

from collections.abc import AsyncIterator
from urllib.parse import parse_qs, urlparse

import httpx2 as httpx
import pytest
from aurelius_atlas_server import ServerSettings, __main__, create_app
from aurelius_atlas_server.root_path import site_path, under_root
from aurelius_atlas_store_es.testing.fake import FakeClient
from fake_issuer import FakeIssuer
from pydantic import ValidationError

ROOT = "/atlas2"
R = "aurelius_atlas_server.root_path"


@pytest.fixture
async def proxied(settings: ServerSettings, fake_es: FakeClient) -> AsyncIterator[httpx.AsyncClient]:
    """A browser's client of the started server under ``/atlas2``, keeping cookies."""
    _ = fake_es
    app = create_app(settings.model_copy(update={"root_path": ROOT}))
    async with app.router.lifespan_context(app):
        transport = httpx.ASGITransport(app=app, root_path=ROOT)
        async with httpx.AsyncClient(transport=transport, base_url="https://localhost:9000") as client:
            yield client


@pytest.mark.covers("aurelius_atlas_server.__main__.uvicorn_options", rules=["PFX-01"])
def test__the_root_path_is_a_setting_uvicorn_takes(settings: ServerSettings) -> None:
    """A path of segments without a trailing slash, or empty for the root."""
    options = __main__.uvicorn_options(settings.model_copy(update={"root_path": ROOT}))

    assert options["root_path"] == ROOT
    assert ServerSettings.model_validate({**settings.model_dump(), "root_path": "/a/b"}).root_path == "/a/b"
    for wrong in ("atlas2", "/atlas2/", "/", "//x", "/a b"):
        with pytest.raises(ValidationError):
            ServerSettings.model_validate({**settings.model_dump(), "root_path": wrong})


@pytest.mark.covers(f"{R}.site_path", f"{R}.under_root", rules=["PFX-02", "PFX-03"])
def test__a_path_is_read_within_the_root_and_led_back_under_it() -> None:
    """Without the prefix for the checks, with it for the browser; a path elsewhere is left as it is."""
    scope = {"root_path": ROOT}

    assert site_path({**scope, "path": "/atlas2/api/atlas/admin/status"}) == "/api/atlas/admin/status"
    assert site_path({**scope, "path": "/atlas2"}) == "/"
    assert site_path({**scope, "path": "/atlas20/x"}) == "/atlas20/x"
    assert site_path({"path": "/n/"}) == "/n/"
    assert under_root(scope, "/login.jsp") == "/atlas2/login.jsp"
    assert under_root({}, "/login.jsp") == "/login.jsp"


@pytest.mark.covers(
    "aurelius_atlas_server.authentication.AuthenticationMiddleware.dispatch",
    "aurelius_atlas_server.security_headers.SecurityHeadersMiddleware.__call__",
    rules=["PFX-02"],
)
async def test__the_open_paths_and_the_api_are_known_under_the_root(proxied: httpx.AsyncClient) -> None:
    """The probes answer without a user, an API call without one is 401, with the API's headers."""
    status = await proxied.get(f"{ROOT}/api/atlas/admin/status")
    refused = await proxied.get(f"{ROOT}/api/atlas/v2/types/typedefs")

    assert (status.status_code, status.json()) == (200, {"Status": "ACTIVE"})
    assert refused.status_code == 401
    assert [answer.headers["x-frame-options"] for answer in (status, refused)] == ["DENY", "DENY"]
    assert refused.headers["cache-control"] == "no-store"


@pytest.mark.covers(
    "aurelius_atlas_server.routes.login.login",
    "aurelius_atlas_server.routes.login.logout",
    rules=["PFX-03", "PFX-04"],
)
async def test__a_browser_signs_in_and_out_under_the_root(proxied: httpx.AsyncClient, issuer: FakeIssuer) -> None:
    """To ``/atlas2/login.jsp``, the provider's return there, back to the page asked; sign-out back to the root."""
    asked = await proxied.get(f"{ROOT}/n/")
    started = await proxied.get(f"{ROOT}/login.jsp")
    query = {name: values[0] for name, values in parse_qs(urlparse(started.headers["location"]).query).items()}
    back = await proxied.get(
        f"{ROOT}/login.jsp", params={"code": issuer.grant_code(query["nonce"]), "state": query["state"]}
    )
    session = await proxied.get(f"{ROOT}/api/atlas/admin/session")
    out = await proxied.get(f"{ROOT}/logout.html")
    leave = {name: values[0] for name, values in parse_qs(urlparse(out.headers["location"]).query).items()}

    assert (asked.status_code, asked.headers["location"]) == (302, "/atlas2/login.jsp")
    assert query["redirect_uri"] == "https://localhost:9000/atlas2/login.jsp"
    assert (back.status_code, back.headers["location"]) == (302, "/atlas2/n/")
    assert session.json()["userName"] == "admin"
    assert leave["post_logout_redirect_uri"] == "https://localhost:9000/atlas2/"
