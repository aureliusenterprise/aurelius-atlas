import base64
import json
import re
import secrets
import time
from collections.abc import Callable
from urllib.parse import quote, urljoin

import pytest
from conftest import (
    COLLECTOR_HOST,
    COLLECTOR_PORT,
    LEGACY_PORT,
    SERVICE_PORT,
    TEMPO_HOST,
    TEMPO_PORT,
)
from playwright.sync_api import Locator, Page, expect

EN_PLACEHOLDER = (
    "Welcome to Aurelius Atlas! We would like to help you get started. Please pick your topic of interest below."
)
NL_PLACEHOLDER = "Welkom bij Aurelius Atlas! We helpen u graag op weg. Kies hieronder uw interessegebied."


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
    body = response.text()

    assert response.status == 200
    assert "text/html" in response.headers["content-type"]
    # The base tag's void-element serialisation is `>` (beasties) or `/>`
    # (Angular raw, DD-149) — accept both.
    assert re.search(rf'<base href="/{locale}/"\s*/?>', body)
    assert f'lang="{locale}"' in body


def test__config_json_is_served_at_the_origin_root(page: Page, root_url: str) -> None:
    """Bootstrap's runtime configuration is reachable at /config.json (SHL-02)."""
    response = page.request.get(urljoin(root_url, "/config.json"))

    assert response.status == 200
    body = response.json()
    assert body["apiBaseUrl"] == "/api"
    assert body["atlasClientId"] == "aurelius-atlas-server"  # EDT-09, DD-324


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
    """The nginx /api/ proxy forwards to the Atlas server with the prefix intact (APC-08, DD-139).

    The real Aurelius server (DD-142) answers the admin status endpoint, which
    needs no user (6.1a, AUT-01), through nginx -> TLS -> server, so the
    response proves the proxy path and that no proxy rewrites the /api prefix
    the client composes into its URLs.
    """
    response = page.request.get(urljoin(root_url, "/api/atlas/admin/status"))

    assert response.status == 200
    assert response.json()["Status"] == "ACTIVE"


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
    that would need one are deferred (DD-143).
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


def test__navbar_greets_the_signed_in_user(authenticated: Page) -> None:
    """The account dropdown's welcome line shows the Keycloak identity (SHC-05, SHC-09).

    ``preferred_username`` from the token, greeted through the
    shell.header.welcome bridge leaf.
    """
    welcome = authenticated.locator("a.navbar-link").filter(has_text="Logged in as")

    expect(welcome).to_be_visible()
    expect(welcome).to_have_text("Logged in as aurelius-writer")


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


def test__footer_shows_the_runtime_config_values(authenticated: Page) -> None:
    """The footer renders copyright year, app name, and version from /config.json (SHC-06, SHC-09)."""
    footer = authenticated.locator("footer.footer")

    expect(footer).to_be_visible()
    expect(footer.locator(".level-left")).to_have_text("Copyright 2022")
    expect(footer.locator(".level > .level-item")).to_have_text("Aurelius Atlas Data Governance")
    expect(footer.locator(".level-right")).to_have_text("0.0.0")
    expect(footer.locator(".level-left .icon svg")).to_be_visible()  # faCopyright


def test__documentation_link_points_at_the_aurelius_docs(authenticated: Page) -> None:
    """The navbar's Documentation link opens the Aurelius docs safely (SHC-03, SHC-09)."""
    link = authenticated.locator('a[target="_blank"]')

    expect(link).to_have_attribute("href", "https://aureliusenterprise.github.io/aurelius-atlas-documentation/")
    expect(link).to_have_attribute("rel", "noopener noreferrer")
    expect(link).to_have_text("Documentation")


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

    logout = authenticated.locator(".navbar-dropdown a.navbar-item", has_text="Logout")
    expect(logout).to_be_visible()


