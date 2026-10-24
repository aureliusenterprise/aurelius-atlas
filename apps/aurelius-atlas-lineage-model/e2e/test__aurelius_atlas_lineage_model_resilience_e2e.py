"""E2E: the chain's upstream outage (9.1, RSL-02, DD-214) — a real container down.

8.5/8.6 prove the outage paths in-process with a fake transport; this file
stops the fixture Atlas container of the running 8.2 chain (DD-200). The
app's real httpx call then hits a refused connection and answers the
Atlas-shaped 502 (LM-12's transport handler, app.py's RequestError arm) —
over real Docker networking, not a mocked socket. Starting the fixture back
restores the canned answer: the chain recovers in place, no container of the
chain itself restarts.

The file sorts after the main suite; the module fixture stops the fixture
Atlas and the test's ``finally`` starts it back and polls the chain to the
canned answer — the recovery is part of the scenario (RSL-02), and the
fixture's teardown is the crash net: this suite's outage must not leak into
the scenario suites that run after it. The recovery polls on the test's own
event loop (the conftest's loop-scope note): no ``asyncio.run`` across loops
here.
"""

import asyncio
import time
from collections.abc import Iterator
from uuid import UUID

import httpx2 as httpx
import pytest
from aurelius_atlas_lineage_model_client import LineageModelClient, LineageModelClientError
from docker import from_env as docker_from_env
from docker.models.containers import Container

E2E_PROJECT = "aurelius-atlas-lineage-model-e2e"
"""The compose project of the chain's e2e stack (docker-compose.yaml `name:`)."""

RECOVERY_DEADLINE_SECONDS = 90
"""How long the chain may take to answer the canned graph after the restart."""

E_IN = UUID("00000000-0000-4000-8000-000000000001")
"""The canned graph's root (the fixtures file's name, DV-78)."""


def _stack_container(service: str) -> Container:
    """The container of a service of the chain's e2e stack, by compose label.

    @param service the compose service name
    @returns the container handle (reloaded: the status read is fresh)
    """
    client = docker_from_env()
    containers = client.containers.list(
        all=True,
        filters={
            "label": [
                f"com.docker.compose.project={E2E_PROJECT}",
                f"com.docker.compose.service={service}",
            ]
        },
    )
    if not containers:
        message = f"no container of service {service!r} in project {E2E_PROJECT}"
        raise ValueError(message)
    container = containers[0]
    container.reload()
    return container


def _ensure_running(container: Container) -> None:
    """Start the container when it is not running (the crash net).

    @param container the handle to bring back
    """
    container.reload()
    if container.status != "running":
        container.start()


@pytest.fixture(scope="module")
def fixture_atlas_down() -> Iterator[Container]:
    """Stop the fixture Atlas of the chain for the module, guarantee a start.

    The stop is the scenario's arrangement; the finalizer's start is the
    crash net — the scenario's own ``finally`` recovers first, and a crashed
    test must not leave the chain down for the suites that run after.
    @yields the stopped container handle
    """
    container = _stack_container("fixture-atlas")
    _ensure_running(container)  # the scenarios' world: the fixture runs
    container.stop(timeout=5)
    try:
        yield container
    finally:
        _ensure_running(container)


@pytest.mark.covers(
    "aurelius_atlas_lineage_model.app.create_app",
    "aurelius_atlas_lineage_model_client.client.LineageModelClient.get",
    rules=["RSL-02", "LM-12", "CL-30"],
)
async def test__a_fixture_atlas_outage_answers_502_and_the_chain_recovers(
    fixture_atlas_down: Container,  # the outage itself is the arrangement
    api: LineageModelClient,
    client: httpx.AsyncClient,
) -> None:
    """RSL-02: with the fixture Atlas down, the app answers the Atlas-shaped 502.

    LM-12 over a real refused connection: the app's httpx call over the
    compose network is refused and the RequestError handler (app.py's
    transport arm) answers 502 with the ``errorCode``/``errorMessage`` body
    (SRV-04 shape) — the client library raises its typed
    ``LineageModelClientError`` carrying exactly that (CL-30, CL-04). The
    recovery half: start the fixture, poll the chain to the canned extract —
    the chain answers again in place, no chain container restarted.
    """
    try:
        with pytest.raises(LineageModelClientError) as raised:
            await api.get(E_IN)

        assert raised.value.status_code == 502
        assert raised.value.error_code  # the Atlas body's errorCode parsed (CL-04)
        assert "unreachable" in str(raised.value.error_message)

        # The raw transport proves the shape is the app's, not the client's:
        # the same call over bare httpx answers the identical Atlas body.
        response = await client.get("/", params={"guid": str(E_IN)})
        assert response.status_code == 502
        assert response.json()["errorCode"] == raised.value.error_code
    finally:
        _ensure_running(fixture_atlas_down)
        deadline = time.monotonic() + RECOVERY_DEADLINE_SECONDS
        recovered = False
        while time.monotonic() < deadline and not recovered:
            try:
                recovered = await api.get(E_IN) is not None
            except LineageModelClientError:
                recovered = False  # still the 502, until the fixture's healthcheck flips
            if not recovered:
                await asyncio.sleep(2)
        assert recovered, "the chain did not answer the canned graph after the restart"
