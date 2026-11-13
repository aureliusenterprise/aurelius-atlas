"""Unit tests for the route factories: the routers the composition root mounts (DTM-01, DTM-10)."""

import pytest
from aurelius_atlas_auth import KeycloakAuth
from aurelius_atlas_data2model.routes import HEALTH, build_router
from aurelius_atlas_data2model.routes.extract import EXTRACT
from aurelius_atlas_data2model.routes.health import liveness
from aurelius_atlas_data2model_client.models import ExtractionResponse
from fastapi import APIRouter
from fastapi.routing import APIRoute


def _routes(router: APIRouter) -> list[APIRoute]:
    """The router's routes, typed: the factories build only APIRoutes."""
    return [route for route in router.routes if isinstance(route, APIRoute)]


@pytest.mark.covers("aurelius_atlas_data2model.routes.build_router", rules=["DTM-01", "DTM-10"])
def test__the_extract_router_carries_the_endpoint_and_its_gate(auth: KeycloakAuth) -> None:
    """One POST /extract on the extract tag, guarded by the verifier's auth dependency (DTM-10)."""
    (route,) = _routes(build_router(auth))

    assert route.path == "/extract"
    assert sorted(route.methods or ()) == ["POST"]
    assert build_router(auth).tags == [EXTRACT]
    # Since 8.23 the answer's model is declared for the OpenAPI document (AUX-06); the route
    # returns a Response, so FastAPI never serialises through it and the bytes stay verbatim (CL-50).
    assert route.response_model is ExtractionResponse
    assert route.dependant.dependencies  # the gate rides the route


@pytest.mark.covers("aurelius_atlas_data2model.routes.build_router", rules=["DTM-10"])
def test__the_gate_is_the_injected_verifier(auth: KeycloakAuth) -> None:
    """The router guards with the verifier it is given — the composition root's, not its own (DD-200)."""
    (route,) = _routes(build_router(auth))
    gates = {str(dependency.call) for dependency in route.dependant.dependencies}

    assert any("KeycloakAuth.user_info" in gate for gate in gates)


@pytest.mark.covers("aurelius_atlas_data2model.routes.health.liveness", rules=["DTM-10"])
def test__the_health_router_is_the_anonymous_liveness_check() -> None:
    """The container healthcheck: GET /liveness answers 204, with no dependency to verify."""
    (route,) = _routes(HEALTH)

    assert route.path == "/liveness"
    assert route.status_code == 204
    assert not route.dependant.dependencies  # anonymous, as the Dockerfile's healthcheck calls it
    assert liveness() is None  # the handler's answer is the status alone
