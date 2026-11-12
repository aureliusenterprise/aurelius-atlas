"""E2E: the 7.22a lineage-model data path — the browser's origin to the aux chain.

The webapp's nginx serves the aux API at ``/lineage-model/`` (LDG-06); the
stack carries both aux containers pointed at this stack's real Atlas server
(LDG-08). The scenarios ride the served origin: the aux API's own answers
arrive through nginx (the proxy adds no auth of its own — an anonymous
request reaches the aux 401, LM-08) and the full LM-04 chain runs over real
services: browser token -> aux -> Atlas lineage -> data2model -> ar3 model.
"""

import json
import re
import secrets
from urllib.parse import urljoin

import pytest
from playwright.sync_api import Locator, Page, expect
from test__aurelius_atlas_webapp import _active_edge, _purge_type, _seed_m4i_mini_graph, _wait_entity_read

LINEAGE_PATH = "/lineage-model/"

# The DET-34 seed's types: the shared dev store is never cleaned between
# runs, so the m4i purge list the DET tests share applies here too (DD-223).
_M4I_TYPES = [
    "m4i_generic_process",
    "m4i_system",
    "m4i_data_attribute",
    "m4i_data_entity",
    "m4i_data_domain",
    "m4i_field",
    "m4i_dataset",
    "m4i_person",
]


# impact=major, likelihood=high (a young screen with churn on its path)
@pytest.mark.high
def test__lineage_model_anonymous_request_reaches_the_aux_401(page: Page, root_url: str) -> None:
    """The proxy adds no auth: an anonymous call gets the aux API's own 401 (LDG-06, LM-08).

    Through the served origin (nginx -> TLS -> aux): the route is gated by the
    app's verifier and nginx is a pipe, not a credential — the same posture
    the /otel/ proxy test proves for the collector.
    """
    response = page.request.get(
        urljoin(root_url, LINEAGE_PATH),
        params={"guid": secrets.token_hex(16), "depth": 3, "direction": "BOTH"},
    )

    assert response.status == 401


# impact=major, likelihood=high (a young screen with churn on its path)
@pytest.mark.high
def test__lineage_model_unknown_guid_answers_no_content(authenticated: Page, root_url: str, user_token: str) -> None:
    """The empty lineage is the aux 204, forwarded through the proxy (LDG-06, LM-05/LM-06).

    A guid the server has never seen answers its lineage 404 (LIN-05), which
    the aux app maps to the 204 (LM-05) — the browser client reads it as
    ``null`` (LDG-03, unit-tested in the data-access lib); through the proxy
    the status must arrive unchanged. The user token rides the request (the
    SPA's interceptor shape, LDG-05): the verifier accepts the browser client
    through the DD-385 audience join, so the answer is the aux's 204, not 401.
    """
    response = authenticated.request.get(
        urljoin(root_url, LINEAGE_PATH),
        params={"guid": secrets.token_hex(16), "depth": 3, "direction": "BOTH"},
        headers={"authorization": f"Bearer {user_token}"},
    )

    assert response.status == 204
    assert not response.text()


