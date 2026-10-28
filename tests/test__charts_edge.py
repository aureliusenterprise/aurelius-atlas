"""Chart-contract suite for the umbrella's Gateway-API edge (CHT-29..32, 10.3a).

The edge is one Gateway with one HTTPS listener per enabled browser host, one
coarse HTTPRoute per listener, and a BackendTLSPolicy only where the backend
speaks TLS (DD-242). The listener set, the SAN list on the shared edge leaf,
and the legacy collector token all follow from the same enabled flags, so the
matrix renders are the interesting part — each render here is a scenario.
"""

import base64
from typing import Any

import pytest
from conftest import (
    UMBRELLA_CHART,
    WORKSPACE,
    container,
    env_map,
    env_value,
    find,
    find_all,
    helm_render,
    helm_render_fails,
    names,
    pod_spec,
)

TEST_VALUES = (UMBRELLA_CHART / "tests/values.test.yaml",)


@pytest.mark.covers(rules=["CHT-29"])
def test__gateway_listeners_per_enabled_host(umbrella_docs: list[dict[str, Any]]) -> None:
    """One HTTPS listener per browser host; keycloak reuses its own cert."""
    gateway = find(umbrella_docs, "Gateway", "atlas")
    assert gateway["spec"]["gatewayClassName"] == "envoy-gateway"
    listeners = {lst["name"]: lst for lst in gateway["spec"]["listeners"]}
    assert set(listeners) == {"atlas", "keycloak"}
    for listener in listeners.values():
        assert listener["port"] == 443
        assert listener["protocol"] == "HTTPS"
        assert listener["allowedRoutes"]["namespaces"]["from"] == "Same"
        assert listener["tls"]["mode"] == "Terminate"
    assert listeners["atlas"]["hostname"] == "atlas.atlas.example"
    assert listeners["atlas"]["tls"]["certificateRefs"] == [{"name": "atlas-edge-tls", "kind": "Secret"}]
    # Keycloak's listener reuses the cert its own chart issues (CHT-29).
    assert listeners["keycloak"]["hostname"] == "keycloak.atlas.example"
    assert listeners["keycloak"]["tls"]["certificateRefs"] == [{"name": "atlas-keycloak-tls", "kind": "Secret"}]
    # The chart never renders a GatewayClass — it is a runbook prerequisite.
    assert "GatewayClass" not in {d["kind"] for d in umbrella_docs}


@pytest.mark.covers(rules=["CHT-29"])
def test__edge_leaf_covers_the_browser_hosts(umbrella_docs: list[dict[str, Any]]) -> None:
    """The shared edge cert's SANs: atlas here; keycloak is not (its chart owns it)."""
    cert = find(umbrella_docs, "Certificate", "atlas-edge-tls")
    assert cert["spec"]["dnsNames"] == ["atlas.atlas.example"]
    assert cert["spec"]["secretName"] == "atlas-edge-tls"
    assert cert["spec"]["issuerRef"]["name"] == "aurelius-atlas-selfsigned"


@pytest.mark.covers(rules=["CHT-29"])
def test__all_hosts_widen_listeners_and_sans() -> None:
    """Dashboard + grafana on: four listeners, three SANs on the shared leaf."""
    docs = helm_render(
        UMBRELLA_CHART,
        value_files=TEST_VALUES,
        sets=("global.hosts.dashboard.enabled=true", "global.hosts.grafana.enabled=true"),
    )
    gateway = find(docs, "Gateway", "atlas")
    assert {lst["name"] for lst in gateway["spec"]["listeners"]} == {"atlas", "keycloak", "dashboard", "grafana"}
    cert = find(docs, "Certificate", "atlas-edge-tls")
    assert cert["spec"]["dnsNames"] == ["atlas.atlas.example", "dashboard.atlas.example", "grafana.atlas.example"]
    # The shared leaf serves the non-keycloak listeners; keycloak keeps its own.
    for listener in gateway["spec"]["listeners"]:
        expected = "atlas-keycloak-tls" if listener["name"] == "keycloak" else "atlas-edge-tls"
        assert listener["tls"]["certificateRefs"][0]["name"] == expected, listener["name"]


