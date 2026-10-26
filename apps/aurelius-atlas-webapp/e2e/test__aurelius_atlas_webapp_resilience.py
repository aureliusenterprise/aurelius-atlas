"""E2E: targeted resilience (9.1, RSL-01/RSL-03, DD-214) — real-container failures.

The unit suites fake the outage (a stopping transport, an erroring
HttpTestingController); this file stops the real container. Two scenarios,
one per visible failure surface, each bounded by the polls inside (the
review's 2-minute budget, DD-214):

- the Atlas server down: nginx's /api/ proxy answers 502 (the resolver's 10s
  cache, e2e/config/nginx.conf), and the shell surfaces the outage the way
  ALR-05 promises — the bell's dot, the drawer naming the failed call — and
  recovers on the next call once the container is back (RSL-01);
- the logout round-trip: Logout ends the session at the real Keycloak, the
  guard redirects to sign-in, and signing in again restores the app (RSL-03).

The file sorts after the main suite so the outage never touches the other
tests, and the outage fixture's finalizer always starts the container — a
crashed test must not leave the dev stack down.
"""

import time
from collections.abc import Iterator
from urllib.parse import urljoin

import pytest
from conftest import Settings
from docker import from_env as docker_from_env
from docker.models.containers import Container
from playwright.sync_api import Page, expect
from playwright.sync_api import TimeoutError as PlaywrightTimeoutError

E2E_PROJECT = "aurelius-atlas-webapp-e2e"
"""The compose project of this suite's stack (docker-compose.yaml `name:`)."""

OUTAGE_DEADLINE_SECONDS = 60
"""How long nginx may keep answering from its DNS cache after the stop."""

RECOVERY_DEADLINE_SECONDS = 90
"""How long the restarted server may take to answer through nginx again."""


def _stack_container(service: str) -> Container:
    """The running container of a service of this suite's compose stack.

    Found by compose labels (the collector fixture's pattern, CIA-03) rather
    than by generated name, so a project-name change cannot break the lookup.
    @param service the compose service name
    @returns the container handle
    """
    client = docker_from_env()
    containers = client.containers.list(
        all=True,
        filters={
            "label": [
                f"com.docker.compose.project={E2E_PROJECT}",
                f"com.docker.compose.service={service}",
            ]
        },
    )
    if not containers:
        message = f"no container of service {service!r} in project {E2E_PROJECT}"
        raise ValueError(message)
    container = containers[0]
    container.reload()
    return container


def _poll_proxy_status(page: Page, root_url: str, expected: int, deadline_seconds: float) -> int:
    """Poll the version endpoint through nginx until it answers `expected`.

    The probe is the same data path the browser's calls take (nginx /api/
    proxy, TLS, server), so it measures what the alert measures. Each probe
    carries a short timeout: mid-restart the TCP connect can hang (the
    container's endpoint exists, the SYN goes unanswered), and a hung probe
    must count as "not yet" — the deadline, not Playwright's 30 s default,
    bounds the poll.
    @param page the Playwright page (its request context ignores the dev CA)
    @param root_url the app origin
    @param expected the status to wait for
    @param deadline_seconds the budget
    @returns the observed status, -1 if no probe answered in time
    """
    deadline = time.monotonic() + deadline_seconds
    status = -1
    while time.monotonic() < deadline:
        try:
            response = page.request.get(
                urljoin(root_url, "/api/atlas/admin/version"), ignore_https_errors=True, timeout=5_000
            )
            status = response.status
        except PlaywrightTimeoutError:
            status = -1
        if status == expected:
            return status
        time.sleep(2)
    return status


@pytest.fixture
def atlas_server_page_down() -> Iterator[Container]:
    """Stop the Atlas server of the stack and guarantee it is running again.

    The finalizer starts the container unconditionally: the outage is this
    suite's own doing, and a crashed assertion must not leave the shared dev
    stack down for the next run.
    """
    container = _stack_container("atlas-server")
    container.stop(timeout=5)
    try:
        yield container
    finally:
        container.reload()
        if container.status != "running":
            container.start()


