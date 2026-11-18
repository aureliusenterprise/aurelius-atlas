"""The standalone stack's one browser host and its certificates (17.2, SPS-01..10, DD-678..681).

The stack addresses itself by one value, `STANDALONE_HOST`, default `localhost`: the issuer, the realm's
browser URIs, the proxy's server name, the collector's validated issuer and the edge certificate all carry
it, and nothing else does. The suite reads the compose as written (the pieces merged, as compose merges
them, DD-671), the realm and the nginx and collector configs as shipped, and the certificate script and its
manifest as shipped - no Docker daemon, no issued certificates.
"""

import json
import os
import re
from typing import Any

import pytest
import yaml
from conftest import WORKSPACE, compose_load, resolved, resolved_from, standalone_compose

STACK = WORKSPACE / "docker"
GATEWAY_NGINX = STACK / "gateway/nginx.conf"
STACK_CONFIG = STACK / "observability/config/otel-collector.yaml"
SCRIPT = STACK / "make-certs.sh"
MANIFEST = STACK / "certs.txt"
README = STACK / "README.md"

# The compose-time spelling of the host variable as the pieces write it (SPS-01): the default lands
# when the operator sets nothing.
HOST = "${STANDALONE_HOST:-localhost}"
ISSUER = f"https://{HOST}:9000/auth"


@pytest.fixture(scope="module")
def services() -> dict[str, Any]:
    """The stack's compose services, the included fragments merged in."""
    return standalone_compose()["services"]


@pytest.mark.covers(rules=["SPS-01", "SPS-05"])
def test__every_app_dials_the_one_host_issuer(services: dict[str, Any]) -> None:
    """Keycloak's hostname, every issuer URL and token URL the stack hands an app, and the sample
    import's URLs carry the one host variable with localhost as its default (SPS-01, SPS-05, DD-678).
    """  # noqa: D205 - one sentence
    keycloak = services["keycloak"]
    assert keycloak["environment"]["KC_HOSTNAME"] == ISSUER
    assert keycloak["environment"]["STANDALONE_HOST"] == HOST
    server = services["aurelius-atlas-server"]["environment"]
    assert server["AURELIUS_ATLAS_SERVER_AUTH_SERVER_URL"] == f"{ISSUER}/"
    sample = services["sample-import"]["environment"]
    assert sample["ATLAS_URL"] == f"https://{HOST}:9000/atlas2"
    for name in (
        "aurelius-atlas-server",
        "aurelius-atlas-data2model",
        "aurelius-atlas-lineage-model",
        "aurelius-atlas-validate-entity",
    ):
        env = services[name]["environment"]
        prefix = name.upper().replace("-", "_")
        assert env[f"{prefix}_AUTH_SERVER_URL"] == f"{ISSUER}/", name
        assert env[f"{prefix}_OTEL_TOKEN_URL"] == f"{ISSUER}/realms/aurelius-atlas/protocol/openid-connect/token", name
    validator = services["aurelius-atlas-validate-entity"]["environment"]
    assert validator["AURELIUS_ATLAS_VALIDATE_ENTITY_TOKEN_URL"].startswith(ISSUER)
    assert sample["TOKEN_URL"].startswith(ISSUER)
    # With nothing set on the host, compose's interpolation is the localhost the stack always served.
    assert resolved(server["AURELIUS_ATLAS_SERVER_AUTH_SERVER_URL"]) == "https://localhost:9000/auth/"


@pytest.mark.covers(rules=["SPS-01", "SPS-03"])
def test__no_other_dial_follows_the_host(services: dict[str, Any]) -> None:
    """The internal in-network dials stay loopback names the internal leaves cover: the lineage and
    validator apps' legs to the server and the extractor do not carry the browser host (SPS-03).
    """  # noqa: D205 - one sentence
    lineage = services["aurelius-atlas-lineage-model"]["environment"]
    assert lineage["AURELIUS_ATLAS_LINEAGE_MODEL_ATLAS_BASE_URL"] == "https://localhost:21000"
    assert lineage["AURELIUS_ATLAS_LINEAGE_MODEL_DATA2MODEL_URL"] == "https://localhost:21001"
    validator = services["aurelius-atlas-validate-entity"]["environment"]
    assert validator["AURELIUS_ATLAS_VALIDATE_ENTITY_SERVER_BASE_URL"] == "https://localhost:21000"


