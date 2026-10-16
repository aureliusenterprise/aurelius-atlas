import asyncio
from collections.abc import AsyncGenerator
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

import pytest
from aurelius_example import Entity
from aurelius_fastapi_example.models import Envelope
from aurelius_fastapi_example.providers import metrics as metrics_module
from aurelius_fastapi_example.providers import notifications as cdc_notifications
from fastapi import FastAPI
from fastapi.testclient import TestClient


@pytest.fixture(autouse=True)
def _clean_sse_counter() -> None:
    """Reset the shared counter so tests are independent of ordering."""
    metrics_module.SSE_CONNECTIONS.add(-metrics_module.SSE_CONNECTIONS.active)


def _override_notifications(
    app: FastAPI,
    *,
    hold: float = 0.0,
    observe: list[int] | None = None,
) -> None:
    """Override the notifications dependency with a stream ending after ``hold`` seconds.

    ``observe`` (when given) receives the live connection-counter value taken
    from inside the generator, i.e. strictly while the stream is open — which
    is deterministic, unlike racing the ASGI transport from the test thread.
    """
    envelope = Envelope[Entity](guid=uuid4(), op="INSERT", timestamp=datetime.now(tz=UTC), value=None)

    async def listener() -> AsyncGenerator[Any]:
        yield envelope
        if hold:
            await asyncio.sleep(hold)
        if observe is not None:
            observe.append(metrics_module.SSE_CONNECTIONS.active)

    app.dependency_overrides[cdc_notifications] = lambda: listener


def test__sse_route_returns_counter_to_zero_after_stream(app: FastAPI, authenticated_client: TestClient) -> None:
    """A completed stream must leave the counter where it found it."""
    assert metrics_module.SSE_CONNECTIONS.active == 0
    _override_notifications(app)

    response = authenticated_client.get("/entities/sse")

    assert response.status_code == 200
    assert metrics_module.SSE_CONNECTIONS.active == 0


def test__sse_route_counts_open_stream(app: FastAPI, authenticated_client: TestClient) -> None:
    """The counter reads 1 while the stream is open, and back to 0 once it ends."""
    observed: list[int] = []
    _override_notifications(app, hold=0.2, observe=observed)

    response = authenticated_client.get("/entities/sse")

    assert response.status_code == 200
    assert observed == [1]
    assert metrics_module.SSE_CONNECTIONS.active == 0
