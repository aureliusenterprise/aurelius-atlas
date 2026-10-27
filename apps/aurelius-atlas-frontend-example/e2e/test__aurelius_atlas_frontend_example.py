import re
from collections.abc import Generator
from urllib.parse import urljoin

import pytest
from aurelius_atlas_example import Entity
from playwright.sync_api import Page, expect
from sqlmodel import Session, select


@pytest.mark.parametrize(
    ("accept_language", "locale"),
    [("", "en-US"), ("en-US,en;q=0.9", "en-US"), ("nl-NL,nl;q=0.9,en;q=0.8", "nl-NL"), ("fr", "en-US")],
)
def test__root_redirects_to_preferred_locale(page: Page, base_url: str, accept_language: str, locale: str) -> None:
    """The image redirects the root to the supported preferred locale."""
    response = page.request.get(
        urljoin(base_url, "/?redirect-check=1"), headers={"Accept-Language": accept_language}, max_redirects=0
    )

    assert response.status == 302
    assert response.headers["location"].endswith(f"/{locale}/?redirect-check=1")


@pytest.mark.parametrize("locale", ["en-US", "nl-NL"])
def test__locale_routes_fall_back_to_localized_app(page: Page, base_url: str, locale: str) -> None:
    """Client-side routes serve the index belonging to their locale."""
    response = page.request.get(urljoin(base_url, f"/{locale}/route-not-found"))

    assert response.status == 200
    assert "text/html" in response.headers["content-type"]
    assert f'<base href="/{locale}/">' in response.text()
    assert f'lang="{locale}"' in response.text()


def test__otel_proxy_forwards_to_the_collector(page: Page, base_url: str, user_token: str) -> None:
    """The nginx /otel/ proxy forwards to the collector with the prefix stripped.

    An OTLP/HTTP POST to the collector answers at /v1/traces with a
    protobuf-level status; if the proxy did not forward, nginx would answer
    502 (unresolvable upstream) or 404 (no location). The collector's browser
    leg demands the signed-in user's token (DD-193, CIA-02) and the proxy
    passes the Authorization header through untouched — reaching the
    collector (any of those statuses, never 401) proves the passthrough.
    """
    response = page.request.post(
        urljoin(base_url, "/otel/v1/traces"),
        data=b"",
        headers={"content-type": "application/x-protobuf", "authorization": f"Bearer {user_token}"},
    )

    assert response.status in (200, 202, 400, 415)


def test__otel_proxy_passes_authorization_through(page: Page, base_url: str) -> None:
    """The /otel/ proxy injects nothing: a token-less push is the collector's 401 (CIA-01, CIA-02).

    The browser leg authenticates the user (DD-193), so a push without a
    bearer rides the proxy all the way to the OIDC receiver and comes back
    401 — the proxy is a pipe, not a credential. (The signed-in SPA attaches
    the user token itself, app.config.ts.)
    """
    response = page.request.post(
        urljoin(base_url, "/otel/v1/traces"),
        data=b"",
        headers={"content-type": "application/x-protobuf"},
    )

    assert response.status == 401


def test__search_input_is_present(authenticated: Page) -> None:
    """
    Test that the search input is present on the page.

    Asserts:
        - The search input field is visible.
        - The search input field has the correct placeholder text.
    """
    search_input = authenticated.locator("#search-input")

    expect(search_input).to_be_visible()
    expect(search_input).to_have_attribute("placeholder", "Search for an entity")


def test__deferred_stylesheet_media_flipped_by_csp_allowed_script(authenticated: Page) -> None:
    """
    Test that the deferred stylesheet becomes active despite the strict CSP.

    @angular/build ships the full stylesheet as ``<link media="print">`` and
    flips it to its real media via a fixed inline script (beasties). The CSP
    allows that script by hash only; if the hash drifts from the build,
    browsers silently block the script and the link stays ``media="print"``
    — the inlined critical CSS hides that from the eye, so assert it here.

    Asserts:
        - The deferred ``styles-*.css`` link exists in the served document.
        - Its effective media is no longer ``print`` (flip script executed).
    """
    deferred = authenticated.locator('link[rel="stylesheet"][href^="styles-"]')

    expect(deferred).to_have_count(1)
    expect(deferred).not_to_have_attribute("media", "print")


def test__search_results_with_no_data(authenticated: Page) -> None:
    """
    Test that the search results section is visible when no data is present.

    Asserts:
        - The search results section is visible.
        - The message indicating no entities found is displayed.
    """
    expect(authenticated.get_by_text(re.compile(r"I have found 0 entities\."))).to_be_visible()
    expect(authenticated.locator(".search-result-card")).to_have_count(0)


@pytest.fixture
def entities(session: Session) -> Generator[list[Entity]]:
    """Fixture to create sample entities in the database."""
    entities = [
        Entity(name="Entity 1", description="Description 1"),
        Entity(name="Entity 2", description="Description 2"),
        Entity(name="Entity 3", description="Description 3"),
    ]

    session.add_all(entities)
    session.commit()

    yield entities

    for entity in entities:
        session.delete(entity)

    session.commit()


def test__search_results_with_data(authenticated: Page, entities: list[Entity]) -> None:
    """
    Test that the search results section displays entities when data is present.

    Asserts:
        - The search results section is visible.
        - The correct number of entities is displayed.
        - A search result card is visible for each entity.
    """
    expect(authenticated.get_by_text(re.compile(rf"I have found {len(entities)} entities\."))).to_be_visible()
    expect(authenticated.locator(".search-result-card")).to_have_count(len(entities))

    for entity in entities:
        expect(authenticated.locator(f".search-result-card[data-guid='{entity.guid}']")).to_be_visible()


