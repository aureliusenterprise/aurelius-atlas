import base64
import json
import re
import secrets
import time
from collections.abc import Callable
from datetime import UTC, datetime
from urllib.parse import quote, urljoin

import pytest
from conftest import (
    COLLECTOR_HOST,
    COLLECTOR_PORT,
    LEGACY_PORT,
    SERVICE_PORT,
    TEMPO_HOST,
    TEMPO_PORT,
    _goto_app,
)
from playwright.sync_api import Locator, Page, Route, expect

EN_PLACEHOLDER = (
    "Welcome to Aurelius Atlas! We would like to help you get started. Please pick your topic of interest below."
)
NL_PLACEHOLDER = "Welkom bij Aurelius Atlas! We helpen u graag op weg. Kies hieronder uw interessegebied."


# impact=severe, likelihood=low (the spine path moves rarely between increments)
@pytest.mark.high
def test__root_redirects_to_preferred_locale(page: Page, root_url: str) -> None:
    """The image redirects the root to the supported preferred locale (SHL-11)."""
    response = page.request.get(
        urljoin(root_url, "/?redirect-check=1"), headers={"Accept-Language": "nl-NL,nl;q=0.9"}, max_redirects=0
    )

    assert response.status == 302
    assert response.headers["location"].endswith("/nl-NL/?redirect-check=1")


# impact=severe, likelihood=low (the spine path moves rarely between increments)
@pytest.mark.high
@pytest.mark.parametrize("locale", ["en-US", "nl-NL"])
def test__locale_routes_fall_back_to_localized_app(page: Page, root_url: str, locale: str) -> None:
    """Client-side routes serve the index belonging to their locale."""
    response = page.request.get(urljoin(root_url, f"/{locale}/search/browse"))
    body = response.text()

    assert response.status == 200
    assert "text/html" in response.headers["content-type"]
    # The base tag's void-element serialisation is `>` (beasties) or `/>`
    # (Angular raw, DD-149) — accept both.
    assert re.search(rf'<base href="/{locale}/"\s*/?>', body)
    assert f'lang="{locale}"' in body


# impact=severe, likelihood=low (bootstrap stops the app; the boot test is the backstop)
@pytest.mark.high
def test__config_json_is_served_at_the_origin_root(page: Page, root_url: str) -> None:
    """Bootstrap's runtime configuration is reachable at /config.json (SHL-02)."""
    response = page.request.get(urljoin(root_url, "/config.json"))

    assert response.status == 200
    body = response.json()
    assert body["apiBaseUrl"] == "/api"
    assert body["atlasClientId"] == "aurelius-atlas-server"  # EDT-09, DD-324


@pytest.mark.critical
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


# impact=major, likelihood=low (the locale promise in its own shell)
@pytest.mark.medium
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


# impact=minor, likelihood=low (a rare mistyped path)
@pytest.mark.low
def test__unknown_path_falls_back_to_the_app(authenticated: Page, base_url: str) -> None:
    """An unknown client-side path serves the app, whose router redirects to browse (SHL-05)."""
    authenticated.goto(urljoin(base_url, "topic-does-not-exist"))

    expect(authenticated.locator("#browse-placeholder")).to_have_text(EN_PLACEHOLDER)


# impact=severe, likelihood=low (all api traffic; every signed-in suite is the backstop)
@pytest.mark.high
def test__api_proxy_forwards_to_the_atlas_server(page: Page, root_url: str) -> None:
    """The nginx /api/ proxy forwards to the Atlas server with the prefix intact (APC-08, DD-139).

    The real Aurelius server (DD-142) answers the admin status endpoint, which
    needs no user (6.1a, AUT-01), through nginx -> TLS -> server, so the
    response proves the proxy path and that no proxy rewrites the /api prefix
    the client composes into its URLs.
    """
    response = page.request.get(urljoin(root_url, "/api/atlas/admin/status"))

    assert response.status == 200
    assert response.json()["Status"] == "ACTIVE"


@pytest.mark.critical
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


# impact=minor, likelihood=medium (a tracing probe, the only proof of the /otel/ leg)
@pytest.mark.medium
def test__otel_proxy_forwards_to_the_collector(page: Page, root_url: str, user_token: str) -> None:
    """The nginx /otel/ proxy forwards to the collector with the prefix stripped (SHL-11, CIA-02).

    An OTLP/HTTP POST to the collector answers at /v1/traces with a
    protobuf-level status; if the proxy did not forward, nginx would answer
    502 (unresolvable upstream) or 404 (no location). The collector's browser
    leg demands the signed-in user's token (DD-193) and the proxy passes the
    Authorization header through untouched — reaching the collector (any of
    those statuses, never 401) proves the passthrough.
    """
    response = page.request.post(
        urljoin(root_url, "/otel/v1/traces"),
        data=b"",
        headers={"content-type": "application/x-protobuf", "authorization": f"Bearer {user_token}"},
    )

    assert response.status in (200, 202, 400, 415)


# impact=minor, likelihood=medium (a tracing auth probe, the only proof)
@pytest.mark.medium
def test__otel_proxy_passes_authorization_through(page: Page, root_url: str) -> None:
    """The /otel/ proxy injects nothing: a token-less push is the collector's 401 (CIA-01, CIA-02).

    The browser leg authenticates the user (DD-193), so a push without a
    bearer rides the proxy all the way to the OIDC receiver and comes back
    401 — the proxy is a pipe, not a credential. (The signed-in SPA attaches
    the user token itself, app.config.ts.)
    """
    response = page.request.post(
        urljoin(root_url, "/otel/v1/traces"),
        data=b"",
        headers={"content-type": "application/x-protobuf"},
    )

    assert response.status == 401


# impact=minor, likelihood=medium (an ingest posture probe, no backstop)
@pytest.mark.medium
def test__collector_rejects_unauthenticated_ingest(page: Page) -> None:
    """The collector's browser leg (OIDC) demands the user's token (CIA-01).

    The direct POST rides the loopback publish (127.0.0.1:4318, the pin CIA-03
    proves). The CA is the shared dev CA; the context relaxes browser
    verification (conftest, ADR 039's named relaxation) — the token, not the
    transport, is what this scenario measures.
    """
    response = page.request.post(
        f"https://{COLLECTOR_HOST}:{COLLECTOR_PORT}/v1/traces",
        data=b"",
        headers={"content-type": "application/x-protobuf"},
    )

    assert response.status == 401


# impact=minor, likelihood=medium (an ingest posture probe, no backstop)
@pytest.mark.medium
def test__collector_accepts_a_user_token_on_the_browser_leg(page: Page, user_token: str) -> None:
    """A Keycloak-minted user token authenticates the browser leg (CIA-01, positive control).

    The token carries the otel-collector audience (the realm's otel-ingest
    scope) and the issuer the receiver validates — an empty protobuf body
    answers 200 once the OIDC checks pass: "not 401" is the point.
    """
    response = page.request.post(
        f"https://{COLLECTOR_HOST}:{COLLECTOR_PORT}/v1/traces",
        data=b"",
        headers={"content-type": "application/x-protobuf", "authorization": f"Bearer {user_token}"},
    )

    assert response.status in (200, 202, 400, 415)


# impact=minor, likelihood=medium (a telemetry stamp probe, no backstop)
@pytest.mark.medium
def test__collector_stamps_the_user_onto_the_telemetry(page: Page, user_token: str) -> None:
    """A browser-leg push carries the token's `sub` onto the telemetry (CIA-05, DD-194).

    The collector's OIDC receiver keeps the verified claims in the request
    context and the resource processor copies ``auth.claims.sub`` to the
    ``enduser.id`` resource attribute. The probe: mint a user token, decode
    its ``sub``, push a uniquely-identified span (OTLP/HTTP JSON) through the
    browser leg, then read the trace back from Tempo and assert its resource
    carries the ``sub`` — the identity rode the data all the way into the
    queryable backend (and a forged push is attributable to the minting
    account, CIA-05's second clause).
    """
    claims = json.loads(base64.urlsafe_b64decode(user_token.split(".")[1] + "=="))
    sub = claims["sub"]
    trace_id = secrets.token_hex(16)
    now_ns = time.time_ns()
    probe = {
        "resourceSpans": [
            {
                "resource": {
                    "attributes": [{"key": "service.name", "value": {"stringValue": "e2e-attribution-probe"}}]
                },
                "scopeSpans": [
                    {
                        "scope": {"name": "e2e-attribution-probe"},
                        "spans": [
                            {
                                "traceId": trace_id,
                                "spanId": secrets.token_hex(8),
                                "name": "cia-05-attribution-probe",
                                "kind": 1,
                                "startTimeUnixNano": str(now_ns - 10**8),
                                "endTimeUnixNano": str(now_ns),
                                "attributes": [],
                            }
                        ],
                    }
                ],
            }
        ]
    }

    push = page.request.post(
        f"https://{COLLECTOR_HOST}:{COLLECTOR_PORT}/v1/traces",
        data=json.dumps(probe),
        headers={"content-type": "application/json", "authorization": f"Bearer {user_token}"},
    )
    assert push.status == 200

    # Tempo flushes the live store continuously; poll trace-by-id (the
    # deterministic read-back: Tempo 3.1's live-store search indexes span
    # attributes, resource-scope predicates need backend blocks, and the
    # route is the plural api/traces/ — singular api/trace/ 404s). The
    # resource attribute is what proves the identity rode the data all the
    # way into storage.
    deadline = time.monotonic() + 60
    while time.monotonic() < deadline:
        fetched = page.request.get(
            f"http://{TEMPO_HOST}:{TEMPO_PORT}/api/traces/{trace_id}",
            params={"encoding": "json"},
        )
        if fetched.status == 200:
            attrs: dict[str, str] = {}
            for line in fetched.text().strip().splitlines():
                for batch in json.loads(line).get("batches", []):
                    for attr in batch.get("resource", {}).get("attributes", []):
                        value = attr.get("value", {})
                        attrs[attr["key"]] = value.get("stringValue", value.get("intValue", ""))
            assert attrs.get("enduser.id") == sub, f"probe resource: {attrs}"
            return
        time.sleep(1)

    pytest.fail(f"Tempo never returned the probe trace attributed to {sub} — the sub claim was not stamped")


# impact=minor, likelihood=medium (a leg-isolation probe, no backstop)
@pytest.mark.medium
def test__collector_rejects_the_shared_token_on_the_browser_leg(page: Page, ingest_token: str) -> None:
    """The service credential does not open the browser leg (CIA-01).

    The legs are distinct proofs (DD-193): the shared ingest token is not a
    JWT the OIDC receiver can verify, so the push is 401 — attribution comes
    from user tokens only, and a leaked service secret cannot forge
    user-attributed telemetry.
    """
    response = page.request.post(
        f"https://{COLLECTOR_HOST}:{COLLECTOR_PORT}/v1/traces",
        data=b"",
        headers={"content-type": "application/x-protobuf", "authorization": f"Bearer {ingest_token}"},
    )

    assert response.status == 401


# impact=minor, likelihood=medium (a leg-isolation probe, no backstop)
@pytest.mark.medium
def test__collector_rejects_the_shared_token_on_the_service_leg(page: Page, ingest_token: str) -> None:
    """The shared token does not open the per-service leg (CIA-06, CIA-08).

    The per-service leg (4319) is an OIDC receiver now (DD-196): the shared
    ingest token is not a JWT the extension can verify, so the push is 401 —
    the legs are credential-typed, and a leaked shared secret can no longer
    write anonymous telemetry.
    """
    response = page.request.post(
        f"https://{COLLECTOR_HOST}:{SERVICE_PORT}/v1/traces",
        data=b"",
        headers={"content-type": "application/x-protobuf", "authorization": f"Bearer {ingest_token}"},
    )

    assert response.status == 401


# impact=minor, likelihood=medium (a leg-isolation probe, no backstop)
@pytest.mark.medium
def test__collector_rejects_a_jwt_on_the_legacy_leg(page: Page, service_token: str) -> None:
    """A Keycloak JWT does not open the legacy leg (CIA-08).

    The legacy leg (4321) is bearertokenauth: a service JWT is not the
    shared token it compares against, so the push is 401. Credential-typed
    in both directions — no bearer works on both legs.
    """
    response = page.request.post(
        f"https://{COLLECTOR_HOST}:{LEGACY_PORT}/v1/traces",
        data=b"",
        headers={"content-type": "application/x-protobuf", "authorization": f"Bearer {service_token}"},
    )

    assert response.status == 401


# impact=minor, likelihood=medium (a leg-auth probe, no backstop)
@pytest.mark.medium
def test__collector_accepts_a_service_jwt(page: Page, service_token: str) -> None:
    """A client-credentials JWT authenticates the per-service leg, stamped by client (CIA-06, CIA-07, CIA-09).

    The probe mirrors the browser-leg stamping test with the machine
    credential: mint a client-credentials token for the otel-atlas-server
    realm client (the grant the graduated producers present), push a
    uniquely-identified span to 4319 (200 — the OIDC receiver accepts
    service accounts on the same issuer/audience as users), then read the
    trace back from Tempo. The resource must carry
    ``otel.ingest.client=otel-atlas-server`` (the azp claim, CIA-09) and an
    empty ``enduser.id`` (transform/identity clears the service-account
    sub — machine pushes do not wear a user identity).
    """
    trace_id = secrets.token_hex(16)
    now_ns = time.time_ns()
    probe = {
        "resourceSpans": [
            {
                "resource": {
                    "attributes": [{"key": "service.name", "value": {"stringValue": "e2e-service-identity-probe"}}]
                },
                "scopeSpans": [
                    {
                        "scope": {"name": "e2e-service-identity-probe"},
                        "spans": [
                            {
                                "traceId": trace_id,
                                "spanId": secrets.token_hex(8),
                                "name": "cia-09-service-identity-probe",
                                "kind": 1,
                                "startTimeUnixNano": str(now_ns - 10**8),
                                "endTimeUnixNano": str(now_ns),
                                "attributes": [],
                            }
                        ],
                    }
                ],
            }
        ]
    }

    push = page.request.post(
        f"https://{COLLECTOR_HOST}:{SERVICE_PORT}/v1/traces",
        data=json.dumps(probe),
        headers={"content-type": "application/json", "authorization": f"Bearer {service_token}"},
    )
    assert push.status == 200

    # Tempo read-back by trace id (the deterministic route; see the user
    # stamping test for the api/traces/ + encoding=json pattern). The
    # resource attributes prove both halves of CIA-09: the client stamp
    # rode the verified azp, the human-identity slot stays empty.
    deadline = time.monotonic() + 60
    while time.monotonic() < deadline:
        fetched = page.request.get(
            f"http://{TEMPO_HOST}:{TEMPO_PORT}/api/traces/{trace_id}",
            params={"encoding": "json"},
        )
        if fetched.status == 200:
            attrs: dict[str, str] = {}
            for line in fetched.text().strip().splitlines():
                for batch in json.loads(line).get("batches", []):
                    for attr in batch.get("resource", {}).get("attributes", []):
                        value = attr.get("value", {})
                        attrs[attr["key"]] = value.get("stringValue", value.get("intValue", ""))
            assert attrs.get("otel.ingest.client") == "otel-atlas-server", f"probe resource: {attrs}"
            assert attrs.get("enduser.id") == "", f"probe resource: {attrs}"
            return
        time.sleep(1)

    pytest.fail(
        f"Tempo never returned the probe trace stamped for otel-atlas-server (trace {trace_id}) — azp not stamped"
    )


