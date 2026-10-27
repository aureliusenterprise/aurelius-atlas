"""Security response headers on API and dashboard answers (SRV-08, DD-236)."""

from collections.abc import AsyncIterator
from pathlib import Path

import httpx2 as httpx
import pytest
from aurelius_atlas_server import ServerSettings, create_app
from aurelius_atlas_store_es.testing.fake import FakeClient
from fastapi import FastAPI

API_HEADERS = {
    "x-content-type-options": "nosniff",
    "x-frame-options": "DENY",
    "referrer-policy": "no-referrer",
    "cache-control": "no-store",
}

DASHBOARD_HEADERS = {
    "x-content-type-options": "nosniff",
    "x-frame-options": "SAMEORIGIN",
    "referrer-policy": "no-referrer",
}


@pytest.fixture
def dashboard_dir(tmp_path: Path) -> Path:
    """A dashboard directory laid out as the build writes it: v2 at the root, v3 in ``n/``."""
    root = tmp_path / "dashboard"
    (root / "n").mkdir(parents=True)
    (root / "js").mkdir()
    (root / "index.html").write_text("<title>dashboardv2</title>")
    (root / "js" / "main.js").write_text("// v2")
    (root / "n" / "index.html").write_text("<title>dashboardv3</title>")
    return root


@pytest.fixture
async def headed_client(app: FastAPI) -> AsyncIterator[httpx.AsyncClient]:
    """The plain app (no dashboard) under the middleware."""
    async with app.router.lifespan_context(app):
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://aurelius-atlas") as client:
            yield client


@pytest.fixture
async def dashboard_client(
    settings: ServerSettings, fake_es: FakeClient, dashboard_dir: Path
) -> AsyncIterator[httpx.AsyncClient]:
    """An app with the dashboards mounted, under the middleware."""
    _ = fake_es
    app = create_app(settings.model_copy(update={"dashboard_dir": dashboard_dir}))
    async with app.router.lifespan_context(app):
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://aurelius-atlas") as client:
            yield client


@pytest.mark.covers("aurelius_atlas_server.security_headers.SecurityHeadersMiddleware.__call__", rules=["SRV-08"])
async def test__api_answers_carry_the_hardening_headers(headed_client: httpx.AsyncClient) -> None:
    """The JSON API: nosniff, framing closed, nothing cached, a CSP that serves no documents (SRV-08)."""
    for path in ("/api/atlas/admin/status", "/api/atlas/admin/version"):
        response = await headed_client.get(path)

        assert response.status_code == 200
        for name, value in API_HEADERS.items():
            assert response.headers[name] == value
        csp = response.headers["content-security-policy"]
        assert csp.startswith("default-src 'none'")
        assert "frame-ancestors 'none'" in csp
        assert response.headers["strict-transport-security"] == "max-age=31536000; includeSubDomains"


@pytest.mark.covers("aurelius_atlas_server.security_headers.SecurityHeadersMiddleware.__call__", rules=["SRV-08"])
async def test__api_errors_carry_them_too(headed_client: httpx.AsyncClient) -> None:
    """A 404 and a 500 are API answers as well: the headers are on the wire for every status."""
    missing = await headed_client.get("/api/atlas/v2/entity/guid/00000000-0000-0000-0000-000000000000")
    assert missing.headers["x-content-type-options"] == "nosniff"
    assert missing.headers["cache-control"] == "no-store"


@pytest.mark.covers(
    "aurelius_atlas_server.security_headers.SecurityHeadersMiddleware.__call__",
    "aurelius_atlas_server.security_headers._is_busted_asset",
    rules=["SRV-08"],
)
async def test__dashboard_answers_carry_a_serving_csp_and_busted_assets_cache(
    dashboard_client: httpx.AsyncClient,
) -> None:
    """The legacy dashboard's own contract (SRV-08).

    Same-origin framing, a 'self' CSP with the inline bootstrap scripts allowed
    (DV-86), and bust-versioned assets cached immutably.
    """
    page = await dashboard_client.get("/")
    assert page.status_code == 200
    for name, value in DASHBOARD_HEADERS.items():
        assert page.headers[name] == value
    csp = page.headers["content-security-policy"]
    assert "default-src 'self'" in csp
    assert "script-src 'self' 'unsafe-inline'" in csp
    assert "cache-control" not in page.headers  # the HTML itself stays fresh

    asset = await dashboard_client.get("/js/main.js?bust=v123")
    assert asset.status_code == 200
    assert asset.headers["cache-control"] == "public, max-age=31536000, immutable"

    plain = await dashboard_client.get("/js/main.js")
    assert plain.headers.get("cache-control") is None


@pytest.mark.covers("aurelius_atlas_server.security_headers.SecurityHeadersMiddleware.__init__", rules=["SRV-08"])
async def test__hsts_off_leaves_localhost_free(fake_es: FakeClient, settings: ServerSettings) -> None:
    """The dev arrangement turns HSTS off (ADR 039, DD-236).

    With hsts_enabled=False, a browser that visited the mkcert server is not pinned
    to HTTPS on the plaintext dev surfaces.
    """
    _ = fake_es
    app = create_app(settings.model_copy(update={"hsts_enabled": False}))
    async with app.router.lifespan_context(app):
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://aurelius-atlas") as client:
            response = await client.get("/api/atlas/admin/status")

    assert "strict-transport-security" not in response.headers
    assert response.headers["x-content-type-options"] == "nosniff"
