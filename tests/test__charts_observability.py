"""Chart-contract suite for the observability chart (CHT-33..44, 10.3b).

The collector is the system's one signal seam (ADR 034); its ConfigMap is the
contract surface, so the two drift guards run here: the structural diff of the
rendered pipeline against infra/observability/config/otel-collector.yaml
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
    pinned_ref,
    pod_spec,
    policy_peers_by_port,
)

DEV_CONFIG = WORKSPACE / "infra/observability/config"
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
    assert app["image"] == pinned_ref("dhi.io/opentelemetry-collector")  # CHT-93
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
        "issuer_url": "https://auth.atlas.test/realms/aurelius-atlas",
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
    # CHT-134 (DD-655): every egress rides TLS — the backends are CA-pinned
    # clients, the prometheus exporter is a TLS server. Dev's egress stays
    # plaintext (a named deviation: the compose carries no mesh CA), so
    # every other exporter key stays dev's exactly.
    assert rendered["exporters"]["otlp_http/loki"] == {
        "endpoint": f"https://{FULLNAME}-loki:3100/otlp",
        "tls": {"ca_file": "/certs/ca.pem"},
    }
    assert rendered["exporters"]["otlp_http/tempo"] == {
        "endpoint": f"https://{FULLNAME}-tempo:4318",
        "tls": {"ca_file": "/certs/ca.pem"},
    }
    rendered_prom, dev_prom = rendered["exporters"]["prometheus"], dev["exporters"]["prometheus"]
    assert rendered_prom["tls"] == {
        "cert_file": "/certs/otel-collector.pem",
        "key_file": "/certs/otel-collector-key.pem",
    }
    assert {k: v for k, v in rendered_prom.items() if k != "tls"} == dev_prom  # 0.0.0.0:9464, native histograms
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


@pytest.mark.covers(rules=["CHT-36", "CHT-134"])
def test__the_mesh_serves_tls_with_cluster_names_only(obs_docs: list[dict[str, Any]]) -> None:
    """Four Certificates — the collector plus the three backends — cluster names only (CHT-36, DD-655).

    Every internal hop verifies against the trust root. No leaf carries a
    browser host: the collector is producer-facing and the backends are
    cluster-internal reads; Grafana's browser-facing leaf is the umbrella's
    edge cert, never one here. tls.secretName / tls.componentSecrets bring
    your own leaves and drop the matching Certificate.
    """
    by_name = {c["metadata"]["name"]: c for c in find_all(obs_docs, "Certificate")}
    assert set(by_name) == {FULLNAME, f"{FULLNAME}-loki", f"{FULLNAME}-tempo", f"{FULLNAME}-prometheus"}
    for name, cert in by_name.items():
        assert cert["spec"]["dnsNames"] == [  # the cert names its own component Service
            name,
            f"{name}.atlas",
            f"{name}.atlas.svc",
            f"{name}.atlas.svc.cluster.local",
        ], name
        assert not any("test" in host for host in cert["spec"]["dnsNames"]), name  # never a browser host
        assert cert["spec"]["issuerRef"]["name"] == "aurelius-atlas-selfsigned", name
        assert cert["spec"]["secretName"] == f"{name}-tls", name
    for service in find_all(obs_docs, "Service"):
        assert service["spec"]["type"] == "ClusterIP", service["metadata"]["name"]


@pytest.mark.covers(rules=["CHT-134"])
def test__brought_leaves_drop_the_matching_certificates() -> None:
    """tls.secretName and tls.componentSecrets are per-leaf BYO switches (CHT-134)."""
    docs = helm_render(
        OBS_CHART,
        value_files=TEST_VALUES,
        sets=("tls.secretName=byo-collector", "tls.componentSecrets.loki=byo-loki"),
    )
    assert names(docs, "Certificate") == {f"{FULLNAME}-tempo", f"{FULLNAME}-prometheus"}
    volumes = {v["name"]: v for v in pod_spec(find(docs, "Deployment", f"{FULLNAME}-loki"))["volumes"]}
    assert volumes["tls"]["secret"]["secretName"] == "byo-loki"


@pytest.mark.covers(rules=["CHT-134"])
def test__backends_mount_their_leaf_and_probe_https(obs_docs: list[dict[str, Any]]) -> None:
    """Each backend mounts its own leaf at tls.mountPath and probes over HTTPS (CHT-134).

    The kubelet does not verify the chain, so a private-CA server needs no
    probe secret. Grafana keeps HTTP probes: its UI stays plaintext and the
    edge terminates TLS in front of it (DD-653).
    """
    for component in ("loki", "tempo", "prometheus"):
        deployment = find(obs_docs, "Deployment", f"{FULLNAME}-{component}")
        app = container(deployment, component)
        for probe in ("livenessProbe", "readinessProbe"):
            assert app[probe]["httpGet"]["scheme"] == "HTTPS", (component, probe)
        volumes = {v["name"]: v for v in pod_spec(deployment)["volumes"]}
        assert volumes["tls"]["secret"]["secretName"] == f"{FULLNAME}-{component}-tls", component
        mounts = {m["name"]: m["mountPath"] for m in app["volumeMounts"]}
        assert mounts["tls"] == "/certs", component
    grafana = container(find(obs_docs, "Deployment", f"{FULLNAME}-grafana"), "grafana")
    assert grafana["readinessProbe"]["httpGet"].get("scheme", "HTTP") == "HTTP"


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
    assert init["image"] == pinned_ref("dhi.io/curl")  # CHT-93
    command = init["command"]
    assert command[0] == "curl"
    assert "--insecure" in command  # a boot gate, not a trust decision
    assert "--retry" in command
    assert "--retry-connrefused" in command
    assert command[-1] == "https://auth.atlas.test/realms/aurelius-atlas/.well-known/openid-configuration"
    # curl writes nothing: the boot gate carries a read-only root on top of
    # the shared posture (DD-282 follow-up — KSV-0014; the collector itself
    # keeps its own root decision).
    assert init["securityContext"]["readOnlyRootFilesystem"] is True
    assert init["resources"]["limits"]["memory"] == "32Mi"  # KSV-0015/16/18 (DD-282)


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

    assert "--web.config.file=/etc/prometheus/web-config.yaml" in app["args"]  # the server serves TLS (CHT-134)
    rendered = yaml.safe_load(find(obs_docs, "ConfigMap", f"{FULLNAME}-prometheus")["data"]["prometheus.yaml"])
    dev = yaml.safe_load((DEV_CONFIG / "prometheus.yaml").read_text())
    jobs = {job["job_name"]: job for job in rendered["scrape_configs"]}
    assert set(jobs) == {job["job_name"] for job in dev["scrape_configs"]}
    # CHT-134 (DD-655): CA-pinned https scrapes, the one exception named.
    web = yaml.safe_load(find(obs_docs, "ConfigMap", f"{FULLNAME}-prometheus")["data"]["web-config.yaml"])
    # The key is the exporter-toolkit's tls_server_config — a bare
    # tls_server fails Prometheus's strict startup validation.
    assert web["tls_server_config"] == {"cert_file": "/certs/tls.crt", "key_file": "/certs/tls.key"}
    for job_name, job in jobs.items():
        if job_name == "otel-collector-internal":  # :8888 has no TLS option (DD-655)
            assert job.get("scheme", "http") == "http", job_name
        else:
            assert job["scheme"] == "https", job_name
            assert job["tls_config"] == {"ca_file": "/certs/ca.crt"}, job_name
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


@pytest.mark.covers(rules=["CHT-39", "CHT-134"])
@pytest.mark.parametrize("asset", ["loki.yaml", "tempo.yaml"])
def test__loki_and_tempo_config_is_the_dev_asset_plus_the_tls_overlay(
    obs_docs: list[dict[str, Any]], asset: str
) -> None:
    """files/<asset> stays byte-identical to dev; the ConfigMap deep-merges the TLS overlay (CHT-39, DD-256/655).

    Append is not an option: Loki parses strictly, a duplicate top-level
    key is a fatal parse error, and -config.file's comma-list loads only
    the first existing file — both proved against 3.7.9. So the merge is
    rendered into the ConfigMap and the asset never gains TLS keys, which
    keeps the dev compose (plaintext, no mesh CA) riding the same bytes.
    """
    cm = find(obs_docs, "ConfigMap", f"{FULLNAME}-{asset.removesuffix('.yaml')}")
    asset_bytes = (OBS_CHART / "files" / asset).read_bytes()
    assert asset_bytes == (DEV_CONFIG / asset).read_bytes()  # dev's bytes never gain TLS (DV: dev stays plaintext)
    tls_block = {"cert_file": "/certs/tls.crt", "key_file": "/certs/tls.key"}
    base = yaml.safe_load(asset_bytes)
    rendered = yaml.safe_load(cm["data"]["config.yaml"])
    assert rendered["server"]["http_tls_config"] == tls_block
    if asset == "tempo.yaml":  # the OTLP receivers ride TLS too — no plaintext ingest door
        protocols = rendered["distributor"]["receivers"]["otlp"]["protocols"]
        assert protocols["grpc"]["tls"] == tls_block
        assert protocols["http"]["tls"] == tls_block
        protocols["grpc"].pop("tls")
        protocols["http"].pop("tls")
    rendered["server"].pop("http_tls_config")
    # Helm re-renders YAML scalars, so the base's bare date in
    # schema_config comes back a quoted string. Normalise it before
    # comparing so only the TLS merge can show a difference.
    for config in base.get("schema_config", {}).get("configs", []):
        config["from"] = str(config["from"])
    assert rendered == base  # everything else is dev's config, structurally


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


@pytest.mark.covers(rules=["CHT-134"])
def test__grafana_writable_tmp_carries_the_plugin_installs(obs_docs: list[dict[str, Any]]) -> None:
    """Grafana's /tmp rides an emptyDir so the startup plugin installs land (CHT-134, DD-657).

    Grafana 13 ships prometheus/loki/tempo as external plugins and installs
    the missing ones at boot; the downloader writes its zips to /tmp, and a
    read-only root (CHT-hardening) makes /tmp read-only too, so every install
    fails and the panels die plugin.notRegistered. Proved live on atlas-dev:
    the emptyDir fix turns the dashboards green, and their queries ride the
    TLS mesh. The plugins persist on the PVC's plugin path, not here.
    """
    deployment = find(obs_docs, "Deployment", f"{FULLNAME}-grafana")
    volumes = {v["name"]: v for v in pod_spec(deployment)["volumes"]}
    assert volumes["tmp"] == {"name": "tmp", "emptyDir": {}}
    mounts = {m["name"]: m["mountPath"] for m in container(deployment, "grafana")["volumeMounts"]}
    assert mounts["tmp"] == "/tmp"  # noqa: S108  # a mountPath assertion, not a temp-file use


@pytest.mark.covers(rules=["CHT-84"])
def test__grafana_logs_in_through_the_realm(obs_docs: list[dict[str, Any]]) -> None:
    """Anonymous off, login form on, generic_oauth against the imported realm (CHT-84).

    The auth URLs derive from the same issuer/realm facts as the collector's
    OIDC receiver (CHT-74); the client secret joins from
    <release>-grafana-oauth. GF_SERVER_ROOT_URL stays unset in this render:
    the chart's own posture keeps the port-forward login (DD-276, part-
    superseded by DD-654 — the host-driven pin is tested next to the
    scopes/PKCE below).
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
    issuer = "https://auth.atlas.test/realms/aurelius-atlas/protocol/openid-connect"
    assert env_value(envs, "GF_AUTH_GENERIC_OAUTH_AUTH_URL") == f"{issuer}/auth"
    assert env_value(envs, "GF_AUTH_GENERIC_OAUTH_TOKEN_URL") == f"{issuer}/token"
    assert env_value(envs, "GF_AUTH_GENERIC_OAUTH_API_URL") == f"{issuer}/userinfo"
    # The chart's own render keeps DD-276's request-derived shape (its
    # chart-local global.hosts.o11y.enabled default is off); the
    # umbrella's default-on host flips it — tested below.
    assert "GF_SERVER_ROOT_URL" not in envs
    # The claims the login asks for, and the PKCE the client enforces
    # (CHT-133, DD-654): without the challenge the issuer rejects the
    # authorize request (attribute pkce.code.challenge.method S256).
    assert env_value(envs, "GF_AUTH_GENERIC_OAUTH_SCOPES") == "openid profile email"
    assert env_value(envs, "GF_AUTH_GENERIC_OAUTH_USE_PKCE") == "true"


