from pathlib import Path

import httpx
import pytest
from aurelius_atlas_parity import Scenario, load_scenarios, run_scenario

SCENARIOS = Path(__file__).parents[1] / "scenarios"


# The client fixture lives on the module loop (asyncio_default_fixture_loop_scope), so the test runs there too.
@pytest.mark.asyncio(loop_scope="module")
@pytest.mark.parametrize("scenario", load_scenarios(SCENARIOS, authenticated_run=True))
async def test__scenario(scenario: Scenario, client: httpx.AsyncClient, writer_bearer: str) -> None:
    """Each parity scenario passes against the container image over HTTPS, on the dev store (ADR 052)."""
    # The session scenario authenticates with {bearer}; the others ask public endpoints and never
    # resolve the name. Minted per test, so the run never races the issuer's token lifetime.
    await run_scenario(scenario, client, saved={"bearer": writer_bearer})
