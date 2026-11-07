"""E2E: the 7.22a lineage-model data path — the browser's origin to the aux chain.

The webapp's nginx serves the aux API at ``/lineage-model/`` (LDG-06); the
stack carries both aux containers pointed at this stack's real Atlas server
(LDG-08). The scenarios ride the served origin: the aux API's own answers
arrive through nginx (the proxy adds no auth of its own — an anonymous
request reaches the aux 401, LM-08) and the full LM-04 chain runs over real
services: browser token -> aux -> Atlas lineage -> data2model -> ar3 model.
"""

import json
import secrets
from urllib.parse import urljoin

import pytest
from playwright.sync_api import Page
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
