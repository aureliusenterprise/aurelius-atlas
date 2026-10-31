"""The lane gate, the resolver shim, the fixtures, and the token mint (CHT-103/104)."""

import base64
import contextlib
import json
import os
import socket
import ssl
import subprocess
import tempfile
import threading
import time
from collections.abc import Iterator
from pathlib import Path
from types import ModuleType
from typing import TYPE_CHECKING, Any

import httpx2 as httpx

if TYPE_CHECKING:
    from collections.abc import Callable

TARGET_ENV = "ATLAS_E2E_TARGET"
"""The environment variable naming the deployment a suite drives."""

DEFAULT_TARGET = "compose"
"""The default lane: the compose stack — CI's lane, every existing invocation."""

DEFAULT_RELEASE = "atlas"
DEFAULT_NAMESPACE = "atlas"
DEFAULT_DOMAIN = "atlas.test"
"""The umbrella install's shapes, per tools/cluster/install.sh (CHT-50)."""

CA_SECRET = "aurelius-atlas-selfsigned-ca"
"""The Secret the chart's cert-manager CA writes its certificate to (key ``ca.crt``)."""

_ALREADY_INSTALLED_ERROR = "the resolver shim is already installed"

_GATE_MESSAGE = (
    f"release {DEFAULT_RELEASE!r} in {DEFAULT_NAMESPACE!r} is not deployed — run tools/cluster/install.sh up first"
)
"""The fail-fast gate message (CHT-53/103): a cluster lane you cannot trust is not a lane."""

_ClusterDict = dict[str, str]


def lane_target() -> str:
    """Which deployment the suite drives (CHT-103).

    ``ATLAS_E2E_TARGET``: ``compose`` (the default — every existing invocation
    stays byte-identical) or ``cluster`` (the Helm umbrella of
    ``tools/cluster/install.sh up``).
    """
    return os.environ.get(TARGET_ENV, DEFAULT_TARGET)


# --- the resolver shim -------------------------------------------------------

_resolve_lock = threading.RLock()
"""Reentrant: install/teardown nest (the install's finally re-enters on the same thread)."""
_resolve_overrides: dict[tuple[str, int | None], tuple[str, int | None]] = {}
_real_getaddrinfo: Callable[..., Any] | None = None


def resolve_overrides() -> dict[tuple[str, int | None], tuple[str, int | None]]:
    """A copy of the shim's live rewrite table (for guards and diagnostics)."""
    with _resolve_lock:
        return dict(_resolve_overrides)


def set_rewrite(host: str, port: int | None, replacement: tuple[str, int | None]) -> None:
    """Register a ``(host, port) -> (host, port)`` rewrite with the shim's table.

    Exact-host keys win over the ``.suffix`` rules; a ``None`` port key matches
    any port, a ``None`` replacement port keeps the original. The
    :class:`~aurelius_atlas_cluster_lane.forward.ServiceForward` host-only shape
    (a ``None``-port key) and the finer (host, port) shape for callers that must
    move a port both register here.
    """
    with _resolve_lock:
        _resolve_overrides[(host, port)] = replacement


def clear_rewrite(host: str, port: int | None) -> None:
    """Drop one registered rewrite (the forward's life ends, the mapping leaves)."""
    with _resolve_lock:
        _resolve_overrides.pop((host, port), None)


@contextlib.contextmanager
def install_resolver_shim(domain: str = DEFAULT_DOMAIN) -> Iterator[None]:
    """Resolve ``*.<domain>`` to the Gateway and Service FQDNs to forwards, in-process only.

    Patching the resolver (instead of ``/etc/hosts``) keeps every request on its
    real hostname — the HTTPRoute match, the SNI name, the verified SAN — while
    leaving the machine untouched; any library resolving through ``socket``
    (httpx's pool included) gets it (CHT-104). The rewrite table matches a
    ``(host, port)`` pair, exact or by ``.suffix`` host match (the leading dot
    makes ``atlas.test`` itself match ``*.atlas.test``); a ``None`` port matches
    any, and a ``None`` replacement port keeps the original.
    :class:`~aurelius_atlas_cluster_lane.forward.ServiceForward` registers its
    host (a ``None``-port key, the URL carrying the forward's own port) for the
    life of the forward.

    The no-op outside cluster mode is the caller's job — :func:`cluster_fixture`
    and :func:`install_cluster_fixtures` skip the whole path on compose.
    """
    global _real_getaddrinfo  # noqa: PLW0603 - one process-wide patch, restored in finally.
    with _resolve_lock:
        if _real_getaddrinfo is not None:  # pragma: no cover - nested install is a bug
            raise RuntimeError(_ALREADY_INSTALLED_ERROR)
        _real_getaddrinfo = socket.getaddrinfo
        real = _real_getaddrinfo

        # The shim's signature is socket.getaddrinfo's own; Any is the honest
        # type for a pass-through replacement (ANN401 waived here, not repo-wide).
        # The host arrives as bytes from httpcore's resolver and str from others,
        # so both are matched (the 10.5 POC's acceptance fix).
        def patched(host: bytes | str | None, *args: Any, **kwargs: Any) -> Any:  # noqa: ANN401
            name = host.decode() if isinstance(host, bytes) else host
            port = args[0] if args else kwargs.get("port")
            if isinstance(name, str):
                with _resolve_lock:
                    replacement = _lookup(name, port if isinstance(port, int) else None)
                if replacement is not None:
                    new_host, new_port = replacement
                    host = new_host.encode() if isinstance(host, bytes) else new_host
                    if new_port is not None:
                        if args:
                            args = (new_port, *args[1:])
                        else:
                            kwargs["port"] = new_port
            return real(host, *args, **kwargs)

        socket.getaddrinfo = patched
        # The POC's blanket suffix rule: every *.atlas.test name lands on the
        # Gateway. Callers who need a finer mapping (a ServiceForward host, or
        # an exact (host, port) key) register it, and exact keys win over the
        # suffix rules.
        with _resolve_lock:
            _resolve_overrides[("." + domain, None)] = ("__gateway__", None)
    try:
        yield
    finally:
        remove_resolver_shim(domain)


