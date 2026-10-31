import base64
import json
import os
import socket
import ssl
import subprocess
import tempfile
import time
from collections.abc import AsyncIterator, Iterator
from pathlib import Path
from typing import Any

import dotenv
import httpx2 as httpx
import pytest
import pytest_asyncio
from aurelius_atlas_server_client import AtlasClient
from testcontainers.compose import DockerCompose

PROJECT = Path(__file__).resolve().parents[1]

TARGET = os.environ.get("ATLAS_E2E_TARGET", "compose")
"""Which deployment the suite drives: the compose stack (default — CI's lane)
or the Helm umbrella on minikube (the 10.5 POC, ATLAS_E2E_TARGET=cluster)."""

SERVICE = "aurelius-atlas-server"

# The cluster shapes (the umbrella install of tools/cluster/install.sh).
RELEASE = "atlas"
NAMESPACE = "atlas"
EDGE_HOST = "atlas.atlas.test"
"""The Gateway hostname whose HTTPRoute serves the webapp edge — the suite
dials the data path by its real name so SNI and certificate verification stay
honest (the chart's edge leaf carries this SAN)."""


def _helm_status() -> str:
    done = subprocess.run(
        ["helm", "status", RELEASE, "-n", NAMESPACE, "-o", "json"],
        capture_output=True,
        check=False,
    )
    if done.returncode != 0:
        return ""
    try:
        return str(json.loads(done.stdout).get("info", {}).get("status", ""))
    except json.JSONDecodeError:
        return ""


@pytest.fixture(scope="session")
def cluster() -> Iterator[dict[str, str]]:
    """The live umbrella install: gate, Gateway address, and the chart's CA.

    The compose lane short-circuits to an empty mapping (the gate and the
    kubectl reads are cluster-mode work). In cluster mode it fails fast —
    never a silent skip — when the install is absent: a POC lane whose signal
    you cannot trust is not a POC.
    """
    if TARGET != "cluster":
        yield {}
        return
    assert _helm_status() == "deployed", (
        f"release {RELEASE!r} in {NAMESPACE!r} is not deployed — run tools/cluster/install.sh up first"
    )
    done = subprocess.run(
        ["kubectl", "-n", NAMESPACE, "get", "gateway", RELEASE, "-o", "jsonpath={.status.addresses[0].value}"],
        capture_output=True,
        check=False,
    )
    gateway_ip = done.stdout.decode().strip()
    assert gateway_ip, "the Gateway carries no address — is `minikube tunnel` running? (install.sh up starts it)"
    done = subprocess.run(
        [
            "kubectl",
            "-n",
            NAMESPACE,
            "get",
            "secret",
            "aurelius-atlas-selfsigned-ca",
            "-o",
            "jsonpath={.data.ca\\.crt}",
        ],
        capture_output=True,
        check=False,
    )
    assert done.returncode == 0, "the chart's self-signed CA Secret is unreadable"
    ca_dir = Path(tempfile.mkdtemp(prefix="atlas-cluster-ca-"))
    ca_path = ca_dir / "ca.crt"
    ca_path.write_bytes(base64.b64decode(done.stdout))
    yield {"gateway_ip": gateway_ip, "ca_file": str(ca_path)}


@pytest.fixture(scope="session", autouse=True)
def _cluster_dns(request: pytest.FixtureRequest) -> Iterator[None]:
    """Resolve *.atlas.test to the Gateway address for this process only.

    The autouse no-op outside cluster mode. Patching the resolver (instead of
    /etc/hosts) keeps the requests on the real hostname — the HTTPRoute match,
    the SNI name, the verified SAN — while leaving the machine untouched; any
    library resolving through socket (httpx's pool included) gets it.
    """
    if TARGET != "cluster":
        yield
        return
    cluster = request.getfixturevalue("cluster")  # the install gate runs first
    real = socket.getaddrinfo

    # The shim's signature is socket.getaddrinfo's own; Any is the honest type
    # for a pass-through replacement (ANN401 waived here, not repo-wide). The
    # host arrives as bytes from httpcore2's resolver and str from others, so
    # both are matched.
    def patched(host: bytes | str | None, *args: Any, **kwargs: Any) -> Any:  # noqa: ANN401
        name = host.decode() if isinstance(host, bytes) else host
        if isinstance(name, str) and name.endswith(".atlas.test"):
            host = cluster["gateway_ip"].encode() if isinstance(host, bytes) else cluster["gateway_ip"]
        return real(host, *args, **kwargs)

    socket.getaddrinfo = patched
    try:
        yield
    finally:
        socket.getaddrinfo = real