# impact=major, likelihood=low (the one-data-plane promise weakens; the header moves rarely)
@pytest.mark.medium
def test__csp_keeps_connect_src_self(page: Page, root_url: str) -> None:
    """The CSP on the served document keeps connect-src 'self' (SHL-11)."""
    response = page.request.get(urljoin(root_url, "/en-US/"))

    csp = response.headers["content-security-policy"]
    assert "connect-src 'self'" in csp
    assert "frame-ancestors 'none'" in csp


START_TENANCY_READ = "/api/aurelius/v1/tenancy"
"""The app start's read of the server's tenancy (TNW-02), before any screen renders."""

START_VERSION_READ = "/api/atlas/admin/version"
"""The app start's read of the server's version (VER-01, DD-733), which the shell's footer
starts behind the guard. It is the start's, not the landing's, like the tenancy read above."""


# impact=severe, likelihood=low (the screen after sign-in; a stable template, boot has a backstop)
@pytest.mark.high
def test__landing_renders_the_three_cards_without_api_calls(authenticated: Page) -> None:
    """The landing renders the hero and the three context cards, issuing no /api requests (BRW-01, BRW-04, BRW-07).

    The screen exists before its API does: the requests recorded across a
    reload of the landing must contain no /api call — the search affordances
    that would need one are deferred (DD-143). The reload restarts the app, whose
    start reads the server's tenancy (TNW-02, 15.6) and its version (VER-01, 7.34).
    Both reads are the start's, not the landing's, and are left out of the count.
    """
    api_requests: list[str] = []
    authenticated.on("request", lambda request: api_requests.append(request.url))

    authenticated.reload()
    expect(authenticated.locator("#browse-placeholder")).to_have_text(EN_PLACEHOLDER)

    hero = authenticated.locator(".box h2.title")
    expect(hero).to_have_text("Getting started")

    card_titles = authenticated.locator(".columns .column .card .media-content .title.is-4")
    expect(card_titles).to_have_text(["Business context", "Technical context", "Data governance organization"])

    start_reads = (START_TENANCY_READ, START_VERSION_READ)
    assert [url for url in api_requests if "/api/" in url and not url.endswith(start_reads)] == []


# impact=major, likelihood=low (a modal in its own screen)
@pytest.mark.medium
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


# impact=major, likelihood=low (the locale strings of the landing)
@pytest.mark.medium
def test__landing_renders_dutch_card_titles(authenticated: Page, root_url: str) -> None:
    """The nl-NL locale renders the Dutch landing strings through the bridge (BRW-02, BRW-07)."""
    authenticated.goto(urljoin(root_url, "/nl-NL/search/browse"))

    card_titles = authenticated.locator(".columns .column .card .media-content .title.is-4")
    expect(card_titles).to_have_text(["Business context", "Technische context", "Data governance organisatie"])


# impact=minor, likelihood=low (a greeting line)
@pytest.mark.low
def test__navbar_greets_the_signed_in_user(authenticated: Page) -> None:
    """The account dropdown's welcome line shows the Keycloak identity (SHC-05, SHC-09).

    ``preferred_username`` from the token, greeted through the
    shell.header.welcome bridge leaf.
    """
    welcome = authenticated.locator("a.navbar-link").filter(has_text="Logged in as")

    expect(welcome).to_be_visible()
    expect(welcome).to_have_text("Logged in as aurelius-writer")


# impact=major, likelihood=low (the locale switch in the settings panel)
@pytest.mark.medium
def test__settings_panel_language_navigates_to_the_dutch_build(authenticated: Page) -> None:
    """Choosing nl-NL in the settings panel lands on the Dutch bundle (SHC-04, SPL-06, SHC-09).

    The navbar's language dropdown moved into the settings panel (7.14,
    SPL-06): the gear opens the drawer, the panel's link is a full-page
    navigation. A real click, not a hand-written URL: the href the panel
    computes (locale prefix swap) and the nginx locale tree are exercised
    together.
    """
    gear = authenticated.locator('a.navbar-item[aria-label="Settings"]')
    gear.click()
    # The panel host's box is zero — the drawer's plate is position:fixed
    # inside it — so visibility is asserted on the plate, the visible part.
    panel = authenticated.locator(".aurelius-drawer-panel")
    expect(panel).to_be_visible()

    panel.locator('a[hreflang="nl-NL"]').click()

    # The drawer segment rides the URL through the locale reload (DD-166's
    # URL-borne open state): match the locale tree prefix, not the tail.
    authenticated.wait_for_url(re.compile(r"/nl-NL/search/browse"))
    card_titles = authenticated.locator(".columns .column .card .media-content .title.is-4")
    expect(card_titles).to_have_text(["Business context", "Technische context", "Data governance organisatie"])


# impact=minor, likelihood=low (footer text from config)
@pytest.mark.low
def test__footer_shows_the_product_name_copyright_and_version(
    authenticated: Page, root_url: str, user_token: str
) -> None:
    """The footer renders the app name, the current year, and the running version (SHC-06, SHC-09).

    Since 7.34 only the name comes from ``config.json``: the copyright prints
    the browser's current year (DD-726) and the version is the server's answer
    (VER-04, VER-01). The version is read back from the same endpoint the footer
    calls, so the pin can never drift with a release.
    """
    footer = authenticated.locator("footer.footer")
    version = authenticated.request.get(
        urljoin(root_url, "/api/atlas/admin/version"),
        headers={"authorization": f"Bearer {user_token}"},
    ).json()["Version"]

    expect(footer).to_be_visible()
    expect(footer.locator(".level-left")).to_have_text(f"Copyright {datetime.now(tz=UTC).year}")
    expect(footer.locator(".level > .level-item")).to_have_text("Aurelius Atlas Data Governance")
    expect(footer.locator(".level-right")).to_have_text(version)
    expect(footer.locator(".level-left .icon svg")).to_be_visible()  # faCopyright


# impact=minor, likelihood=low (an outbound link)
@pytest.mark.low
def test__documentation_link_points_at_the_aurelius_docs(authenticated: Page) -> None:
    """The navbar's Documentation link opens the Aurelius docs safely (SHC-03, SHC-09)."""
    link = authenticated.locator('a[target="_blank"]')

    expect(link).to_have_attribute("href", "https://aureliusenterprise.github.io/aurelius-atlas-documentation/")
    expect(link).to_have_attribute("rel", "noopener noreferrer")
    expect(link).to_have_text("Documentation")


# impact=minor, likelihood=medium (the mobile door to logout; the viewport emulation is fragile)
@pytest.mark.medium
def test__burger_menu_opens_the_dropdown_with_the_logout_entry(authenticated: Page) -> None:
    """The mobile burger opens the menu: the session's Logout is reachable (SHC-05, DD-153).

    The burger's toggle/aria-expanded/is-active logic is the ui-lib header's,
    unit-tested there; this is the real-browser flow at a phone viewport,
    signed in. The chrome's computed-style pins (DD-153's ink, plates and
    chevrons) left e2e with DD-223: interactions are guarded here, pixels
    belong to the storybook slice.
    """
    authenticated.set_viewport_size({"width": 375, "height": 667})
    burger = authenticated.locator(".navbar-burger")
    burger.click()

    logout = authenticated.locator(".navbar-dropdown button.navbar-item", has_text="Logout")
    expect(logout).to_be_visible()


# impact=major, likelihood=high (the dead-link answer; the details screen churns)
@pytest.mark.high
def test__details_screen_answers_a_404_deep_link_with_the_empty_state(authenticated: Page, root_url: str) -> None:
    """A direct visit to /search/details/<unknown guid> renders the empty screen (DET-07, DET-13).

    The URL is the screen's whole state (DD-186): the screen fetches the
    guid (DET-08), the server answers 404 (the store owns it, DET-03), and
    the screen keeps the empty shape — the fallback title, zero rows — with
    no alert for the 404 (DET-13: the empty state answers it, ALR-05's
    silence). The chrome strings ride the bridge (DET-04). The guid is
    UUID text so the request reaches the store (DV-161): a malformed one
    would be a 400 alert, which is the case the server suite pins.
    """
    authenticated.goto(urljoin(root_url, "/en-US/search/details/00000000-0000-0000-0000-000000000000"))

    expect(authenticated.locator("h1.aurelius-details-title")).to_have_text("Entity type")
    expect(authenticated.locator("#description-details .title.is-3")).to_have_text("Description")
    expect(authenticated.locator(".aurelius-details-nav .menu-label")).to_have_text("Details")
    # The description box shows the legacy placeholder line (DET-10, DD-321).
    expect(authenticated.locator(".aurelius-details-description")).to_have_count(0)
    expect(authenticated.locator(".aurelius-details-description-empty")).to_have_text("No description available.")
    # Zero rows: the legacy shell's swap shows the placeholder in place of
    # the table, headers included (DET-11).
    expect(authenticated.locator(".aurelius-details-properties")).to_have_count(0)
    expect(authenticated.locator(".aurelius-details-properties-empty")).to_have_text("No data available")
    # The 404 adds no alert (DET-13): the bell carries no unread dot.
    expect(authenticated.locator(".aurelius-badge-dot")).to_have_count(0)


# impact=major, likelihood=low (the locale chrome of the details)
@pytest.mark.medium
def test__details_skeleton_renders_dutch_chrome(authenticated: Page, root_url: str) -> None:
    """The nl-NL locale renders the Dutch details chrome through the bridge (DET-04, DET-07)."""
    authenticated.goto(urljoin(root_url, "/nl-NL/search/details/00000000-0000-0000-0000-000000000000"))

    expect(authenticated.locator("h1.aurelius-details-title")).to_have_text("Entiteit type")
    expect(authenticated.locator("#description-details .title.is-3")).to_have_text("Beschrijving")
    expect(authenticated.locator(".aurelius-details-description-empty")).to_have_text("Geen beschrijving beschikbaar.")
    expect(authenticated.locator(".aurelius-details-properties-empty")).to_have_text("Geen gegevens beschikbaar")


def _seed_entities(page: Page, root_url: str, token: str, type_name: str, names: list[str]) -> dict[str, str]:
    """Seed entities through the proxy's bulk endpoint; return the guid assignments.

    The calls carry the signed-in user's token, which the server verifies
    (6.1a, AUT-02). Names are **single tokens** carrying a unique ``run``
    word: the free-text matcher is word-exact (FTX-01/SRC-06), and the shared
    dev stack is never cleaned between runs — hyphenated names would share
    their words with every earlier run's seeds and match them (term-OR).
    """
    body = {
        "entities": [
            {
                "typeName": type_name,
                "guid": f"-{i}",
                "attributes": {"qualifiedName": name, "name": name},
            }
            for i, name in enumerate(names)
        ]
    }
    response = page.request.post(
        urljoin(root_url, "/api/atlas/v2/entity/bulk"),
        data=json.dumps(body),
        headers={"content-type": "application/json", "authorization": f"Bearer {token}"},
    )

    assert response.status == 200, response.text()

    return response.json()["guidAssignments"]


def _purge_type(page: Page, root_url: str, token: str, type_name: str) -> None:
    """Delete every entity of a type (the shared stack's determinism fix).

    The dev stack is never cleaned between runs, and the explore search is a
    type-only first page (limit 10): glossaries from earlier runs fill it and
    push this run's seed off page 1. A type-scoped purge — list by type,
    delete by guid — makes a type-filtered assertion deterministic.
    """
    listing = page.request.post(
        urljoin(root_url, "/api/atlas/v2/search/basic"),
        data=json.dumps({"typeName": type_name, "limit": 1000, "offset": 0, "excludeDeletedEntities": True}),
        headers={"content-type": "application/json", "authorization": f"Bearer {token}"},
    )

    assert listing.status == 200, listing.text()

    for entity in listing.json().get("entities", []):
        _delete_entity(page, root_url, token, entity["guid"])


def _purge_and_drop_types(
    page: Page, root_url: str, token: str, entity_types: list[str], type_names: list[str]
) -> None:
    """Delete a run's own types and every entity of them, softly first then purged.

    ENS-09 keeps a type in use while an entity of it exists in ANY state, and
    the e2e server deletes softly (DD-059): the run's soft-deleted entities
    must pass through the admin's purge (EDL-01, the hard remove) before their
    types may go, and the relationship before the entity types it names. The
    typedef delete races the purge's ES refresh, so it retries the ``has
    references`` 409 (bounded; self-cleaning only, the idiom of the
    classification cleanup).
    """
    guids: list[str] = []
    for entity_type in entity_types:
        listing = page.request.post(
            urljoin(root_url, "/api/atlas/v2/search/basic"),
            data=json.dumps(
                {"typeName": entity_type, "limit": 1000, "offset": 0, "excludeDeletedEntities": False},
            ),
            headers={"content-type": "application/json", "authorization": f"Bearer {token}"},
        )

        assert listing.status == 200, listing.text()

        guids += [entity["guid"] for entity in listing.json().get("entities", [])]

    if guids:
        purged = page.request.put(
            urljoin(root_url, "/api/atlas/admin/purge"),
            data=json.dumps(guids),
            headers={"content-type": "application/json", "authorization": f"Bearer {token}"},
        )

        assert purged.status == 200, purged.text()

    deadline = time.monotonic() + 30
    for type_name in type_names:
        while True:
            removed = page.request.delete(
                urljoin(root_url, f"/api/atlas/v2/types/typedef/name/{type_name}"),
                headers={"authorization": f"Bearer {token}"},
            )
            if removed.status in (204, 404):  # gone, or never landed
                break
            assert removed.status == 409, removed.text()
            assert time.monotonic() < deadline, removed.text()
            time.sleep(1)