def remove_resolver_shim(domain: str = DEFAULT_DOMAIN) -> None:
    """Uninstall the shim: restore ``socket.getaddrinfo`` and drop the domain rule."""
    global _real_getaddrinfo  # noqa: PLW0603 - the pair of install_resolver_shim.
    with _resolve_lock:
        if _real_getaddrinfo is None:
            return
        socket.getaddrinfo = _real_getaddrinfo
        _real_getaddrinfo = None
        _resolve_overrides.pop(("." + domain, None), None)


def _lookup(name: str, port: int | None) -> tuple[str, int | None] | None:
    """The live rewrite for a resolved (host, port), exact keys before suffix rules."""
    exact = _resolve_overrides.get((name, port))
    if exact is None:
        exact = _resolve_overrides.get((name, None))
    if exact is not None:
        return _materialize(exact)
    for (host, rule_port), replacement in _resolve_overrides.items():
        if rule_port is not None and rule_port != port:
            continue
        if host.startswith(".") and name.endswith(host):
            return _materialize(replacement)
    return None


def _materialize(replacement: tuple[str, int | None]) -> tuple[str, int | None]:
    """Resolve the ``__gateway__`` sentinel to the live Gateway address."""
    if replacement[0] == "__gateway__":
        return (_gateway_ip(), replacement[1])
    return replacement


_gateway_ip_cache: str | None = None


def _gateway_ip() -> str:
    global _gateway_ip_cache  # noqa: PLW0603 - process-lifetime cache, set on first resolve.
    if _gateway_ip_cache is None:
        _gateway_ip_cache = read_gateway_ip()
    return _gateway_ip_cache


# --- the gate and the cluster reads -------------------------------------------


def _helm_status(release: str, namespace: str) -> str:
    done = subprocess.run(
        ["helm", "status", release, "-n", namespace, "-o", "json"],
        capture_output=True,
        check=False,
    )
    if done.returncode != 0:
        return ""
    try:
        return str(json.loads(done.stdout).get("info", {}).get("status", ""))
    except json.JSONDecodeError:
        return ""


def cluster_gate(release: str = DEFAULT_RELEASE, namespace: str = DEFAULT_NAMESPACE) -> None:
    """Fail fast — never a silent skip — unless the umbrella release is ``deployed``.

    The message names ``install.sh up`` (CHT-53/103): a lane whose signal you
    cannot trust is not a lane.
    """
    assert _helm_status(release, namespace) == "deployed", _GATE_MESSAGE


def read_gateway_ip(
    release: str = DEFAULT_RELEASE,
    namespace: str = DEFAULT_NAMESPACE,
    *,
    timeout: float = 60.0,
    poll: float = 2.0,
) -> str:
    """The Gateway's external address, waited for (the tunnel assigns it late on cold starts)."""
    deadline = time.monotonic() + timeout
    gateway_ip = ""
    while time.monotonic() < deadline:
        done = subprocess.run(
            ["kubectl", "-n", namespace, "get", "gateway", release, "-o", "jsonpath={.status.addresses[0].value}"],
            capture_output=True,
            check=False,
        )
        gateway_ip = done.stdout.decode().strip()
        if gateway_ip:
            break
        time.sleep(poll)
    assert gateway_ip, "the Gateway carries no address — is `minikube tunnel` running? (install.sh up starts it)"
    return gateway_ip


def read_chart_ca(namespace: str = DEFAULT_NAMESPACE, secret: str = CA_SECRET) -> str:
    """Write the chart's self-signed CA (Secret ``ca.crt``) to a temp file; return its path."""
    done = subprocess.run(
        ["kubectl", "-n", namespace, "get", "secret", secret, "-o", "jsonpath={.data.ca\\.crt}"],
        capture_output=True,
        check=False,
    )
    assert done.returncode == 0, "the chart's self-signed CA Secret is unreadable"
    ca_dir = Path(tempfile.mkdtemp(prefix="atlas-cluster-ca-"))
    ca_path = ca_dir / "ca.crt"
    ca_path.write_bytes(base64.b64decode(done.stdout))
    return str(ca_path)


