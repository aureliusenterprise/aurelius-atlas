"""E2E: targeted resilience (9.1, RSL-03, DD-214) — the logout round-trip.

The unit suites fake the IdP (an ``HttpTestingController`` logout, a stubbed
keycloak service); this file round-trips the real Keycloak: sign in, log out
at the navbar, and the IdP session ends — the guard lands the app on the
sign-in page and signing in again restores the greeted shell (RSL-03).

The real-container outage scenario that shared this file (RSL-01) is retired
by DD-281: its fixture stops compose containers through the docker SDK,
which the Helm/minikube lane has no counterpart for.
"""

from conftest import Settings
from playwright.sync_api import Page, expect


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