def test__search_result_with_data_and_query(authenticated: Page, entities: list[Entity]) -> None:
    """
    Test that the search results section filters entities based on the search query.

    Asserts:
        - The search input field is visible.
        - The search input field accepts text input.
        - The search results update based on the query.
    """
    search_input = authenticated.locator("#search-input")

    entity = entities[0]

    if not entity.name:
        message = "Entity name is empty, cannot perform search."
        raise ValueError(message)

    search_input.fill(entity.name)

    expect(authenticated.get_by_text(re.compile(r"I have found 1 entity\."))).to_be_visible()
    expect(authenticated.locator(".search-result-card")).to_have_count(1)
    expect(authenticated.locator(f".search-result-card[data-guid='{entity.guid}']")).to_be_visible()


def test__edit_entity_via_ui(authenticated: Page, entities: list[Entity]) -> None:
    """
    Test that an entity can be edited via the UI.

    Asserts:
        - The edit button for the first entity is visible.
        - Clicking the edit button opens the editor.
        - The editor form is pre-filled with the entity's data.
        - The form can be filled out and submitted.
        - The editor is closed after saving changes.
        - The updated entity appears in the search results.
    """
    entity = entities[0]

    if not (entity.name and entity.description):
        message = "Entity name or description is empty, cannot check the form."
        raise ValueError(message)

    search_result = authenticated.locator(f".search-result-card[data-guid='{entity.guid}']")

    expect(search_result).to_be_visible()

    edit_button = search_result.locator(f"#edit-entity-{entity.guid}")

    expect(edit_button).to_be_visible()

    edit_button.click()

    editor = authenticated.get_by_text("Editor")

    expect(editor).to_be_visible()

    guid_input = authenticated.get_by_label("GUID")

    expect(guid_input).to_be_visible()
    expect(guid_input).to_have_value(str(entity.guid))
    expect(guid_input).to_have_attribute("readonly", "")

    name_input = authenticated.get_by_label("Name")

    expect(name_input).to_be_visible()
    expect(name_input).to_have_value(entity.name)

    description_input = authenticated.get_by_label("Description")

    expect(description_input).to_be_visible()
    expect(description_input).to_have_value(entity.description)

    new_name = "Updated Entity Name"
    new_description = "Updated Description"

    name_input.fill(new_name)
    description_input.fill(new_description)

    authenticated.get_by_role("button", name="Save").click()

    expect(editor).not_to_be_visible()

    expect(
        authenticated.locator(f".search-result-card[data-guid='{entity.guid}']", has_text=new_name),
    ).to_be_visible()

    expect(
        authenticated.locator(f".search-result-card[data-guid='{entity.guid}']", has_text=new_description),
    ).to_be_visible()


def test__delete_entity_via_ui(authenticated: Page, entities: list[Entity]) -> None:
    """
    Test that an entity can be deleted via the UI.

    Asserts:
        - The delete button is visible in the editor.
        - The editor is closed after deletion.
        - The search results are updated after deletion.
    """
    entity = entities[0]

    search_result = authenticated.locator(f".search-result-card[data-guid='{entity.guid}']")

    expect(search_result).to_be_visible()

    edit_button = search_result.locator(f"#edit-entity-{entity.guid}")

    expect(edit_button).to_be_visible()

    edit_button.click()

    editor = authenticated.get_by_text("Editor")

    expect(editor).to_be_visible()

    delete_button = authenticated.get_by_role("button", name="Delete")

    expect(delete_button).to_be_visible()

    delete_button.click()

    expect(editor).not_to_be_visible()
    expect(search_result).not_to_be_visible()


@pytest.fixture
def new_entity(session: Session) -> Generator[Entity]:
    """Fixture to create a new entity for testing."""
    entity = Entity(name="New Entity", description="This is a new entity.")

    yield entity

    query = select(Entity).where(Entity.name == entity.name).where(Entity.description == entity.description)
    results = session.exec(query).all()

    for result in results:
        session.delete(result)

    session.commit()


def test__create_entity_via_ui(authenticated: Page, new_entity: Entity) -> None:
    """
    Test that a new entity can be created via the UI.

    Asserts:
        - The editor is opened when the create button is clicked.
        - The form can be filled out and submitted.
        - The editor is closed after submission.
        - The new entity appears in the search results.
    """
    expect(authenticated.locator(".search-result-card", has_text=new_entity.name)).not_to_be_visible()
    expect(authenticated.locator(".search-result-card", has_text=new_entity.description)).not_to_be_visible()

    authenticated.locator("#create-entity").click()

    editor = authenticated.get_by_text("Editor")

    expect(editor).to_be_visible()

    guid_input = authenticated.get_by_label("GUID")
    expect(guid_input).to_be_visible()
    expect(guid_input).to_have_attribute("readonly", "")
    expect(guid_input).to_have_attribute("placeholder", "New Entity")

    if not (new_entity.name and new_entity.description):
        message = "New entity name or description is empty, cannot fill the form."
        raise ValueError(message)

    name_input = authenticated.get_by_label("Name")
    expect(name_input).to_be_visible()
    expect(name_input).to_have_value("")

    description_input = authenticated.get_by_label("Description")
    expect(description_input).to_be_visible()
    expect(description_input).to_have_value("")

    name_input.fill(new_entity.name)
    description_input.fill(new_entity.description)

    authenticated.get_by_role("button", name="Save").click()

    expect(editor).not_to_be_visible()
    expect(authenticated.locator(".search-result-card", has_text=new_entity.name)).to_be_visible()
    expect(authenticated.locator(".search-result-card", has_text=new_entity.description)).to_be_visible()