@pytest.mark.covers(rules=["CHT-133", "CHT-135"])
def test__grafana_root_url_follows_the_host() -> None:
    """The umbrella's host posture pins GF_SERVER_ROOT_URL (CHT-133, DD-654/653).

    With the host on, Grafana builds the OIDC redirect from root_url — the
    realm client registers only the public host, so the request-derived
    redirect 400s at the issuer. The pin follows the listener rule: a
    named host wins over the domain one, and turning the host off
    (port-forward posture) drops the pin back to DD-276's shape even when
    a stale host lingers in the values.
    """
    on = helm_render(OBS_CHART, value_files=TEST_VALUES, sets=("global.hosts.o11y.enabled=true",))
    envs = env_map(container(find(on, "Deployment", f"{FULLNAME}-grafana"), "grafana"))
    assert env_value(envs, "GF_SERVER_ROOT_URL") == "https://o11y.atlas.test"
    named = helm_render(
        OBS_CHART,
        value_files=TEST_VALUES,
        sets=("global.hosts.o11y.enabled=true", "global.hosts.o11y.host=metrics.example"),
    )
    envs = env_map(container(find(named, "Deployment", f"{FULLNAME}-grafana"), "grafana"))
    assert env_value(envs, "GF_SERVER_ROOT_URL") == "https://metrics.example"
    off = helm_render(
        OBS_CHART,
        value_files=TEST_VALUES,
        sets=("global.hosts.o11y.enabled=false", "global.hosts.o11y.host=metrics.example"),
    )
    envs = env_map(container(find(off, "Deployment", f"{FULLNAME}-grafana"), "grafana"))
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


