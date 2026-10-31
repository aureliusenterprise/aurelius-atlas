"""E2E fixtures: the deployed shell at the edge, the collector legs, and the mints (DD-284).

The suite's one target is the Helm umbrella of ``tools/cluster/install.sh up``:
the browser and the API/OTel proxies ride the whole deployment — Gateway, the
webapp chart's nginx (the shipped template, resolved by the chart's init
container), backend TLS to the server — under the edge hostname whose HTTPRoute
serves it, so SNI and certificate verification stay honest (the chart's edge
leaf carries this SAN). The collector and Tempo legs are the cluster's own
services, port-forwarded to the loopback ports the test modules name as
constants (CHT-104's ``local_port`` pin, migrated from the compose stack's
fixed publishes unchanged). The cluster machinery is
aurelius-atlas-cluster-lane's (10.5b, DD-282/283); this conftest names only
what is the webapp suite's own shape — which services it dials, which identity
it signs in as.

The browser legs need the hosts block (``tools/cluster/install.sh hosts``,
CHT-106): Playwright's bundled browsers resolve names outside this process,
so the in-process shim (CHT-104) cannot carry them — the fenced /etc/hosts
entry is what makes ``atlas.atlas.test`` and ``keycloak.atlas.test`` dialable
from a browser.
"""

import re
import ssl
import sys
import time
from collections.abc import Generator, Iterator

import httpx2 as httpx
import pytest
from aurelius_atlas_cluster_lane import SecretReader, ServiceForward, install_cluster_fixtures, mint_token
from playwright.sync_api import Browser, Page
from playwright.sync_api import Error as PlaywrightError
from pydantic import SecretStr
from tenacity import RetryCallState, retry, retry_if_exception_type, stop_after_attempt, wait_fixed

# The cluster shapes (the umbrella install of tools/cluster/install.sh).
RELEASE = "atlas"
NAMESPACE = "atlas"
EDGE_HOST = "atlas.atlas.test"
"""The Gateway hostname whose HTTPRoute serves the webapp edge (CHT-50)."""
ISSUER = "https://keycloak.atlas.test/realms/master"
"""The edge-routed issuer: CoreDNS rewrites it in-cluster (DD-265), the
resolver/hosts block map it here — the pods' own issuer origin."""
KEYCLOAK_USERS_SECRET = "atlas-keycloak-users"
"""The release Secret carrying the smoke users' passwords (CHT-78)."""
OTEL_CLIENTS_SECRET = "atlas-otel-clients"
"""The release Secret carrying the otel-atlas-server client secret (CHT-78)."""
COLLECTOR_LEGACY_SECRET = "atlas-collector-legacy"
"""The release Secret carrying the shared legacy ingest token (CHT-78)."""

# The collector legs (the chart's Service, the compose stack's publishes): the
# direct-ingest tests dial them on loopback through a port-forward pinned at
# these ports (CHT-104's local_port). The legs serve TLS whose certificate
# carries the "otel-collector" SAN; the dials here are the raw loopback
# endpoints the test modules name, verified by the tokens they carry rather
# than the transport (ADR 039's named relaxation, as under compose).
COLLECTOR_HOST = "127.0.0.1"
COLLECTOR_PORT = 4318
SERVICE_PORT = 4319
LEGACY_PORT = 4321
COLLECTOR_SERVICE = f"{RELEASE}-observability"

# Tempo's query API on the same chart (Service port 3200, plain HTTP): the
# attribution probe reads back through it — the resource predicates prove the
# collector stamped the user onto the telemetry (CIA-05, DD-194).
TEMPO_HOST = "127.0.0.1"
TEMPO_PORT = 3200
TEMPO_SERVICE = f"{RELEASE}-observability-tempo"

# The sign-in identity (APC-10): the realm's smoke writer, whose password the
# release Secret carries. The username is what the navbar greets with
# (SHC-09's pin), so it is a constant, not configuration.
SIGN_IN_USER = "aurelius-writer"

MINT_TIMEOUT_SECONDS = 120.0
"""How long to wait for the realm to serve tokens (a warming stack may be starting up)."""

# The session `cluster` gate, the autouse resolver shim, and `ca_file` come
# from the library (CHT-103).
install_cluster_fixtures(sys.modules[__name__])


class Settings:
    """Test configuration: the dev identity the browser signs in as (APC-10).

    Migrated from the pydantic-settings class: on the cluster the identity is
    the release's own smoke user (the Secret is the source, not the Nx-
    injected environment), so there is nothing left to load.
    """

    auth_realm_name: str = "master"
    """The realm the tokens are minted from."""

    username: str = SIGN_IN_USER
    """The dev user the browser signs in as."""

    def __init__(self, password: SecretStr) -> None:
        self.password = password
        """The dev user's password; never shown in logs."""


