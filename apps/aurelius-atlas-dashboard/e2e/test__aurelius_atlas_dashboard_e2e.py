"""The dashboard origin: what the nginx image serves and proxies (DSH-01 to DSH-06; DD-034)."""

from collections.abc import AsyncIterator

import httpx
import pytest
from playwright.async_api import Browser, Response, async_playwright

SESSION = "/api/atlas/admin/session"


@pytest.fixture(scope="module")
async def browser() -> AsyncIterator[Browser]:
    """Chromium on Playwright's async API.

    pytest-playwright's sync ``page`` fixture keeps an event loop running on the main thread for the whole
    session, which stops pytest-asyncio from running the async tests after it; the async API shares
    pytest-asyncio's loop instead.
    """
    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch()
        yield browser
        await browser.close()


@pytest.mark.asyncio(loop_scope="module")
@pytest.mark.covers(rules=["DSH-01", "DSH-02"])
@pytest.mark.parametrize(
    ("path", "needle", "content_type"),
    [
        ("/", "<title>Atlas</title>", "text/html"),
        ("/index.html", "<title>Atlas</title>", "text/html"),
        ("/js/main.js", None, "javascript"),
        ("/n/", "<title>Atlas</title>", "text/html"),
        ("/n/js/main.js", None, "javascript"),
    ],
)
async def test__the_dashboards_are_served_where_atlas_serves_them(
    dashboard_client: httpx.AsyncClient, path: str, needle: str | None, content_type: str
) -> None:
    """dashboardv2 answers at the root and dashboardv3 under ``/n/``, as built (DSH-01, DSH-02)."""
    response = await dashboard_client.get(path)

    assert response.status_code == 200
    assert content_type in response.headers["content-type"]
    if needle is not None:
        assert needle in response.text


@pytest.mark.asyncio(loop_scope="module")
@pytest.mark.covers(rules=["DSH-02"])
async def test__dashboardv3_without_a_slash_redirects(dashboard_client: httpx.AsyncClient) -> None:
    """``/n`` leads to ``/n/``, as a browser expects of a directory (DSH-02; DV-09: 308 keeps the method)."""
    response = await dashboard_client.get("/n", follow_redirects=False)

    assert response.status_code == 308
    assert response.headers["location"].endswith("/n/")


@pytest.mark.asyncio(loop_scope="module")
@pytest.mark.covers(rules=["DSH-03"])
@pytest.mark.parametrize(
    ("path", "status"), [("/api/atlas/admin/status", 200), ("/missing.js", 404), ("/n/missing.js", 404)]
)
async def test__the_api_wins_on_its_prefix_and_unknown_files_stay_404(
    dashboard_client: httpx.AsyncClient, path: str, status: int
) -> None:
    """The API wins on its prefix; unknown files stay 404 (DSH-03).

    An API path is proxied to the server even though it shares the origin, and a path neither the API
    nor a dashboard file answers is 404, not an index.html fallback.
    """
    response = await dashboard_client.get(path)

    assert response.status_code == status
    if status == 200:
        assert response.json() == {"Status": "ACTIVE"}


@pytest.mark.asyncio(loop_scope="module")
@pytest.mark.covers(rules=["DSH-04"])
async def test__the_server_answers_the_api_only(server_client: httpx.AsyncClient) -> None:
    """On its own origin the server answers the API only (DSH-04).

    No dashboard path answers where the server served the dashboards until DD-034 moved them to the
    dashboard image.
    """
    assert (await server_client.get("/")).status_code == 404
    assert (await server_client.get("/n/")).status_code == 404
    assert (await server_client.get("/api/atlas/admin/status")).status_code == 200


# The browser fixture lives on the module loop, so the test runs there too.
@pytest.mark.asyncio(loop_scope="module")
@pytest.mark.covers(rules=["DSH-05", "DSH-06"])
@pytest.mark.parametrize("path", ["/", "/n/"], ids=["dashboardv2", "dashboardv3"])
async def test__dashboard_loads_and_asks_the_origin_for_the_session(
    browser: Browser, dashboard: str, path: str
) -> None:
    """Each dashboard loads from the dashboard image and asks it for the session (DSH-05, DSH-06).

    The page and all of its own files come from the image — the built vendored source — and the session
    call reaches the server through the same origin's proxy.

    Playwright's bundled browsers have their own trust stores and cannot enroll the mkcert root, so page
    navigation skips certificate verification. This is the one named relaxation of the browser-facing
    path (ADR 039), as in the frontend example: the tests above verify this same origin's certificate
    against the CA with ``dashboard_client``.
    """
    context = await browser.new_context(ignore_https_errors=True)
    page = await context.new_page()
    broken: list[str] = []

    def record(response: Response) -> None:
        if "/api/" not in response.url and response.status >= 400:
            broken.append(f"{response.status} {response.url}")

    page.on("response", record)
    async with page.expect_response(lambda response: SESSION in response.url, timeout=30_000) as session:
        await page.goto(f"{dashboard}{path}")

    assert (await session.value).status == 200
    assert await page.title() == "Atlas"
    assert broken == []
    await context.close()
