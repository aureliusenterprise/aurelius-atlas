"""A TLS-enabled Elasticsearch in a container, for tests that need a real server (DD-007).

Note:
    Please install the `testing` extra to use this module.
"""

import base64
import json
import secrets
import shutil
import ssl
import tempfile
import time
import urllib.error
import urllib.request
from collections.abc import Generator
from contextlib import contextmanager
from pathlib import Path

import trustme
from testcontainers.core.container import DockerContainer

from aurelius_atlas_store_es.health import HEALTHY_CLUSTER_STATUSES
from aurelius_atlas_store_es.settings import StoreSettings

ELASTICSEARCH_IMAGE = "dhi.io/elasticsearch:9.5-debian13"
"""Hardened Elasticsearch image; the same tag as ``dev/elasticsearch``."""

ELASTICSEARCH_HOST = "localhost"
"""Host test clients connect to: the ephemeral certificate covers only loopback names."""

STARTUP_TIMEOUT_SECONDS = 180.0
"""How long to wait for the cluster to report green or yellow."""

_CONFIG_DIR = "/usr/share/elasticsearch/config"

_REPO_ROOT = next(
    p for p in Path(__file__).resolve().parents if (p / "tools/es-coredump-agent/coredump-noop.jar").is_file()
)

_AGENT_JAR = _REPO_ROOT / "tools" / "es-coredump-agent" / "coredump-noop.jar"
"""The coredump-redirect javaagent (``tools/es-coredump-agent``): the ES image is
started with it via ``ES_JAVA_OPTS``. Without it, Elasticsearch 9.x aborts at
bootstrap on hosts that deny writes to ``/proc/self/coredump_filter`` (GKE's
container lockdown does this for every Docker container on its nodes); the
agent swaps the path for a harmless one. No-op elsewhere."""

_ELASTICSEARCH_YML = """\
cluster.name: aurelius-atlas-test
network.host: 0.0.0.0
discovery.type: single-node
xpack.security.enabled: true
xpack.security.autoconfiguration.enabled: false
xpack.security.http.ssl.enabled: true
xpack.security.http.ssl.certificate: tls/server.pem
xpack.security.http.ssl.key: tls/server-key.pem
xpack.security.transport.ssl.enabled: false
xpack.ml.enabled: false
node.store.allow_mmap: false
cluster.routing.allocation.disk.threshold_enabled: false
"""
"""The settings of ``dev/elasticsearch/config/elasticsearch.yml`` that matter for tests."""

STARTUP_TIMEOUT_ERROR = "Elasticsearch did not become healthy within {timeout} seconds"

LOG_TAIL_SUFFIX = "\n\nElasticsearch container log (last lines):\n{lines}"
"""Appended to the timeout message so a failed boot shows the server's own output."""


def _write_material(work_dir: Path) -> Path:
    """Write the node configuration and ephemeral TLS material; return the CA file.

    Files are world-readable because the server runs as its own user (uid 1000), which need not
    match the user running the tests. The key is throwaway and lives only as long as the container.
    """
    ca = trustme.CA()
    server = ca.issue_cert(ELASTICSEARCH_HOST, "127.0.0.1", "::1")

    tls_dir = work_dir / "tls"
    tls_dir.mkdir()
    ca_file = work_dir / "ca.pem"
    ca.cert_pem.write_to_path(ca_file)
    server.cert_chain_pems[0].write_to_path(tls_dir / "server.pem")
    server.private_key_pem.write_to_path(tls_dir / "server-key.pem")
    (work_dir / "elasticsearch.yml").write_text(_ELASTICSEARCH_YML)

    for path in (work_dir, tls_dir):
        path.chmod(0o755)
    for path in (*tls_dir.iterdir(), ca_file, work_dir / "elasticsearch.yml"):
        path.chmod(0o644)

    return ca_file


def _wait_until_healthy(settings: StoreSettings, timeout: float) -> None:
    """Poll the cluster health until it is green or yellow."""
    context = ssl.create_default_context(cafile=settings.ca_certs_path)
    token = base64.b64encode(f"{settings.username}:{settings.password.get_secret_value()}".encode()).decode()
    request = urllib.request.Request(  # noqa: S310 - the URL is built from an https-only settings object
        f"{settings.host_urls[0]}/_cluster/health",
        headers={"Authorization": f"Basic {token}"},
    )
    deadline = time.monotonic() + timeout

    while time.monotonic() < deadline:
        try:
            with urllib.request.urlopen(request, context=context, timeout=5) as response:  # noqa: S310
                if json.load(response).get("status") in HEALTHY_CLUSTER_STATUSES:
                    return
        except OSError, urllib.error.URLError, ValueError:
            pass
        time.sleep(1)

    raise TimeoutError(STARTUP_TIMEOUT_ERROR.format(timeout=timeout))


@contextmanager
def elasticsearch_container(
    image: str = ELASTICSEARCH_IMAGE,
    heap: str = "512m",
    timeout: float = STARTUP_TIMEOUT_SECONDS,
) -> Generator[StoreSettings]:
    """Start a single-node Elasticsearch with TLS and authentication on, and yield settings for it.

    The node is configured like ``dev/elasticsearch`` (DD-006): HTTPS only with a certificate from an
    ephemeral CA, basic authentication for ``elastic`` with a random password. The container and the
    TLS material are removed on exit.

    Args:
        image: The Elasticsearch image.
        heap: JVM heap size, used for both ``-Xms`` and ``-Xmx``.
        timeout: Seconds to wait for the cluster to become green or yellow.

    Yields:
        Settings that connect to the container through its published port on localhost.
    """
    work_dir = Path(tempfile.mkdtemp(prefix="aurelius-atlas-es-"))
    password = secrets.token_urlsafe(16)

    try:
        ca_file = _write_material(work_dir)
        container = (
            DockerContainer(image)
            .with_env("ELASTIC_PASSWORD", password)
            .with_env("ES_JAVA_OPTS", f"-Xms{heap} -Xmx{heap} -javaagent:/agent/coredump-noop.jar")
            .with_volume_mapping(str(_AGENT_JAR), "/agent/coredump-noop.jar", "ro")
            .with_volume_mapping(str(work_dir / "elasticsearch.yml"), f"{_CONFIG_DIR}/elasticsearch.yml", "ro")
            .with_volume_mapping(str(work_dir / "tls"), f"{_CONFIG_DIR}/tls", "ro")
            .with_exposed_ports(9200)
        )

        with container:
            settings = StoreSettings.model_validate(
                {
                    "hosts": [f"https://{ELASTICSEARCH_HOST}:{container.get_exposed_port(9200)}"],
                    "password": password,
                    "ca_certs": ca_file,
                },
            )
            try:
                _wait_until_healthy(settings, timeout)
            except TimeoutError:
                stdout, stderr = container.get_logs()
                log_tail = "\n".join((stdout + stderr).decode(errors="replace").splitlines()[-200:])
                detail = STARTUP_TIMEOUT_ERROR.format(timeout=timeout) + LOG_TAIL_SUFFIX.format(lines=log_tail)
                raise TimeoutError(detail) from None
            yield settings
    finally:
        shutil.rmtree(work_dir, ignore_errors=True)