@pytest.mark.covers(rules=["CHT-85", "CHT-136"])
def test__grafana_rbac_maps_grafana_client_roles(obs_docs: list[dict[str, Any]]) -> None:
    """The client roles gate the door: admin/editor escalate, no role is denied (CHT-85, CHT-136, DD-659).

    The Viewer fallback of DD-275 made every realm user a reader of every
    workload's telemetry; the strict mapping denies a user holding neither
    grafana client role instead.
    """
    app = container(find(obs_docs, "Deployment", f"{FULLNAME}-grafana"), "grafana")
    envs = env_map(app)
    path = env_value(envs, "GF_AUTH_GENERIC_OAUTH_ROLE_ATTRIBUTE_PATH")
    # The denied case is the JMESPath empty-string literal (''), not "Viewer".
    # JMESPath has no ternary operator, so the chain uses && and ||.
    assert path == (
        "contains(resource_access.grafana.roles[*], 'admin') && 'Admin' "
        "|| contains(resource_access.grafana.roles[*], 'editor') && 'Editor' || ''"
    )
    assert '"Viewer"' not in path  # the denied case carries no role (DD-659)
    assert env_value(envs, "GF_AUTH_GENERIC_OAUTH_ROLE_ATTRIBUTE_STRICT") == "true"
    # The realm is the boundary: no role-list path, no org allow-list.
    assert "GF_AUTH_GENERIC_OAUTH_ROLE_LIST_PATH" not in envs
    assert "GF_AUTH_GENERIC_OAUTH_ALLOWED_ORGANIZATIONS" not in envs


