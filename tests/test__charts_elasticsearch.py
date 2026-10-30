"""Chart-contract suite for ``atlas-elasticsearch`` (CHT-10..15, 10.2).

The store's cluster shape is asserted at the render, the same invariants the
dev compose sibling states (``dev/elasticsearch/docker-compose.yaml``): the
single-node arrangement, the hardened ``elasticsearch.yml``, the cert-manager
Certificate and its SANs, the generated-secret bootstrap password, the exec
healthcheck, and the coredump-agent wiring.
"""

from typing import Any

import pytest
import yaml
from conftest import (
    ES_CHART,
    container,
    env_map,
    env_value,
    find,
    helm_render,
    helm_render_fails,
    names,
    peer_labels,
    pod_spec,
    policy_peers_by_port,
)


@pytest.mark.covers(rules=["CHT-10"])
def test__store_workload_shapes(es_docs: list[dict[str, Any]]) -> None:
    """StatefulSet + headless + ClusterIP, single replica (CHT-10)."""
    ss = find(es_docs, "StatefulSet", "atlas-elasticsearch")
    assert ss["spec"]["replicas"] == 1
    assert ss["spec"]["serviceName"] == "atlas-elasticsearch-headless"
    cluster_ip = find(es_docs, "Service", "atlas-elasticsearch")
    assert cluster_ip["spec"]["type"] == "ClusterIP"
    assert cluster_ip["spec"].get("clusterIP") != "None"
    headless = find(es_docs, "Service", "atlas-elasticsearch-headless")
    assert headless["spec"]["clusterIP"] == "None"
    assert headless["spec"]["publishNotReadyAddresses"] is True


@pytest.mark.covers(rules=["CHT-10"])
def test__replicas_above_one_fails_render() -> None:
    """The quorum switch is a later increment, so replicas 2 fails the render."""
    error = helm_render_fails(ES_CHART, sets=("replicas=2",))
    assert "quorum" in error


@pytest.mark.covers(rules=["CHT-11"])
def test__elasticsearch_yml_contract(es_docs: list[dict[str, Any]]) -> None:
    """The hardened settings file is the store's only settings channel (CHT-11).

    Security on, TLS-only HTTP, transport TLS off, ML off, mmap off,
    single-node discovery — and the file mounts over the image's own, because
    the hardened image ignores dotted env vars.
    """
    cm = find(es_docs, "ConfigMap", "atlas-elasticsearch")
    settings = yaml.safe_load(cm["data"]["elasticsearch.yml"])
    assert settings["xpack.security.enabled"] is True
    assert settings["xpack.security.http.ssl.enabled"] is True
    assert settings["xpack.security.transport.ssl.enabled"] is False
    assert settings["xpack.ml.enabled"] is False
    assert settings["node.store.allow_mmap"] is False
    assert settings["discovery.type"] == "single-node"
    ss = find(es_docs, "StatefulSet", "atlas-elasticsearch")
    config_volumes = [v for v in pod_spec(ss)["volumes"] if "configMap" in v]
    assert any(v["configMap"]["name"] == "atlas-elasticsearch" for v in config_volumes)
    config_mount = next(vm for vm in container(ss, "elasticsearch")["volumeMounts"] if vm["name"] == "config")
    assert config_mount["subPath"] == "elasticsearch.yml"
    assert config_mount["mountPath"] == "/usr/share/elasticsearch/config/elasticsearch.yml"


@pytest.mark.covers(rules=["CHT-11"])
def test__no_dotted_env_settings(es_docs: list[dict[str, Any]]) -> None:
    """No ``es.setting.*``-style dotted settings leak into the container env."""
    ss = find(es_docs, "StatefulSet", "atlas-elasticsearch")
    env_names = [e["name"] for e in container(ss, "elasticsearch").get("env", [])]
    assert not [n for n in env_names if n.startswith("es.") or "." in n]


@pytest.mark.covers(rules=["CHT-12"])
def test__certificate_sans(es_docs: list[dict[str, Any]]) -> None:
    """The Certificate covers the service, headless, and FQDN names (CHT-12)."""
    cert = find(es_docs, "Certificate", "atlas-elasticsearch")
    sans = set(cert["spec"]["dnsNames"])
    assert {
        "atlas-elasticsearch",
        "atlas-elasticsearch.atlas",
        "atlas-elasticsearch.atlas.svc",
        "atlas-elasticsearch.atlas.svc.cluster.local",
        "atlas-elasticsearch-headless",
        "atlas-elasticsearch-headless.atlas.svc.cluster.local",
    } <= sans
    assert cert["spec"]["secretName"] == "atlas-elasticsearch-tls"
    assert cert["spec"]["issuerRef"]["name"] == "aurelius-atlas-selfsigned"


