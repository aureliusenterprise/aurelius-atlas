"""The dev store (``dev/elasticsearch``) as ``nx up`` starts it: ESD-01 to ESD-06 of increment 0.2."""

import asyncio
import json
import re
import ssl
import time
import urllib.error
import urllib.parse
import urllib.request
from asyncio.subprocess import PIPE, STDOUT
from pathlib import Path

import pytest
import trustme
from aurelius_atlas_store_es import ElasticsearchStore, HealthStatus, StoreSettings

PROMETHEUS_QUERY_URL = "http://localhost:9090/api/v1/query"
METRICS_QUERY = 'count({exported_job="dev-elasticsearch"})'
METRICS_TIMEOUT_SECONDS = 180
HEAP_UNITS = {"m": 1024**2, "g": 1024**3}
UNAUTHORIZED = 401

# The async fixtures run on the module loop (asyncio_default_fixture_loop_scope); so must async tests.
ON_MODULE_LOOP = pytest.mark.asyncio(loop_scope="module")


def request_status(settings: StoreSettings, *, authorization: str | None) -> int:
    """Send ``GET /`` over verified HTTPS and return the status code."""
    headers = {} if authorization is None else {"Authorization": authorization}
    request = urllib.request.Request(f"{settings.host_urls[0]}/", headers=headers)  # noqa: S310 - https only
    context = ssl.create_default_context(cafile=settings.ca_certs_path)
    try:
        with urllib.request.urlopen(request, context=context, timeout=10) as response:  # noqa: S310
            return response.status
    except urllib.error.HTTPError as error:
        return error.code


@ON_MODULE_LOOP
@pytest.mark.covers("aurelius_atlas_store_es.ElasticsearchStore.health", rules=["ESD-01"])
async def test__dev_elasticsearch_is_a_healthy_single_node_9(dev_store: ElasticsearchStore) -> None:
    """The dev store answers on https://localhost as a healthy, single-node Elasticsearch 9."""
    report = await dev_store.health()
    nodes = await dev_store.client.nodes.info()

    assert report.status is HealthStatus.UP
    assert report.cluster_name == "aurelius-atlas"
    assert report.version is not None
    assert report.version.startswith("9.")
    assert len(nodes["nodes"]) == 1


@pytest.mark.covers(rules=["ESD-02"])
def test__dev_elasticsearch_requires_authentication(dev_settings: StoreSettings) -> None:
    """A request without credentials, or with a wrong password, is rejected."""
    assert request_status(dev_settings, authorization=None) == UNAUTHORIZED
    assert request_status(dev_settings, authorization="Basic ZWxhc3RpYzp3cm9uZw==") == UNAUTHORIZED


@pytest.mark.covers(rules=["ESD-02"])
def test__dev_elasticsearch_serves_only_tls_from_the_workspace_ca(dev_settings: StoreSettings, tmp_path: Path) -> None:
    """Plain HTTP gets no answer, and a client that trusts another CA refuses the certificate."""
    plain = dev_settings.host_urls[0].replace("https://", "http://")
    with pytest.raises((urllib.error.URLError, ConnectionError)):
        urllib.request.urlopen(f"{plain}/", timeout=10)  # noqa: S310 - checks that plain HTTP is refused

    other_ca = tmp_path / "other-ca.pem"
    trustme.CA().cert_pem.write_to_path(other_ca)
    context = ssl.create_default_context(cafile=other_ca)
    with pytest.raises(urllib.error.URLError, match="CERTIFICATE_VERIFY_FAILED"):
        urllib.request.urlopen(f"{dev_settings.host_urls[0]}/", context=context, timeout=10)  # noqa: S310


@pytest.mark.covers(rules=["ESD-03"])
def test__dev_elasticsearch_password_is_only_in_the_encrypted_env(dev_env: dict[str, str], dev_dir: Path) -> None:
    """The password is stored encrypted, reaches the container by interpolation, and is in no other file."""
    encrypted = (dev_dir / ".env.enc").read_text()
    assert re.search(r"^ELASTICSEARCH_PASSWORD=ENC\[", encrypted, re.MULTILINE)
    assert "${ELASTICSEARCH_PASSWORD:?}" in (dev_dir / "docker-compose.yaml").read_text()

    password = dev_env["ELASTICSEARCH_PASSWORD"]
    plaintext = [
        path
        for path in dev_dir.rglob("*")
        if path.is_file() and path.name != ".env" and "certs" not in path.parts and password in path.read_text()
    ]
    assert plaintext == []


@ON_MODULE_LOOP
@pytest.mark.covers(rules=["ESD-05"])
async def test__dev_elasticsearch_heap_is_fixed(dev_store: ElasticsearchStore, dev_env: dict[str, str]) -> None:
    """The JVM heap is the configured size, minimum equal to maximum."""
    heap = dev_env["ELASTICSEARCH_HEAP"]
    expected = int(heap[:-1]) * HEAP_UNITS[heap[-1].lower()]

    nodes = await dev_store.client.nodes.info(metric="jvm")
    (node,) = nodes["nodes"].values()

    assert node["jvm"]["mem"]["heap_max_in_bytes"] == expected
    assert node["jvm"]["mem"]["heap_init_in_bytes"] == expected


@pytest.mark.covers(rules=["ESD-06"])
def test__dev_elasticsearch_metrics_reach_prometheus() -> None:
    """The sidecar's cluster metrics arrive in the dev Prometheus, attributed to dev-elasticsearch."""
    url = f"{PROMETHEUS_QUERY_URL}?{urllib.parse.urlencode({'query': METRICS_QUERY})}"
    deadline = time.monotonic() + METRICS_TIMEOUT_SECONDS
    series = 0
    while time.monotonic() < deadline:
        with urllib.request.urlopen(url, timeout=10) as response:  # noqa: S310 - the local dev Prometheus
            result = json.load(response)["data"]["result"]
        series = int(result[0]["value"][1]) if result else 0
        if series:
            break
        time.sleep(5)

    assert series > 0


@ON_MODULE_LOOP
@pytest.mark.covers(rules=["ESD-04"])
async def test__dev_elasticsearch_keeps_data_across_down_and_up(dev_settings: StoreSettings, dev_dir: Path) -> None:
    """A document written before ``docker compose down`` is there after the stack comes back up."""
    index = "esd-04-persistence"
    async with ElasticsearchStore(dev_settings) as store:
        await store.client.index(index=index, id="1", document={"kept": True}, refresh=True)

    compose = ["docker", "compose", "--project-directory", str(dev_dir)]
    for command in (["down"], ["up", "--detach", "--wait"]):
        process = await asyncio.create_subprocess_exec(*compose, *command, stdout=PIPE, stderr=STDOUT)
        output, _ = await process.communicate()
        assert process.returncode == 0, output.decode()

    async with ElasticsearchStore(dev_settings) as store:
        try:
            document = await store.client.get(index=index, id="1")
        finally:
            await store.client.indices.delete(index=index)

    assert document["_source"] == {"kept": True}
