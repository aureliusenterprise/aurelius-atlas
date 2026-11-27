"""The standalone stack's localhost surface, its scripts, and its certificates.

17.2 keeps the certificate rules (SPS-02/03/09/10) and 17.4 adds the localhost surface, the scripts
folder, and the host script (SPC-01..03, SPC-11, DD-694, DD-699).

The stack serves one host, `localhost`, written into every browser-facing file rather than rendered at boot:
the proxy's `nginx.conf`, the webapp's `config.json`, and the realm asset. A person who wants another host
runs the script that rewrites those files and re-issues the edge leaf. Every script a person runs by hand sits
in `docker/bin/`, and each finds the stack's root two folders above its own file. The suite reads the compose
as written (the pieces merged, as compose merges them, DD-671), the static files and the scripts as shipped,
and the certificate script and its manifest as shipped - no Docker daemon, no issued certificates.
"""

import json
import os
import re
import subprocess
from typing import Any

import pytest
import yaml
from conftest import WORKSPACE, compose_load, standalone_compose

STACK = WORKSPACE / "docker"
BIN = STACK / "bin"
GATEWAY_NGINX = STACK / "gateway/nginx.conf"
WEBAPP_CONFIG = WORKSPACE / "apps/aurelius-atlas-webapp/docker/config.json"
REALM = STACK / "keycloak/aurelius-atlas.json"
STACK_CONFIG = STACK / "observability/config/otel-collector.yaml"
SCRIPT = BIN / "make-certs.sh"
MANIFEST = STACK / "certs.txt"
README = STACK / "README.md"

# The five scripts a person runs by hand (SPC-11): the certificate script, the three of SPC-03, SPC-06 and
# SPC-07, and the tenant command's (TAD-12).
SCRIPTS = ("make-certs.sh", "set-host.sh", "import-sample.sh", "provision-tenants.sh", "tenant.sh")

# The three files that name the browser host (SPC-03), and no more.
HOST_BEARING = (
    "docker/gateway/nginx.conf",
    "apps/aurelius-atlas-webapp/docker/config.json",
    "docker/keycloak/aurelius-atlas.json",
)


@pytest.fixture(scope="module")
def services() -> dict[str, Any]:
    """The stack's compose services, the included fragments merged in."""
    return standalone_compose()["services"]


def _commands(script: str) -> str:
    """The script's lines without comments: the commands, not the prose."""
    return "\n".join(line for line in script.splitlines() if not line.lstrip().startswith("#"))


@pytest.mark.covers(rules=["SPC-02", "SPC-05"])
def test__every_app_dials_localhost(services: dict[str, Any]) -> None:
    """Keycloak's hostname, every issuer URL and token URL the stack hands an app, and the sample
    import's URLs carry the literal host the stack serves (SPC-02, DD-694). No piece carries a host
    variable, and no service renders one (SPS-01 retires).
    """  # noqa: D205 - one sentence
    issuer = "https://localhost:9000/auth"
    keycloak = services["keycloak"]
    assert keycloak["environment"]["KC_HOSTNAME"] == issuer
    assert "STANDALONE_HOST" not in keycloak["environment"]
    server = services["aurelius-atlas-server"]["environment"]
    assert server["AURELIUS_ATLAS_SERVER_AUTH_SERVER_URL"] == f"{issuer}/"
    sample = services["sample-import"]["environment"]
    assert sample["ATLAS_URL"] == "https://localhost:9000/atlas2"
    assert sample["TOKEN_URL"] == f"{issuer}/realms/aurelius-atlas/protocol/openid-connect/token"
    for name in (
        "aurelius-atlas-server",
        "aurelius-atlas-data2model",
        "aurelius-atlas-lineage-model",
        "aurelius-atlas-validate-entity",
    ):
        env = services[name]["environment"]
        prefix = name.upper().replace("-", "_")
        assert env[f"{prefix}_AUTH_SERVER_URL"] == f"{issuer}/", name
        assert env[f"{prefix}_OTEL_TOKEN_URL"] == f"{issuer}/realms/aurelius-atlas/protocol/openid-connect/token", name
    # The front door dials the same issuer (MCP-17) and carries no OTEL token
    # URL beside it — it has no ingest identity to mint with (MCP-18, DD-893).
    mcp = services["aurelius-atlas-mcp"]["environment"]
    assert mcp["AURELIUS_ATLAS_MCP_AUTH_SERVER_URL"] == f"{issuer}/"
    assert "AURELIUS_ATLAS_MCP_OTEL_TOKEN_URL" not in mcp
    # SPC-02: the stack names the variable nowhere, and declares no render service (SPC-05 drops
    # the Keycloak build one shot too).
    text = yaml.dump(standalone_compose())
    assert "STANDALONE_HOST" not in text
    for gone in ("gateway-config", "webapp-config", "keycloak-build"):
        assert gone not in services, gone
    # The one-shot dials (SPS-03, kept): the internal in-network legs never carry the browser host.
    lineage = services["aurelius-atlas-lineage-model"]["environment"]
    assert lineage["AURELIUS_ATLAS_LINEAGE_MODEL_ATLAS_BASE_URL"] == "https://localhost:21000"
    assert lineage["AURELIUS_ATLAS_LINEAGE_MODEL_DATA2MODEL_URL"] == "https://localhost:21001"
    validator = services["aurelius-atlas-validate-entity"]["environment"]
    assert validator["AURELIUS_ATLAS_VALIDATE_ENTITY_SERVER_BASE_URL"] == "https://localhost:21000"


