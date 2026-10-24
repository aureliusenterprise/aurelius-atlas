from __future__ import annotations

import asyncio
import json
import secrets
import time
from collections.abc import AsyncIterator

import httpx2 as httpx
import pytest
from aurelius_atlas_server_client import AtlasClient
from playwright.async_api import Browser, Response, async_playwright

SESSION = "/api/atlas/admin/session"

TEMPO_HOST = "127.0.0.1"
TEMPO_PORT = 3200
"""The dev Tempo query API (loopback-published, CIA-03): the ES probe reads the trace back through it."""


@pytest.fixture(scope="module")
async def browser() -> AsyncIterator[Browser]:
    """Chromium on Playwright's async API.

    pytest-playwright's sync ``page`` fixture keeps an event loop running on the main thread for the whole
    session, which stops pytest-asyncio from running the scenario tests after it; the async API shares
    pytest-asyncio's loop instead.
    """
    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch()
        yield browser
        await browser.close()


# The browser fixture lives on the module loop, so the test runs there too.
@pytest.mark.asyncio(loop_scope="module")
@pytest.mark.covers(rules=["DSH-01", "DSH-02", "DSH-05", "DSH-06"])
@pytest.mark.parametrize("path", ["/", "/n/"], ids=["dashboardv2", "dashboardv3"])
async def test__dashboard_loads_and_asks_the_server_for_the_session(browser: Browser, server: str, path: str) -> None:
    """The dashboard's page and all of its own files load from the image, and it asks for the session.

    Playwright's bundled browsers have their own trust stores and cannot enroll the mkcert root, so page
    navigation skips certificate verification. This is the one named relaxation of the browser-facing path
    (ADR 039), as in the frontend example: the API tests in this directory verify the server's certificate
    against the CA.
    """
    context = await browser.new_context(ignore_https_errors=True)
    page = await context.new_page()
    broken: list[str] = []

    def record(response: Response) -> None:
        if "/api/" not in response.url and response.status >= 400:
            broken.append(f"{response.status} {response.url}")

    page.on("response", record)
    async with page.expect_response(lambda response: SESSION in response.url, timeout=30_000) as session:
        await page.goto(f"{server}{path}")

    assert (await session.value).status == 200
    assert await page.title() == "Atlas"
    assert broken == []
    await context.close()


@pytest.mark.covers(
    "aurelius_atlas_server_client.client.AdminApi.version",
    "aurelius_atlas_server_client.client.AdminApi.status",
    "aurelius_atlas_server_client.client.AdminApi.liveness",
    "aurelius_atlas_server_client.client.AdminApi.readiness",
    rules=["ADM-01", "ADM-02", "ADM-03", "ADM-04", "CL-11"],
)
async def test__the_admin_answers_come_through_the_client_library(api: AtlasClient) -> None:
    """The client library reads the container's admin routes over TLS (CL-11, ADM-01..ADM-04).

    The typed twin of the dashboard's session call: the same server, the same
    dev CA, parsed into the contract models (CL-10) — readiness proves the
    store is healthy enough to serve, which is what the image's healthcheck asserts.
    """
    version = await api.admin.version()
    assert version.name == "aurelius-atlas"
    assert version.version
    assert (await api.admin.status()).status == "ACTIVE"
    assert await api.admin.liveness() == "Service is live"
    assert await api.admin.readiness() == "Service is ready to accept requests"


async def _fetch_trace(trace_id: str) -> str | None:
    """One Tempo trace-by-id poll: the NDJSON body when the trace is queryable, else None."""
    async with httpx.AsyncClient(timeout=10) as tempo:
        fetched = await tempo.get(
            f"http://{TEMPO_HOST}:{TEMPO_PORT}/api/traces/{trace_id}",
            params={"encoding": "json"},
        )
    return fetched.text if fetched.status_code == 200 else None


@pytest.mark.covers(rules=["CIA-07"])
async def test__the_store_calls_ride_the_server_trace(client: httpx.AsyncClient) -> None:
    """elasticsearch-py's native OTel spans ride the server trace (DD-210, DD-196).

    elasticsearch-py >= 8.13 emits a span per store operation on the global
    tracer, on by default; ``setup_telemetry`` installs that tracer, so the
    app-owned per-service leg (the JWT pipeline, CIA-07) carries the store
    spans as children of the request span — with ``db.system.name`` and
    ``db.operation.name`` on them. The probe: mint a trace id, GET
    typedefs/headers with it as W3C ``traceparent``, read the trace back from
    Tempo, and require BOTH the server's request span and an
    ``elasticsearch``-attributed span under the caller's trace id — the store
    round-trip is visible inside the request it served.
    """
    trace_id = secrets.token_hex(16)
    parent_id = secrets.token_hex(8)

    # BatchSpanProcessor exports on a 5s cycle and Tempo's live store indexes
    # within seconds; poll trace-by-id (404 first, data after — the webapp
    # suite's stamping-probe pattern, 120s). The GET repeats every cycle: a
    # store span lost in a collector/Tempo hiccup is replaced by the next
    # cycle's, so the probe fails only when ES emits no spans at all.
    deadline = time.monotonic() + 120
    while time.monotonic() < deadline:
        response = await client.get(
            "/api/atlas/v2/types/typedefs/headers",
            headers={"traceparent": f"00-{trace_id}-{parent_id}-01"},
        )
        assert response.status_code == 200
        body = await _fetch_trace(trace_id)
        if body is not None:
            request_span = False
            store_span = False
            for line in body.strip().splitlines():
                for batch in json.loads(line).get("batches", []):
                    for scope in batch.get("scopeSpans", []):
                        for span in scope.get("spans", []):
                            attrs = {a["key"]: a["value"].get("stringValue", "") for a in span.get("attributes", [])}
                            if span.get("name") == "GET /api/atlas/v2/types/typedefs/headers":
                                request_span = True
                            if attrs.get("db.system.name") == "elasticsearch":
                                store_span = True
            if request_span and store_span:
                return
        await asyncio.sleep(3)

    pytest.fail(f"Tempo never showed a store span inside the request trace {trace_id} — ES not instrumented")