def test__details_screen_answers_a_404_deep_link_with_the_empty_state(authenticated: Page, root_url: str) -> None:
    """A direct visit to /search/details/<unknown guid> renders the empty screen (DET-07, DET-13).

    The URL is the screen's whole state (DD-186): the screen fetches the
    guid (DET-08), the server answers 404 (the store owns it, DET-03), and
    the screen keeps the empty shape — the fallback title, zero rows — with
    no alert for the 404 (DET-13: the empty state answers it, ALR-05's
    silence). The chrome strings ride the bridge (DET-04).
    """
    authenticated.goto(urljoin(root_url, "/en-US/search/details/7a1b-2c3d"))

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


def test__details_skeleton_renders_dutch_chrome(authenticated: Page, root_url: str) -> None:
    """The nl-NL locale renders the Dutch details chrome through the bridge (DET-04, DET-07)."""
    authenticated.goto(urljoin(root_url, "/nl-NL/search/details/7a1b-2c3d"))

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
        deleted = page.request.delete(
            urljoin(root_url, "/api/atlas/v2/entity/bulk"),
            params={"guid": entity["guid"]},
            headers={"authorization": f"Bearer {token}"},
        )

        assert deleted.status == 200, deleted.text()


def test__hero_search_shows_seeded_results_in_both_locales(authenticated: Page, root_url: str, user_token: str) -> None:
    """The hero field searches: seeded hits, the count, the card → details link (SRH-01..SRH-05).

    A query submitted in the hero's search field runs POST
    ``/api/atlas/v2/search/basic``, rides into ``search/results?query=``, and
    renders a card per hit with the count above the box (the legacy
    results screen, DD-218). Clicking a card deep-links the 2.3 skeleton with
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
    """Seed the DET-27 m4i mini-graph through the proxy's bulk endpoint.

    One bulk create carries the whole graph: a domain, an entity with two
    attributes and two persons on its people ends, a field on one attribute's
    ``fields`` end, and a dataset holding the field. The ends ride
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
        ]
    }

    response = page.request.post(
        urljoin(root_url, "/api/atlas/v2/entity/bulk"),
        data=json.dumps(body),
        headers={"content-type": "application/json", "authorization": f"Bearer {token}"},
    )

    assert response.status == 200, response.text()

    assignments = response.json()["guidAssignments"]

    return {key: assignments[temp_guid] for key, temp_guid in zip(names, [f"-{i}" for i in range(8)], strict=True)}


def _active_edge(entity: dict, key: str, guid: str) -> bool:
    """Whether an entity read holds an ACTIVE relationship edge to ``guid``."""
    return any(
        entry["guid"] == guid and entry.get("relationshipStatus") == "ACTIVE"
        for entry in entity.get("relationshipAttributes", {}).get(key, [])
    )


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
    page.go_back()
    expect(page).to_have_url(re.compile(r"/search/details/[^#]+$"))
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
    so the screen lands it once its box renders).
    """
    page.goto(urljoin(root_url, f"/en-US/search/details/{entity_guid}#related-attributes"))
    expect(page.locator("h1.aurelius-details-title")).to_have_text(f"zz{run}entity")
    expect(page.locator("#related-attributes aurelius-atlas-ui-entity-card")).to_have_count(2)
    page.wait_for_function(
        "() => Math.abs(document.getElementById('related-attributes').getBoundingClientRect().top - 68) <= 2"
    )


def test__m4i_details_render_the_seeded_sections(authenticated: Page, root_url: str, user_token: str) -> None:
    """The m4i details layout renders from a seeded mini-graph (DET-15..DET-20, DET-23, DET-27).

    The 7.21a screen on real data: the dispatch picks the m4i layout for the
    entity type (DET-15, a direct hit — no typedef walk), the People box
    shows the owner and steward links of the seeded people ends (DET-23),
    the Data Attributes section seeds from ``relationshipAttributes`` and
    resolves its cards with their definition text (DET-17, DET-19), the
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

        authenticated.goto(urljoin(root_url, f"/en-US/search/details/{entity_guid}"))
        expect(authenticated.locator("h1.aurelius-details-title")).to_have_text(f"zz{run}entity")

        # DET-23: the People box with the owner and steward links (the empty
        # Domain Lead end renders no row).
        people = authenticated.locator("#people-details")
        expect(people.locator(".aurelius-people-row")).to_have_count(2)
        expect(people).to_contain_text(f"Data Owner(s) : zz{run}owner")
        expect(people).to_contain_text(f"Data Steward(s) : zz{run}steward")

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
            "m4i_dataset",
            "m4i_person",
        ]:
            _purge_type(authenticated, root_url, user_token, type_name)
        _delete_entity(authenticated, root_url, user_token, dataset_guid)


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
    # restarts from the URL alone — the empty query, which searches every
    # entity (_ALL_ENTITY_TYPES, DD-221). The purged type holds exactly the
    # seeded glossary, so a filtered re-run would show its one row; the
    # every-entity search shows more (stack-size agnostic: on a fresh CI
    # stack the few seeded entities, on a shared stack the full page of ten).
    authenticated.reload()
    expect(authenticated.locator(".result-row")).not_to_have_count(1)


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
    """Delete one entity by guid (the editor scenarios' self-cleaning, EDT-12)."""
    deleted = page.request.delete(
        urljoin(root_url, "/api/atlas/v2/entity/bulk"),
        params={"guid": guid},
        headers={"authorization": f"Bearer {token}"},
    )

    assert deleted.status == 200, deleted.text()


