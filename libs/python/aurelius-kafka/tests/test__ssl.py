from aurelius_kafka import ssl_client_config, tls_host


def test__ssl_client_config() -> None:
    """Verify the SSL client options are built as expected."""
    config = ssl_client_config(ca_location="/certs/ca.pem")

    assert config == {
        "security.protocol": "SSL",
        "ssl.ca.location": "/certs/ca.pem",
        "ssl.endpoint.identification.algorithm": "https",
    }


def test__ssl_client_config_merges_extra() -> None:
    """Verify extra options are merged into the SSL client options."""
    config = ssl_client_config(ca_location="/certs/ca.pem", extra={"client.id": "test"})

    assert config["client.id"] == "test"
    assert config["security.protocol"] == "SSL"


def test__ssl_client_config_with_client_certificate() -> None:
    """Verify client certificate options for listeners requiring mTLS."""
    config = ssl_client_config(
        ca_location="/certs/ca.pem",
        client_cert_location="/certs/client.pem",
        client_key_location="/certs/client-key.pem",
    )

    assert config == {
        "security.protocol": "SSL",
        "ssl.ca.location": "/certs/ca.pem",
        "ssl.endpoint.identification.algorithm": "https",
        "ssl.certificate.location": "/certs/client.pem",
        "ssl.key.location": "/certs/client-key.pem",
    }


def test__tls_host_maps_wildcards() -> None:
    """Verify wildcard bind addresses are mapped to a verifiable host name."""
    assert tls_host("0.0.0.0") == "localhost"  # noqa: S104
    assert tls_host("::") == "localhost"
    assert tls_host(None) == "localhost"


def test__tls_host_keeps_named_hosts() -> None:
    """Verify concrete host names are kept as-is."""
    assert tls_host("localhost") == "localhost"
    assert tls_host("127.0.0.1") == "127.0.0.1"
    assert tls_host("broker") == "broker"
