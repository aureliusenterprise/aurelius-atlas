"""The dashboard origin: what the nginx image serves, proxies and gates (DSH-01 to DSH-08; DD-034, DD-036).

The stack runs the server with authentication on, so page loads carry a session: the gate is nginx's
(DSH-07), the assets stay open (DSH-08), and the tests sign in through the very flow a browser walks.
"""

from collections.abc import AsyncIterator

import httpx
import pytest
from playwright.async_api import Browser, Response, async_playwright

SESSION = "/api/atlas/admin/session"
PAGES = ["/", "/index.html", "/n/", "/n/index.html", "/login.jsp"]
"""The gated page locations of the gate in nginx.conf (DD-036, DD-040).

``/login.jsp`` is Atlas's login URI — its logoutSuccessUrl and the vendored UI's 401 landing
(Utils.defaultErrorHandler) — and the fifth gated page: anonymous in takes the login start, and a
session gets the login page (webapp/login.html), which resolves to the dashboard in use (DD-040).
"""


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
    logged_in_client: httpx.AsyncClient, path: str, needle: str | None, content_type: str
) -> None:
    """dashboardv2 answers at the root and dashboardv3 under ``/n/``, as built (DSH-01, DSH-02).

    A session is held for the page paths — the gate answers them only to a signed-in request (DSH-07);
    the asset paths answer either way, which DSH-08 proves with a fresh client.
    """
    response = await logged_in_client.get(path)

    assert response.status_code == 200
    assert content_type in response.headers["content-type"]
    if needle is not None:
        assert needle in response.text