@pytest.mark.critical
def test__hero_search_shows_seeded_results_in_both_locales(authenticated: Page, root_url: str, user_token: str) -> None:
    """The hero field searches: seeded hits, the count, the parentless card trail (SRH-01..SRH-05).

    A query submitted in the hero's search field runs POST
    ``/api/aurelius/v1/search`` (16.5a, VSR-03), rides into
    ``search/results?query=``, and renders a card per hit with the count
    above the box (the legacy results screen, DD-218). Clicking a card deep-links the 2.3 skeleton with
    that guid; the results URL survives so a reload re-runs the search
    (SRH-02). The nl-NL locale renders the Dutch word (SRH-10).
    """
    run = secrets.token_hex(4)
    names = [f"zz{run}alpha", f"zz{run}beta", f"zz{run}gamma"]
    query = " ".join(names)
    guids = _seed_entities(authenticated, root_url, user_token, "DataSet", names)

    authenticated.goto(urljoin(root_url, "/en-US/search"))
    field = authenticated.locator(".hero aurelius-atlas-ui-search-field input")
    expect(field).to_be_visible()
    field.fill(query)
    # The submit button, not Enter: the native `search` event on Enter is
    # Chromium-only (the legacy input shares the quirk, `(search)` only).
    authenticated.locator(".hero aurelius-atlas-ui-search-field button.button.is-success").click()

    expect(authenticated).to_have_url(re.compile(r"/en-US/search/results\?query="))
    expect(authenticated.locator(".results-count")).to_have_text(re.compile(r"3\s+results"))
    rows = authenticated.locator(".result-row")
    expect(rows).to_have_count(3)
    for name in names:
        expect(rows.filter(has_text=name)).to_have_count(1)

    # VDR-11 (16.5g): these seeds have no parent, and the trail rule asks a
    # stored parent — the legacy guard drew no trail for a parentless entity,
    # since the one crumb would repeat the card's own title (DD-630). The
    # trail body renders nothing; the filled trail rides the seeded-parentage
    # scenario below (VDR-06, DD-606).
    trail = rows.filter(has_text=names[0]).locator(".aurelius-card-trail")
    expect(trail.locator("nav")).to_have_count(0)

    # The card → details deep link (SRH-05): the clicked guid rides the URL,
    # and the header renders the live entity the read answers (7.20, DET-09).
    clicked = names[0]
    rows.filter(has_text=clicked).locator("a").first.click()
    expect(authenticated).to_have_url(re.compile(rf"/en-US/search/details/{guids['-0']}$"))
    expect(authenticated.locator("h1.aurelius-details-title")).to_have_text(clicked)

    # The results URL is the screen's state (SRH-02): reload re-runs the
    # search from the URL alone and the hero shows the query.
    authenticated.go_back()
    expect(authenticated.locator(".results-count")).to_have_text(re.compile(r"3\s+results"))
    expect(field).to_have_value(query)

    # SRH-10: the same screen in Dutch — the count word rides the bridge.
    authenticated.goto(urljoin(root_url, f"/nl-NL/search/results?query={quote(query)}"))
    expect(authenticated.locator(".results-count")).to_have_text(re.compile(r"3\s+resultaten"))


@pytest.mark.critical
def test__facet_sidebar_filters_by_type(authenticated: Page, root_url: str, user_token: str) -> None:
    """The door's answer fills the facet sidebar; ticking a type narrows the list (SDX-02..08).

    The 7.4b spine on the view search door (16.5a, VSR-03/04/06): one
    ``POST /api/aurelius/v1/search`` answers the hits and the four facets, so
    the sidebar renders a menu per non-empty facet in answer order (SDX-02/03)
    — the type facet as checkboxes (SDX-04), the state and service-type facets
    as read-only text (SDX-05). Ticking a type re-POSTs narrowed to it (the
    ``filters`` of VSR-04) while the seen-set keeps the other value visible
    with its last count (SDX-07, DD-426); unticking broadens again. The hero's
    submit clears the tick (SDX-06, DD-425). Two base-model types
    (``DataSet``, ``Process``, both outside the name dictionary) keep the
    values raw and locale-stable; the door matches whole words (AVR-04), so
    the query names this run's seeds and matches those alone. Namespaced and
    cleaned by guid (DD-223's rule on the shared store).
    """
    run = secrets.token_hex(4)
    prefix = f"zz{run}"
    datasets = [f"{prefix}alpha", f"{prefix}beta"]
    processes = [f"{prefix}proc"]
    query = " ".join([*datasets, *processes])
    ds_guids = _seed_entities(authenticated, root_url, user_token, "DataSet", datasets)
    proc_guids = _seed_entities(authenticated, root_url, user_token, "Process", processes)

    try:
        authenticated.goto(urljoin(root_url, f"/en-US/search/results?query={quote(query)}"))

        # One answer feeds the list and the sidebar: three rows, and a menu per
        # non-empty facet in answer order — type, state, service type (SDX-02).
        expect(authenticated.locator(".result-row")).to_have_count(3)
        facets = authenticated.locator(".column.is-one-third aurelius-atlas-ui-facet-list")
        expect(facets).to_have_count(3)
        expect(facets.locator(".menu-label")).to_have_text(["Type", "State", "Service Type"])

        # The type facet lists both types with their counts (DataSet 2, Process
        # 1, most first); the state and service-type facets read ACTIVE /
        # atlas_core with no checkbox (SDX-05).
        type_rows = facets.nth(0).locator(".menu-list li .label-text")
        expect(type_rows).to_have_text(["DataSet (2)", "Process (1)"])
        expect(facets.nth(0).locator("input[type=checkbox]")).to_have_count(2)
        expect(facets.nth(1).locator("input[type=checkbox]")).to_have_count(0)
        expect(facets.nth(1).locator(".menu-list li").first).to_have_text("ACTIVE (3)")
        expect(facets.nth(2).locator("input[type=checkbox]")).to_have_count(0)
        expect(facets.nth(2).locator(".menu-list li").first).to_have_text("atlas_core (3)")

        # Ticking DataSet re-POSTs narrowed to it: the list drops to its two,
        # and the seen-set keeps Process visible with its last count (SDX-04/07).
        dataset_box = authenticated.locator('.column.is-one-third input[name="DataSet"]')
        dataset_box.check()
        expect(authenticated.locator(".result-row")).to_have_count(2)
        expect(dataset_box).to_be_checked()
        expect(facets.nth(0).locator("input[type=checkbox]")).to_have_count(2)

        # Unticking broadens the list back to all three (SDX-04).
        dataset_box.uncheck()
        expect(authenticated.locator(".result-row")).to_have_count(3)

        # Ticking again, then a hero submit: the selection clears and the tick
        # goes with it (SDX-06, DD-425) — the list stays the broad three.
        dataset_box.check()
        expect(authenticated.locator(".result-row")).to_have_count(2)
        field = authenticated.locator(".hero aurelius-atlas-ui-search-field input")
        field.fill(query)
        authenticated.locator(".hero aurelius-atlas-ui-search-field button.button.is-success").click()
        expect(dataset_box).not_to_be_checked()
        expect(authenticated.locator(".result-row")).to_have_count(3)

        # SDX-08: the same sidebar in Dutch — the titles ride the bridge
        # (nl-NL: Type, Status, Servicetype). The values stay raw (base-model names).
        authenticated.goto(urljoin(root_url, f"/nl-NL/search/results?query={quote(query)}"))
        expect(authenticated.locator(".column.is-one-third .menu-label")).to_have_text(
            ["Type", "Status", "Servicetype"]
        )
    finally:
        for guid in [*ds_guids.values(), *proc_guids.values()]:
            _delete_entity(authenticated, root_url, user_token, guid)


@pytest.mark.critical
def test__meaning_mode_falls_back_to_words_on_a_server_without_embedding(
    authenticated: Page, root_url: str, user_token: str
) -> None:
    """Choosing Meaning on a server with no embedder warns and lands on the words answer (VSR-08, SBW-06).

    16.5a's door scenario: the results screen asks
    ``POST /api/aurelius/v1/search`` (VSR-03), and this stack runs no embedder,
    so the door refuses a meaning mode with 404 ``AURELIUS-404-00-001``
    (ASV-09). Picking Meaning in the settings panel (SBX-01) restarts the
    shown query (SBX-02, VSR-09), that request fails, and the known fallback
    runs (SBW-06): a warning lands in the alerts feed and the mode stores back
    to Words, whose change searches again — so the words answer renders the
    seeded row and the panel reads Words again. The door's keyword answer is
    what the rows come back on (VSR-03).
    """
    run = secrets.token_hex(4)
    name = f"zz{run}meaning"
    guids = _seed_entities(authenticated, root_url, user_token, "DataSet", [name])

    try:
        authenticated.goto(urljoin(root_url, f"/en-US/search/results?query={name}"))
        expect(authenticated.locator(".result-row")).to_have_count(1)

        gear = authenticated.locator('a.navbar-item[aria-label="Settings"]')
        gear.click()
        panel = authenticated.locator(".aurelius-drawer-panel")
        expect(panel).to_be_visible()
        panel.locator(".settings-search-mode button", has_text="Meaning").click()
        # The panel stays open over the scrim, which covers the navbar: Escape
        # dismisses it (the drawer's keyboard path) before the bell is clicked.
        authenticated.keyboard.press("Escape")

        # The failed meaning search warns (SBW-06): the alert feed carries the
        # line, through the bell's drawer.
        authenticated.locator('a.navbar-item[aria-label="Alerts"]').click()
        expect(authenticated.locator(".aurelius-alert-message")).to_have_text(
            "Search by meaning is not available on this server"
        )

        # The words answer the store fell back to is what renders: the seeded
        # row (VSR-03), and the panel — reopened — reads Words as pressed
        # again, the stored mode the fallback wrote (SBW-06, SBX-02).
        expect(authenticated.locator(".result-row")).to_have_count(1)
        authenticated.keyboard.press("Escape")
        gear.click()
        words = panel.locator(".settings-search-mode button", has_text="Words")
        expect(words).to_have_attribute("aria-pressed", "true")
    finally:
        _delete_entity(authenticated, root_url, user_token, guids["-0"])


@pytest.mark.critical
def test__details_screen_shows_a_seeded_entity(authenticated: Page, root_url: str, user_token: str) -> None:
    """A seeded entity opened at its details URL renders from the read (DET-14).

    The 7.20 data spine: the screen fetches the guid (DET-08), the header
    shows the seeded name and the type line (DET-09), and the description box
    carries the seeded ``description`` — the Atlas model types carry their
    text there (DET-10, DD-320). The properties table holds zero rows and the
    count reads 0: ``name`` and ``qualifiedName`` ride the title (blacklisted
    per DET-11), and ``description`` rides the box.
    """
    run = secrets.token_hex(4)
    name = f"zz{run}details"
    guids = _seed_entities(authenticated, root_url, user_token, "DataSet", [name])
    guid = guids["-0"]

    # The seed helper carries qualifiedName/name only; set a description
    # (EWR-15's attribute update) so the description box has its text — the
    # Atlas model types carry the text in ``description`` (DET-10, DD-320).
    updated = authenticated.request.put(
        urljoin(root_url, f"/api/atlas/v2/entity/guid/{guid}"),
        params={"name": "description"},
        data=json.dumps("A seeded description."),
        headers={"content-type": "application/json", "authorization": f"Bearer {user_token}"},
    )
    assert updated.status == 200, updated.text()

    authenticated.goto(urljoin(root_url, f"/en-US/search/details/{guid}"))

    expect(authenticated.locator("h1.aurelius-details-title")).to_have_text(name)
    expect(authenticated.locator(".aurelius-details-type")).to_contain_text("DataSet")
    expect(authenticated.locator(".aurelius-details-description")).to_have_text("A seeded description.")
    expect(authenticated.locator(".aurelius-details-property-count")).to_have_text("0")
    # Zero rows: the placeholder stands in for the whole table (DET-11).
    expect(authenticated.locator(".aurelius-details-properties")).to_have_count(0)
    expect(authenticated.locator(".aurelius-details-properties-empty")).to_have_text("No data available")


def _seed_m4i_mini_graph(page: Page, root_url: str, token: str, run: str) -> dict[str, str]:
    """Seed the DET-27/DET-34 m4i mini-graph through the proxy's bulk endpoint.

    One bulk create carries the whole graph: a domain, an entity with two
    attributes and two persons on its people ends, a field on one attribute's
    ``fields`` end, a dataset holding the field, and — since 7.21c — a system,
    a process seeded from its own ``inputs``/``outputs``/``system`` ends to the
    dataset and system, and a second process left unconnected. The ends ride
    ``relationshipAttributes`` naming the request's own temporary guids, which
    the server resolves through the request's guid assignments (REL-11 — the
    editor scenarios' edge-seed idiom, per-request this time). Names are
    single ``zz<run>`` tokens (the seed helper's word-exact rule); the
    ``beta``/``alpha`` filter terms cannot appear inside a hex run token.
    """
    names = {
        "domain": f"zz{run}domain",
        "entity": f"zz{run}entity",
        "alpha": f"zz{run}alpha",
        "beta": f"zz{run}beta",
        "field": f"zz{run}field",
        "dataset": f"zz{run}warehouse",
        "owner": f"zz{run}owner",
        "steward": f"zz{run}steward",
        "system": f"zz{run}elastic",
        "process": f"zz{run}pipeline",
        "lonely": f"zz{run}lonely",
    }

    def entity(temp_guid: str, type_name: str, key: str, **extra: object) -> dict:
        body: dict = {
            "typeName": type_name,
            "guid": temp_guid,
            "attributes": {"qualifiedName": names[key], "name": names[key]},
        }
        body.update(extra)
        return body

    body = {
        "entities": [
            entity(
                "-0",
                "m4i_data_domain",
                "domain",
                relationshipAttributes={"dataEntity": [{"guid": "-1", "typeName": "m4i_data_entity"}]},
            ),
            entity(
                "-1",
                "m4i_data_entity",
                "entity",
                relationshipAttributes={
                    "attributes": [
                        {"guid": "-2", "typeName": "m4i_data_attribute"},
                        {"guid": "-3", "typeName": "m4i_data_attribute"},
                    ],
                    "businessOwner": [{"guid": "-6", "typeName": "m4i_person"}],
                    "steward": [{"guid": "-7", "typeName": "m4i_person"}],
                },
            ),
            {
                "typeName": "m4i_data_attribute",
                "guid": "-2",
                "attributes": {
                    "qualifiedName": names["alpha"],
                    "name": names["alpha"],
                    "definition": "The alpha definition.",
                },
            },
            {
                "typeName": "m4i_data_attribute",
                "guid": "-3",
                "attributes": {
                    "qualifiedName": names["beta"],
                    "name": names["beta"],
                    "definition": "The beta definition.",
                },
            },
            entity(
                "-4",
                "m4i_field",
                "field",
                relationshipAttributes={"attributes": [{"guid": "-2", "typeName": "m4i_data_attribute"}]},
            ),
            entity(
                "-5",
                "m4i_dataset",
                "dataset",
                relationshipAttributes={"fields": [{"guid": "-4", "typeName": "m4i_field"}]},
            ),
            entity("-6", "m4i_person", "owner"),
            entity("-7", "m4i_person", "steward"),
            # DET-34's lineage nodes (7.21c), added without renaming the
            # DET-27 nodes: a system, a process seeded from its own ends
            # (inputs/outputs to the dataset, system to the system — so the
            # dataset reads back one producer and one consumer), and a second
            # process left unconnected (DET-33's zero case).
            entity("-8", "m4i_system", "system"),
            entity(
                "-9",
                "m4i_generic_process",
                "process",
                relationshipAttributes={
                    "inputs": [{"guid": "-5", "typeName": "m4i_dataset"}],
                    "outputs": [{"guid": "-5", "typeName": "m4i_dataset"}],
                    "system": {"guid": "-8", "typeName": "m4i_system"},
                },
            ),
            entity("-10", "m4i_generic_process", "lonely"),
        ]
    }

    response = page.request.post(
        urljoin(root_url, "/api/atlas/v2/entity/bulk"),
        data=json.dumps(body),
        headers={"content-type": "application/json", "authorization": f"Bearer {token}"},
    )

    assert response.status == 200, response.text()

    assignments = response.json()["guidAssignments"]

    return {key: assignments[temp_guid] for key, temp_guid in zip(names, [f"-{i}" for i in range(11)], strict=True)}


