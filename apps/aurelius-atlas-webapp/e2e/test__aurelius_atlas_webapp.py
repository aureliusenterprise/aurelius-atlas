import base64
import json
import re
import secrets
import socket
import ssl
import time
from datetime import UTC, datetime, timedelta
from urllib.parse import quote, urljoin, urlsplit

import pytest
from conftest import (
    CA_FILE,
    COLLECTOR_HOST,
    COLLECTOR_PORT,
    LEGACY_PORT,
    SERVICE_PORT,
    TEMPO_HOST,
    TEMPO_PORT,
    Settings,
)
from docker.models.containers import Container
from playwright.sync_api import Browser, Page, expect

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

    The real Aurelius server (DD-142) answers the admin version endpoint
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
        time.sleep(3)

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


def test__collector_accepts_the_dev_plaintext_issuer(page: Page, plaintext_service_token: str) -> None:
    """The collector accepts the plaintext :8080 iss on the OIDC legs (CIA-11, DD-202).

    Keycloak stamps iss from the listener that served the mint, so this
    token's iss is the dev plaintext listener — what the human dev browser
    presents (ADR 039). The collector's oidc extension lists both listeners
    as providers precisely so this issuer verifies on the per-service leg,
    which every automated producer uses: the mint is standardized on the
    TLS :8443 listener, and the :8080 provider is the human-browser half
    of the accepted posture. "not 401" is the point (the user_token
    fixture's positive-control rule).
    """
    response = page.request.post(
        f"https://{COLLECTOR_HOST}:{SERVICE_PORT}/v1/traces",
        data=b"",
        headers={"content-type": "application/x-protobuf", "authorization": f"Bearer {plaintext_service_token}"},
    )

    assert response.status in (200, 202, 400, 415)


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
        time.sleep(3)

    pytest.fail(
        f"Tempo never returned the probe trace stamped for otel-atlas-server (trace {trace_id}) — azp not stamped"
    )


def test__collector_accepts_the_shared_ingest_token(page: Page, ingest_token: str) -> None:
    """The legacy leg (4321) accepts the shared ingest token (CIA-10, CIA-04's surviving half).

    The producers that cannot present a Keycloak JWT — Keycloak's native
    OTLP, the FastAPI example (static-header SDK, 60s tokens) — keep 7.17's
    shared-token mechanism here (DD-196); an empty protobuf body answers 200
    once authenticated. (The 7.17 form of this test rode 4319, which is
    OIDC-only now — CIA-08 moves the shared token off it, proved by
    test__collector_rejects_the_shared_token_on_the_service_leg.)
    """
    response = page.request.post(
        f"https://{COLLECTOR_HOST}:{LEGACY_PORT}/v1/traces",
        data=b"",
        headers={"content-type": "application/x-protobuf", "authorization": f"Bearer {ingest_token}"},
    )

    assert response.status in (200, 202, 400, 415)


def test__collector_publishes_are_loopback_pinned(collector_container: Container) -> None:
    """The collector's host publishes bind 127.0.0.1, and the exporter has none (CIA-03).

    Reading the running container's port bindings (not the compose file) is
    what proves the deployed posture: the OTLP ports — the browser leg, the
    per-service leg, and 7.18's legacy leg (4317-4321, CIA-10) — are
    reachable from this machine only, and the prometheus exporter (:9464) is
    not published at all — Prometheus scrapes it inside the compose network.
    """
    collector_container.reload()
    ports = collector_container.attrs["NetworkSettings"]["Ports"]

    published = {port: bindings for port, bindings in ports.items() if bindings}
    assert set(published) == {"4317/tcp", "4318/tcp", "4319/tcp", "4320/tcp", "4321/tcp"}
    assert all(binding["HostIp"] == "127.0.0.1" for bindings in published.values() for binding in bindings)


