import socket
import ssl
from urllib.parse import urljoin, urlsplit

import pytest
from conftest import CA_FILE
from playwright.sync_api import Page, expect

EN_PLACEHOLDER = (
    "Welcome to Aurelius Atlas! We would like to help you get started. Please pick your topic of interest below."
)
NL_PLACEHOLDER = "Welkom bij Aurelius Atlas! We helpen u graag op weg. Kies hieronder uw interessegebied."


def test__browser_facing_tls_verifies_against_ca(root_url: str) -> None:
    """The browser-facing endpoint verifies against the local development CA (SHL-11).

    Playwright's bundled browsers cannot enroll the mkcert root, so the browser
    context relaxes certificate verification (see ``conftest`` — ADR 039). This
    check performs the equivalent CA and hostname verification of the same
    endpoint: the handshake fails if nginx serves a certificate the CA did not
    issue or one that does not cover the connecting hostname.
    """
    parts = urlsplit(root_url)
    host = parts.hostname or "localhost"
    port = parts.port or 443

    context = ssl.create_default_context(cafile=str(CA_FILE))
    with (
        socket.create_connection((host, port), timeout=10) as sock,
        context.wrap_socket(sock, server_hostname=host) as tls,
    ):
        cert = tls.getpeercert()
        assert cert is not None

    subject_alt_names = {value for _type, value in cert["subjectAltName"]}
    assert host in subject_alt_names


def test__root_redirects_to_preferred_locale(page: Page, root_url: str) -> None:
    """The image redirects the root to the supported preferred locale (SHL-11)."""
    response = page.request.get(
        urljoin(root_url, "/?redirect-check=1"), headers={"Accept-Language": "nl-NL,nl;q=0.9"}, max_redirects=0
    )

    assert response.status == 302
    assert response.headers["location"].endswith("/nl-NL/?redirect-check=1")


@pytest.mark.parametrize("locale", ["en-US", "nl-NL"])
def test__locale_routes_fall_back_to_localized_app(page: Page, root_url: str, locale: str) -> None:
    """Client-side routes serve the index belonging to their locale."""
    response = page.request.get(urljoin(root_url, f"/{locale}/search/browse"))

    assert response.status == 200
    assert "text/html" in response.headers["content-type"]
    assert f'<base href="/{locale}/">' in response.text()
    assert f'lang="{locale}"' in response.text()


def test__config_json_is_served_at_the_origin_root(page: Page, root_url: str) -> None:
    """Bootstrap's runtime configuration is reachable at /config.json (SHL-02)."""
    response = page.request.get(urljoin(root_url, "/config.json"))

    assert response.status == 200
    body = response.json()
    assert body["apiBaseUrl"] == "/api"


def test__browse_placeholder_renders_in_every_browser(authenticated: Page) -> None:
    """The signed-in app boots zoneless at /search/browse and renders the Aurelius placeholder (SHL-12, APC-10).

    pytest-playwright runs this test in each of chromium, firefox and webkit
    (the e2e target passes all three), so the scenario proves cross-browser
    boot of the shell behind the auth guard — reaching the placeholder means
    Keycloak issued the session and the guard let the route through. It also
    proves SHL-02: a missing or malformed /config.json aborts bootstrap and
    nothing renders.
    """
    expect(authenticated.locator("#browse-placeholder")).to_have_text(EN_PLACEHOLDER)


def test__locale_switch_shows_localized_shell(authenticated: Page, root_url: str) -> None:
    """Switching to the nl-NL locale serves the localised shell (SHL-12).

    7.1 has no in-app language switcher (the header arrives with a later
    slice); the locale switch at the deployment layer is the locale-prefixed
    URL, so the scenario switches that way — the Keycloak session cookie makes
    the guard pass on the new locale without a second sign-in.
    """
    authenticated.goto(urljoin(root_url, "/nl-NL/search/browse"))

    expect(authenticated.locator("#browse-placeholder")).to_have_text(NL_PLACEHOLDER)
    assert authenticated.url.rstrip("/").endswith("/nl-NL/search/browse")


def test__unknown_path_falls_back_to_the_app(authenticated: Page, base_url: str) -> None:
    """An unknown client-side path serves the app, whose router redirects to browse (SHL-05)."""
    authenticated.goto(urljoin(base_url, "topic-does-not-exist"))

    expect(authenticated.locator("#browse-placeholder")).to_have_text(EN_PLACEHOLDER)


