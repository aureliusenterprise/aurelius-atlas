import shutil
from pathlib import Path

import httpx2 as httpx
import pytest
from aurelius_atlas_core.model_loader import BUILTIN_MODELS_DIR
from aurelius_atlas_parity import Scenario, load_scenarios, run_scenario
from aurelius_atlas_server.settings import ServerSettings

SCENARIOS = Path(__file__).parents[1] / "scenarios"
BASE_MODEL = Path("0000-Area0") / "0010-base_model.json"
NEEDS_BASE_MODEL = ("lineage/",)
"""Scenarios on the base model's types (``DataSet``, ``Process``), which the e2e server loads with every model."""


@pytest.fixture
def settings(settings: ServerSettings, tmp_path: Path, request: pytest.FixtureRequest) -> ServerSettings:
    """The conftest's settings; for a scenario on the base model's types, that model alone (MDL-16)."""
    scenario: Scenario = request.node.callspec.params["scenario"]
    if not scenario.id.startswith(NEEDS_BASE_MODEL):
        return settings
    models = tmp_path / "base-model"
    (models / BASE_MODEL.parent).mkdir(parents=True)
    shutil.copy(BUILTIN_MODELS_DIR / BASE_MODEL, models / BASE_MODEL)
    return settings.model_copy(update={"models_dir": models})


@pytest.mark.parametrize("scenario", load_scenarios(SCENARIOS))
async def test__scenario(scenario: Scenario, client: httpx.AsyncClient) -> None:
    """Each parity scenario passes against the application in-process (ADR 052)."""
    await run_scenario(scenario, client)