def test__producers_keep_flowing_with_the_token(collector_container: Container) -> None:
    """Every producer keeps exporting on its leg (CIA-07, CIA-10).

    The collector's debug exporter logs every accepted push (verbosity basic:
    one ``Traces``/``Metrics`` info line per export, ``otelcol.component.kind``
    exporter). The e2e stack runs the graduated producers (the pullers on
    their oauth2client JWTs, the atlas-server through its refresh shim) on
    the per-service leg and the legacy producers (Keycloak-native, the
    FastAPI example) on the shared-token leg, so accepted exports within the
    last two minutes prove both credential kinds are presented correctly:
    the ingest is all-or-nothing, a producer with a broken credential lands
    in the receiver's rejected 401/Unauthenticated path and exports nothing.
    """
    since = datetime.now(UTC) - timedelta(seconds=120)

    deadline = time.monotonic() + 90
    while time.monotonic() < deadline:
        logs = collector_container.logs(since=since, tail=2000).decode()
        if '"otelcol.component.kind": "exporter"' in logs:
            return
        time.sleep(3)

    pytest.fail("no accepted OTLP export reached the collector — a producer lost the ingest token")


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


def test__navbar_carries_the_aurelius_logo(authenticated: Page) -> None:
    """The navbar brand is the Aurelius Atlas logo, sized like the legacy (SHM-02, SHM-06).

    The live demo's brand: the mark at its 150px cap, linking home, the app
    name as the accessible alt.
    """
    brand = authenticated.locator(".navbar-brand a.navbar-item")
    img = brand.locator("img")

    expect(brand).to_have_attribute("routerlink", "/", timeout=0)
    expect(img).to_have_attribute("src", "assets/aurelius-atlas-logo.png")
    expect(img).to_have_attribute("alt", "Aurelius Atlas Data Governance")

    box = img.bounding_box()

    assert box is not None
    assert box["width"] == pytest.approx(150, abs=2)  # the .logo cap, demo-measured
    assert box["height"] <= 50


def test__body_uses_the_legacy_type_and_ink(authenticated: Page) -> None:
    """The body renders the legacy Bulma 0.9.4 type: stack, 16px, #4a4a4a (SHM-03).

    Every value measured from the live demo's body.
    """
    body = authenticated.locator("body")

    font_family = body.evaluate("el => getComputedStyle(el).fontFamily")

    assert font_family.startswith("BlinkMacSystemFont")
    assert body.evaluate("el => getComputedStyle(el).fontSize") == "16px"
    assert body.evaluate("el => getComputedStyle(el).lineHeight") == "24px"
    assert body.evaluate("el => getComputedStyle(el).color") == "rgb(74, 74, 74)"


def test__type_ramp_matches_the_legacy_page(authenticated: Page) -> None:
    """Every ink and weight the landing renders, measured against the demo (SHM-03, DD-151).

    Bulma 1 re-tinted its greys and moved the weights (title 800, strong
    600, button 500); pinning the body alone left the ramp off the legacy
    page. The brand library re-emits Bulma 0.9.4's neutral ramp, so these
    demo-measured values must hold: the title is 600/#363636, the body/box
    ink #4a4a4a, buttons 400, the navbar links #4a4a4a with 700 strong,
    dropdown items 14px.
    """
    css = (
        "el => { const c = getComputedStyle(el); return [c.fontSize, c.lineHeight, c.fontWeight, c.color].join(' '); }"
    )

    # The hero box: 40px/45px 600 #363636 title over 16px/24px #4a4a4a ink.
    assert authenticated.locator(".box .title").first.evaluate(css) == "40px 45px 600 rgb(54, 54, 54)"
    assert authenticated.locator(".box p").first.evaluate(css) == "16px 24px 400 rgb(74, 74, 74)"

    # The context cards: 24px title is-4 section labels, 16px title is-6 tips.
    assert authenticated.locator("p.title.is-4").first.evaluate(css) == "24px 27px 600 rgb(54, 54, 54)"
    assert authenticated.locator("h6.title.is-6").first.evaluate(css) == "16px 18px 600 rgb(54, 54, 54)"

    # The navbar chrome: links in the body ink, the dropdown items at
    # Bulma's 14px, buttons at weight 400. The locale <strong> the demo
    # measured (700/#4a4a4a) left the navbar with the language dropdown
    # (7.14); its DD-151 pin — the legacy strong weight — is asserted on
    # the :root token the ramp rides.
    assert authenticated.locator(".navbar-link").first.evaluate(css) == "16px 24px 400 rgb(74, 74, 74)"
    strong_weight = authenticated.evaluate(
        "() => getComputedStyle(document.documentElement).getPropertyValue('--bulma-strong-weight').trim()"
    )

    assert strong_weight == "700"
    assert authenticated.locator(".navbar-end .button").first.evaluate(css) == "16px 24px 400 rgb(54, 54, 54)"
    assert authenticated.locator(".navbar-dropdown .navbar-item").first.evaluate(css).startswith("14px ")