@pytest.mark.asyncio(loop_scope="module")
@pytest.mark.covers(rules=["DSH-09"])
async def test__dashboardv3_without_a_slash_redirects(dashboard_client: httpx.AsyncClient) -> None:
    """``/n`` leads to ``/n/``, as a browser expects of a directory (DSH-02; DV-09: 308 keeps the method).

    The 308 answers before the gate — nginx's ``return`` runs in the rewrite phase — so the directory
    redirect stays open, and following it reaches the gated page.
    """
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
    nor a dashboard file answers is 404, not an index.html fallback. Only exact page locations carry
    the gate, so an unknown file is a 404 with or without a session (DSH-08's open prefixes).
    """
    response = await dashboard_client.get(path)

    assert response.status_code == status
    if status == 200:
        assert response.json() == {"Status": "ACTIVE"}


@pytest.mark.asyncio(loop_scope="module")
@pytest.mark.covers(rules=["DSH-04"])
async def test__the_server_answers_the_api_only(server_client: httpx.AsyncClient, writer_bearer: str) -> None:
    """On its own origin the server answers the API only (DSH-04).

    No dashboard path answers where the server served the dashboards until DD-034 moved them to the
    dashboard image. The dashboard paths are checked on a bearer so the guard lets them reach the
    router — the 404 must come from the missing route, not from the guard.
    """
    headers = {"Authorization": f"Bearer {writer_bearer}"}
    assert (await server_client.get("/", headers=headers)).status_code == 404
    assert (await server_client.get("/n/", headers=headers)).status_code == 404
    assert (await server_client.get("/api/atlas/admin/status")).status_code == 200


@pytest.mark.asyncio(loop_scope="module")
@pytest.mark.covers(rules=["DSH-07", "DSH-09"])
@pytest.mark.parametrize("path", PAGES)
async def test__a_page_load_without_a_session_starts_the_login_flow(
    dashboard_client: httpx.AsyncClient, path: str
) -> None:
    """The gate redirects each page to the server's login start, keeping the intended URL (DSH-07).

    The answer comes from nginx (``auth_request`` + ``error_page``), so this proves the stack's config,
    not the server's; the kept URL is the page itself, which the flow returns to after Keycloak —
    including ``/login.jsp``, Atlas's login URI: the vendored UI navigates there on any 401, and
    Atlas keeps it off the ignore list under Keycloak, where the adapter runs the dance through it.
    """
    response = await dashboard_client.get(path, follow_redirects=False)

    assert response.status_code == 302
    location = response.headers["location"]
    assert location == f"/api/atlas/auth/login?next={path}"

    onward = await dashboard_client.get(location, follow_redirects=False)
    assert onward.status_code == 302  # the login start answers the issuer's authorization URL
    assert onward.headers["location"].startswith("https://keycloak.localhost:8443/")


@pytest.mark.asyncio(loop_scope="module")
@pytest.mark.covers(rules=["DSH-07"])
async def test__a_page_load_without_a_session_returns_to_keycloak(
    browser: Browser, dashboard: str, writer_password: str
) -> None:
    """A real browser walks the whole dance: page, Keycloak's form, back to the page (DSH-07).

    Playwright's bundled browsers have their own trust stores and cannot enroll the mkcert root, so page
    navigation skips certificate verification. This is the one named relaxation of the browser-facing
    path (ADR 039), as in the frontend example: the tests above verify this same origin's certificate
    against the CA with ``dashboard_client``.
    """
    context = await browser.new_context(ignore_https_errors=True)
    page = await context.new_page()

    await page.goto(f"{dashboard}/n/")  # the gate sends this to login, login to Keycloak
    await page.wait_for_selector("#kc-form-login")
    await page.fill("#username", "aurelius-writer")
    await page.fill("#password", writer_password)
    await page.click("#kc-login")  # the form's own submit button

    await page.wait_for_url(f"{dashboard}/n/", timeout=30_000)
    assert await page.title() == "Atlas"  # back at the intended page, on a session
    await context.close()


@pytest.mark.asyncio(loop_scope="module")
@pytest.mark.covers(rules=["DSH-08"])
async def test__the_login_page_answers_a_session_with_the_resolver(
    logged_in_client: httpx.AsyncClient,
) -> None:
    """On a session, ``/login.jsp`` is served the login page — the resolver of the vendored form (DD-040).

    Atlas answers the URI with its login form (AtlasLoginServlet); here the page is this project's own
    (webapp/login.html), and its body is the rule: read the session and ``last_ui_load`` and continue
    to the dashboard the user was on — the script that returns a v3 sign-in to v3 rather than v2.
    """
    response = await logged_in_client.get("/login.jsp")

    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
    assert "<title>Atlas Login</title>" in response.text
    assert "last_ui_load" in response.text  # the resolver reads the UI the dashboards record
    assert SESSION in response.text  # and asks the same origin for the session, as atlasLogin.js does


@pytest.mark.asyncio(loop_scope="module")
@pytest.mark.covers(rules=["DSH-09"])
async def test__signing_out_of_dashboardv3_and_back_in_returns_to_it(
    browser: Browser, dashboard: str, writer_password: str
) -> None:
    """The whole walk a user takes: v3, sign out, sign in — back on v3, not on v2 (DD-040).

    The vendored v3 header records ``last_ui_load=v2`` and navigates to ``/logout.html``; the logout
    lands on ``/login.jsp`` (Atlas's logoutSuccessUrl), the gate starts the login through it, and the
    login page resolves back to ``/n/``. A context starts with clean storage, as a first visit does.
    """
    context = await browser.new_context(ignore_https_errors=True)
    page = await context.new_page()

    await page.goto(f"{dashboard}/n/")  # the dance in: a fresh sign-in lands on the intended page
    await page.wait_for_selector("#kc-form-login")
    await page.fill("#username", "aurelius-writer")
    await page.fill("#password", writer_password)
    await page.click("#kc-login")
    await page.wait_for_url(f"{dashboard}/n/", timeout=30_000)

    # Logout waits in the header's user dropdown (hidden until it opens): open it as a user does,
    # and the click writes last_ui_load=v2 and navigates to /logout.html.
    await page.wait_for_selector(".header-menu a.user-dropdown")  # the v3 header, booted
    await page.click(".header-menu a.user-dropdown")
    await page.click("[data-id='signOut']")
    await page.wait_for_selector("#kc-logout")  # the issuer's logout confirmation
    await page.click("#kc-logout")  # ends the issuer session, returns to /login.jsp
    await page.wait_for_selector("#kc-form-login")  # the gate takes the login start, keeping /login.jsp
    await page.fill("#username", "aurelius-writer")
    await page.fill("#password", writer_password)
    await page.click("#kc-login")

    await page.wait_for_url(f"{dashboard}/n/index.html", timeout=30_000)  # the resolver's answer
    assert await page.title() == "Atlas"
    await context.close()


@pytest.mark.asyncio(loop_scope="module")
@pytest.mark.covers(rules=["DSH-08"])
@pytest.mark.parametrize(
    "path",
    ["/js/main.js", "/css/animate.min.css", "/img/atlas_logo.svg", "/n/js/main.js"],
)
async def test__assets_serve_without_a_session(dashboard_client: httpx.AsyncClient, path: str) -> None:
    """Static assets answer an anonymous request (DSH-08), as in Atlas's ignore list.

    The fresh client holds no cookie, so a 200 here can only mean the asset path carries no gate —
    the login flow's own assets, and the dashboards' JS/CSS/images, load before and without a session.
    """
    response = await dashboard_client.get(path)

    assert response.status_code == 200
    assert "location" not in response.headers  # served, not redirected to login


# The browser fixture lives on the module loop, so the test runs there too.
@pytest.mark.asyncio(loop_scope="module")
@pytest.mark.covers(rules=["DSH-05", "DSH-06"])
@pytest.mark.parametrize("path", ["/", "/n/"], ids=["dashboardv2", "dashboardv3"])
async def test__dashboard_loads_and_asks_the_origin_for_the_session(
    browser: Browser, dashboard: str, session_cookie: str, path: str
) -> None:
    """Each dashboard loads from the dashboard image and asks it for the session (DSH-05, DSH-06).

    The page and all of its own files come from the image — the built vendored source — and the session
    call reaches the server through the same origin's proxy. The context starts on a session the gate
    accepts (6.1); the load and its XHR then behave as before.
    """
    context = await browser.new_context(ignore_https_errors=True)
    await context.add_cookies([{"name": "ATLASSESSIONID", "value": session_cookie, "url": dashboard}])
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
