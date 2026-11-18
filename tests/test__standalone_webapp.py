"""The standalone stack's webapp (SWA-01..04, 9.5d).

The stack's compose, the proxy's nginx config, the template resolver, the webapp's runtime config and the
stack's realm are read as written, the compose with the webapp's fragment merged in as compose merges it
(ADR 065), the resolver against the placeholders of the webapp's own nginx template.
"""

import json
import re
from typing import Any

import pytest
from conftest import WORKSPACE, standalone_compose

STACK = WORKSPACE / "docker"
FRAGMENT = WORKSPACE / "apps/aurelius-atlas-webapp/docker"
TEMPLATE = WORKSPACE / "apps/aurelius-atlas-webapp/nginx.conf.template"
PLACEHOLDER = re.compile(r"\$\{(AURELIUS_ATLAS_WEBAPP_[A-Z_]+)\}")


@pytest.fixture(scope="module")
def services() -> dict[str, Any]:
    """The stack's compose services, the included fragments merged in."""
    return standalone_compose()["services"]


@pytest.mark.covers(rules=["SWA-01"])
def test__the_webapp_runs_apart_from_the_proxy_on_its_resolved_config(services: dict[str, Any]) -> None:
    """A container of its own on the stack network, reading the filled template, config.json, certs (SWA-01)."""
    config, webapp = services["webapp-config"], services["aurelius-atlas-webapp"]
    assert config["image"] == webapp["image"] == "ghcr.io/aureliusenterprise/aurelius-atlas-webapp:local"
    assert "webapp-nginx-conf:/out" in config["volumes"]
    assert "network_mode" not in webapp
    assert services["aurelius-atlas-server"]["network_mode"] == "service:proxy"
    assert webapp["depends_on"]["webapp-config"] == {"condition": "service_completed_successfully"}
    assert set(webapp["volumes"]) == {
        "webapp-nginx-conf:/etc/nginx/conf.d:ro",
        "./config.json:/usr/share/nginx/html/config.json:ro",
        "../certs:/certs:ro",
    }


@pytest.mark.covers(rules=["SWA-02"])
def test__the_resolver_fills_every_placeholder_of_the_template() -> None:
    """Each placeholder of the webapp's template is replaced; its own API upstream is the server (SWA-02)."""
    script = (FRAGMENT / "resolve-nginx.sh").read_text()
    # Two quoting shapes: the literal fills (single-quoted) and the env-fed fills (double-quoted,
    # DD-675: the edge's OTLP leg takes the collector address and the ingest bearer from the piece).
    replaced = dict(
        re.findall(
            r"""-e ["']s\|\\?\$\{(AURELIUS_ATLAS_WEBAPP_[A-Z_]+)\}\|([^|]*)\|g["']""",
            script,
        )
    )
    assert set(replaced) == set(PLACEHOLDER.findall(TEMPLATE.read_text()))
    # The env-fed fills carry their literal default (DD-675): the collector's legacy gRPC port,
    # and the ingest bearer the stack's env-files supply.
    assert "https://otel-collector:4320" in replaced["AURELIUS_ATLAS_WEBAPP_OTLP_ENDPOINT"]
    assert replaced["AURELIUS_ATLAS_WEBAPP_OTEL_INGEST_TOKEN"] == "${AURELIUS_ATLAS_WEBAPP_OTEL_INGEST_TOKEN:-none}"  # noqa: S105 - the resolver's default, not a secret
    assert replaced["AURELIUS_ATLAS_WEBAPP_API_UPSTREAM"] == "https://proxy:21000"
    assert replaced["AURELIUS_ATLAS_WEBAPP_API_UPSTREAM_NAME"] == "aurelius-atlas-server"
    # The aux APIs share the proxy's network too, so their addresses are the proxy's ports and their
    # certificate names are the service names (the webapp reaches them through the proxy's namespace).
    assert replaced["AURELIUS_ATLAS_WEBAPP_LINEAGE_MODEL_UPSTREAM"] == "https://proxy:21002"
    assert replaced["AURELIUS_ATLAS_WEBAPP_LINEAGE_MODEL_UPSTREAM_NAME"] == "aurelius-atlas-lineage-model"
    assert replaced["AURELIUS_ATLAS_WEBAPP_VALIDATE_ENTITY_UPSTREAM"] == "https://proxy:21003"
    assert replaced["AURELIUS_ATLAS_WEBAPP_VALIDATE_ENTITY_UPSTREAM_NAME"] == "aurelius-atlas-validate-entity"
    assert replaced["AURELIUS_ATLAS_WEBAPP_TLS_CERT_FILE"] == "/certs/aurelius-atlas-webapp.pem"


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


@pytest.mark.covers(rules=["SWA-04"])
def test__the_webapp_signs_in_to_the_stacks_realm() -> None:
    """config.json names the realm aurelius-atlas under /auth and the public client, which returns to the
    stack (SWA-04). The host inside is the render placeholder (17.2, SPS-01): the proxy serves the
    rendered copy (docker/gateway/), and the file here keeps the default spelling.
    """  # noqa: D205 - one sentence
    config = json.loads((FRAGMENT / "config.json").read_text())
    assert config["keycloak"] == {
        "clientId": "aurelius",
        "realm": "aurelius-atlas",
        "url": "https://@STANDALONE_HOST@:9000/auth",
    }
    assert (config["apiBaseUrl"], config["atlasClientId"]) == ("/api", "aurelius-atlas-server")
    realm = json.loads((STACK / "keycloak/aurelius-atlas.json").read_text())
    public = next(client for client in realm["clients"] if client["clientId"] == "aurelius")
    assert public["standardFlowEnabled"]
    assert public["redirectUris"] == ["https://${STANDALONE_HOST}:9000/*"]
    assert public["webOrigins"] == ["https://${STANDALONE_HOST}:9000"]
    assert public["attributes"]["pkce.code.challenge.method"] == "S256"


@pytest.mark.covers(rules=["SWA-05"])
def test__the_realm_speaks_english_and_dutch_and_lets_the_webapp_save_the_language() -> None:
    """English and Dutch, English first; the public client may read and change its user's profile (SWA-05)."""
    realm = json.loads((STACK / "keycloak/aurelius-atlas.json").read_text())
    assert realm["internationalizationEnabled"]
    assert (realm["supportedLocales"], realm["defaultLocale"]) == (["en", "nl"], "en")
    mappings = realm["clientScopeMappings"]["account"]
    assert mappings == [{"client": "aurelius", "roles": ["manage-account", "view-profile"]}]
