"""Chart-contract suite for the observability chart (CHT-33..44, 10.3b).

The collector is the system's one signal seam (ADR 034); its ConfigMap is the
contract surface, so the two drift guards run here: the structural diff of the
rendered pipeline against dev/observability/config/otel-collector.yaml
(CHT-34, the DD-256 guard in structural form) and byte-identity of the four
environment-free assets (CHT-39/40). The cross-chart joins (pullers, aux
telemetry, the issuer's 443) are asserted in the files of the charts that own
them, as always.
"""

from typing import Any

import pytest
import yaml
from conftest import (
    OBS_CHART,
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

DEV_CONFIG = WORKSPACE / "dev/observability/config"
TEST_VALUES = (OBS_CHART / "tests/values.test.yaml",)
FULLNAME = "atlas-observability"


def _collector_config(docs: list[dict[str, Any]]) -> dict[str, Any]:
    """The rendered collector pipeline, parsed."""
    return yaml.safe_load(find(docs, "ConfigMap", FULLNAME)["data"]["config.yaml"])


def _dev_config() -> dict[str, Any]:
    return yaml.safe_load((DEV_CONFIG / "otel-collector.yaml").read_text())


@pytest.mark.covers(rules=["CHT-33"])
def test__collector_deployment_and_service_legs(obs_docs: list[dict[str, Any]]) -> None:
    """The collector Deployment and Service: contrib image, five ingest legs, two scrape ports (CHT-33).

    HTTP probes on the health_check port.
    """
    deployment = find(obs_docs, "Deployment", FULLNAME)
    app = container(deployment, "observability")
    assert app["image"] == "dhi.io/opentelemetry-collector:0-debian13-contrib"
    assert {p["name"]: p["containerPort"] for p in app["ports"]} == {
        "otlp-browser": 4318,
        "otlp-svc-grpc": 4317,
        "otlp-svc-http": 4319,
        "otlp-leg-grpc": 4320,
        "otlp-leg-http": 4321,
        "metrics": 9464,
        "internal": 8888,
        "health": 13133,
    }
    for probe in ("livenessProbe", "readinessProbe"):
        assert app[probe]["httpGet"] == {"path": "/", "port": "health"}

    service = find(obs_docs, "Service", FULLNAME)
    assert service["spec"]["type"] == "ClusterIP"
    assert {p["name"]: p["port"] for p in service["spec"]["ports"]} == {
        "otlp-browser": 4318,
        "otlp-svc-grpc": 4317,
        "otlp-svc-http": 4319,
        "otlp-leg-grpc": 4320,
        "otlp-leg-http": 4321,
        "metrics": 9464,
        "internal": 8888,
    }
    assert len(find_all(obs_docs, "Deployment")) == 5  # collector + four backends


@pytest.mark.covers(rules=["CHT-33"])
def test__workload_selectors_are_component_scoped(obs_docs: list[dict[str, Any]]) -> None:
    """No two workloads share a selector: each pins its component label (CHT-33).

    The chart's name/instance pair alone would let the collector adopt a
    backend's pods, and vice versa.
    """
    selectors = []
    for deployment in find_all(obs_docs, "Deployment"):
        selector = deployment["spec"]["selector"]["matchLabels"]
        assert "app.kubernetes.io/component" in selector, deployment["metadata"]["name"]
        selectors.append(frozenset(selector.items()))
    assert len(set(selectors)) == len(selectors) == 5


@pytest.mark.covers(rules=["CHT-34"])
def test__collector_pipeline_is_the_dev_shape(obs_docs: list[dict[str, Any]]) -> None:
    """The rendered pipeline matches the dev file structurally (CHT-34, DD-265/268).

    Only the named environment slots differ.
    """
    rendered, dev = _collector_config(obs_docs), _dev_config()

    assert set(rendered["receivers"]) == set(dev["receivers"])
    for name, receiver in dev["receivers"].items():
        assert rendered["receivers"][name]["protocols"] == receiver["protocols"], name
    assert set(rendered["processors"]) == set(dev["processors"])
    assert set(rendered["exporters"]) == set(dev["exporters"])
    assert rendered["service"]["pipelines"] == dev["service"]["pipelines"]
    assert set(rendered["extensions"]) == set(dev["extensions"])

    # The allowed slots: the single public-issuer provider (DD-265), the
    # chart-qualified backends, the values-named environment (DD-268), and
    # the health_check extension pinned off loopback (CHT-33).
    (provider,) = rendered["extensions"]["oidc"]["providers"]
    assert provider == {
        "issuer_url": "https://keycloak.atlas.test/realms/aurelius-atlas",
        "audience": "otel-collector",
        "issuer_ca_path": "/certs/ca.pem",
    }
    assert len(dev["extensions"]["oidc"]["providers"]) == 2  # the dual listener (DD-202)
    rendered_env = next(
        a for a in rendered["processors"]["resource"]["attributes"] if a["key"] == "deployment.environment.name"
    )
    dev_env = next(a for a in dev["processors"]["resource"]["attributes"] if a["key"] == "deployment.environment.name")
    assert rendered_env["value"] == "cluster"
    assert dev_env["value"] == "development"
    assert rendered["exporters"]["otlp_http/loki"] == {"endpoint": f"http://{FULLNAME}-loki:3100/otlp"}
    assert rendered["exporters"]["otlp_http/tempo"] == {"endpoint": f"http://{FULLNAME}-tempo:4318"}
    assert rendered["exporters"]["prometheus"] == dev["exporters"]["prometheus"]  # 0.0.0.0:9464, native histograms
    assert rendered["extensions"]["health_check"] == {"endpoint": "0.0.0.0:13133"}
    assert rendered["service"]["telemetry"] == dev["service"]["telemetry"]  # :8888 both


@pytest.mark.covers(rules=["CHT-35"])
def test__ingest_auth_as_dev_token_only_via_env(obs_docs: list[dict[str, Any]]) -> None:
    """Legs authenticate as in dev; no token material in the ConfigMap (CHT-35, R5).

    The legacy bearer arrives only as an env placeholder.
    """
    config = _collector_config(obs_docs)
    auth = {
        (receiver_name, protocol): leg["auth"]["authenticator"]
        for receiver_name, receiver in config["receivers"].items()
        for protocol, leg in receiver["protocols"].items()
    }
    assert set(auth.values()) == {"oidc", "bearertokenauth"}
    assert auth[("otlp", "http")] == "oidc"  # the browser leg
    assert auth[("otlp/services", "grpc")] == auth[("otlp/services", "http")] == "oidc"
    assert auth[("otlp/legacy", "grpc")] == auth[("otlp/legacy", "http")] == "bearertokenauth"
    assert config["extensions"]["bearertokenauth"]["tokens"] == ["${env:OTEL_COLLECTOR_INGEST_TOKEN}"]
    rendered = find(obs_docs, "ConfigMap", FULLNAME)["data"]["config.yaml"]
    assert "Bearer" not in rendered

    app = container(find(obs_docs, "Deployment", FULLNAME), "observability")
    token = env_map(app)["OTEL_COLLECTOR_INGEST_TOKEN"]["valueFrom"]["secretKeyRef"]
    assert token == {"name": "atlas-collector-legacy", "key": "token"}


@pytest.mark.covers(rules=["CHT-35"])
def test__receiver_tls_files_are_the_projected_secret_names(obs_docs: list[dict[str, Any]]) -> None:
    """Receiver TLS files are the Secret projected to dev's names (CHT-35/34).

    tls.crt/tls.key/ca.crt become otel-collector.pem, -key.pem and ca.pem.
    """
    config = _collector_config(obs_docs)
    for receiver in config["receivers"].values():
        for leg in receiver["protocols"].values():
            assert leg["tls"]["cert_file"] == "/certs/otel-collector.pem"
            assert leg["tls"]["key_file"] == "/certs/otel-collector-key.pem"
    volumes = {v["name"]: v for v in pod_spec(find(obs_docs, "Deployment", FULLNAME))["volumes"]}
    assert volumes["tls"]["secret"]["secretName"] == f"{FULLNAME}-tls"
    assert [(i["key"], i["path"]) for i in volumes["tls"]["secret"]["items"]] == [
        ("tls.crt", "otel-collector.pem"),
        ("tls.key", "otel-collector-key.pem"),
        ("ca.crt", "ca.pem"),
    ]


@pytest.mark.covers(rules=["CHT-36"])
def test__only_the_collector_has_a_certificate_with_cluster_names(obs_docs: list[dict[str, Any]]) -> None:
    """One Certificate, cluster names only (CHT-36).

    The collector is producer-facing; Grafana/Prometheus/Loki/Tempo serve
    plaintext ClusterIP.
    """
    certs = find_all(obs_docs, "Certificate")
    assert [c["metadata"]["name"] for c in certs] == [FULLNAME]
    assert certs[0]["spec"]["dnsNames"] == [
        FULLNAME,
        f"{FULLNAME}.atlas",
        f"{FULLNAME}.atlas.svc",
        f"{FULLNAME}.atlas.svc.cluster.local",
    ]
    assert not any("test" in host for host in certs[0]["spec"]["dnsNames"])  # never a browser host
    assert certs[0]["spec"]["issuerRef"]["name"] == "aurelius-atlas-selfsigned"
    for service in find_all(obs_docs, "Service"):
        assert service["spec"]["type"] == "ClusterIP", service["metadata"]["name"]


@pytest.mark.covers(rules=["CHT-37"])
def test__issuer_wait_polls_the_public_well_known(obs_docs: list[dict[str, Any]]) -> None:
    """The curl init waits for the issuer's well-known endpoint (CHT-37, DD-269).

    The Kubernetes port of the unbounded restart: the collector starts only
    once the realm answers. Busybox's wget cannot handshake Keycloak's TLS at
    all, so the boot gate ships as curl with native retry (no shell in the
    hardened image).
    """
    (init,) = pod_spec(find(obs_docs, "Deployment", FULLNAME))["initContainers"]
    assert init["name"] == "issuer-wait"
    assert init["image"] == "dhi.io/curl:8"
    command = init["command"]
    assert command[0] == "curl"
    assert "--insecure" in command  # a boot gate, not a trust decision
    assert "--retry" in command
    assert "--retry-connrefused" in command
    assert command[-1] == "https://keycloak.atlas.test/realms/aurelius-atlas/.well-known/openid-configuration"


@pytest.mark.covers(rules=["CHT-37"])
def test__issuer_wait_is_values_switchable() -> None:
    """collector.issuerWait.enabled=false drops the init container."""
    docs = helm_render(OBS_CHART, value_files=TEST_VALUES, sets=("collector.issuerWait.enabled=false",))
    assert "initContainers" not in pod_spec(find(docs, "Deployment", FULLNAME))


@pytest.mark.covers(rules=["CHT-38"])
def test__prometheus_argv_and_scrape_config_retargeted(obs_docs: list[dict[str, Any]]) -> None:
    """The compose argv + retention; five dev jobs kept with native-histogram pins (CHT-38).

    Scrape targets retargeted to the chart's Services.
    """
    deployment = find(obs_docs, "Deployment", f"{FULLNAME}-prometheus")
    app = container(deployment, "prometheus")
    assert app["args"][:1] == ["--config.file=/etc/prometheus/prometheus.yaml"]
    assert "--storage.tsdb.path=/var/prometheus" in app["args"]
    assert "--storage.tsdb.retention.time=15d" in app["args"]
    assert "--web.enable-otlp-receiver" in app["args"]
    claim = find(obs_docs, "PersistentVolumeClaim", f"{FULLNAME}-prometheus")
    assert claim["spec"]["resources"]["requests"]["storage"] == "20Gi"

    rendered = yaml.safe_load(find(obs_docs, "ConfigMap", f"{FULLNAME}-prometheus")["data"]["prometheus.yaml"])
    dev = yaml.safe_load((DEV_CONFIG / "prometheus.yaml").read_text())
    jobs = {job["job_name"]: job for job in rendered["scrape_configs"]}
    assert set(jobs) == {job["job_name"] for job in dev["scrape_configs"]}
    dev_collector = next(job for job in dev["scrape_configs"] if job["job_name"] == "otel-collector")
    assert jobs["otel-collector"]["scrape_protocols"] == dev_collector["scrape_protocols"]
    assert jobs["otel-collector"]["scrape_native_histograms"] is True
    assert [job["static_configs"][0]["targets"] for job in rendered["scrape_configs"]] == [
        [f"{FULLNAME}-prometheus:9090"],
        [f"{FULLNAME}:9464"],
        [f"{FULLNAME}:8888"],
        [f"{FULLNAME}-loki:3100"],
        [f"{FULLNAME}-tempo:3200"],
    ]


@pytest.mark.covers(rules=["CHT-38"])
def test__no_prometheus_operator_appears(obs_docs: list[dict[str, Any]]) -> None:
    """Static configs, not discovery: no Prometheus Operator (CHT-38, DD-266)."""
    assert not {"ServiceMonitor", "PodMonitor"} & {d["kind"] for d in obs_docs}


@pytest.mark.covers(rules=["CHT-39"])
@pytest.mark.parametrize("asset", ["loki.yaml", "tempo.yaml"])
def test__loki_and_tempo_config_is_a_byte_copy(obs_docs: list[dict[str, Any]], asset: str) -> None:
    """files/<asset> is byte-identical to the dev config (CHT-39, DD-256).

    The ConfigMap ships it verbatim.
    """
    cm = find(obs_docs, "ConfigMap", f"{FULLNAME}-{asset.removesuffix('.yaml')}")
    asset_bytes = (OBS_CHART / "files" / asset).read_bytes()
    assert cm["data"]["config.yaml"].encode() == asset_bytes
    assert asset_bytes == (DEV_CONFIG / asset).read_bytes()


@pytest.mark.covers(rules=["CHT-39"])
def test__loki_and_tempo_workload_shapes(obs_docs: list[dict[str, Any]]) -> None:
    """Loki/Tempo Deployment + 20Gi PVC each; Tempo's Service carries two ports (CHT-39/36).

    The collector and Grafana dial them — never the 4317 ingest shape.
    """
    for component in ("loki", "tempo"):
        find(obs_docs, "Deployment", f"{FULLNAME}-{component}")
        claim = find(obs_docs, "PersistentVolumeClaim", f"{FULLNAME}-{component}")
        assert claim["spec"]["resources"]["requests"]["storage"] == "20Gi"
    ports = {p["port"] for p in find(obs_docs, "Service", f"{FULLNAME}-tempo")["spec"]["ports"]}
    assert ports == {4318, 3200}


@pytest.mark.covers(rules=["CHT-40"])
def test__grafana_admin_recovery_join(obs_docs: list[dict[str, Any]]) -> None:
    """The <release>-grafana-admin join stays (CHT-40, DD-267).

    With the realm login as the daily door (CHT-84), the generated admin is
    account recovery — the env pair survives 10.8 unchanged.
    """
    app = container(find(obs_docs, "Deployment", f"{FULLNAME}-grafana"), "grafana")
    envs = env_map(app)
    for key, name in (("user", "GF_SECURITY_ADMIN_USER"), ("password", "GF_SECURITY_ADMIN_PASSWORD")):
        assert envs[name]["valueFrom"]["secretKeyRef"] == {"name": "atlas-grafana-admin", "key": key}
    find(obs_docs, "PersistentVolumeClaim", f"{FULLNAME}-grafana")


@pytest.mark.covers(rules=["CHT-84"])
def test__grafana_logs_in_through_the_realm(obs_docs: list[dict[str, Any]]) -> None:
    """Anonymous off, login form on, generic_oauth against the imported realm (CHT-84).

    The auth URLs derive from the same issuer/realm facts as the collector's
    OIDC receiver (CHT-74); the client secret joins from
    <release>-grafana-oauth; GF_SERVER_ROOT_URL stays unset so a
    port-forward completes the login (DD-276).
    """
    app = container(find(obs_docs, "Deployment", f"{FULLNAME}-grafana"), "grafana")
    envs = env_map(app)
    assert env_value(envs, "GF_AUTH_ANONYMOUS_ENABLED") == "false"
    assert env_value(envs, "GF_AUTH_DISABLE_LOGIN_FORM") == "false"
    assert "GF_AUTH_ANONYMOUS_ORG_ROLE" not in envs
    assert "GF_USERS_VIEWERS_CAN_EDIT" not in envs
    assert env_value(envs, "GF_AUTH_GENERIC_OAUTH_ENABLED") == "true"
    assert env_value(envs, "GF_AUTH_GENERIC_OAUTH_NAME") == "Keycloak"
    assert env_value(envs, "GF_AUTH_GENERIC_OAUTH_CLIENT_ID") == "grafana"
    assert envs["GF_AUTH_GENERIC_OAUTH_CLIENT_SECRET"]["valueFrom"]["secretKeyRef"] == {
        "name": "atlas-grafana-oauth",
        "key": "client-secret",
    }
    issuer = "https://keycloak.atlas.test/realms/aurelius-atlas/protocol/openid-connect"
    assert env_value(envs, "GF_AUTH_GENERIC_OAUTH_AUTH_URL") == f"{issuer}/auth"
    assert env_value(envs, "GF_AUTH_GENERIC_OAUTH_TOKEN_URL") == f"{issuer}/token"
    assert env_value(envs, "GF_AUTH_GENERIC_OAUTH_API_URL") == f"{issuer}/userinfo"
    assert "GF_SERVER_ROOT_URL" not in envs


@pytest.mark.covers(rules=["CHT-84"])
def test__grafana_oauth_urls_follow_the_realm_and_issuer() -> None:
    """global.realm / global.issuer.url retarget the login (CHT-74's rule)."""
    docs = helm_render(
        OBS_CHART,
        release="atlas",
        value_files=TEST_VALUES,
        sets=("global.realm=other-realm", "global.issuer.url=https://id.example/auth"),
    )
    envs = env_map(container(find(docs, "Deployment", f"{FULLNAME}-grafana"), "grafana"))
    issuer = "https://id.example/auth/realms/other-realm/protocol/openid-connect"
    assert env_value(envs, "GF_AUTH_GENERIC_OAUTH_AUTH_URL") == f"{issuer}/auth"
    assert env_value(envs, "GF_AUTH_GENERIC_OAUTH_TOKEN_URL") == f"{issuer}/token"


@pytest.mark.covers(rules=["CHT-85"])
def test__grafana_rbac_maps_grafana_client_roles(obs_docs: list[dict[str, Any]]) -> None:
    """Viewer default, editor/admin client roles escalate (CHT-85, DD-275)."""
    app = container(find(obs_docs, "Deployment", f"{FULLNAME}-grafana"), "grafana")
    envs = env_map(app)
    assert env_value(envs, "GF_AUTH_GENERIC_OAUTH_ROLE_ATTRIBUTE_PATH") == (
        'contains(resource_access.grafana.roles[*], "admin") ? "Admin" '
        ': contains(resource_access.grafana.roles[*], "editor") ? "Editor" : "Viewer"'
    )
    # The realm is the boundary: no role-list path, no org allow-list.
    assert "GF_AUTH_GENERIC_OAUTH_ROLE_LIST_PATH" not in envs
    assert "GF_AUTH_GENERIC_OAUTH_ALLOWED_ORGANIZATIONS" not in envs


@pytest.mark.covers(rules=["CHT-40"])
def test__datasources_pin_uids_and_crosslinks(obs_docs: list[dict[str, Any]]) -> None:
    """Datasource uids prometheus/loki/tempo and the cross-links (CHT-40).

    serviceMap to prometheus, tracesToLogsV2 to loki, filterByTraceID, and
    the service.name tag join.
    """
    sources = yaml.safe_load(find(obs_docs, "ConfigMap", f"{FULLNAME}-grafana-datasources")["data"]["datasources.yaml"])
    by_uid = {d["uid"]: d for d in sources["datasources"]}
    assert set(by_uid) == {"prometheus", "loki", "tempo"}
    assert by_uid["prometheus"]["url"] == f"http://{FULLNAME}-prometheus:9090"
    assert by_uid["loki"]["url"] == f"http://{FULLNAME}-loki:3100"
    assert by_uid["tempo"]["url"] == f"http://{FULLNAME}-tempo:3200"
    tempo_json = by_uid["tempo"]["jsonData"]
    assert tempo_json["serviceMap"]["datasourceUid"] == "prometheus"
    assert tempo_json["tracesToLogsV2"]["datasourceUid"] == "loki"
    assert tempo_json["tracesToLogsV2"]["filterByTraceID"] is True
    assert tempo_json["tracesToLogsV2"]["tags"] == ["service.name"]


@pytest.mark.covers(rules=["CHT-40"])
def test__grafana_assets_are_byte_copies(obs_docs: list[dict[str, Any]]) -> None:
    """Provider + all seven dashboards byte-identical to dev (CHT-40, DD-256).

    Their queries (the exported_job pins) are the contract.
    """
    provider = find(obs_docs, "ConfigMap", f"{FULLNAME}-grafana-provisioning")
    assert provider["data"]["dashboards.yaml"].encode() == (OBS_CHART / "files/grafana-dashboards.yaml").read_bytes()
    assert (OBS_CHART / "files/grafana-dashboards.yaml").read_bytes() == (
        DEV_CONFIG / "grafana/dashboards.yaml"
    ).read_bytes()

    dashboards = find(obs_docs, "ConfigMap", f"{FULLNAME}-grafana-dashboards")
    dev_dir = DEV_CONFIG / "grafana/dashboards"
    expected = sorted(path.name for path in dev_dir.glob("*.json"))
    assert sorted(dashboards["data"]) == expected
    assert len(expected) == 7
    for name in expected:
        assert dashboards["data"][name].encode() == (dev_dir / name).read_bytes()


@pytest.mark.covers(rules=["CHT-44"])
def test__every_workload_runs_as_65532_dropped_and_unprivileged(obs_docs: list[dict[str, Any]]) -> None:
    """Pod uid/fsGroup 65532 + RuntimeDefault; containers drop ALL, no escalation (DD-257, CHT-44)."""
    for deployment in find_all(obs_docs, "Deployment"):
        spec = pod_spec(deployment)
        psc = spec["securityContext"]
        assert psc["runAsNonRoot"] is True, deployment["metadata"]["name"]
        assert psc["runAsUser"] == 65532, deployment["metadata"]["name"]
        assert psc["seccompProfile"] == {"type": "RuntimeDefault"}
        for app in spec["containers"]:
            sc = app["securityContext"]
            assert sc["allowPrivilegeEscalation"] is False
            assert sc["capabilities"]["drop"] == ["ALL"]


@pytest.mark.covers(rules=["CHT-44"])
def test__no_pdbs_no_secrets_no_token_material(obs_docs: list[dict[str, Any]]) -> None:
    """No PDB and no Secrets (CHT-44, R5).

    The telemetry stack's loss degrades telemetry, never the data path.
    """
    kinds = {d["kind"] for d in obs_docs}
    assert "PodDisruptionBudget" not in kinds
    assert "Secret" not in kinds


@pytest.mark.covers(rules=["CHT-44"])
def test__bare_render_needs_no_cluster() -> None:
    """The defaults render standalone: five workloads, five Services."""
    docs = helm_render(OBS_CHART, sets=("global.domain=atlas.test",))
    assert len(names(docs, "Deployment")) == 5
    assert len(names(docs, "Service")) == 5
    assert len(names(docs, "PersistentVolumeClaim")) == 4


@pytest.mark.covers(rules=["CHT-67", "CHT-71"])
def test__collector_legs_admit_their_producers(obs_docs: list[dict[str, Any]]) -> None:
    """Each collector leg accepts exactly its producers; 13133 never (CHT-67/71)."""
    policy = find(obs_docs, "NetworkPolicy", "atlas-observability-ingress")
    assert policy["spec"]["podSelector"]["matchLabels"] == peer_labels("atlas-observability", component="observability")
    assert policy_peers_by_port(obs_docs, "atlas-observability-ingress") == {
        4318: {"atlas-webapp"},
        4317: {
            "atlas-server",
            "atlas-data2model",
            "atlas-lineage-model",
            "atlas-validate-entity",
            "atlas-elasticsearch-metrics-puller",
            "atlas-keycloak-metrics-puller",
        },
        4319: {
            "atlas-server",
            "atlas-data2model",
            "atlas-lineage-model",
            "atlas-validate-entity",
            "atlas-elasticsearch-metrics-puller",
            "atlas-keycloak-metrics-puller",
        },
        4320: {"atlas-webapp", "atlas-keycloak"},
        4321: {"atlas-webapp", "atlas-keycloak"},
        9464: {"atlas-observability"},
        8888: {"atlas-observability"},
    }
    ports = {p["port"] for r in policy["spec"]["ingress"] for p in r["ports"]}
    assert ports == {4318, 4317, 4319, 4320, 4321, 9464, 8888}  # CHT-71: no health 13133
    scrape = [
        e["podSelector"]["matchLabels"]
        for r in policy["spec"]["ingress"]
        if 9464 in [p["port"] for p in r["ports"]]
        for e in r["from"]
    ]
    assert scrape == [peer_labels("atlas-observability", component="prometheus")]


@pytest.mark.covers(rules=["CHT-68"])
def test__backends_admit_prometheus_grafana_and_the_collector(obs_docs: list[dict[str, Any]]) -> None:
    """The backend joins per CHT-68: scrape/datasource/export legs by component."""
    assert policy_peers_by_port(obs_docs, "atlas-observability-prometheus-ingress") == {
        9090: {"atlas-observability"}  # self-scrape + Grafana panels, both by component
    }
    prom = find(obs_docs, "NetworkPolicy", "atlas-observability-prometheus-ingress")
    assert prom["spec"]["podSelector"]["matchLabels"] == peer_labels("atlas-observability", component="prometheus")
    assert {
        e["podSelector"]["matchLabels"]["app.kubernetes.io/component"] for e in prom["spec"]["ingress"][0]["from"]
    } == {
        "prometheus",
        "grafana",
    }
    assert policy_peers_by_port(obs_docs, "atlas-observability-loki-ingress") == {
        3100: {"atlas-observability"}  # collector export + Prometheus scrape + Grafana datasource
    }
    loki = find(obs_docs, "NetworkPolicy", "atlas-observability-loki-ingress")
    assert {
        e["podSelector"]["matchLabels"]["app.kubernetes.io/component"] for e in loki["spec"]["ingress"][0]["from"]
    } == {
        "observability",
        "prometheus",
        "grafana",
    }
    tempo_peers = policy_peers_by_port(obs_docs, "atlas-observability-tempo-ingress")
    assert tempo_peers == {4318: {"atlas-observability"}, 3200: {"atlas-observability"}}
    tempo = find(obs_docs, "NetworkPolicy", "atlas-observability-tempo-ingress")
    ingest = next(r for r in tempo["spec"]["ingress"] if r["ports"][0]["port"] == 4318)
    assert [e["podSelector"]["matchLabels"] for e in ingest["from"]] == [
        peer_labels("atlas-observability", component="observability")
    ]
    scrape = next(r for r in tempo["spec"]["ingress"] if r["ports"][0]["port"] == 3200)
    assert {e["podSelector"]["matchLabels"]["app.kubernetes.io/component"] for e in scrape["from"]} == {
        "prometheus",
        "grafana",
    }


@pytest.mark.covers(rules=["CHT-69"])
def test__grafana_receives_no_chart_owned_allow(obs_docs: list[dict[str, Any]]) -> None:
    """No policy in this chart selects Grafana's pods (CHT-69).

    Grafana's only allow is the umbrella's gateway rule, and only when the
    host is enabled — tested there. Port-forward rides the kubelet.
    """
    grafana_targets = [
        p["metadata"]["name"]
        for p in find_all(obs_docs, "NetworkPolicy")
        if p["spec"]["podSelector"]["matchLabels"].get("app.kubernetes.io/component") == "grafana"
    ]
    assert grafana_targets == []
    # Grafana appears as a dialer of the backends (panels/datasources), never a target.
    dialers = [
        e["podSelector"]["matchLabels"]
        for p in find_all(obs_docs, "NetworkPolicy")
        for r in p["spec"].get("ingress", [])
        for e in r["from"]
        if e["podSelector"]["matchLabels"].get("app.kubernetes.io/component") == "grafana"
    ]
    assert dialers


@pytest.mark.covers(rules=["CHT-70"])
def test__puller_peers_join_by_qualified_pod_name() -> None:
    """A puller peer's name label carries the release qualifier (CHT-70)."""
    docs = helm_render(OBS_CHART, release="foo", value_files=(OBS_CHART / "tests/values.test.yaml",))
    policy = find(docs, "NetworkPolicy", "foo-atlas-observability-ingress")
    peers = [
        e["podSelector"]["matchLabels"]
        for r in policy["spec"]["ingress"]
        if r["ports"][0]["port"] == 4317
        for e in r["from"]
    ]
    assert peer_labels("foo-atlas-elasticsearch-metrics-puller", instance="foo") in peers
    assert peer_labels("foo-atlas-keycloak-metrics-puller", instance="foo") in peers
    assert peer_labels("atlas-server", instance="foo") in peers


@pytest.mark.covers(rules=["CHT-67", "CHT-72"])
def test__observability_network_policy_off_changes_nothing_else() -> None:
    """The disable switch removes the four policies and nothing else (CHT-72)."""
    on = helm_render(OBS_CHART, value_files=(OBS_CHART / "tests/values.test.yaml",))
    off = helm_render(
        OBS_CHART, value_files=(OBS_CHART / "tests/values.test.yaml",), sets=("networkPolicy.enabled=false",)
    )
    assert names(on, "NetworkPolicy") == {
        "atlas-observability-ingress",
        "atlas-observability-prometheus-ingress",
        "atlas-observability-loki-ingress",
        "atlas-observability-tempo-ingress",
    }
    assert names(off, "NetworkPolicy") == set()

    def rest(docs: list[dict[str, Any]]) -> list[tuple[str, str]]:
        return sorted((d["kind"], d["metadata"]["name"]) for d in docs if d["kind"] != "NetworkPolicy")

    assert rest(on) == rest(off)