@pytest.mark.covers(rules=["SPC-02", "SPC-08"])
def test__the_collector_validates_localhosts_issuer() -> None:
    """The collector's one validated issuer carries the literal host in the file it ships, so the
    config needs no env provider and the piece gives the container no host variable (SPC-02, SPC-08,
    DD-694, DD-698).
    """  # noqa: D205 - one sentence
    config = STACK_CONFIG.read_text()
    providers = yaml.safe_load(config)["extensions"]["oidc"]["providers"]
    assert providers[0]["issuer_url"] == "https://localhost:9000/auth/realms/aurelius-atlas"
    # The only env reference left is the ingest bearer (DD-196); no host rides confmap's env provider.
    assert "STANDALONE_HOST" not in config
    collector = compose_load(STACK / "observability/compose.yaml")["services"]["otel-collector"]
    assert "STANDALONE_HOST" not in (collector.get("environment") or {})


@pytest.mark.covers(rules=["SPC-01", "SPC-02"])
def test__the_proxy_names_localhost_and_catchalls() -> None:
    """The proxy's server block names `localhost` as a static asset and stays the only, catch-all
    block on the loopback publish (SPC-01, SPC-02, DD-694). The webapp serves its own `config.json`
    through the catch-all, so the proxy holds no `location = /config.json` block, and no container
    maps the host to itself: the apps share the proxy's namespace and dial its address.
    """  # noqa: D205 - one sentence
    nginx = GATEWAY_NGINX.read_text()
    assert "server_name localhost;" in nginx
    assert nginx.count("\nserver {") == 1
    assert "${" not in nginx
    assert "location = /config.json {" not in nginx
    proxy = compose_load(STACK / "gateway/compose.yaml")["services"]["proxy"]
    assert "./nginx.conf:/etc/nginx/conf.d/default.conf:ro" in proxy["volumes"]
    assert "extra_hosts" not in proxy
    services = standalone_compose()["services"]
    assert "extra_hosts" not in services["proxy"]
    # The apps that dial the host share this container's network namespace (SPS-04 retired with
    # extra_hosts: localhost is already this namespace's own name).
    for name in (
        "aurelius-atlas-server",
        "sample-import",
        "tenants",
        "aurelius-atlas-data2model",
        "aurelius-atlas-lineage-model",
        "aurelius-atlas-validate-entity",
        "aurelius-atlas-mcp",  # the front door (21.2, MCP-17)
    ):
        assert services[name]["network_mode"] == "service:proxy", name
    config = json.loads(WEBAPP_CONFIG.read_text())
    assert config["keycloak"]["url"] == "https://localhost:9000/auth"


@pytest.mark.covers(rules=["SPC-03"])
def test__the_realm_names_localhost_written_in() -> None:
    """The two clients' redirect URIs, web origins and post-logout URIs are the literal host (SPC-03,
    DD-694): the import stores them as they sit in the file, so the Keycloak environment carries no
    host and no placeholder flag. The host change path lives in docker/bin/set-host.sh.
    """  # noqa: D205 - one sentence
    realm = json.loads(REALM.read_text())
    clients = {client["clientId"]: client for client in realm["clients"]}
    public = clients["aurelius"]
    assert public["redirectUris"] == ["https://localhost:9000/*"]
    assert public["webOrigins"] == ["https://localhost:9000"]
    assert public["attributes"]["post.logout.redirect.uris"] == "https://localhost:9000/*"
    server = clients["aurelius-atlas-server"]
    assert server["redirectUris"] == ["https://localhost:9000/atlas2/login.jsp"]
    assert server["attributes"]["post.logout.redirect.uris"] == "https://localhost:9000/atlas2/"
    assert "${STANDALONE_HOST}" not in json.dumps(realm)
    keycloak = standalone_compose()["services"]["keycloak"]
    assert "replace-placeholders" not in keycloak["environment"]["JAVA_OPTS"]