class Cluster:
    """The live umbrella install: the Gateway address and the chart CA (CHT-103)."""

    def __init__(self, gateway_ip: str, ca_file: str) -> None:
        self.gateway_ip = gateway_ip
        self.ca_file = ca_file


def cluster_fixture_dict(cluster: Cluster) -> _ClusterDict:
    """The install as the ``{"gateway_ip", "ca_file"}`` mapping fixtures hand out."""
    return {"gateway_ip": cluster.gateway_ip, "ca_file": cluster.ca_file}


def _cluster() -> Iterator[_ClusterDict]:
    """The session ``cluster`` fixture body: gate, Gateway address, and the chart CA.

    The compose lane short-circuits to an empty mapping (the gate and the
    kubectl reads are cluster-mode work). In cluster mode it fails fast — see
    :func:`cluster_gate`.
    """
    if lane_target() != "cluster":
        yield {}
        return
    cluster_gate()
    yield cluster_fixture_dict(Cluster(read_gateway_ip(), read_chart_ca()))


def _cluster_dns(request: Any) -> Iterator[None]:  # noqa: ANN401 - pytest passes the FixtureRequest.
    """The session autouse shim fixture body: install the resolver for cluster mode only.

    Depending on ``cluster`` runs the install gate before any dial; the shim
    then maps ``*.atlas.test`` (and every :class:`~aurelius_atlas_cluster_lane.forward.ServiceForward`'s
    registered pair) onto loopback for this process only.
    """
    if lane_target() != "cluster":
        yield
        return
    request.getfixturevalue("cluster")  # the install gate runs first
    with install_resolver_shim():
        yield


def ca_file_fixture(cluster: _ClusterDict, project_certs: Path) -> str:
    """The ``ca_file`` fixture body: the chart CA on cluster, the mkcert dev CA on compose.

    Args:
        cluster: The session ``cluster`` mapping (empty outside cluster mode).
        project_certs: The project's ``certs/`` directory (``nx certgen`` output).
    """
    if lane_target() == "cluster":
        return cluster["ca_file"]
    return str(project_certs / "ca.pem")


def install_cluster_fixtures(module: ModuleType, project_certs: Path) -> None:
    """Install the session-scoped ``cluster``, ``_cluster_dns``, and ``ca_file`` fixtures.

    The library keeps its kubectl-shaped code out of pytest11 plugin autoload
    (CHT-103: a compose-mode consumer must never import cluster paths at call
    time through every pytest run in the workspace); a conftest opts in with
    this one call and keeps only what is *its* lane shape — which services,
    which clients.

    ``module`` is the calling conftest module (``sys.modules[__name__]``):
    pytest collects a conftest's fixtures by scanning that module's own
    namespace at collection time, so that is where the decorated fixtures
    are installed.
    """
    import pytest  # noqa: PLC0415 - pytest enters only when a conftest opts in (CHT-103).

    ns = vars(module)
    ns["cluster"] = pytest.fixture(scope="session")(_cluster)
    ns["_cluster_dns"] = pytest.fixture(scope="session", autouse=True)(_cluster_dns)
    ns["ca_file"] = pytest.fixture(scope="session")(lambda cluster: ca_file_fixture(cluster, project_certs))


# --- the token mint ------------------------------------------------------------


def mint_token(
    issuer_base_url: str,
    password: str,
    *,
    realm: str = "master",
    client_id: str = "aurelius",
    username: str = "aurelius-writer",
    ca_file: str,
    timeout: float = 120.0,
) -> str:
    """A bearer token from the realm's password grant, waited for (a warming realm retries).

    One mint, two origins: the compose lane calls it with the dev realm's
    loopback-published URL, the cluster lane with the edge's
    ``https://keycloak.<domain>`` — the same issuer origin the deployed pods
    themselves verify against (DD-265's split horizon makes it honest). The
    public ``aurelius`` client's tokens carry ``azp=aurelius`` (CHT-79); the
    aux charts' minikube audience override (CHT-105) is what accepts them.
    """
    deadline = time.monotonic() + timeout
    last_error: Exception | None = None
    while time.monotonic() < deadline:
        try:
            response = httpx.post(
                f"{issuer_base_url}/realms/{realm}/protocol/openid-connect/token",
                data={
                    "client_id": client_id,
                    "grant_type": "password",
                    "username": username,
                    "password": password,
                },
                verify=ssl.create_default_context(cafile=ca_file),
                timeout=10,
            )
            response.raise_for_status()
            return str(response.json()["access_token"])
        except (httpx.HTTPError, KeyError) as error:  # The realm import may still be running.
            last_error = error
            time.sleep(2)
    timeout_error = TimeoutError(f"the realm at {issuer_base_url} served no token within {timeout}s")
    raise timeout_error from last_error
