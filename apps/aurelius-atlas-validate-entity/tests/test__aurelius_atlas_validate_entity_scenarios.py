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
        "qualifiedName": "m4i_dataset--name",
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
        "qualifiedName": "m4i_dataset--fields",
        "active": True,
        "dqcheckkind": "ATTRIBUTE_NOT_EMPTY",
        "dqattribute": "fields",
        "compliantMessage": "This dataset has at least one field",
        "nonCompliantMessage": "This dataset should have at least one field",
    },
)
CHILD_RULE = rule_entity(
    "rule-dataset-child",
    "Dataset has a child",
    {
        "name": "Dataset has a child",
        "qualifiedName": "m4i_dataset--childDataset",
        "active": True,
        "dqcheckkind": "ATTRIBUTE_PRESENT",
        "dqattribute": "childDataset",
        "compliantMessage": "This entity has a childDataset",
        "nonCompliantMessage": "This entity is missing a childDataset",
    },
)
"""The sample corpus's own ``completeness('childDataset')`` record (guid 0d3807d0-d6cc-4093-
b990-6a0928504a94 in ``data/atlas-sample/sample_data.zip``), restated in the vocabulary
shape: a PRESENCE rule over a relationship attribute (12.7a, VEV-08, DD-634)."""
SYSTEM_NAME_RULE = rule_entity(
    "rule-system-name",
    "System has a name",
    {
        "name": "System has a name",
        "qualifiedName": "m4i_system--name",
        "active": True,
        "dqcheckkind": "ATTRIBUTE_PRESENT",
        "dqattribute": "name",
        "compliantMessage": "This system has a name",
        "nonCompliantMessage": "This system should have a name",
    },
)
"""The m4i_system corpus's own name record (VEV-07): a foreign draft must not answer it."""
"""The scenario's rules: the m4i_dataset corpus's own name/fields records, in 12.6's shape
(``.scratch/aurelius/libs/m4i-governance-data-quality/.../definitions/m4i_dataset.json``),
beside the m4i_system name record of the same corpus (12.7a, VEV-07)."""


def _bearer(token: str) -> dict[str, str]:
    """The authorization header for a bearer token."""
    return {"authorization": f"Bearer {token}"}


@pytest.fixture
def scenario_catalogue(catalogue: FakeCatalogue) -> FakeCatalogue:
    """The fake catalogue answering the rule walk with the scenario's rules."""

    def handler(_request: httpx.Request) -> httpx.Response:
        return FakeCatalogue.json(
            200,
            search_result([NAME_RULE, FIELDS_RULE, CHILD_RULE, SYSTEM_NAME_RULE], "-1"),
        )

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