def _active_edge(entity: dict, key: str, guid: str) -> bool:
    """Whether an entity read holds an ACTIVE relationship edge to ``guid``.

    A single-valued end (18.3) reads back as one map, not a list, so it is held as the one edge.
    """
    value = entity.get("relationshipAttributes", {}).get(key, [])
    ends = [value] if isinstance(value, dict) else value
    return any(entry["guid"] == guid and entry.get("relationshipStatus") == "ACTIVE" for entry in ends)


def _wait_search_cards(page: Page, root_url: str, token: str, guids: list[str], *, timeout: float = 90) -> None:
    """Ask the search door until it carries every guid (bounded).

    The section cards and the results rows ride the view search door's
    answer (16.5d, DD-615/DD-616), and the door's cards are the indexer
    worker's derived documents: the read door answers a just-seeded entity
    right away, while the search door can still answer without its card —
    and DET-18 quietly drops a relation whose card is missing. A scenario
    that asserts card bodies therefore waits the door's beat first, the
    propagation-retry idiom of ``_wait_entity_read`` (CLS-12's sibling)
    on the slower indexer.
    """
    deadline = time.monotonic() + timeout
    while True:
        answer = page.request.post(
            urljoin(root_url, "/api/aurelius/v1/search"),
            data=json.dumps({"filters": {"guid": guids}, "limit": len(guids)}),
            headers={"content-type": "application/json", "authorization": f"Bearer {token}"},
        ).json()
        found = {card["guid"] for card in answer.get("cards", [])}
        if set(guids) <= found:
            return
        assert time.monotonic() < deadline, f"the search door never carried the cards: missing {set(guids) - found}"
        time.sleep(2)


def _wait_card_role_relations(
    page: Page, root_url: str, token: str, guid: str, attributes: list[str], *, timeout: float = 90
) -> None:
    """Ask the search door until the card of ``guid`` carries every role relation (bounded).

    The 16.5f card rows read the door's role relations (AVS-10), which ride the
    indexer's derived document: the edges are active long before the document
    re-derives with its role fields filled. The same propagation-retry idiom as
    ``_wait_search_cards``, waiting the role fill rather than the card's presence.
    """
    deadline = time.monotonic() + timeout
    while True:
        answer = page.request.post(
            urljoin(root_url, "/api/aurelius/v1/search"),
            data=json.dumps({"filters": {"guid": [guid]}, "limit": 1}),
            headers={"content-type": "application/json", "authorization": f"Bearer {token}"},
        ).json()
        cards = answer.get("cards", [])
        held = {relation["attribute"] for card in cards for relation in card.get("relations", [])}
        if set(attributes) <= held:
            return
        assert time.monotonic() < deadline, (
            f"the door never carried the role relations on {guid}: missing {set(attributes) - held}"
        )
        time.sleep(2)


def _the_rich_card_shows_its_labelled_roles(
    page: Page, root_url: str, token: str, guids: dict[str, str], run: str
) -> None:
    """The shared rich card renders the seeded roles as labelled rows (VCF-15, 16.5f).

    Open the seeded domain's page: its Child Entities box resolves the entity's
    card, and the card shows the owner and steward as the legacy's labelled
    rows — the role relations ride the door's answer since AVS-10, filled by
    the indexer's re-derive (ASD-07), so wait that beat through the door first.
    """
    _wait_card_role_relations(page, root_url, token, guids["entity"], ["businessOwner", "steward"])
    page.goto(urljoin(root_url, f"/en-US/search/details/{guids['domain']}"))
    entity_card = page.locator("#related-entities aurelius-atlas-webapp-catalogue-card").filter(
        has_text=f"zz{run}entity"
    )
    expect(entity_card).to_have_count(1)
    # the empty domainLead end draws no row: two rows, the seeded roles (VCF-15).
    expect(entity_card.locator(".aurelius-people-row")).to_have_count(2)
    expect(entity_card).to_contain_text(f"Data Owner(s) : zz{run}owner")
    expect(entity_card).to_contain_text(f"Data Steward(s) : zz{run}steward")


def _jump_with_side_navigation(page: Page) -> None:
    """The floating side navigation jumps within the details page (DET-25, DD-381).

    Open the menu and click one item. The click is a router navigation
    (DD-381): the item's ``routerLink`` keeps the screen and puts the
    box's anchor in the url, so the section is shareable and a back step
    walks the jumps (never the landing page — DD-380's bare ``#anchor``
    bug). The scroll itself is browser behaviour no headless assert
    adds. The item click waits for the opened menu by itself
    (Playwright's actionability), so the open state needs no assertion
    of its own — the toggle is the lib's UIC-18.
    """
    nav = page.locator(".aurelius-details-nav")
    nav.locator("button").click()
    nav.locator(".menu-list a", has_text="Data Attributes").click()
    expect(page).to_have_url(re.compile(r"/search/details/[^#]+#related-attributes$"))
    expect(page.locator("#related-attributes")).to_be_visible()

    # DD-381: the box seats below the fixed navbar (the 68px offset the
    # router scroller carries). The smooth scroll settles; the wait polls
    # until the box reaches the navbar's foot.
    page.wait_for_function(
        "() => Math.abs(document.getElementById('related-attributes').getBoundingClientRect().top - 68) <= 2"
    )

    # DD-381: the jumps are history now — back leaves the fragment off
    # and the screen stays the entity's, forward puts the anchor back.
    # WebKit restores the sign-in callback's OAuth fragment (#state=...&
    # code=...) on the history entry a back step lands on, even though the
    # app cleaned the address bar (its replaceState edits the address, not
    # the stored entry); Chromium/Firefox clean the entry too. The residue
    # is the browser's history bookkeeping, not the app's — the DD-381 rule
    # is the app's own anchor, so the pin rejects #related-attributes and
    # tolerates the OAuth fragment.
    page.go_back()
    expect(page).to_have_url(re.compile(r"/search/details/[^#]*(#(state|session_state|iss|code)=.*)?$"))
    expect(page.locator("h1.aurelius-details-title")).to_be_visible()
    page.go_forward()
    expect(page).to_have_url(re.compile(r"/search/details/[^#]+#related-attributes$"))


def _filters_the_cards_and_resets_them(section: Locator, cards: Locator, run: str) -> None:
    """The section's keyword filter narrows the cards as typed, and the count line resets (DET-20).

    DD-375: the filter follows the keystroke, so the submit button's click
    is a no-op the filter already applied. The reset line restores both the
    cards and its own count.
    """
    section.locator("aurelius-atlas-ui-search-field input").fill("beta")
    expect(cards).to_have_count(1)
    expect(cards.first).to_contain_text(f"zz{run}beta")
    section.locator("aurelius-atlas-ui-search-field button.button.is-success").click()
    expect(section.locator("a.aurelius-card-section-reset")).to_have_text("1 result(s)")

    section.locator("a.aurelius-card-section-reset").click()
    expect(cards).to_have_count(2)
    expect(section.locator(".aurelius-card-section-count")).to_contain_text("2 result(s)")


def _deep_link_lands_its_section(page: Page, root_url: str, entity_guid: str, run: str) -> None:
    """A cold visit to a section's url opens the entity at that section (DET-25, DD-381).

    The jump's address is shareable: opened cold, the screen shows the
    entity, its cards fill the section, and the section seats below the
    fixed navbar (the router's own jump runs before the entity answers,
    so the screen lands it once its box renders). The boot wait inside
    ``_goto_app`` is what makes the cold open safe on a contended runner
    (ADR 062: the webkit flake).
    """
    _goto_app(page, urljoin(root_url, f"/en-US/search/details/{entity_guid}#related-attributes"))
    expect(page.locator("h1.aurelius-details-title")).to_have_text(f"zz{run}entity")
    expect(page.locator("#related-attributes aurelius-atlas-ui-entity-card")).to_have_count(2)
    page.wait_for_function(
        "() => Math.abs(document.getElementById('related-attributes').getBoundingClientRect().top - 68) <= 2"
    )


@pytest.mark.critical
def test__m4i_details_render_the_seeded_sections(authenticated: Page, root_url: str, user_token: str) -> None:
    """The m4i details layout renders from a seeded mini-graph (DET-15..DET-20, DET-23, DET-27, VCF-15).

    The 7.21a screen on real data: the dispatch picks the m4i layout for the
    entity type (DET-15, a direct hit — no typedef walk), the People box
    shows the owner and steward links of the seeded people ends (DET-23),
    the shared rich card on the domain's Child Entities box shows the same
    roles labelled on it (VCF-15, 16.5f), the Data Attributes section seeds
    from ``relationshipAttributes`` and resolves its cards with their
    definition text (DET-17, DET-19), the
    keyword filter narrows the cards and the reset count line restores them
    (DET-20), and Child Entities renders at its zero count (the empty box,
    no cards). Opening the seeded attribute shows its Fields section — the
    field's edge read back at the other end. A ``DataSet`` is not m4i and
    not an m4i subtype: it keeps the DET-01 default chrome (DET-14's shape,
    no card sections). Self-cleaned by the purge helper (DD-223: no shared
    service restarts, namespaced by the run token).
    """
    run = secrets.token_hex(4)
    guids = _seed_m4i_mini_graph(authenticated, root_url, user_token, run)
    entity_guid = guids["entity"]
    alpha_guid = guids["alpha"]
    dataset_guid = _seed_entities(authenticated, root_url, user_token, "DataSet", [f"zz{run}plain"])["-0"]

    try:
        # The edges are separate near-real-time records the read searches
        # (CLS-12's race): wait both ends visible before the screen reads.
        _wait_entity_read(
            authenticated,
            root_url,
            user_token,
            entity_guid,
            predicate=lambda entity: (
                _active_edge(entity, "attributes", guids["alpha"])
                and _active_edge(entity, "attributes", guids["beta"])
                and _active_edge(entity, "businessOwner", guids["owner"])
                and _active_edge(entity, "steward", guids["steward"])
            ),
        )
        _wait_entity_read(
            authenticated,
            root_url,
            user_token,
            alpha_guid,
            predicate=lambda entity: _active_edge(entity, "fields", guids["field"]),
        )
        # The section cards ride the search door (16.5d, DD-615): wait its
        # beat until it carries the attribute pair the boxes resolve, so
        # DET-18 never drops a card the indexer has not derived yet.
        _wait_search_cards(authenticated, root_url, user_token, [alpha_guid, guids["beta"]])

        authenticated.goto(urljoin(root_url, f"/en-US/search/details/{entity_guid}"))
        expect(authenticated.locator("h1.aurelius-details-title")).to_have_text(f"zz{run}entity")

        # DET-23: the People box with the owner and steward links (the empty
        # Domain Lead end renders no row).
        people = authenticated.locator("#people-details")
        expect(people.locator(".aurelius-people-row")).to_have_count(2)
        expect(people).to_contain_text(f"Data Owner(s) : zz{run}owner")
        expect(people).to_contain_text(f"Data Steward(s) : zz{run}steward")

        # VCF-15 (16.5f): the same roles, labelled, on the shared rich card
        # the entity's card draws on the domain page's Child Entities box.
        _the_rich_card_shows_its_labelled_roles(authenticated, root_url, user_token, guids, run)
        authenticated.goto(urljoin(root_url, f"/en-US/search/details/{entity_guid}"))
        expect(authenticated.locator("h1.aurelius-details-title")).to_have_text(f"zz{run}entity")

        # DET-17/DET-19: the Data Attributes section at its seeded count,
        # two cards whose bodies carry the seeded definition text.
        section = authenticated.locator("#related-attributes")
        cards = section.locator("aurelius-atlas-ui-entity-card")
        expect(cards).to_have_count(2)
        expect(section.locator(".aurelius-card-section-count")).to_contain_text("2 result(s)")
        expect(cards.filter(has_text=f"zz{run}alpha")).to_contain_text("The alpha definition.")
        expect(cards.filter(has_text=f"zz{run}beta")).to_contain_text("The beta definition.")

        # DET-20 (DD-375): the keyword filter narrows the cards as it is
        # typed, and the reset count line restores them.
        _filters_the_cards_and_resets_them(section, cards, run)

        # DET-17: Child Entities renders at its zero count — the box with
        # the count line and no cards (the seed has no childEntity end).
        children = authenticated.locator("#related-entities")
        expect(children).to_be_visible()
        expect(children.locator(".aurelius-card-section-count")).to_contain_text("0 result(s)")
        expect(children.locator("aurelius-atlas-ui-entity-card")).to_have_count(0)

        # DET-25 (DD-380/DD-381): the floating side navigation jumps to a
        # box, the anchor rides the url, and the screen stays put (never
        # the landing page).
        _jump_with_side_navigation(authenticated)

        # DET-25 (DD-381): the same url opens cold — the jump is shareable.
        _deep_link_lands_its_section(authenticated, root_url, entity_guid, run)

        # DET-17: the attribute page shows its Fields section — the field's
        # edge read back at the attribute end, one resolved card. The layout
        # table gives the attribute a People box too (DET-16); the attribute
        # holds no people ends, so its empty placeholder line renders (DET-23).
        # The field card rides the door too (DD-615): wait it before opening.
        _wait_search_cards(authenticated, root_url, user_token, [guids["field"]])
        authenticated.goto(urljoin(root_url, f"/en-US/search/details/{alpha_guid}"))
        fields = authenticated.locator("#related-fields")
        expect(fields).to_be_visible()
        expect(fields.locator(".aurelius-card-section-count")).to_contain_text("1 result(s)")
        expect(fields.locator("aurelius-atlas-ui-entity-card")).to_have_count(1)
        expect(fields).to_contain_text(f"zz{run}field")
        expect(authenticated.locator("#people-details .aurelius-people-empty")).to_have_text("No people assigned.")

        # DET-15: a DataSet is neither an m4i type nor an m4i subtype, so it
        # keeps the DET-01 default — no card sections at all. The supertype
        # walk settles after the read (DataSet → Process, both built-in), so
        # the boxes' absence is checked after it has had its turns.
        authenticated.goto(urljoin(root_url, f"/en-US/search/details/{dataset_guid}"))
        expect(authenticated.locator("h1.aurelius-details-title")).to_have_text(f"zz{run}plain")
        authenticated.wait_for_timeout(1_000)
        expect(authenticated.locator(".aurelius-details-section")).to_have_count(0)
        expect(authenticated.locator(".aurelius-people-row")).to_have_count(0)
    finally:
        for type_name in [
            "m4i_data_entity",
            "m4i_data_attribute",
            "m4i_data_domain",
            "m4i_field",
            "m4i_system",
            "m4i_generic_process",
            "m4i_dataset",
            "m4i_person",
        ]:
            _purge_type(authenticated, root_url, user_token, type_name)
        _delete_entity(authenticated, root_url, user_token, dataset_guid)