# impact=major, likelihood=high (a young screen with churn on its path)
@pytest.mark.high
@pytest.mark.covers(rules=["LDG-06"])
def test__lineage_model_answers_the_seeded_chain(authenticated: Page, root_url: str, user_token: str) -> None:
    """The seeded m4i graph comes back as an ar3 model through the whole chain (LDG-06, LM-04).

    The DET-34 mini-graph seeded through the /api/ proxy, then read through
    the /lineage-model/ proxy: the aux app walks the real server's lineage,
    flattens it, and extracts through the real data2model — all on the
    caller's own token, forwarded unchanged (LM-04). The answer carries the
    ``model`` as a JSON string parsing to an ``ar3_model`` document plus its
    ``{id, data}`` metadata rows (LM-04, DV-68's passthrough). The browser
    token passes the aux verifier only through the DD-385 join (aud
    ``aurelius`` beside the app's own), and rides on to data2model (audience
    ``aurelius``, AUX-04) and the server (AUT-02) — one token, three
    verifiers. Self-cleaned by the shared m4i purge (DD-223).
    """
    run = secrets.token_hex(4)
    guids = _seed_m4i_mini_graph(authenticated, root_url, user_token, run)

    try:
        # The lineage walks the edge records (separate near-real-time
        # documents, CLS-12's race): wait the dataset's lineage ends visible
        # before the aux chain reads them.
        _wait_entity_read(
            authenticated,
            root_url,
            user_token,
            guids["dataset"],
            predicate=lambda entity: (
                _active_edge(entity, "outputFromProcesses", guids["process"])
                and _active_edge(entity, "inputToProcesses", guids["process"])
            ),
        )

        response = authenticated.request.get(
            urljoin(root_url, LINEAGE_PATH),
            params={"guid": guids["dataset"], "depth": 3, "direction": "BOTH"},
            headers={"authorization": f"Bearer {user_token}"},
        )

        assert response.status == 200, response.text()
        body = response.json()

        # LM-04/DV-68: the model stays a JSON string, not a parsed object.
        assert isinstance(body["model"], str)
        ar3 = json.loads(body["model"])
        assert "ar3_model" in ar3

        rows = body["metadata"]
        assert rows, "the seeded graph must yield metadata rows"
        assert all({"id", "data"} <= set(row) for row in rows)
        # The seeded dataset names itself among the model's elements: the
        # flatten carries the display text (LM-02) and the extractor writes it
        # as the element's ar3_name (DTM-02) — the metadata rows carry the
        # guid and the type mapping, not the name (DTM-03).
        elements = ar3["ar3_model"]["ar3_elements"]["ar3_element"]
        names = {name["value"] for element in elements for name in element.get("ar3_name", [])}
        assert f"zz{run}warehouse" in names
    finally:
        for type_name in _M4I_TYPES:
            _purge_type(authenticated, root_url, user_token, type_name)


def _selection_reads_the_chain_metadata(
    authenticated: Page, root_url: str, user_token: str, drawer: Locator, *, run: str, dataset_guid: str
) -> None:
    """LDG-21 over the live chain: the Selection tab's Name, Type, and merged Properties.

    The expected value is the chain's own answer (DTM-03): the clicked
    element's id and its row's m4i_original_id, read from the same aux call
    the page made — the merge's row-wins half, over live data rather than the
    fixture.
    """
    selection = drawer.locator("aurelius-atlas-webapp-lineage-selection")
    expect(selection.locator(".field", has=authenticated.locator(".label", has_text="Name"))).to_contain_text(
        f"zz{run}pipeline"
    )
    expect(selection.locator(".field", has=authenticated.locator(".label", has_text="Type"))).to_contain_text("Process")
    chain = authenticated.request.get(
        urljoin(root_url, LINEAGE_PATH),
        params={"guid": dataset_guid, "depth": 3, "direction": "BOTH"},
        headers={"authorization": f"Bearer {user_token}"},
    )
    assert chain.status == 200
    ar3 = json.loads(chain.json()["model"])
    rows = chain.json()["metadata"]
    process_id = next(
        element["@identifier"]
        for element in ar3["ar3_model"]["ar3_elements"]["ar3_element"]
        if any(name["value"] == f"zz{run}pipeline" for name in element.get("ar3_name", []))
    )
    original_id = next(row["data"]["m4i_original_id"] for row in rows if row["id"] == process_id)
    properties = selection.locator(".field", has=authenticated.locator(".label", has_text="Properties"))
    expect(properties).to_contain_text("Model Extractor API")
    expect(properties).to_contain_text(original_id)


def _browse_tab_lists_the_view_and_tree(drawer: Locator, box: Locator, run: str) -> None:
    """LDG-23/DD-406: the Browse tab's dropdown lists the drawn view over the tree's folders.

    Opened through a node (the reader's path): the dropdown holds the chain's
    one view, named "Lineage" by the server's rule, and the tree under it
    shows the producer's three folders holding the concepts as leaves.
    """
    box.locator("g.node", has_text=f"zz{run}warehouse").click()
    expect(drawer).to_be_visible()
    drawer.locator(".aurelius-model-browser-tab", has_text="Browse").click()
    browse = drawer.locator("aurelius-atlas-webapp-lineage-browse-tab")
    expect(browse.locator("select")).to_be_visible()
    options = browse.locator("select option")
    # The placeholder option plus the chain's one view.
    expect(options).to_have_count(2)
    expect(options.nth(1)).to_have_text("Lineage")
    tree = browse.locator(".aurelius-browse-tree")
    expect(tree).to_be_visible()
    expect(browse.locator(".aurelius-browse-tree-folder")).to_have_text(["Other", "Relations", "Views"])
    expect(tree.locator(".aurelius-browse-tree-leaf", has_text=f"zz{run}warehouse")).to_be_visible()


