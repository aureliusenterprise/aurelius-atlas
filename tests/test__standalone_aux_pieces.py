"""The aux services' compose pieces in the stack (IRT-10, 17.1, DD-674).

The extractor, the lineage API and the validator each own a piece beside their project, the umbrella
includes it always on, and their e2e files (and the webapp's) extend the piece and state only the
test's differences. The stack's compose is read as written, with the pieces merged as compose merges
them (DD-671).
"""

from typing import Any

import pytest
from conftest import WORKSPACE, compose_load, standalone_compose

STACK = WORKSPACE / "docker"
AUX = ("aurelius-atlas-data2model", "aurelius-atlas-lineage-model", "aurelius-atlas-validate-entity")


def _piece_env(name: str) -> dict[str, str]:
    """The standalone service's environment, as the project's own piece writes it."""
    piece = compose_load(WORKSPACE / "apps" / name / "docker" / "compose.yaml")
    return piece["services"][name]["environment"]


@pytest.fixture(scope="module")
def services() -> dict[str, Any]:
    """The stack's compose services, the included fragments merged in."""
    return standalone_compose()["services"]


@pytest.mark.covers(rules=["IRT-10"])
def test__the_umbrella_includes_each_aux_piece_always_on(services: dict[str, Any]) -> None:
    """The umbrella includes the three aux pieces with no profile, so a plain `up -d` serves the
    webapp's lineage and validator pages (IRT-10).
    """  # noqa: D205 - one sentence
    umbrella = compose_load(STACK / "docker-compose.yaml")
    included = {entry["path"] for entry in umbrella.get("include") or ()}
    for name in AUX:
        assert f"../apps/{name}/docker/compose.yaml" in included
    for entry in umbrella.get("include") or ():
        assert "profiles" not in entry, entry["path"]
    for name in (*AUX, "aurelius-atlas-webapp", "embedder"):
        assert name in services, name


@pytest.mark.covers(rules=["IRT-10"])
def test__each_aux_piece_states_the_standalone_posture() -> None:
    """Each piece runs in the proxy's network against the stack's issuer and realm, with the chart's
    audience (the lineage pair keeps `aurelius` as its extra, DD-385) (IRT-10).
    """  # noqa: D205 - one sentence
    for name in AUX:
        piece = compose_load(WORKSPACE / "apps" / name / "docker" / "compose.yaml")
        assert piece["services"][name]["network_mode"] == "service:proxy", name
        env = _piece_env(name)
        key = name.upper().replace("-", "_")
        assert env[f"{key}_AUTH_SERVER_URL"] == "https://localhost:9000/auth/", name
        assert env[f"{key}_AUTH_REALM"] == "aurelius-atlas", name
    assert _piece_env("aurelius-atlas-data2model")["AURELIUS_ATLAS_DATA2MODEL_AUTH_AUDIENCE"] == "aurelius"
    lineage = _piece_env("aurelius-atlas-lineage-model")
    assert lineage["AURELIUS_ATLAS_LINEAGE_MODEL_AUTH_AUDIENCE"] == "aurelius-atlas-lineage-model"
    assert lineage["AURELIUS_ATLAS_LINEAGE_MODEL_AUTH_EXTRA_AUDIENCES"] == '["aurelius"]'
    assert _piece_env("aurelius-atlas-validate-entity")["AURELIUS_ATLAS_VALIDATE_ENTITY_AUTH_AUDIENCE"] == ("aurelius")


@pytest.mark.covers(rules=["IRT-10"])
def test__each_e2e_layer_extends_its_own_piece() -> None:
    """The aux e2e files and the webapp's e2e file extend the project's piece and reset
    `network_mode` back onto their stack network (IRT-10, DD-674).
    """  # noqa: D205 - one sentence
    layers = {
        "aurelius-atlas-data2model": "apps/aurelius-atlas-data2model/e2e/compose.data2model.yaml",
        "aurelius-atlas-lineage-model": "apps/aurelius-atlas-lineage-model/e2e/compose.lineage-model.yaml",
        "aurelius-atlas-validate-entity": "apps/aurelius-atlas-validate-entity/e2e/compose.validate-entity.yaml",
        "aurelius-atlas-webapp": "apps/aurelius-atlas-webapp/e2e/docker-compose.yaml",
    }
    for name, layer_path in layers.items():
        layer = compose_load(WORKSPACE / layer_path)["services"][name]
        extends = layer["extends"]
        assert extends["service"] == name, layer_path
        base = (WORKSPACE / layer_path).parent / extends["file"]
        assert base.resolve() == (WORKSPACE / "apps" / name / "docker" / "compose.yaml").resolve(), layer_path
        if name in AUX:
            assert layer["network_mode"].kind == "reset", f"{name}: the e2e layer keeps its own network"