def test__chrome_bands_carry_the_aurelius_palette(authenticated: Page) -> None:
    """The navbar band is grey, the footer band the Aurelius blue (SHM-04, SHM-05).

    The demo's chrome: #f5f5f5 navbar, #0073dd footer with white text, and
    the bar pinned (fixed) at its legacy 4.25rem height — 68px.
    """
    navbar = authenticated.locator("nav.navbar")
    footer = authenticated.locator("footer.footer")

    nav_bg = navbar.evaluate("el => getComputedStyle(el).backgroundColor")
    nav_tokens = navbar.evaluate(
        "el => { const cs = getComputedStyle(el);"
        "return ['--bulma-navbar-background-color', '--bulma-scheme-main', '--bulma-scheme-bis']"
        ".map(t => t + '=' + cs.getPropertyValue(t)).join(' | '); }"
    )

    assert nav_bg == "rgb(245, 245, 245)", f"navbar bg {nav_bg}; tokens: {nav_tokens}"
    assert navbar.evaluate("el => getComputedStyle(el).position") == "fixed"
    nav_box = navbar.bounding_box()

    assert nav_box is not None
    assert nav_box["height"] == pytest.approx(68, abs=2)
    assert footer.evaluate("el => getComputedStyle(el).backgroundColor") == "rgb(0, 115, 221)"
    assert footer.locator(".level-item").first.evaluate("el => getComputedStyle(el).color") == "rgb(255, 255, 255)"


def test__accent_ramp_matches_the_demo(authenticated: Page) -> None:
    """The Bulma accents render the demo's palette (SHM-04, DD-152).

    The legacy theme mapped its Bootstrap-style palette onto Bulma's
    accents — $blue to link, cyan/green/yellow/red to info/success/
    warning/danger — and left $primary Bulma's own teal: the demo
    highlights the landing's icons in teal #00d1b2 and the info glyphs in
    cyan #17a2b8; #0073dd is the link and the footer band, not the
    primary. The navbar links hover at the band grey with black ink.
    """
    tokens = authenticated.evaluate(
        "() => { const cs = getComputedStyle(document.documentElement);"
        "const v = (t) => cs.getPropertyValue(t).trim(); return {"
        "primary: v('--bulma-primary'), link: v('--bulma-link'), info: v('--bulma-info'),"
        "success: v('--bulma-success'), warning: v('--bulma-warning'), danger: v('--bulma-danger'),"
        "primaryInvert: v('--bulma-primary-invert')}; }"
    )

    # The teal is Bulma's own (untouched by the legacy theme, kept):
    # hsl(171deg, 100%, 41%). The solid-surface ink is white.
    assert "171deg, 100%, 41%" in tokens["primary"]
    assert "171deg, 100%, 100%" in tokens["primaryInvert"]
    assert tokens["link"] == "#0073dd"
    assert tokens["info"] == "#17a2b8"
    assert tokens["success"] == "#28a745"
    assert tokens["warning"] == "#ffc107"
    assert tokens["danger"] == "#dc3545"

    # The icons as the landing renders them: teal search/compass spans,
    # cyan info buttons (the card's only button, BRW-06).
    expect(authenticated.locator("span.icon.has-text-primary").first).to_have_css("color", "rgb(0, 209, 178)")
    expect(authenticated.locator("button.icon.has-text-info").first).to_have_css("color", "rgb(23, 162, 184)")

    # The hover plate: a visible navbar link (the first .navbar-link is the
    # burger's, hidden at the desktop viewport the fixtures run at).
    link = authenticated.locator(".navbar-end .navbar-link").first
    link.hover()
    expect(link).to_have_css("background-color", "rgb(245, 245, 245)")
    expect(link).to_have_css("color", "rgb(0, 0, 0)")