@pytest.mark.critical
def test__the_details_trail_follows_the_seeded_parentage(authenticated: Page, root_url: str, user_token: str) -> None:
    """The seeded entity's details show the filled trail, its own crumb active (VDR-06, DD-606).

    16.5b fills the 7.20 seam (DD-317): the read door answers the view with
    the index document's stored breadcrumb, and the screen renders it top
    down with the opened entity's own crumb last and active. The mini-graph
    parents the entity to its domain (the ``dataDomain`` edge), so the trail
    is domain → entity. The document is the indexer worker's: the scenario
    waits the door for its breadcrumb, bounded — the poll interval (10 s)
    plus the document upkeep rides inside the wait. Self-cleaned by the
    purge helper (DD-223: no shared service restarts, namespaced by the run
    token).
    """
    run = secrets.token_hex(4)
    guids = _seed_m4i_mini_graph(authenticated, root_url, user_token, run)

    try:
        # VDR-06's source is the stored document, not the entity: wait the
        # read door until the indexer has derived the entity's breadcrumb.
        deadline = time.monotonic() + 90
        while True:
            view = authenticated.request.get(
                urljoin(root_url, f"/api/aurelius/v1/entity/guid/{guids['entity']}"),
                headers={"authorization": f"Bearer {user_token}"},
            ).json()
            crumbs = [crumb["guid"] for crumb in view.get("breadcrumb", [])]
            if crumbs == [guids["domain"]]:
                break
            assert time.monotonic() < deadline, f"the breadcrumb never arrived: {view.get('breadcrumb')}"
            time.sleep(2)

        _goto_app(authenticated, urljoin(root_url, f"/en-US/search/details/{guids['entity']}"))
        expect(authenticated.locator("h1.aurelius-details-title")).to_have_text(f"zz{run}entity")

        # The stored trail top-down plus the opened entity's own crumb,
        # marked active (VDR-06): the domain above, the entity last. The
        # header's own trail — since 16.5d the rich section cards carry a
        # trail too (VCF-05), so the locator names the header's.
        trail = authenticated.locator(".aurelius-details-header .aurelius-details-trail")
        items = trail.locator("li")
        expect(items).to_have_count(2)
        expect(items.nth(0)).to_have_text(f"zz{run}domain")
        expect(items.nth(1)).to_have_text(f"zz{run}entity")
        expect(items.nth(1)).to_have_class(re.compile("is-active"))

        # DET-06 on real crumbs: the parent crumb is a link that routes the
        # screen to the domain's own details.
        items.nth(0).locator("a").click()
        expect(authenticated).to_have_url(re.compile(rf"/en-US/search/details/{guids['domain']}$"))
        expect(authenticated.locator("h1.aurelius-details-title")).to_have_text(f"zz{run}domain")
    finally:
        for type_name in [
            "m4i_data_entity",
            "m4i_data_attribute",
            "m4i_data_domain",
            "m4i_field",
            "m4i_system",
            "m4i_generic_process",
            "m4i_dataset",
            "m4i_person",
        ]:
            _purge_type(authenticated, root_url, user_token, type_name)


@pytest.mark.critical
def test__the_dataset_and_process_pages_render_their_lineage_sections(
    authenticated: Page, root_url: str, user_token: str
) -> None:
    """Producers/Consumers on the m4i dataset, and the eighth layout on its process (DET-32..DET-34).

    The 7.21c screens on the same seeded mini-graph: opened at the m4i
    dataset, the Producers box counts 1 and holds the process card and the
    Consumers box counts it too — both seeded from the dataset's own lineage
    ends (DET-32), with the stats bar in the legacy order (the lineage-model
    entry back in since 7.22d, LDG-32). Clicking the producer card routes the
    screen to the process, which renders the eighth layout: Systems/Inputs/
    Outputs boxes with their one card each, no People box (DET-33). The
    unconnected process renders the same three boxes at zero. Self-cleaned by
    the purge helper (DD-223), which the DET-27 finally gained the two new
    types for.
    """
    run = secrets.token_hex(4)
    guids = _seed_m4i_mini_graph(authenticated, root_url, user_token, run)
    dataset_guid = guids["dataset"]
    process_guid = guids["process"]
    lonely_guid = guids["lonely"]

    try:
        # The lineage edges are separate near-real-time records (CLS-12's
        # race): wait them visible at both ends before the screens read.
        _wait_entity_read(
            authenticated,
            root_url,
            user_token,
            dataset_guid,
            predicate=lambda entity: (
                _active_edge(entity, "fields", guids["field"])
                and _active_edge(entity, "outputFromProcesses", process_guid)
                and _active_edge(entity, "inputToProcesses", process_guid)
            ),
        )
        _wait_entity_read(
            authenticated,
            root_url,
            user_token,
            process_guid,
            predicate=lambda entity: (
                _active_edge(entity, "system", guids["system"])
                and _active_edge(entity, "inputs", dataset_guid)
                and _active_edge(entity, "outputs", dataset_guid)
            ),
        )
        # The lineage boxes' and the process page's cards ride the search
        # door (16.5d, DD-615): wait its beat for every card the scenario
        # asserts — the producer, the system, and the dataset.
        _wait_search_cards(authenticated, root_url, user_token, [process_guid, guids["system"], dataset_guid])

        authenticated.goto(urljoin(root_url, f"/en-US/search/details/{dataset_guid}"))
        expect(authenticated.locator("h1.aurelius-details-title")).to_have_text(f"zz{run}warehouse")

        # DET-32: the two lineage boxes at their seeded counts — one process
        # card each, read through the same bulk path as every section.
        for anchor in ("related-producers", "related-consumers"):
            box = authenticated.locator(f"#{anchor}")
            expect(box).to_be_visible()
            expect(box.locator(".aurelius-card-section-count")).to_contain_text("1 result(s)")
            cards = box.locator("aurelius-atlas-ui-entity-card")
            expect(cards).to_have_count(1)
            expect(cards.first).to_contain_text(f"zz{run}pipeline")

        # DET-32/LDG-32: the stats bar in the legacy order (Data Quality
        # out, DD-369) with the lineage entry between Child Datasets and
        # Producers — its word reads the box's state, and the seeded dataset
        # has lineage, so the model drew ("Available"). The strip renders its
        # labels uppercase (CSS text-transform), so they are compared
        # case-folded; the wait below both pins the word and settles the
        # box's own call before the list read.
        lineage_stat = authenticated.locator(
            ".aurelius-details-stats .level-item",
            has=authenticated.locator('p.heading a[href="#lineage-model"]'),
        )
        expect(lineage_stat.locator("p.title")).to_have_text("Available")
        stats = [
            (
                item.locator("p.heading a").inner_text().strip().casefold(),
                item.locator("p.title").inner_text().strip().casefold(),
            )
            for item in authenticated.locator(".aurelius-details-stats .level-item").all()
        ]
        assert stats == [
            ("fields", "1"),
            ("child datasets", "0"),
            ("lineage model", "available"),
            ("producers", "1"),
            ("consumers", "1"),
            ("properties", "0"),
        ]
        # LDG-32: the side navigation lists the link beside the stat (the
        # menu stays closed — the list is projected either way, UIC-18).
        expect(authenticated.locator(".aurelius-details-nav .menu-list a", has_text="Lineage Model")).to_have_count(1)

        # DET-32/DET-33: the producer card's title routes the screen to the
        # process — the eighth layout, no People box, three boxes at one.
        authenticated.locator("#related-producers aurelius-atlas-ui-entity-card a").first.click()
        expect(authenticated).to_have_url(re.compile(rf"/en-US/search/details/{process_guid}$"))
        expect(authenticated.locator("h1.aurelius-details-title")).to_have_text(f"zz{run}pipeline")
        expect(authenticated.locator("#people-details")).to_have_count(0)

        boxes = {
            "related-systems": f"zz{run}elastic",
            "related-inputs": f"zz{run}warehouse",
            "related-outputs": f"zz{run}warehouse",
        }
        for anchor, expected in boxes.items():
            box = authenticated.locator(f"#{anchor}")
            expect(box).to_be_visible()
            cards = box.locator("aurelius-atlas-ui-entity-card")
            expect(cards).to_have_count(1)
            expect(cards.first).to_contain_text(expected)

        # DET-33/LDG-32: the lineage stat sits between Systems and Inputs —
        # the seeded process has lineage ends, so its box drew a model.
        lineage_stat = authenticated.locator(
            ".aurelius-details-stats .level-item",
            has=authenticated.locator('p.heading a[href="#lineage-model"]'),
        )
        expect(lineage_stat.locator("p.title")).to_have_text("Available")
        stats = [
            item.locator("p.heading a").inner_text().strip().casefold()
            for item in authenticated.locator(".aurelius-details-stats .level-item").all()
        ]
        assert stats == ["systems", "lineage model", "inputs", "outputs", "properties"]

        # DET-33: the unconnected process renders the same layout at zeros —
        # the empty boxes with their count lines, no cards.
        authenticated.goto(urljoin(root_url, f"/en-US/search/details/{lonely_guid}"))
        expect(authenticated.locator("h1.aurelius-details-title")).to_have_text(f"zz{run}lonely")
        for anchor in ("related-systems", "related-inputs", "related-outputs"):
            box = authenticated.locator(f"#{anchor}")
            expect(box).to_be_visible()
            expect(box.locator(".aurelius-card-section-count")).to_contain_text("0 result(s)")
            expect(box.locator("aurelius-atlas-ui-entity-card")).to_have_count(0)

        # LDG-32: the unconnected process has no lineage — the box's state
        # rests empty, so its stat reads "Unavailable" (the word, never a
        # count — the legacy's shape).
        lineage_stat = authenticated.locator(
            ".aurelius-details-stats .level-item",
            has=authenticated.locator('p.heading a[href="#lineage-model"]'),
        )
        expect(lineage_stat.locator("p.title")).to_have_text("Unavailable")
    finally:
        for type_name in [
            "m4i_generic_process",
            "m4i_system",
            "m4i_data_attribute",
            "m4i_data_entity",
            "m4i_data_domain",
            "m4i_field",
            "m4i_dataset",
            "m4i_person",
        ]:
            _purge_type(authenticated, root_url, user_token, type_name)


# impact=major, likelihood=high (a rules box in a young screen, churn on its path)
@pytest.mark.high
@pytest.mark.covers(rules=["DET-35", "DET-36"])
def test__the_field_page_shows_its_data_quality_rules(authenticated: Page, root_url: str, user_token: str) -> None:
    """The field page's rules box, stat, and link over a seeded rule (DET-35, DET-36).

    The 7.24 field layout on real data: the third box (``#related-rules``) seeds
    from the field's own ``dataQuality`` relationship end (DD-444), so a seeded
    ``m4i_data_quality`` rule lands there as one resolved card at the box count.
    The stats bar gains the Data Quality Rules stat in the legacy place — after
    Child Fields, before Properties — carrying the DET-24 section count (DET-36),
    and the side navigation gains its link. The field's empty Child Fields end
    renders its box at zero count, as every DET-17 section does. The rule's edge
    is a separate near-real-time record the read searches, so the scenario waits
    it before opening the screen (the CLS-12 race, the mini-graph idiom).
    Self-cleaned by the purge helper, gained the ``m4i_data_quality`` type (DD-223).
    """
    run = secrets.token_hex(4)
    guids = _seed_m4i_mini_graph(authenticated, root_url, user_token, run)
    field_guid = guids["field"]
    rule_name = f"zz{run}rule"

    rule = authenticated.request.post(
        urljoin(root_url, "/api/atlas/v2/entity/bulk"),
        data=json.dumps(
            {
                "entities": [
                    {
                        "typeName": "m4i_data_quality",
                        "guid": "-0",
                        "attributes": {
                            "qualifiedName": rule_name,
                            "name": rule_name,
                            # `id` is a mandatory INT attribute of the rule type.
                            "id": int(run[:6], 16),
                            "ruleDescription": "The field must carry a value.",
                        },
                        "relationshipAttributes": {"fields": [{"guid": field_guid, "typeName": "m4i_field"}]},
                    }
                ]
            }
        ),
        headers={"content-type": "application/json", "authorization": f"Bearer {user_token}"},
    )
    assert rule.status == 200, rule.text()
    rule_guid = rule.json()["guidAssignments"]["-0"]

    try:
        _wait_entity_read(
            authenticated,
            root_url,
            user_token,
            field_guid,
            predicate=lambda entity: _active_edge(entity, "dataQuality", rule_guid),
        )
        # The rules box card rides the search door (16.5d, DD-615): wait its
        # beat before the screen resolves the box.
        _wait_search_cards(authenticated, root_url, user_token, [rule_guid])

        authenticated.goto(urljoin(root_url, f"/en-US/search/details/{field_guid}"))
        expect(authenticated.locator("h1.aurelius-details-title")).to_have_text(f"zz{run}field")

        # DET-35: the rules box at its seeded count, the rule as one resolved card.
        section = authenticated.locator("#related-rules")
        expect(section).to_be_visible()
        expect(section.locator(".aurelius-card-section-count")).to_contain_text("1 result(s)")
        expect(section.locator("aurelius-atlas-ui-entity-card")).to_have_count(1)
        expect(section).to_contain_text(rule_name)

        # DET-35: the empty Child Fields end renders its box at zero count.
        children = authenticated.locator("#related-fields")
        expect(children).to_be_visible()
        expect(children.locator(".aurelius-card-section-count")).to_contain_text("0 result(s)")
        expect(children.locator("aurelius-atlas-ui-entity-card")).to_have_count(0)

        # DET-36: the rules stat in the legacy place, its value the section
        # count (the legacy's `dqscorecnt_overall` stand-in, DD-444).
        rules_stat = authenticated.locator(
            ".aurelius-details-stats .level-item", has=authenticated.locator('p.heading a[href="#related-rules"]')
        )
        expect(rules_stat).to_have_count(1)
        expect(rules_stat.locator("p.title")).to_have_text("1")
        stats = [
            item.locator("p.heading a").inner_text().strip().casefold()
            for item in authenticated.locator(".aurelius-details-stats .level-item").all()
        ]
        assert stats == ["data attributes", "child fields", "data quality rules", "properties"]

        # DET-36: the side navigation gained the matching link.
        nav_link = authenticated.locator(".aurelius-details-nav .menu-list a", has_text="Data Quality Rules")
        expect(nav_link).to_have_count(1)
    finally:
        for type_name in [
            "m4i_data_quality",
            "m4i_data_entity",
            "m4i_data_attribute",
            "m4i_data_domain",
            "m4i_field",
            "m4i_system",
            "m4i_generic_process",
            "m4i_dataset",
            "m4i_person",
        ]:
            _purge_type(authenticated, root_url, user_token, type_name)


