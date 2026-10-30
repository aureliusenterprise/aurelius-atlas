import shutil
from pathlib import Path

import httpx2 as httpx
import pytest
from aurelius_atlas_core.model_loader import BUILTIN_MODELS_DIR
from aurelius_atlas_parity import Scenario, load_scenarios, run_scenario

SCENARIOS = Path(__file__).parents[1] / "scenarios"
CORE_MODELS = (Path("0000-Area0") / "0010-base_model.json", Path("0000-Area0") / "0011-glossary_model.json")
NEEDS_CORE_MODELS = ("glossary/", "lineage/")
"""Scenarios on the base and glossary models' types (``DataSet``, ``Process``, ``AtlasGlossary``), which the e2e
server loads with every model."""


def core_models(directory: Path) -> Path:
    """A models directory holding Atlas's base and glossary models alone (MDL-16)."""
    for model in CORE_MODELS:
        (directory / model.parent).mkdir(parents=True, exist_ok=True)
        shutil.copy(BUILTIN_MODELS_DIR / model, directory / model)
    return directory


@pytest.fixture
def models_dir(models_dir: Path, tmp_path: Path, request: pytest.FixtureRequest) -> Path:
    """No models, but for a scenario on the core models' types those models alone."""
    scenario: Scenario = request.node.callspec.params["scenario"]
    return core_models(tmp_path / "core-models") if scenario.id.startswith(NEEDS_CORE_MODELS) else models_dir


@pytest.mark.parametrize("scenario", load_scenarios(SCENARIOS))
async def test__scenario(scenario: Scenario, client: httpx.AsyncClient) -> None:
    """Each parity scenario passes against the application in-process (ADR 052)."""
    await run_scenario(scenario, client)