@pytest.mark.covers(rules=["CHT-40", "CHT-134"])
def test__datasources_pin_uids_the_crosslinks_and_the_ca(obs_docs: list[dict[str, Any]]) -> None:
    """Datasource uids prometheus/loki/tempo, the cross-links, and the CA-pinned https url (CHT-40, DD-655).

    serviceMap to prometheus, tracesToLogsV2 to loki, filterByTraceID, and
    the service.name tag join. Every url rides https — the backends serve
    TLS internally — with the trust CA pinned by file, so a hand-made cert
    on the hop fails the query instead of trusting it.
    """
    sources = yaml.safe_load(find(obs_docs, "ConfigMap", f"{FULLNAME}-grafana-datasources")["data"]["datasources.yaml"])
    by_uid = {d["uid"]: d for d in sources["datasources"]}
    assert set(by_uid) == {"prometheus", "loki", "tempo"}
    assert by_uid["prometheus"]["url"] == f"https://{FULLNAME}-prometheus:9090"
    assert by_uid["loki"]["url"] == f"https://{FULLNAME}-loki:3100"
    assert by_uid["tempo"]["url"] == f"https://{FULLNAME}-tempo:3200"
    for source in by_uid.values():
        assert source["jsonData"]["tlsAuthWithCACert"] is True
        assert source["secureJsonDataFiles"]["tlsCACert"] == "/certs/ca.crt"
    tempo_json = by_uid["tempo"]["jsonData"]
    assert tempo_json["serviceMap"]["datasourceUid"] == "prometheus"
    assert tempo_json["tracesToLogsV2"]["datasourceUid"] == "loki"
    assert tempo_json["tracesToLogsV2"]["filterByTraceID"] is True
    assert tempo_json["tracesToLogsV2"]["tags"] == ["service.name"]


