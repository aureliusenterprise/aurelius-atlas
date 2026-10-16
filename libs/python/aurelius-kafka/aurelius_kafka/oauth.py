"""OAuth (OAUTHBEARER) client configuration for the Kafka dev cluster.

The dev Kafka broker exposes SASL_SSL listeners whose OAUTHBEARER tokens are
JWTs minted by the dedicated ``kafka`` realm of the dev Keycloak (see
``dev/keycloak/import/kafka.json``); the broker validates them against the
realm's JWKS endpoint. Clients fetch tokens with their own Keycloak client
credentials (client-credentials grant) from the realm's token endpoint.
These helpers build the ``confluent_kafka`` client options so the caller only
supplies the endpoint, credentials, and CA path.
"""

from collections.abc import Mapping

SECURITY_PROTOCOL_SASL_SSL = "SASL_SSL"
SASL_MECHANISM_OAUTHBEARER = "OAUTHBEARER"
OIDC_METHOD = "oidc"
ENDPOINT_IDENTIFICATION_HTTPS = "https"


def oauth_client_config(  # noqa: PLR0913  # every parameter is a distinct client config key
    *,
    token_endpoint_url: str,
    client_id: str,
    client_secret: str,
    ca_location: str | None = None,
    scope: str | None = None,
    extra: Mapping[str, str] | None = None,
) -> dict[str, str]:
    """
    Build `confluent_kafka` client options for OAUTHBEARER/OIDC authentication.

    When a ``ca_location`` is given it is applied to both ``ssl.ca.location``
    (broker TLS) and ``https.ca.location`` (the token endpoint HTTP client):
    in development the same CA normally signs both. Without it, the
    operating system's default trust stores are used for both.

    Args:
        token_endpoint_url (str): OIDC token endpoint of the ``kafka`` realm.
        client_id (str): Keycloak confidential client id (per-role).
        client_secret (str): Keycloak client secret.
        ca_location (str | None): Path to the PEM CA bundle that signed the
            broker and the token endpoint, or ``None`` for system trust.
        scope (str | None): Optional scope to request with the token grant.
        extra (Mapping[str, str] | None): Additional options merged last.

    Returns:
        dict[str, str]: Options to merge into a producer/consumer/admin config.

    Raises:
        ValueError: If ``token_endpoint_url`` is not an ``https://`` URL. The
            client-credentials grant posts the client secret to this endpoint;
            over plain http it would travel in cleartext, so a non-TLS URL is
            rejected here rather than left to the transport (librdkafka does
            not enforce it).
    """
    if not token_endpoint_url.startswith("https://"):
        message = (
            "Kafka OAuth token endpoint must use https:// — the client-credentials "
            f"grant would leak the client secret in cleartext: {token_endpoint_url!r}"
        )
        raise ValueError(message)
    config = {
        "security.protocol": SECURITY_PROTOCOL_SASL_SSL,
        "sasl.mechanism": SASL_MECHANISM_OAUTHBEARER,
        "sasl.oauthbearer.method": OIDC_METHOD,
        "sasl.oauthbearer.token.endpoint.url": token_endpoint_url,
        "sasl.oauthbearer.client.credentials.client.id": client_id,
        "sasl.oauthbearer.client.credentials.client.secret": client_secret,
        "ssl.endpoint.identification.algorithm": ENDPOINT_IDENTIFICATION_HTTPS,
    }
    if ca_location is not None:
        config["ssl.ca.location"] = ca_location
        config["https.ca.location"] = ca_location
    if scope is not None:
        config["sasl.oauthbearer.scope"] = scope
    if extra:
        config.update(extra)
    return config
