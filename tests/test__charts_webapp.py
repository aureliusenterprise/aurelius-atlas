"""Chart-contract suite for the webapp chart (CHT-23/24/25/26, 10.3a; DD-270).

The shape the spec pins: a TLS listener on 8080 behind the Gateway (the
Gateway's BackendTLSPolicy dials it, DD-270) with HTTPS probes and a
chart-issued leaf; the nginx config shipped as a byte-copy chart asset
resolved at pod start by an init container (DD-262) — Helm never renders a
placeholder; the twelve CHT-25 placeholders computed by the chart;
/config.json rendered from values for the SPA's bootstrap fetch.
"""

from typing import Any

import pytest
import yaml
from conftest import WEBAPP_CHART, container, env_map, env_value, find, helm_render, pod_spec

TEST_VALUES = (WEBAPP_CHART / "tests/values.test.yaml",)

# The thirteen placeholder names CHT-25 fixes as the template contract (the
# listener leaf paths join DD-270's pair; HSTS_HEADER joined with CHT-99).
PLACEHOLDERS = [
    "AURELIUS_ATLAS_WEBAPP_API_UPSTREAM",
    "AURELIUS_ATLAS_WEBAPP_HSTS_HEADER",
    "AURELIUS_ATLAS_WEBAPP_API_UPSTREAM_NAME",
    "AURELIUS_ATLAS_WEBAPP_DNS_RESOLVER",
    "AURELIUS_ATLAS_WEBAPP_KEYCLOAK_ORIGINS",
    "AURELIUS_ATLAS_WEBAPP_OTEL_UPSTREAM",
    "AURELIUS_ATLAS_WEBAPP_OTEL_UPSTREAM_NAME",
    "AURELIUS_ATLAS_WEBAPP_OTLP_ENDPOINT",
    "AURELIUS_ATLAS_WEBAPP_REALIP_BLOCK",
    "AURELIUS_ATLAS_WEBAPP_TLS_CA_FILE",
    "AURELIUS_ATLAS_WEBAPP_TLS_CERT_FILE",
    "AURELIUS_ATLAS_WEBAPP_TLS_KEY_FILE",
    "AURELIUS_ATLAS_WEBAPP_OTEL_INGEST_TOKEN",
]


@pytest.mark.covers(rules=["CHT-23"])
def test__tls_service_and_https_probes(webapp_docs: list[dict[str, Any]]) -> None:
    """8080 ClusterIP with a TLS listener (DD-270): HTTPS probes and a chart-issued leaf."""
    service = find(webapp_docs, "Service", "atlas-webapp")
    assert service["spec"]["type"] == "ClusterIP"
    assert service["spec"]["ports"] == [{"name": "https", "port": 8080, "targetPort": 8080, "protocol": "TCP"}]
    app = container(find(webapp_docs, "Deployment", "atlas-webapp"), "webapp")
    assert app["readinessProbe"]["httpGet"]["scheme"] == "HTTPS"
    assert app["readinessProbe"]["httpGet"]["path"] == "/config.json"
    assert app["livenessProbe"]["httpGet"]["scheme"] == "HTTPS"
    cert = find(webapp_docs, "Certificate", "atlas-webapp")
    assert cert["spec"]["secretName"] == "atlas-webapp-tls"
    # CHT-22's SAN rule: the names the BackendTLSPolicy dials (SNI = Service).
    assert cert["spec"]["dnsNames"] == [
        "atlas-webapp",
        "atlas-webapp.atlas",
        "atlas-webapp.atlas.svc",
        "atlas-webapp.atlas.svc.cluster.local",
    ]
    # The listener's leaf pair mounts whole; the trust root stays item-picked.
    volumes = {v["name"]: v for v in pod_spec(find(webapp_docs, "Deployment", "atlas-webapp"))["volumes"]}
    assert volumes["leaf"]["secret"]["secretName"] == "atlas-webapp-tls"
    assert "items" not in volumes["leaf"]["secret"]
    assert volumes["ca"]["secret"]["items"] == [{"key": "ca.crt", "path": "ca.crt"}]


@pytest.mark.covers(rules=["CHT-23"])
def test__bring_your_own_leaf_renders_no_certificate() -> None:
    """tls.certSecretName brings the leaf: no Certificate, mounted as-is."""
    docs = helm_render(WEBAPP_CHART, value_files=TEST_VALUES, sets=("tls.certSecretName=my-leaf",))
    assert "Certificate" not in {d["kind"] for d in docs}
    volumes = {v["name"]: v for v in pod_spec(find(docs, "Deployment", "atlas-webapp"))["volumes"]}
    assert volumes["leaf"]["secret"]["secretName"] == "my-leaf"


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
def test__init_container_resolves_the_thirteen_placeholders(webapp_docs: list[dict[str, Any]]) -> None:
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
    # The init's env is exactly the thirteen names (CHT-25, DD-270).
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
    # The listener leaf paths (DD-270): the cert-manager Secret's key names,
    # mounted whole at tls.mountPath's sibling.
    assert env_value(envs, "AURELIUS_ATLAS_WEBAPP_TLS_CERT_FILE") == "/etc/aurelius-atlas/tls/leaf/tls.crt"
    assert env_value(envs, "AURELIUS_ATLAS_WEBAPP_TLS_KEY_FILE") == "/etc/aurelius-atlas/tls/leaf/tls.key"
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
    assert config["keycloak"]["realm"] == "aurelius-atlas"  # CHT-74: global.realm
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


