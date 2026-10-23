"""Unit tests for the route factories: the routers the composition root mounts (LM-01, LM-08, LM-09)."""

import pytest
from aurelius_atlas_auth import KeycloakAuth
from aurelius_atlas_lineage_model.routes import HEALTH, build_router
from aurelius_atlas_lineage_model.routes.health import liveness
from aurelius_atlas_lineage_model.routes.lineage import LINEAGE
from fastapi import APIRouter
from fastapi.routing import APIRoute


def _routes(router: APIRouter) -> list[APIRoute]:
    """The router's routes, typed: the factories build only APIRoutes."""
    return [route for route in router.routes if isinstance(route, APIRoute)]


@pytest.mark.covers("aurelius_atlas_lineage_model.routes.build_router", rules=["LM-01", "LM-08"])
def test__the_lineage_router_carries_the_endpoint_and_its_gate(auth: KeycloakAuth) -> None:
    """One GET / on the lineage tag, guarded by the verifier's auth dependency (LM-08)."""
    (route,) = _routes(build_router(auth))

    assert route.path == "/"
    assert sorted(route.methods or ()) == ["GET"]
    assert build_router(auth).tags == [LINEAGE]
    assert route.response_model is None  # the answer is built by hand, verbatim (LM-01)
    assert route.dependant.dependencies  # the gate rides the route


@pytest.mark.covers("aurelius_atlas_lineage_model.routes.build_router", rules=["LM-08"])
def test__the_gate_is_the_injected_verifier(auth: KeycloakAuth) -> None:
    """The router guards with the verifier it is given — the composition root's, not its own (DD-111)."""
    (route,) = _routes(build_router(auth))
    gates = {str(dependency.call) for dependency in route.dependant.dependencies}

    assert any("KeycloakAuth.user_info" in gate for gate in gates)


@pytest.mark.covers("aurelius_atlas_lineage_model.routes.health.liveness", rules=["LM-09"])
def test__the_health_router_is_the_anonymous_liveness_check() -> None:
    """The container healthcheck: GET /liveness answers 204, with no dependency to verify (LM-09)."""
    (route,) = _routes(HEALTH)

    assert route.path == "/liveness"
    assert route.status_code == 204
    assert not route.dependant.dependencies  # anonymous, as the Dockerfile's healthcheck calls it
    assert liveness() is None  # the handler's answer is the status alone
