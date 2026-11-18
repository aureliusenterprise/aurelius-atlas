"""The standalone stack's certificate and sample folders (SBD-12, DD-687).

Each app piece names the folder it mounts read-only through a required compose variable, so an install that
sets no folder fails the start with the variable's name rather than reading a path of the repository. The
three infra pieces keep their own literal paths, which the bundle's path rewriter relocates (SBD-03). The
merged stack is read as compose resolves it (DD-671), with no Docker daemon.
"""

import re
from typing import Any

import pytest
from conftest import STACK, standalone_compose

# A folder a piece requires: a `${NAME:?message}` source on a certificate or sample mount.
FOLDER_MOUNT = re.compile(r"^\$\{(?P<var>[A-Z][A-Z0-9_]+):\?[^}]*\}:(?:/certs|/sample):ro$")

# The nine services of the seven app pieces that mount a folder the stack requires.
GUARDED_SERVICES = {
    "proxy",
    "aurelius-atlas-server",
    "aurelius-atlas-webapp",
    "embedder",
    "aurelius-atlas-data2model",
    "aurelius-atlas-lineage-model",
    "aurelius-atlas-validate-entity",
    "sample-import",
    "tenants",
}

# The infra services that keep a literal certificate folder (SBD-03). The build one shot of 17.2
# is gone with the Keycloak build stage (SPC-05, DD-696).
LITERAL_SERVICES = {"keycloak", "postgres-keycloak", "otel-collector"}


@pytest.fixture(scope="module")
def services() -> dict[str, Any]:
    """The stack's compose services, the included fragments merged in."""
    return standalone_compose()["services"]


def _folder_mounts(service: dict[str, Any]) -> list[str]:
    """The mounts that read a certificate or a sample folder into the container."""
    return [v for v in service.get("volumes") or [] if v.endswith(("/certs:ro", "/sample:ro"))]


@pytest.mark.covers(rules=["SBD-12", "SPC-01", "SPC-02"])
def test__every_app_folder_mount_names_a_required_variable(services: dict[str, Any]) -> None:
    """No app folder mount carries a default path: a defaulted `:-` would let an install read a path of
    this repository, which is the failure SBD-12 removes (DD-687).
    """  # noqa: D205 - one sentence
    guarded: set[str] = set()
    literal: set[str] = set()
    for name, service in services.items():
        for mount in _folder_mounts(service):
            if mount.startswith("${"):
                assert FOLDER_MOUNT.match(mount) is not None, f"{name}: {mount}"
                guarded.add(name)
            else:
                literal.add(name)
    assert guarded == GUARDED_SERVICES
    assert literal == LITERAL_SERVICES


@pytest.mark.covers(rules=["SBD-12"])
def test__stacks_env_answers_every_required_folder(services: dict[str, Any]) -> None:
    """The repository's own answers in `docker/stack.env` are exactly the folder names the pieces require,
    so the umbrella starts with no extra argument and a new name without an answer fails here (DD-687).
    """  # noqa: D205 - one sentence
    required = set()
    for service in services.values():
        for mount in _folder_mounts(service):
            match = FOLDER_MOUNT.match(mount)
            if match is not None:
                required.add(match.group("var"))
    answered = {
        line.split("=", 1)[0]
        for line in (STACK / "stack.env").read_text().splitlines()
        if line and not line.startswith("#")
    }
    assert required == answered
