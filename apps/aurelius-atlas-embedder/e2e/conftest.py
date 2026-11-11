"""E2E fixtures: the embedder image with its real model, on TLS, and a client of it."""

import ssl
import subprocess
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

import httpx2 as httpx
import pytest
from testcontainers.compose import DockerCompose

PROJECT = Path(__file__).resolve().parents[1]
CA_FILE = PROJECT / "certs" / "ca.pem"
"""The dev CA (`nx certgen`) that signed the embedder's certificate."""

SERVICE = "aurelius-atlas-embedder"


def _startup_report(compose: DockerCompose, context: Path) -> str:
    """What the stack's containers say about themselves: the reason ``up --wait`` did not tell."""
    command = compose.docker_compose_command()
    parts = []
    for args in (["ps", "-a"], ["logs", "--no-color", "--tail", "50"]):
        try:
            run = subprocess.run(  # noqa: S603 - the fixed compose CLI, fixed arguments
                [*command, *args],
                cwd=context,
                capture_output=True,
                text=True,
                timeout=60,
                check=False,
            )
            parts.append(f"$ docker compose {' '.join(args)}\n{run.stdout}{run.stderr}")
        except Exception as note:  # noqa: BLE001 - a report that cannot be made must not hide the real failure
            parts.append(f"$ docker compose {' '.join(args)}: unavailable ({note})")
    return "\n".join(parts)


@contextmanager
def _started(context: Path) -> Iterator[DockerCompose]:
    """The stack up, or a failure that carries the containers' own words.

    ``up --wait`` answers a container that dies during boot (runs 42655774581/42655716287: the image
    ``exited (3)`` on loaded CI runners) with exit code 1 and the reason only in captured stderr, which
    reads as "the whole suite errored" rather than "the image died starting".
    """
    compose = DockerCompose(context=context)
    try:
        compose.start()
    except subprocess.CalledProcessError as failure:  # `up --wait` exits non-zero: the report below says why
        report = _startup_report(compose, context)  # before the teardown: a stopped stack reports nothing
        compose.stop(not compose.keep_volumes)
        pytest.fail(f"{SERVICE} failed to start: {failure}\n\n{report}")
    try:
        yield compose
    finally:
        compose.stop(not compose.keep_volumes)


@pytest.fixture(scope="session")
def compose() -> Iterator[DockerCompose]:
    """The image, started and healthy: ``up --wait`` returns once its model has loaded (EMB-07)."""
    with _started(Path(__file__).parent.absolute()) as started:
        yield started


@pytest.fixture(scope="session")
def client(compose: DockerCompose) -> Iterator[httpx.Client]:
    """A client of the running embedder over HTTPS, verifying it against the dev CA."""
    port = compose.get_service_port(SERVICE, 21004)
    verify = ssl.create_default_context(cafile=str(CA_FILE))
    with httpx.Client(base_url=f"https://localhost:{port}", verify=verify, timeout=60) as started:
        yield started