# impact=major, likelihood=medium (the glossary promise in browse; churn on the search path)
@pytest.mark.high
def test__business_explore_lists_glossary_entities_without_a_url_query(
    authenticated: Page, root_url: str, user_token: str
) -> None:
    """The business card's explore button lists glossary entities, type-filtered (SRH-08, DV-84).

    Explore is the legacy ``directToGlossary``: an empty query plus the
    session type filter ``typeName=AtlasGlossary`` (DV-84 — the Atlas type,
    not the m4i ``Glossary`` label, which the server would reject as
    UNKNOWN_TYPENAME, SRC-03). The filter rides the store, never the URL
    (SRH-02: the URL carries only ``?query=``), so the results URL stays
    clean — reloading it restarts from the URL alone: the empty query, which
    lists every entity (DD-221), proving the filter lived only in the
    session store.

    The type is purged first: the shared stack keeps every run's glossaries
    and the explore page shows the first ten (limit 10) — the purge makes
    the seeded entity the page.
    """
    run = secrets.token_hex(4)
    name = f"zz{run}domain"
    _purge_type(authenticated, root_url, user_token, "AtlasGlossary")
    _seed_entities(authenticated, root_url, user_token, "AtlasGlossary", [name])

    authenticated.goto(urljoin(root_url, "/en-US/search"))
    authenticated.get_by_role("button", name="Start browsing data domains").click()

    expect(authenticated).to_have_url(re.compile(r"/en-US/search/results$"))
    rows = authenticated.locator(".result-row")
    expect(rows.filter(has_text=name)).to_have_count(1)

    # The type filter is session state: reloading the bare results URL
    # restarts from the URL alone — the empty query with no filter, which the
    # door answers with every entity (VSR-04, AVR-11). The purged type holds
    # exactly the seeded glossary, so a filtered re-run would show its one
    # row; the every-entity search shows more (stack-size agnostic: on a
    # fresh CI stack the few seeded entities, on a shared stack the full page
    # of ten).
    authenticated.reload()
    expect(authenticated.locator(".result-row")).not_to_have_count(1)


# impact=major, likelihood=low (the empty-result pair; a stable screen)
@pytest.mark.medium
def test__no_match_shows_the_legacy_no_results_pair(authenticated: Page, root_url: str) -> None:
    """A query with no hits renders the legacy no-results card (SRH-06).

    The legacy results-box twin: "No results found" + "Please, try to make
    another query.", from the bridge. The query is one token unique to the
    run, so zero hits are guaranteed on the shared stack (word-exact terms,
    FTX-01).
    """
    run = secrets.token_hex(8)

    authenticated.goto(urljoin(root_url, f"/en-US/search/results?query=zzmiss{run}"))

    expect(authenticated.locator(".no-results")).to_have_text("No results found")
    expect(authenticated.locator(".another-query")).to_have_text("Please, try to make another query.")
    expect(authenticated.locator(".result-row")).to_have_count(0)


def _delete_entity(page: Page, root_url: str, token: str, guid: str) -> None:
    """Delete one entity by guid (the scenarios' self-cleaning, EDT-12).

    A just-seeded entity is still being written by the indexer worker when the
    scenario finishes, and the soft delete can land mid-write: the server
    answers 500 "changed by another write" (the store's version conflict).
    That resolves as soon as the worker's own write lands, so the delete
    retries it a few times before failing.
    """
    attempt = 0
    while True:
        deleted = page.request.delete(
            urljoin(root_url, "/api/atlas/v2/entity/bulk"),
            params={"guid": guid},
            headers={"authorization": f"Bearer {token}"},
        )

        if deleted.status == 200 or "changed by another write" not in deleted.text() or attempt == 10:
            break
        time.sleep(1 + attempt)
        attempt += 1

    assert deleted.status == 200, deleted.text()


def _open_editor_from_details(page: Page, root_url: str, guid: str) -> None:
    """Open the editor drawer on a seeded entity's details through the pencil (EDT-01)."""
    _goto_app(page, urljoin(root_url, f"/en-US/search/details/{guid}"))
    expect(page.locator("h1.aurelius-details-title")).to_have_text(re.compile(r"\S"))

    pencil = page.locator("button.aurelius-details-edit")
    expect(pencil).to_be_visible()  # the writer holds atlas-write (EDT-09)
    pencil.click()

    expect(page.locator(".aurelius-drawer")).to_be_visible()
    expect(page).to_have_url(re.compile(r"\(drawer:edit"))


def _wait_entity_read(
    page: Page, root_url: str, token: str, guid: str, *, predicate: Callable[[dict], bool], timeout: float = 30
) -> dict:
    """Read one entity by guid until the predicate holds (bounded).

    The store assembles relationship attributes by SEARCHING the edge records,
    which are separate near-real-time documents: a read landing right after a
    write can still answer the pre-write state. An editor that reads early
    keeps that state for its whole life (it reads once), so every scenario
    opening the editor on a just-written relationship waits the read first —
    the propagation-retry idiom the classification self-cleaning uses (CLS-12).
    """
    deadline = time.monotonic() + timeout
    while True:
        entity = page.request.get(
            urljoin(root_url, f"/api/atlas/v2/entity/guid/{guid}"),
            headers={"authorization": f"Bearer {token}"},
        ).json()["entity"]
        if predicate(entity):
            return entity
        assert time.monotonic() < deadline, f"entity {guid} never matched the predicate: {entity}"
        time.sleep(1)


@pytest.mark.critical
def test__the_editor_edits_a_seeded_entity(authenticated: Page, root_url: str, user_token: str) -> None:
    """The pencil opens the editor with the entity filled; a saved edit reads back (EDT-01, EDT-12).

    The drawer's edit mode: the form holds the seeded name and description,
    the Definition textarea is the description key (EDT-03, DET-10/DD-320),
    Save posts the merged entity (EDT-06), the drawer goes away, and the
    details screen underneath — never reloaded, same URL (EDT-01) — shows
    the new text through the save tick's re-read (DD-327).
    """
    run = secrets.token_hex(4)
    name = f"zz{run}edit"
    guids = _seed_entities(authenticated, root_url, user_token, "DataSet", [name])
    guid = guids["-0"]

    updated = authenticated.request.put(
        urljoin(root_url, f"/api/atlas/v2/entity/guid/{guid}"),
        params={"name": "description"},
        data=json.dumps("The first description."),
        headers={"content-type": "application/json", "authorization": f"Bearer {user_token}"},
    )
    assert updated.status == 200, updated.text()

    try:
        _open_editor_from_details(authenticated, root_url, guid)

        drawer = authenticated.locator(".aurelius-drawer")
        expect(drawer).to_contain_text("Edit entity")
        expect(authenticated.locator("#editor-name")).to_have_value(name)
        expect(authenticated.locator("textarea#editor-description")).to_have_value("The first description.")

        authenticated.locator("textarea#editor-description").fill("The edited description.")
        drawer.locator("button.aurelius-editor-save").click()

        # The drawer navigates away and the same details URL re-reads the
        # saved entity (EDT-06's navigation + DD-327's tick): the new text
        # shows without a page reload (URL identity proves no reload).
        expect(authenticated).to_have_url(re.compile(rf"/en-US/search/details/{guid}$"))
        expect(authenticated.locator(".aurelius-drawer")).to_have_count(0)
        expect(authenticated.locator(".aurelius-details-description")).to_have_text("The edited description.")
    finally:
        _delete_entity(authenticated, root_url, user_token, guid)


@pytest.mark.critical
def test__the_editor_deletes_an_entity(authenticated: Page, root_url: str, user_token: str) -> None:
    """The drawer's hold-to-confirm Delete deletes the entity and lands on browse (EDT-19, VDE-11, WFE-01, WFE-02).

    The live flow behind 19.6's outcome signal (DD-803): a quick tap on the
    Delete button releases the hold early, so nothing is deleted and the
    drawer stays open (the hold control gates the action); the full three-
    second hold completes the delete, the drawer closes, and the app lands on
    the browse landing — the deleted entity's details are no longer a
    destination (VDE-11). The read-back is the store's own answer: the entity
    reads ``DELETED`` (the e2e server deletes softly, DD-059). The drawer's
    "Entity deleted" line rides the outcome tick the delete code fires
    (WFE-01, WFE-02, DD-803) and is proven where it lives, in the component's
    own test (LR-005's reword case) — a line gone by the time the browser
    arrives is not a browser assertion (a timing pin, not a user interaction).
    """
    run = secrets.token_hex(4)
    name = f"zz{run}deleted"
    guids = _seed_entities(authenticated, root_url, user_token, "DataSet", [name])
    guid = guids["-0"]

    try:
        _open_editor_from_details(authenticated, root_url, guid)

        delete_button = authenticated.locator("button.aurelius-editor-delete")
        expect(delete_button).to_be_visible()

        # An early release is a cancellation (the hold control's rule): the
        # pointer goes down and up well inside the three seconds, and the
        # drawer stays open with the entity untouched (EDT-19).
        delete_button.scroll_into_view_if_needed()
        box = delete_button.bounding_box()
        assert box is not None
        authenticated.mouse.move(box["x"] + box["width"] / 2, box["y"] + box["height"] / 2)
        authenticated.mouse.down()
        authenticated.mouse.up()

        expect(authenticated).to_have_url(re.compile(r"\(drawer:edit"))
        expect(authenticated.locator(".aurelius-drawer")).to_be_visible()

        # Nothing is deleted: the store still reads the entity ACTIVE.
        still = authenticated.request.get(
            urljoin(root_url, f"/api/atlas/v2/entity/guid/{guid}"),
            headers={"authorization": f"Bearer {user_token}"},
        ).json()["entity"]
        assert still["status"] == "ACTIVE", still["status"]

        # The full hold confirms: the pointer stays down past the three
        # seconds, the delete goes out, and the app navigates itself to the
        # browse landing (VDE-11) — the drawer outlet is cleared (DD-330's
        # shape) and the details screen underneath is gone with it.
        authenticated.mouse.move(box["x"] + box["width"] / 2, box["y"] + box["height"] / 2)
        authenticated.mouse.down()
        authenticated.wait_for_timeout(4_200)
        authenticated.mouse.up()

        expect(authenticated).to_have_url(re.compile(r"/en-US/search/browse$"), timeout=15_000)
        expect(authenticated.locator(".aurelius-drawer")).to_have_count(0)
        expect(authenticated.locator("#browse-placeholder")).to_be_visible()

        _wait_entity_read(
            authenticated, root_url, user_token, guid, predicate=lambda entity: entity["status"] == "DELETED"
        )
    finally:
        _delete_entity(authenticated, root_url, user_token, guid)


# impact=minor, likelihood=medium (the preview render inside the drawer; the save is proven by the editor suite)
@pytest.mark.medium
def test__the_editor_previews_markdown_it_saves(authenticated: Page, root_url: str, user_token: str) -> None:
    """The description's markdown previews in the drawer and renders on details (EDT-20).

    The write-then-read circle in one scenario: the markdown field's Preview
    tab renders the typed source through the shared block (UIC-26, DD-352),
    the save sends the source string unchanged (EDT-06 untouched), and the
    details description box — the same block (DET-10, DD-321) — shows the
    same rendered heading. What you preview is what details will show.
    """
    run = secrets.token_hex(4)
    name = f"zz{run}md"
    guids = _seed_entities(authenticated, root_url, user_token, "DataSet", [name])
    guid = guids["-0"]

    try:
        _open_editor_from_details(authenticated, root_url, guid)

        drawer = authenticated.locator(".aurelius-drawer")
        area = authenticated.locator("textarea#editor-description")
        area.fill("# The saved heading")

        drawer.get_by_role("tab", name="Preview").click()
        preview_heading = drawer.locator(".aurelius-markdown-editor-preview h1.title")
        expect(preview_heading).to_have_text("The saved heading")

        # Back to Write: the source stays where it was (the pane only hid).
        drawer.get_by_role("tab", name="Write").click()
        expect(area).to_have_value("# The saved heading")

        drawer.locator("button.aurelius-editor-save").click()

        expect(authenticated).to_have_url(re.compile(rf"/en-US/search/details/{guid}$"))
        expect(authenticated.locator(".aurelius-drawer")).to_have_count(0)
        # The details box renders the saved source through the same block:
        # the heading there is the drawer's preview, one renderer (DD-321).
        expect(authenticated.locator(".aurelius-details-description h1.title")).to_have_text("The saved heading")
    finally:
        _delete_entity(authenticated, root_url, user_token, guid)


@pytest.mark.critical
def test__the_editor_tags_an_entity(authenticated: Page, root_url: str, user_token: str) -> None:
    """A classification added in the drawer lands as a chip on the details header (EDT-05, EDT-12).

    The tag box offers the typedefs whose ``entityTypes`` name the entity's
    type: a run-unique classification typedef over ``DataSet`` is seeded
    first, typed into the box, Enter attaches the tag, Save applies the
    diff (DD-326), and the chip rides the details header's classification
    field. The typedef and the entity are deleted at the end (namespaced
    self-cleaning).
    """
    run = secrets.token_hex(4)
    tag = f"zz{run}tag"
    name = f"zz{run}tagged"

    typedef = authenticated.request.post(
        urljoin(root_url, "/api/atlas/v2/types/typedefs"),
        data=json.dumps({"classificationDefs": [{"name": tag, "entityTypes": ["DataSet"]}]}),
        headers={"content-type": "application/json", "authorization": f"Bearer {user_token}"},
    )
    assert typedef.status == 200, typedef.text()

    guids = _seed_entities(authenticated, root_url, user_token, "DataSet", [name])
    guid = guids["-0"]

    try:
        _open_editor_from_details(authenticated, root_url, guid)

        drawer = authenticated.locator(".aurelius-drawer")
        expect(drawer.locator(".aurelius-editor-tag")).to_have_count(0)

        box = authenticated.locator("input.aurelius-editor-classification-input")
        box.fill(tag)
        box.press("Enter")
        expect(drawer.locator(".aurelius-editor-tag")).to_have_text(tag)

        drawer.locator("button.aurelius-editor-save").click()
        expect(authenticated).to_have_url(re.compile(rf"/en-US/search/details/{guid}$"))

        chips = authenticated.locator(".aurelius-details-classifications .control")
        expect(chips).to_have_count(1)
        expect(chips.first).to_have_text(tag)
    finally:
        # CLS-12: the type stays in use while a classification instance of it
        # exists in ANY state — a soft-deleted entity keeps its tag — so the
        # instance must go through the detach (the editor's own DELETE path,
        # DD-326) before the entity and then the typedef can. The detach and
        # the typedef delete both race the async work the server runs after
        # the write: the detach answers 406 "propagation is in progress ...
        # please try again" until the attach settles, the typedef delete 409
        # "has references" until the detach is visible. Retry both (bounded;
        # self-cleaning only).
        deadline = time.monotonic() + 30
        while True:
            detached = authenticated.request.delete(
                urljoin(root_url, f"/api/atlas/v2/entity/guid/{guid}/classification/{tag}"),
                headers={"authorization": f"Bearer {user_token}"},
            )
            if detached.status in (204, 404):  # detached, or already gone
                break
            assert detached.status == 406, detached.text()
            assert time.monotonic() < deadline, detached.text()
            time.sleep(1)

        _delete_entity(authenticated, root_url, user_token, guid)
        while True:
            removed = authenticated.request.delete(
                urljoin(root_url, f"/api/atlas/v2/types/typedef/name/{tag}"),
                headers={"authorization": f"Bearer {user_token}"},
            )
            if removed.status in (204, 404):  # gone, or never landed
                break
            assert removed.status == 409, removed.text()
            assert time.monotonic() < deadline, removed.text()
            time.sleep(1)


