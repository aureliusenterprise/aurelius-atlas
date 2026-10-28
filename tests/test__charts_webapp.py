"""Chart-contract suite for the webapp chart (CHT-23/24/25/26, 10.3a).

The shape the spec pins: plaintext 8080 behind the Gateway (DD-242) with HTTP
probes; the nginx config shipped as a byte-copy chart asset resolved at pod
start by an init container (DD-262) — Helm never renders a placeholder; the
ten CHT-25 placeholders computed by the chart; /config.json rendered from
values for the SPA's bootstrap fetch.
"""

from typing import Any

import pytest
import yaml
from conftest import WEBAPP_CHART, container, env_map, env_value, find, helm_render, pod_spec

TEST_VALUES = (WEBAPP_CHART / "tests/values.test.yaml",)

# The ten placeholder names CHT-25 fixes as the template contract.
PLACEHOLDERS = [
    "AURELIUS_ATLAS_WEBAPP_API_UPSTREAM",
    "AURELIUS_ATLAS_WEBAPP_API_UPSTREAM_NAME",
    "AURELIUS_ATLAS_WEBAPP_DNS_RESOLVER",
    "AURELIUS_ATLAS_WEBAPP_KEYCLOAK_ORIGINS",
    "AURELIUS_ATLAS_WEBAPP_OTEL_UPSTREAM",
    "AURELIUS_ATLAS_WEBAPP_OTEL_UPSTREAM_NAME",
    "AURELIUS_ATLAS_WEBAPP_OTLP_ENDPOINT",
    "AURELIUS_ATLAS_WEBAPP_REALIP_BLOCK",
    "AURELIUS_ATLAS_WEBAPP_TLS_CA_FILE",
    "AURELIUS_ATLAS_WEBAPP_OTEL_INGEST_TOKEN",
]


@pytest.mark.covers(rules=["CHT-23"])
def test__plaintext_service_and_http_probes(webapp_docs: list[dict[str, Any]]) -> None:
    """8080 ClusterIP, no Certificate/leaf Secret — TLS ends at the Gateway."""
    service = find(webapp_docs, "Service", "atlas-webapp")
    assert service["spec"]["type"] == "ClusterIP"
    assert service["spec"]["ports"] == [{"name": "http", "port": 8080, "targetPort": 8080, "protocol": "TCP"}]
    app = container(find(webapp_docs, "Deployment", "atlas-webapp"), "webapp")
    assert app["readinessProbe"]["httpGet"]["scheme"] == "HTTP"
    assert app["readinessProbe"]["httpGet"]["path"] == "/config.json"
    assert app["livenessProbe"]["httpGet"]["scheme"] == "HTTP"
    assert "Certificate" not in {d["kind"] for d in webapp_docs}


@pytest.mark.covers(rules=["CHT-23"])
def test__nginx_uid_with_writable_emptydirs(webapp_docs: list[dict[str, Any]]) -> None:
    """Read-only rootfs; the nginx pid/temp/log paths ride emptyDirs + fsGroup."""
    spec = pod_spec(find(webapp_docs, "Deployment", "atlas-webapp"))
    psc = spec["securityContext"]
    assert psc["runAsUser"] == 65532
    assert psc["runAsNonRoot"] is True
    assert psc["fsGroup"] == 65532
    assert (
        container(find(webapp_docs, "Deployment", "atlas-webapp"), "webapp")["securityContext"][
            "readOnlyRootFilesystem"
        ]
        is True
    )
    empty_dirs = {v["name"] for v in spec["volumes"] if "emptyDir" in v}
    mounts = {
        m["mountPath"]: m["name"]
        for m in container(find(webapp_docs, "Deployment", "atlas-webapp"), "webapp")["volumeMounts"]
    }
    for path in ("/run/nginx", "/var/lib/nginx/tmp", "/var/log/nginx"):
        assert path in mounts, path
        assert mounts[path] in empty_dirs, path


@pytest.mark.covers(rules=["CHT-24"])
def test__nginx_asset_is_a_byte_copy_of_the_app_template() -> None:
    """helm/files/nginx.conf.template == the app's own template (DD-256 pattern)."""
    chart_asset = (WEBAPP_CHART / "files/nginx.conf.template").read_bytes()
    app_template = (WEBAPP_CHART.parent / "nginx.conf.template").read_bytes()
    assert chart_asset == app_template, "the chart asset drifted from apps/aurelius-atlas-webapp/nginx.conf.template"


@pytest.mark.covers(rules=["CHT-24"])
def test__configmap_ships_the_raw_template(webapp_docs: list[dict[str, Any]]) -> None:
    """Helm never substitutes: the ConfigMap keeps every ${...} placeholder."""
    configmap = find(webapp_docs, "ConfigMap", "atlas-webapp-nginx")
    template = configmap["data"]["nginx.conf.template"]
    for name in PLACEHOLDERS:
        assert "${" + name + "}" in template, name