def _open_editor_from_details(page: Page, root_url: str, guid: str) -> None:
    """Open the editor drawer on a seeded entity's details through the pencil (EDT-01)."""
    page.goto(urljoin(root_url, f"/en-US/search/details/{guid}"))
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


def test__the_editor_creates_an_entity(authenticated: Page, root_url: str, user_token: str) -> None:
    """The hero `+` opens the picker; a chosen type and a name create an entity (EDT-04, EDT-12).

    Create mode (DD-325's payload idiom, server-side): the picker lists the
    shipped types (EDT-04), DataSet is chosen — the type rides the drawer's
    URL segment (DD-330) — the form is empty, a switch to Process and back
    re-seeds it (EDT-04), Save sends the negative temp guid, and the landing
    URL carries the server's guid from ``guidAssignments`` — the new entity's
    details, titled by the entered name.
    """
    run = secrets.token_hex(4)
    name = f"zz{run}created"

    authenticated.goto(urljoin(root_url, "/en-US/search/browse"))
    plus = authenticated.locator("button.aurelius-create-entity")
    expect(plus).to_be_visible()  # the writer holds atlas-write (EDT-09)
    plus.click()

    drawer = authenticated.locator(".aurelius-drawer")
    expect(drawer).to_contain_text("Create new entity")

    authenticated.locator(".aurelius-editor-picker select").select_option(label="DataSet")

    # The type is part of the path (DD-330), and the form for the chosen
    # type arrived with it: an empty required name, no entity yet.
    expect(authenticated).to_have_url(re.compile(r"/en-US/search/browse\(drawer:create/DataSet\)$"))
    expect(authenticated.locator("#editor-name")).to_have_value("")

    # Switching (EDT-04): a half-typed draft is dropped, the picker stays
    # selected at the new type, and switching back re-seeds the DataSet form.
    authenticated.locator("#editor-name").fill("half-typed")
    authenticated.locator(".aurelius-editor-picker select").select_option(label="Process")
    expect(authenticated).to_have_url(re.compile(r"/en-US/search/browse\(drawer:create/Process\)$"))
    authenticated.locator(".aurelius-editor-picker select").select_option(label="DataSet")
    expect(authenticated.locator("#editor-name")).to_have_value("")

    authenticated.locator("#editor-name").fill(name)
    drawer.locator("button.aurelius-editor-save").click()

    # The landing URL is the created entity's real guid (EDT-06, DD-325).
    expect(authenticated).to_have_url(re.compile(r"/en-US/search/details/[0-9a-f-]{36}$"), timeout=30_000)
    expect(authenticated.locator("h1.aurelius-details-title")).to_have_text(name)

    created = re.search(r"/details/([0-9a-f-]{36})$", authenticated.url)
    assert created is not None
    _delete_entity(authenticated, root_url, user_token, created.group(1))


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
        box = block.locator(".aurelius-relationship-input")
        box.fill(process_name)
        row = block.locator('[role="option"]').filter(has_text=process_name)
        expect(row).to_be_visible(timeout=10_000)
        row.click()
        expect(block.locator(".aurelius-relationship-chip")).to_have_count(1)

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
        chip = drawer.locator('[data-field="inputToProcesses"] .aurelius-relationship-chip')
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
        expect(block.locator(".aurelius-relationship-chip")).to_have_count(1)

        block.locator(".aurelius-classification-chip-delete").first.click()
        expect(block.locator(".aurelius-relationship-chip")).to_have_count(0)

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
        expect(drawer.locator('[data-field="inputToProcesses"] .aurelius-relationship-chip')).to_have_count(0)
    finally:
        _delete_entity(authenticated, root_url, user_token, proc_guid)
        _delete_entity(authenticated, root_url, user_token, ds_guid)


