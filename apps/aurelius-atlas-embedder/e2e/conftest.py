"""E2E fixtures: the embedder image with its real model, on TLS, and a client of it."""

import ssl
from collections.abc import Iterator
from pathlib import Path

import httpx2 as httpx
import pytest
from testcontainers.compose import DockerCompose

PROJECT = Path(__file__).resolve().parents[1]
CA_FILE = PROJECT / "certs" / "ca.pem"
"""The dev CA (`nx certgen`) that signed the embedder's certificate."""

SERVICE = "aurelius-atlas-embedder"


@pytest.fixture(scope="session")
def compose() -> Iterator[DockerCompose]:
    """The image, started and healthy: ``up --wait`` returns once its model has loaded (EMB-07)."""
    with DockerCompose(context=Path(__file__).parent.absolute()) as started:
        yield started


@pytest.fixture(scope="session")
def client(compose: DockerCompose) -> Iterator[httpx.Client]:
    """A client of the running embedder over HTTPS, verifying it against the dev CA."""
    port = compose.get_service_port(SERVICE, 21004)
    verify = ssl.create_default_context(cafile=str(CA_FILE))
    with httpx.Client(base_url=f"https://localhost:{port}", verify=verify, timeout=60) as started:
        yield started
