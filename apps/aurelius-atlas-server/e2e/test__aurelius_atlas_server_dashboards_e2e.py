from collections.abc import AsyncIterator

import pytest
from aurelius_atlas_server_client import AtlasClient
from playwright.async_api import Browser, Response, async_playwright

SESSION = "/api/atlas/admin/session"


@pytest.fixture(scope="module")
async def browser() -> AsyncIterator[Browser]:
    """Chromium on Playwright's async API.

    pytest-playwright's sync ``page`` fixture keeps an event loop running on the main thread for the whole
    session, which stops pytest-asyncio from running the scenario tests after it; the async API shares
    pytest-asyncio's loop instead.
    """
    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch()
        yield browser
        await browser.close()


# The browser fixture lives on the module loop, so the test runs there too.
@pytest.mark.asyncio(loop_scope="module")
@pytest.mark.covers(rules=["DSH-01", "DSH-02", "DSH-05", "DSH-06"])
@pytest.mark.parametrize("path", ["/", "/n/"], ids=["dashboardv2", "dashboardv3"])
async def test__dashboard_loads_and_asks_the_server_for_the_session(browser: Browser, server: str, path: str) -> None:
    """The dashboard's page and all of its own files load from the image, and it asks for the session.

    Playwright's bundled browsers have their own trust stores and cannot enroll the mkcert root, so page
    navigation skips certificate verification. This is the one named relaxation of the browser-facing path
    (ADR 039), as in the frontend example: the API tests in this directory verify the server's certificate
    against the CA.
    """
    context = await browser.new_context(ignore_https_errors=True)
    page = await context.new_page()
    broken: list[str] = []

    def record(response: Response) -> None:
        if "/api/" not in response.url and response.status >= 400:
            broken.append(f"{response.status} {response.url}")

    page.on("response", record)
    async with page.expect_response(lambda response: SESSION in response.url, timeout=30_000) as session:
        await page.goto(f"{server}{path}")

    assert (await session.value).status == 200
    assert await page.title() == "Atlas"
    assert broken == []
    await context.close()


@pytest.mark.covers(
    "aurelius_atlas_server_client.client.AdminApi.version",
    "aurelius_atlas_server_client.client.AdminApi.status",
    "aurelius_atlas_server_client.client.AdminApi.liveness",
    "aurelius_atlas_server_client.client.AdminApi.readiness",
    rules=["ADM-01", "ADM-02", "ADM-03", "ADM-04", "CL-11"],
)
async def test__the_admin_answers_come_through_the_client_library(api: AtlasClient) -> None:
    """The client library reads the container's admin routes over TLS (CL-11, ADM-01..ADM-04).

    The typed twin of the dashboard's session call: the same server, the same
    dev CA, parsed into the contract models (CL-10) — readiness proves the
    store is healthy enough to serve, which is what the image's healthcheck asserts.
    """
    version = await api.admin.version()
    assert version.name == "aurelius-atlas"
    assert version.version
    assert (await api.admin.status()).status == "ACTIVE"
    assert await api.admin.liveness() == "Service is live"
    assert await api.admin.readiness() == "Service is ready to accept requests"