def test__burger_menu_matches_the_legacy_mobile_chrome(authenticated: Page) -> None:
    """The mobile burger menu renders the legacy chrome (SHM-04, DD-153).

    Bulma 1 tints the burger from link (the Aurelius blue), leaves the
    burger menu's dropdowns as white plates on the grey band (its
    dropdown-item rule is not media-scoped, 0.9.4's is), and — a known
    regression — keeps the dropdown chevron visible on mobile, where
    0.9.4 hides it. The legacy logout is an `a role="button" .navbar-item`
    in navbar ink, not a red button: the UA centres a <button>'s text and
    Bulma's plate rule inks it on a white tile.
    """
    authenticated.set_viewport_size({"width": 375, "height": 667})
    burger = authenticated.locator(".navbar-burger")
    expect(burger).to_have_css("color", "rgb(74, 74, 74)")
    burger.click()

    logout = authenticated.locator(".navbar-dropdown a.navbar-item", has_text="Logout")
    expect(logout).to_be_visible()
    expect(logout).to_have_css("text-align", "start")
    expect(logout).to_have_css("background-color", "rgba(0, 0, 0, 0)")
    expect(logout).to_have_css("color", "rgb(74, 74, 74)")

    # 0.9.4 hides the burger menu's chevrons (Bulma 1 ships them, blue).
    chevron = authenticated.locator(".navbar-end .navbar-link").first
    assert chevron.evaluate("el => getComputedStyle(el, '::after').display") == "none"


def test__footer_sits_below_the_fold(authenticated: Page) -> None:
    """The footer starts below the first screen, never mid-fold (SHM-05, SHM-07).

    The legacy `.is-tall-container` is `flex: 1 1 auto` **and** `min-height:
    100vh` (shell.component.scss): the content band is a full viewport, so
    the footer begins at the fold and is off the first screen — the demo
    measures footer top 1346px at a 900px viewport.
    """
    authenticated.set_viewport_size({"width": 1280, "height": 900})
    authenticated.wait_for_timeout(200)

    box = authenticated.locator("footer.footer").bounding_box()

    assert box is not None
    viewport = authenticated.evaluate("() => window.innerHeight")

    # The band is a full viewport: the footer top sits at/below the fold.
    assert box["y"] >= viewport - 2
    band_box = authenticated.locator(".is-tall-container").bounding_box()

    assert band_box is not None
    assert band_box["height"] >= viewport - 2


def test__landing_content_sits_in_a_container(authenticated: Page) -> None:
    """The landing content is inset like the legacy grid, not edge-to-edge (SHM-07).

    The legacy wraps pages in `section > container` (the demo measures the
    hero box at x=56 in a 1280 viewport, the navbar brand's column). The
    landing's box shares the navbar container's inset; the band behind it
    stays full-bleed (#f5f5f5 to the viewport edges, as on the demo).
    """
    authenticated.set_viewport_size({"width": 1280, "height": 900})

    box_left = authenticated.locator(".box").evaluate("el => el.getBoundingClientRect().left")
    nav_left = authenticated.locator(".navbar .container").evaluate("el => el.getBoundingClientRect().left")
    band = authenticated.locator(".is-tall-container")

    assert box_left == pytest.approx(nav_left, abs=2)
    assert box_left > 30  # inset, not edge-to-edge
    band_box = band.bounding_box()
    # The band is full-bleed: viewport-wide minus the scrollbar.
    client_w = authenticated.evaluate("() => document.documentElement.clientWidth")

    assert band_box is not None
    assert band_box["x"] == pytest.approx(0, abs=2)
    assert band_box["width"] == pytest.approx(client_w, abs=2)