@pytest.mark.covers(rules=["CHT-98"])
def test__resolved_config_volume_is_tmpfs(webapp_docs: list[dict[str, Any]]) -> None:
    """nginx-conf rides Memory, its secret-bearing content never on disk (CHT-98).

    The resolved config carries the legacy bearer in its otel_exporter block;
    the pid/temp/log emptyDirs beside it stay disk-backed — only this one
    holds a credential.
    """
    volumes = {v["name"]: v for v in pod_spec(find(webapp_docs, "Deployment", "atlas-webapp"))["volumes"]}
    assert volumes["nginx-conf"]["emptyDir"] == {"medium": "Memory"}
    for name in ("nginx-run", "nginx-lib", "nginx-log"):
        assert volumes[name]["emptyDir"] == {}, name


@pytest.mark.covers(rules=["CHT-99"])
def test__hsts_rides_the_listener_and_the_placeholder_gates_it() -> None:
    """HSTS renders through the placeholder; disabled substitutes nothing (CHT-99).

    Whole-directive placeholder like the realip block: the chart spells the
    add_header, the ConfigMap keeps only the hole, and the enable switch
    lands in the init's env — the compose/e2e shape is the empty side.
    """
    docs = helm_render(WEBAPP_CHART, value_files=TEST_VALUES)
    init = _init(find(docs, "Deployment", "atlas-webapp"), "resolve-nginx-config")
    hsts = env_value(env_map(init), "AURELIUS_ATLAS_WEBAPP_HSTS_HEADER")
    assert hsts == 'add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;'
    template = find(docs, "ConfigMap", "atlas-webapp-nginx")["data"]["nginx.conf.template"]
    assert "${AURELIUS_ATLAS_WEBAPP_HSTS_HEADER}" in template
    assert "Strict-Transport-Security" not in template  # substituted, not spelled
    off = helm_render(WEBAPP_CHART, value_files=TEST_VALUES, sets=("nginx.hsts.enabled=false",))
    off_init = _init(find(off, "Deployment", "atlas-webapp"), "resolve-nginx-config")
    assert env_value(env_map(off_init), "AURELIUS_ATLAS_WEBAPP_HSTS_HEADER") == ""


@pytest.mark.covers(rules=["CHT-100"])
def test__otel_location_carries_its_own_limiter(webapp_docs: list[dict[str, Any]]) -> None:
    """The browser-leg zone beside /api/'s, in the shipped asset and its e2e twin (CHT-100)."""
    template = find(webapp_docs, "ConfigMap", "atlas-webapp-nginx")["data"]["nginx.conf.template"]
    assert "limit_req_zone $atlas_api_limit_addr zone=atlas_otel:10m rate=600r/m;" in template
    otel_body = template.split("location /otel/ {")[1].split("}")[0]
    assert "limit_req zone=atlas_otel burst=100 nodelay;" in otel_body
    e2e = (WEBAPP_CHART.parent / "e2e/config/nginx.conf").read_text()
    assert "limit_req_zone $binary_remote_addr zone=atlas_otel:10m rate=600r/m;" in e2e
    e2e_otel_body = e2e.split("location /otel/ {")[1].split("}")[0]
    assert "limit_req zone=atlas_otel burst=100 nodelay;" in e2e_otel_body


@pytest.mark.covers(rules=["CHT-92"])
def test__image_digest_override_replaces_the_tag() -> None:
    """image.digest renders <base>@<digest> at both joins (CHT-92).

    The app container and the resolve-nginx-config init share the one
    reference, so an operator-set digest lands on both. The field ships
    empty (CHT-94: own images ride the signed chart artifact), so this is
    the override path — repo renders stay tag-shaped.
    """
    docs = helm_render(WEBAPP_CHART, value_files=TEST_VALUES, sets=(f"image.digest=sha256:{6:064d}",))
    deployment = find(docs, "Deployment", "atlas-webapp")
    expected = "ghcr.io/aureliusenterprise/aurelius-atlas-webapp@sha256:" + "0" * 63 + "6"
    assert container(deployment, "webapp")["image"] == expected
    assert _init(deployment, "resolve-nginx-config")["image"] == expected