def _edge_click_selects_the_relation(drawer: Locator, box: Locator) -> None:
    """LDG-17/DD-409: an edge click — anywhere along the wide hit path — selects the relation.

    The Selection tab reads the relation's type and carries no search card
    (a relation has no details page, DD-405's condition). The click goes on
    the wide hit path itself: the edge's visible stroke is 1 px and its
    bounding box is a zero-height line (a straight horizontal edge here), so
    a pointer aimed at the box races the slide animation and the redraw.
    The Selection tab reads the relation's type and carries no search card
    (a relation has no details page, DD-405's condition). The hit path's
    bounding box is a zero-height line (the edge is straight horizontal
    here), so Playwright's visibility gate misjudges it and the click goes
    force: true — the mouse event is real and lands on the path, riding the
    group's handler. The close that precedes this helper must be fully
    committed first: the drawer's layer stays mounted through its slide-out
    and its scrim covers the viewport, so the guard waits for the exit
    animation to end — the layer is gone — before the click.
    """
    expect(drawer).to_have_count(0)
    box.locator(".connection-hit").first.click(force=True)
    expect(drawer).to_be_visible()
    expect(drawer.locator(".aurelius-model-browser-tab.is-active")).to_have_text("Selection")
    edge_selection = drawer.locator("aurelius-atlas-webapp-lineage-selection")
    # The Type value element is unique to the Selection tab (LDG-20); its
    # text is the relation's human-readable type from the metamodel table.
    expect(edge_selection.locator(".aurelius-selection-type")).to_contain_text("Data Lineage")
    expect(edge_selection.locator("aurelius-atlas-ui-entity-card")).to_have_count(0)
    drawer.locator(".aurelius-drawer-panel button.delete").click()
    expect(drawer).not_to_be_visible()