def test__the_editor_requires_a_mandatory_relationship(authenticated: Page, root_url: str, user_token: str) -> None:
    """Create refuses until the mandatory relationship picker holds a chip (EDT-13, EDT-17).

    ``ozone_bucket.volume`` is a non-optional ``SINGLE`` relationship attribute
    (probed self-contained: neither type demands a plain attribute). The
    create form marks the picker ``*`` (EDT-13) and the save bails while the
    picker is empty — no POST, the notification stands (EDT-17, where the
    server itself would answer the create with the mandatory-attribute error).
    Picking the API-seeded volume through the picker's own search lands the
    create, and reopening shows its chip.
    """
    run = secrets.token_hex(4)
    volume_name = f"zz{run}volume"
    bucket_name = f"zz{run}bucket"
    volume_guid = _seed_entities(authenticated, root_url, user_token, "ozone_volume", [volume_name])["-0"]

    created: str | None = None
    try:
        authenticated.goto(urljoin(root_url, "/en-US/search/browse"))
        authenticated.locator("button.aurelius-create-entity").click()
        authenticated.locator(".aurelius-editor-picker select").select_option(label="ozone_bucket")

        drawer = authenticated.locator(".aurelius-drawer")
        block = drawer.locator('.aurelius-editor-relationship[data-field="volume"]')
        expect(block.locator("p.label")).to_contain_text("volume (ozone_volume)")
        expect(block.locator("p.label .has-text-danger")).to_have_text("*")  # the EDT-13 marker

        authenticated.locator("#editor-name").fill(bucket_name)
        drawer.locator("button.aurelius-editor-save").click()

        # EDT-17: the save fires nothing — the notification appears and the
        # drawer stays open on the create route.
        expect(drawer.locator(".aurelius-editor-notification")).to_be_visible()
        expect(authenticated).to_have_url(re.compile(r"drawer:create/ozone_bucket"))

        # The pick (EDT-14): the volume arrives through the picker's search.
        box = block.locator(".aurelius-relationship-input")
        box.fill(volume_name)
        row = block.locator('[role="option"]').filter(has_text=volume_name)
        expect(row).to_be_visible(timeout=10_000)
        row.click()
        expect(block.locator(".aurelius-relationship-chip")).to_have_count(1)

        drawer.locator("button.aurelius-editor-save").click()
        expect(authenticated).to_have_url(re.compile(r"/en-US/search/details/[0-9a-f-]{36}$"), timeout=30_000)
        expect(authenticated.locator("h1.aurelius-details-title")).to_have_text(bucket_name)

        landed = re.search(r"/details/([0-9a-f-]{36})$", authenticated.url)
        assert landed is not None
        created = bucket_guid = landed.group(1)

        # The volume edge visible before the reopened editor reads (the rule
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
        expect(drawer.locator('[data-field="volume"] .aurelius-relationship-chip')).to_contain_text(volume_name)
    finally:
        if created is not None:
            _delete_entity(authenticated, root_url, user_token, created)
        _delete_entity(authenticated, root_url, user_token, volume_guid)


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
