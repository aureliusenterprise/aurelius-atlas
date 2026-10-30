"""Chart-contract suite for the server chart (CHT-20/21/22, 10.3a).

The shape the spec pins: a Deployment + ClusterIP Service on the settings
port with HTTPS probes (the server always serves TLS, SRV-06); every settings
value that names a peer is a join (store Service, generated credential
Secrets, issuer URL), never a literal; the Certificate's SANs are exactly the
names the webapp's nginx pins with proxy_ssl_name (CHT-25's twin).
"""

from typing import Any

import pytest
from conftest import (
    SERVER_CHART,
    container,
    env_map,
    env_value,
    find,
    helm_render,
    names,
    peer_labels,
    pod_spec,
    policy_peers_by_port,
)

TEST_VALUES = (SERVER_CHART / "tests/values.test.yaml",)


@pytest.mark.covers(rules=["CHT-20"])
def test__deployment_and_https_service(server_docs: list[dict[str, Any]]) -> None:
    """ClusterIP Service on the settings port; probes are HTTPS (SRV-06)."""
    service = find(server_docs, "Service", "atlas-server")
    assert service["spec"]["type"] == "ClusterIP"
    assert service["spec"]["ports"] == [{"name": "https", "port": 21000, "targetPort": 21000, "protocol": "TCP"}]
    deployment = find(server_docs, "Deployment", "atlas-server")
    assert deployment["spec"]["replicas"] == 1
    app = container(deployment, "server")
    assert app["ports"] == [{"name": "https", "containerPort": 21000, "protocol": "TCP"}]
    for probe_name, path in (
        ("readinessProbe", "/api/atlas/admin/readiness"),
        ("livenessProbe", "/api/atlas/admin/liveness"),
    ):
        probe = app[probe_name]
        assert probe["httpGet"]["scheme"] == "HTTPS", probe_name
        assert probe["httpGet"]["path"] == path
        assert probe["httpGet"]["port"] == 21000


@pytest.mark.covers(rules=["CHT-21"])
def test__settings_are_joins_not_literals(server_docs: list[dict[str, Any]]) -> None:
    """Store URL, ES password, and the CA/TLS paths all derive from peers."""
    envs = env_map(container(find(server_docs, "Deployment", "atlas-server"), "server"))
    assert env_value(envs, "AURELIUS_ATLAS_SERVER_ELASTICSEARCH_HOSTS") == '["https://atlas-elasticsearch:9200"]'
    password = envs["AURELIUS_ATLAS_SERVER_ELASTICSEARCH_PASSWORD"]["valueFrom"]["secretKeyRef"]
    assert password == {"name": "atlas-elasticsearch", "key": "elastic-password"}
    for name in (
        "AURELIUS_ATLAS_SERVER_TLS_CA_FILE",
        "AURELIUS_ATLAS_SERVER_OTEL_CA_FILE",
        "AURELIUS_ATLAS_SERVER_ELASTICSEARCH_CA_CERTS",
    ):
        assert env_value(envs, name) == "/etc/aurelius-atlas/tls/ca.crt", name
    # The leaf paths ride the Certificate's whole-Secret mount (CHT-22/27).
    assert env_value(envs, "AURELIUS_ATLAS_SERVER_TLS_CERT_FILE") == "/etc/aurelius-atlas/tls/tls.crt"
    assert env_value(envs, "AURELIUS_ATLAS_SERVER_TLS_KEY_FILE") == "/etc/aurelius-atlas/tls/tls.key"
    mount = find(server_docs, "Deployment", "atlas-server")["spec"]["template"]["spec"]["volumes"]
    tls_volume = next(v for v in mount if v["name"] == "tls")
    assert tls_volume["secret"]["secretName"] == "atlas-server-tls"