# impact=major, likelihood=high (a young screen with churn on its path)
@pytest.mark.high
@pytest.mark.covers(rules=["LDG-17", "LDG-19", "LDG-21", "LDG-23", "LDG-25"])
def test__the_quickview_panel_opens_on_a_node_click(authenticated: Page, root_url: str, user_token: str) -> None:
    """The 7.22c quickview panel: a node click opens it, live metadata lands in Properties (LDG-19/LDG-21/LDG-25).

    The DET-34 mini-graph again: clicking the process node opens the drawer
    on the Selection tab, whose Name and Type read the element and whose
    Properties table carries the chain's own metadata rows (created_by and
    the seed's guid as m4i_original_id — the LDG-21 merge over live rows,
    DV-68's passthrough). The selected element gains the search card (DD-405)
    and its title opens the entity's own details page. The drawer's close
    hides the panel AND deselects the diagram (LDG-25, DD-403 — no box stays
    painted without its panel). On the Browse tab the dropdown lists the
    drawn view ("Lineage", the server's rule, LDG-23) over the organization
    tree's folders (DD-406). An edge click — the wide hit path, DD-409 —
    selects the relation (LDG-17). Interactions only — the tab strip's pixels
    and the table's sort are the unit specs' (the e2e rule). Self-cleaned by
    the shared m4i purge (DD-223).
    """
    run = secrets.token_hex(4)
    guids = _seed_m4i_mini_graph(authenticated, root_url, user_token, run)
    dataset_guid = guids["dataset"]

    try:
        # The lineage walks the edge records (CLS-12's race): wait the
        # dataset's lineage ends visible before the screen reads them.
        _wait_entity_read(
            authenticated,
            root_url,
            user_token,
            dataset_guid,
            predicate=lambda entity: (
                _active_edge(entity, "outputFromProcesses", guids["process"])
                and _active_edge(entity, "inputToProcesses", guids["process"])
            ),
        )

        authenticated.goto(urljoin(root_url, f"/en-US/search/details/{dataset_guid}"))
        expect(authenticated.locator("h1.aurelius-details-title")).to_have_text(f"zz{run}warehouse")
        box = authenticated.locator("#lineage-model")

        # LDG-25: the process node's click opens the drawer on the Selection
        # tab (the layer mounts, DD-162's open state).
        process_node = box.locator("g.node", has_text=f"zz{run}pipeline")
        process_node.click()
        drawer = authenticated.locator(".aurelius-drawer")
        expect(drawer).to_be_visible()
        active_tab = drawer.locator(".aurelius-model-browser-tab.is-active")
        expect(active_tab).to_have_text("Selection")

        # LDG-19/DD-410: the four-tab strip in the legacy's order —
        # Browse, Model, View, Selection (the keyvalue order over the
        # legacy's tabs object). The panel is "Details" (the quickview's
        # default header) and its footer holds the Close button.
        tabs = drawer.locator(".aurelius-model-browser-tab")
        expect(tabs).to_have_count(4)
        expect(tabs.nth(0)).to_have_text("Browse")
        expect(tabs.nth(1)).to_have_text("Model")
        expect(tabs.nth(2)).to_have_text("View")
        expect(tabs.nth(3)).to_have_text("Selection")
        expect(drawer.locator(".aurelius-drawer-title")).to_have_text("Details")
        expect(drawer.locator("button[drawer-footer]")).to_have_text("Close")

        # LDG-21 over the live chain: Name, Type, and the merged Properties
        # read the chain's own answer (the helper).
        _selection_reads_the_chain_metadata(
            authenticated, root_url, user_token, drawer, run=run, dataset_guid=dataset_guid
        )

        # DD-405: the selected element gains the search card — the results
        # screen's shape, name and badge included; its title is the anchor to
        # the entity's own details page (checked after the drawer steps).
        selection = drawer.locator("aurelius-atlas-webapp-lineage-selection")
        card = selection.locator("aurelius-atlas-ui-entity-card")
        expect(card).to_be_visible()
        expect(card.locator(".title.is-4")).to_contain_text(f"zz{run}pipeline")
        expect(card.locator(".icon-text")).to_contain_text("Process")

        # LDG-25/DD-403: the drawer's close hides the panel and clears the
        # selection — the painted box never outlives its panel.
        drawer.locator(".aurelius-drawer-panel button.delete").click()
        expect(drawer).not_to_be_visible()
        expect(box.locator("g.node.is-selected")).to_have_count(0)

        # LDG-23/DD-406: reopened through a node, the Browse tab lists the
        # drawn view in its dropdown over the organization tree's folders.
        _browse_tab_lists_the_view_and_tree(drawer, box, run)
        drawer.locator(".aurelius-drawer-panel button.delete").click()
        expect(drawer).not_to_be_visible()

        # LDG-17/DD-409: an edge click through the wide hit path selects the
        # relation, not a node (the helper).
        _edge_click_selects_the_relation(drawer, box)

        # DD-405: the card's title click routes to the entity's details
        # page — the element, not the dataset the reader arrived on.
        box.locator("g.node", has_text=f"zz{run}pipeline").click()
        expect(drawer).to_be_visible()
        drawer.locator("aurelius-atlas-ui-entity-card .title.is-4 a").click()
        expect(authenticated.locator("h1.aurelius-details-title")).to_have_text(f"zz{run}pipeline")
    finally:
        for type_name in _M4I_TYPES:
            _purge_type(authenticated, root_url, user_token, type_name)