@pytest.mark.covers(rules=["SPS-08"])
def test__the_collector_validates_the_hosts_issuer(services: dict[str, Any]) -> None:
    """The collector's one validated issuer carries the host through confmap's env provider, and the
    piece gives the container the variable so the reference always resolves (SPS-08, DD-675).
    """  # noqa: D205 - one sentence
    providers = yaml.safe_load(STACK_CONFIG.read_text())["extensions"]["oidc"]["providers"]
    assert providers[0]["issuer_url"] == "https://${env:STANDALONE_HOST}:9000/auth/realms/aurelius-atlas"
    collector = services["otel-collector"]
    assert collector["environment"]["STANDALONE_HOST"] == HOST


@pytest.mark.covers(rules=["SPS-04"])
def test__the_proxy_resolves_the_host_to_itself(services: dict[str, Any]) -> None:
    """The proxy maps the host to the loopback address, which the containers sharing its network
    namespace read as their /etc/hosts entry, so the browser URL reaches it from inside (SPS-04,
    DD-678).
    """  # noqa: D205 - one sentence
    proxy = services["proxy"]
    assert proxy["extra_hosts"] == [f"{HOST}:127.0.0.1"]
    # The apps that dial the host share this container's network namespace.
    for name in (
        "aurelius-atlas-server",
        "sample-import",
        "tenants",
        "aurelius-atlas-data2model",
        "aurelius-atlas-lineage-model",
        "aurelius-atlas-validate-entity",
    ):
        assert services[name]["network_mode"] == "service:proxy", name


@pytest.mark.covers(rules=["SPS-02"])
def test__the_edge_names_the_host_and_catchalls() -> None:
    """The proxy's server block names the host - rendered at boot by the gateway-config one shot,
    because the hardened nginx image has no envsubst - and stays the only, catch-all block on the
    loopback publish (SPS-02, DD-679).
    """  # noqa: D205 - one sentence
    nginx = GATEWAY_NGINX.read_text()
    assert "server_name @STANDALONE_HOST@;" in nginx
    assert nginx.count("\nserver {") == 1
    # The browser's runtime config answers from the proxy, rendered for the host (SPS-01's browser leg).
    assert "location = /config.json {" in nginx
    assert "alias /srv/config.json;" in nginx
    gateway = compose_load(STACK / "gateway/compose.yaml")["services"]["gateway-config"]
    assert gateway["environment"]["STANDALONE_HOST"] == "${STANDALONE_HOST:-localhost}"
    rendered = re.findall(r"@STANDALONE_HOST@", nginx)
    assert len(rendered) == 1  # only the server name
    config = json.loads((WORKSPACE / "apps/aurelius-atlas-webapp/docker/config.json").read_text())
    assert config["keycloak"]["url"] == "https://@STANDALONE_HOST@:9000/auth"


@pytest.mark.covers(rules=["SPS-03"])
def test__the_proxy_still_reaches_the_stack_by_service_names() -> None:
    """Changing the host changes no internal hop: the proxy still dials the server on loopback with
    its leaf's localhost name, the webapp and the collector by service name SNI, Keycloak by name on
    the plaintext listener (SPS-03, DD-679).
    """  # noqa: D205 - one sentence
    nginx = GATEWAY_NGINX.read_text()
    assert nginx.count("proxy_ssl_name localhost;") == 2  # the server's two locations
    assert "proxy_ssl_name otel-collector;" in nginx
    assert "proxy_ssl_name aurelius-atlas-webapp;" in nginx
    assert "set $keycloak http://keycloak:8080;" in nginx


@pytest.mark.covers(rules=["SPS-02", "SPS-03"])
def test__only_the_edge_manifest_line_names_the_host() -> None:
    """The script's manifest names the browser host on the edge leaf alone - beside localhost and
    127.0.0.1, which every leaf keeps - and no internal leaf ever names it (SPS-02, SPS-03, DD-679).
    """  # noqa: D205 - one sentence
    lines = [line.split() for line in MANIFEST.read_text().splitlines() if line and not line.startswith("#")]
    assert lines, "the manifest holds the stack's leaves"
    edge = [line for line in lines if "$HOST" in line]
    assert [line[1] for line in edge] == ["aurelius-atlas-server"]
    for line in lines:
        sans = line[2:]
        assert "localhost" in sans, line
        assert "127.0.0.1" in sans, line
        assert line[1] in sans, line  # every leaf names the service it serves


