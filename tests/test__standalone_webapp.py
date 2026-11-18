"""The standalone stack's webapp (SWA-01..04, 9.5d; SPC-02, SPC-04, DD-695).

The stack's compose, the proxy's nginx config, the stack's own static webapp nginx config, the webapp's
runtime config and the stack's realm are read as written, the compose with the webapp's fragment merged in
as compose merges it (ADR 065), the static config against the placeholders of the webapp's own nginx
template.
"""

import json
import re
from typing import Any

import pytest
from conftest import WORKSPACE, standalone_compose

STACK = WORKSPACE / "docker"
FRAGMENT = WORKSPACE / "apps/aurelius-atlas-webapp/docker"
TEMPLATE = WORKSPACE / "apps/aurelius-atlas-webapp/nginx.conf.template"
STACK_NGINX = STACK / "webapp/nginx.conf"
PLACEHOLDER = re.compile(r"\$\{(AURELIUS_ATLAS_WEBAPP_[A-Z_]+)\}")


@pytest.fixture(scope="module")
def services() -> dict[str, Any]:
    """The stack's compose services, the included fragments merged in."""
    return standalone_compose()["services"]


@pytest.mark.covers(rules=["SWA-01", "SPC-04"])
def test__the_webapp_runs_apart_from_the_proxy_on_a_static_config(services: dict[str, Any]) -> None:
    """A container of its own on the stack network, reading the stack's static nginx config, config.json
    and certs, with no service rendering anything (SWA-01; SPC-04, DD-695).
    """  # noqa: D205 - one sentence
    webapp = services["aurelius-atlas-webapp"]
    # The image is an install's knob over the nx docker-build default (the stack builds, never pulls).
    assert webapp["image"] == "${WEBAPP_IMAGE:-ghcr.io/aureliusenterprise/aurelius-atlas-webapp:local}"
    assert "webapp-config" not in services
    assert "network_mode" not in webapp
    assert services["aurelius-atlas-server"]["network_mode"] == "service:proxy"
    assert webapp["depends_on"] == {"aurelius-atlas-server": {"condition": "service_started"}}
    # The stack ships the file the webapp's nginx reads (SPC-04): a bind, not a rendered volume.
    assert set(webapp["volumes"]) == {
        "docker/webapp/nginx.conf:/etc/nginx/conf.d/default.conf:ro",
        "apps/aurelius-atlas-webapp/docker/config.json:/usr/share/nginx/html/config.json:ro",
        "${WEBAPP_CERTS_DIR:?name the webapp certificate folder}:/certs:ro",
    }


@pytest.mark.covers(rules=["SWA-02", "SPC-04"])
def test__the_stacks_static_config_names_every_upstream_and_holds_no_placeholder() -> None:
    """The stack's file answers every placeholder of the webapp's template with this stack's value and
    keeps no ingest token, because the proxy carries the browser's OTLP push (SWA-02; SPC-04, DD-695).
    """  # noqa: D205 - one sentence
    static = STACK_NGINX.read_text()
    # The template's placeholder set drives the check: a placeholder the image gains must be
    # answered here too, or the webapp fails at config parse (DD-262's rule for any deployment).
    assert PLACEHOLDER.findall(TEMPLATE.read_text()), "the template holds no placeholder to answer"
    assert not PLACEHOLDER.search(static), "a template placeholder left in the static file"
    # The upstreams the chart's init container renders for the same shape (DD-262), written in here.
    assert "set $api_upstream https://proxy:21000;" in static
    assert "proxy_ssl_name aurelius-atlas-server;" in static
    assert "set $otel_upstream https://otel-collector:4318;" in static
    assert "proxy_ssl_name otel-collector;" in static
    assert "set $lineage_model_upstream https://proxy:21002;" in static
    assert "proxy_ssl_name aurelius-atlas-lineage-model;" in static
    assert "set $validate_entity_upstream https://proxy:21003;" in static
    assert "proxy_ssl_name aurelius-atlas-validate-entity;" in static
    assert "resolver 127.0.0.11 valid=10s ipv6=off;" in static
    # The listener's own material, which the piece's cert mount supplies.
    assert "ssl_certificate /certs/aurelius-atlas-webapp.pem;" in static
    assert "ssl_certificate_key /certs/aurelius-atlas-webapp-key.pem;" in static
    assert static.count("proxy_ssl_trusted_certificate /certs/ca.pem;") == 4
    # No ingest token (DD-695): the browser's OTLP push rides the proxy, so the edge leg here is a
    # spare path and its exporter block states no bearer header.
    assert "header authorization" not in static
    assert "endpoint https://otel-collector:4320;" in static
    # The three clauses the resolver filled with nothing are gone rather than empty. The check
    # reads directives only: the file's own comments name what it leaves out.
    directives = "\n".join(line for line in static.splitlines() if not line.lstrip().startswith("#"))
    for gone in ("set_real_ip_from", "AURELIUS_ATLAS_WEBAPP_", "strict-transport-security"):
        assert gone not in directives, gone
    assert (FRAGMENT / "resolve-nginx.sh").exists() is False