# impact=major, likelihood=high (a young screen with churn on its path)
@pytest.mark.high
@pytest.mark.covers(rules=["LDG-09", "LDG-10", "LDG-17", "LDG-18"])
def test__the_details_page_draws_the_lineage_box(authenticated: Page, root_url: str, user_token: str) -> None:
    """The Lineage Model box draws the seeded chain on the details page (LDG-09/LDG-10/LDG-17/LDG-18).

    The 7.22b screen over the DET-34 mini-graph and the real aux chain: the
    box sits between Child Datasets and Producers on the dataset page (the
    legacy position, LDG-09), its header carries the drawn view's name —
    "Lineage", the server's rule — and the diagram holds the seeded process
    and dataset by their names (LDG-10's diagram state, over the whole
    chain). Clicking a node selects it (LDG-17, the ``.is-selected``
    stroke); the page's own entity rides the highlight (LDG-18,
    ``.is-highlighted`` on the dataset node the page opened). The unlinked
    process answers the aux 204 and the box rests at the empty message
    (LDG-10). Interactions only — the pixels are the unit specs' (the e2e
    rule). Self-cleaned by the shared m4i purge (DD-223).
    """
    run = secrets.token_hex(4)
    guids = _seed_m4i_mini_graph(authenticated, root_url, user_token, run)
    dataset_guid = guids["dataset"]
    lonely_guid = guids["lonely"]

    try:
        # The lineage walks the edge records (CLS-12's race): wait the
        # dataset's lineage ends visible before the screen reads them.
        _wait_entity_read(
            authenticated,
            root_url,
            user_token,
            dataset_guid,
            predicate=lambda entity: (
                _active_edge(entity, "outputFromProcesses", guids["process"])
                and _active_edge(entity, "inputToProcesses", guids["process"])
            ),
        )

        authenticated.goto(urljoin(root_url, f"/en-US/search/details/{dataset_guid}"))
        expect(authenticated.locator("h1.aurelius-details-title")).to_have_text(f"zz{run}warehouse")

        # LDG-09: the box, in the legacy position between Child Datasets and
        # Producers (the section order is the unit spec's; the anchor living
        # between the two boxes is the position the page must keep).
        box = authenticated.locator("#lineage-model")
        expect(box).to_be_visible()
        box_ids = authenticated.locator("section[id], div.box[id]").evaluate_all("(els) => els.map((el) => el.id)")
        assert box_ids.index("lineage-model") == box_ids.index("related-datasets") + 1
        assert box_ids.index("related-producers") == box_ids.index("lineage-model") + 1

        # LDG-10's diagram state through the chain, LDG-09's header: the
        # drawn view's name (the server's rule names it "Lineage").
        expect(box.locator(".aurelius-lineage-title")).to_have_text("Lineage")
        nodes = box.locator("g.node")
        # The walk's own count is the chain's (both lineage ends ride it);
        # the screen's promise is the seeded ends drawn, each once.
        expect(nodes.filter(has_text=f"zz{run}pipeline")).to_have_count(1)
        expect(nodes.filter(has_text=f"zz{run}warehouse")).to_have_count(1)

        # LDG-14 through the chain: the connections and the arrow marker are
        # drawn (the walk's own count is the chain's; the path geometry and
        # the marker's pixels are the viewer's unit spec — a horizontal
        # line has no box to be "visible" in, per the e2e rule).
        expect(box.locator("g.connection")).not_to_have_count(0)
        expect(box.locator("defs marker#generic-arrow")).to_have_count(1)

        # LDG-18: the page's own entity carries the highlight stroke — the
        # dataset node, on the dataset's page (not the process node).
        highlighted = box.locator("g.node.is-highlighted")
        expect(highlighted).to_have_count(1)
        expect(highlighted).to_contain_text(f"zz{run}warehouse")

        # LDG-17: a node click selects it and opens the quickview (7.22c);
        # the process node is the one not highlighted. The drawer's scrim
        # covers the diagram while the panel is open (DD-393), so the next
        # diagram click lands after the panel is dismissed — and the dismiss
        # itself deselects the box (LDG-25, DD-403).
        process_node = box.locator("g.node", has_text=f"zz{run}pipeline")
        process_node.click()
        expect(box.locator("g.node.is-selected")).to_have_count(1)
        expect(box.locator("g.node.is-selected")).to_contain_text(f"zz{run}pipeline")
        drawer = authenticated.locator(".aurelius-drawer")
        expect(drawer).to_be_visible()
        drawer.locator(".aurelius-drawer-scrim").click()
        expect(drawer).not_to_be_visible()
        expect(box.locator("g.node.is-selected")).to_have_count(0)
        process_node.click()
        expect(box.locator("g.node.is-selected")).to_have_count(1)
        drawer.locator(".aurelius-drawer-scrim").click()
        expect(drawer).not_to_be_visible()

        # LDG-10's empty state: the unlinked process has no lineage — the
        # aux 204 (LM-05/LM-06, proven above) and the plain message.
        authenticated.goto(urljoin(root_url, f"/en-US/search/details/{lonely_guid}"))
        expect(authenticated.locator("h1.aurelius-details-title")).to_have_text(f"zz{run}lonely")
        lonely_box = authenticated.locator("#lineage-model")
        expect(lonely_box.locator(".aurelius-lineage-empty")).to_be_visible()
        expect(lonely_box.locator("aurelius-atlas-webapp-lineage-viewer")).to_have_count(0)
    finally:
        for type_name in _M4I_TYPES:
            _purge_type(authenticated, root_url, user_token, type_name)


