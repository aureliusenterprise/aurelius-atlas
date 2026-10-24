"""Unit tests for the route factories: the routers the composition root mounts (VE-01, VE-03, VE-04)."""

import pytest
from aurelius_atlas_auth import KeycloakAuth
from aurelius_atlas_validate_entity.routes import HEALTH, build_router
from aurelius_atlas_validate_entity.routes.health import liveness
from aurelius_atlas_validate_entity.routes.validate import VALIDATE
from fastapi import APIRouter
from fastapi.routing import APIRoute


def _routes(router: APIRouter) -> list[APIRoute]:
    """The router's routes, typed: the factories build only APIRoutes."""
    return [route for route in router.routes if isinstance(route, APIRoute)]


@pytest.mark.covers("aurelius_atlas_validate_entity.routes.build_router", rules=["VE-01", "VE-03"])
def test__the_validate_router_carries_the_endpoint_and_its_gate(auth: KeycloakAuth) -> None:
    """One POST / on the validate tag, guarded by the verifier's auth dependency (VE-03)."""
    (route,) = _routes(build_router(auth))

    assert route.path == "/"
    assert sorted(route.methods or ()) == ["POST"]
    assert build_router(auth).tags == [VALIDATE]
    assert route.dependant.dependencies  # the gate rides the route


@pytest.mark.covers("aurelius_atlas_validate_entity.routes.build_router", rules=["VE-03"])
def test__the_gate_is_the_injected_verifier(auth: KeycloakAuth) -> None:
    """The router guards with the verifier it is given — the composition root's, not its own (DD-112)."""
    (route,) = _routes(build_router(auth))
    gates = {str(dependency.call) for dependency in route.dependant.dependencies}

    assert any("KeycloakAuth.user_info" in gate for gate in gates)


@pytest.mark.covers("aurelius_atlas_validate_entity.routes.health.liveness", rules=["VE-04"])
def test__the_health_router_is_the_anonymous_liveness_check() -> None:
    """The container healthcheck: GET /liveness answers 204, with no dependency to verify (VE-04, DV-59)."""
    (route,) = _routes(HEALTH)

    assert route.path == "/liveness"
    assert route.status_code == 204
    assert not route.dependant.dependencies  # anonymous, as the Dockerfile's healthcheck calls it
    assert liveness() is None  # the handler's answer is the status alone