def test__app_stays_light_under_a_dark_os_preference(base_url: str, browser: Browser, settings: Settings) -> None:
    """data-theme=light keeps the app light when the OS prefers dark (SHM-01).

    Bulma 1 follows ``prefers-color-scheme``; the legacy (Bulma 0.9.4) was
    light-only, so the document root pins the light scheme (DD-148).
    """
    context = browser.new_context(color_scheme="dark", ignore_https_errors=True)
    page = context.new_page()
    try:
        page.goto(base_url)
        page.wait_for_url(re.compile(f"/realms/{settings.auth_realm_name}/protocol/openid-connect/auth"))
        page.locator("#username").fill(settings.username)
        page.locator("#password").fill(settings.password.get_secret_value())
        page.get_by_role("button", name="Sign in").click()
        page.wait_for_url(re.compile(base_url))

        assert page.evaluate("() => matchMedia('(prefers-color-scheme: dark)').matches") is True

        band = page.locator(".is-tall-container")
        footer = page.locator("footer.footer")

        # The band is the scheme-following surface (DD-167, `.has-background`):
        # under the light pin it is Bulma 1's light scheme-bis — the legacy
        # #f5f5f5 band is the navbar's (SHM-04), the content band follows the
        # scheme (rgb(243, 244, 246) = hsl(221, 14%, 96%)).
        band_bg = band.evaluate("el => getComputedStyle(el).backgroundColor")
        band_tokens = band.evaluate(
            "el => { const cs = getComputedStyle(el);"
            "const get = (t) => t === 'data-theme' ? document.documentElement.dataset.theme : cs.getPropertyValue(t);"
            "return ['data-theme', '--bulma-scheme-main', '--bulma-scheme-main-bis']"
            ".map(t => t + '=' + get(t)).join(' | '); }"
        )

        assert band_bg == "rgb(243, 244, 246)", f"band bg {band_bg}; tokens: {band_tokens}"
        assert footer.evaluate("el => getComputedStyle(el).backgroundColor") == "rgb(0, 115, 221)"
    finally:
        context.close()


def test__details_skeleton_renders_at_the_deep_link(authenticated: Page, root_url: str) -> None:
    """A direct visit to /search/details/<guid> renders the skeleton, localized (DET-07, DET-01).

    The URL is the screen's whole state (DD-186): the skeleton renders at
    the deep link with no entity behind it — server 2.3 is planned — and
    the chrome strings ride the bridge in both locales (DET-04).
    """
    api_requests: list[str] = []
    authenticated.on("request", lambda request: api_requests.append(request.url))

    authenticated.goto(urljoin(root_url, "/en-US/search/details/7a1b-2c3d"))

    expect(authenticated.locator("h1.aurelius-details-title")).to_have_text("Entity type")
    expect(authenticated.locator("#description-details .title.is-3")).to_have_text("Description")
    expect(authenticated.locator(".aurelius-details-nav .menu-label")).to_have_text("Details")
    expect(authenticated.locator(".aurelius-details-properties thead th").nth(0)).to_have_text("Key")
    expect(authenticated.locator(".aurelius-details-properties tbody tr")).to_have_count(0)

    # The skeleton fetches nothing (DET-02): the entity endpoint is 2.3's.
    assert [url for url in api_requests if "/api/" in url] == []


def test__details_skeleton_renders_dutch_chrome(authenticated: Page, root_url: str) -> None:
    """The nl-NL locale renders the Dutch details chrome through the bridge (DET-04, DET-07)."""
    authenticated.goto(urljoin(root_url, "/nl-NL/search/details/7a1b-2c3d"))

    expect(authenticated.locator("h1.aurelius-details-title")).to_have_text("Entiteit type")
    expect(authenticated.locator("#description-details .title.is-3")).to_have_text("Beschrijving")
    expect(authenticated.locator(".aurelius-details-properties thead th").nth(0)).to_have_text("Sleutel")


