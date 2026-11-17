"""The standalone stack's telemetry (IRT-11, 17.1, DD-675).

The collector, Prometheus, Loki, Tempo and Grafana join the umbrella as the stack's own piece,
extending the infra observability slice (ADR 066). The piece's one fork is the collector's
configuration: the OIDC validator reads the stack realm's keys from a file, because the stack's
issuer is the proxy's browser address. The suite reads the compose as written, the realm as
imported, and the resolver script as shipped.
"""

import json
from typing import Any

import pytest
import yaml
from conftest import WORKSPACE, compose_load, standalone_compose

STACK = WORKSPACE / "docker"
SLICE_COMPOSE = WORKSPACE / "infra/observability/docker-compose.yaml"
SLICE_CONFIG = WORKSPACE / "infra/observability/config/otel-collector.yaml"
STACK_CONFIG = STACK / "observability/config/otel-collector.yaml"
SERVER_TOKEN_URL = "https://localhost:9000/auth/realms/aurelius-atlas/protocol/openid-connect/token"  # noqa: S105  # a URL constant, not a secret


@pytest.fixture(scope="module")
def services() -> dict[str, Any]:
    """The stack's compose services, the included fragments merged in."""
    return standalone_compose()["services"]


@pytest.mark.covers(rules=["IRT-11"])
def test__the_umbrella_includes_the_observability_piece_always_on(services: dict[str, Any]) -> None:
    """A plain `up -d` brings the whole system with its telemetry: the five backends and the JWKS
    fetch, none behind a profile (IRT-11).
    """  # noqa: D205 - one sentence
    umbrella = compose_load(STACK / "docker-compose.yaml")
    included = {entry["path"] for entry in umbrella.get("include") or ()}
    assert "observability/compose.yaml" in included
    for entry in umbrella.get("include") or ():
        assert "profiles" not in entry, entry["path"]
    for name in ("otel-collector", "prometheus", "loki", "tempo", "grafana", "jwks-fetch"):
        assert name in services, name


@pytest.mark.covers(rules=["IRT-11"])
def test__the_stack_collector_extends_the_slice_and_keeps_the_publish_off(
    services: dict[str, Any],
) -> None:
    """The collector's image, restart pattern and certificates' mount are the slice's (the leaf's
    SANs name otel-collector); the stack swaps in its own config and starts only after the realm's
    keys landed (IRT-11, DD-675).
    """  # noqa: D205 - one sentence
    collector = services["otel-collector"]
    base = yaml.safe_load(SLICE_COMPOSE.read_text())["services"]["otel-collector"]
    assert collector["image"] == base["image"]
    assert collector["restart"] == base["restart"]
    # conftest spells rebased bind sources workspace-relative (DD-671): the config is the stack's,
    # the certificates' mount stays the slice's.
    assert "docker/observability/config/otel-collector.yaml:/etc/otelcol-contrib/config.yaml:ro" in collector["volumes"]
    assert "jwks-data:/jwks:ro" in collector["volumes"]
    assert "infra/observability/certs:/certs:ro" in collector["volumes"]
    # No host publish: the producers ride the stack's network, not the machine's loopback.
    assert "ports" not in collector
    assert collector["depends_on"]["jwks-fetch"] == {"condition": "service_completed_successfully"}
    fetch = services["jwks-fetch"]
    assert fetch["image"] == services["aurelius-atlas-server"]["image"]
    assert (
        fetch["environment"]["JWKS_URL"]
        == "http://keycloak:8080/auth/realms/aurelius-atlas/protocol/openid-connect/certs"
    )


@pytest.mark.covers(rules=["IRT-11"])
def test__the_stack_collector_validates_the_stacks_issuer_from_a_file() -> None:
    """The slice's validator dials the dev Keycloak's published listeners; the stack's reads one
    issuer - the proxy's browser address, undialable from inside - from the fetched JWKS file
    (IRT-11, DD-675).
    """  # noqa: D205 - one sentence
    providers = yaml.safe_load(STACK_CONFIG.read_text())["extensions"]["oidc"]["providers"]
    assert providers == [
        {
            "issuer_url": "https://localhost:9000/auth/realms/aurelius-atlas",
            "audience": "otel-collector",
            "public_keys_file": "/jwks/jwks.json",
        }
    ]
    slice_providers = yaml.safe_load(SLICE_CONFIG.read_text())["extensions"]["oidc"]["providers"]
    assert not any("public_keys_file" in provider for provider in slice_providers)


@pytest.mark.covers(rules=["IRT-11"])
def test__every_producer_signs_for_the_stacks_collector(services: dict[str, Any]) -> None:
    """The server and the three aux apps mint through the stack's issuer for the per-service leg
    (:4319), Keycloak and the webapp's edge carry the shared bearer to the legacy leg (:4320), and
    the realm carries the four ingest clients plus the browser's audience scope - every secret
    unguarded in a piece, so a stack without telemetry still starts (IRT-11, DD-196, DD-675).
    """  # noqa: D205 - one sentence
    for name in (
        "aurelius-atlas-server",
        "aurelius-atlas-data2model",
        "aurelius-atlas-lineage-model",
        "aurelius-atlas-validate-entity",
    ):
        env = services[name]["environment"]
        prefix = name.upper().replace("-", "_")
        assert env[f"{prefix}_OTEL_TOKEN_URL"] == SERVER_TOKEN_URL, name
        assert env[f"{prefix}_OTEL_ENDPOINT"] == "https://otel-collector:4319", name
        assert env[f"{prefix}_OTEL_CLIENT_SECRET"] == "${OTEL_INGEST_CLIENT_SECRET:-}", name
    keycloak = services["keycloak"]
    assert keycloak["environment"]["OTEL_EXPORTER_OTLP_ENDPOINT"] == "https://otel-collector:4320"
    webapp = services["webapp-config"]["environment"]
    assert webapp["AURELIUS_ATLAS_WEBAPP_OTLP_ENDPOINT"] == "https://otel-collector:4320"
    realm = json.loads((STACK / "keycloak/aurelius-atlas.json").read_text())
    clients = {client["clientId"]: client for client in realm["clients"]}
    for client_id in ("otel-atlas-server", "otel-data2model", "otel-lineage-model", "otel-validate-entity"):
        ingest = clients[client_id]
        assert ingest["secret"] == "${OTEL_INGEST_CLIENT_SECRET}", client_id  # noqa: S105  # the placeholder, not a secret
        assert (ingest["serviceAccountsEnabled"], ingest["standardFlowEnabled"]) == (True, False), client_id
        assert "otel-ingest" in ingest["defaultClientScopes"], client_id
    assert "otel-ingest" in clients["aurelius"]["defaultClientScopes"]
    scope = next(s for s in realm["clientScopes"] if s["name"] == "otel-ingest")
    mapper = scope["protocolMappers"][0]["config"]
    assert mapper["included.custom.audience"] == "otel-collector"