@pytest.mark.critical
def test__the_editor_creates_an_entity(authenticated: Page, root_url: str, user_token: str) -> None:
    """The hero `+` opens the picker; a chosen type and a name create an entity (EDT-04, EDT-12).

    Create mode (DD-325's payload idiom, server-side): the picker lists the
    metamodel types (EDT-04 as scoped by MMS-07), Dataset is chosen — the type
    rides the drawer's URL segment (DD-330) — the form is empty, a switch to
    Collection and back re-seeds it (EDT-04), Save sends the negative temp
    guid, and the landing URL carries the server's guid from ``guidAssignments``
    — the new entity's details, titled by the entered name.
    """
    run = secrets.token_hex(4)
    name = f"zz{run}created"

    authenticated.goto(urljoin(root_url, "/en-US/search/browse"))
    plus = authenticated.locator("button.aurelius-create-entity")
    expect(plus).to_be_visible()  # the writer holds atlas-write (EDT-09)
    plus.click()

    drawer = authenticated.locator(".aurelius-drawer")
    expect(drawer).to_contain_text("Create new entity")

    authenticated.locator(".aurelius-editor-picker select").select_option(label="Dataset")

    # The type is part of the path (DD-330), and the form for the chosen
    # type arrived with it: an empty required name, no entity yet.
    expect(authenticated).to_have_url(re.compile(r"/en-US/search/browse\(drawer:create/m4i_dataset\)$"))
    expect(authenticated.locator("#editor-name")).to_have_value("")

    # Switching (EDT-04): a half-typed draft is dropped, the picker stays
    # selected at the new type, and switching back re-seeds the Dataset form.
    authenticated.locator("#editor-name").fill("half-typed")
    authenticated.locator(".aurelius-editor-picker select").select_option(label="Collection")
    expect(authenticated).to_have_url(re.compile(r"/en-US/search/browse\(drawer:create/m4i_collection\)$"))
    authenticated.locator(".aurelius-editor-picker select").select_option(label="Dataset")
    expect(authenticated.locator("#editor-name")).to_have_value("")

    authenticated.locator("#editor-name").fill(name)
    drawer.locator("button.aurelius-editor-save").click()

    # The landing URL is the created entity's real guid (EDT-06, DD-325).
    expect(authenticated).to_have_url(re.compile(r"/en-US/search/details/[0-9a-f-]{36}$"), timeout=30_000)
    expect(authenticated.locator("h1.aurelius-details-title")).to_have_text(name)

    created = re.search(r"/details/([0-9a-f-]{36})$", authenticated.url)
    assert created is not None
    _delete_entity(authenticated, root_url, user_token, created.group(1))


@pytest.mark.critical
def test__the_editor_links_a_relationship(authenticated: Page, root_url: str, user_token: str) -> None:
    """A pick in the editor's picker lands a real edge, read back at both ends (EDT-14, EDT-16).

    The DataSet editor's ``inputToProcesses`` picker searches processes by
    name prefix (EDT-14's contract): the seeded process is picked, Save posts
    the merged entity (EDT-16), and reopening the editor shows the chip — the
    body the save wrote, read back through EDT-15's ACTIVE-only seed. The
    Process reads the data set on its ``inputs`` end through the API; the
    details table shows neither end because DET-11's verbatim legacy blacklist
    lists the relationship keys (inputs, outputs, inputToProcesses).
    """
    run = secrets.token_hex(4)
    dataset_name = f"zz{run}dataset"
    process_name = f"zz{run}process"
    ds_guid = _seed_entities(authenticated, root_url, user_token, "DataSet", [dataset_name])["-0"]
    proc_guid = _seed_entities(authenticated, root_url, user_token, "Process", [process_name])["-0"]

    try:
        _open_editor_from_details(authenticated, root_url, ds_guid)
        drawer = authenticated.locator(".aurelius-drawer")
        block = drawer.locator('.aurelius-editor-relationship[data-field="inputToProcesses"]')

        # Type the process's name; the picker's debounced prefix-search finds
        # the row, and the click attaches it as a chip (EDT-14).
        box = block.locator(".aurelius-token-input")
        box.fill(process_name)
        row = block.locator('[role="option"]').filter(has_text=process_name)
        expect(row).to_be_visible(timeout=10_000)
        row.click()
        expect(block.locator(".aurelius-token-chip")).to_have_count(1)

        drawer.locator("button.aurelius-editor-save").click()
        expect(authenticated).to_have_url(re.compile(rf"/en-US/search/details/{ds_guid}$"))

        # The edge's read visibility before the editor's own read: the reopened
        # editor reads once and keeps its answer for its whole life, and the
        # edge records are searched, not joined (near-real-time, CLS-12's race)
        # — racing it is a flake, not a product bug.
        _wait_entity_read(
            authenticated,
            root_url,
            user_token,
            ds_guid,
            predicate=lambda entity: any(
                entry["guid"] == proc_guid and entry.get("relationshipStatus") == "ACTIVE"
                for entry in entity.get("relationshipAttributes", {}).get("inputToProcesses", [])
            ),
        )

        # The reopened picker holds the chip: the saved relationshipAttributes
        # survived the round trip (EDT-16 -> EDT-15).
        _open_editor_from_details(authenticated, root_url, ds_guid)
        chip = drawer.locator('[data-field="inputToProcesses"] .aurelius-token-chip')
        expect(chip).to_have_count(1)
        expect(chip).to_contain_text(process_name)

        # The other end, through the API: the Process's `inputs` edge is
        # ACTIVE to the data set (the read 7.6 answers, probed shape) — the
        # same visibility wait, since the edge was just written.
        _wait_entity_read(
            authenticated,
            root_url,
            user_token,
            proc_guid,
            predicate=lambda entity: any(
                entry["guid"] == ds_guid and entry.get("relationshipStatus") == "ACTIVE"
                for entry in entity.get("relationshipAttributes", {}).get("inputs", [])
            ),
        )
    finally:
        _delete_entity(authenticated, root_url, user_token, proc_guid)
        _delete_entity(authenticated, root_url, user_token, ds_guid)


@pytest.mark.critical
def test__the_editor_unlinks_a_relationship(authenticated: Page, root_url: str, user_token: str) -> None:
    """The chip's delete removes the edge and the tombstone never returns (EDT-15, EDT-16).

    The edge is seeded through the API (the update POST's full-replace
    contract, probed), so the scenario starts from a chip it did not create:
    the delete empties the picker, Save sends the empty list (EDT-16), and
    the reopened editor shows no chip — the server's DELETED tombstone stays
    out of the seed forever (EDT-15; the edge itself stays DELETED under the
    Java-parity rule DD-340 records).
    """
    run = secrets.token_hex(4)
    dataset_name = f"zz{run}dataset"
    process_name = f"zz{run}process"
    ds_guid = _seed_entities(authenticated, root_url, user_token, "DataSet", [dataset_name])["-0"]
    proc_guid = _seed_entities(authenticated, root_url, user_token, "Process", [process_name])["-0"]

    # The update body repeats the mandatory plain attributes: the server
    # validates the whole entity on an update, not only what changed (probed —
    # a body without them answers the create/update parameters error).
    seeded = authenticated.request.post(
        urljoin(root_url, "/api/atlas/v2/entity"),
        data=json.dumps(
            {
                "entity": {
                    "guid": ds_guid,
                    "typeName": "DataSet",
                    "attributes": {"name": dataset_name, "qualifiedName": dataset_name},
                    "relationshipAttributes": {"inputToProcesses": [{"guid": proc_guid, "typeName": "Process"}]},
                }
            }
        ),
        headers={"content-type": "application/json", "authorization": f"Bearer {user_token}"},
    )
    assert seeded.status == 200, seeded.text()

    # The seeded edge must be visible before the editor opens on it (the
    # one-read-caches-forever rule the links scenario documents).
    _wait_entity_read(
        authenticated,
        root_url,
        user_token,
        ds_guid,
        predicate=lambda entity: any(
            entry["guid"] == proc_guid and entry.get("relationshipStatus") == "ACTIVE"
            for entry in entity.get("relationshipAttributes", {}).get("inputToProcesses", [])
        ),
    )

    try:
        _open_editor_from_details(authenticated, root_url, ds_guid)
        drawer = authenticated.locator(".aurelius-drawer")
        block = drawer.locator('.aurelius-editor-relationship[data-field="inputToProcesses"]')
        expect(block.locator(".aurelius-token-chip")).to_have_count(1)

        block.locator(".aurelius-classification-chip-delete").first.click()
        expect(block.locator(".aurelius-token-chip")).to_have_count(0)

        drawer.locator("button.aurelius-editor-save").click()
        expect(authenticated).to_have_url(re.compile(rf"/en-US/search/details/{ds_guid}$"))

        # The removal must show on the read before the editor reopens (the
        # visibility wait, again): the reopened read must be the post-removal
        # state, or the editor would cache the stale ACTIVE edge.
        _wait_entity_read(
            authenticated,
            root_url,
            user_token,
            ds_guid,
            predicate=lambda entity: (
                not any(
                    entry.get("relationshipStatus") == "ACTIVE"
                    for entry in entity.get("relationshipAttributes", {}).get("inputToProcesses", [])
                )
            ),
        )

        # Reopened: the DELETED tombstone earns no chip (EDT-15).
        _open_editor_from_details(authenticated, root_url, ds_guid)
        expect(drawer.locator('[data-field="inputToProcesses"] .aurelius-token-chip')).to_have_count(0)
    finally:
        _delete_entity(authenticated, root_url, user_token, proc_guid)
        _delete_entity(authenticated, root_url, user_token, ds_guid)


@pytest.mark.critical
def test__the_editor_requires_a_mandatory_relationship(authenticated: Page, root_url: str, user_token: str) -> None:
    """Create refuses until the mandatory relationship picker holds a chip (EDT-13, EDT-17).

    A run-unique pair of types seeded through the typedef door plays the part
    the vendored ``ozone_bucket.volume`` used to (DD-734, 18.1): the holder
    gets a ``COMPOSITION`` over the leaf with a non-container ``SINGLE`` end,
    which makes the leaf's ``volume`` attribute non-optional (the rule
    relationship_type.py derives). The create form marks the picker ``*``
    (EDT-13) and the save bails while the picker is empty — no POST, the
    notification stands (EDT-17, where the server itself would answer the
    create with the mandatory-attribute error). Picking the API-seeded leaf
    through the picker's own search lands the create, and reopening shows its
    chip. The drawer opens on the deep link (``drawer:create/<type>``): the
    create picker lists the icon map's types alone (MMS-07, DD-719), so a
    runtime type arrives no person could pick from that list either.
    """
    run = secrets.token_hex(4)
    leaf_type, holder_type, link = f"zz{run}_leaf", f"zz{run}_holder", f"zz{run}_holds"
    volume_name = f"zz{run}volume"
    bucket_name = f"zz{run}bucket"

    entity_def = {"superTypes": ["DataSet"], "attributeDefs": []}
    seeded = authenticated.request.post(
        urljoin(root_url, "/api/atlas/v2/types/typedefs"),
        data=json.dumps(
            {
                "entityDefs": [
                    {"name": leaf_type, **entity_def},
                    {"name": holder_type, **entity_def},
                ],
                "relationshipDefs": [
                    {
                        "name": link,
                        "relationshipCategory": "COMPOSITION",
                        "endDef1": {"type": leaf_type, "name": "buckets", "isContainer": True, "cardinality": "SET"},
                        "endDef2": {"type": holder_type, "name": "volume", "cardinality": "SINGLE"},
                    }
                ],
            }
        ),
        headers={"content-type": "application/json", "authorization": f"Bearer {user_token}"},
    )
    assert seeded.status == 200, seeded.text()

    volume_guid = _seed_entities(authenticated, root_url, user_token, leaf_type, [volume_name])["-0"]

    created: str | None = None
    try:
        _goto_app(authenticated, urljoin(root_url, f"/en-US/search/browse(drawer:create/{holder_type})"))

        drawer = authenticated.locator(".aurelius-drawer")
        block = drawer.locator('.aurelius-editor-relationship[data-field="volume"]')
        # No catalogue key: the raw name (EDT-33), and no target-type bracket (EDT-34, DD-724).
        expect(block.locator("p.label")).to_contain_text("volume")
        expect(block.locator("p.label")).not_to_contain_text(leaf_type)
        expect(block.locator("p.label .has-text-danger")).to_have_text("*")  # the EDT-13 marker

        authenticated.locator("#editor-name").fill(bucket_name)
        drawer.locator("button.aurelius-editor-save").click()

        # EDT-17: the save fires nothing — the notification appears and the
        # drawer stays open on the create route.
        expect(drawer.locator(".aurelius-editor-notification")).to_be_visible()
        expect(authenticated).to_have_url(re.compile(rf"drawer:create/{holder_type}"))

        # The pick (EDT-14): the leaf arrives through the picker's search.
        box = block.locator(".aurelius-token-input")
        box.fill(volume_name)
        row = block.locator('[role="option"]').filter(has_text=volume_name)
        expect(row).to_be_visible(timeout=10_000)
        row.click()
        expect(block.locator(".aurelius-token-chip")).to_have_count(1)

        drawer.locator("button.aurelius-editor-save").click()
        expect(authenticated).to_have_url(re.compile(r"/en-US/search/details/[0-9a-f-]{36}$"), timeout=30_000)
        expect(authenticated.locator("h1.aurelius-details-title")).to_have_text(bucket_name)

        landed = re.search(r"/details/([0-9a-f-]{36})$", authenticated.url)
        assert landed is not None
        created = bucket_guid = landed.group(1)

        # The leaf edge visible before the reopened editor reads (the rule
        # the links scenario documents).
        _wait_entity_read(
            authenticated,
            root_url,
            user_token,
            bucket_guid,
            predicate=lambda entity: (
                (entity.get("relationshipAttributes", {}).get("volume") or {}).get("guid") == volume_guid
            ),
        )

        _open_editor_from_details(authenticated, root_url, bucket_guid)
        expect(drawer.locator('[data-field="volume"] .aurelius-token-chip')).to_contain_text(volume_name)
    finally:
        if created is not None:
            _delete_entity(authenticated, root_url, user_token, created)
        _delete_entity(authenticated, root_url, user_token, volume_guid)
        # ENS-09 keeps a type in use while an entity of it exists in ANY state
        # and the deletes above are soft (DD-059), so the run's own entities are
        # purged before their types may go (DD-734).
        _purge_and_drop_types(
            authenticated,
            root_url,
            user_token,
            [leaf_type, holder_type],
            [link, leaf_type, holder_type],
        )


