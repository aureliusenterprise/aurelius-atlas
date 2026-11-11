"""Parity scenarios: the draft's contract, read from the Aurelius source (ADR 052, ADR 061).

Since 12.7 a scenario's answer rides the fake catalogue: the stub answers the
rule walk with the very rule records the scenario's ``source`` cites (the
m4i_dataset corpus's name/fields rules, restated in 12.6's vocabulary), and the
expected document is those records' own verdict lines (VEV-02). The comparison
is whole-body, as 8.6's mock scenarios were — now over the verdict shape.
"""

from collections.abc import Callable
from pathlib import Path

import httpx2 as httpx
import pytest
from aurelius_atlas_parity import Scenario, load_scenarios, run_scenario
from fake_catalogue import FakeCatalogue, rule_entity, search_result

SCENARIOS = Path(__file__).parents[1] / "scenarios"

NAME_RULE = rule_entity(
    "rule-dataset-name",
    "Dataset has a name",
    {
        "name": "Dataset has a name",
        "active": True,
        "dqcheckkind": "ATTRIBUTE_PRESENT",
        "dqattribute": "name",
        "compliantMessage": "This dataset has a name",
        "nonCompliantMessage": "This dataset should have a name",
    },
)
FIELDS_RULE = rule_entity(
    "rule-dataset-fields",
    "Dataset has a field",
    {
        "name": "Dataset has a field",
        "active": True,
        "dqcheckkind": "ATTRIBUTE_NOT_EMPTY",
        "dqattribute": "fields",
        "compliantMessage": "This dataset has at least one field",
        "nonCompliantMessage": "This dataset should have at least one field",
    },
)
"""The scenario's rules: the m4i_dataset corpus's own name/fields records, in 12.6's shape
(``.scratch/aurelius/libs/m4i-governance-data-quality/.../definitions/m4i_dataset.json``)."""


def _bearer(token: str) -> dict[str, str]:
    """The authorization header for a bearer token."""
    return {"authorization": f"Bearer {token}"}


@pytest.fixture
def scenario_catalogue(catalogue: FakeCatalogue) -> FakeCatalogue:
    """The fake catalogue answering the rule walk with the scenario's two rules."""

    def handler(_request: httpx.Request) -> httpx.Response:
        return FakeCatalogue.json(200, search_result([NAME_RULE, FIELDS_RULE], "-1"))

    catalogue.handler = handler
    return catalogue


# The scenario's rules/covers become the test's covers marker by load_scenarios (ADR 049).
@pytest.mark.parametrize("scenario", load_scenarios(SCENARIOS))
async def test__scenario(
    scenario: Scenario,
    client: httpx.AsyncClient,
    token: Callable[..., str],
    scenario_catalogue: FakeCatalogue,
) -> None:
    """Each parity scenario passes against the application in-process, over the stubbed rules."""
    _ = scenario_catalogue  # the fixture's only purpose is to wire the catalogue handler
    client.headers.update(_bearer(token()))
    await run_scenario(scenario, client)