@pytest.mark.covers(rules=["CHT-24"])
def test__init_container_resolves_the_ten_placeholders(webapp_docs: list[dict[str, Any]]) -> None:
    """resolve-nginx-config: same image, sed per name, fail-loud guard."""
    init = _init(find(webapp_docs, "Deployment", "atlas-webapp"), "resolve-nginx-config")
    image_app = container(find(webapp_docs, "Deployment", "atlas-webapp"), "webapp")
    assert init["image"] == image_app["image"]
    script = " ".join(init["args"])
    assert init["command"] == ["/bin/sh", "-ec"]
    for name in PLACEHOLDERS:
        # Search side escaped so sed sees it literally; replacement side is
        # the shell expansion of the env var.
        assert f"s|\\${{{name}}}|${{{name}}}|g" in script, name
    assert "exit 1" in script  # the unresolved-placeholder guard
    # The init's env is exactly the ten names (CHT-25).
    assert sorted(env_map(init)) == sorted(PLACEHOLDERS)


@pytest.mark.covers(rules=["CHT-25"])
def test__placeholder_values_are_chart_joins(webapp_docs: list[dict[str, Any]]) -> None:
    """Every placeholder derives from a peer name, the issuer, or a Secret."""
    init = _init(find(webapp_docs, "Deployment", "atlas-webapp"), "resolve-nginx-config")
    envs = env_map(init)
    assert env_value(envs, "AURELIUS_ATLAS_WEBAPP_API_UPSTREAM") == "https://atlas-server.atlas.svc.cluster.local:21000"
    assert env_value(envs, "AURELIUS_ATLAS_WEBAPP_API_UPSTREAM_NAME") == "atlas-server.atlas.svc.cluster.local"
    assert (
        env_value(envs, "AURELIUS_ATLAS_WEBAPP_OTEL_UPSTREAM")
        == "https://atlas-observability.atlas.svc.cluster.local:4318"
    )
    assert (
        env_value(envs, "AURELIUS_ATLAS_WEBAPP_OTLP_ENDPOINT")
        == "https://atlas-observability.atlas.svc.cluster.local:4320"
    )
    assert env_value(envs, "AURELIUS_ATLAS_WEBAPP_KEYCLOAK_ORIGINS") == "https://keycloak.atlas.test"
    assert env_value(envs, "AURELIUS_ATLAS_WEBAPP_DNS_RESOLVER") == "10.96.0.10"
    assert env_value(envs, "AURELIUS_ATLAS_WEBAPP_TLS_CA_FILE") == "/etc/aurelius-atlas/tls/ca.crt"
    # The ingest bearer arrives from the Secret at pod start, never rendered.
    token = envs["AURELIUS_ATLAS_WEBAPP_OTEL_INGEST_TOKEN"]["valueFrom"]["secretKeyRef"]
    assert token == {"name": "atlas-collector-legacy", "key": "token"}


@pytest.mark.covers(rules=["CHT-25", "CHT-32"])
def test__realip_block_follows_the_values() -> None:
    """Empty by default (no hop trusted); a CIDR list becomes one line."""
    default = env_map(
        _init(
            find(helm_render(WEBAPP_CHART, value_files=TEST_VALUES), "Deployment", "atlas-webapp"),
            "resolve-nginx-config",
        )
    )
    assert env_value(default, "AURELIUS_ATLAS_WEBAPP_REALIP_BLOCK") == ""
    docs = helm_render(
        WEBAPP_CHART,
        value_files=TEST_VALUES,
        sets=("nginx.trustedProxyCIDRs={10.244.0.0/16,10.96.0.0/16}",),
    )
    init = _init(find(docs, "Deployment", "atlas-webapp"), "resolve-nginx-config")
    realip = env_value(env_map(init), "AURELIUS_ATLAS_WEBAPP_REALIP_BLOCK")
    assert "\n" not in realip  # sed-safe: one line
    expected = (
        "real_ip_header X-Forwarded-For; real_ip_recursive on; "
        "set_real_ip_from 10.244.0.0/16; set_real_ip_from 10.96.0.0/16;"
    )
    assert realip == expected


@pytest.mark.covers(rules=["CHT-26"])
def test__config_json_rendered_from_values(webapp_docs: list[dict[str, Any]]) -> None:
    """ApiBaseUrl / keycloak.url / otelExporterUrl, mounted at the SPA's path."""
    configmap = find(webapp_docs, "ConfigMap", "atlas-webapp-config")
    config = yaml.safe_load(configmap["data"]["config.json"])
    assert config["apiBaseUrl"] == "/api"
    assert config["keycloak"]["url"] == "https://keycloak.atlas.test"
    assert config["otelExporterUrl"] == "/otel/v1/traces"
    mounts = {
        m["mountPath"]: m for m in container(find(webapp_docs, "Deployment", "atlas-webapp"), "webapp")["volumeMounts"]
    }
    mount = mounts["/usr/share/nginx/html/config.json"]
    assert mount["subPath"] == "config.json"
    assert mount["readOnly"] is True


def _init(deployment: dict[str, Any], name: str) -> dict[str, Any]:
    inits = [c for c in pod_spec(deployment)["initContainers"] if c["name"] == name]
    assert len(inits) == 1
    return inits[0]