@pytest.mark.covers(rules=["CHT-29"])
def test__disabled_component_loses_its_listener() -> None:
    """Webapp off drops the atlas listener — the keycloak-only render survives."""
    docs = helm_render(UMBRELLA_CHART, value_files=TEST_VALUES, sets=("atlas-webapp.enabled=false",))
    gateway = find(docs, "Gateway", "atlas")
    assert {lst["name"] for lst in gateway["spec"]["listeners"]} == {"keycloak"}
    assert names(docs, "HTTPRoute") == {"atlas-keycloak"}


@pytest.mark.covers(rules=["CHT-29"])
def test__gateway_off_renders_no_edge_at_all() -> None:
    """global.gateway.enabled=false: no Gateway, routes, policies, or edge cert."""
    docs = helm_render(UMBRELLA_CHART, value_files=TEST_VALUES, sets=("global.gateway.enabled=false",))
    kinds = {d["kind"] for d in docs}
    assert not {"Gateway", "HTTPRoute", "BackendTLSPolicy"} & kinds
    assert "atlas-edge-tls" not in names(docs, "Certificate")


@pytest.mark.covers(rules=["CHT-29"])
def test__gateway_without_hosts_fails_loudly() -> None:
    """An enabled Gateway with no resolvable host is a misconfiguration."""
    stderr = helm_render_fails(
        UMBRELLA_CHART,
        value_files=TEST_VALUES,
        sets=("global.hosts.atlas.enabled=false", "global.hosts.keycloak.enabled=false"),
    )
    assert "no browser host resolves" in stderr


@pytest.mark.covers(rules=["CHT-30"])
def test__one_route_per_listener_with_one_backend(umbrella_docs: list[dict[str, Any]]) -> None:
    """Each listener gets its own pinned-hostname HTTPRoute, one backend each."""
    routes = find_all(umbrella_docs, "HTTPRoute")
    assert {r["metadata"]["name"] for r in routes} == {"atlas-atlas", "atlas-keycloak"}
    for route in routes:
        (parent,) = route["spec"]["parentRefs"]
        assert parent["name"] == "atlas"
        assert parent["sectionName"] == route["metadata"]["name"].removeprefix("atlas-")
        (rule,) = route["spec"]["rules"]
        assert len(rule["backendRefs"]) == 1
    route = find(umbrella_docs, "HTTPRoute", "atlas-atlas")
    assert route["spec"]["hostnames"] == ["atlas.atlas.example"]
    assert route["spec"]["rules"][0]["backendRefs"] == [{"name": "atlas-webapp", "port": 8080}]


@pytest.mark.covers(rules=["CHT-30"])
def test__backend_tls_policies_pin_the_trusted_ca(umbrella_docs: list[dict[str, Any]]) -> None:
    """TLS backends get a BackendTLSPolicy; plaintext ones (webapp) never do."""
    policies = {p["metadata"]["name"]: p for p in find_all(umbrella_docs, "BackendTLSPolicy")}
    assert set(policies) == {"atlas-atlas-keycloak"}  # the only TLS backend on the default render
    policy = policies["atlas-atlas-keycloak"]
    (target,) = policy["spec"]["targetRefs"]
    assert target == {"group": "", "kind": "Service", "name": "atlas-keycloak"}
    assert policy["apiVersion"] == "gateway.networking.k8s.io/v1"
    assert policy["spec"]["validation"]["hostname"] == "atlas-keycloak"
    assert policy["spec"]["validation"]["caCertificateRefs"] == [
        {"group": "", "kind": "Secret", "name": "aurelius-atlas-selfsigned-ca"}
    ]