@pytest.mark.covers(rules=["SWA-03"])
def test__the_proxy_routes_the_api_to_the_server_and_the_rest_to_the_webapp() -> None:
    """/api/ goes to the server; / and every path but /atlas2/, /auth/, /otel/ to the webapp by name (SWA-03)."""
    nginx = (STACK / "gateway/nginx.conf").read_text()
    api = nginx[nginx.index("    location /api/ {") :]
    assert api[: api.index("}")].count("proxy_pass https://127.0.0.1:21000;") == 1
    root = nginx[nginx.index("    location / {") :]
    assert "set $webapp https://aurelius-atlas-webapp:8080;" in root
    assert "proxy_pass $webapp;" in root
    assert "resolver 127.0.0.11" in nginx
    assert "proxy_ssl_name aurelius-atlas-webapp;" in root
    assert "proxy_redirect https://localhost:8080/ /;" in root
    assert "location = / {" not in nginx
    # /otel/ rides the collector's browser leg (DD-193, DD-675): TLS, shared CA, the service
    # name as SNI, and the /v1/* rewrite the collector's endpoints need.
    otel = nginx[nginx.index("    location /otel/ {") :]
    assert "set $otel https://otel-collector:4318;" in otel
    assert "rewrite ^/otel(/.*)$ $1 break;" in otel
    assert "proxy_ssl_name otel-collector;" in otel


@pytest.mark.covers(rules=["SWA-04", "SPC-02"])
def test__the_webapp_signs_in_to_the_stacks_realm() -> None:
    """config.json names the realm aurelius-atlas under /auth and the public client, which returns to the
    stack (SWA-04). It carries the one host the stack serves, written in - the same answer the proxy's
    server_name and the realm's URIs hold, and the proxy's catch-all serves this file to the browser
    (SPC-02, DD-694).
    """  # noqa: D205 - one sentence
    config = json.loads((FRAGMENT / "config.json").read_text())
    assert config["keycloak"] == {
        "clientId": "aurelius",
        "realm": "aurelius-atlas",
        "url": "https://localhost:9000/auth",
    }
    assert (config["apiBaseUrl"], config["atlasClientId"]) == ("/api", "aurelius-atlas-server")
    realm = json.loads((STACK / "keycloak/aurelius-atlas.json").read_text())
    public = next(client for client in realm["clients"] if client["clientId"] == "aurelius")
    assert public["standardFlowEnabled"]
    assert public["redirectUris"] == ["https://localhost:9000/*"]
    assert public["webOrigins"] == ["https://localhost:9000"]
    assert public["attributes"]["pkce.code.challenge.method"] == "S256"


@pytest.mark.covers(rules=["SWA-05"])
def test__the_realm_speaks_english_and_dutch_and_lets_the_webapp_save_the_language() -> None:
    """English and Dutch, English first; the public client may read and change its user's profile (SWA-05)."""
    realm = json.loads((STACK / "keycloak/aurelius-atlas.json").read_text())
    assert realm["internationalizationEnabled"]
    assert (realm["supportedLocales"], realm["defaultLocale"]) == (["en", "nl"], "en")
    mappings = realm["clientScopeMappings"]["account"]
    assert mappings == [{"client": "aurelius", "roles": ["manage-account", "view-profile"]}]
