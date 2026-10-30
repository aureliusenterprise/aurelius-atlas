"""Chart-contract suite for the three aux API charts (CHT-27/28, 10.3a).

The aux apps (data2model, lineage-model, validate-entity) share one template
family, so the rules are parametrized across all three. CHT-27 pins the
per-Service leaf certificate; CHT-28 applies to lineage-model only — its two
upstream URLs are joins to the co-deployed Services (DD-251's second finding:
settings.py requires both with no defaults).
"""

from typing import Any

import pytest
from conftest import (
    AUX_CHARTS,
    env_map,
    env_value,
    find,
    helm_render,
    names,
    peer_labels,
    pod_spec,
    policy_peers_by_port,
)

AUX = sorted(AUX_CHARTS)


@pytest.fixture(scope="session", params=AUX)
def aux_docs(request: pytest.FixtureRequest) -> list[dict[str, Any]]:
    """Each aux chart at its defaults (the bare render, CHT-27)."""
    chart = AUX_CHARTS[request.param]
    return helm_render(chart, value_files=(chart / "tests/values.test.yaml",))


@pytest.mark.covers(rules=["CHT-27"])
def test__leaf_certificate_san_is_the_service_name(aux_docs: list[dict[str, Any]]) -> None:
    """One Certificate per Service; SANs are the Service name and its FQDNs."""
    service_name = _expect(aux_docs)
    assert {d["metadata"]["name"] for d in aux_docs if d["kind"] == "Service"} == {service_name}
    cert = find(aux_docs, "Certificate", service_name)
    assert cert["spec"]["dnsNames"] == [
        service_name,
        f"{service_name}.atlas",
        f"{service_name}.atlas.svc",
        f"{service_name}.atlas.svc.cluster.local",
    ]
    assert cert["spec"]["secretName"] == f"{service_name}-tls"
    assert cert["spec"]["issuerRef"]["name"] == "aurelius-atlas-selfsigned"
    # No Secret of the chart's own — cert-manager writes the leaf (CHT-22 twin).
    assert "Secret" not in {d["kind"] for d in aux_docs if d["metadata"]["name"] == f"{service_name}-tls"}


@pytest.mark.covers(rules=["CHT-27"])
def test__leaf_secret_mounted_read_only(aux_docs: list[dict[str, Any]]) -> None:
    """The whole leaf Secret rides the shared CA/TLS mount point, read-only."""
    deployment = find(aux_docs, "Deployment", _expect(aux_docs))
    volumes = {v["name"]: v for v in pod_spec(deployment)["volumes"]}
    assert volumes["tls"]["secret"]["secretName"] == f"{_expect(aux_docs)}-tls"
    mounts = {m["name"]: m for m in _app(aux_docs)["volumeMounts"]}
    assert mounts["tls"]["mountPath"] == "/etc/aurelius-atlas/tls"
    assert mounts["tls"]["readOnly"] is True


@pytest.mark.covers(rules=["CHT-27"])
def test__uid_pinned_with_fsgroup(aux_docs: list[dict[str, Any]]) -> None:
    """The dhi.io nonroot uid (65532) and fsGroup, read-only rootfs (DD-257)."""
    psc = pod_spec(find(aux_docs, "Deployment", _expect(aux_docs)))["securityContext"]
    assert psc["runAsUser"] == 65532
    assert psc["runAsNonRoot"] is True
    assert psc["fsGroup"] == 65532
    sc = _app(aux_docs)["securityContext"]
    assert sc["readOnlyRootFilesystem"] is True


def test__service_on_the_settings_port(aux_docs: list[dict[str, Any]]) -> None:
    """ClusterIP Service; the port matches the app's settings default."""
    name = _expect(aux_docs)
    service = find(aux_docs, "Service", name)
    assert service["spec"]["type"] == "ClusterIP"
    (port,) = service["spec"]["ports"]
    assert port["name"] == "https"
    assert port["port"] == port["targetPort"]


@pytest.mark.covers(rules=["CHT-28"])
def test__lineage_upstreams_are_joins(lineage_docs: list[dict[str, Any]]) -> None:
    """ATLAS_BASE_URL/DATA2MODEL_URL point at the co-deployed Services."""
    envs = env_map(_app(lineage_docs))
    assert env_value(envs, "AURELIUS_ATLAS_LINEAGE_MODEL_ATLAS_BASE_URL") == "https://atlas-server:21000/"
    assert env_value(envs, "AURELIUS_ATLAS_LINEAGE_MODEL_DATA2MODEL_URL") == "https://atlas-data2model:21001/"