@pytest.mark.covers(rules=["CHT-30"])
def test__dashboard_route_joins_server_with_a_tls_policy() -> None:
    """The dashboard host: server backend on 21000 + a second BackendTLSPolicy."""
    docs = helm_render(UMBRELLA_CHART, value_files=TEST_VALUES, sets=("global.hosts.dashboard.enabled=true",))
    route = find(docs, "HTTPRoute", "atlas-dashboard")
    assert route["spec"]["rules"][0]["backendRefs"] == [{"name": "atlas-server", "port": 21000}]
    policies = {p["metadata"]["name"]: p for p in find_all(docs, "BackendTLSPolicy")}
    assert set(policies) == {"atlas-atlas-keycloak", "atlas-atlas-server"}
    assert policies["atlas-atlas-server"]["spec"]["targetRefs"][0]["name"] == "atlas-server"
    # grafana's route (when on) is plaintext — no policy.
    docs_g = helm_render(UMBRELLA_CHART, value_files=TEST_VALUES, sets=("global.hosts.grafana.enabled=true",))
    assert find(docs_g, "HTTPRoute", "atlas-grafana")["spec"]["rules"][0]["backendRefs"] == [
        {"name": "atlas-observability-grafana", "port": 3000}
    ]
    assert {p["metadata"]["name"] for p in find_all(docs_g, "BackendTLSPolicy")} == {"atlas-atlas-keycloak"}


@pytest.mark.covers(rules=["CHT-31"])
def test__collector_legacy_secret_keys_compose(umbrella_docs: list[dict[str, Any]]) -> None:
    """Token + otel-header = "Authorization=Bearer <token>", from one token."""
    secret = find(umbrella_docs, "Secret", "atlas-collector-legacy")
    assert set(secret["data"]) == {"token", "otel-header"}
    token = base64.b64decode(secret["data"]["token"]).decode()
    header = base64.b64decode(secret["data"]["otel-header"]).decode()
    assert len(token) == 32
    assert header == "Authorization=Bearer " + token


@pytest.mark.covers(rules=["CHT-31"])
def test__collector_legacy_gates_on_its_consumers() -> None:
    """Keycloak alone still gets the secret (the spec's consumer set is webapp OR keycloak)."""
    docs = helm_render(UMBRELLA_CHART, value_files=TEST_VALUES, sets=("atlas-webapp.enabled=false",))
    assert "atlas-collector-legacy" in names(docs, "Secret")
    # The gateway host guard would fail the render with nothing left to
    # publish, so the edge goes off too — the secret is what's under test.
    docs_both_off = helm_render(
        UMBRELLA_CHART,
        value_files=TEST_VALUES,
        sets=("atlas-webapp.enabled=false", "atlas-keycloak.enabled=false", "global.gateway.enabled=false"),
    )
    assert "atlas-collector-legacy" not in names(docs_both_off, "Secret")


@pytest.mark.covers(rules=["CHT-31"])
def test__supplied_legacy_token_wins() -> None:
    """secrets.collectorLegacy.token rides both keys verbatim."""
    docs = helm_render(UMBRELLA_CHART, value_files=TEST_VALUES, sets=("secrets.collectorLegacy.token=supplied-token",))
    secret = find(docs, "Secret", "atlas-collector-legacy")
    assert base64.b64decode(secret["data"]["token"]).decode() == "supplied-token"
    assert base64.b64decode(secret["data"]["otel-header"]).decode() == "Authorization=Bearer supplied-token"


@pytest.mark.covers(rules=["CHT-32"])
def test__environment_overlays_name_the_pod_cidrs() -> None:
    """minikube/gke overlays feed both hops: server FORWARDED_ALLOW_IPS + nginx realip."""
    for values, cidr in (
        ("helm/environments/minikube.yaml", "10.244.0.0/16"),
        ("helm/environments/gke.yaml", "10.4.0.0/14"),
    ):
        docs = helm_render(UMBRELLA_CHART, value_files=(WORKSPACE / values,))
        server_envs = env_map(container(find(docs, "Deployment", "atlas-server"), "server"))
        assert env_value(server_envs, "AURELIUS_ATLAS_SERVER_FORWARDED_ALLOW_IPS") == cidr, values
        init = next(
            c
            for c in pod_spec(find(docs, "Deployment", "atlas-webapp"))["initContainers"]
            if c["name"] == "resolve-nginx-config"
        )
        realip = env_value(env_map(init), "AURELIUS_ATLAS_WEBAPP_REALIP_BLOCK")
        assert realip == f"real_ip_header X-Forwarded-For; real_ip_recursive on; set_real_ip_from {cidr};", values
