"""Parity scenarios: the lineage caller's payload, read from the Aurelius source (ADR 052, ADR 055)."""

from collections.abc import Callable
from pathlib import Path

import httpx
import pytest
from aurelius_atlas_parity import Scenario, load_scenarios, run_scenario

SCENARIOS = Path(__file__).parents[1] / "scenarios"


def _bearer(token: str) -> dict[str, str]:
    """The authorization header for a bearer token."""
    return {"authorization": f"Bearer {token}"}


@pytest.fixture
def authorized_client(client: httpx.AsyncClient, token: Callable[..., str]) -> httpx.AsyncClient:
    """The in-process client, carrying a bearer token minted for this app (the scenarios call /extract)."""
    client.headers.update(_bearer(token()))
    return client


# The scenario's rules/covers become the test's covers marker by load_scenarios (ADR 049).
@pytest.mark.parametrize("scenario", load_scenarios(SCENARIOS))
async def test__scenario(scenario: Scenario, authorized_client: httpx.AsyncClient) -> None:
    """Each parity scenario passes against the application in-process."""
    await run_scenario(scenario, authorized_client)
