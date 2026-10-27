"""E2E: the 8.2 chain — the container, a Keycloak-minted token, the real data2model, the fixture Atlas.

The chain (DD-200): GET / fetches the canned graph from the fixture Atlas,
flattens it, and extracts the model through the real 8.1 data2model container,
forwarding the caller's bearer token (LM-04). The answer must equal the bytes
the scenario fixture carries — the 8.1 engine's own output for the same rows —
so the suite proves cross-container byte parity, not just a 200 (LM-01).
"""

import asyncio
import json
import secrets
import time
from pathlib import Path
from uuid import UUID

import httpx2 as httpx
import pytest
from aurelius_atlas_lineage_model_client import LineageModelClient

# Tempo's query API on the dev observability stack (its publishes are
# loopback-pinned, CIA-03): the chain-stitch probe reads the caller's trace
# back through it to prove both containers answered inside one trace (DD-210).
TEMPO_HOST = "127.0.0.1"
TEMPO_PORT = 3200

CANNED_EXTRACT = Path(__file__).parents[1] / "scenarios" / "fixtures" / "graph.extract.json"
"""The 8.1 engine's answer for the canned graph's rows, generated with the fixtures."""

E_IN = UUID("00000000-0000-4000-8000-000000000001")
"""The canned graph's root: the fixed UUID the fixture file is named for (DV-78)."""


async def _fetch_trace(trace_id: str) -> str | None:
    """One Tempo trace-by-id poll: the NDJSON body when the trace is queryable, else None."""
    async with httpx.AsyncClient(timeout=10) as tempo:
        fetched = await tempo.get(
            f"http://{TEMPO_HOST}:{TEMPO_PORT}/api/traces/{trace_id}",
            params={"encoding": "json"},
        )
    return fetched.text if fetched.status_code == 200 else None


@pytest.mark.covers("aurelius_atlas_lineage_model.app.create_app", rules=["LM-08"])
async def test__a_missing_token_is_rejected(anonymous_client: httpx.AsyncClient) -> None:
    """The container, on the dev issuer: no bearer token is a 401 (LM-08, AUX-05)."""
    response = await anonymous_client.get("/", params={"guid": str(E_IN)})
    assert response.status_code == 401


@pytest.mark.covers(
    "aurelius_atlas_lineage_model.app.create_app",
    "aurelius_atlas_lineage_model_client.client.LineageModelClient.get",
    rules=["LM-01", "LM-04", "LM-08", "CL-03", "CL-30"],
)
async def test__the_lineage_graph_extracts_through_the_chain(api: LineageModelClient) -> None:
    """With a real realm token, the client library runs the chain to the real data2model (LM-01, LM-04)."""
    response = await api.get(E_IN)
    assert response is not None
    # The proxy answers the extraction verbatim: the same bytes the 8.1 engine
    # produces for the graph's rows (LM-01, proven against the 8.1 scenario).
    # The typed round-trip equals the fixture document, key for key.
    assert response.model_dump(mode="json", by_alias=True) == json.loads(CANNED_EXTRACT.read_text())


@pytest.mark.covers(
    "aurelius_atlas_lineage_model.app.create_app",
    "aurelius_atlas_lineage_model_client.client.LineageModelClient.get",
    rules=["LM-05", "CL-30"],
)
async def test__an_unknown_guid_is_no_content(api: LineageModelClient) -> None:
    """The fixture Atlas has no file for the guid: the 204 becomes the client's ``None`` (LM-05, CL-30)."""
    assert await api.get(UUID(int=9)) is None


@pytest.mark.covers("aurelius_atlas_lineage_model.app.create_app", rules=["LM-09"])
async def test__liveness_answers_anonymously(anonymous_client: httpx.AsyncClient) -> None:
    """The container healthcheck route answers without a token (the image is healthy by construction)."""
    assert (await anonymous_client.get("/liveness")).status_code == 204


@pytest.mark.covers("aurelius_atlas_lineage_model.app.create_app", rules=["LM-04"])
async def test__the_chain_shares_one_trace_with_the_caller(client: httpx.AsyncClient) -> None:
    """The caller's traceparent rides the chain: both containers answer in ONE trace (DD-210).

    The probe: mint a trace id, GET / with it as W3C ``traceparent``, then read
    the trace back from Tempo (the webapp suite's api/traces/ pattern). The
    native FastAPI instrumentor joins the caller's trace and the httpx
    instrumentor carries it to the extract (LM-04's call), so the lineage-model
    server span and the data2model ``POST /extract`` server span must surface
    under the minted trace id — the 8.2 chain is one trace in Tempo.
    """
    trace_id = secrets.token_hex(16)
    response = await client.get(
        "/",
        params={"guid": str(E_IN)},
        headers={"traceparent": f"00-{trace_id}-{secrets.token_hex(8)}-01"},
    )
    assert response.status_code == 200

    # The e2e containers export on a 1s BatchSpanProcessor cycle (DD-225) and
    # Tempo's live store indexes within seconds; poll trace-by-id (the
    # deterministic route — 404 first, data after; see the webapp suite's
    # stamping probe).
    deadline = time.monotonic() + 90
    while time.monotonic() < deadline:
        body = await _fetch_trace(trace_id)
        if body is not None:
            seen: dict[str, set[str]] = {}
            for line in body.strip().splitlines():
                for batch in json.loads(line).get("batches", []):
                    attrs = batch.get("resource", {}).get("attributes", [])
                    service = next(
                        (a["value"].get("stringValue", "") for a in attrs if a.get("key") == "service.name"),
                        "",
                    )
                    for scope in batch.get("scopeSpans", []):
                        for span in scope.get("spans", []):
                            seen.setdefault(service, set()).add(span.get("name", ""))
            if "GET /" in seen.get("aurelius-atlas-lineage-model", set()) and "POST /extract" in seen.get(
                "aurelius-atlas-data2model", set()
            ):
                return
        await asyncio.sleep(1)

    pytest.fail(f"Tempo never showed the chain inside the caller's trace {trace_id} — no stitch")
