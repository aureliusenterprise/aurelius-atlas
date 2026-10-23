"""Parity scenarios: the legacy proxy's contract, read from the Aurelius source (ADR 052, ADR 055).

Each scenario is served by the fake upstream (DD-111) answering from the
generated fixtures: the canned Atlas lineage for the graph's root, and the
canned data2model extraction — the 8.1 engine's own bytes for the same rows.
The app's answer must match the expected response in full: the proxy answers
the extraction verbatim (LM-01).
"""

import json
from collections.abc import Callable
from pathlib import Path
from typing import Any

import httpx
import pytest
from aurelius_atlas_parity import Scenario, load_scenarios, run_scenario
from fake_upstream import FakeUpstream

SCENARIOS = Path(__file__).parents[1] / "scenarios"
FIXTURES = SCENARIOS / "fixtures"


def _bearer(token: str) -> dict[str, str]:
    """The authorization header for a bearer token."""
    return {"authorization": f"Bearer {token}"}


@pytest.fixture
def scenario_upstream(upstream: FakeUpstream) -> FakeUpstream:
    """The fake Atlas/data2model answering the scenario's calls from the fixtures."""
    lineage: dict[str, Any] = json.loads((FIXTURES / "graph.lineage.json").read_text())
    extract: dict[str, Any] = json.loads((FIXTURES / "graph.extract.json").read_text())

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/v2/lineage/e-in":
            return FakeUpstream.json(200, lineage)
        if request.url.path == "/extract":
            return FakeUpstream.json(200, extract)
        return FakeUpstream.json(404, {"error": f"unstubbed {request.url.path}"})

    upstream.handler = handler
    return upstream


@pytest.fixture
def authorized_client(
    client: httpx.AsyncClient, token: Callable[..., str], scenario_upstream: FakeUpstream
) -> httpx.AsyncClient:
    """The in-process client with a bearer token, wired to the scenario's fixtures."""
    _ = scenario_upstream  # the fixture's only purpose is to wire the upstream handler
    client.headers.update(_bearer(token()))
    return client


# The scenario's rules/covers become the test's covers marker by load_scenarios (ADR 049).
@pytest.mark.parametrize("scenario", load_scenarios(SCENARIOS))
async def test__scenario(scenario: Scenario, authorized_client: httpx.AsyncClient) -> None:
    """Each parity scenario passes against the application in-process."""
    await run_scenario(scenario, authorized_client)
