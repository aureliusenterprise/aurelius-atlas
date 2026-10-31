import ssl
import sys
from collections.abc import AsyncIterator, Iterator
from pathlib import Path

import dotenv
import httpx2 as httpx
import pytest
import pytest_asyncio
from aurelius_atlas_cluster_lane import ServiceForward, install_cluster_fixtures, lane_target
from aurelius_atlas_server_client import AtlasClient
from testcontainers.compose import DockerCompose

PROJECT = Path(__file__).resolve().parents[1]

SERVICE = "aurelius-atlas-server"

# The cluster shapes (the umbrella install of tools/cluster/install.sh).
RELEASE = "atlas"
NAMESPACE = "atlas"
EDGE_HOST = "atlas.atlas.test"
"""The Gateway hostname whose HTTPRoute serves the webapp edge — the suite
dials the data path by its real name so SNI and certificate verification stay
honest (the chart's edge leaf carries this SAN)."""

# The lane machinery is aurelius-atlas-cluster-lane's (10.5b, DD-282): the
# session `cluster` gate (fail-fast on a missing install), the autouse resolver
# shim, and the `ca_file` fixture. This conftest keeps only what is the server
# suite's own lane shape — which services it dials.
install_cluster_fixtures(sys.modules[__name__], PROJECT / "certs")


@pytest.fixture(scope="session")
def server(_cluster_dns: None) -> Iterator[str]:
    """The server's base URL, from the lane ATLAS_E2E_TARGET picked.

    Compose (default): the e2e stack on the dev store, started here once
    healthy — ``docker compose up --wait`` returns when the image's healthcheck
    passes. Cluster (the 10.5 POC): the edge hostname through the installed
    umbrella, so traffic rides the whole deployment — Gateway, the webapp's
    nginx /api/ proxy, backend TLS to the server — not a bypass.
    """
    if lane_target() == "cluster":
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
    dashboard tests still exercise the dashboard, not the webapp. The dial
    stays the loopback URL Playwright opens under ``ignore_https_errors``
    (ADR 039 — browsers bypass the shim), which is why its readiness probe is
    the insecure check (CHT-104's one sanctioned 127.0.0.1).
    """
    if lane_target() != "cluster":
        yield server
        return
    with ServiceForward(
        f"{RELEASE}-server",
        21000,
        "127.0.0.1",
        namespace=NAMESPACE,
        probe_path="/api/atlas/admin/liveness",
        insecure=True,
    ) as forward:
        yield f"https://127.0.0.1:{forward.local_port}"


@pytest.fixture(scope="session")
def tempo_url(_cluster_dns: None) -> Iterator[str]:
    """Tempo's query API, per lane.

    The dev stack's loopback publish (CIA-03), or a port-forward to the
    cluster's Tempo Service — the suite's own local ingress, since the cluster
    publishes nothing to the host.
    """
    if lane_target() != "cluster":
        yield "http://127.0.0.1:3200"
        return
    with ServiceForward(
        f"{RELEASE}-observability-tempo",
        3200,
        "127.0.0.1",
        namespace=NAMESPACE,
        probe_path="/ready",
        scheme="http",
    ) as forward:
        yield f"http://127.0.0.1:{forward.local_port}"


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