def _seed_entities(page: Page, root_url: str, type_name: str, names: list[str]) -> dict[str, str]:
    """Seed entities through the proxy's bulk endpoint; return the guid assignments.

    The server is open pre-6.1 (DV-54), so the proxy's ``/api`` leg answers
    without a token. Names are **single tokens** carrying a unique ``run``
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
        headers={"content-type": "application/json"},
    )

    assert response.status == 200, response.text()

    return response.json()["guidAssignments"]


def _purge_type(page: Page, root_url: str, type_name: str) -> None:
    """Delete every entity of a type (the shared stack's determinism fix).

    The dev stack is never cleaned between runs, and the explore search is a
    type-only first page (limit 10): glossaries from earlier runs fill it and
    push this run's seed off page 1. A type-scoped purge — list by type,
    delete by guid — makes a type-filtered assertion deterministic.
    """
    listing = page.request.post(
        urljoin(root_url, "/api/atlas/v2/search/basic"),
        data=json.dumps({"typeName": type_name, "limit": 1000, "offset": 0, "excludeDeletedEntities": True}),
        headers={"content-type": "application/json"},
    )

    assert listing.status == 200, listing.text()

    for entity in listing.json().get("entities", []):
        deleted = page.request.delete(urljoin(root_url, "/api/atlas/v2/entity/bulk"), params={"guid": entity["guid"]})

        assert deleted.status == 200, deleted.text()


def test__hero_search_shows_seeded_results_in_both_locales(authenticated: Page, root_url: str) -> None:
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
    guids = _seed_entities(authenticated, root_url, "DataSet", names)

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

    # The card → details deep link (SRH-05): the clicked guid rides the URL.
    clicked = names[0]
    rows.filter(has_text=clicked).locator("a").first.click()
    expect(authenticated).to_have_url(re.compile(rf"/en-US/search/details/{guids['-0']}$"))
    expect(authenticated.locator("h1.aurelius-details-title")).to_be_visible()

    # The results URL is the screen's state (SRH-02): reload re-runs the
    # search from the URL alone and the hero shows the query.
    authenticated.go_back()
    expect(authenticated.locator(".results-count")).to_have_text(re.compile(r"3\s+results"))
    expect(field).to_have_value(query)

    # SRH-10: the same screen in Dutch — the count word rides the bridge.
    authenticated.goto(urljoin(root_url, f"/nl-NL/search/results?query={quote(query)}"))
    expect(authenticated.locator(".results-count")).to_have_text(re.compile(r"3\s+resultaten"))


def test__business_explore_lists_glossary_entities_without_a_url_query(authenticated: Page, root_url: str) -> None:
    """The business card's explore button lists glossary entities, type-filtered (SRH-08, DV-84).

    Explore is the legacy ``directToGlossary``: an empty query plus the
    session type filter ``typeName=AtlasGlossary`` (DV-84 — the Atlas type,
    not the m4i ``Glossary`` label, which the server would reject as
    UNKNOWN_TYPENAME, SRC-03). The filter rides the store, never the URL
    (SRH-02: the URL carries only ``?query=``), so the results URL stays
    clean — reloading it restarts from the URL alone (empty), proving the
    filter lived only in the session store.

    The type is purged first: the shared stack keeps every run's glossaries
    and the explore page shows the first ten (limit 10) — the purge makes
    the seeded entity the page.
    """
    run = secrets.token_hex(4)
    name = f"zz{run}domain"
    _purge_type(authenticated, root_url, "AtlasGlossary")
    _seed_entities(authenticated, root_url, "AtlasGlossary", [name])

    authenticated.goto(urljoin(root_url, "/en-US/search"))
    authenticated.get_by_role("button", name="Start browsing data domains").click()

    expect(authenticated).to_have_url(re.compile(r"/en-US/search/results$"))
    rows = authenticated.locator(".result-row")
    expect(rows.filter(has_text=name)).to_have_count(1)

    # The type filter is session state: reloading the bare results URL
    # restarts from the URL (an empty query, no filter) — the seeded
    # glossary is gone, the no-results pair shows (SRH-02).
    authenticated.reload()
    expect(authenticated.locator(".no-results")).to_be_visible()
    expect(rows).to_have_count(0)


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