@pytest.mark.covers(rules=["CHT-12"])
def test__tls_mounts_at_config_tls_in_pem_names(es_docs: list[dict[str, Any]]) -> None:
    """The Secret projects into the image's PEM names under ``config/tls``.

    Never ``config/certs`` — that directory belongs to security
    auto-configuration (CHT-12).
    """
    ss = find(es_docs, "StatefulSet", "atlas-elasticsearch")
    volumes = {v["name"]: v for v in pod_spec(ss)["volumes"]}
    tls = volumes["tls"]["secret"]
    assert tls["secretName"] == "atlas-elasticsearch-tls"
    items = {i["key"]: i["path"] for i in tls["items"]}
    assert items == {
        "tls.crt": "elasticsearch.pem",
        "tls.key": "elasticsearch-key.pem",
        "ca.crt": "ca.pem",
    }
    mount = next(vm for vm in container(ss, "elasticsearch")["volumeMounts"] if vm["name"] == "tls")
    assert mount["mountPath"] == "/usr/share/elasticsearch/config/tls"
    assert "config/certs" not in str(volumes)


@pytest.mark.covers(rules=["CHT-12"])
def test__configmap_pins_tls_file_paths(es_docs: list[dict[str, Any]]) -> None:
    """``elasticsearch.yml`` points the HTTP TLS pair at the mounted PEM names.

    The paths are config-relative; the image resolves them under ``config/``.
    """
    cm = find(es_docs, "ConfigMap", "atlas-elasticsearch")
    settings = yaml.safe_load(cm["data"]["elasticsearch.yml"])
    assert settings["xpack.security.http.ssl.certificate"] == "tls/elasticsearch.pem"
    assert settings["xpack.security.http.ssl.certificate_authorities"] == ["tls/ca.pem"]
    assert settings["xpack.security.http.ssl.key"] == "tls/elasticsearch-key.pem"
    # Auto-configuration must never run: every security setting is explicit.
    assert settings["xpack.security.autoconfiguration.enabled"] is False


@pytest.mark.covers(rules=["CHT-13"])
def test__bootstrap_password_from_generated_secret(es_docs: list[dict[str, Any]]) -> None:
    """ELASTIC_PASSWORD arrives as a secretKeyRef, never inline (CHT-13)."""
    ss = find(es_docs, "StatefulSet", "atlas-elasticsearch")
    envs = env_map(container(ss, "elasticsearch"))
    ref = envs["ELASTIC_PASSWORD"]["valueFrom"]["secretKeyRef"]
    assert ref == {"name": "atlas-elasticsearch", "key": "elastic-password"}
    assert "value" not in envs["ELASTIC_PASSWORD"]
    # The chart consumes the generated Secret; it never renders one (CHT-19).
    assert "Secret" not in {d["kind"] for d in es_docs}


@pytest.mark.covers(rules=["CHT-14"])
def test__exec_probes_are_openssl_s_client(es_docs: list[dict[str, Any]]) -> None:
    """The probes run the compose healthcheck's shape (CHT-14).

    openssl s_client to localhost, CA-pinned, with the health endpoint and the
    green-or-yellow answer.
    """
    ss = find(es_docs, "StatefulSet", "atlas-elasticsearch")
    c = container(ss, "elasticsearch")
    for probe in ("startupProbe", "readinessProbe", "livenessProbe"):
        script = " ".join(c[probe]["exec"]["command"])
        assert "openssl s_client" in script, probe
        assert "-CAfile /usr/share/elasticsearch/config/tls/ca.pem" in script, probe
        assert "_cluster/health" in script, probe
        assert "(green|yellow)" in script, probe


@pytest.mark.covers(rules=["CHT-15"])
def test__agent_init_and_javaopts(es_docs: list[dict[str, Any]]) -> None:
    """The coredump agent lands via an init container and the javaagent flag."""
    ss = find(es_docs, "StatefulSet", "atlas-elasticsearch")
    spec = pod_spec(ss)
    init = spec["initContainers"][0]
    assert init["image"].startswith("ghcr.io/aureliusenterprise/aurelius-atlas-elasticsearch-agent:")
    assert "coredump-noop.jar" in " ".join(init["command"])
    volumes = {v["name"]: v for v in spec["volumes"]}
    assert "emptyDir" in volumes["agent"]
    envs = env_map(container(ss, "elasticsearch"))
    java_opts = env_value(envs, "ES_JAVA_OPTS")
    assert "-javaagent:/agent/coredump-noop.jar" in java_opts
    assert "-Xms1g" in java_opts
    assert "-Xmx1g" in java_opts
    agent_mount = next(vm for vm in container(ss, "elasticsearch")["volumeMounts"] if vm["name"] == "agent")
    assert agent_mount["mountPath"] == "/agent"


