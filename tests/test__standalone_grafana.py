"""The standalone stack's Grafana per tenant (TGF-01, TGF-02, TGF-12, TGF-13, 15.9).

The realm file, the compose pieces as Compose resolves them, the proxy's configuration and the one shot's script
are read as written.
"""

import json
from typing import Any

import pytest
from conftest import WORKSPACE, standalone_compose

STACK = WORKSPACE / "docker"
TENANTS = WORKSPACE / "apps/aurelius-atlas-server/docker/tenants.py"


def _environment(service: dict[str, Any]) -> dict[str, str]:
    environment = service["environment"]
    return environment if isinstance(environment, dict) else dict(item.split("=", 1) for item in environment)


@pytest.mark.covers(rules=["TGF-01"])
def test__the_realm_holds_grafanas_confidential_client() -> None:
    """The client ``grafana``: confidential, its secret a placeholder, its one redirect the stack's Grafana, and the
    organization claim in its tokens.
    """  # noqa: D205 - one sentence
    realm = json.loads((STACK / "keycloak/aurelius-atlas.json").read_text())
    client = next(c for c in realm["clients"] if c["clientId"] == "grafana")
    assert client["publicClient"] is False
    assert client["secret"] == "${GRAFANA_CLIENT_SECRET}"  # noqa: S105 - a placeholder
    assert client["redirectUris"] == ["https://localhost:9000/grafana/login/generic_oauth"]
    assert any("organization" in m["protocolMapper"] for m in client["protocolMappers"])
    keycloak = standalone_compose()["services"]["keycloak"]
    assert "GRAFANA_CLIENT_SECRET" in _environment(keycloak)


@pytest.mark.covers(rules=["TGF-02", "TGF-03", "TGF-15"])
def test__grafana_sits_behind_the_proxy_and_signs_in_through_keycloak_alone() -> None:
    """Grafana in the proxy's network with no port of its own, served from /grafana/; anonymous access and the
    login form off, generic OAuth on the client ``grafana``, no role taken from the token, everyone in the main
    organization with no role, its local administrator's password a secret.
    """  # noqa: D205 - one sentence
    grafana = standalone_compose()["services"]["grafana"]
    assert grafana["network_mode"] == "service:proxy"
    assert not grafana.get("ports")
    env = _environment(grafana)
    assert env["GF_SERVER_ROOT_URL"] == "https://localhost:9000/grafana/"
    assert env["GF_SERVER_SERVE_FROM_SUB_PATH"] == "true"
    assert (env["GF_AUTH_ANONYMOUS_ENABLED"], env["GF_AUTH_DISABLE_LOGIN_FORM"]) == ("false", "true")
    assert (env["GF_AUTH_GENERIC_OAUTH_ENABLED"], env["GF_AUTH_GENERIC_OAUTH_CLIENT_ID"]) == ("true", "grafana")
    assert env["GF_AUTH_GENERIC_OAUTH_SKIP_ORG_ROLE_SYNC"] == "true"
    assert (env["GF_USERS_AUTO_ASSIGN_ORG_ID"], env["GF_USERS_AUTO_ASSIGN_ORG_ROLE"]) == ("1", "None")
    assert env["GF_AUTH_GENERIC_OAUTH_TOKEN_URL"].startswith("https://localhost:9000/auth/realms/aurelius-atlas/")
    assert env["GF_SECURITY_ADMIN_PASSWORD"]
    major, minor = (int(part) for part in grafana["image"].split(":")[1].split("-")[0].split(".")[:2])
    assert (major, minor) >= (13, 3), "13.2 can't delete an organization (DD-765)"
    targets = {v["target"] if isinstance(v, dict) else v.split(":")[1] for v in grafana["volumes"]}
    assert not any("demo-tenant" in target for target in targets)
    nginx = (STACK / "gateway/nginx.conf").read_text()
    route = nginx[nginx.index("location /grafana/ {") :]
    assert "proxy_pass http://127.0.0.1:3000;" in route[: route.index("}")]


@pytest.mark.covers(rules=["TGF-12", "TGF-13"])
def test__the_one_shot_keeps_grafana_through_the_command() -> None:
    """The one shot names Grafana's API and its administrator's password, waits for Grafana, seeds the tenants'
    Grafana organizations with ``grafana sync``, and makes no store user of its own for Grafana.
    """  # noqa: D205 - one sentence
    tenants = standalone_compose()["services"]["tenants"]
    env = _environment(tenants)
    assert env["AURELIUS_ATLAS_SERVER_GRAFANA_URL"] == "http://127.0.0.1:3000"
    assert env["AURELIUS_ATLAS_SERVER_GRAFANA_ADMIN_PASSWORD"]
    assert "GRAFANA_ES_READER_PASSWORD" not in env
    assert "grafana" in tenants["depends_on"]
    script = TENANTS.read_text()
    assert '["grafana", "sync"]' in script
    assert "grafana_demo_reader" not in script
    assert not (STACK / "observability/config/grafana").exists()


@pytest.mark.covers(rules=["TDL-11"])
def test__the_server_names_grafanas_browser_address() -> None:
    """The stack's server gives the tenant's dashboards link on the proxy's Grafana address."""
    server = standalone_compose()["services"]["aurelius-atlas-server"]
    assert _environment(server)["AURELIUS_ATLAS_SERVER_GRAFANA_PUBLIC_URL"] == "https://localhost:9000/grafana"