# impact=major, likelihood=high (a young screen with churn on its path)
@pytest.mark.high
@pytest.mark.covers(rules=["LDG-28", "LDG-30", "LDG-31"])
def test__the_toolbar_saves_the_view_and_toggles_fullscreen(
    authenticated: Page, root_url: str, user_token: str
) -> None:
    """The 7.22d toolbar: the save downloads the PNG, fullscreen fixes the drawing (LDG-28/LDG-30/LDG-31).

    The same seeded chain: the save button hands the drawn view to the
    converter and downloads ``Lineage.png`` (the view's own name, LDG-30),
    whose bytes carry the ``tEXt`` chunk pairing ``Title`` with
    ``Lineage`` — the metadata the writer placed before IEND, read back
    from the download (LDG-31). Which conversion path produced the bytes is the engine's
    (the foreignObject fallback included) — the unit spec pins both; here
    the promise is the file. The fullscreen toggle fixes and frees the
    drawing region (LDG-28) and swaps in the fullscreen-only Browse copy.
    The tooltips and the class's pixels are the viewer's unit spec (the
    e2e rule). Self-cleaned by the shared m4i purge (DD-223).
    """
    run = secrets.token_hex(4)
    guids = _seed_m4i_mini_graph(authenticated, root_url, user_token, run)
    dataset_guid = guids["dataset"]

    try:
        # The lineage walks the edge records (CLS-12's race): wait the
        # dataset's lineage ends visible before the screen reads them.
        _wait_entity_read(
            authenticated,
            root_url,
            user_token,
            dataset_guid,
            predicate=lambda entity: (
                _active_edge(entity, "outputFromProcesses", guids["process"])
                and _active_edge(entity, "inputToProcesses", guids["process"])
            ),
        )

        authenticated.goto(urljoin(root_url, f"/en-US/search/details/{dataset_guid}"))
        box = authenticated.locator("#lineage-model")
        expect(box.locator(".aurelius-lineage-title")).to_have_text("Lineage")
        expect(box.locator("g.node", has_text=f"zz{run}warehouse")).to_have_count(1)

        # LDG-30/LDG-31: the save downloads the view under its name, with
        # the metadata chunk in the bytes (the writer's keyword NUL value,
        # read from the download — the tEXt chunk lands before IEND).
        with authenticated.expect_download() as download_info:
            box.locator(".controls .aurelius-lineage-save").click()
        download = download_info.value
        assert download.suggested_filename == "Lineage.png"
        png = download.path().read_bytes()
        assert png[:8] == b"\x89PNG\r\n\x1a\n"
        assert b"Title\x00Lineage" in png

        # LDG-28: the toggle fixes the drawing region and gains the
        # fullscreen-only Browse copy; toggling again frees both.
        drawing = box.locator(".lineage-drawing")
        expect(drawing).not_to_have_class(re.compile("is-fullscreen"))
        expect(box.locator(".controls .aurelius-lineage-browse")).to_have_count(0)

        box.locator(".controls .aurelius-lineage-fullscreen").click()
        expect(drawing).to_have_class(re.compile("is-fullscreen"))
        expect(box.locator(".controls .aurelius-lineage-browse")).to_be_visible()

        box.locator(".controls .aurelius-lineage-fullscreen").click()
        expect(drawing).not_to_have_class(re.compile("is-fullscreen"))
        expect(box.locator(".controls .aurelius-lineage-browse")).to_have_count(0)
    finally:
        for type_name in _M4I_TYPES:
            _purge_type(authenticated, root_url, user_token, type_name)