@pytest.fixture(scope="session")
def server(_cluster_dns: None) -> Iterator[str]:
    """The server's base URL, from the lane ATLAS_E2E_TARGET picked.

    Compose (default): the e2e stack on the dev store, started here once
    healthy — ``docker compose up --wait`` returns when the image's healthcheck
    passes. Cluster (the 10.5 POC): the edge hostname through the installed
    umbrella, so traffic rides the whole deployment — Gateway, the webapp's
    nginx /api/ proxy, backend TLS to the server — not a bypass.
    """
    if TARGET == "cluster":
        yield f"https://{EDGE_HOST}"
        return
    with DockerCompose(context=Path(__file__).parent, env_file=str(PROJECT / ".env")) as compose:
        port = compose.get_service_port(SERVICE, 21000)
        yield f"https://localhost:{port}"


@pytest.fixture(scope="session")
def server_direct(_cluster_dns: None, server: str) -> Iterator[str]:
    """The server pod's own URL, bypassing the edge, per lane.

    The legacy dashboard is baked into the server image (DD-018) and served at
    its own root; at the edge, `/` belongs to the SPA. The compose lane shares
    the stack's one URL; the POC lane port-forwards the Service so the
    dashboard tests still exercise the dashboard, not the webapp.
    """
    if TARGET != "cluster":
        yield server
        return
    with socket.socket() as probe:
        probe.bind(("127.0.0.1", 0))
        local = probe.getsockname()[1]
    fwd = subprocess.Popen(
        ["kubectl", "-n", NAMESPACE, "port-forward", f"svc/{RELEASE}-server", f"{local}:21000"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    try:
        deadline = time.monotonic() + 30
        while time.monotonic() < deadline:
            if (
                subprocess.run(
                    [
                        "curl",
                        "-sk",
                        "--max-time",
                        "2",
                        f"https://127.0.0.1:{local}/api/atlas/admin/liveness",
                    ],
                    capture_output=True,
                    check=False,
                ).returncode
                == 0
            ):
                break
            time.sleep(0.5)
        else:
            pytest.fail("the server port-forward never became ready")
        yield f"https://127.0.0.1:{local}"
    finally:
        fwd.terminate()
        fwd.wait(timeout=10)


@pytest.fixture(scope="session")
def ca_file(cluster: dict[str, str]) -> str:
    """The CA that signed the server's certificate, per lane.

    The mkcert dev CA (`nx certgen`) for compose, the chart's self-signed CA
    pulled from the cluster Secret for the POC lane.
    """
    if TARGET == "cluster":
        return cluster["ca_file"]
    return str(PROJECT / "certs" / "ca.pem")


@pytest.fixture(scope="session")
def tempo_url(_cluster_dns: None) -> Iterator[str]:
    """Tempo's query API, per lane.

    The dev stack's loopback publish (CIA-03), or a port-forward to the
    cluster's Tempo Service — the suite's own local ingress, since the cluster
    publishes nothing to the host.
    """
    if TARGET != "cluster":
        yield "http://127.0.0.1:3200"
        return
    with socket.socket() as probe:
        probe.bind(("127.0.0.1", 0))
        local = probe.getsockname()[1]
    fwd = subprocess.Popen(
        ["kubectl", "-n", NAMESPACE, "port-forward", f"svc/{RELEASE}-observability-tempo", f"{local}:3200"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    try:
        deadline = time.monotonic() + 30
        while time.monotonic() < deadline:
            if (
                subprocess.run(
                    ["curl", "-sS", "--max-time", "2", f"http://127.0.0.1:{local}/ready"],
                    capture_output=True,
                    check=False,
                ).returncode
                == 0
            ):
                break
            time.sleep(0.5)
        else:
            pytest.fail("the Tempo port-forward never became ready")
        yield f"http://127.0.0.1:{local}"
    finally:
        fwd.terminate()
        fwd.wait(timeout=10)


@pytest.fixture(scope="session", autouse=True)
def _environment() -> None:
    """Load the project's decrypted settings, which the compose file reads."""
    dotenv.load_dotenv(PROJECT / ".env")


@pytest_asyncio.fixture(loop_scope="function")
async def client(server: str, ca_file: str) -> AsyncIterator[httpx.AsyncClient]:
    """A client for the running server over HTTPS, verifying it against the lane's CA."""
    async with httpx.AsyncClient(base_url=server, verify=ssl.create_default_context(cafile=ca_file)) as client:
        yield client


# The function loop (pytest-asyncio 1.x): the root config gives async fixtures
# a module loop, which here outlives the test loops its TLS connections were
# opened on — aclose then schedules on a closed loop ("Event loop is closed").
# On the function loop, the client, its requests, and aclose share one loop.
@pytest_asyncio.fixture(loop_scope="function")
async def api(server: str, ca_file: str) -> AsyncIterator[AtlasClient]:
    """The typed Atlas client for the running server over HTTPS (CL-11).

    The fixture builds the httpx pool and closes it (CL-02). The server's admin
    routes are open until 6.1, so the token source is empty — an empty source
    travels unauthenticated (CL-03), exactly as the dashboard calls arrive.
    """
    async with httpx.AsyncClient(base_url=server, verify=ssl.create_default_context(cafile=ca_file)) as http:
        yield AtlasClient(http, "")
