"""The standalone stack's embedder (EMB-11, 11.2).

The compose file is read as written: the service, its certificate, and what it does not have.
"""

from typing import Any

import pytest
import yaml
from conftest import WORKSPACE

STANDALONE = WORKSPACE / "apps/aurelius-atlas-server/standalone"
EMBEDDER_CERTS = WORKSPACE / "apps/aurelius-atlas-embedder/certs"


@pytest.fixture(scope="module")
def services() -> dict[str, Any]:
    """The stack's compose services."""
    return yaml.safe_load((STANDALONE / "docker-compose.yaml").read_text())["services"]


@pytest.mark.covers(rules=["EMB-11"])
def test__the_embedder_runs_on_the_stack_network_with_no_published_port(services: dict[str, Any]) -> None:
    """Only the stack's network reaches it: no ports, no other network mode (DD-432)."""
    embedder = services["embedder"]

    assert embedder["image"] == "ghcr.io/aureliusenterprise/aurelius-atlas-embedder:local"
    assert "ports" not in embedder
    assert "network_mode" not in embedder
    assert "networks" not in embedder


@pytest.mark.covers(rules=["EMB-11"])
def test__the_embedder_serves_tls_with_its_own_certificate(services: dict[str, Any]) -> None:
    """Its certificate is the embedder project's, mounted read-only; the SANs name the stack's service."""
    embedder = services["embedder"]

    assert embedder["volumes"] == ["../../aurelius-atlas-embedder/certs:/certs:ro"]
    assert embedder["environment"] == {
        "AURELIUS_ATLAS_EMBEDDER_TLS_CERT_FILE": "/certs/aurelius-atlas-embedder.pem",
        "AURELIUS_ATLAS_EMBEDDER_TLS_KEY_FILE": "/certs/aurelius-atlas-embedder-key.pem",
        "AURELIUS_ATLAS_EMBEDDER_TLS_CA_FILE": "/certs/ca.pem",
    }
    tls = yaml.safe_load((WORKSPACE / "apps/aurelius-atlas-embedder/tls.json").read_text())
    assert "embedder" in tls["services"]["aurelius-atlas-embedder"]
    assert (STANDALONE / "../../aurelius-atlas-embedder/certs").resolve() == EMBEDDER_CERTS


@pytest.mark.covers(rules=["EMB-11"])
def test__no_service_of_the_stack_waits_for_the_embedder(services: dict[str, Any]) -> None:
    """The stack starts as without it."""
    for name, service in services.items():
        assert "embedder" not in (service.get("depends_on") or {}), name