def test__a_server_outage_surfaces_an_alert_and_the_app_recovers(
    atlas_server_page_down: Container,  # noqa: ARG001  # the outage itself is the arrangement
    authenticated: Page,
    root_url: str,
) -> None:
    """RSL-01: with the server down, the shell surfaces the outage; with it back, the next call succeeds.

    No reload, no manual repair. The probe: the settings panel's session call
    (the shell's one construction-time /api call, SPL-14). During the outage
    it answers nginx's 502, and the alerts chain (ALR-05) reports it: the
    bell's dot and the drawer's row. After the restart the same panel opens
    clean: the dot is gone (opening read the feed, ALR-12) and a fresh
    session call adds no new alert.
    """
    page = authenticated

    # 1. The outage reaches the data path: nginx answers 502 (resolver cache
    #    expiry, e2e/nginx.conf — valid=10s).
    assert _poll_proxy_status(page, root_url, 502, OUTAGE_DEADLINE_SECONDS) == 502

    # 2. The shell surfaces it: open the settings panel (the gear), whose
    #    session call fails, then read the bell + the drawer.
    gear = page.locator('a.navbar-item[aria-label="Settings"]')
    gear.click()
    expect(page.locator(".aurelius-drawer-panel")).to_be_visible()
    page.locator(".aurelius-drawer-panel button.delete").first.click()  # close

    expect(page.locator('a.navbar-item[aria-label="Alerts"] .aurelius-badge-dot')).to_be_visible()

    alerts_link = page.locator('a.navbar-item[aria-label="Alerts"]')
    alerts_link.click()
    feed = page.locator(".aurelius-alert-list")
    expect(feed).to_be_visible()
    first_message = feed.locator(".aurelius-alert-message").first
    expect(first_message).to_contain_text("Request failed: GET /api/atlas/admin/session 502")

    # Opening read the feed (ALR-12): the dot goes.
    expect(page.locator('a.navbar-item[aria-label="Alerts"] .aurelius-badge-dot')).to_have_count(0)

    # 3. Recovery: start the server (the fixture's finalizer guarantees the
    #    start; do it explicitly so the poll below races nothing), and the
    #    data path answers again.
    container: Container = _stack_container("atlas-server")
    if container.status != "running":
        container.start()
    assert _poll_proxy_status(page, root_url, 200, RECOVERY_DEADLINE_SECONDS) == 200

    # The app recovers in place: a fresh panel open makes a session call that
    # succeeds, so no new alert arrives (the dot stays away).
    page.locator(".aurelius-drawer-panel button.delete").first.click()  # close alerts
    gear.click()
    expect(page.locator(".aurelius-drawer-panel")).to_be_visible()
    page.locator(".aurelius-drawer-panel button.delete").first.click()  # close settings
    expect(page.locator('a.navbar-item[aria-label="Alerts"] .aurelius-badge-dot')).to_have_count(0)


def test__logout_returns_to_sign_in_and_signing_in_again_restores_the_app(
    authenticated: Page,
    settings: Settings,
    base_url: str,
) -> None:
    """RSL-03: Logout ends the Keycloak session (SHC-05, APC-05/10).

    The dropdown is Bulma's CSS-hover (DD-153: Logout is an anchor): hover
    opens it, the click ends the session at the IdP and lands the app on the
    origin. The guard's check-sso then finds no SSO session and redirects to
    Keycloak's login — the same page the ``authenticated`` fixture signs
    through — and signing in again returns the greeted app: the round-trip
    completes, twice.
    """
    page = authenticated

    page.locator(".navbar-link").hover()
    logout = page.locator('a.navbar-item[role="button"]', has_text="Logout")
    expect(logout).to_be_visible()
    logout.click()

    # The session is gone at the IdP: the guard redirects to sign-in.
    page.wait_for_url("**/realms/master/protocol/openid-connect/auth**", wait_until="domcontentloaded")
    assert "client_id=aurelius" in page.url

    # Sign in again: the guard's redirect_uri brings the app back, greeted.
    page.locator("#username").fill(settings.username)
    page.locator("#password").fill(settings.password.get_secret_value())
    page.get_by_role("button", name="Sign in").click()
    page.wait_for_url(f"{base_url}**", wait_until="domcontentloaded")

    expect(page.locator(".navbar-link")).to_contain_text(settings.username)
