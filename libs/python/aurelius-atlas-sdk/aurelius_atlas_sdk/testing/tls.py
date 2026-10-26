"""
This module provides TLS helpers for tests.

Note:
    Please install the `testing` extra to use this module.
"""

import shutil
import tempfile
from collections.abc import Generator, Sequence
from contextlib import contextmanager
from pathlib import Path
from typing import NamedTuple

import trustme
from testcontainers.community.postgres import PostgresContainer

TLS_POSTGRES_IMAGE = "dhi.io/postgres:18-alpine3.23"
"""Hardened PostgreSQL image used by the TLS test arrangement."""

TLS_POSTGRES_HOST = "localhost"
"""Host test clients connect to.

The ephemeral certificates cover only loopback names and libpq verifies the
host parameter against them, so clients connect to localhost through the
published port rather than to ``get_container_host_ip()`` (a bridge/gateway
address in some Docker setups). This requires the Docker daemon to be
reachable on the local machine - the case in the dev container; a remote
DOCKER_HOST would need its address added as a SAN.
"""

DEFAULT_TLS_SANS: tuple[str, ...] = ("localhost", "127.0.0.1", "::1")
"""Default certificate identities: the loopback names and addresses."""

_PG_HBA_CONF = (
    "# TLS-only client authentication: local socket connections stay open for the\n"
    "# container's own tools (the testcontainers wait strategy uses psql over the\n"
    "# loopback socket); every TCP connection must present TLS. This mirrors\n"
    "# dev/postgres/pg_hba.conf so unit tests exercise the same posture as dev/e2e.\n"
    "local all all trust\n"
    "hostssl all all all scram-sha-256\n"
)

_TLS_STARTUP_COMMAND = (
    # The copy (not a direct bind-mount at the ssl paths) is Postgres' own
    # rule: the key must be 0600 and owned by the server user, and a bind
    # mount exposes host ownership. mktemp -d, not a fixed /tmp path: the
    # target must be born with the running user's ownership every boot -
    # fixed paths collide on a warm daemon ("File exists", run 40225940082;
    # then EACCES over a foreign-owned file, sticky /tmp, run 40228376483).
    # The template is ABSOLUTE: the hardened image is alpine/busybox, whose
    # mktemp with no template writes tmp.XXXXXX in the CWD (the postgres
    # user's CWD is / - "mktemp: : Permission denied", run 40229842880);
    # glibc (dev laptops) defaults to /tmp, so only CI caught this.
    "d=$(mktemp -d /tmp/atlas-certs.XXXXXX) &&"
    " install -m 600 /certs/server.pem $d/server.pem &&"
    " install -m 600 /certs/server-key.pem $d/server-key.pem &&"
    " exec docker-entrypoint.sh -c ssl=on"
    " -c ssl_cert_file=$d/server.pem"
    " -c ssl_key_file=$d/server-key.pem"
    " -c hba_file=/certs/pg_hba.conf"
)


def _write_tls_material(cert_dir: Path, sans: Sequence[str]) -> None:
    """Generate ephemeral TLS material for one container into ``cert_dir``.

    Writes a throwaway certificate authority, a server leaf certificate (with
    the given SANs) signed by it, and the TLS-only pg_hba.conf, mirroring the
    layout dev/postgres mounts.
    """
    ca = trustme.CA()
    leaf = ca.issue_cert(*sans)
    ca.cert_pem.write_to_path(cert_dir / "ca.pem")
    leaf.cert_chain_pems[0].write_to_path(cert_dir / "server.pem")
    leaf.private_key_pem.write_to_path(cert_dir / "server-key.pem")
    # World-readable on the host: the service user differs per image and
    # bind mounts keep host ownership; the entrypoint tightens the mode.
    (cert_dir / "server-key.pem").chmod(0o644)
    (cert_dir / "pg_hba.conf").write_text(_PG_HBA_CONF, encoding="utf-8")


class TlsCertificates(NamedTuple):
    """Ephemeral TLS material for a TLS-enforcing test container."""

    directory: Path
    """Directory to mount at /certs in the container (ca.pem, server certs, pg_hba.conf)."""

    ca_bundle_path: Path
    """PEM CA bundle clients point sslrootcert at to verify the server."""


@contextmanager
def tls_certificates(
    *,
    prefix: str = "aurelius-tls",
    sans: Sequence[str] = DEFAULT_TLS_SANS,
) -> Generator[TlsCertificates]:
    """Generate ephemeral TLS material, removing the directory again on exit.

    A throwaway CA and server certificate (SANs: ``sans``) live in a temporary
    directory - named with ``prefix`` - for the duration of the block, keeping
    the fixture as hermetic as the random credentials next to it; no
    certgen/decrypt is needed to run tests.

    Args:
        prefix: Name prefix for the temporary certificate directory.
        sans: Certificate identities (host names and addresses) the server
            certificate is issued for.

    Usage in a fixture::

        @pytest.fixture(scope="session")
        def db_tls_material() -> Generator[TlsCertificates]:
            with tls_certificates() as certs:
                yield certs
    """
    cert_dir = Path(tempfile.mkdtemp(prefix=f"{prefix}-"))
    # mkdtemp creates 0700; the container user must be able to traverse it.
    cert_dir.chmod(0o755)
    try:
        _write_tls_material(cert_dir, sans)
        yield TlsCertificates(directory=cert_dir, ca_bundle_path=cert_dir / "ca.pem")
    finally:
        shutil.rmtree(cert_dir, ignore_errors=True)


def configure_tls_postgres(container: PostgresContainer, certs: TlsCertificates) -> None:
    """Configure a PostgreSQL test container to enforce TLS, mirroring dev/postgres.

    Call before the container starts. The server comes up with ssl=on and a
    hostssl-only pg_hba.conf, so plaintext TCP connections are rejected
    server-side; clients connect with sslmode=verify-full against
    ``certs.ca_bundle_path`` (host: :data:`TLS_POSTGRES_HOST`).

    The hardened image runs as a fixed non-root user that cannot read
    host-owned key material it does not own, so — like dev/postgres — the
    certificates are copied into the container filesystem with strict
    permissions before startup (Postgres also refuses world-readable keys).
    The copy lands on an explicit ``/tmp`` tmpfs: the image's own ``/tmp``
    is 2775 root:999 (setgid, no sticky bit) in the digest a warm CI image
    store serves, where uid 70 gets EACCES on ``mktemp -d`` (run
    40240896184); pinning ``mode=1777`` keeps the boot independent of
    which build the daemon happens to have cached.
    """
    container.with_kwargs(entrypoint=["/bin/sh", "-c"])
    # with_tmpfs_mount, NOT with_kwargs(tmpfs=...): the fork's start()
    # passes self.tmpfs to create() as an explicit keyword, so a tmpfs
    # entry in _kwargs is a second one - TypeError: create() got
    # multiple values for keyword argument 'tmpfs' (CI run 40270804386;
    # the kwarg form only survived on daemons whose image /tmp is the
    # 1777 fresh-pull default, where the mount is a no-op failure).
    container.with_tmpfs_mount("/tmp", "mode=1777,exec")  # noqa: S108 - container mount target, not a host path
    container.with_env("POSTGRES_HOST_AUTH_METHOD", "scram-sha-256")
    container.with_command([_TLS_STARTUP_COMMAND])
    container.with_volume_mapping(certs.directory, "/certs", "ro")