@pytest.mark.covers(rules=["CHT-40", "OBS-02"])
def test__grafana_assets_are_byte_copies(obs_docs: list[dict[str, Any]]) -> None:
    """Provider + all five dashboards byte-identical to dev (CHT-40, DD-256; the server's joins with OBS-02).

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
    assert len(expected) == 5
    for name in expected:
        assert dashboards["data"][name].encode() == (dev_dir / name).read_bytes()


@pytest.mark.covers(rules=["OBS-03"])
def test__the_alert_rules_are_a_byte_copy_mounted_for_grafana(obs_docs: list[dict[str, Any]]) -> None:
    """The rules ride byte-identical to dev, on Grafana's alerting provisioning path (OBS-03, DD-256's guard)."""
    alerting = find(obs_docs, "ConfigMap", f"{FULLNAME}-grafana-alerting")
    assert alerting["data"]["rules.yaml"].encode() == (OBS_CHART / "files/grafana-alerting.yaml").read_bytes()
    assert (OBS_CHART / "files/grafana-alerting.yaml").read_bytes() == (
        DEV_CONFIG / "grafana/alerting/rules.yaml"
    ).read_bytes()

    rules = yaml.safe_load(alerting["data"]["rules.yaml"])["groups"][0]["rules"]
    assert all(rule["labels"]["team"] == "maintainers" for rule in rules)
    assert {rule["labels"]["severity"] for rule in rules} == {"critical", "warning"}

    grafana = pod_spec(find(obs_docs, "Deployment", f"{FULLNAME}-grafana"))
    mounts = {
        m["name"]: m["mountPath"]
        for m in container(find(obs_docs, "Deployment", f"{FULLNAME}-grafana"), "grafana")["volumeMounts"]
    }
    assert mounts["alerting"] == "/etc/grafana/provisioning/alerting"
    volumes = {v["name"]: v for v in grafana["volumes"]}
    assert volumes["alerting"]["configMap"]["name"] == f"{FULLNAME}-grafana-alerting"


@pytest.mark.covers(rules=["OBS-04"])
def test__a_webhook_secret_routes_every_rule_to_the_maintainers() -> None:
    """Without the Secret no contact point; with it, the webhook reads its URL from the Secret's env (OBS-04)."""
    plain = find(helm_render(OBS_CHART, value_files=TEST_VALUES), "ConfigMap", f"{FULLNAME}-grafana-alerting")
    assert set(plain["data"]) == {"rules.yaml"}

    docs = helm_render(OBS_CHART, value_files=TEST_VALUES, sets=("grafana.alerting.webhookSecret=alert-hook",))
    provisioned = yaml.safe_load(find(docs, "ConfigMap", f"{FULLNAME}-grafana-alerting")["data"]["contact-points.yaml"])
    [contact] = provisioned["contactPoints"]
    assert contact["name"] == "maintainers"
    assert contact["receivers"][0]["settings"]["url"] == "$__env{ALERT_WEBHOOK_URL}"
    assert provisioned["policies"][0]["receiver"] == "maintainers"
    envs = env_map(container(find(docs, "Deployment", f"{FULLNAME}-grafana"), "grafana"))
    assert envs["ALERT_WEBHOOK_URL"]["valueFrom"]["secretKeyRef"] == {"name": "alert-hook", "key": "url"}