@pytest.mark.covers(rules=["CHT-15"])
def test__runs_as_image_uid_with_fs_group(es_docs: list[dict[str, Any]]) -> None:
    """The pod runs the image's uid (1000), never root, with fsGroup for data.

    DD-257: the hardened image does no privilege drop and its JVM refuses
    root; fsGroup is the compose volume-init's in-cluster shape.
    """
    ss = find(es_docs, "StatefulSet", "atlas-elasticsearch")
    psc = pod_spec(ss)["securityContext"]
    assert psc["runAsUser"] == 1000
    assert psc["runAsUser"] != 0
    assert psc["fsGroup"] == 1000
    assert psc["seccompProfile"] == {"type": "RuntimeDefault"}
    init = pod_spec(ss)["initContainers"][0]
    assert init["securityContext"]["runAsUser"] == 1000


@pytest.mark.covers(rules=["CHT-18"])
def test__pdb_and_storage_class_defaults(es_docs: list[dict[str, Any]]) -> None:
    """PDB minAvailable 1; storageClassName omitted at the "" default."""
    pdb = find(es_docs, "PodDisruptionBudget", "atlas-elasticsearch")
    assert pdb["spec"]["minAvailable"] == 1
    ss = find(es_docs, "StatefulSet", "atlas-elasticsearch")
    vct = ss["spec"]["volumeClaimTemplates"][0]
    assert "storageClassName" not in vct["spec"]
    assert vct["spec"]["resources"]["requests"]["storage"] == "30Gi"


@pytest.mark.covers(rules=["CHT-18"])
def test__storage_class_set_when_global_provided() -> None:
    """global.storageClass non-empty appears on the volume claim."""
    docs = helm_render(ES_CHART, sets=("global.storageClass=fast-ssd",))
    ss = find(docs, "StatefulSet", "atlas-elasticsearch")
    assert ss["spec"]["volumeClaimTemplates"][0]["spec"]["storageClassName"] == "fast-ssd"


@pytest.mark.covers(rules=["CHT-12"])
def test__bring_your_own_secret_suppresses_certificate() -> None:
    """tls.secretName brings your own and the Certificate renders nothing."""
    docs = helm_render(ES_CHART, sets=("tls.secretName=my-es-tls",))
    assert "atlas-elasticsearch" not in names(docs, "Certificate")
    ss = find(docs, "StatefulSet", "atlas-elasticsearch")
    volumes = {v["name"]: v for v in pod_spec(ss)["volumes"]}
    assert volumes["tls"]["secret"]["secretName"] == "my-es-tls"


@pytest.mark.covers(rules=["CHT-43"])
def test__metrics_puller_renders_when_telemetry_enabled() -> None:
    """telemetry.enabled renders the puller (CHT-43, DD-266).

    The contrib image, the dev config's dev-elasticsearch service.name, the
    store + client joins, the public mint URL, and the per-service collector
    target.
    """
    docs = helm_render(ES_CHART, sets=("global.domain=atlas.test", "telemetry.enabled=true"))
    deployment = find(docs, "Deployment", "atlas-elasticsearch-metrics-puller")
    app = container(deployment, "metrics-puller")
    assert app["image"] == "dhi.io/opentelemetry-collector:0-debian13-contrib"
    psc = pod_spec(deployment)["securityContext"]
    assert psc["runAsNonRoot"] is True
    assert psc["runAsUser"] == 65532
    assert app["securityContext"]["capabilities"]["drop"] == ["ALL"]  # CHT-44
    # The issuer-wait init (the oauth2client boot race, DD-195/226).
    (init,) = pod_spec(deployment)["initContainers"]
    assert init["name"] == "issuer-wait"

    config = yaml.safe_load(find(docs, "ConfigMap", "atlas-elasticsearch-metrics-puller")["data"]["config.yaml"])
    (upsert,) = config["processors"]["resource"]["attributes"]
    assert upsert["value"] == "dev-elasticsearch"  # the dashboard's exported_job pin
    receiver = config["receivers"]["elasticsearch"]
    assert receiver["endpoint"] == "https://atlas-elasticsearch:9200"
    assert config["exporters"]["otlp"]["endpoint"] == "https://atlas-observability:4317"
    oauth = config["extensions"]["oauth2client"]
    assert oauth["token_url"] == "https://keycloak.atlas.test/realms/master/protocol/openid-connect/token"  # noqa: S105  # a public URL, not a secret
    assert oauth["client_id"] == "otel-elasticsearch"
    assert oauth["client_secret"] == "${env:OTEL_INGEST_CLIENT_SECRET}"  # noqa: S105  # the placeholder, never material

    envs = env_map(app)
    assert envs["ELASTICSEARCH_PASSWORD"]["valueFrom"]["secretKeyRef"] == {
        "name": "atlas-elasticsearch",
        "key": "elastic-password",
    }
    assert envs["OTEL_INGEST_CLIENT_SECRET"]["valueFrom"]["secretKeyRef"] == {
        "name": "atlas-otel-clients",
        "key": "OTEL_INGEST_CLIENT_SECRET",
    }
    # R5: no credential literal renders into the puller's ConfigMap.
    assert (
        "elastic-password" not in find(docs, "ConfigMap", "atlas-elasticsearch-metrics-puller")["data"]["config.yaml"]
    )