@pytest.fixture(scope="session")
def settings() -> Settings:
    """The sign-in identity, with the password read from the release's Secret (CHT-103)."""
    password = SecretReader(NAMESPACE).read(KEYCLOAK_USERS_SECRET, "writer-password")
    return Settings(SecretStr(password))


@pytest.fixture(scope="session")
def root_url(_cluster_dns: None) -> str:
    """The origin root URL: the edge hostname through the installed umbrella.

    Traffic rides the whole deployment — Gateway, the webapp's nginx, backend
    TLS to the server — not a bypass (the server suite's rule, shared for the
    shell's own scenarios: the guard's redirect, the locale tree, the proxies).
    """
    return f"https://{EDGE_HOST}/"


@pytest.fixture(scope="session")
def base_url(root_url: str) -> str:
    """The en-US app URL for the application."""
    return f"{root_url}en-US/"


@pytest.fixture(scope="session", autouse=True)
def _collector_legs(_cluster_dns: None) -> Iterator[None]:
    """Forward the collector's three HTTP legs and Tempo's query API to their pinned ports.

    The test modules name these loopback endpoints as constants (the compose
    stack's fixed publishes); the forwards pin the same ports (CHT-104's
    ``local_port``). Readiness is curl exit 0 on the leg — a 401 answer is
    ready (the receiver is up), a refused connection is not. Session-scoped
    and autouse: the direct-ingest tests dial the raw ports with no fixture
    of their own, and one process-wide set of forwards owns them.

    These are the suite's only 127.0.0.1 dials (CHT-104's sanctioned shape,
    like the server suite's baked-dashboard forward): the loopback URL is
    what the migrated test modules speak, and the legs' credentials — not
    the transport — are what those scenarios measure.
    """
    legs = [
        ServiceForward(
            COLLECTOR_SERVICE,
            port,
            COLLECTOR_HOST,
            namespace=NAMESPACE,
            probe_path="/v1/traces",
            insecure=True,
            local_port=port,
        )
        for port in (COLLECTOR_PORT, SERVICE_PORT, LEGACY_PORT)
    ] + [
        ServiceForward(
            TEMPO_SERVICE,
            TEMPO_PORT,
            TEMPO_HOST,
            namespace=NAMESPACE,
            probe_path="/ready",
            scheme="http",
            local_port=TEMPO_PORT,
        ),
    ]
    with legs[0], legs[1], legs[2], legs[3]:
        yield


def _clear_cookies(retry_state: RetryCallState) -> None:
    """Start the next login attempt from a clean cookie jar."""
    page: Page = retry_state.kwargs.get("page") or retry_state.args[0]
    page.context.clear_cookies()


def _sign_in(page: Page, base_url: str, settings: Settings) -> None:
    """Run the Keycloak form login, and wait for the authenticated app.

    The page sits on the login form (the auth guard's redirect landed there);
    fill it, sign in, and settle: the navbar renders once the SPA's check-sso
    handshake has traded the SSO session for tokens, so a caller can trust
    the page — and the context's cookies — as signed in (APC-05, APC-10).
    """
    page.wait_for_url(re.compile(f"/realms/{settings.auth_realm_name}/protocol/openid-connect/auth"))
    page.locator("#username").fill(settings.username)
    page.locator("#password").fill(settings.password.get_secret_value())
    page.get_by_role("button", name="Sign in").click()

    page.wait_for_url(re.compile(base_url))

    page.locator("nav.navbar").wait_for(state="visible", timeout=30_000)


def _wait_signed_in(page: Page) -> bool:
    """Watch the boot: True when the app renders, False when Keycloak's form answers.

    The auth guard's redirect and the SPA boot race by design; the navbar is
    the app's own chrome (the Keycloak form has none), so the first of the two
    to appear decides. The poll interval bounds the common path's cost: a
    replayed session shows the navbar in ~1s, a form lands within the first
    polls (DD-224).
    """
    deadline = time.monotonic() + 15
    while time.monotonic() < deadline:
        if "/realms/" in page.url:
            return False
        if page.locator("nav.navbar").count() > 0:
            return True
        page.wait_for_timeout(250)
    return False


@pytest.fixture(scope="session")
def _storage_state(
    tmp_path_factory: pytest.TempPathFactory,
    browser: Browser,
    base_url: str,
    settings: Settings,
) -> str:
    """Sign in once per browser and save the session as a Playwright storage state (DD-224).

    The suite's ~37 authenticated tests per browser each used to run the full
    Keycloak form login. What a login leaves behind is the realm's SSO session
    (``KEYCLOAK_IDENTITY``, a 30-minute idle window refreshed by every visit),
    and the SPA boots with ``check-sso`` and a silent-iframe redirect (APC-05):
    a test context that starts from this state mints its own access tokens
    from the stored SSO session, with no login form. The user's password never
    enters the state — it carries cookies, not credentials.

    A navigation can be aborted mid-boot when the edge is cold (its first TLS
    handshakes, the SPA's first bundle through a cold Gateway), so each retry
    starts from a clean cookie jar: Keycloak may already have issued the
    session on the failed pass.
    """
    state_path = str(tmp_path_factory.mktemp("auth") / "state.json")

    @retry(
        retry=retry_if_exception_type(PlaywrightError),
        stop=stop_after_attempt(2),
        wait=wait_fixed(1),
        reraise=True,
        before_sleep=_clear_cookies,
    )
    def sign_in(page: Page) -> None:
        page.goto(base_url)

        _sign_in(page, base_url, settings)

    context = browser.new_context(ignore_https_errors=True)
    try:
        sign_in(page=context.new_page())

        context.storage_state(path=state_path)
    finally:
        context.close()

    return state_path