@pytest.mark.covers(rules=["CHT-44"])
def test__every_workload_runs_as_65532_dropped_and_unprivileged(obs_docs: list[dict[str, Any]]) -> None:
    """Pod uid/fsGroup 65532 + RuntimeDefault; containers drop ALL and run read-only.

    No escalation anywhere (DD-257, CHT-44, DD-282 Tier 3). The shared
    securityContext covers all five Tier 3 workloads: none of them
    writes to its root (the live overlay's write map — every writable path
    rides a volume; the collector's home cache gets its own emptyDir).
    """
    for deployment in find_all(obs_docs, "Deployment"):
        spec = pod_spec(deployment)
        psc = spec["securityContext"]
        assert psc["runAsNonRoot"] is True, deployment["metadata"]["name"]
        assert psc["runAsUser"] == 65532, deployment["metadata"]["name"]
        assert psc["runAsGroup"] == 65532, deployment["metadata"]["name"]  # KSV-0021 (DD-282)
        assert psc["seccompProfile"] == {"type": "RuntimeDefault"}
        for app in spec["containers"]:
            sc = app["securityContext"]
            assert sc["allowPrivilegeEscalation"] is False
            assert sc["capabilities"]["drop"] == ["ALL"]
            assert sc["readOnlyRootFilesystem"] is True, deployment["metadata"]["name"]


@pytest.mark.covers(rules=["CHT-33"])
def test__collector_cache_empty_dir_backs_the_read_only_root(obs_docs: list[dict[str, Any]]) -> None:
    """The collector's one root-FS write rides an emptyDir.

    The contrib image's ~/.cache (the live overlay) — DD-282 Tier 3.
    """
    deployment = find(obs_docs, "Deployment", FULLNAME)
    app = container(deployment, "observability")
    cache_mount = next(m for m in app["volumeMounts"] if m["name"] == "cache")
    assert cache_mount["mountPath"] == "/home/nonroot/.cache"
    volumes = {v["name"]: v for v in pod_spec(deployment)["volumes"]}
    assert "emptyDir" in volumes["cache"]


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

    Grafana's only allow is the umbrella's gateway edge rule, and that
    exists once the browser host is on — the umbrella's default since
    DD-653 — tested there. Port-forward rides the kubelet.
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


@pytest.mark.covers(rules=["CHT-93"])
def test__backend_images_digest_pinned(obs_docs: list[dict[str, Any]]) -> None:
    """Prometheus/Loki/Tempo/Grafana render <repo>@sha256:... (CHT-93).

    The four dhi.io backends this chart owns carry committed digests, so a
    stock install pulls immutable bytes; no third-party image renders by tag.
    """
    for component in ("prometheus", "loki", "tempo", "grafana"):
        app = container(find(obs_docs, "Deployment", f"{FULLNAME}-{component}"), component)
        assert app["image"] == pinned_ref(f"dhi.io/{component}"), component


@pytest.mark.covers(rules=["CHT-92"])
def test__component_image_digest_wins_over_tag() -> None:
    """grafana.image.digest renders dhi.io/grafana@<digest> (CHT-92).

    componentImage's digest branch: the digest wins over the repository's
    tag, and the repository base is unchanged.
    """
    docs = helm_render(
        OBS_CHART,
        sets=("global.domain=atlas.test", f"grafana.image.digest=sha256:{7:064d}"),
    )
    app = container(find(docs, "Deployment", f"{FULLNAME}-grafana"), "grafana")
    assert app["image"] == "dhi.io/grafana@sha256:" + "0" * 63 + "7"
