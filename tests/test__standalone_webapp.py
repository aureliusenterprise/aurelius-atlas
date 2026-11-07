"""The standalone stack's webapp (SWA-01..04, 9.5d).

The compose file, the proxy's nginx config, the template resolver, the webapp's runtime config and the demo
realm are read as written, the resolver against the placeholders of the webapp's own nginx template.
"""

import json
import re
from typing import Any

import pytest
import yaml
from conftest import WORKSPACE

STANDALONE = WORKSPACE / "apps/aurelius-atlas-server/standalone"
TEMPLATE = WORKSPACE / "apps/aurelius-atlas-webapp/nginx.conf.template"
PLACEHOLDER = re.compile(r"\$\{(AURELIUS_ATLAS_WEBAPP_[A-Z_]+)\}")


@pytest.fixture(scope="module")
def services() -> dict[str, Any]:
    """The stack's compose services."""
    return yaml.safe_load((STANDALONE / "docker-compose.yaml").read_text())["services"]


@pytest.mark.covers(rules=["SWA-01"])
def test__the_webapp_runs_in_the_proxy_network_on_its_resolved_config(services: dict[str, Any]) -> None:
    """A one-shot fills the template into a volume; the webapp reads it, its config.json and its certs (SWA-01)."""
    config, webapp = services["webapp-config"], services["aurelius-atlas-webapp"]
    assert config["image"] == webapp["image"] == "ghcr.io/aureliusenterprise/aurelius-atlas-webapp:local"
    assert "webapp-nginx-conf:/out" in config["volumes"]
    assert webapp["network_mode"] == "service:proxy"
    assert webapp["depends_on"]["webapp-config"] == {"condition": "service_completed_successfully"}
    assert set(webapp["volumes"]) == {
        "webapp-nginx-conf:/etc/nginx/conf.d:ro",
        "./webapp/config.json:/usr/share/nginx/html/config.json:ro",
        "../../aurelius-atlas-webapp/certs:/certs:ro",
    }


@pytest.mark.covers(rules=["SWA-02"])
def test__the_resolver_fills_every_placeholder_of_the_template() -> None:
    """Each placeholder of the webapp's template is replaced, and the server is the API upstream (SWA-02)."""
    script = (STANDALONE / "webapp/resolve-nginx.sh").read_text()
    replaced = dict(re.findall(r"-e 's\|\$\{(AURELIUS_ATLAS_WEBAPP_[A-Z_]+)\}\|([^|]*)\|g'", script))
    assert set(replaced) == set(PLACEHOLDER.findall(TEMPLATE.read_text()))
    assert replaced["AURELIUS_ATLAS_WEBAPP_API_UPSTREAM"] == "https://127.0.0.1:21000"
    assert replaced["AURELIUS_ATLAS_WEBAPP_API_UPSTREAM_NAME"] == "aurelius-atlas-server"
    assert replaced["AURELIUS_ATLAS_WEBAPP_TLS_CERT_FILE"] == "/certs/aurelius-atlas-webapp.pem"


@pytest.mark.covers(rules=["SWA-03"])
def test__the_proxy_serves_the_webapp_at_the_root() -> None:
    """`/` and every path but /atlas2/, /auth/ and /otel/ go to the webapp, its redirects on port 9000 (SWA-03)."""
    nginx = (STANDALONE / "nginx.conf").read_text()
    root = nginx[nginx.index("    location / {") :]
    assert "proxy_pass https://127.0.0.1:8080;" in root
    assert "proxy_ssl_name aurelius-atlas-webapp;" in root
    assert "proxy_redirect https://localhost:8080/ /;" in root
    assert "location = / {" not in nginx
    assert re.search(r"location /otel/ \{\s*return 204;", nginx)


@pytest.mark.covers(rules=["SWA-04"])
def test__the_webapp_signs_in_to_the_demo_realm() -> None:
    """config.json names the demo realm under /auth and the public client, which returns to the stack (SWA-04)."""
    config = json.loads((STANDALONE / "webapp/config.json").read_text())
    assert config["keycloak"] == {"clientId": "aurelius", "realm": "demo", "url": "https://localhost:9000/auth"}
    assert (config["apiBaseUrl"], config["atlasClientId"]) == ("/api", "aurelius-atlas-server")
    realm = json.loads((STANDALONE / "keycloak/demo.json").read_text())
    public = next(client for client in realm["clients"] if client["clientId"] == "aurelius")
    assert public["standardFlowEnabled"]
    assert public["redirectUris"] == ["https://localhost:9000/*"]
    assert public["webOrigins"] == ["https://localhost:9000"]
    assert public["attributes"]["pkce.code.challenge.method"] == "S256"
