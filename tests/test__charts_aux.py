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
    UMBRELLA_CHART,
    WORKSPACE,
    container,
    env_map,
    env_value,
    find,
    find_all,
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


@pytest.mark.covers(rules=["CHT-42", "CHT-90"])
@pytest.mark.parametrize("component", AUX)
def test__telemetry_join_names_collector_and_public_issuer(component: str) -> None:
    """telemetry.enabled wires the per-service OTLP join (CHT-21's twin, CHT-42).

    OTEL_ENDPOINT/OTEL_TOKEN_URL/OTEL_CLIENT_SECRET exactly as the server
    chart's join: the collector's HTTP+OIDC leg, the issuer's public realm
    token URL — the same URL the browser authenticates against, resolvable
    in-cluster per DD-265 — and the ingest client secret. CHT-90 (DD-277):
    on the prod realm the join is the chart's own client key in the
    <release>-otel-clients Secret; the container-facing env name is
    unchanged.
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
    assert secret == {"name": "atlas-otel-clients", "key": _OTEL_CLIENT_IDS[component]}


@pytest.mark.covers(rules=["CHT-90", "CHT-91"])
@pytest.mark.parametrize("component", AUX)
def test__master_realm_join_falls_back_to_the_shared_key(component: str) -> None:
    """global.realm=master restores the shared ingest key on the join (CHT-90/91).

    The master hatch keeps the master asset's single shared placeholder, so
    the join reverts to OTEL_INGEST_CLIENT_SECRET.
    """
    chart = AUX_CHARTS[component]
    docs = helm_render(
        chart,
        value_files=(chart / "tests/values.test.yaml",),
        sets=("telemetry.enabled=true", "global.realm=master"),
    )
    prefix = _PREFIXES[component]
    envs = env_map(_app(docs))
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

# The ingest client each aux chart is (CHT-90): the key it joins on in the
# <release>-otel-clients Secret on a non-master realm (DD-277).
_OTEL_CLIENT_IDS = {
    "data2model": "otel-data2model",
    "lineage-model": "otel-lineage-model",
    "validate-entity": "otel-validate-entity",
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


@pytest.mark.covers(rules=["CHT-92"])
@pytest.mark.parametrize("component", AUX)
def test__image_digest_override_replaces_the_tag(component: str) -> None:
    """image.digest renders <base>@<digest> in every aux chart (CHT-92).

    Same helper family as the server chart; the field stays empty in the
    repo (CHT-94) and this is the operator override path.
    """
    chart = AUX_CHARTS[component]
    docs = helm_render(chart, value_files=(chart / "tests/values.test.yaml",), sets=(f"image.digest=sha256:{9:064d}",))
    (deployment,) = find_all(docs, "Deployment")
    (app,) = pod_spec(deployment)["containers"]
    assert app["image"] == f"ghcr.io/aureliusenterprise/aurelius-atlas-{component}@sha256:" + "0" * 63 + "9"


# The audience the e2e suites mint for (CHT-105): the public `aurelius`
# client's tokens (CHT-79) carry azp=aurelius; the minikube environment —
# nothing else — accepts them on the twins. Per-service key: the aux Service
# name, its chart container name, the audience env, and the shipped default
# audience (the settings default, DV-74/75 territory — untouched here).
_MINIKUBE_VALUES = (WORKSPACE / "helm" / "environments" / "minikube.yaml",)

_AUX_AUDIENCE = {
    "data2model": (
        "atlas-data2model",
        "data2model",
        "AURELIUS_ATLAS_DATA2MODEL_AUTH_AUDIENCE",
        "aurelius-atlas-data2model",
    ),
    "validate-entity": (
        "atlas-validate-entity",
        "validate-entity",
        "AURELIUS_ATLAS_VALIDATE_ENTITY_AUTH_AUDIENCE",
        "aurelius-atlas-validate-entity",
    ),
}


@pytest.mark.covers(rules=["CHT-105"])
@pytest.mark.parametrize("component", ["data2model", "validate-entity"])
def test__default_aux_audience_is_per_service(component: str) -> None:
    """A stock render keeps the narrow per-service audience (CHT-105: no shipped default moved)."""
    service, _, env_name, default_audience = _AUX_AUDIENCE[component]
    chart = AUX_CHARTS[component]
    docs = helm_render(chart, value_files=(chart / "tests/values.test.yaml",))
    assert find(docs, "Service", service)  # the bare-chart service name matches the umbrella's
    envs = env_map(_app(docs))
    assert env_value(envs, env_name) == default_audience


@pytest.mark.covers(rules=["CHT-105"])
@pytest.mark.parametrize("component", ["data2model", "validate-entity"])
def test__minikube_overlay_overrides_the_aux_audience(component: str) -> None:
    """The minikube environment alone carries AUTH_AUDIENCE=aurelius on the twins (CHT-105).

    The flat aux `config:` map coalesces key-by-key over the chart defaults
    (verified live), so the overlay replaces only the audience — and the
    default-render assertion above proves the shipped shape is untouched.
    """
    service, container_name, env_name, _ = _AUX_AUDIENCE[component]
    docs = helm_render(UMBRELLA_CHART, value_files=_MINIKUBE_VALUES)
    envs = env_map(container(find(docs, "Deployment", service), container_name))
    assert env_value(envs, env_name) == "aurelius", service
