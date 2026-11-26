"""The standalone stack's image references (SBD-06, DD-685).

Every Aurelius image the stack runs is built in the repository, so each piece names it through a
compose-time variable (`<PROJECT>_IMAGE`) whose default is the `nx docker-build` tag (ADR 065: the
stack builds, never pulls). The variable is what lets one install point the whole stack at published
images, which is what increment 17.3's bundle does. Third-party images (`dhi.io/*`) keep their
committed tags: they are pinned by the hardening increment, not moved by an install. The stack's
compose is read as written, with the fragments merged as compose merges them (DD-671).
"""

import re
from typing import Any

import pytest
from conftest import standalone_compose

# A variable that names an Aurelius image: `${NAME_IMAGE:-ghcr.io/<org>/<project>:local}`.
AURELIUS_IMAGE = re.compile(
    r"^\$\{(?P<var>[A-Z][A-Z0-9_]*_IMAGE):-ghcr\.io/aureliusenterprise/[a-z0-9][a-z0-9-]*:local\}$"
)

# The seven images the stack builds. The observability piece's jwks-fetch one shot shares the server's,
# because it runs that image for its Python and its CA trust.
IMAGE_VARIABLES = {
    "SERVER_IMAGE",
    "WEBAPP_IMAGE",
    "EMBEDDER_IMAGE",
    "DATA2MODEL_IMAGE",
    "LINEAGE_MODEL_IMAGE",
    "VALIDATE_ENTITY_IMAGE",
    "MCP_IMAGE",  # the front door (21.2, MCP-17)
}


@pytest.fixture(scope="module")
def services() -> dict[str, Any]:
    """The stack's compose services, the included fragments merged in."""
    return standalone_compose()["services"]


@pytest.mark.covers(rules=["SBD-11"])
def test__every_aurelius_image_names_its_compose_variable(services: dict[str, Any]) -> None:
    """No piece bakes an Aurelius image: a literal tag there cannot be re-pointed at a release build, so
    the bundle would have to edit the copy instead of setting a value (SBD-11, DD-686).
    """  # noqa: D205 - one sentence
    found = set()
    for name, service in services.items():
        image = service.get("image")
        if image is None:
            continue
        if "ghcr.io/aureliusenterprise/" not in image:
            continue  # third-party: pinned by the hardening increment, not an install's knob
        match = AURELIUS_IMAGE.match(image)
        assert match is not None, f"{name}: {image}"
        found.add(match.group("var"))
    assert found == IMAGE_VARIABLES


@pytest.mark.covers(rules=["SBD-11"])
def test__the_jwks_one_shot_moves_with_the_server(services: dict[str, Any]) -> None:
    """The JWKS fetch runs the server's image, so it names `SERVER_IMAGE`: one value moves the server and
    the one shot together, and a bundle cannot ship them from two builds (SBD-11, DD-686).
    """  # noqa: D205 - one sentence
    assert services["jwks-fetch"]["image"] == services["aurelius-atlas-server"]["image"]