@pytest.mark.covers(rules=["CHT-43"])
def test__puller_default_off() -> None:
    """The bare render carries no puller (CHT-42/43).

    Telemetry is opt-in; the umbrella turns it on for the stock install.
    """
    assert "atlas-elasticsearch-metrics-puller" not in names(helm_render(ES_CHART), "Deployment")
    assert "atlas-elasticsearch-metrics-puller" not in names(helm_render(ES_CHART), "ConfigMap")


@pytest.mark.covers(rules=["CHT-64", "CHT-71"])
def test__store_admits_server_only_bare(es_docs: list[dict[str, Any]]) -> None:
    """9200 accepts the server pods only; 9300 has no rule (CHT-64).

    The transport port is denied by absence — a single-node store has no
    peer node to admit — and no rule opens anything else.
    """
    policy = find(es_docs, "NetworkPolicy", "atlas-elasticsearch-ingress")
    assert policy["spec"]["podSelector"]["matchLabels"] == peer_labels("atlas-elasticsearch")
    assert policy_peers_by_port(es_docs, "atlas-elasticsearch-ingress") == {9200: {"atlas-server"}}
    ports = {p["port"] for r in policy["spec"]["ingress"] for p in r["ports"]}
    assert ports == {9200}


@pytest.mark.covers(rules=["CHT-64", "CHT-70"])
def test__store_puller_joins_by_qualified_pod_name() -> None:
    """With telemetry the puller joins 9200 under its fullname name (CHT-64/70).

    A puller pod's name label is the fullname-qualified name, and the
    qualifier follows the release: the same override-free rule the pod
    carries (a peer renamed for a policy is the ``peers`` override, never
    the Service-name join).
    """
    docs = helm_render(ES_CHART, sets=("global.domain=atlas.test", "telemetry.enabled=true"))
    assert policy_peers_by_port(docs, "atlas-elasticsearch-ingress") == {
        9200: {"atlas-server", "atlas-elasticsearch-metrics-puller"}
    }
    other = helm_render(ES_CHART, release="foo", sets=("global.domain=atlas.test", "telemetry.enabled=true"))
    assert policy_peers_by_port(other, "foo-atlas-elasticsearch-ingress") == {
        9200: {"atlas-server", "foo-atlas-elasticsearch-metrics-puller"}
    }
    peers = [
        e["podSelector"]["matchLabels"]
        for r in find(other, "NetworkPolicy", "foo-atlas-elasticsearch-ingress")["spec"]["ingress"]
        for e in r["from"]
    ]
    assert peer_labels("foo-atlas-elasticsearch-metrics-puller", instance="foo") in peers


@pytest.mark.covers(rules=["CHT-64", "CHT-72"])
def test__store_network_policy_off_changes_nothing_else() -> None:
    """The chart's disable switch is surgical (CHT-72)."""
    on = helm_render(ES_CHART)
    off = helm_render(ES_CHART, sets=("networkPolicy.enabled=false",))
    assert names(on, "NetworkPolicy") == {"atlas-elasticsearch-ingress"}
    assert names(off, "NetworkPolicy") == set()

    def rest(docs: list[dict[str, Any]]) -> list[tuple[str, str]]:
        return sorted((d["kind"], d["metadata"]["name"]) for d in docs if d["kind"] != "NetworkPolicy")

    assert rest(on) == rest(off)