def test__api_proxy_forwards_to_the_atlas_server(page: Page, root_url: str) -> None:
    """The nginx /api/ proxy forwards to the Atlas server with the prefix intact (APC-08, DD-050).

    The real Aurelius server (DD-053) answers the admin version endpoint
    through nginx -> TLS -> server -> Elasticsearch, so the response proves
    the whole data path and that no proxy rewrites the /api prefix the client
    composes into its URLs.
    """
    response = page.request.get(urljoin(root_url, "/api/atlas/admin/version"))

    assert response.status == 200
    assert response.json()["Name"] == "aurelius-atlas"


def test__unauthenticated_visit_redirects_to_keycloak(page: Page, base_url: str) -> None:
    """An anonymous visit to a guarded route lands on the Keycloak sign-in page (APC-05, APC-10).

    The guard's check-sso finds no SSO session, so it calls login() with the
    current URL as the redirect_uri — the sign-in page's URL carries it, which
    is what returns the user to the app after signing in.
    """
    page.goto(base_url)

    page.wait_for_url("**/realms/master/protocol/openid-connect/auth**")
    assert "client_id=aurelius" in page.url
    expect(page.locator("#username")).to_be_visible()


def test__otel_proxy_forwards_to_the_collector(page: Page, root_url: str) -> None:
    """The nginx /otel/ proxy forwards to the collector with the prefix stripped (SHL-11).

    An OTLP/HTTP POST to the collector answers at /v1/traces with a
    protobuf-level status; if the proxy did not forward, nginx would answer
    502 (unresolvable upstream) or 404 (no location).
    """
    response = page.request.post(
        urljoin(root_url, "/otel/v1/traces"),
        data=b"",
        headers={"content-type": "application/x-protobuf"},
    )

    assert response.status in (200, 202, 400, 415)


def test__csp_keeps_connect_src_self(page: Page, root_url: str) -> None:
    """The CSP on the served document keeps connect-src 'self' (SHL-11)."""
    response = page.request.get(urljoin(root_url, "/en-US/"))

    csp = response.headers["content-security-policy"]
    assert "connect-src 'self'" in csp
    assert "frame-ancestors 'none'" in csp


def test__landing_renders_the_three_cards_without_api_calls(authenticated: Page) -> None:
    """The landing renders the hero and the three context cards, issuing no /api requests (BRW-01, BRW-04, BRW-07).

    The screen exists before its API does: the requests recorded across a
    reload of the landing must contain no /api call — the search affordances
    that would need one are deferred (DD-054).
    """
    api_requests: list[str] = []
    authenticated.on("request", lambda request: api_requests.append(request.url))

    authenticated.reload()
    expect(authenticated.locator("#browse-placeholder")).to_have_text(EN_PLACEHOLDER)

    hero = authenticated.locator(".box h2.title")
    expect(hero).to_have_text("Getting started")

    card_titles = authenticated.locator(".columns .column .card .media-content .title.is-4")
    expect(card_titles).to_have_text(["Business context", "Technical context", "Data governance organization"])

    assert [url for url in api_requests if "/api/" in url] == []


def test__info_modal_opens_and_closes(authenticated: Page) -> None:
    """A card's info icon opens its modal with the legacy rows; closing returns to the landing (BRW-03, BRW-07).

    The info button's accessible name is the modal title, so it is addressable
    by role; the modal's Bulma content mounts under ``.modal`` and the close
    button is the card anatomy's delete control.
    """
    modal = authenticated.locator(".modal")
    expect(modal).to_be_hidden()

    authenticated.get_by_role("button", name="Business context", exact=True).click()
    expect(modal).to_be_visible()
    expect(modal.locator(".modal-card-title")).to_have_text("Business context")
    expect(modal.locator("tbody th")).to_have_text(["Data Domain", "Data Entity", "Data Attribute"])

    modal.locator(".modal-card-head button.delete").click()
    expect(modal).to_be_hidden()


def test__landing_renders_dutch_card_titles(authenticated: Page, root_url: str) -> None:
    """The nl-NL locale renders the Dutch landing strings through the bridge (BRW-02, BRW-07)."""
    authenticated.goto(urljoin(root_url, "/nl-NL/search/browse"))

    card_titles = authenticated.locator(".columns .column .card .media-content .title.is-4")
    expect(card_titles).to_have_text(["Business context", "Technische context", "Data governance organisatie"])
