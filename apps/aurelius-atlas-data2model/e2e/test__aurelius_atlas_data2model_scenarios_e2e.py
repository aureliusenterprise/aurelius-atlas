"""The parity scenarios, run against the container image over HTTPS with a realm token (ADR 052)."""

from pathlib import Path

import httpx2 as httpx
import pytest
from aurelius_atlas_parity import Scenario, load_scenarios, run_scenario

SCENARIOS = Path(__file__).parents[1] / "scenarios"


@pytest.mark.parametrize("scenario", load_scenarios(SCENARIOS))
async def test__scenario(scenario: Scenario, client: httpx.AsyncClient) -> None:
    """Each parity scenario passes against the container image (the client carries the realm token)."""
    await run_scenario(scenario, client)
