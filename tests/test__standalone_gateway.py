"""The standalone stack's gateway piece (IRT-12, DD-677).

The umbrella names the project and includes every piece, holding no service of its own; the
gateway's piece owns the proxy, the stack's only published port, and its nginx config sits
beside it. The suite reads the compose as written, the umbrella with its fragments merged as
compose merges it (DD-671).
"""

from typing import Any

import pytest
from conftest import WORKSPACE, compose_load, standalone_compose

STACK = WORKSPACE / "docker"


@pytest.fixture(scope="module")
def services() -> dict[str, Any]:
    """The stack's compose services, the included fragments merged in."""
    return standalone_compose()["services"]


@pytest.mark.covers(rules=["IRT-12"])
def test__the_umbrella_includes_the_gateway_and_holds_no_service() -> None:
    """The umbrella's own services are empty and the gateway joins the include list (IRT-12)."""
    umbrella = compose_load(STACK / "docker-compose.yaml")
    assert not umbrella.get("services"), "the umbrella holds no service of its own (DD-677)"
    included = {entry["path"] for entry in umbrella.get("include") or ()}
    assert "gateway/compose.yaml" in included


@pytest.mark.covers(rules=["IRT-12"])
def test__the_gateway_piece_owns_the_stacks_only_published_port(services: dict[str, Any]) -> None:
    """The proxy publishes loopback 9000 and mounts its rendered nginx config and the server's
    certificates; the one shot renders the config and the browser's config.json from the pieces
    beside it (IRT-12, DD-677; 17.2's gateway-config).
    """  # noqa: D205 - one sentence
    gateway = compose_load(STACK / "gateway/compose.yaml")["services"]["proxy"]
    proxy = services["proxy"]
    assert proxy["image"] == "dhi.io/nginx:1.30-alpine3.24"
    assert proxy["ports"] == ["127.0.0.1:9000:9000"]
    # The rendered config volume replaced the direct nginx.conf bind (17.2, SPS-02); the one shot
    # reads the config and the webapp's config.json from beside it.
    assert "gateway-conf:/etc/nginx/conf.d:ro" in gateway["volumes"]
    # The edge leaf is the server's, named through the gateway's own required knob (DD-687).
    assert "${GATEWAY_CERTS_DIR:?name the gateway certificate folder}:/certs:ro" in gateway["volumes"]
    render = services["gateway-config"]
    assert "docker/gateway/nginx.conf:/template/nginx.conf:ro" in render["volumes"]
    assert "apps/aurelius-atlas-webapp/docker/config.json:/template/config.json:ro" in render["volumes"]
    assert proxy["depends_on"]["gateway-config"] == {"condition": "service_completed_successfully"}
    # The proxy is the app surface's only host publish; the four observability backends keep
    # their inherited loopback views (DD-675), and the collector's publish is reset.
    published = {name for name, service in services.items() if service.get("ports")}
    assert published - {"prometheus", "loki", "tempo", "grafana"} == {"proxy"}