# impact=major, likelihood=high (the conflict re-edit is a young promise on the mutation door)
@pytest.mark.high
@pytest.mark.covers(rules=["VDE-07"])
def test__the_editor_re_edits_from_the_stored_view_after_a_conflict(
    authenticated: Page, root_url: str, user_token: str
) -> None:
    """A lost update answers the conflict line; saving again writes over the stored version (VDE-07, AVW-04).

    The drawer reads once and keeps its answer, so when another hand changes
    the entity while it is open the save is a lost update: the door answers 409
    with the stored view beside it (AVW-04) and the editor re-seeds from that
    view (VDE-07) — the typed edit survives, the untouched owner slot takes the
    stored answer's new value, and the line above the fields says what
    happened. The second Save rides the stored version and lands: the drawer
    goes away and the details screen underneath shows the saved text.
    """
    run = secrets.token_hex(4)
    name = f"zz{run}conflict"
    guids = _seed_entities(authenticated, root_url, user_token, "DataSet", [name])
    guid = guids["-0"]

    try:
        _open_editor_from_details(authenticated, root_url, guid)
        drawer = authenticated.locator(".aurelius-drawer")
        # The drawer's read has landed: the form carries the seeded name.
        expect(authenticated.locator("#editor-name")).to_have_value(name)

        # Another hand saves through the API while the drawer is open: the put
        # sets a new updateTime, so the drawer now edits a stale view.
        bumped = authenticated.request.put(
            urljoin(root_url, f"/api/atlas/v2/entity/guid/{guid}"),
            params={"name": "owner"},
            data=json.dumps("ops-after-conflict"),
            headers={"content-type": "application/json", "authorization": f"Bearer {user_token}"},
        )
        assert bumped.status == 200, bumped.text()

        authenticated.locator("textarea#editor-description").fill("The kept edit.")
        drawer.locator("button.aurelius-editor-save").click()

        # The door refuses the lost update whole (AVW-04): the warning line
        # appears, the drawer stays open, and the typed edit survives (VDE-07).
        expect(drawer.locator(".aurelius-editor-conflict")).to_be_visible()
        expect(authenticated.locator("textarea#editor-description")).to_have_value("The kept edit.")
        expect(authenticated).to_have_url(re.compile(r"drawer:edit"))

        # The re-seed (VDE-07): the untouched owner slot now carries the
        # stored answer's new value; the typed description stayed.
        expect(authenticated.locator("#editor-owner")).to_have_value("ops-after-conflict")

        # Saving again rides the stored updateTime and lands (AVW-04): the
        # drawer closes and the details screen shows the kept edit.
        drawer.locator("button.aurelius-editor-save").click()
        expect(authenticated).to_have_url(re.compile(rf"/en-US/search/details/{guid}$"))
        expect(authenticated.locator(".aurelius-drawer")).to_have_count(0)
        expect(authenticated.locator(".aurelius-details-description")).to_have_text("The kept edit.")
    finally:
        _delete_entity(authenticated, root_url, user_token, guid)


# impact=major, likelihood=low (the refusal path is young, but two creators colliding is rare)
@pytest.mark.medium
@pytest.mark.covers(rules=["VDE-08"])
def test__the_editor_keeps_the_draft_when_the_name_is_taken(
    authenticated: Page, root_url: str, user_token: str
) -> None:
    """A create whose qualified name is held answers one line and keeps the draft (VDE-08, AVW-06).

    The door answers 409 ``ENTITY_NAME_TAKEN`` for a create whose unique
    ``qualifiedName`` another entity holds (AVW-06); the editor adds one alert
    line, the drawer stays open, and the typed name survives (VDE-08) — no
    conflict line, because the name-taken answer carries no stored view. The
    form does not expose ``qualifiedName`` (the client sends a fresh uuid,
    DD-592), so the scenario routes the door's POST and hands the server the
    held qualified name in the browser's place: the 409 the page renders is the
    real server's refusal.
    """
    run = secrets.token_hex(4)
    held_name = f"zz{run}held"
    draft_name = f"zz{run}draft"
    # Seed on the type the editor creates (m4i_dataset): a create's unique
    # value is checked against its own type and its sub types (ENS-06), so a
    # held name on a base supertype would not collide (DD-719).
    guids = _seed_entities(authenticated, root_url, user_token, "m4i_dataset", [held_name])

    def _hand_the_held_name(route: Route) -> None:
        body = json.loads(route.request.post_data or "{}")
        body.setdefault("attributes", {})["qualifiedName"] = held_name
        route.continue_(post_data=json.dumps(body))

    authenticated.route("**/api/aurelius/v1/entity", _hand_the_held_name)
    try:
        authenticated.goto(urljoin(root_url, "/en-US/search/browse"))
        authenticated.locator("button.aurelius-create-entity").click()
        authenticated.locator(".aurelius-editor-picker select").select_option(label="Dataset")
        authenticated.locator("#editor-name").fill(draft_name)
        drawer = authenticated.locator(".aurelius-drawer")
        drawer.locator("button.aurelius-editor-save").click()

        # The create is refused (AVW-06): the drawer stays open on the create
        # route with the draft intact, and no conflict line shows (VDE-08).
        expect(drawer.locator(".aurelius-editor-conflict")).to_have_count(0)
        expect(authenticated).to_have_url(re.compile(r"drawer:create/m4i_dataset"))
        expect(authenticated.locator("#editor-name")).to_have_value(draft_name)
        expect(authenticated.locator(".aurelius-badge-dot")).to_have_count(1)  # the bell marks the alert unread

        # The line itself, in the alerts feed: the bell's drawer names the
        # refusal. The kept drawer rides the scrim that covers the navbar, so
        # it goes first (16.5a's idiom) — pressed on a field, because the
        # drawer listens for Escape on its panel and a failed Save leaves the
        # focus on the body, where the keydown would die.
        authenticated.locator("#editor-name").press("Escape")
        authenticated.locator('a.navbar-item[aria-label="Alerts"]').click()
        expect(authenticated.locator(".aurelius-alert-message")).to_have_text(
            "That name is already held by another entity."
        )
    finally:
        authenticated.unroute("**/api/aurelius/v1/entity")
        _delete_entity(authenticated, root_url, user_token, guids["-0"])


def _seed_gov_rule(page: Page, root_url: str, token: str, attributes: dict[str, str]) -> str:
    """Seed one ACTIVE governance rule through the proxy; return its real guid (12.7, VEV-02).

    The banner test seeds through the catalogue — the same store the deployed
    validate-entity app reads — with the run's word in every visible string.
    A rule answers only the drafts of the type its qualifiedName names (VEV-07),
    so the default prefix is the editor's own DataSet type; a caller seeding for
    another type (the person box) passes its qualifiedName in ``attributes``.
    The assertions still name this run's sentences (DD-223).
    """
    name = attributes["name"]
    body = {
        "entities": [
            {
                "typeName": "m4i_gov_data_quality",
                "guid": "-0",
                # `id` is mandatory on the type (isOptional: false): the create must
                # carry it, the legacy editor's create seeds -1 (the rules editor's
                # idiom in quality-fields.ts); the attribute is not unique.
                "attributes": {"qualifiedName": f"DataSet--{name}", "id": -1, **attributes},
            }
        ]
    }
    response = page.request.post(
        urljoin(root_url, "/api/atlas/v2/entity/bulk"),
        data=json.dumps(body),
        headers={"content-type": "application/json", "authorization": f"Bearer {token}"},
    )

    assert response.status == 200, response.text()

    return response.json()["guidAssignments"]["-0"]


# impact=major, likelihood=high (a banner verdict is a young promise with churn on its path)
@pytest.mark.high
@pytest.mark.covers(rules=["EDT-24"])
def test__the_editor_shows_the_governance_banner(authenticated: Page, root_url: str, user_token: str) -> None:
    """The drawer validates the draft and paints the live verdict lines (EDT-23, EDT-24, VEV-02).

    The 12.7 editor over the deployed chain: opening the drawer posts the draft
    to ``/validate-entity/`` through the webapp's own nginx (EDT-22), the app
    reads its rules from the chain's server as its own identity (VEV-04), and
    the seeded rules answer. The drawer renders one line per verdict whose
    attribute names a rendered control (EDT-24): the DataSet editor carries
    ``name`` and the description key, so this run's success line appears under
    Name and its refusal line, warning-iconed, under Description. Since 12.7a
    the answer carries only DataSet's own rules (VEV-07, DD-631): the sample
    corpus's m4i rules — the ones that once warned a dataset about a missing
    ``kibanaSpace`` — stay out, which the exact per-field line counts pin
    beside the run-keyed lookups. Self-cleaned.
    """
    run = secrets.token_hex(4)
    name = f"zz{run}govbanner"
    ok_line = f"zz{run} the dataset carries a name"
    warn_line = f"zz{run} the dataset has no description"
    guids = _seed_entities(authenticated, root_url, user_token, "DataSet", [name])
    guid = guids["-0"]
    rule_guids = [
        _seed_gov_rule(
            authenticated,
            root_url,
            user_token,
            {
                "name": f"zz{run}name-present",
                "active": "true",
                "dqcheckkind": "ATTRIBUTE_PRESENT",
                "dqattribute": "name",
                "qualityDimension": "COMPLETENESS",
                "compliantMessage": ok_line,
                "nonCompliantMessage": f"zz{run} the dataset carries no name",
            },
        ),
        _seed_gov_rule(
            authenticated,
            root_url,
            user_token,
            {
                "name": f"zz{run}description-filled",
                "active": "true",
                "dqcheckkind": "ATTRIBUTE_NOT_EMPTY",
                "dqattribute": "description",
                "qualityDimension": "COMPLETENESS",
                "compliantMessage": f"zz{run} the dataset describes itself",
                "nonCompliantMessage": warn_line,
            },
        ),
    ]

    try:
        _open_editor_from_details(authenticated, root_url, guid)
        drawer = authenticated.locator(".aurelius-drawer")

        # The open round renders the lines without any edit (EDT-23's trigger),
        # each under its own control (EDT-24's keying), icon by the verdict.
        # The unfiltered counts are the VEV-07 proof: no foreign rule's line
        # rides either control — the drawer shows exactly this run's two.
        name_field = drawer.locator(".aurelius-editor-field", has=authenticated.locator("#editor-name"))
        ok = name_field.locator("[data-gov-line]").filter(has_text=ok_line)
        expect(ok).to_have_count(1)
        expect(ok.locator(".icon.has-text-success")).to_have_count(1)
        expect(name_field.locator("[data-gov-line]")).to_have_count(1)

        description_field = drawer.locator(
            ".aurelius-editor-field", has=authenticated.locator("textarea#editor-description")
        )
        warn = description_field.locator("[data-gov-line]").filter(has_text=warn_line)
        expect(warn).to_have_count(1)
        expect(warn.locator(".icon.has-text-warning")).to_have_count(1)
        expect(description_field.locator("[data-gov-line]")).to_have_count(1)
    finally:
        _delete_entity(authenticated, root_url, user_token, guid)
        for rule_guid in rule_guids:
            _delete_entity(authenticated, root_url, user_token, rule_guid)


# impact=major, likelihood=low (the drawer survives a dead call; a contained resilience path)
@pytest.mark.medium
@pytest.mark.covers(rules=["EDT-23"])
def test__an_aborted_validation_leaves_the_drawer_usable(authenticated: Page, root_url: str, user_token: str) -> None:
    """A validation call that never answers keeps the drawer whole (EDT-23).

    The quiet swallow over the deployed stack: ``page.route`` aborts the
    ``/validate-entity/`` request, so the browser gets no answer at all (the
    aux API down, the network gone). The editor renders no lines, raises no
    alert (the legacy's ``catchError`` to empty, DD-446), and the drawer stays
    fully usable — the seeded value reads back and a save still lands. This
    proves the banner is advisory: an aux API failure never interrupts the edit.
    """
    run = secrets.token_hex(4)
    name = f"zz{run}abortgov"
    guids = _seed_entities(authenticated, root_url, user_token, "DataSet", [name])
    guid = guids["-0"]

    authenticated.route("**/validate-entity/", lambda route: route.abort())
    try:
        _open_editor_from_details(authenticated, root_url, guid)
        drawer = authenticated.locator(".aurelius-drawer")
        expect(authenticated.locator("#editor-name")).to_have_value(name)

        # No lines, no alert: the aborted call renders nothing and says
        # nothing. The settle is the window a live call needs to answer, so
        # the zero count below pins the abort, not a race.
        authenticated.wait_for_timeout(400)
        expect(drawer.locator("[data-gov-line]")).to_have_count(0)
        expect(authenticated.locator(".aurelius-badge-dot")).to_have_count(0)

        # The drawer stays usable: an edit saves through the normal path.
        authenticated.locator("textarea#editor-description").fill("Saved despite the failed validation.")
        drawer.locator("button.aurelius-editor-save").click()
        expect(authenticated).to_have_url(re.compile(rf"/en-US/search/details/{guid}$"))
        expect(authenticated.locator(".aurelius-details-description")).to_have_text(
            "Saved despite the failed validation."
        )
    finally:
        authenticated.unroute("**/validate-entity/")
        _delete_entity(authenticated, root_url, user_token, guid)


@pytest.mark.critical
def test__the_reader_sees_no_editor_affordances(reader_authenticated: Page, root_url: str) -> None:
    """The reader (atlas-read only) gets neither the pencil nor the `+` (EDT-09, EDT-12).

    The gate reads the token's ``resource_access.<atlasClientId>.roles``
    (DD-324): the dev reader holds ``atlas-read`` only, so the details
    pencil and the hero create button stay unrendered. The deep link is not
    route-guarded (EDT-09): the drawer still opens for a hand-typed outlet
    URL, where the server's 403 is the real gate — the reader's form simply
    cannot write, which is what the reader's save-path unit tests cover.
    """
    reader_authenticated.goto(urljoin(root_url, "/en-US/search/details/00000000-0000-0000-0000-000000000000"))
    expect(reader_authenticated.locator("nav.navbar")).to_be_visible()
    expect(reader_authenticated.locator("button.aurelius-details-edit")).to_have_count(0)

    reader_authenticated.goto(urljoin(root_url, "/en-US/search/browse"))
    expect(reader_authenticated.locator("button.aurelius-create-entity")).to_have_count(0)