@pytest.fixture
def authenticated(
    browser: Browser,
    browser_context_args: dict,
    _storage_state: str,
    base_url: str,
    settings: Settings,
) -> Generator[Page]:
    """
    Return a page signed in through Keycloak (APC-05 / APC-10, DD-224).

    Every webapp route sits behind the auth guard (DD-141), so the page tests
    start from here. The Keycloak SSO session captured once per browser
    (``_storage_state``) rides the new context: the SPA's check-sso boot
    mints the test's own access tokens from it, and no login form runs. The
    context is the test's own — cookies, storage and cache stay isolated the
    way the per-test form login left them.

    Self-healing: when the page lands on the login form anyway — the shared
    session died (the resilience suite's logout test ends the realm session,
    DD-153/RSL-03) — the fixture runs the form login and refreshes the shared
    state, so the next test replays from a live session again.
    """
    context = browser.new_context(storage_state=_storage_state, **browser_context_args)
    try:
        page = context.new_page()
        page.goto(base_url)

        if not _wait_signed_in(page):
            _sign_in(page, base_url, settings)
            context.storage_state(path=_storage_state)

        yield page
    finally:
        context.close()


@pytest.fixture(scope="session")
def browser_context_args(browser_context_args: dict) -> dict:  # noqa: ARG001
    """Trust the chart's self-signed chain in Playwright browsers.

    Playwright's bundled browsers ship their own trust stores and cannot
    enroll the cert-manager self-signed CA (cert-manager's CA injection is a
    per-pod volume mount, not a browser profile), so page navigation skips
    browser certificate verification. This is the one named relaxation of the
    browser-facing path (ADR 039): every non-browser dial here verifies the
    chain against the chart CA (the lane's ``ca_file``), nginx still verifies
    its proxies with ``proxy_ssl_verify``, and the certificate wiring is the
    chart contract suite's own ground.
    """
    return {"ignore_https_errors": True}


@pytest.fixture(scope="session")
def ingest_token() -> str:
    """The shared collector ingest token, read from the release Secret (DD-193, CHT-103)."""
    return SecretReader(NAMESPACE).read(COLLECTOR_LEGACY_SECRET, "token")


@pytest.fixture
def user_token(ca_file: str, settings: Settings) -> str:
    """A real user access token minted by the cluster's Keycloak (DD-193, CIA-01/02).

    The password grant for the dev sign-in user (the same ``aurelius`` client
    the SPA rides, ``directAccessGrantsEnabled``): the token carries the
    ``otel-collector`` audience the realm's otel-ingest scope mints, which is
    what the collector's OIDC receiver requires. Minted at
    ``https://keycloak.atlas.test`` — the same issuer origin the deployed pods
    verify against (DD-265) — verified against the chart CA.

    Function-scoped on purpose: the suite runs each test once per browser and
    the stamping probes ride late — a session-scoped token is stale by the
    last browser (the dev realm's lifespan is what it is).
    """
    return mint_token(
        ISSUER.rsplit("/realms/", 1)[0],
        settings.password.get_secret_value(),
        realm=settings.auth_realm_name,
        username=settings.username,
        ca_file=ca_file,
        timeout=MINT_TIMEOUT_SECONDS,
    )


@pytest.fixture
def service_token(ca_file: str) -> str:
    """A client-credentials token for the otel-atlas-server ingest client (DD-196, CIA-06/07).

    The same grant the graduated producers present on the per-service leg:
    the realm's confidential ``otel-atlas-server`` client (the realm asset's
    service account) with the secret the release's ``atlas-otel-clients``
    Secret carries. Function-scoped: the browser loop outlives any token
    (the ``user_token`` fixture's rule, same for the client grant).
    """
    secret = SecretReader(NAMESPACE).read(OTEL_CLIENTS_SECRET, "OTEL_INGEST_CLIENT_SECRET")
    response = httpx.post(
        f"{ISSUER}/protocol/openid-connect/token",
        data={
            "grant_type": "client_credentials",
            "client_id": "otel-atlas-server",
            "client_secret": secret,
        },
        verify=ssl.create_default_context(cafile=ca_file),
        timeout=30,
    )
    response.raise_for_status()
    return str(response.json()["access_token"])
