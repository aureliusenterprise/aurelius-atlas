"""Parity scenarios: the editor's contract, read from the Aurelius source (ADR 052, ADR 055).

The mock answers a constant, so a scenario is a whole-body comparison: the
caller's entity payload in, the legacy's ``output`` dict out, byte equality,
with no volatile fields and no upstream to stub (DV-14).
"""

from collections.abc import Callable
from pathlib import Path

import httpx2 as httpx
import pytest
from aurelius_atlas_parity import Scenario, load_scenarios, run_scenario

SCENARIOS = Path(__file__).parents[1] / "scenarios"


def _bearer(token: str) -> dict[str, str]:
    """The authorization header for a bearer token."""
    return {"authorization": f"Bearer {token}"}


@pytest.fixture
def authorized_client(client: httpx.AsyncClient, token: Callable[..., str]) -> httpx.AsyncClient:
    """The in-process client with a bearer token, as the editor's caller sends it."""
    client.headers.update(_bearer(token()))
    return client


# The scenario's rules/covers become the test's covers marker by load_scenarios (ADR 049).
@pytest.mark.parametrize("scenario", load_scenarios(SCENARIOS))
async def test__scenario(scenario: Scenario, authorized_client: httpx.AsyncClient) -> None:
    """Each parity scenario passes against the application in-process."""
    await run_scenario(scenario, authorized_client)