@pytest.mark.covers(rules=["CHT-42"])
@pytest.mark.parametrize("component", AUX)
def test__telemetry_join_names_collector_and_public_issuer(component: str) -> None:
    """telemetry.enabled wires the per-service OTLP join (CHT-21's twin, CHT-42).

    OTEL_ENDPOINT/OTEL_TOKEN_URL/OTEL_CLIENT_SECRET exactly as the server
    chart's join: the collector's HTTP+OIDC leg, the issuer's public realm
    token URL — the same URL the browser authenticates against, resolvable
    in-cluster per DD-265 — and the shared ingest client secret.
    """
    chart = AUX_CHARTS[component]
    docs = helm_render(chart, value_files=(chart / "tests/values.test.yaml",), sets=("telemetry.enabled=true",))
    prefix = _PREFIXES[component]
    envs = env_map(_app(docs))
    assert env_value(envs, f"{prefix}OTEL_ENDPOINT") == "https://atlas-observability:4319"
    assert (
        env_value(envs, f"{prefix}OTEL_TOKEN_URL")
        == "https://keycloak.atlas.test/realms/aurelius-atlas/protocol/openid-connect/token"
    )
    secret = envs[f"{prefix}OTEL_CLIENT_SECRET"]["valueFrom"]["secretKeyRef"]
    assert secret == {"name": "atlas-otel-clients", "key": "OTEL_INGEST_CLIENT_SECRET"}


@pytest.mark.covers(rules=["CHT-42"])
@pytest.mark.parametrize("component", AUX)
def test__telemetry_off_renders_no_collector_env(component: str) -> None:
    """The default render carries no collector env (CHT-42).

    The join is opt-in and the umbrella turns it on.
    """
    chart = AUX_CHARTS[component]
    docs = helm_render(chart, value_files=(chart / "tests/values.test.yaml",))
    envs = env_map(_app(docs))
    prefix = _PREFIXES[component]
    assert f"{prefix}OTEL_ENDPOINT" not in envs
    assert f"{prefix}OTEL_CLIENT_SECRET" not in envs


_PREFIXES = {
    "data2model": "AURELIUS_ATLAS_DATA2MODEL_",
    "lineage-model": "AURELIUS_ATLAS_LINEAGE_MODEL_",
    "validate-entity": "AURELIUS_ATLAS_VALIDATE_ENTITY_",
}


@pytest.fixture(scope="session")
def lineage_docs() -> list[dict[str, Any]]:
    """lineage-model at its defaults (the CHT-28 render)."""
    chart = AUX_CHARTS["lineage-model"]
    return helm_render(chart, value_files=(chart / "tests/values.test.yaml",))


def _expect(docs: list[dict[str, Any]]) -> str:
    """The single Deployment's name (== the aux Service name)."""
    deploys = [d for d in docs if d["kind"] == "Deployment"]
    assert len(deploys) == 1
    return deploys[0]["metadata"]["name"]


def _app(docs: list[dict[str, Any]]) -> dict[str, Any]:
    """The app container (the chart names it after the short component)."""
    deployment = find(docs, "Deployment", _expect(docs))
    (app,) = pod_spec(deployment)["containers"]
    return app


@pytest.mark.covers(rules=["CHT-66"])
def test__data2model_admits_only_lineage_model() -> None:
    """21001 accepts the lineage-model join only (CHT-66)."""
    chart = AUX_CHARTS["data2model"]
    docs = helm_render(chart, value_files=(chart / "tests/values.test.yaml",))
    policy = find(docs, "NetworkPolicy", "atlas-data2model-ingress")
    assert policy["spec"]["podSelector"]["matchLabels"] == peer_labels("atlas-data2model")
    assert policy_peers_by_port(docs, "atlas-data2model-ingress") == {21001: {"atlas-lineage-model"}}


@pytest.mark.covers(rules=["CHT-66"])
def test__lineage_model_and_validate_entity_render_no_policies() -> None:
    """Nothing in the system dials them, so no allow is rendered (CHT-66).

    A policy here would be a lie about a caller that does not exist; the
    charts render zero NetworkPolicy even with the default-on gate.
    """
    for component in ("lineage-model", "validate-entity"):
        chart = AUX_CHARTS[component]
        docs = helm_render(chart, value_files=(chart / "tests/values.test.yaml",))
        assert names(docs, "NetworkPolicy") == set()