@pytest.mark.covers(rules=["SPS-02", "SPS-03"])
def test__the_proxy_still_reaches_the_stack_by_service_names() -> None:
    """Changing nothing internally: the proxy still dials the server on loopback with its leaf's
    localhost name, the webapp and the collector by service name SNI, Keycloak by name on the
    plaintext listener (SPS-03, DD-679).
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


@pytest.mark.covers(rules=["SPS-09", "SPC-11"])
def test__the_shipped_script_issues_the_stacks_material() -> None:
    """docker/bin/make-certs.sh exists, is executable, needs openssl alone, issues every leaf the
    stack mounts and the JVM truststore, and installs nothing into a trust store - bring-your-own
    stays the default posture (SPS-09, DD-681). It finds the stack's root two folders above its own
    file, as every script of the folder does (SPC-11, DD-699).
    """  # noqa: D205 - one sentence
    assert os.access(SCRIPT, os.X_OK)
    script = SCRIPT.read_text()
    assert "openssl" in script
    # The commands, not the prose: the header explains what the script leaves out (mkcert -install),
    # and the truststore comment names keytool as the tool the script does not need.
    commands = _commands(script)
    for forbidden in ("mkcert", "keytool", "jq ", "certgen", "update-ca-certificates", "security add"):
        assert forbidden not in commands, forbidden
    # SPC-11: the anchor and the paths that hang off it.
    assert 'root="$(cd "$here/../.." && pwd)"' in script
    assert 'ca_dir="$here/../certs"' in script
    assert 'done <"$here/../certs.txt"' in script
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
        "apps/aurelius-atlas-mcp/certs",
        "infra/elasticsearch/certs",
        "infra/keycloak/certs",
        "infra/observability/certs",
    ):
        assert path in manifest, path
    assert "truststore.p12" in script  # Keycloak's JVM dials Postgres and OTLP with it
    # The CA lives outside the mounted trees, and its home is git-ignored like every certs/.
    assert (STACK / "certs/.gitignore").read_text().splitlines()[0] == "*"


@pytest.mark.covers(rules=["SPC-03", "SPC-11"])
def test__the_host_script_rewrites_the_three_files_and_reissues_the_leaf() -> None:
    """docker/bin/set-host.sh is executable and optional (SPC-03, DD-694): it reads the current host
    from the proxy's `server_name`, writes the new one into the three host-bearing files, calls the
    certificate script for the new name, and tells the person to clear the store - because Keycloak
    imports a realm only into an empty database, so a host change retires the keep-data path.
    """  # noqa: D205 - one sentence
    script = (BIN / "set-host.sh").read_text()
    assert os.access(BIN / "set-host.sh", os.X_OK)
    assert 'root="$(cd "$here/../.." && pwd)"' in script
    for path in HOST_BEARING:
        assert path in script, path
    assert "sed -n" in script  # the current host is read, not assumed
    assert "server_name" in script
    assert '"$here/make-certs.sh" "$host"' in script
    assert "down -v" in script  # the store clear the rule demands
    commands = _commands(script)
    # The substitution reaches the URL prefix, which is what every browser-facing host is.
    assert 'prefix="https://${current}:9000"' in commands
    # The always-on stack never runs it: no piece names it (SPC-03).
    text = yaml.dump(standalone_compose())
    assert "set-host" not in text


@pytest.mark.covers(rules=["SPC-06", "SPC-11"])
def test__the_sample_script_runs_the_demo_one_shot_through_compose() -> None:
    """docker/bin/import-sample.sh is executable, sits behind nothing but the profile it opens, and
    asks Compose to run the one shot: the service's wiring stays in the pieces (SPC-06, DD-697). The
    script names no secret, and the always-on stack starts no import - `sample-import` sits behind
    the profile `demo`.
    """  # noqa: D205 - one sentence
    script = (BIN / "import-sample.sh").read_text()
    assert os.access(BIN / "import-sample.sh", os.X_OK)
    assert 'root="$(cd "$here/../.." && pwd)"' in script
    assert "COMPOSE_PROFILES=demo" in script
    assert "run --rm sample-import" in script
    # The stack's env files supply the secrets (DD-669); the script names none of its own.
    for env_file in ("apps/aurelius-atlas-server/.env", "infra/keycloak/.env", "infra/elasticsearch/.env"):
        assert env_file in script, env_file
    assert not re.search(r"(SECRET|PASSWORD|TOKEN)=\S", _commands(script))
    services = standalone_compose()["services"]
    assert services["sample-import"]["profiles"] == ["demo"]


@pytest.mark.covers(rules=["TAD-12"])
def test__the_tenant_script_runs_the_command_in_the_tenancy_one_shot() -> None:
    """docker/bin/tenant.sh is executable and asks Compose to run the server's provisioning command in the
    `tenants` one shot, its entrypoint replaced and the script's arguments passed through, the profile
    `tenancy` open and tenancy on (TAD-12, DD-702). It names no secret, edits no file, and with no argument
    prints its usage and exits 2.
    """  # noqa: D205 - one sentence
    script = (BIN / "tenant.sh").read_text()
    assert os.access(BIN / "tenant.sh", os.X_OK)
    assert 'root="$(cd "$here/../.." && pwd)"' in script
    assert "COMPOSE_PROFILES=tenancy ATLAS_TENANCY_ENABLED=true" in script
    assert 'run --rm --no-deps --entrypoint python tenants -m aurelius_atlas_server.provisioning "$@"' in script
    for env_file in ("apps/aurelius-atlas-server/.env", "infra/keycloak/.env", "infra/elasticsearch/.env"):
        assert f"--env-file {env_file}" in script
    commands = _commands(script)
    assert "PASSWORD" not in commands
    assert "SECRET" not in commands
    for writer in (" > ", ">>", "sed -i", "tee "):
        assert writer not in commands, writer
    usage = subprocess.run(["bash", str(BIN / "tenant.sh")], capture_output=True, text=True, check=False)
    assert usage.returncode == 2
    assert "add <tenant> [--sample <name>] [--users atlas|all]" in usage.stdout


@pytest.mark.covers(rules=["SPC-07", "SPC-11"])
def test__the_tenants_script_runs_the_tenancy_one_shot_through_compose() -> None:
    """docker/bin/provision-tenants.sh is executable and asks Compose to run the `tenants` one shot,
    which sits behind the profile `tenancy` (SPC-07, DD-697). The script names no secret, and turns
    tenancy on for the run it starts.
    """  # noqa: D205 - one sentence
    script = (BIN / "provision-tenants.sh").read_text()
    assert os.access(BIN / "provision-tenants.sh", os.X_OK)
    assert 'root="$(cd "$here/../.." && pwd)"' in script
    assert "COMPOSE_PROFILES=tenancy" in script
    assert "ATLAS_TENANCY_ENABLED=true" in script
    assert "run --rm tenants" in script
    for env_file in ("apps/aurelius-atlas-server/.env", "infra/keycloak/.env", "infra/elasticsearch/.env"):
        assert env_file in script, env_file
    assert not re.search(r"(SECRET|PASSWORD|TOKEN)=\S", _commands(script))
    services = standalone_compose()["services"]
    assert services["tenants"]["profiles"] == ["tenancy"]


@pytest.mark.covers(rules=["SPC-11"])
def test__the_scripts_folder_holds_every_script_a_person_runs() -> None:
    """`docker/bin/` holds exactly the four scripts, each executable, and nothing else travels
    outside it (SPC-11, DD-699): the stack tree carries no other script a person runs by hand.
    """  # noqa: D205 - one sentence
    shipped = sorted(path.name for path in BIN.iterdir() if path.is_file())
    assert shipped == sorted(SCRIPTS)
    for name in SCRIPTS:
        assert os.access(BIN / name, os.X_OK), name
    # No stray script left behind at docker/'s root: the certificate script moved here (SPC-11).
    assert not (STACK / "make-certs.sh").exists()
    pieces = [
        *STACK.glob("*/compose.yaml"),
        *WORKSPACE.glob("apps/*/docker/compose.yaml"),
    ]
    for piece in pieces:
        text = piece.read_text()
        assert "make-certs.sh" not in text or "bin/make-certs.sh" in text, piece


@pytest.mark.covers(rules=["SPC-03", "SPS-10"])
def test__the_readme_teaches_the_host_script_and_the_clear() -> None:
    """README.md names the script that moves the host, the certificate script at its new path, the
    store clear a host change needs, and the one warning a private CA causes (SPC-03, SPS-09,
    SPS-10). The keep-data admin API path retired with the host machinery (SPS-07).
    """  # noqa: D205 - one sentence
    readme = README.read_text()
    for needle in ("docker/bin/set-host.sh", "docker/bin/make-certs.sh", "down -v", "trust store"):
        assert needle in readme, needle
    assert "STANDALONE_HOST" not in readme
    assert "warns once" in readme or "warning" in readme  # the private CA's browser warning stays named
