"""Edge tracing: the webapp's nginx exports spans to the collector (SHL-15, DD-239).

The probes ride the real path — the built image, the e2e nginx config (OTel
module loaded through the image's main-context modules include), the dev
collector's legacy gRPC leg (TLS + shared ingest token), and Tempo read-back.
"""

import base64
import json
import secrets
import time

import pytest
from conftest import TEMPO_HOST, TEMPO_PORT
from playwright.sync_api import Page

EDGE_SERVICE = "aurelius-atlas-webapp-edge"
SERVER_SERVICE = "aurelius-atlas-server"  # app.py NAME — the server span's resource


def _spans_of(body: str) -> list[tuple[dict[str, str], dict]]:
    """(resource attributes, span) pairs for every span in a Tempo NDJSON body."""
    pairs = []
    for line in body.strip().splitlines():
        for batch in json.loads(line).get("batches", []):
            resource = {
                attr["key"]: attr.get("value", {}).get("stringValue", "")
                for attr in batch.get("resource", {}).get("attributes", [])
            }
            pairs.extend((resource, span) for scope in batch.get("scopeSpans", []) for span in scope.get("spans", []))
    return pairs


def _hex(span_id: str) -> str:
    """Tempo's JSON encoding carries ids base64; the minted ones are hex."""
    return base64.b64decode(span_id).hex()


def _attrs(span: dict) -> dict[str, object]:
    raw = {}
    for attr in span.get("attributes", []):
        value = attr.get("value", {})
        raw[attr["key"]] = value.get("stringValue", value.get("intValue", ""))
    return raw


@pytest.mark.covers(rules=["ETR-01", "ETR-02"])
def test__the_edge_span_rides_the_browser_trace_to_the_server(page: Page, root_url: str) -> None:
    """A minted traceparent turns into edge span -> server span, stitched (ETR-01, ETR-02).

    The probe: GET the server's version endpoint through nginx with a minted
    ``traceparent``. The edge span must carry the minted trace id and the
    minted parent id (``otel_trace_context propagate`` extracts), the edge's
    own view of the request (method/target/route/status/client addr — the
    module's default attributes), and be the parent of the server's request
    span (propagate injects the edge span id upstream). That is the seam the
    stack was blind to: requests refused at the edge (9.3's limiter) live
    entirely in this span, upstream of the server.
    """
    trace_id = secrets.token_hex(16)
    parent_id = secrets.token_hex(8)

    response = page.request.get(
        f"{root_url}api/atlas/admin/version",
        headers={"traceparent": f"00-{trace_id}-{parent_id}-01"},
    )
    assert response.status == 200

    deadline = time.monotonic() + 60
    while time.monotonic() < deadline:
        fetched = page.request.get(
            f"http://{TEMPO_HOST}:{TEMPO_PORT}/api/traces/{trace_id}",
            params={"encoding": "json"},
        )
        if fetched.status == 200:
            pairs = _spans_of(fetched.text())
            edge = next(
                ((resource, span) for resource, span in pairs if resource.get("service.name") == EDGE_SERVICE),
                None,
            )
            if edge is None:
                time.sleep(1)
                continue

            _resource, span = edge
            attrs = _attrs(span)

            assert _hex(span.get("parentSpanId", "")) == parent_id, (
                f"edge span parent is {span.get('parentSpanId')!r}, not the minted {parent_id!r}"
                " — propagate did not extract"
            )
            assert attrs.get("http.method") == "GET"
            assert attrs.get("http.target") == "/api/atlas/admin/version"
            assert str(attrs.get("http.status_code")) == "200"
            assert attrs.get("http.route") == "/api/"
            assert attrs.get("net.sock.peer.addr"), "edge span carries no client address"

            # The seam (ETR-01's other half): the server's request span is
            # this span's child — the edge span id rode the injected
            # traceparent into the ASGI instrumentation.
            server_parented = any(
                _hex(span.get("spanId", "")) == _hex(child.get("parentSpanId", ""))
                for child in (s for r, s in pairs if r.get("service.name") == SERVER_SERVICE)
            )
            assert server_parented, "the server's request span is not a child of the edge span"
            return
        time.sleep(1)

    pytest.fail(f"Tempo never showed the edge span for trace {trace_id} — exporter leg, module load, or sampling")


@pytest.mark.covers(rules=["ETR-03"])
def test__edge_telemetry_is_producer_attributed(page: Page, root_url: str) -> None:
    """The legacy-leg stamp holds: edge spans carry no user identity (ETR-03).

    The collector's resource processor upserts enduser.id from the verified
    token's claims; the shared ingest token has no OIDC context, so the
    upsert lands no user value — the attribute reaches Tempo absent (the
    empty upsert is not stored) — and the edge is attributed as a producer
    (service.name), never as a user. A leaked ingest token cannot forge
    user-attributed telemetry (CIA-05's rule, edge edition).
    """
    trace_id = secrets.token_hex(16)

    response = page.request.get(
        f"{root_url}api/atlas/admin/version",
        headers={"traceparent": f"00-{trace_id}-{secrets.token_hex(8)}-01"},
    )
    assert response.status == 200

    deadline = time.monotonic() + 60
    while time.monotonic() < deadline:
        fetched = page.request.get(
            f"http://{TEMPO_HOST}:{TEMPO_PORT}/api/traces/{trace_id}",
            params={"encoding": "json"},
        )
        if fetched.status == 200:
            for resource, _span in _spans_of(fetched.text()):
                if resource.get("service.name") == EDGE_SERVICE:
                    assert resource.get("enduser.id") in (None, ""), (
                        f"edge resource carries enduser.id={resource.get('enduser.id')!r}"
                        " — the legacy leg lands user-less (DD-194)"
                    )
                    return
            time.sleep(1)
        else:
            time.sleep(1)

    pytest.fail(f"Tempo never showed the edge span for trace {trace_id}")
