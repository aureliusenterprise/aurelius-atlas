"""SSL client configuration for the TLS-only local development broker.

The dev Kafka broker and Schema Registry serve TLS only (no plaintext
listener); every client must verify them against the local development CA
produced by `nx certgen` (see `tls.json`). These helpers build the
`confluent_kafka` client options so the caller only supplies the CA path.
"""

from collections.abc import Mapping

SECURITY_PROTOCOL_SSL = "SSL"
ENDPOINT_IDENTIFICATION_HTTPS = "https"

#: Bind addresses Docker publishes ports on; not valid TLS SNI/verification
#: names, so clients connect via ``localhost`` (covered by the dev cert SANs).
WILDCARD_HOSTS = frozenset({"0.0.0.0", "::"})  # noqa: S104  # published-port bind hosts, never bound here


def tls_host(host: str | None) -> str:
    """
    Return a host name usable for verified TLS connections.

    Docker publishes container ports on wildcard addresses (``0.0.0.0``/``::``)
    and tools like testcontainers report those verbatim (or ``None`` when the
    port is unpublished); hostname verification
    (``ssl.endpoint.identification.algorithm=https``) would then fail because
    wildcard addresses are not certificate SANs. Map those to ``localhost``,
    which is covered by the dev certificate SANs.

    Args:
        host (str | None): Host reported by the tooling (may be a wildcard bind).

    Returns:
        str: A verifiable host name.
    """
    if host is None or host in WILDCARD_HOSTS:
        return "localhost"
    return host


def ssl_client_config(
    *,
    ca_location: str,
    client_cert_location: str | None = None,
    client_key_location: str | None = None,
    extra: Mapping[str, str] | None = None,
) -> dict[str, str]:
    """
    Build `confluent_kafka` client options for connecting to the TLS dev broker.

    The dev broker's SSL listeners require client certificates (mTLS), so a
    client that reaches them (rather than the SASL/OAUTHBEARER listeners)
    passes its own leaf and key alongside the CA bundle.

    Args:
        ca_location (str): Path to the PEM CA bundle that signed the broker.
        client_cert_location (str | None): Path to the PEM client certificate,
            for listeners with ``ssl.client.auth`` required.
        client_key_location (str | None): Path to the PEM private key matching
            ``client_cert_location``.
        extra (Mapping[str, str] | None): Additional options merged last.

    Returns:
        dict[str, str]: Options to merge into a producer/consumer/admin config.
    """
    config = {
        "security.protocol": SECURITY_PROTOCOL_SSL,
        "ssl.ca.location": ca_location,
        "ssl.endpoint.identification.algorithm": ENDPOINT_IDENTIFICATION_HTTPS,
    }
    if client_cert_location:
        config["ssl.certificate.location"] = client_cert_location
    if client_key_location:
        config["ssl.key.location"] = client_key_location
    if extra:
        config.update(extra)
    return config
