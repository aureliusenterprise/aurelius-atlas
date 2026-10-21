import re
import socket
import ssl
from urllib.parse import urljoin, urlsplit

import pytest
from conftest import CA_FILE, Settings
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
    # (Angular raw, DD-060) — accept both.
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


def test__navbar_greets_the_signed_in_user(authenticated: Page) -> None:
    """The account dropdown's welcome line shows the Keycloak identity (SHC-05, SHC-09).

    ``preferred_username`` from the token, greeted through the
    shell.header.welcome bridge leaf.
    """
    welcome = authenticated.locator("a.navbar-link").filter(has_text="Logged in as")

    expect(welcome).to_be_visible()
    expect(welcome).to_have_text("Logged in as aurelius-writer")


def test__language_dropdown_navigates_to_the_dutch_build(authenticated: Page) -> None:
    """Choosing nl-NL in the language dropdown lands on the Dutch bundle (SHC-04, SHC-09).

    A real click on the dropdown item, not a hand-written URL: the href the
    header computes (locale prefix swap) and the nginx locale tree are
    exercised together.
    """
    dropdown = authenticated.locator(".navbar-item.has-dropdown").filter(has_text="Your language is")
    dropdown.hover()
    dropdown.locator('a[hreflang="nl-NL"]').click()

    authenticated.wait_for_url(re.compile(r"/nl-NL/search/browse$"))
    expect(authenticated.locator("#browse-placeholder")).to_have_text(NL_PLACEHOLDER)


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
    """Every ink and weight the landing renders, measured against the demo (SHM-03, DD-062).

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

    # The navbar chrome: links in the body ink, the locale <strong> bold in
    # the same ink, dropdown items at Bulma's 14px, buttons at weight 400.
    assert authenticated.locator(".navbar-link").first.evaluate(css) == "16px 24px 400 rgb(74, 74, 74)"
    strong = authenticated.locator(".navbar strong").first

    assert strong.evaluate("el => getComputedStyle(el).fontWeight") == "700"
    assert strong.evaluate("el => getComputedStyle(el).color") == "rgb(74, 74, 74)"
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
    """The Bulma accents render the demo's palette (SHM-04, DD-063).

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
    light-only, so the document root pins the light scheme (DD-059).
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

        band_bg = band.evaluate("el => getComputedStyle(el).backgroundColor")
        band_tokens = band.evaluate(
            "el => { const cs = getComputedStyle(el);"
            "return ['--bulma-light-h', '--bulma-light-s', '--bulma-light-l', '--bulma-scheme-main']"
            ".map(t => t + '=' + cs.getPropertyValue(t)).join(' | '); }"
        )

        assert band_bg == "rgb(245, 245, 245)", f"band bg {band_bg}; tokens: {band_tokens}"
        assert footer.evaluate("el => getComputedStyle(el).backgroundColor") == "rgb(0, 115, 221)"
    finally:
        context.close()
