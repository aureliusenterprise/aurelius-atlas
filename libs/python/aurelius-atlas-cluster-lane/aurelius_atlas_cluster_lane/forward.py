"""The ServiceForward port-forward helper (CHT-104)."""

import socket
import subprocess
import time
from collections.abc import Iterator
from types import TracebackType
from typing import Self

from aurelius_atlas_cluster_lane.lane import DEFAULT_NAMESPACE, _lookup, _resolve_lock, _resolve_overrides

_NEEDS_CA_ERROR = "an honest HTTPS forward needs ca_file (or insecure=True)"
_NEVER_READY_ERROR = "the {} port-forward never became ready"

_LOOPBACK_NAMES = frozenset({"127.0.0.1", "::1", "localhost"})
"""Names that resolve to this machine already — a loopback dial needs no shim entry."""


def free_port() -> int:
    """A port number just freed by binding and releasing loopback:0."""
    with socket.socket() as probe:
        probe.bind(("127.0.0.1", 0))
        return int(probe.getsockname()[1])


class ServiceForward:
    """``kubectl port-forward`` of one Service to a free loopback port, with an honest dial name.

    The cluster exposes nothing to the host, so the suite forwards the Service
    it dials and the shim maps the Service's real name —
    ``<service>.<ns>.svc.cluster.local`` — onto the forward, keeping the port
    the URL names. The dial URL therefore carries this forward's own free
    loopback port (``<host>:<local_port>``): the hostname stays the real
    Service FQDN, so SNI and the verified SAN stay honest while the connection
    rides the Service (CHT-104). A host-only rewrite (not a host+port pair) is
    what makes the async path honest too — the async HTTP stack (anyio) resolves
    the host but connects on the URL's own port, so a port rewrite would be
    ignored and the dial would miss the forward; naming the URL at the local
    port and rewriting only the host reaches the forward on every stack. The
    chart's leaf carries the FQDN in its SAN, so verification is against the
    real name, never 127.0.0.1. The mapping registers for the life of the
    forward and leaves when it stops.

    Readiness is a curl poll of one path on the forwarded port. ``insecure``
    is for the loopback-only dial the baked-dashboard Playwright legs use
    (ADR 039's ``ignore_https_errors``): the URL names 127.0.0.1, whose
    certificate no SAN covers, so the probe must not verify it. A caller
    dialling a SAN-honest FQDN over the forward passes its CA file instead.
    """

    def __init__(
        self,
        service: str,
        service_port: int,
        host: str,
        *,
        namespace: str = DEFAULT_NAMESPACE,
        probe_path: str,
        scheme: str = "https",
        insecure: bool = False,
        ca_file: str | None = None,
        ready_timeout: float = 30.0,
    ) -> None:
        """Forward ``svc/<service>:<service-port>``; the dial name the shim maps is ``host``.

        With the shim installed, the URL ``<scheme>://<host>:<local-port>``
        resolves to this forward (a host-only rewrite — the URL names the free
        port itself); the loopback dial name the browser legs use is
        ``host="127.0.0.1"``, which no SAN covers (hence ``insecure=True``,
        ADR 039).
        """
        self._service = service
        self._service_port = service_port
        self._host = host
        self._namespace = namespace
        self._probe_path = probe_path
        self._scheme = scheme
        self._insecure = insecure
        self._ca_file = ca_file
        self._ready_timeout = ready_timeout
        self._local_port = free_port()
        self._process: subprocess.Popen[bytes] | None = None

    @property
    def local_port(self) -> int:
        """The loopback port the Service is forwarded to."""
        return self._local_port

    @property
    def url(self) -> str:
        """The base URL to dial the Service at: its real name, this forward's port.

        The hostname is the real Service FQDN (the SAN the leaf carries); the
        port is the free loopback port the Service is forwarded to, which the
        shim resolves from that name (CHT-104).
        """
        return f"{self._scheme}://{self._host}:{self._local_port}"

    def __enter__(self) -> Self:
        if self._host not in _LOOPBACK_NAMES:
            # A host-only rewrite: the URL already names the free port, and the
            # async HTTP stack connects on the URL's port regardless (CHT-104).
            # A loopback dial needs none — its URL resolves to itself.
            with _resolve_lock:
                _resolve_overrides[(self._host, None)] = ("127.0.0.1", None)
        self._process = subprocess.Popen(
            [
                "kubectl",
                "-n",
                self._namespace,
                "port-forward",
                f"svc/{self._service}",
                f"{self._local_port}:{self._service_port}",
            ],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        try:
            self._wait_ready()
        except BaseException:
            self._stop()
            raise
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        self._stop()

    def _stop(self) -> None:
        if self._host not in _LOOPBACK_NAMES:
            with _resolve_lock:
                _resolve_overrides.pop((self._host, None), None)
        if self._process is not None:
            self._process.terminate()
            try:
                self._process.wait(timeout=10)
            except subprocess.TimeoutExpired:  # pragma: no cover - a wedged kubectl plugin
                self._process.kill()
                self._process.wait(timeout=10)
            self._process = None

    def _wait_ready(self) -> None:
        cmd = ["curl", "-sS", "--max-time", "2"]
        if self._scheme == "https":
            if self._insecure:
                # The loopback browser dial (ADR 039): verify nothing, the
                # dial's own honesty bar is the Playwright leg's.
                cmd.insert(1, "-k")
                target = f"https://127.0.0.1:{self._local_port}{self._probe_path}"
            elif self._ca_file:
                # The curl twin of the shim: the dial name stays the FQDN, the
                # address is the forward — SNI and SAN verification stay honest
                # (CHT-104), so readiness proves the same thing the tests dial.
                cmd += ["--resolve", f"{self._host}:{self._local_port}:127.0.0.1", "--cacert", self._ca_file]
                target = f"https://{self._host}:{self._local_port}{self._probe_path}"
            else:
                raise ValueError(_NEEDS_CA_ERROR)
        else:
            target = f"http://127.0.0.1:{self._local_port}{self._probe_path}"
        deadline = time.monotonic() + self._ready_timeout
        while time.monotonic() < deadline:
            if subprocess.run([*cmd, target], capture_output=True, check=False).returncode == 0:
                return
            time.sleep(0.5)
        raise RuntimeError(_NEVER_READY_ERROR.format(self._service))


def forward_service(
    service: str,
    service_port: int,
    *,
    namespace: str = DEFAULT_NAMESPACE,
    host: str,
    probe_path: str,
    scheme: str = "https",
    insecure: bool = False,
    ca_file: str | None = None,
    ready_timeout: float = 30.0,
) -> Iterator[str]:
    """Context-manager sugar: run a forward for a session fixture, yield its dial URL.

    The pattern every cluster-mode fixture uses — start, yield the honest URL,
    terminate in the ``finally`` of the with-block (the pytest fixture's exit).
    """
    forward = ServiceForward(
        service,
        service_port,
        host,
        namespace=namespace,
        probe_path=probe_path,
        scheme=scheme,
        insecure=insecure,
        ca_file=ca_file,
        ready_timeout=ready_timeout,
    )
    with forward:
        yield forward.url


def shim_lookup(host: str, port: int | None = None) -> tuple[str, int | None] | None:
    """The live rewrite for a (host, port) pair — exposed for guard tests."""
    return _lookup(host, port)


__all__ = ["ServiceForward", "forward_service", "free_port", "shim_lookup"]