@pytest.mark.covers(rules=["SPS-06", "SPS-07"])
def test__the_realm_carries_the_host_not_its_literal(services: dict[str, Any]) -> None:
    """The two clients' redirect URIs, web origins and post-logout URIs are the host placeholder,
    which the import fills from Keycloak's environment - the realm asset names no literal host
    (SPS-06, DD-680). A restart cannot refresh a stored realm; README.md gives the two paths
    (SPS-07).
    """  # noqa: D205 - one sentence
    realm = json.loads((STACK / "keycloak/aurelius-atlas.json").read_text())
    clients = {client["clientId"]: client for client in realm["clients"]}
    for client_id in ("aurelius", "aurelius-atlas-server"):
        client = clients[client_id]
        assert "localhost" not in json.dumps(client), client_id
    public = clients["aurelius"]
    assert public["redirectUris"] == ["https://${STANDALONE_HOST}:9000/*"]
    assert public["webOrigins"] == ["https://${STANDALONE_HOST}:9000"]
    assert public["attributes"]["post.logout.redirect.uris"] == "https://${STANDALONE_HOST}:9000/*"
    server = clients["aurelius-atlas-server"]
    assert server["redirectUris"] == ["https://${STANDALONE_HOST}:9000/atlas2/login.jsp"]
    assert server["attributes"]["post.logout.redirect.uris"] == "https://${STANDALONE_HOST}:9000/atlas2/"
    # The import resolves the placeholder (the flag JAVA_OPTS already carried for the secrets), from
    # the container's environment - measured on Keycloak 26.7 (DD-680).
    keycloak = services["keycloak"]
    assert "-Dkeycloak.migration.replace-placeholders=true" in keycloak["environment"]["JAVA_OPTS"]
    assert keycloak["environment"]["STANDALONE_HOST"] == HOST
    # What the stored realm becomes for a host: the placeholder is compose-free, so Keycloak's own
    # substitution is the only step - proven here against the value the environment carries.
    assert resolved_from(public["redirectUris"][0], "atlas.test") == "https://atlas.test:9000/*"


@pytest.mark.covers(rules=["SPS-09"])
def test__the_shipped_script_issues_the_stacks_material() -> None:
    """docker/make-certs.sh exists, is executable, needs openssl alone, issues every leaf the stack
    mounts and the JVM truststore, and installs nothing into a trust store - bring-your-own stays the
    default posture (SPS-09, DD-681).
    """  # noqa: D205 - one sentence
    assert os.access(SCRIPT, os.X_OK)
    script = SCRIPT.read_text()
    assert "openssl" in script
    # The commands, not the prose: the header explains what the script leaves out (mkcert -install),
    # and the truststore comment names keytool as the tool the script does not need.
    commands = "\n".join(line for line in script.splitlines() if not line.lstrip().startswith("#"))
    for forbidden in ("mkcert", "keytool", "jq ", "certgen", "update-ca-certificates", "security add"):
        assert forbidden not in commands, forbidden
    manifest = MANIFEST.read_text()
    # Every directory the stack mounts a leaf from appears in the manifest (compose reads them as
    # ./../certs binds; the manifest spells them repo-relative).
    for path in (
        "apps/aurelius-atlas-server/certs",
        "apps/aurelius-atlas-webapp/certs",
        "apps/aurelius-atlas-embedder/certs",
        "apps/aurelius-atlas-data2model/certs",
        "apps/aurelius-atlas-lineage-model/certs",
        "apps/aurelius-atlas-validate-entity/certs",
        "infra/elasticsearch/certs",
        "infra/keycloak/certs",
        "infra/observability/certs",
    ):
        assert path in manifest, path
    assert "truststore.p12" in script  # Keycloak's JVM dials Postgres and OTLP with it
    # The CA lives outside the mounted trees, and its home is git-ignored like every certs/.
    assert 'ca_dir="$here/certs"' in script
    assert (STACK / "certs/.gitignore").read_text().splitlines()[0] == "*"


@pytest.mark.covers(rules=["SPS-07", "SPS-10"])
def test__the_readme_teaches_the_host_the_script_and_the_two_paths() -> None:
    """README.md names the host variable, the certificate script, the once-warn a private CA causes,
    and both ways to change the host on a stack that holds data (SPS-07, SPS-09, SPS-10).
    """  # noqa: D205 - one sentence
    readme = README.read_text()
    for needle in ("STANDALONE_HOST", "make-certs.sh", "down -v", "admin API", "warns once"):
        assert needle in readme, needle
    # Trust by mount, not by store: the README says the CA is mounted and never installed.
    assert "trust store" in readme
