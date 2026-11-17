"""The standalone stack's embedder (EMB-11, 11.2) and the server embedding through it (VEC-11, 11.3).

The stack's compose is read as written, the umbrella and the embedder's fragment merged as compose
merges them (ADR 065): the service, its certificate, and what it does not have.
"""

from typing import Any

import pytest
import yaml
from conftest import WORKSPACE, standalone_compose

FRAGMENT = WORKSPACE / "apps/aurelius-atlas-embedder/docker"
EMBEDDER_CERTS = WORKSPACE / "apps/aurelius-atlas-embedder/certs"


@pytest.fixture(scope="module")
def services() -> dict[str, Any]:
    """The stack's compose services, the included fragments merged in."""
    return standalone_compose()["services"]


@pytest.mark.covers(rules=["EMB-11"])
def test__the_embedder_runs_on_the_stack_network_with_no_published_port(services: dict[str, Any]) -> None:
    """Only the stack's network reaches it: no ports, no other network mode (DD-432)."""
    embedder = services["embedder"]

    # The image is an install's knob over the nx docker-build default (the stack builds, never pulls).
    assert embedder["image"] == "${EMBEDDER_IMAGE:-ghcr.io/aureliusenterprise/aurelius-atlas-embedder:local}"
    assert "ports" not in embedder
    assert "network_mode" not in embedder
    assert "networks" not in embedder


@pytest.mark.covers(rules=["EMB-11"])
def test__the_embedder_serves_tls_with_its_own_certificate(services: dict[str, Any]) -> None:
    """Its certificate is the embedder project's, mounted read-only; the SANs name the stack's service."""
    embedder = services["embedder"]

    # The certificate folder is an install's knob over this project's certgen folder; a relative
    # value still reads from the fragment's folder, like the default it carries.
    assert embedder["volumes"] == ["${EMBEDDER_CERTS_DIR:-../certs}:/certs:ro"]
    assert embedder["environment"] == {
        "AURELIUS_ATLAS_EMBEDDER_TLS_CERT_FILE": "/certs/aurelius-atlas-embedder.pem",
        "AURELIUS_ATLAS_EMBEDDER_TLS_KEY_FILE": "/certs/aurelius-atlas-embedder-key.pem",
        "AURELIUS_ATLAS_EMBEDDER_TLS_CA_FILE": "/certs/ca.pem",
    }
    tls = yaml.safe_load((WORKSPACE / "apps/aurelius-atlas-embedder/tls.json").read_text())
    assert "embedder" in tls["services"]["aurelius-atlas-embedder"]
    assert (FRAGMENT / "../certs").resolve() == EMBEDDER_CERTS


@pytest.mark.covers(rules=["EMB-11"])
def test__no_service_of_the_stack_waits_for_the_embedder(services: dict[str, Any]) -> None:
    """The stack starts as without it."""
    for name, service in services.items():
        assert "embedder" not in (service.get("depends_on") or {}), name


@pytest.mark.covers(rules=["VEC-11"])
def test__the_server_embeds_through_the_stack_s_embedder(services: dict[str, Any]) -> None:
    """Its URL on the stack network, trusting the stack's CA; the server does not wait for it."""
    server = services["aurelius-atlas-server"]

    assert server["environment"]["AURELIUS_ATLAS_SERVER_EMBEDDING_URL"] == "https://embedder:21004"
    assert server["environment"]["AURELIUS_ATLAS_SERVER_EMBEDDING_CA_FILE"] == "/certs/ca.pem"
    assert "embedder" not in server["depends_on"]