@pytest.mark.covers(rules=["CHT-21"])
def test__telemetry_join_names_collector_and_issuer() -> None:
    """telemetry.enabled wires OTEL_ENDPOINT/OTEL_TOKEN_URL/OTEL_CLIENT_SECRET."""
    docs = helm_render(SERVER_CHART, value_files=TEST_VALUES, sets=("telemetry.enabled=true",))
    envs = env_map(container(find(docs, "Deployment", "atlas-server"), "server"))
    assert env_value(envs, "AURELIUS_ATLAS_SERVER_OTEL_ENDPOINT") == "https://atlas-observability:4319"
    assert (
        env_value(envs, "AURELIUS_ATLAS_SERVER_OTEL_TOKEN_URL")
        == "https://keycloak.atlas.test/realms/master/protocol/openid-connect/token"
    )
    client_secret = envs["AURELIUS_ATLAS_SERVER_OTEL_CLIENT_SECRET"]["valueFrom"]["secretKeyRef"]
    assert client_secret == {"name": "atlas-otel-clients", "key": "OTEL_INGEST_CLIENT_SECRET"}
    assert env_value(envs, "AURELIUS_ATLAS_SERVER_OTEL_CLIENT_ID") == "otel-atlas-server"


@pytest.mark.covers(rules=["CHT-21"])
def test__telemetry_off_renders_no_collector_env(server_docs: list[dict[str, Any]]) -> None:
    """The default render carries no OTEL_ENDPOINT — telemetry is opt-in."""
    envs = env_map(container(find(server_docs, "Deployment", "atlas-server"), "server"))
    assert "AURELIUS_ATLAS_SERVER_OTEL_ENDPOINT" not in envs
    assert "AURELIUS_ATLAS_SERVER_OTEL_CLIENT_SECRET" not in envs


@pytest.mark.covers(rules=["CHT-21"])
def test__image_uid_pinned_with_fsgroup(server_docs: list[dict[str, Any]]) -> None:
    """The dhi.io python nonroot uid (65532), no privilege (DD-257)."""
    psc = pod_spec(find(server_docs, "Deployment", "atlas-server"))["securityContext"]
    assert psc["runAsUser"] == 65532
    assert psc["runAsNonRoot"] is True
    assert psc["fsGroup"] == 65532
    sc = container(find(server_docs, "Deployment", "atlas-server"), "server")["securityContext"]
    assert sc["readOnlyRootFilesystem"] is True
    assert sc["allowPrivilegeEscalation"] is False


@pytest.mark.covers(rules=["CHT-22"])
def test__certificate_sans_are_the_service_names(server_docs: list[dict[str, Any]]) -> None:
    """The Service name and FQDN forms — nginx's proxy_ssl_name target."""
    cert = find(server_docs, "Certificate", "atlas-server")
    assert cert["spec"]["secretName"] == "atlas-server-tls"
    assert cert["spec"]["dnsNames"] == [
        "atlas-server",
        "atlas-server.atlas",
        "atlas-server.atlas.svc",
        "atlas-server.atlas.svc.cluster.local",
    ]
    assert cert["spec"]["issuerRef"]["name"] == "aurelius-atlas-selfsigned"


@pytest.mark.covers(rules=["CHT-22"])
def test__no_password_renders_anywhere(server_docs: list[dict[str, Any]]) -> None:
    """Secrets are refs; the render carries no credential material."""
    assert not any(d["kind"] == "Secret" for d in server_docs)
    text = str(server_docs)
    assert "password:" not in text  # refs only carry key names, e.g. elastic-password


@pytest.mark.covers(rules=["CHT-65"])
def test__server_admits_webapp_and_lineage_model(server_docs: list[dict[str, Any]]) -> None:
    """21000 accepts the webapp proxy and the lineage-model join only (CHT-65)."""
    policy = find(server_docs, "NetworkPolicy", "atlas-server-ingress")
    assert policy["spec"]["podSelector"]["matchLabels"] == peer_labels("atlas-server")
    assert policy_peers_by_port(server_docs, "atlas-server-ingress") == {21000: {"atlas-webapp", "atlas-lineage-model"}}


@pytest.mark.covers(rules=["CHT-65", "CHT-72"])
def test__server_network_policy_off_changes_nothing_else() -> None:
    """The disable switch removes the policy and nothing else (CHT-72's chart half)."""
    on = helm_render(SERVER_CHART, value_files=TEST_VALUES)
    off = helm_render(SERVER_CHART, value_files=TEST_VALUES, sets=("networkPolicy.enabled=false",))
    assert "atlas-server-ingress" in names(on, "NetworkPolicy")
    assert names(off, "NetworkPolicy") == set()

    def rest(docs: list[dict[str, Any]]) -> list[tuple[str, str]]:
        return sorted((d["kind"], d["metadata"]["name"]) for d in docs if d["kind"] != "NetworkPolicy")

    assert rest(on) == rest(off)
